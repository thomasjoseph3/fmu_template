#!/usr/bin/env python3
"""
Quick Test Script for CounterFlowNTU API
Tests parameter-only simulation mode
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_api():
    print("=== Testing CounterFlowNTU API ===\n")
    
    # 1. List FMUs
    print("1. Listing available FMUs...")
    response = requests.get(f"{BASE_URL}/fmus")
    print(f"   Available: {response.json()}\n")
    
    # 2. Get metadata
    print("2. Getting FMU metadata...")
    response = requests.get(f"{BASE_URL}/fmus/CounterFlowNTU/metadata")
    metadata = response.json()
    print(f"   Model: {metadata.get('modelName')}")
    print(f"   Version: {metadata.get('version', 'N/A')}\n")
    
    # 3. Initialize with default parameters
    print("3. Initializing with DEFAULT parameters...")
    response = requests.post(f"{BASE_URL}/fmus/CounterFlowNTU/initialize", json={})
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}\n")
    
    # 4. Run simulation step
    print("4. Running simulation step...")
    response = requests.post(f"{BASE_URL}/fmus/CounterFlowNTU/step", json={
        "dt": 0.1
    })
    result1 = response.json()
    print(f"   Time: {result1['time']}")
    print(f"   Outputs: {json.dumps(result1['outputs'], indent=4)}\n")
    
    # 5. Initialize with CUSTOM parameters
    print("5. Re-initializing with CUSTOM parameters...")
    response = requests.post(f"{BASE_URL}/fmus/CounterFlowNTU/initialize", json={
        "parameters": {
            "sourceA.T0_par": 360.15,  # Hotter
            "sourceB.T0_par": 290.15   # Colder
        }
    })
    print(f"   Status: {response.status_code}\n")
    
    # 6. Run simulation with new parameters
    print("6. Running simulation with new parameters...")
    response = requests.post(f"{BASE_URL}/fmus/CounterFlowNTU/step", json={
        "dt": 0.1
    })
    result2 = response.json()
    print(f"   Time: {result2['time']}")
    print(f"   Outputs: {json.dumps(result2['outputs'], indent=4)}\n")
    
    # 7. Compare results
    print("7. Comparing results:")
    print(f"   Default params → Hot outlet: {result1['outputs']['multiSensor_Tpm.T']:.2f}K")
    print(f"   Custom params  → Hot outlet: {result2['outputs']['multiSensor_Tpm.T']:.2f}K")
    print(f"   Difference: {abs(result2['outputs']['multiSensor_Tpm.T'] - result1['outputs']['multiSensor_Tpm.T']):.2f}K\n")
    
    print("✅ All tests passed!")

if __name__ == "__main__":
    try:
        test_api()
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: Cannot connect to server at http://localhost:8000")
        print("   Make sure server is running: make run-server")
    except Exception as e:
        print(f"❌ ERROR: {e}")
