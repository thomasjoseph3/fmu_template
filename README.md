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
  └── /tests
      ├── stimuli.csv        # Time, Input1, Input2... (The scenario)
      └── reference.csv      # Time, Output1, Output2... (The golden result)
```

### Managing Multiple Models
You can organize multiple versions or different models using **subfolders**. The system is recursive.

**Recommended Structure for Versioning:**
```text
/inputs
  ├── v1/
  │   ├── HeatExchanger.fmu       # ID: HeatExchanger (Note: rename if needed)
  │   └── tests/                  # Tests for v1
  │       ├── stimuli.csv
  │       └── reference.csv
  │
  ├── v2/
  │   ├── HeatExchanger_v2.fmu    # ID: HeatExchanger_v2
  │   └── tests/                  # Tests for v2 (Different CSVs!)
  │       ├── stimuli.csv
  │       └── reference.csv
```

*   **Validation**: The system will find *each* FMU and look for its *local* `tests/` folder.
*   **Runtime**: All FMUs are loaded. `v1` and `v2` are strictly separated by their filename ID.

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
*   Docker Desktop installed
*   Make (included on Linux/Mac, install via Chocolatey on Windows: `choco install make`)

### Quick Commands (Recommended)

**Validate FMUs (Run Tests):**
```bash
make validate
```

**Start API Server:**
```bash
make run-server
```

**Test API Endpoints:**
```bash
make test-api
```

**View All Commands:**
```bash
make help
```

### Alternative: Direct Docker Commands

If you don't have `make`, use these commands:

**1. Run Verification (Batch Mode):**
```powershell
docker build -t fmu-validator -f docker/Dockerfile .
docker run fmu-validator python /app/scripts/run_tests.py
```

**2. Run Server (Interactive Mode):**
```powershell
docker run -p 8000:8000 fmu-validator
```
## 5. Runtime Mode (FastAPI Server)
This template is **Dual-Purpose**.
1.  **CI/CD**: Runs `run_tests.py` to validate the FMU.
2.  **Runtime**: Runs `server.py` to expose a REST API for controlling the simulation.

When you deploy this image to Cloud Run or Kubernetes, it automatically starts the Server.

### API Endpoints

The server exposes a REST API for real-time simulation control.

#### 1. Health Check
```bash
GET /health
```
**Response:**
```json
{
  "status": "ok",
  "fmus_loaded": ["CounterFlowNTU", "CounterFlowNTU_v2"]
}
```

#### 2. List Available FMUs
```bash
GET /fmus
```
**Response:**
```json
["CounterFlowNTU", "CounterFlowNTU_v2"]
```

#### 3. Get FMU Metadata
```bash
GET /fmus/{fmu_id}/metadata
```
**Response:**
```json
{
  "modelName": "CounterFlowNTU",
  "variables": [
    {
      "name": "sourceA.T0_par",
      "type": "Real",
      "causality": "parameter",
      "unit": "K",
      "description": "Hot fluid inlet temperature"
    }
  ]
}
```

#### 4. Get Complete Manifest
```bash
GET /fmus/{fmu_id}/manifest
```
**Response:** (Auto-generated during validation)
```json
{
  "fmiVersion": "2.0",
  "modelName": "CounterFlowNTU",
  "guid": "...",
  "generationTool": "Dymola Version 2023x",
  "description": "Counter flow heat exchanger model",
  "variables": [
    {
      "name": "sourceA.T0_par",
      "type": "Real",
      "causality": "parameter",
      "unit": "K",
      "description": "Hot fluid inlet temperature"
    }
  ]
}
```

#### 5. Initialize Simulation
```bash
POST /fmus/{fmu_id}/initialize
Content-Type: application/json

{
  "start_time": 0.0,
  "parameters": {
    "sourceA.T0_par": 353.15,
    "sourceB.T0_par": 288.15
  }
}
```
**Response:**
```json
{
  "status": "initialized",
  "time": 0.0
}
```

#### 5. Step Simulation
```bash
POST /fmus/{fmu_id}/step
Content-Type: application/json

