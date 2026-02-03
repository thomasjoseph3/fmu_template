# FMU Template Platform

**Standardized deployment and validation for FMU (Functional Mock-up Unit) models.**

Drop in your FMU → Instant validation & REST API

---

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| **[OVERVIEW.md](OVERVIEW.md)** | Why this exists, benefits, architecture |
| **[SETUP_AND_USAGE.md](SETUP_AND_USAGE.md)** | How to run, make commands, testing |
| **[DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)** | How to add FMUs, YAML configuration |
| **[API_DOCUMENTATION.md](API_DOCUMENTATION.md)** | REST API reference, examples |

---

## ⚡ Quick Start

```bash
# 1. Clone repository
git clone <repo-url>
cd fmu_template

# 2. Validate all FMUs
make validate

# 3. Start API server
make run-server

# 4. Test it
curl http://localhost:8000/fmus
```

---

## 🎯 What You Get

- ✅ **Automated validation** - Regression tests for every FMU
- ✅ **REST API** - Instant model-as-a-service
- ✅ **CI/CD ready** - One-command deployment
- ✅ **Multi-version support** - Run v1, v2, v3 side-by-side
- ✅ **Zero-code config** - YAML drives everything

---

## 📁 Project Structure

```
fmu_template/
├── inputs/                    # FMU packages
│   ├── v1/
│   │   ├── Model.fmu         # Your FMU file
│   │   ├── Model.yaml        # Configuration
│   │   └── tests/
│   │       ├── stimuli.csv   # Test inputs
│   │       └── reference.csv # Expected outputs
│   └── v2/...
├── scripts/
│   ├── run_tests.py          # Validation engine
│   └── server.py             # REST API server
├── docker/
│   └── Dockerfile
├── Makefile                   # Command shortcuts
└── requirements.txt           # Python dependencies
```

---

## 🚀 Adding Your FMU

1. **Create folder:**
   ```bash
   mkdir inputs/my_model
   ```

2. **Add files:**
   ```bash
   cp MyModel.fmu inputs/my_model/
   # Create MyModel.yaml (see DEVELOPER_GUIDE.md)
   # Create tests/stimuli.csv and reference.csv
   ```

3. **Validate:**
   ```bash
   make rebuild
   make validate
   ```

4. **Done!** Your model is validated and API-ready.

---

## 🔧 Make Commands

```bash
make setup       # Setup virtual environment (Linux)
make validate    # Run all FMU validation tests
make run-server  # Start REST API server
make test-api    # Smoke test the API
make rebuild     # Rebuild Docker image
make clean       # Clean up everything
make logs        # View server logs
make stop        # Stop server
```

---

## 📡 API Example

```bash
# List available FMUs
GET /fmus

# Initialize simulation
POST /fmus/MyModel/initialize
{
  "parameters": {
    "design_temp": 360.15
  }
}

# Run simulation step
POST /fmus/MyModel/step
{
  "dt": 0.1,
  "inputs": {
    "sensor_temp": 355.2
  }
}

# Response
{
  "time": 0.1,
  "outputs": {
    "predicted_temp": 340.5
  }
}
```

---

## 🎯 Use Cases

- **CI/CD Quality Gates** - Automated model validation
- **Design Optimization** - Parameter sweeps & comparisons
- **Digital Twin** - Real-time sensor integration
- **Model-as-a-Service** - API-based model access
- **Version Management** - Track model changes with code

---

## 🛠️ Technology Stack

- Python 3.11+ (FMPy, FastAPI, Pandas)
- Docker (containerization)
- Make (build automation)
- YAML (configuration)

---

## 📋 Requirements

- Docker Desktop (Windows/Mac) or Docker Engine (Linux)
- Make (Linux/Mac: built-in, Windows: `choco install make`)
- Git

---

## 🔗 CI/CD Integration

### GitHub Actions
```yaml
- run: make validate
```

### GitLab CI
```yaml
script:
  - make validate
```

### Jenkins
```groovy
sh 'make validate'
```

---

## 📖 Learn More

- [OVERVIEW.md](OVERVIEW.md) - System architecture & benefits
- [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) - Complete developer reference
- [API_DOCUMENTATION.md](API_DOCUMENTATION.md) - API endpoints & examples

---

## 🤝 Contributing

1. Add your FMU to `inputs/`
2. Ensure `make validate` passes
3. Submit pull request

---

## 📜 License

[Your License]

---

## 🙋 Support

- Documentation: See docs above
- Issues: [Your Issue Tracker]
- Contact: [Your Contact]
