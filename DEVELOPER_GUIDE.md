# FMU Developer Guide

## Overview
This guide explains how to add your FMU to the validation and deployment template.

---

## Quick Start

### 1. Package Structure
Place your FMU in the `inputs/` directory with this structure:

```
inputs/
  └── your_model/          # Any folder name (can be version like v1, v2)
      ├── ModelName.fmu    # Your FMU file
      ├── ModelName.yaml   # Configuration (required)
      └── tests/           # Test data (required)
          ├── stimuli.csv
          └── reference.csv
```

**Example:**
```
inputs/
  ├── v1/
  │   ├── HeatExchanger.fmu
  │   ├── HeatExchanger.yaml
  │   └── tests/
  │       ├── stimuli.csv
  │       └── reference.csv
  └── v2/
      ├── HeatExchanger_v2.fmu
      ├── HeatExchanger_v2.yaml
      └── tests/...
```

---

## 2. YAML Configuration

The YAML file defines your FMU's API interface and validation behavior.

### Basic Template

```yaml
metadata:
  name: "Your Model Name"
  version: "1.0.0"
  description: "Brief description"
  author: "Your Team"
  tolerance: 0.001              # Test tolerance (optional, default: 0.001)
  supported_modes: ["scenario"] # See modes below

parameters:
  - name: param1
    label: "Parameter Label"
    description: "What this parameter does"
    unit: "K"
    default: 300.0
    min: 273.0
    max: 400.0
    tweakable: true    # Show in UI, allow via API

outputs:
  - name: output1
    label: "Output Label"
    description: "What this output represents"
    unit: "K"

testing:
  mode: "parameter_based"  # How to test this FMU
```

---

## 3. Simulation Modes

Choose the mode that matches your FMU's behavior:

### Mode 1: Scenario (Parameter-Only)

**Use when:** FMU only needs initial parameters, no runtime inputs

**YAML:**
```yaml
metadata:
  supported_modes: ["scenario"]

parameters:
  - name: design_temp
    default: 350.0
    tweakable: true

# NO inputs section!

outputs:
  - name: outlet_temp

testing:
  mode: "parameter_based"
```

**API Usage:**
```bash
POST /initialize {"parameters": {"design_temp": 360}}
POST /step {"dt": 0.1}  # No inputs needed
```

**Test Data (stimuli.csv):**
Not used - validation uses fixed parameters from code.

---

### Mode 2: Digital Twin (Input-Based)

**Use when:** FMU accepts changing sensor data at each time step

**YAML:**
```yaml
metadata:
  supported_modes: ["digital_twin"]

parameters:
  - name: heat_capacity
    default: 1000.0
    tweakable: false  # Fixed design parameter

inputs:
  - name: sensor_temp
    label: "Temperature Sensor"
    unit: "K"
    required: true      # Must provide at each step
    expected_range: [273, 400]
    
  - name: flow_rate
    label: "Flow Sensor"
    unit: "kg/s"
    required: false     # Optional - uses default
    default: 0.5

outputs:
  - name: predicted_temp

testing:
  mode: "input_based"
```

**API Usage:**
```bash
POST /initialize {"parameters": {"heat_capacity": 1000}}
POST /step {"dt": 1.0, "inputs": {"sensor_temp": 355.2, "flow_rate": 0.6}}
POST /step {"dt": 1.0, "inputs": {"sensor_temp": 358.1, "flow_rate": 0.65}}
```

**Test Data (stimuli.csv):**
```csv
time,sensor_temp,flow_rate
0.0,353.15,0.5
1.0,355.0,0.52
2.0,357.5,0.55
```

---

### Mode 3: Hybrid

**Use when:** FMU supports both parameter variations AND runtime inputs

**YAML:**
```yaml
metadata:
  supported_modes: ["scenario", "digital_twin"]

parameters:
  - name: design_capacity
    tweakable: true

inputs:
  - name: sensor_reading
    required: false  # Can run without inputs

outputs:
  - name: result
```

**API Usage:**
```bash
# As scenario: vary parameters, no inputs
POST /initialize {"parameters": {"design_capacity": 1000}}
POST /step {"dt": 0.1}

# As digital twin: fixed parameter, varying inputs
POST /initialize {"parameters": {"design_capacity": 1000}}
POST /step {"dt": 1.0, "inputs": {"sensor_reading": 355}}
```

---

## 4. YAML Field Reference

### metadata

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Display name |
| `version` | Yes | Semantic version (e.g., "1.0.0") |
| `description` | Yes | Brief description |
| `author` | No | Team/person name |
| `tolerance` | No | Test tolerance (default: 0.001) |
| `supported_modes` | Yes | `["scenario"]`, `["digital_twin"]`, or both |

### parameters

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Exact FMU parameter name |
| `label` | Yes | Human-readable name |
| `description` | Yes | What it does |
| `unit` | No | Physical unit |
| `default` | Yes | Default value |
| `min` | No | Minimum allowed value |
| `max` | No | Maximum allowed value |
| `tweakable` | Yes | `true`: show in UI, `false`: advanced only |

### inputs (Digital Twin mode only)

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Exact FMU input name |
| `label` | Yes | Human-readable name |
| `description` | Yes | What it represents |
| `unit` | No | Physical unit |
| `required` | Yes | `true`: must provide, `false`: optional |
| `default` | If !required | Default if not provided |
| `expected_range` | No | `[min, max]` for validation |

