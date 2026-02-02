# FMU CI/CD Standardization Kit

This project provides a **Standardized Interface and Validation Layer** for deploying Modelica FMUs to the cloud. It ensures that every FMU is self-verification capable and automatically documented.

## 1. The Deployment Problem
Traditionally, deploying FMUs involves:
*   Emailing zip files.
*   "It works on my machine" issues.
*   Manual extraction of variable names for APIs.
*   No guarantee that the cloud simulation matches the Modelica simulation.

## 2. The Solution: "Self-Verifying Packages"
We treat FMUs like software artifacts. every FMU must come with:
1.  **The Proof**: The inputs used to test it (`stimuli.csv`).
2.  **The Promise**: The expected output (`reference.csv`).

If the cloud simulation doesn't match the "Promise" (within a tolerance), the deployment is **rejected**.

## 3. The New Standard Structure
Your FMU uploads must look like this:
```text
/inputs
  ├── my_model.fmu           # The FMU binary
  └── /tests
      ├── stimuli.csv        # Time, Input1, Input2... (The scenario)
      └── reference.csv      # Time, Output1, Output2... (The golden result)
```

## 4. How It Works (The CI Pipeline)
When you push this package, the Docker container (`fmu-validator`) performs these steps automatically:

### Step A: Regression Testing
It runs the FMU using your `stimuli.csv`.
It treats `reference.csv` as the "Truth".
*   **Deviation > 0.001?** -> **BUILD FAILED**. (Catches bugs/platform diffs).
*   **Deviation < 0.001?** -> **PASS**.

### Step B: Auto-Documentation
You no longer need to manually write API docs.
The validator reads `modelDescription.xml` inside the FMU and generates `manifest.json`:
```json
{
  "modelName": "BiomassPlant",
  "variables": [
    {"name": "inputs.valve_pos", "unit": "m", "causality": "input"},
    {"name": "outputs.temp", "unit": "K", "causality": "output"}
  ]
}
```
This file is pushed to the cloud, allowing your frontend to automatically build UI forms.

## 5. Quick Start
### Prerequisites
*   Docker Desktop installed.

### Run Verification Locally
1.  Place your `.fmu` and `tests/` folder into `inputs/`.
2.  Run:
    ```powershell
    docker build -t fmu-validator -f docker/Dockerfile .
    docker run fmu-validator
    ```
3.  Check output:
    *   ✅ **PASS**: "All Steps Passed"
    *   ❌ **FAIL**: "Variable 'x' max deviation 0.05 > 1e-3"