{
  "inputs": {
    "valve.position": 0.8
  },
  "dt": 0.1
}
```
**Response:**
```json
{
  "time": 0.1,
  "outputs": {
    "multiSensor_Tpm.T": 80.0,
    "multiSensor_Tpm1.T": 56.94,
    "multiSensor_Tpm2.T": 45.31,
    "multiSensor_Tpm3.T": 15.0
  },
  "status": "ok"
}
```

#### 6. Reset Simulation
```bash
POST /fmus/{fmu_id}/reset
```

### Example Workflow

**Scenario Testing (Parameters):**
```bash
# 1. Initialize with custom design parameters
curl -X POST "http://localhost:8000/fmus/HeatExchanger/initialize" \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"sourceA.T0_par": 353.15}}'

# 2. Run simulation (no runtime inputs needed)
curl -X POST "http://localhost:8000/fmus/HeatExchanger/step" \
  -H "Content-Type: application/json" \
  -d '{"dt": 0.1}'
```

**Digital Twin (Runtime Inputs):**
```bash
# 1. Initialize with fixed design parameters
curl -X POST "http://localhost:8000/fmus/Pump/initialize" \
  -d '{"parameters": {"pump.diameter": 0.2}}'

# 2. Send live sensor data every second
while true; do
  curl -X POST "http://localhost:8000/fmus/Pump/step" \
    -d '{"inputs": {"speed_cmd": 1450}, "dt": 1.0}'
  sleep 1
done
```

## 6. Documentation Files

- **[FMU_STANDARD.md](FMU_STANDARD.md)** - Package structure specification and YAML schema
- **[DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)** - Complete guide for FMU developers
- **[SYSTEM_OVERVIEW.md](SYSTEM_OVERVIEW.md)** - High-level overview and developer onboarding

## 7. CI/CD Integration

The Makefile makes integration trivial in any CI/CD platform:

### GitHub Actions
```yaml
name: FMU Validation
on: [push]
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Validate FMUs
        run: make validate
```

### GitLab CI
```yaml
validate:
  image: docker:latest
  services:
    - docker:dind
  script:
    - make validate
```

### Jenkins
```groovy
stage('Validate') {
  steps {
    sh 'make validate'
  }
}
```

### Azure Pipelines
```yaml
- task: Bash@3
  inputs:
    targetType: 'inline'
    script: 'make validate'
```

## 8. Cloud Deployment

To deploy to Google Cloud Run:
```bash
gcloud builds submit --config cloudbuild.yaml
```

The server automatically starts on port 8000 and is ready for traffic.
*   `GET /fmus`: List available models.
*   `GET /fmus/{id}/metadata`: Get variables and units.
*   `POST /fmus/{id}/initialize`: Start/Restart simulation.
*   `POST /fmus/{id}/step`: Advance simulation.
    *   **Body**: `{"inputs": {"valve": 0.5}, "dt": 0.1}`
    *   **Response**: `{"time": 0.1, "outputs": {"temp": 300.1}}`

### Example Usage (CURL)
You can test the API from your terminal:

**1. Initialize**
```bash
curl -X POST "http://localhost:8000/fmus/CounterFlowNTU/initialize"
```

**2. Step**
```bash
curl -X POST "http://localhost:8000/fmus/CounterFlowNTU/step" \
     -H "Content-Type: application/json" \
     -d '{"inputs": {"inputs.water_inlet_temp": 300.0}, "dt": 0.1}'
```

## 7. Scalability & Architecture
Is this scalable? **Yes, but with vertical limits.**

*   **Architecture**: Stateful Container.
    *   The server holds the FMU in RAM.
    *   This is "Vertical Scaling" (one container = many FMUs).
*   **Limits**:
    1.  **Memory**: FMUs are heavy. 100 loaded FMUs might consume 2-4GB RAM.
    2.  **CPU**: Simulation steps block the CPU. Python's GIL means this server processes steps **sequentially** (one by one), not in parallel.
*   **Scaling Strategy**:
    *   To handle 1000 users, you deploy **multiple containers** (Horizontal Scaling) behind a Load Balancer ensuring "Sticky Sessions" (so User A always talks to Container 1 where their simulation lives).
