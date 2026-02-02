import os
import shutil
import sys
import glob
import json
import pandas as pd
import numpy as np
from fmpy import simulate_fmu, dump, read_model_description

INPUTS_DIR = "/app/inputs"
MANIFEST_FILE = "/app/inputs/manifest.json"

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

    fmu_files = glob.glob(os.path.join(INPUTS_DIR, "*.fmu"))
    if not fmu_files:
        print(f"No .fmu files found in {INPUTS_DIR}")
        sys.exit(1)
        
    fmu_path = fmu_files[0] # Assume standardized package has one FMU
    print(f"Found FMU: {fmu_path}")

    # 1. Look for Standard Tests
    tests_dir = os.path.join(INPUTS_DIR, "tests")
    stimuli = os.path.join(tests_dir, "stimuli.csv")
    reference = os.path.join(tests_dir, "reference.csv")

    tests_passed = True
    
    if os.path.exists(stimuli) and os.path.exists(reference):
        tests_passed = run_regression_test(fmu_path, stimuli, reference)
    else:
        print("Warning: Standard 'tests/stimuli.csv' and 'tests/reference.csv' not found.")
        print("Skipping regression test. Basic load test only.")
        try:
            dump(fmu_path)
            print("Basic load test passed.")
        except Exception as e:
            print(f"Basic load test failed: {e}")
            tests_passed = False

    # 2. Extract Metadata (Manifest)
    meta_success = extract_metadata(fmu_path, MANIFEST_FILE)

    if not tests_passed:
        print("!!! Validation FAILED !!!")
        sys.exit(1)
        
    if not meta_success:
        print("!!! Metadata Extraction FAILED !!!")
        sys.exit(1)

    print("=== All Steps Passed (Validation + Documentation) ===")

if __name__ == "__main__":
    main()
