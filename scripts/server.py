import os
import glob
import shutil
import logging 
from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import fmpy
from fmpy import read_model_description, extract
from fmpy.fmi2 import FMU2Slave

# Configuration
INPUTS_DIR = "/app/inputs"
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fmu-server")

app = FastAPI(title="FMU Simulation Server")

# Global State: Dictionary to hold active FMU instances
# Key: fmu_id (filename without ext), Value: FMU2Slave instance
active_fmus: Dict[str, FMU2Slave] = {}
fmu_paths: Dict[str, str] = {}

class StepRequest(BaseModel):
    inputs: Dict[str, float]
    dt: float

class StepResponse(BaseModel):
    time: float
    outputs: Dict[str, Any]
    status: str

# --- Helper Functions ---
def load_fmu_map():
    """Scans the inputs directory and populates the fmu_paths map."""
    if not os.path.exists(INPUTS_DIR):
        logger.error(f"Inputs directory {INPUTS_DIR} not found!")
        return

    files = glob.glob(os.path.join(INPUTS_DIR, "*.fmu"))
    for f in files:
        fmu_id = os.path.splitext(os.path.basename(f))[0]
        fmu_paths[fmu_id] = f
        logger.info(f"Registered FMU: {fmu_id} -> {f}")

# Initialize on startup
load_fmu_map()

# --- Endpoints ---

@app.get("/health")
def health_check():
    """Health check endpoint for Kubernetes/Cloud Run."""
    return {"status": "ok", "fmus_loaded": list(fmu_paths.keys())}

@app.get("/fmus")
def list_fmus():
    """List available FMU IDs."""
    return list(fmu_paths.keys())

@app.get("/fmus/{fmu_id}/metadata")
def get_metadata(fmu_id: str):
    """Get variable names and descriptions."""
    if fmu_id not in fmu_paths:
        raise HTTPException(status_code=404, detail="FMU not found")
    
    path = fmu_paths[fmu_id]
    try:
        md = read_model_description(path)
        variables = []
        for var in md.modelVariables:
            if var.causality in ['input', 'output', 'parameter']:
                variables.append({
                    "name": var.name,
                    "type": var.type,
                    "causality": var.causality,
                    "unit": var.unit,
                    "description": var.description
                })
        return {"modelName": md.modelName, "variables": variables}
    except Exception as e:
        logger.error(f"Error reading metadata: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/fmus/{fmu_id}/initialize")
def initialize_fmu(fmu_id: str, start_time: float = 0.0):
    """Initialize or Re-initialize the FMU simulation."""
    if fmu_id not in fmu_paths:
        raise HTTPException(status_code=404, detail="FMU not found")
    
    path = fmu_paths[fmu_id]
    
    # If already open, cleanup
    if fmu_id in active_fmus:
        try:
            active_fmus[fmu_id].terminate()
            active_fmus[fmu_id].freeInstance()
        except:
            pass
        del active_fmus[fmu_id]

    try:
        # Load and Instantiate
        dump_dir = os.path.join(INPUTS_DIR, f"{fmu_id}_start")
        unzipdir = extract(path, unzipdir=dump_dir)
        
        md = read_model_description(path)
        
        fmu = FMU2Slave(
            guid=md.guid,
            unzipDirectory=unzipdir,
            modelIdentifier=md.coSimulation.modelIdentifier,
            instanceName=fmu_id
        )
        
        fmu.instantiate()
        fmu.setupExperiment(startTime=start_time)
        fmu.enterInitializationMode()
        fmu.exitInitializationMode()
        
        active_fmus[fmu_id] = fmu
        logger.info(f"FMU {fmu_id} initialized at t={start_time}")
        
        return {"status": "initialized", "time": start_time}
        
    except Exception as e:
        logger.error(f"Failed to init FMU: {e}")
        raise HTTPException(status_code=500, detail=f"Initialization failed: {str(e)}")

@app.post("/fmus/{fmu_id}/step", response_model=StepResponse)
def step_simulation(fmu_id: str, request: StepRequest):
    """Advance the simulation by dt with provided inputs."""
    if fmu_id not in active_fmus:
        raise HTTPException(status_code=400, detail="FMU not initialized. Call /initialize first.")
    
    fmu = active_fmus[fmu_id]
    
    try:
        # 1. Set Inputs
        # FMPy requires mapping variable names to VR (Value References)
        # For simplicity in this template, we assume the user knows the variable names
        # and we iterate to find them. 
        # CAUTION: This is slow if doing lookup every step. 
        # Optimization: Cache VR lookup map.
        
        # Helper: Get VR map
        # Note: In a production server, cache this!
        vr_map = {v.name: v.valueReference for v in fmu.modelDescription.modelVariables}
        
        vrs_to_set = []
        values_to_set = []
        
        for name, value in request.inputs.items():
            if name in vr_map:
                vrs_to_set.append(vr_map[name])
                values_to_set.append(value)
            else:
                pass # Ignore unknown inputs or log warning
        
        if vrs_to_set:
            fmu.setReal(vrs_to_set, values_to_set)
        
        # 2. Do Step
        current_time = fmu.time
        fmu.doStep(currentCommunicationPoint=current_time, communicationStepSize=request.dt)
        
        # 3. Get Outputs
        # Retrieve all outputs? Or just specific ones?
        # For now, let's retrieve all outputs.
        # Optimization: Allow client to specify requested outputs in body.
        outputs = {}
        out_vrs = []
        out_names = []
        
        for v in fmu.modelDescription.modelVariables:
            if v.causality == 'output':
                out_vrs.append(v.valueReference)
                out_names.append(v.name)
        
        if out_vrs:
            res_values = fmu.getReal(out_vrs)
            for i, val in enumerate(res_values):
                outputs[out_names[i]] = val
        
        return {
            "time": fmu.time, 
            "outputs": outputs, 
            "status": "ok"
        }

    except Exception as e:
        logger.error(f"Step failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/fmus/{fmu_id}/reset")
def reset_simulation(fmu_id: str):
    """Reset the FMU."""
    return initialize_fmu(fmu_id, start_time=0.0)
