FROM python:3.9-slim

# Install system dependencies
# - build-essential: for compiling C extensions
# - libgomp1: OpenMP runtime, often needed by FMUs (Modelica)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Create a virtual environment
ENV VIRTUAL_ENV=/app/venv
RUN python -m venv $VIRTUAL_ENV
# Place venv bin on PATH so we don't need to prefix commands with path to venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy validation scripts
COPY scripts/ /app/scripts/

# Create a directory for inputs and copy them
RUN mkdir -p /app/inputs
COPY inputs/ /app/inputs/

# Default command: run the validation script
CMD ["python", "/app/scripts/run_tests.py"]
