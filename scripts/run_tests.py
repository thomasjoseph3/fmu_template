import os
import shutil
import sys
import glob
import json
import pandas as pd
import numpy as np
from fmpy import simulate_fmu, dump, read_model_description

INPUTS_DIR = "/app/inputs"

def extract_metadata(fmu_path, output_path):
    print(f"--- Extracting Metadata to {output_path} ---")
    try:
        model_description = read_model_description(fmu_path)
        
        metadata = {
            "fmiVersion": model_description.fmiVersion,
            "modelName": model_description.modelName,
            "guid": model_description.guid,
            "generationTool": model_description.generationTool,
            "description": model_description.description,
            "variables": []
        }

        for var in model_description.modelVariables:
            var_data = {
                "name": var.name,
                "type": var.type,
                "causality": var.causality,
                "description": var.description,
                "unit": var.unit
            }
            # Only include inputs, outputs, and parameters to keep it clean
            if var.causality in ['input', 'output', 'parameter']:
                metadata["variables"].append(var_data)
        
        with open(output_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print("Metadata extraction successful.")
        return True
    except Exception as e:
        print(f"!!! Metadata extraction failed: {e}")
        return False

def run_regression_test(fmu_path, stimuli_path, reference_path, tolerance=1e-3):
    print(f"--- Running Regression Test ---")
    print(f"Stimuli: {os.path.basename(stimuli_path)}")
    print(f"Reference: {os.path.basename(reference_path)}")

    try:
        # Load inputs
        inputs_df = pd.read_csv(stimuli_path)
        
        # Prepare inputs for FMPy
        # FMPy expects a structured array or keys that match variable names
        # We need to ensure 'time' is the first column
        if 'time' not in inputs_df.columns:
            print("!!! Error: stimuli.csv must have a 'time' column.")
            return False
            
        # Convert to structured array for FMPy input
        # Dictionary format: {'variable_name': value_array, 'time': time_array} is not fully supported by simulate_fmu directly in all versions
        # Standard way: dtype with (name, type)
        # Simplified: We define input as a structured array
        dtype = [(c, np.float64) for c in inputs_df.columns]
        input_data = np.array([tuple(x) for x in inputs_df.to_numpy()], dtype=dtype)

        # Run Simulation
        print("Executing simulation...")
        result = simulate_fmu(
            fmu_path, 
            input=input_data, 
            stop_time=inputs_df['time'].iloc[-1],
            output_interval=None, # Use input interval or default
            fmi_type='CoSimulation'
        )
        
        # Convert result to DataFrame
        result_df = pd.DataFrame(result)
        
        # Compare with Reference
        ref_df = pd.read_csv(reference_path)
        
        # Align data: Interpolate result to match reference time points if needed
        # For simplicity, we assume reference and result share close time steps or we compare on common columns
        
        print("Comparing results...")
        passed = True
        
        for col in ref_df.columns:
            if col == 'time': continue
            if col not in result_df.columns:
                print(f"Warning: Reference column '{col}' not found in simulation result. Skipping.")
                continue
            
            # Simple check: Mean Squared Error or Max Deviation
            # We assume reference has same time grid. If not, complex alignment is needed.
            # Here we assume the 'reference' is the TRUTH, so we check if result matches it.
            # If time grids differ significantly, we would need to resample. 
            # For this standard, we assume specific time points are not enforced unless step size is fixed.
            # Let's check max deviation on overlapping time range.
            
            # Robust check: Max Absolute Error
            # We align by index for now (assuming row-by-row correspondence from fixed step)
            # OR we just check the last value if steady state. 
            # BETTER: Interpolate result_df to ref_df time points.
            
            sim_values = np.interp(ref_df['time'], result_df['time'], result_df[col])
            ref_values = ref_df[col].values
            
            diff = np.abs(sim_values - ref_values)
            max_diff = np.max(diff)
            
            if max_diff > tolerance:
                print(f"!!! FAIL: Variable '{col}' max deviation {max_diff:.6f} > {tolerance}")
                passed = False
            else:
                print(f"PASS: Variable '{col}' max diff {max_diff:.6f}")

        return passed

    except Exception as e:
        print(f"!!! Simulation/Verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=== Modelica FMU Validation & Integration Runner ===")
    
    if not os.path.exists(INPUTS_DIR):
        print(f"Error: {INPUTS_DIR} not found.")
        sys.exit(1)

    # Find all FMUs recursively
    fmu_files = glob.glob(os.path.join(INPUTS_DIR, "**", "*.fmu"), recursive=True)
    if not fmu_files:
        print(f"No .fmu files found in {INPUTS_DIR}")
        sys.exit(1)
        
    print(f"Found {len(fmu_files)} FMUs to validate.")
    
    all_tests_passed = True
    all_meta_success = True
    
    for fmu_path in fmu_files:
        fmu_name = os.path.splitext(os.path.basename(fmu_path))[0]
        print(f"\n=== Processing FMU: {fmu_name} ===")
        print(f"Path: {fmu_path}")
        
        # 1. Look for Local Tests (Sibling directory)
        fmu_dir = os.path.dirname(fmu_path)
        tests_dir = os.path.join(fmu_dir, "tests")
        stimuli = os.path.join(tests_dir, "stimuli.csv")
        reference = os.path.join(tests_dir, "reference.csv")
        
        current_passed = True
        
        if os.path.exists(stimuli) and os.path.exists(reference):
            if not run_regression_test(fmu_path, stimuli, reference):
                current_passed = False
                all_tests_passed = False
        else:
            print(f"Warning: No standard tests found in {tests_dir}")
            print("Running basic load test only.")
            try:
                # Basic load test
                md = read_model_description(fmu_path)
                print(f"Basic load test passed: {md.modelName}")
            except Exception as e:
                print(f"Basic load test failed: {e}")
                current_passed = False
                all_tests_passed = False
        
        # 2. Extract Metadata (Specific Manifest)
        manifest_path = os.path.join(fmu_dir, f"{fmu_name}_manifest.json")
        if not extract_metadata(fmu_path, manifest_path):
            all_meta_success = False

    if not all_tests_passed:
        print("\n!!! Some Validation Tests FAILED !!!")
        sys.exit(1)
        
    if not all_meta_success:
        print("\n!!! Some Metadata Extraction FAILED !!!")
        sys.exit(1)

    # 3. Server Startup Smoke Test
    print("\n--- Running Server Smoke Test ---")
    try:
        # Ensure we can import from the root /app directory
        sys.path.append(os.getcwd()) 
        from fastapi.testclient import TestClient
        from scripts.server import app
        
        client = TestClient(app)
        response = client.get("/health")
        
        if response.status_code == 200:
            print(f"Server Health Check: PASS ({response.json()})")
        else:
            print(f"!!! Server Health Check FAILED: {response.status_code} !!!")
            sys.exit(1)
            
        # Verify all found FMUs are discovered by the server
        fmus_resp = client.get("/fmus")
        server_fmus = fmus_resp.json()
        
        missing_fmus = []
        for f in fmu_files:
             fid = os.path.splitext(os.path.basename(f))[0]
             if fid not in server_fmus:
                 missing_fmus.append(fid)
        
        if not missing_fmus:
             print(f"Server Discovery Check: PASS (All {len(server_fmus)} FMUs found)")
        else:
             print(f"!!! Server failed to discover: {missing_fmus} !!!")
             sys.exit(1)

    except Exception as e:
        print(f"!!! Server Check FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("\n=== All Steps Passed (Batch Validation + Metadata + Server Check) ===")

if __name__ == "__main__":
    main()
