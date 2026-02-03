# Simulation Modes Guide

## Overview
The FMU platform supports **two distinct simulation modes**, dynamically configured via YAML:

1. **Scenario Mode** (Parameter-Based)
2. **Digital Twin Mode** (Input-Based)

---

## 🎯 Mode 1: Scenario Simulation (Parameter-Based)

### Use Case
- Design optimization
- "What-if" analysis
- Parametric studies
- Testing different configurations

### Configuration (YAML)
```yaml
metadata:
  supported_modes: ["scenario"]

parameters:
  - name: sourceA.T0_par
    tweakable: true    # Users can change this
    default: 353.15
    
inputs:  # Not used in this mode
  []
```

### API Usage
```python
# 1. Initialize with different parameters
POST /fmus/CounterFlowNTU/initialize
{
  "parameters": {
    "sourceA.T0_par": 360.15,  # Try hotter temperature
    "sourceB.T0_par": 290.15
  }
}

# 2. Run simulation (NO inputs needed!)
POST /fmus/CounterFlowNTU/step
{
  "dt": 0.1
  # NO "inputs" field - parameters drive the simulation
}

# 3. Get results
Response:
{
  "time": 0.1,
  "outputs": {
    "multiSensor_Tpm.T": 340.5,   # Outlet temp hot side
    "multiSensor_Tpm1.T": 312.3,  # Outlet temp cold side
    "hex.Q_flow": 15234.5         # Heat transfer rate
  }
}
```

### Testing (Regression)
```yaml
testing:
  mode: "parameter_based"
```

**Test behavior:**
- Stimuli.csv contains **parameter variations**
- Each row = different parameter set
- Tests: Does changing parameters produce expected outputs?

---

## 🌐 Mode 2: Digital Twin (Input-Based)

### Use Case
- Real-time prediction
- Sensor integration
- Live monitoring
- Anomaly detection

### Configuration (YAML)
```yaml
metadata:
  supported_modes: ["digital_twin"]

parameters:
  - name: hex.UA_par     # Fixed design parameters
    tweakable: false
    
inputs:  # Real-time sensor data
  - name: sourceA.T_in
    required: true       # Must provide at each step
    expected_range: [273.15, 400.0]
    
  - name: sourceB.T_in
    required: true
```

### API Usage
```python
# 1. Initialize (parameters = fixed design)
POST /fmus/CounterFlowNTU/initialize
{
  "parameters": {
    "hex.UA_par": 1000.0  # Fixed heat exchanger capacity
  }
}

# 2. Run simulation WITH live sensor data
while True:
    sensor_data = get_sensors()  # Read from real sensors
    
    POST /fmus/CounterFlowNTU/step
    {
      "dt": 1.0,
      "inputs": {
        "sourceA.T_in": sensor_data['temp_hot'],    # Live data!
        "sourceB.T_in": sensor_data['temp_cold']
      }
    }
    
    # Use outputs['multiSensor_Tpm.T'] for prediction/monitoring
```

### Testing (Regression)
```yaml
testing:
  mode: "input_based"
```

**Test behavior:**
- Stimuli.csv contains **time-series input data**
- Each row = inputs at specific time
- Tests: Does time-varying input produce expected output trajectory?

---

## 🔀 Mode 3: Hybrid (Both)

### Use Case
- Compare designs under real conditions
- "What if we used design B with today's weather?"

### Configuration
```yaml
metadata:
  supported_modes: ["scenario", "digital_twin"]

parameters:
  - name: hex.UA_par    # Tweakable design parameter
    tweakable: true
    
inputs:
  - name: sourceA.T_in  # Live sensor data
    required: false     # Optional - uses parameter if not provided
```

### API Usage
```python
# Initialize with design variant A
POST /initialize {"parameters": {"hex.UA_par": 1000}}

# Run with live data
POST /step {"dt": 1.0, "inputs": {"sourceA.T_in": 355.2}}

# Later: Try design variant B with SAME sensor data
POST /initialize {"parameters": {"hex.UA_par": 1500}}
POST /step {"dt": 1.0, "inputs": {"sourceA.T_in": 355.2}}
```

---

## 📋 YAML Configuration Reference

### Complete Example
```yaml
metadata:
  name: "Heat Exchanger Model"
  version: "1.0.0"
  tolerance: 0.001
  supported_modes: ["scenario", "digital_twin"]

# Fixed at initialization - for design exploration
parameters:
  - name: hex.UA_par
    label: "Heat Transfer Coefficient x Area"
    unit: "W/K"
    default: 1000.0
    min: 500.0
    max: 5000.0
    tweakable: true        # Show in UI, allow API changes
    description: "Overall UA value - determines heat exchanger capacity"
    
  - name: sourceA.cp_par
    label: "Hot Fluid Heat Capacity"
    unit: "J/(kg·K)"
    default: 4180.0
    tweakable: false       # Hidden - advanced only
    description: "Specific heat capacity of hot fluid"

# Change every time step - for real-time simulation
inputs:
  - name: sourceA.T_in
    label: "Hot Inlet Temperature"
    unit: "K"
    default: 353.15        # Used if not provided
    expected_range: [273.15, 400.0]
    required: false        # Can run without (uses default)
    description: "Live temperature reading from sensor A"
    
  - name: sourceA.m_flow_in
    label: "Hot Flow Rate"
    unit: "kg/s"
    default: 0.5
    expected_range: [0.0, 10.0]
    required: false

# What to return
outputs:
  - name: multiSensor_Tpm.T
    label: "Hot Outlet Temperature"
    unit: "K"
    
  - name: hex.Q_flow
    label: "Heat Transfer Rate"
    unit: "W"

# How to test
testing:
  mode: "input_based"      # or "parameter_based" or "hybrid"
  scenarios:               # Optional: pre-defined test cases
    - name: "Normal Operation"
      parameters: {"hex.UA_par": 1000}
    - name: "Oversized"
      parameters: {"hex.UA_par": 2000}
```

---

## 🎨 Dynamic Behavior

### Server automatically adapts:

**If YAML has `inputs` section:**
```python
# /step endpoint accepts inputs
# Validates input names against YAML
# Returns error if invalid input provided
```

**If YAML has NO `inputs` section:**
```python
# /step runs without inputs
# Parameters (from /initialize) drive everything
```

**If YAML has `tweakable: true`:**
```python
# Parameter shown in auto-generated UI
# Listed in /metadata endpoint
```

**If YAML has `tweakable: false`:**
```python
# Parameter hidden from basic UI
# Still settable via API (advanced users)
```

---

## 🧪 Testing Modes

### Parameter-Based Testing
```csv
# tests/stimuli.csv
heat_capacity,flow_rate
1000,0.5
1500,0.5
2000,0.5
```
Tests different design configurations.

### Input-Based Testing
```csv
# tests/stimuli.csv
time,sourceA.T_in,sourceB.T_in
0.0,353.15,293.15
0.1,355.20,294.00
0.2,357.50,295.30
```
Tests dynamic response to changing inputs.

---

## 🚀 Next Steps

1. **Update your YAML** - Add `inputs`, `tweakable`, `testing.mode`
2. **Rebuild Docker** - `make rebuild`
3. **Test scenario mode** - Initialize with parameters, step without inputs
4. **Test digital twin mode** - Initialize once, step with changing inputs

**Example workflows in next document!**
