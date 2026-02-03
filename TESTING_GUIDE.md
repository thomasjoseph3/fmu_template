# Quick Start Testing Guide

## Prerequisites Check
✅ Docker installed: `Docker version 28.5.1`
⚠️ Make not installed (optional - we'll use Docker commands first)

---

## Option 1: Test WITHOUT Make (Use This Now!)

### Step 1: Start Docker Desktop
1. Open Docker Desktop application
2. Wait for "Docker Desktop is running" notification

### Step 2: Build the Image
```powershell
cd C:\Users\tj089\OneDrive\Desktop\fmu\fmu_template
docker build -t fmu-validator -f docker/Dockerfile .
```
**Expected:** Build completes successfully (takes ~2 minutes first time)

### Step 3: Run Validation Tests
```powershell
docker run --rm fmu-validator python /app/scripts/run_tests.py
```
**Expected Output:**
```
=== Processing FMU: CounterFlowNTU ===
--- Running Regression Test ---
✅ Simulation passed
✅ Metadata extraction successful

=== Processing FMU: CounterFlowNTU_v2 ===
--- Running Regression Test ---
✅ Simulation passed
✅ Metadata extraction successful

Server Health Check: PASS
=== All Steps Passed ===
```

### Step 4: Start the Server
```powershell
docker rm -f fmu-server
docker run -d -p 8000:8000 --name fmu-server fmu-validator
```
**Expected:** Container ID returned

### Step 5: Test the API
```powershell
# Health check
curl http://localhost:8000/health

# List FMUs
curl http://localhost:8000/fmus

# Get manifest
curl http://localhost:8000/fmus/CounterFlowNTU/manifest

# Initialize simulation
curl -X POST "http://localhost:8000/fmus/CounterFlowNTU/initialize" `
  -H "Content-Type: application/json" `
  -d '{\"parameters\": {\"sourceA.T0_par\": 353.15}}'

# Run simulation step
curl -X POST "http://localhost:8000/fmus/CounterFlowNTU/step" `
  -H "Content-Type: application/json" `
  -d '{\"dt\": 0.1}'
```

### Step 6: View Server Logs
```powershell
docker logs fmu-server
```

### Step 7: Stop the Server
```powershell
docker rm -f fmu-server
```

---

## Option 2: Install Make and Use Simplified Commands

### Install Make (Pick One)

**Option A: Via Chocolatey**
```powershell
# Run PowerShell as Administrator
choco install make
```

**Option B: Via Scoop**
```powershell
scoop install make
```

**Option C: Use Git Bash**
Open Git Bash instead of PowerShell, `make` is included.

### Test Make Commands
```bash
cd /c/Users/tj089/OneDrive/Desktop/fmu/fmu_template

# View all commands
make help

# Run validation (builds image + runs tests)
make validate

# Start server (builds image + starts container)
make run-server

# Test API
make test-api

# View logs
make logs

# Stop server
make stop

# Clean everything
make clean
```

---

## Troubleshooting

### "Docker daemon not running"
→ Start Docker Desktop and wait 30 seconds

### "Port 8000 already in use"
→ `docker rm -f fmu-server` to stop existing container

### "YAML version error in requirements.txt"
→ Line 10 should be `PyYAML>=6.0` not `PyYAML>=0.23.0`

### "Make command not found"
→ Use Option 1 (direct Docker commands) or install make

---

## Quick Commands Summary

**Docker (Works Now):**
```powershell
docker build -t fmu-validator -f docker/Dockerfile .
docker run --rm fmu-validator python /app/scripts/run_tests.py
docker run -d -p 8000:8000 --name fmu-server fmu-validator
curl http://localhost:8000/health
```

**Make (After Installing):**
```bash
make validate
make run-server
make test-api
```

**Both do the same thing!** Use whichever is easier for you.
