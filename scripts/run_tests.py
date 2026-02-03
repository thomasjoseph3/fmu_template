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
    print(f"FMU: {os.path.basename(fmu_path)}")
    print(f"Stimuli: {os.path.basename(stimuli_path)}")
    print(f"Reference: {os.path.basename(reference_path)}")
    print(f"Tolerance: {tolerance}")

    try:
        # Validate and load stimuli
        try:
            inputs_df = pd.read_csv(stimuli_path)
        except FileNotFoundError:
            print(f"❌ ERROR: Stimuli file not found: {stimuli_path}")
            return False
        except pd.errors.EmptyDataError:
            print(f"❌ ERROR: Stimuli file is empty: {stimuli_path}")
            return False
        except Exception as e:
            print(f"❌ ERROR: Failed to parse stimuli CSV: {e}")
            return False
        
        # Validate 'time' column
        if 'time' not in inputs_df.columns:
            print(f"❌ ERROR: stimuli.csv must have a 'time' column")
            print(f"   Found columns: {list(inputs_df.columns)}")
            return False
        
        # Check for NaN values
        if inputs_df.isnull().any().any():
            print(f"❌ ERROR: stimuli.csv contains NaN values")
            nan_cols = inputs_df.columns[inputs_df.isnull().any()].tolist()
            print(f"   Columns with NaN: {nan_cols}")
            return False
            
        # Convert to structured array for FMPy
        dtype = [(c, np.float64) for c in inputs_df.columns]
        input_data = np.array([tuple(x) for x in inputs_df.to_numpy()], dtype=dtype)

        # Run Simulation
        print("Executing simulation...")
        try:
            result = simulate_fmu(
                fmu_path, 
                input=input_data, 
                stop_time=inputs_df['time'].iloc[-1],
                output_interval=None,
                fmi_type='CoSimulation'
            )
        except Exception as e:
            print(f"❌ ERROR: Simulation failed: {e}")
            return False
        
        # Convert result to DataFrame
        result_df = pd.DataFrame(result)
        
        # Validate and load reference
        try:
            ref_df = pd.read_csv(reference_path)
        except FileNotFoundError:
            print(f"❌ ERROR: Reference file not found: {reference_path}")
            return False
        except pd.errors.EmptyDataError:
            print(f"❌ ERROR: Reference file is empty: {reference_path}")
            return False
        except Exception as e:
            print(f"❌ ERROR: Failed to parse reference CSV: {e}")
            return False
        
        # Validate reference has required columns
        if 'time' not in ref_df.columns:
            print(f"❌ ERROR: reference.csv must have a 'time' column")
            print(f"   Found columns: {list(ref_df.columns)}")
            return False
        
        print("Comparing results...")
        passed = True
        deviations = []
        
        for col in ref_df.columns:
            if col == 'time': 
                continue
            
            if col not in result_df.columns:
                print(f"⚠️  WARNING: Reference column '{col}' not found in simulation result. Skipping.")
                continue
            
            # Calculate max deviation
            ref_val = ref_df[col].values
            sim_val = result_df[col].values[:len(ref_val)]  # Match lengths
            
            max_dev = np.max(np.abs(ref_val - sim_val))
            deviations.append((col, max_dev))
            
            if max_dev > tolerance:
                passed = False
                print(f"❌ FAIL: '{col}' deviation {max_dev:.6f} exceeds tolerance {tolerance}")
                # Show where the max deviation occurred
                max_idx = np.argmax(np.abs(ref_val - sim_val))
                print(f"   At time={ref_df['time'].iloc[max_idx]:.3f}: expected={ref_val[max_idx]:.6f}, got={sim_val[max_idx]:.6f}")
            else:
                print(f"✅ PASS: '{col}' max deviation {max_dev:.6f}")
        
        if passed:
            print(f"✅ Regression test PASSED")
        else:
            print(f"❌ Regression test FAILED")
        
        return passed
        
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {e}")
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
        
        # 1. Look for YAML config (for tolerance and version info)
        yaml_path = os.path.join(fmu_dir, f"{fmu_name}.yaml")
        tolerance = 1e-3  # Default
        version_info = "N/A"
        
        if os.path.exists(yaml_path):
            try:
                import yaml
                with open(yaml_path, 'r') as f:
                    config = yaml.safe_load(f)
                    if config and 'metadata' in config:
                        tolerance = config['metadata'].get('tolerance', 1e-3)
                        version_info = config['metadata'].get('version', 'N/A')
                        print(f"Version: {version_info}")
                        print(f"Custom tolerance: {tolerance}")
            except Exception as e:
                print(f"Warning: Failed to load YAML config: {e}")
        
        # 2. Look for Local Tests (Sibling directory)
        fmu_dir = os.path.dirname(fmu_path)
        tests_dir = os.path.join(fmu_dir, "tests")
        stimuli = os.path.join(tests_dir, "stimuli.csv")
        reference = os.path.join(tests_dir, "reference.csv")
        
        current_passed = True
        
        if os.path.exists(stimuli) and os.path.exists(reference):
            if not run_regression_test(fmu_path, stimuli, reference, tolerance=tolerance):
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
