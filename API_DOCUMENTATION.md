# API Documentation

Base URL: `http://localhost:8000`

---

## Endpoints

### 1. Health Check

**GET** `/health`

Check if server is running.

**Response:**
```json
{
  "status": "healthy"
}
```

**Status Codes:**
- `200` - Server is healthy

---

### 2. List FMUs

**GET** `/fmus`

Get all available FMU IDs.

**Response:**
```json
["CounterFlowNTU", "CounterFlowNTU_v2", "PumpModel"]
```

**Status Codes:**
- `200` - Success

---

### 3. Get FMU Metadata

**GET** `/fmus/{fmu_id}/metadata`

Get parameters, inputs, outputs, and version info.

**Path Parameters:**
- `fmu_id` (string) - FMU identifier from `/fmus` list

**Response:**
```json
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
    {
      "name": "multiSensor_Tpm.T",
      "type": "Real",
      "causality": "output",
      "unit": "K",
      "description": "Hot outlet temperature"
    }
  ]
}
```

**Status Codes:**
- `200` - Success
- `404` - FMU not found
- `500` - Error reading FMU

---

### 4. Get FMU Manifest

**GET** `/fmus/{fmu_id}/manifest`

Get complete auto-generated manifest (includes all variables).

**Path Parameters:**
- `fmu_id` (string) - FMU identifier

**Response:**
```json
{
  "fmiVersion": "2.0",
  "modelName": "CounterFlowNTU",
  "guid": "...",
  "generationTool": "Dymola",
  "description": "...",
  "variables": [
    {
      "name": "sourceA.T0_par",
      "type": "Real",
      "causality": "parameter",
      "description": "...",
      "unit": "K"
    }
  ]
}
```

**Status Codes:**
- `200` - Success
- `404` - FMU or manifest not found (run validation first)
- `500` - Error reading manifest

---

### 5. Initialize Simulation

**POST** `/fmus/{fmu_id}/initialize`

Initialize or reset FMU simulation with parameters.

**Path Parameters:**
- `fmu_id` (string) - FMU identifier

