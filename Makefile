# FMU Validation and Deployment Makefile
# Simple commands for CI/CD and local testing

.PHONY: help validate run-server clean build rebuild test-api logs stop check-image

# Image name
IMAGE_NAME = fmu-validator

# Default target
help:
	@echo "FMU Template - Available Commands:"
	@echo ""
	@echo "  make setup         - Create virtual environment & install dependencies (Linux)"
	@echo "  make validate      - Run FMU validation tests (auto-builds if needed)"
	@echo "  make run-server    - Start the REST API server (auto-builds if needed)"
	@echo "  make test-api      - Run API smoke tests"
	@echo "  make rebuild       - Force rebuild Docker image"
	@echo "  make clean         - Stop all containers and clean up"
	@echo "  make logs          - Show server logs"
	@echo "  make stop          - Stop the running server"
	@echo ""

# Setup virtual environment (Linux only)
setup:
	@echo "=== Setting Up Virtual Environment ==="
	python3 -m venv venv
	./venv/bin/pip install --upgrade pip
	./venv/bin/pip install -r requirements.txt
	@echo "✅ Setup complete!"
	@echo ""
	@echo "To activate: source venv/bin/activate"
	@echo "To test locally: python scripts/run_tests.py"
	@echo ""

# Check if image exists, build only if missing
check-image:
	@docker image inspect $(IMAGE_NAME) >/dev/null 2>&1 || $(MAKE) build

# Build the Docker image
build:
	@echo "=== Building FMU Validator Image ==="
	docker build -t $(IMAGE_NAME) -f docker/Dockerfile .
	@echo "✅ Build complete!"

# Force rebuild (ignores existing image)
rebuild:
	@echo "=== Force Rebuilding Image ==="
	docker build --no-cache -t $(IMAGE_NAME) -f docker/Dockerfile .
	@echo "✅ Rebuild complete!"

# Run validation tests (only builds if image missing)
validate: check-image
	@echo "=== Running FMU Validation Tests ==="
	docker run --rm $(IMAGE_NAME) python /app/scripts/run_tests.py
	@echo "✅ Validation complete!"

# Start the REST API server (only builds if image missing)
run-server: check-image
	@echo "=== Starting FMU REST API Server ==="
	@docker rm -f fmu-server 2>/dev/null || true
	docker run -d -p 8000:8000 --name fmu-server $(IMAGE_NAME)
	@echo "✅ Server started at http://localhost:8000"
	@echo "   View logs: make logs"
	@echo "   Stop server: make stop"

# Test API endpoints
test-api:
	@echo "=== Testing API Endpoints ==="
	@echo ""
	@echo "1. Health Check:"
	@curl -s http://localhost:8000/health | python -m json.tool || echo "❌ Server not running"
	@echo ""
	@echo "2. List FMUs:"
	@curl -s http://localhost:8000/fmus | python -m json.tool || echo "❌ Failed"
	@echo ""
	@echo "✅ API tests complete!"

# Show server logs
logs:
	@echo "=== Server Logs (Ctrl+C to exit) ==="
	docker logs -f fmu-server

# Stop the server
stop:
	@echo "=== Stopping Server ==="
	docker rm -f fmu-server 2>/dev/null || echo "No server running"
	@echo "✅ Server stopped"

# Clean up everything
clean: stop
	@echo "=== Cleaning Up ==="
	docker rmi $(IMAGE_NAME) 2>/dev/null || echo "Image already removed"
	@echo "✅ Cleanup complete!"

# Quick test: validate + run + test
quick-test: validate run-server
	@echo "Waiting for server startup..."
	@sleep 3
	@$(MAKE) test-api
