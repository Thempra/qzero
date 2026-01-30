# QZero Requirements

## Core Dependencies

### Python Version
- **Python**: >= 3.10

### Essential Dependencies

```txt
# Core ML & Data Processing
numpy>=1.24.0
pandas>=2.0.0
scikit-learn>=1.3.0

# Quantum Computing
qiskit>=1.0.0
qiskit-aer>=0.13.0
qiskit-machine-learning>=0.7.0

# Deep Learning (for QI-VAE)
torch>=2.0.0

# API & Web
fastapi>=0.104.0
uvicorn>=0.24.0
pydantic>=2.0.0

# Dashboard
streamlit>=1.28.0

# Data Download
kaggle>=1.5.0
```

## Optional Dependencies

```txt
# Visualization
matplotlib>=3.7.0
seaborn>=0.12.0

# Testing
pytest>=7.4.0
pytest-cov>=4.1.0

# Code Quality
black>=23.0.0
flake8>=6.0.0
mypy>=1.4.0

# Docker
docker>=6.0.0
docker-compose>=2.0.0
```

## Installation

### Quick Install (Recommended)

```bash
# Clone repository
git clone https://github.com/thempra/qzero.git
cd qzero

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or: venv\Scripts\activate  # Windows

# Install core dependencies
pip install -r requirements.txt

# Install dev dependencies (optional)
pip install -r requirements-dev.txt
```

### Docker Installation

```bash
# Build and run
docker compose up -d --build

# Check status
docker compose ps

# View logs
docker compose logs -f qzero-api
```

## Version Requirements

| Package | Minimum | Recommended | Maximum |
|---------|---------|-------------|---------|
| Python | 3.10 | 3.11 | 3.12 |
| NumPy | 1.24 | 1.26 | 2.0 |
| Pandas | 2.0 | 2.1 | 2.2 |
| Qiskit | 1.0 | 1.1 | 1.2 |
| PyTorch | 2.0 | 2.1 | 2.2 |

## Hardware Requirements

### Minimum
- CPU: 4 cores
- RAM: 8 GB
- Disk: 5 GB

### Recommended
- CPU: 8 cores
- RAM: 16 GB
- Disk: 20 GB
- GPU: Optional (CUDA-capable)

### Quantum Hardware
For real QPU execution:
- Access to IBM Quantum, IonQ, or equivalent
- Account with API credentials

## Platform Support

| Platform | Status | Notes |
|----------|--------|-------|
| Linux (Ubuntu 20.04+) | ✅ Full Support | Best experience |
| macOS (11.0+) | ✅ Full Support | Works on Intel and M1/M2/M3 |
| Windows 10/11 | ⚠️ Limited | Use WSL2 for best results |
| WSL2 | ✅ Full Support | Recommended for Windows |

## Dependencies Graph

```
QZero
├── Core ML
│   ├── numpy
│   ├── pandas
│   └── scikit-learn
│
├── Quantum Computing
│   ├── qiskit
│   ├── qiskit-aer
│   └── qiskit-machine-learning
│
├── Deep Learning
│   └── torch
│
├── API & Web
│   ├── fastapi
│   ├── uvicorn
│   └── pydantic
│
└── Dashboard
    └── streamlit
```

## Troubleshooting

### ImportError: qiskit not found
```bash
pip install qiskit qiskit-aer qiskit-machine-learning
```

### CUDA out of memory
```bash
# Force CPU usage
export CUDA_VISIBLE_DEVICES=""
# or set device to CPU in code
```

### Slow quantum simulation
```bash
# Reduce circuit complexity
# Use fewer qubits or fewer repetitions
```

### Kaggle download errors
```bash
# Ensure proper Kaggle credentials
chmod 600 ~/.kaggle/kaggle.json

# Or download manually and place in data/raw/
```