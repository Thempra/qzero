# QZero Installation Guide

> Step-by-step installation instructions for the Quantum Zero-Day Detection Platform

## Table of Contents

- [Requirements](#requirements)
- [Quick Start](#quick-start)
- [Detailed Installation](#detailed-installation)
- [Docker Installation](#docker-installation)
- [Development Setup](#development-setup)
- [Troubleshooting](#troubleshooting)
- [Verification](#verification)

---

## Requirements

### Hardware

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 4 cores | 8+ cores |
| RAM | 8 GB | 16+ GB |
| Disk | 5 GB | 20 GB |
| GPU | Not required | CUDA-capable (optional) |

> **Note**: Quantum simulation is CPU-intensive. More cores = faster training.

### Software

| Software | Version | Required |
|----------|---------|----------|
| Python | 3.10+ | Yes |
| pip | 21.0+ | Yes |
| Git | 2.30+ | Yes |
| Docker | 20.10+ | Optional |
| Docker Compose | 2.0+ | Optional |

### Operating Systems

- ✅ Linux (Ubuntu 20.04+, Debian 11+, RHEL 8+)
- ✅ macOS (11.0+ Big Sur)
- ✅ Windows 10/11 (with WSL2 recommended)

---

## Quick Start

Get up and running in 5 minutes:

```bash
# Clone repository
git clone https://github.com/thempra/qzero.git
cd qzero

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Run demo pipeline
python scripts/run_pipeline.py

# Start API server
python -m uvicorn src.api:app --reload
```

---

## Detailed Installation

### Step 1: Clone the Repository

```bash
# HTTPS (recommended)
git clone https://github.com/thempra/qzero.git

# SSH (if configured)
git clone git@github.com:thempra/qzero.git

# Navigate to project directory
cd qzero
```

### Step 2: Set Up Python Environment

#### Option A: venv (Recommended)

```bash
# Create virtual environment
python3 -m venv venv

# Activate (Linux/macOS)
source venv/bin/activate

# Activate (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Activate (Windows CMD)
venv\Scripts\activate.bat

# Verify activation
which python  # Should show: .../qzero/venv/bin/python
```

#### Option B: Conda

```bash
# Create conda environment
conda create -n qzero python=3.11 -y

# Activate
conda activate qzero

# Verify
python --version  # Should show: Python 3.11.x
```

### Step 3: Install Dependencies

```bash
# Core dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Verify Qiskit installation
python -c "import qiskit; print(f'Qiskit version: {qiskit.__version__}')"
# Expected: Qiskit version: 1.x.x

# Verify PyTorch installation
python -c "import torch; print(f'PyTorch version: {torch.__version__}')"
# Expected: PyTorch version: 2.x.x
```

### Step 4: (Optional) Download Dataset

```bash
# Download UGRansome dataset from Kaggle
python scripts/download_data.py

# Or manually:
# 1. Go to https://www.kaggle.com/datasets/nkongolo/ugransome-dataset
# 2. Download final(2).csv
# 3. Place in data/raw/final(2).csv
```

### Step 5: Verify Installation

```bash
# Run test pipeline
python scripts/run_pipeline.py

# Expected output:
# ======================================================================
# QZero - Quantum Zero-Day Detection System
# End-to-End Pipeline Demo
# ======================================================================
# 📊 Step 1: Generating synthetic data...
# ...
# 🎉 Pipeline complete!
```

---

## Docker Installation

### Prerequisites

```bash
# Install Docker (Ubuntu)
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker

# Install Docker Compose
sudo apt install docker-compose-plugin

# Verify
docker --version
docker compose version
```

### Build and Run

```bash
# Build the image
docker compose build

# Start services
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f qzero-api

# Stop services
docker compose down
```

### Custom Build

```bash
# Build manually
docker build -t qzero:latest .

# Run container
docker run -d \
    --name qzero \
    -p 8000:8000 \
    -v $(pwd)/data:/app/data \
    -e QZERO_BACKEND=aer_simulator \
    qzero:latest

# Access API
curl http://localhost:8000/
```

### Docker Compose Configuration

```yaml
# docker-compose.yml
version: '3.8'

services:
  qzero-api:
    build: .
    container_name: qzero-api
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    environment:
      - QZERO_BACKEND=aer_simulator
      - LOG_LEVEL=INFO
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/"]
      interval: 30s
      timeout: 10s
      retries: 3
```

---

## Development Setup

### Install Dev Dependencies

```bash
# Install development tools
pip install pytest pytest-cov black flake8 mypy

# Or from requirements-dev.txt (if available)
pip install -r requirements-dev.txt
```

### IDE Configuration

#### VS Code

Create `.vscode/settings.json`:

```json
{
    "python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python",
    "python.formatting.provider": "black",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "editor.formatOnSave": true,
    "[python]": {
        "editor.codeActionsOnSave": {
            "source.organizeImports": true
        }
    }
}
```

#### PyCharm

1. **File → Settings → Project → Python Interpreter**
2. Click gear icon → **Add → Existing Environment**
3. Select `qzero/venv/bin/python`

### Running Tests

```bash
# Run all tests
pytest

# With coverage
pytest --cov=src --cov-report=html

# Specific test file
pytest tests/test_qsvm.py -v

# Run with verbose output
pytest -v -s
```

### Code Style

```bash
# Format code with Black
black src/ scripts/ app/

# Check with flake8
flake8 src/ scripts/ app/

# Type checking
mypy src/
```

---

## Platform-Specific Notes

### Linux (Ubuntu/Debian)

```bash
# Install system dependencies
sudo apt update
sudo apt install -y python3-dev python3-venv build-essential

# For GPU support (optional)
# Install CUDA toolkit from NVIDIA
```

### macOS

```bash
# Install Homebrew if not present
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python 3.11+
brew install python@3.11

# Use correct Python
python3.11 -m venv venv
```

### Windows

**Recommended: Use WSL2**

```powershell
# Enable WSL2
wsl --install

# Install Ubuntu
wsl --install -d Ubuntu

# Then follow Linux instructions inside WSL
```

**Native Windows:**

```powershell
# Install Python from python.org
# Ensure "Add to PATH" is checked during installation

# Create virtual environment
py -3.11 -m venv venv

# Activate
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

---

## Troubleshooting

### Common Issues

#### 1. Qiskit Import Error

```
ImportError: No module named 'qiskit'
```

**Solution:**
```bash
pip uninstall qiskit qiskit-terra qiskit-aer
pip install qiskit qiskit-aer qiskit-machine-learning
```

#### 2. PyTorch CUDA Issues

```
RuntimeError: CUDA out of memory
```

**Solution:**
```python
# Force CPU usage
import os
os.environ["CUDA_VISIBLE_DEVICES"] = ""

# Or in code
device = torch.device("cpu")
```

#### 3. Memory Error During Training

```
MemoryError: Unable to allocate array
```

**Solution:**
```python
# Reduce batch size
config = QIVAEConfig(batch_size=16)  # Instead of 32

# Use smaller dataset
qsvm_config = QSVMConfig(max_samples_quantum=100)  # Instead of 500
```

#### 4. Slow Quantum Simulation

**Solution:**
```bash
# Use Aer simulator with GPU (if available)
pip install qiskit-aer-gpu

# Or reduce circuit complexity
config = QSVMConfig(
    n_qubits=4,  # Fewer qubits
    feature_map_reps=1  # Fewer repetitions
)
```

#### 5. Module Not Found Errors

```
ModuleNotFoundError: No module named 'src'
```

**Solution:**
```bash
# Run from project root
cd /path/to/qzero

# Or add to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Or install in editable mode
pip install -e .
```

### Dependency Conflicts

```bash
# Check for conflicts
pip check

# Create fresh environment
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Getting Help

1. **Check logs**: `tail -f logs/qzero.log`
2. **Verbose mode**: Add `-v` to commands
3. **GitHub Issues**: Open an issue with error details

---

## Verification

Run the verification script to ensure everything is installed correctly:

```bash
python -c "
import sys
print(f'Python: {sys.version}')

# Core
import numpy as np
print(f'NumPy: {np.__version__}')

import pandas as pd
print(f'Pandas: {pd.__version__}')

import sklearn
print(f'Scikit-learn: {sklearn.__version__}')

# Quantum
import qiskit
print(f'Qiskit: {qiskit.__version__}')

try:
    import qiskit_machine_learning
    print(f'Qiskit ML: {qiskit_machine_learning.__version__}')
except ImportError:
    print('Qiskit ML: Not installed')

# Deep Learning
import torch
print(f'PyTorch: {torch.__version__}')

# Dashboard
import streamlit
print(f'Streamlit: {streamlit.__version__}')

print('\\n✅ All dependencies installed correctly!')
"
```

### Expected Output

```
Python: 3.11.x
NumPy: 1.24.x
Pandas: 2.x.x
Scikit-learn: 1.3.x
Qiskit: 1.x.x
Qiskit ML: 0.7.x
PyTorch: 2.x.x
Streamlit: 1.x.x

✅ All dependencies installed correctly!
```

---

## Next Steps

After successful installation:

1. 📖 Read the [Usage Guide](USAGE.md) for examples
2. 🏗️ Review the [Architecture](ARCHITECTURE.md) documentation
3. 🔌 Check the [API Reference](API.md) for integration
4. 🚀 Run the demo: `python scripts/run_pipeline.py`
5. 📊 Launch the dashboard: `streamlit run app/dashboard.py`

---

*Document Version: 1.0.0 | Last Updated: 2025*
