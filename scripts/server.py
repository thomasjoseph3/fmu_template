import os
import glob
import shutil
import logging 
import yaml
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
# Key: fmu_id (filename without ext), Value: Dict containing 'instance' and 'md'
active_fmus: Dict[str, Dict[str, Any]] = {}
fmu_paths: Dict[str, str] = {}
fmu_configs: Dict[str, Dict[str, Any]] = {}  # YAML configs

class StepRequest(BaseModel):
    inputs: Optional[Dict[str, float]] = None  # Optional for parameter-only mode
    dt: float

class InitRequest(BaseModel):
    start_time: float = 0.0
    parameters: Optional[Dict[str, float]] = None

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

    files = glob.glob(os.path.join(INPUTS_DIR, "**", "*.fmu"), recursive=True)
    for f in files:
        fmu_id = os.path.splitext(os.path.basename(f))[0]
        # Check for ID collision
        if fmu_id in fmu_paths:
            logger.warning(f"Duplicate FMU ID found: {fmu_id} (Skipping {f})")
            continue
        fmu_paths[fmu_id] = f
        logger.info(f"Registered FMU: {fmu_id} -> {f}")

# Initialize on startup
load_fmu_map()

def load_configs():
    """Load YAML configuration files for each FMU."""
    for fmu_id, fmu_path in fmu_paths.items():
        # Look for {fmu_name}.yaml in the same directory
        fmu_dir = os.path.dirname(fmu_path)
        config_path = os.path.join(fmu_dir, f"{fmu_id}.yaml")
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    fmu_configs[fmu_id] = config
                    logger.info(f"Loaded config for {fmu_id}: {config.get('metadata', {}).get('name', fmu_id)}")
            except Exception as e:
                logger.error(f"Failed to load config for {fmu_id}: {e}")
        else:
            logger.info(f"No config found for {fmu_id}, using automatic detection")

load_configs()

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
    """Get variable names, descriptions, and version info."""
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
        
        # Add version info from YAML if available
        version_info = {"modelName": md.modelName, "variables": variables}
        if fmu_id in fmu_configs and 'metadata' in fmu_configs[fmu_id]:
            version_info["version"] = fmu_configs[fmu_id]['metadata'].get('version', 'N/A')
            version_info["description"] = fmu_configs[fmu_id]['metadata'].get('description', md.description)
            version_info["author"] = fmu_configs[fmu_id]['metadata'].get('author', 'N/A')
        
        return version_info
    except Exception as e:
        logger.error(f"Error reading metadata: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/fmus/{fmu_id}/manifest")
def get_manifest(fmu_id: str):
    """Get the auto-generated manifest.json for this FMU (includes all metadata)."""
    if fmu_id not in fmu_paths:
        raise HTTPException(status_code=404, detail="FMU not found")
    
    # Look for {fmu_id}_manifest.json next to the FMU
    fmu_dir = os.path.dirname(fmu_paths[fmu_id])
    manifest_path = os.path.join(fmu_dir, f"{fmu_id}_manifest.json")
    
    if not os.path.exists(manifest_path):
        raise HTTPException(
            status_code=404, 
            detail=f"Manifest not found. Run validation to generate {fmu_id}_manifest.json"
        )
    
    try:
        import json
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        return manifest
    except Exception as e:
        logger.error(f"Error reading manifest: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/fmus/{fmu_id}/initialize")