**Request Body:**
```json
{
  "start_time": 0.0,
  "parameters": {
    "sourceA.T0_par": 360.15,
    "sourceB.T0_par": 290.15
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `start_time` | float | No | Start time (default: 0.0) |
| `parameters` | object | No | Parameter name-value pairs |

**Response:**
```json
{
  "message": "FMU CounterFlowNTU initialized",
  "start_time": 0.0
}
```

**Status Codes:**
- `200` - Successfully initialized
- `400` - Invalid parameter names (see error detail)
- `404` - FMU not found
- `500` - Initialization failed

**Error Example (Invalid Parameters):**
```json
{
  "error": "Invalid parameter names",
  "invalid_parameters": ["sourceA.T0_parr"],
  "valid_parameters": ["sourceA.T0_par", "sourceB.T0_par"],
  "hint": "Total 2 parameters available. Use /fmus/CounterFlowNTU/metadata to see all."
}
```

---

###6. Simulation Step

**POST** `/fmus/{fmu_id}/step`

Execute one simulation time step.

**Path Parameters:**
- `fmu_id` (string) - FMU identifier

**Request Body (Parameter-Only Mode):**
```json
{
  "dt": 0.1
}
```

**Request Body (Input-Based Mode):**
```json
{
  "dt": 1.0,
  "inputs": {
    "sensor_temp": 355.2,
    "flow_rate": 0.65
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `dt` | float | Yes | Time step size |
| `inputs` | object | No* | Input name-value pairs |

*Required if FMU YAML defines `inputs` with `required: true`

**Response:**
```json
{
  "time": 0.1,
  "outputs": {
    "multiSensor_Tpm.T": 340.25,
    "multiSensor_Tpm1.T": 312.50
  }
}
```

**Status Codes:**
- `200` - Success
- `400` - Invalid input names or FMU not initialized
- `404` - FMU not initialized
- `500` - Simulation step failed

**Error Example (Invalid Inputs):**
```json
{
  "error": "Invalid input names",
  "invalid_inputs": ["sensor_temp_wrong"],
  "valid_inputs": ["sensor_temp", "flow_rate"],
  "hint": "Check YAML config for valid input names or use /fmus/Model/metadata"
}
```

---

### 7. Reset Simulation

**POST** `/fmus/{fmu_id}/reset`

Reset FMU to initial state (keeps same parameters).

**Path Parameters:**
- `fmu_id` (string) - FMU identifier

**Response:**
```json
{
  "message": "FMU CounterFlowNTU reset to initial state"
}
```

**Status Codes:**
- `200` - Success
- `404` - FMU not initialized

---

## Usage Examples

### Scenario 1: Parameter Sweep (Design Study)

Test multiple design configurations:

```python
import requests

BASE_URL = "http://localhost:8000"

for temp in [340, 350, 360, 370]:
    # Initialize with this design
    requests.post(f"{BASE_URL}/fmus/HeatExchanger/initialize", json={
        "parameters": {"design_temp": temp}
    })
    
    # Run simulation
    result = requests.post(f"{BASE_URL}/fmus/HeatExchanger/step", json={
        "dt": 0.1
    })
    
    print(f"Design temp {temp}K → Output: {result.json()['outputs']}")
```

### Scenario 2: Digital Twin (Real-Time Monitoring)

Integrate with sensors:

```python
import requests
import time

BASE_URL = "http://localhost:8000"

# Initialize once
requests.post(f"{BASE_URL}/fmus/Pump/initialize", json={
    "parameters": {"rated_capacity": 100.0}
})

# Real-time loop
while True:
    sensors = read_scada()  # Your sensor reading function
    
    # Run step with live data
    result = requests.post(f"{BASE_URL}/fmus/Pump/step", json={
        "dt": 1.0,
        "inputs": {
            "speed_setpoint": sensors['vfd_speed'],
            "suction_pressure": sensors['pressure']
        }
    })
    
    predicted_flow = result.json()['outputs']['flow_rate']
    
    # Anomaly detection
    if abs(predicted_flow - sensors['actual_flow']) > 5.0:
        alert("Pump performance degraded!")
    
    time.sleep(1.0)
```

### Scenario 3: Batch Simulation

Analyze time-series data:

```python
import requests
import pandas as pd

BASE_URL = "http://localhost:8000"

# Load historical data
data = pd.read_csv("sensor_history.csv")

# Initialize
requests.post(f"{BASE_URL}/fmus/Model/initialize", json={
    "parameters": {"capacity": 1000}
})

# Simulate through history
results = []
for _, row in data.iterrows():
    resp = requests.post(f"{BASE_URL}/fmus/Model/step", json={
        "dt": 1.0,
        "inputs": {
            "temp": row['temperature'],
            "flow": row['flow_rate']
        }
    })
    results.append(resp.json()['outputs'])

# Analyze
df = pd.DataFrame(results)
df.to_csv("simulation_results.csv")
```

---

## Error Handling

All errors return JSON with `detail` field:

```json
{
  "detail": "Error message or object"
}
```

**Common Errors:**
- `404` - FMU not found or not initialized
- `400` - Invalid parameters/inputs
- `500` - Simulation failed (check FMU)

**Best Practice:**
```python
try:
    response = requests.post(url, json=data)
    response.raise_for_status()
    result = response.json()
except requests.exceptions.HTTPError as e:
    print(f"Error: {e.response.json()['detail']}")
```

---

## Rate Limits

None currently implemented.

---

## Authentication

None currently required.

---

## Versioning

API version is implicit in server deployment. No `/v1/` prefix currently.

---

## WebSocket Support

Not currently supported. Use polling via `/step` endpoint.

---

## Notes

- **State is per-FMU, not per-session** - Multiple clients share same simulation
- **Initialize resets state** - Previous simulation is lost
- **Thread safety** - Not guaranteed for concurrent requests to same FMU
- **Response times** - Typically < 100ms, depends on FMU complexity

For production multi-user scenarios, consider session-based architecture (not currently implemented).
