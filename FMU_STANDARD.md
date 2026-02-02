# FMU Package Standard

This document defines the standard directory structure and file formats required for FMUs to be processed by our CI/CD pipeline.

## 1. Package Structure
Every FMU release must be a **directory** or **ZIP archive** with the following strict structure:

```text
my_device_v1/
├── model.fmu             # The Co-Simulation FMU
└── tests/                # Validation Data
    ├── stimuli.csv       # Input time series
    └── reference.csv     # Expected output time series
```

> [!NOTE]
> You do **not** need to manually create `manifest.json`. The CI pipeline will automatically generate it from the `model.fmu`.

## 2. File Requirements

### 2.1 model.fmu
*   **Type**: Co-Simulation (FMI 2.0 or 3.0).
*   **Binaries**: Must contain Linux (`binaries/linux64`) binaries for cloud execution. Windows binaries are optional but recommended for local testing.

### 2.2 tests/stimuli.csv
A CSV file containing the input signals to drive the simulation.
*   **Format**: Comma-separated values.
*   **Header**: First row must be variable names in double quotes, exactly matching the FMU input variables.
*   **First Column**: Must be `"time"`.
*   **Data**: Monotonically increasing time steps.

**Example:**
```csv
"time","inputs.speed_cmd","inputs.enable"
0.0,0.0,0
0.1,10.0,1
0.5,50.0,1
1.0,0.0,0
```

### 2.3 tests/reference.csv
A CSV file containing the expected results. This is typically the output exported directly from your modeling tool (e.g., Dymola/Simulink).
*   **Header**: Variable names matching FMU outputs.
*   **Columns**: Can differ from stimuli, but must contain the key variables you want to verify.

## 3. Automated Validation Process
When this package is pushed to the cloud, the CI pipeline performs the following:

1.  **Structure Check**: Ensures `model.fmu` and `tests/` exist.
2.  **Simulation**: Runs `model.fmu` using `stimuli.csv` as input.
3.  **Regression Test**: Compares the simulation output against `reference.csv`.
    *   **Tolerance**: The build fails if results deviate by more than **1e-3** (configurable).
4.  **Metadata Extraction**: Extracts variable definitions to create `manifest.json`.
5.  **Deployment**: Publishes the package if all tests pass.