### outputs

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Exact FMU output name |
| `label` | Yes | Human-readable name |
| `description` | Yes | What it represents |
| `unit` | No | Physical unit |

### testing

| Field | Required | Description |
|-------|----------|-------------|
| `mode` | Yes | `"parameter_based"` or `"input_based"` |

---

## 5. Test Data

### reference.csv (Always Required)

Contains expected output values for validation.

**Format:**
```csv
time,output1,output2,...
0.0,340.5,1500.2
0.1,342.1,1520.5
```

- First column: `time`
- Other columns: Must match `outputs` names in YAML
- Values: Expected simulation results

### stimuli.csv (Mode-Dependent)

**For input_based mode:**
```csv
time,input1,input2,...
0.0,353.15,0.5
1.0,355.0,0.52
```
- First column: `time`
- Other columns: Must match `inputs` names in YAML
- Values: Input time series

**For parameter_based mode:**
Not used directly - validation uses parameters from code.

---

## 6. Finding FMU Variable Names

Your FMU contains a `modelDescription.xml` file with all variable names.

**Option 1: Extract and inspect**
```bash
unzip YourModel.fmu
cat modelDescription.xml
```

**Option 2: Use validation (will generate manifest)**
```bash
make validate
# Creates YourModel_manifest.json with all variables
```

**Option 3: Use API (after adding FMU)**
```bash
GET /fmus/YourModel/metadata
# Returns all parameters, inputs, outputs
```

---

## 7. Workflow

1. **Export FMU** from your modeling tool (Modelica, Simulink, etc.)
   - Must include Linux64 binaries
   - FMI 2.0 Co-Simulation

2. **Create folder** in `inputs/`
   ```bash
   mkdir inputs/my_model
   ```

3. **Copy FMU**
   ```bash
   cp MyModel.fmu inputs/my_model/
   ```

4. **Create YAML**
   ```bash
   # Use one of the mode templates above
   nano inputs/my_model/MyModel.yaml
   ```

5. **Create test data**
   ```bash
   mkdir inputs/my_model/tests
   # Create stimuli.csv and reference.csv
   ```

6. **Validate**
   ```bash
   make validate
   # or
   make setup && source venv/bin/activate && python scripts/run_tests.py
   ```

7. **If validation passes:**
   - FMU is ready!
   - Commit to Git
   - CI/CD will auto-deploy

---

## 8. Common Issues

### "Parameter X not found"
- Check exact spelling in YAML vs FMU
- Use `GET /fmus/Model/manifest` to see available names

### "Validation fails with large deviation"
- Adjust `tolerance` in YAML metadata
- Check if reference.csv values are correct

### "Input X not found"
- Ensure input exists in FMU
- Check causality is 'input' not 'parameter'

### "No FMUs discovered"
- YAML filename must match FMU filename
- FMU must be in `inputs/**/*.fmu`

---

## 9. Best Practices

✅ **Use semantic versioning** (1.0.0, 1.1.0, 2.0.0)  
✅ **Set realistic tolerances** (0.001 for steady-state, 0.01 for transient)  
✅ **Mark tweakable=false** for advanced parameters  
✅ **Provide meaningful descriptions** for auto-generated docs  
✅ **Test with representative data** matching real operating conditions  
✅ **Use v1/, v2/ folders** to maintain multiple versions  

---

## 10. Example: Complete Package

```
inputs/v1/
├── PumpModel.fmu
├── PumpModel.yaml
└── tests/
    ├── stimuli.csv
    └── reference.csv
```

**PumpModel.yaml:**
```yaml
metadata:
  name: "Centrifugal Pump Model"
  version: "1.0.0"
  description: "Variable speed pump with efficiency curve"
  tolerance: 0.002
  supported_modes: ["digital_twin"]

parameters:
  - name: pump.rated_capacity
    label: "Rated Capacity"
    unit: "m³/h"
    default: 100.0
    tweakable: false

  - name: pump.rated_head
    label: "Rated Head"
    unit: "m"
    default: 50.0
    tweakable: true

inputs:
  - name: speed_setpoint
    label: "Speed Command"
    description: "From VFD controller"
    unit: "RPM"
    required: true
    expected_range: [0, 3600]

  - name: suction_pressure
    label: "Suction Pressure"
    description: "From pressure sensor"
    unit: "bar"
    required: false
    default: 1.0

outputs:
  - name: flow_rate
    label: "Flow Rate"
    unit: "m³/h"

  - name: power_consumption
    label: "Power"
    unit: "kW"

testing:
  mode: "input_based"
```

**tests/stimuli.csv:**
```csv
time,speed_setpoint,suction_pressure
0.0,1000,1.0
1.0,1500,1.05
2.0,2000,1.1
```

**tests/reference.csv:**
```csv
time,flow_rate,power_consumption
0.0,33.5,2.1
1.0,50.2,4.5
2.0,67.0,8.2
```

---

## Need Help?

- Check [API_DOCUMENTATION.md](API_DOCUMENTATION.md) for endpoint details
- See [SETUP_AND_USAGE.md](SETUP_AND_USAGE.md) for testing commands
- Review existing examples in `inputs/v1/` and `inputs/v2/`
