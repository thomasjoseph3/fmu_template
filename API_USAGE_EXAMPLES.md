# API Usage Guide for CounterFlowNTU FMU
# Parameter-Only (Scenario Mode) Simulation

## Your FMU Structure

**Type:** Parameter-Based (No Runtime Inputs)

**How it works:**
- Set parameters at initialization (hot temp, cold temp)
- Run simulation steps (no inputs needed!)
- FMU internally calculates steady-state outputs

---

## 🚀 API Call Examples

### Example 1: Basic Simulation

```bash
# Step 1: Initialize with default parameters
curl -X POST "http://localhost:8000/fmus/CounterFlowNTU/initialize" \
  -H "Content-Type: application/json" \
  -d '{}'

# Response:
{
  "message": "FMU CounterFlowNTU initialized",
  "start_time": 0.0
}

# Step 2: Run simulation step (NO inputs needed!)
curl -X POST "http://localhost:8000/fmus/CounterFlowNTU/step" \
  -H "Content-Type: application/json" \
  -d '{
    "dt": 0.1
  }'

# Response:
{
  "time": 0.1,
  "outputs": {
    "multiSensor_Tpm.T": 340.25,    # Hot outlet temp
    "multiSensor_Tpm1.T": 312.50    # Cold outlet temp
  }
}
```

---

### Example 2: Custom Parameters (Design Variant)

```bash
# Initialize with DIFFERENT temperatures
curl -X POST "http://localhost:8000/fmus/CounterFlowNTU/initialize" \
  -H "Content-Type: application/json" \
  -d '{
    "parameters": {
      "sourceA.T0_par": 360.15,   # Hotter: 360K instead of 353K
      "sourceB.T0_par": 290.15    # Colder: 290K instead of 293K
    }
  }'

# Run simulation
curl -X POST "http://localhost:8000/fmus/CounterFlowNTU/step" \
  -H "Content-Type: application/json" \
  -d '{"dt": 0.1}'

# Outputs will reflect the new parameter values!
```

---

### Example 3: Parameter Sweep (Testing Multiple Designs)

```python
import requests

base_url = "http://localhost:8000"

# Test 5 different hot temperatures
results = []

for hot_temp in [340, 350, 360, 370, 380]:
    # Initialize with this temperature
    requests.post(f"{base_url}/fmus/CounterFlowNTU/initialize", json={
        "parameters": {
            "sourceA.T0_par": hot_temp,
            "sourceB.T0_par": 293.15
        }
    })
    
    # Run simulation
    response = requests.post(f"{base_url}/fmus/CounterFlowNTU/step", json={
        "dt": 0.1
    })
    
    outputs = response.json()['outputs']
    results.append({
        "input_temp": hot_temp,
        "hot_outlet": outputs['multiSensor_Tpm.T'],
        "cold_outlet": outputs['multiSensor_Tpm1.T']
    })

# Analyze results
for r in results:
    print(f"T_in={r['input_temp']}K → T_hot_out={r['hot_outlet']:.2f}K, T_cold_out={r['cold_outlet']:.2f}K")
```

---

## 📋 Available Endpoints

### 1. List FMUs
```bash
GET /fmus

Response:
["CounterFlowNTU", "CounterFlowNTU_v2"]
```

### 2. Get Metadata (See available parameters)
```bash
GET /fmus/CounterFlowNTU/metadata

Response:
{
  "modelName": "CounterFlowNTU",
  "version": "1.0.0",
  "description": "Heat exchanger model using Number of Transfer Units method",
  "author": "Thermal Systems Team",
  "variables": [
    {
      "name": "sourceA.T0_par",
      "type": "Real",
      "causality": "parameter",
      "unit": "K",
      "description": "Design temperature for hot fluid source"
    },
    ...
  ]
}
```

### 3. Initialize
```bash
POST /fmus/{fmu_id}/initialize
Body: {
  "start_time": 0.0,          # Optional, default 0.0
  "parameters": {             # Optional, uses defaults if not provided
    "sourceA.T0_par": 360.15,
    "sourceB.T0_par": 290.15
  }
}
```

### 4. Step Simulation
```bash
POST /fmus/{fmu_id}/step
Body: {
  "dt": 0.1         # Time step size
  # NO "inputs" needed for parameter-only FMU!
}
```

### 5. Reset
```bash
POST /fmus/{fmu_id}/reset

Response:
{
  "message": "FMU CounterFlowNTU reset to initial state"
}
```

---

## ⚠️ Important Notes

### What This FMU Does:
1. Takes **parameters** (hot temp, cold temp) at initialization
2. Runs steady-state calculation
3. Returns outlet temperatures

### What It Does NOT Do:
- ❌ Accept changing inputs during simulation
- ❌ Model transient dynamics
- ❌ Connect to real sensors

### To Change Operating Conditions:
Must **re-initialize** with new parameters:
```bash
# Can't do this:
POST /step {"inputs": {"T_in": 360}}  # ❌ No inputs!

# Do this instead:
POST /initialize {"parameters": {"sourceA.T0_par": 360}}  # ✅ New simulation
POST /step {"dt": 0.1}
```

---

## 🎯 Use Cases

### ✅ Good For:
- Design optimization (find best temperatures)
- Parameter sensitivity analysis
- Steady-state performance prediction
- "What-if" scenarios

### ❌ Not Good For:
- Real-time sensor integration (no inputs)
- Transient response simulation
- Time-varying conditions

---

## 🧪 Testing

**Your stimuli.csv should contain parameter values, not time-series:**

```csv
# tests/stimuli.csv - WRONG for this FMU
time,sourceA.T_in,sourceB.T_in
0.0,353.15,293.15
0.1,355.0,295.0

# tests/stimuli.csv - CORRECT (not used in current setup)
# Just stick with reference.csv for output validation
```

**Current testing uses parameters set in code, validates against reference.csv**

---

## 🔧 PowerShell Example (Windows)

```powershell
# Initialize
$response = Invoke-RestMethod -Uri "http://localhost:8000/fmus/CounterFlowNTU/initialize" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"parameters": {"sourceA.T0_par": 360.15}}'

# Run step
$output = Invoke-RestMethod -Uri "http://localhost:8000/fmus/CounterFlowNTU/step" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"dt": 0.1}'

Write-Host "Hot Outlet: $($output.outputs.'multiSensor_Tpm.T') K"
Write-Host "Cold Outlet: $($output.outputs.'multiSensor_Tpm1.T') K"
```

---

## Summary

**Your FMU:**
- ✅ Parameters: `sourceA.T0_par`, `sourceB.T0_par`
- ✅ Outputs: `multiSensor_Tpm.T`, `multiSensor_Tpm1.T`
- ❌ Inputs: None (parameter-only mode)

**API Flow:**
1. `/initialize` with parameters
2. `/step` without inputs (just `dt`)
3. Get outputs
4. Re-initialize for different parameters
