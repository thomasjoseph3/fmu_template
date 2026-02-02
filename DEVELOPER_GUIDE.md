# FMU Developer Guide

This guide explains how to prepare your Modelica models for the Cloud Simulation Platform.

## 1. Exporting Your FMU
When exporting from your tool (Dymola, OpenModelica, Simulink, etc.), ensure these settings:

*   **FMI Type**: Co-Simulation (CS).
*   **FMI Version**: 2.0 or 3.0.
*   **Binaries**: You **MUST** include `linux64` binaries.
    *   *Why?* The cloud servers run Linux. Windows-only FMUs will fail.
    *   *Tip*: In Dymola, select "Binary Model Selection" -> "Linux64" (or use a Docker cross-compiler).

## 2. Creating Test Data
You must prove your model works. We use **CSV files** for this.

1.  **Stimuli (`tests/stimuli.csv`)**:
    *   The inputs you used during your design simulation.
    *   Must have a `time` column.
    *   Example: `time, inputs.speed, inputs.enable`
2.  **Reference (`tests/reference.csv`)**:
    *   The results you got from your local tool.
    *   We will compare the Cloud output against this to ensure accuracy.

## 3. Packaging
Your handover package is simply a folder structure. You do not need to write Python code.

1.  Create a folder (e.g., `MyModel_Release_v1`).
2.  Drop your `.fmu` file at the root.
3.  Create a `tests` subfolder.
4.  Drop your CSVs there.

**Final Structure:**
```text
/MyModel_Release_v1
    ├── MyModel.fmu
    └── tests/
        ├── stimuli.csv
        └── reference.csv
```

## 4. Verifying Locally
Before submitting, verify your package using our Validator Tool.

1.  **Preparation**:
    *   Open the `fmu_template/inputs/` directory in this repo.
    *   **Delete** any existing files there.
    *   **Copy** your `.fmu` file and your `tests/` folder directly into `fmu_template/inputs/`.

    *Correct Structure check:*
    ```text
    fmu_template/inputs/
    ├── MyModel.fmu
    └── tests/
        ├── stimuli.csv
        └── reference.csv
    ```
2.  **Run** the check:
    ```powershell
    # In the fmu_template directory
    docker build -t fmu-validator -f docker/Dockerfile .
    docker run fmu-validator python /app/scripts/run_tests.py
    ```

### Interpreting Functionality
*   **✅ PASSED**: You will see `All Steps Passed`. Your FMU is valid, metadata was extracted, and the server works.
*   **❌ FAILED**: Read the error log.
    *   *Simulation Failed*: Your FMU might be crashing on Linux.
    *   *Deviation > Tolerance*: The cloud results differ from your reference. Check variable units or solver settings.

## 5. Metadata (Automatic)
You do **not** need to document your variable names manually.
The system automatically generates a `manifest.json` from your FMU. Ensure you use clear, descriptive variable names in your Modelica model (e.g., `inputs.water_temperature` instead of `u1`).
