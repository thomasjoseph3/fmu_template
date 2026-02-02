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
*   Docker Desktop installed.

### 1. Run Verification (Batch Mode)
    Use this to test if your FMU is valid.
    ```powershell
    docker build -t fmu-validator -f docker/Dockerfile .
    docker run fmu-validator python /app/scripts/run_tests.py
    ```

### 2. Run Server (Interactive Mode)
    Use this to start the API and control the simulation.
    ```powershell
    docker run -p 8000:8000 fmu-validator
    ```
## 5. Runtime Mode (FastAPI Server)
This template is **Dual-Purpose**.
1.  **CI/CD**: Runs `run_tests.py` to validate the FMU.
2.  **Runtime**: Runs `server.py` to expose a REST API for controlling the simulation.

When you deploy this image to Cloud Run or Kubernetes, it automatically starts the Server.

### API Endpoints
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
