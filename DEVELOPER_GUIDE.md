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

## 6. Creating API Configuration (model.yaml)

The YAML file defines how your FMU is exposed via the REST API. **This file is optional but highly recommended.**

### 6.1 Why You Need This

Without YAML:
- ❌ Cannot set parameters via API
- ❌ API returns 100+ variables (slow, confusing)
- ❌ No documentation for API consumers

With YAML:
- ✅ Clean, curated API with only relevant variables
- ✅ Set design parameters dynamically
- ✅ Self-documenting API with labels and units

### 6.2 Quick Start

1. Create a file named `{your_fmu_name}.yaml` (e.g., if your FMU is `CounterFlowNTU.fmu`, create `CounterFlowNTU.yaml`)
2. Place it **next to your FMU** in the same directory
3. Use the template below

**Template:**
```yaml
metadata:
  name: "Your Model Name"
  version: "1.0"
  description: "Brief description"
  author: "Your name"

parameters:
  # List parameters here (if any)

inputs:
  # List runtime inputs here (if any)

outputs:
  # List the important outputs to expose
  - name: "exact.variable.name.from.fmu"
    label: "Human-Readable Name"
    description: "What this measures"
    unit: "K"
```

### 6.3 Identifying Your Variables

#### Step 1: Find Variable Names
Open your FMU in a tool like FMPy GUI or check `modelDescription.xml`:
```bash
python -c "from fmpy import read_model_description; md = read_model_description('MyModel.fmu'); print([v.name for v in md.modelVariables])"
```

#### Step 2: Classify Variables

Ask yourself: **"Can this change during runtime?"**

| Variable Type | Classification | YAML Section |
|--------------|----------------|--------------|
| Pipe diameter | ❌ Cannot change | `parameters` |
| Heater capacity | ❌ Cannot change | `parameters` |
| Inlet temperature (design) | ❌ Cannot change (parameter) | `parameters` |
| Inlet temperature (sensor) | ✅ Changes every second | `inputs` |
| Valve position | ✅ Control signal | `inputs` |
| Outlet temperature | 📊 Reading | `outputs` |

### 6.4 Example: Scenario Testing Model (Parameters Only)

If your FMU is for **design validation** (not real-time), you only have parameters:

```yaml
metadata:
  name: "Heat Exchanger Design Validator"
  version: "1.0"

parameters:
  - name: "fluid_A.T_inlet"
    label: "Hot Fluid Inlet Temp"
    description: "Design inlet temperature for hot side"
    unit: "K"
    default: 333.15
  
  - name: "fluid_B.T_inlet"
    label: "Cold Fluid Inlet Temp"
    unit: "K"
    default: 293.15

inputs: []  # No runtime inputs

outputs:
  - name: "sensor.T_out_hot"
    label: "Hot Outlet Temp"
    unit: "K"
  
  - name: "sensor.T_out_cold"
    label: "Cold Outlet Temp"
    unit: "K"
```

**Use Case:** Testing different design scenarios. API user sets temperatures once and runs simulation.

### 6.5 Example: Digital Twin (Runtime Inputs)

If your FMU will be connected to **live sensors**, you need runtime inputs:

```yaml
metadata:
  name: "Centrifugal Pump Digital Twin"
  version: "1.0"

parameters:
  - name: "pump.impeller_diameter"
    label: "Impeller Diameter"
    description: "Physical pump design parameter"
    unit: "m"
    default: 0.2

inputs:
  - name: "pump.speed_cmd"
    label: "Motor Speed Setpoint"
    description: "Live control signal from PLC"
    unit: "rpm"
  
  - name: "fluid.inlet_pressure"
    label: "Inlet Pressure Sensor"
    description: "Live sensor reading"
    unit: "Pa"

outputs:
  - name: "pump.flow_rate"
    label: "Flow Rate"
    unit: "m3/h"
  
  - name: "pump.power_consumption"
    label: "Electrical Power"
    unit: "kW"
```

**Use Case:** Real-time simulation. API user sends fresh sensor data every 100ms.

### 6.6 Critical Rule: Modelica Variables Must Match

> [!CAUTION]
> **The FMU must have actual input connectors for runtime inputs.**
> 
> ❌ **Wrong (Parameter):**
> ```modelica
> parameter Real T_inlet = 300;  // This is a constant!
> ```
> 
> ✅ **Correct (Runtime Input):**
> ```modelica
> Modelica.Blocks.Interfaces.RealInput T_inlet;  // This can change!
> ```

If you only have parameters in your FMU, do NOT list them under `inputs:` in the YAML. Use `parameters:` instead.

### 6.7 Packaging Checklist

Before submitting, verify:
- [ ] YAML filename matches FMU filename (e.g., `MyModel.fmu` → `MyModel.yaml`)
- [ ] All variable names in YAML exactly match names in FMU
- [ ] Variables are classified correctly (parameters vs inputs)
- [ ] At least 2-3 key outputs are listed (don't list all 100 variables)
- [ ] Units are specified for all variables
- [ ] YAML file is placed in the same directory as the FMU