def initialize_fmu(fmu_id: str, request: InitRequest = Body(default=InitRequest())):
    """Initialize or Re-initialize the FMU simulation."""
    if fmu_id not in fmu_paths:
        raise HTTPException(status_code=404, detail="FMU not found")
    
    path = fmu_paths[fmu_id]
    start_time = request.start_time
    parameters = request.parameters
    
    # If already open, cleanup
    if fmu_id in active_fmus:
        try:
            active_fmus[fmu_id]['instance'].terminate()
            active_fmus[fmu_id]['instance'].freeInstance()
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
        
        # Validate and apply parameters if provided
        if parameters:
            md = read_model_description(path)
            vr_map = {v.name: v.valueReference for v in md.modelVariables if v.causality == 'parameter'}
            
            # Validate all parameter names first
            invalid_params = []
            for param_name in parameters.keys():
                if param_name not in vr_map:
                    invalid_params.append(param_name)
            
            if invalid_params:
                valid_params = list(vr_map.keys())
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "Invalid parameter names",
                        "invalid_parameters": invalid_params,
                        "valid_parameters": valid_params[:20] if len(valid_params) > 20 else valid_params,
                        "hint": f"Total {len(valid_params)} parameters available. Use /fmus/{fmu_id}/metadata to see all."
                    }
                )
            
            # Apply valid parameters
            param_vrs = []
            param_vals = []
            
            for param_name, param_value in parameters.items():
                param_vrs.append(vr_map[param_name])
                param_vals.append(param_value)
                logger.info(f"Setting parameter {param_name} = {param_value}")
            
            if param_vrs:
                fmu.setReal(param_vrs, param_vals)
        
        fmu.enterInitializationMode()
        fmu.exitInitializationMode()
        
        # STORE BOTH INSTANCE AND METADATA
        active_fmus[fmu_id] = {
            "instance": fmu,
            "md": md,
            "time": start_time
        }
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
    
    # UNPACK
    fmu_data = active_fmus[fmu_id]
    fmu = fmu_data['instance']
    md = fmu_data['md']
    
    try:
        # 1. Set Inputs (if provided)
        vr_map = {v.name: v.valueReference for v in md.modelVariables}
        
        if request.inputs:
            # Validate inputs against YAML config if available
            if fmu_id in fmu_configs and fmu_configs[fmu_id].get('inputs'):
                config_input_names = [inp['name'] for inp in fmu_configs[fmu_id]['inputs']]
                invalid_inputs = [name for name in request.inputs.keys() if name not in config_input_names]
                
                if invalid_inputs:
                    raise HTTPException(
                        status_code=400,
                        detail={
                            "error": "Invalid input names",
                            "invalid_inputs": invalid_inputs,
                            "valid_inputs": config_input_names,
                            "hint": f"Check YAML config for valid input names or use /fmus/{fmu_id}/metadata"
                        }
                    )
            
            vrs_to_set = []
            values_to_set = []
            
            for name, value in request.inputs.items():
                if name in vr_map:
                    vrs_to_set.append(vr_map[name])
                    values_to_set.append(value)
                    logger.debug(f"Setting input {name} = {value}")
                else:
                    logger.warning(f"Input '{name}' not found in FMU model variables")
            
            if vrs_to_set:
                fmu.setReal(vrs_to_set, values_to_set)
        else:
            logger.debug(f"No inputs provided - running in parameter-only mode")
        
        # 2. Do Step
        current_time = fmu_data['time']
        fmu.doStep(currentCommunicationPoint=current_time, communicationStepSize=request.dt)
        fmu_data['time'] += request.dt
        
        # 3. Get Outputs
        outputs = {}
        out_vrs = []
        out_names = []
        
        # PRIORITY 1: Use YAML config if available
        if fmu_id in fmu_configs and fmu_configs[fmu_id].get('outputs'):
            logger.debug(f"Using YAML config outputs for {fmu_id}")
            vr_map = {v.name: v.valueReference for v in md.modelVariables}
            
            for output_def in fmu_configs[fmu_id]['outputs']:
                var_name = output_def['name']
                if var_name in vr_map:
                    out_vrs.append(vr_map[var_name])
                    out_names.append(var_name)
                else:
                    logger.warning(f"YAML output '{var_name}' not found in FMU")
        else:
            # PRIORITY 2: Try FMI-standard outputs
            for v in md.modelVariables:
                if v.causality == 'output':
                    out_vrs.append(v.valueReference)
                    out_names.append(v.name)
            
            # PRIORITY 3: FALLBACK - If no outputs found, expose all Real variables
            if not out_vrs:
                logger.warning(f"FMU {fmu_id} has no FMI outputs. Falling back to all Real variables.")
                for v in md.modelVariables:
                    if v.type == 'Real' and v.variability != 'constant':
                        try:
                            out_vrs.append(v.valueReference)
                            out_names.append(v.name)
                        except:
                            pass  # Skip variables that can't be accessed
        
        if out_vrs:
            res_values = fmu.getReal(out_vrs)
            for i, val in enumerate(res_values):
                outputs[out_names[i]] = val
        
        return {
            "time": fmu_data['time'], 
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
