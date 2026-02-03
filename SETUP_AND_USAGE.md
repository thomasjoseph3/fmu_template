# Setup and Usage Guide

## Prerequisites

- **Docker Desktop** (Windows/Mac) or **Docker Engine** (Linux)
- **Make** (Linux/Mac: pre-installed, Windows: `choco install make`)
- **Git** (for version control)

---

## Quick Start

### Option 1: Docker (Recommended - Works Everywhere)

```bash
# 1. Clone repository
git clone <your-repo-url>
cd fmu_template

# 2. Validate FMUs
make validate

# 3. Start API server
make run-server

# 4. Test API
make test-api
```

### Option 2: Local Development (Linux)

```bash
# 1. Setup virtual environment
make setup

# 2. Activate environment
source venv/bin/activate

# 3. Run tests locally
python scripts/run_tests.py

# 4. Run server locally
python scripts/server.py
```

---

##

 Make Commands

### `make help`
Show all available commands.

```bash
make help
```

---

### `make setup` (Linux Only)
Creates Python virtual environment and installs dependencies.

```bash
make setup

# Then activate:
source venv/bin/activate

# To deactivate:
deactivate
```

**What it does:**
- Creates `venv/` directory
- Installs all packages from `requirements.txt`
- Ready for local testing without Docker

---

### `make validate`
Runs FMU validation tests in Docker.

```bash
make validate
```

**What it does:**
1. Builds Docker image (if not exists)
2. Scans `inputs/` for all FMUs
3. For each FMU:
   - Loads YAML config
   - Runs regression tests (stimuli → reference)
   - Generates manifest JSON
   - Validates tolerance
4. Runs server health check

**Output:**
```
Found 2 FMUs to validate.

=== Processing FMU: CounterFlowNTU ===
Version: 1.0.0
Custom tolerance: 0.001
--- Running Regression Test ---
✅ PASS: 'multiSensor_Tpm.T' max deviation 0.000234
✅ PASS: 'multiSensor_Tpm1.T' max deviation 0.000156
✅ Regression test PASSED

=== All Steps Passed ===
```

**Fails if:**
- FMU file corrupted
- Test deviation > tolerance
- Missing test files
- Server won't start

---

### `make run-server`
Starts REST API server on port 8000.

```bash
make run-server

# Server runs in background
# Access at http://localhost:8000
```

**What it does:**
1. Builds Docker image (if not exists)
2. Stops any existing server
3. Starts new container with name `fmu-server`
4. Exposes port 8000

**Test it's running:**
```bash
curl http://localhost:8000/health
# Should return: {"status": "healthy"}
```

---

### `make test-api`
Runs smoke tests on running server.

```bash
make test-api
```

**Requires:** Server must be running (`make run-server`)

**What it tests:**
- Health endpoint
- List FMUs endpoint
- Returns formatted JSON

---

### `make logs`
View server logs (Ctrl+C to exit).

```bash
make logs
```

**Shows:**
- Startup messages
- API requests
- Errors
- FMU initialization logs

---

### `make stop`
Stops the running server.

```bash
make stop
```

---

### `make rebuild`
Force rebuild Docker image (ignores cache).

```bash
make rebuild
```

**Use when:**
- Changed Python code (`server.py`, `run_tests.py`)
- Updated `requirements.txt`
- Added new dependencies

---

### `make clean`
Stops server and removes Docker image.

```bash
make clean
```

**Use for:** Complete reset

---

## Testing Workflow

### Test New FMU
```bash
# 1. Add FMU to inputs/
mkdir inputs/my_model
cp MyModel.fmu inputs/my_model/
cp MyModel.yaml inputs/my_model/
mkdir inputs/my_model/tests
# Create stimuli.csv and reference.csv

# 2. Validate
make rebuild  # Rebuild to include new FMU
make validate # Run tests

# 3. If passed, start server
make run-server

# 4. Test API
curl http://localhost:8000/fmus
curl http://localhost:8000/fmus/MyModel/metadata
```

### Test Code Changes
```bash
# 1. Edit server.py or run_tests.py

# 2. Rebuild image
make rebuild

# 3. Test
make validate
make run-server
make test-api
```

### Quick Iteration (Local Development)
```bash
# Setup once
make setup
source venv/bin/activate

# Rapid testing (no Docker rebuild)
python scripts/run_tests.py
python scripts/server.py  # Ctrl+C to stop
```

---

## CI/CD Integration

### GitHub Actions
```yaml
name: Validate FMUs
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - run: make validate
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

---

## Troubleshooting

### "Docker daemon not running"
```bash
# Start Docker Desktop (Windows/Mac)
# Or start Docker service (Linux):
sudo systemctl start docker
```

### "Port 8000 already in use"
```bash
make stop  # Stop existing server
# Or kill manually:
docker rm -f fmu-server
```

### "Make command not found" (Windows)
```powershell
# Install via Chocolatey:
choco install make

# Or use direct Docker commands:
docker build -t fmu-validator -f docker/Dockerfile .
docker run --rm fmu-validator python /app/scripts/run_tests.py
```

### "Module not found" (local development)
```bash
# Recreate virtual environment:
rm -rf venv
make setup
source venv/bin/activate
```

### "FMU not discovered"
- Check FMU is in `inputs/**/*.fmu`
- YAML filename must match FMU filename
- Run `make rebuild` after adding FMU

---

## File Locations

| Location | Purpose |
|----------|---------|
| `inputs/` | FMU files, YAML configs, test data |
| `scripts/` | Python validation and server code |
| `docker/` | Dockerfile |
| `venv/` | Virtual environment (local only, gitignored) |
| `requirements.txt` | Python dependencies |
| `Makefile` | Command shortcuts |

---

## Environment Variables

None currently configured. All settings in YAML and Docker.

---

## Performance Tips

- **First build is slow** (~2 min) - subsequent builds use cache
- **Validation scales linearly** with number of FMUs
- **Server startup** < 5 seconds
- **API response** < 100ms per request

---

## Next Steps

- Read [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) to add FMUs
- Check [API_DOCUMENTATION.md](API_DOCUMENTATION.md) for endpoint details
- See [OVERVIEW.md](OVERVIEW.md) for system architecture
