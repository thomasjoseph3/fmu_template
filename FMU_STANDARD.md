# FMU Package Standard

This document defines the standard directory structure and file formats required for FMUs to be processed by our CI/CD pipeline.

## 1. Package Structure
Every FMU release must be a **directory** or **ZIP archive** with the following structure:

```text
my_device_v1/
├── model.fmu             # The Co-Simulation FMU
├── model.yaml            # API Configuration (Optional but Recommended)
└── tests/                # Validation Data
    ├── stimuli.csv       # Input time series
    └── reference.csv     # Expected output time series
```

> [!NOTE]
> You do **not** need to manually create `manifest.json`. The CI pipeline will automatically generate it from the `model.fmu`.

> [!TIP]
> Including a `model.yaml` file enables optimized API performance and provides better documentation for API consumers.

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

## 4. API Configuration (model.yaml)

The YAML configuration file defines which variables are exposed via the REST API and provides metadata for consumers.

### 4.1 Schema

```yaml
metadata:
  name: "Human-Readable Model Name"
  version: "1.0"
  description: "Brief description of the model"
  author: "Your Name / Team"

# Parameters: Set once during initialization
parameters:
  - name: "variable.name.in.fmu"      # Exact FMU variable name
    label: "Human-Readable Label"
    description: "What this parameter controls"
    unit: "K"                         # SI unit
    default: 333.15                   # Default value
    min: 273.15                       # Optional: Minimum value
    max: 373.15                       # Optional: Maximum value

# Runtime Inputs: Changed at every simulation step
inputs:
  - name: "input.variable.name"
    label: "Sensor Name"
    description: "Live sensor data"
    unit: "m/s"

# Outputs: Values returned from each step
outputs:
  - name: "output.variable.name"
    label: "Measurement Name"
    description: "What this output represents"
    unit: "W"
```

### 4.2 Parameters vs Inputs

| Feature | **Parameters** | **Runtime Inputs** |
|---------|---------------|-------------------|
| When set | Once at `/initialize` | Every `/step` |
| Use case | Design constants (pipe diameter, heater capacity) | Live sensor data, control signals |
| Example | `heater_power_max = 100kW` | `heater_power_current = 85kW` |
| Digital Twin | ❌ Static simulation only | ✅ Reacts to real-world data |

### 4.3 Example: Heat Exchanger with Parameters

```yaml
metadata:
  name: "Counter Flow Heat Exchanger"
  version: "1.0"

parameters:
  - name: "sourceA.T0_par"
    label: "Hot Fluid Inlet Temp"
    unit: "K"
    default: 333.15

inputs: []  # No runtime inputs

outputs:
  - name: "sensor.T_out"
    label: "Outlet Temperature"
    unit: "K"
```

**API Usage:**
```bash
# Set parameters once
curl -X POST "http://server/fmus/HeatExchanger/initialize" \
  -d '{"parameters": {"sourceA.T0_par": 353.15}}'

# Step simulation (no inputs)
curl -X POST "http://server/fmus/HeatExchanger/step" \
  -d '{"dt": 0.1}'
```

### 4.4 Example: Pump with Runtime Inputs (Digital Twin)

```yaml
metadata:
  name: "Centrifugal Pump"

parameters:
  - name: "pump.diameter"
    label: "Impeller Diameter"
    unit: "m"
    default: 0.2

inputs:
  - name: "pump.speed_setpoint"
    label: "Motor Speed Command"
    unit: "rpm"

outputs:
  - name: "pump.flow_rate"
    label: "Flow Rate"
    unit: "m3/s"
```

**API Usage:**
```bash
# Initialize with design parameters
curl -X POST ".../initialize" -d '{"parameters": {"pump.diameter": 0.25}}'

# Send live sensor data every second
curl -X POST ".../step" -d '{"inputs": {"pump.speed_setpoint": 1450}, "dt": 1.0}'
```

### 4.5 Fallback Behavior

If no YAML file is provided:
- **Parameters**: Cannot be set via API (FMU uses defaults)
- **Outputs**: Server returns all Real-type variables (inefficient, returns 100+ variables)
