# QZero Architecture (v3.0)

## Package Structure

```
src/qzero/
├── __init__.py            # Public API: QZero, QZeroPredictor, NetworkTrafficAnalyzer
├── config.py              # Centralized configuration (YAML + env vars)
├── logger.py              # Structured logging setup
│
├── quantum/               # Quantum algorithms
│   ├── __init__.py
│   ├── feature_maps.py    # ZZ / Z / Pauli / custom feature maps (Qiskit)
│   ├── qsvm.py            # Quantum Support Vector Machine
│   └── qivae.py           # Quantum-Inspired Variational Autoencoder (PyTorch)
│
├── preprocessing/         # Data ingestion and preparation
│   ├── __init__.py
│   ├── data_loader.py     # UGRansome CSV loader + synthetic data generator
│   └── feature_engineering.py  # PCA/MI reduction, angle encoding [0, π]
│
├── classical/             # Classical ML baselines
│   ├── __init__.py
│   └── baseline.py        # RandomForest, SVM-RBF, GBM, KNN, MLP
│
├── evaluation/            # Metrics
│   ├── __init__.py
│   └── metrics.py         # Accuracy, F1, ROC-AUC, FPR/FNR, zero-day detection rate
│
├── core/                  # Business logic layer
│   ├── __init__.py
│   ├── predictor.py       # QZeroPredictor: trains/evaluates/saves all models
│   └── detector.py        # NetworkTrafficAnalyzer: PCAP -> features -> predictions
│
├── api/                   # REST API
│   ├── __init__.py
│   ├── app.py             # FastAPI app + endpoints
│   └── schemas.py         # Pydantic request/response schemas
│
└── cli/                   # Command-line interface
    ├── __init__.py
    └── main.py            # Click commands: train, analyze, server, monitor
```

## Detection Pipeline

```
PCAP File / Live Interface
        |
        v
NetworkTrafficAnalyzer._extract_features()
  - Per-packet: src_ip, dst_ip, protocol, ports, size
        |
        v
FeatureEngineer.transform()
  - PCA to n_qubits dimensions
  - MinMax scale to [0, π]  (angle encoding)
        |
        v
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│      QSVM        │    │     QI-VAE       │    │    Classical     │
│  (quantum kernel)│    │ (reconstruction  │    │   (RF / SVM)     │
│                  │    │    error score)  │    │                  │
└─────────┬────────┘    └────────┬─────────┘    └─────────┬────────┘
          |                      |                         |
          └──────────────────────┴─────────────────────────┘
                                 |
                          Ensemble vote
                                 |
                          Anomaly score (0–1)
                                 |
                     Binary label: NORMAL / ANOMALY
```

## Key Design Decisions

### 1. Lazy dependency loading
Quantum and API dependencies (Qiskit, PyTorch, FastAPI) are optional. The core package
imports cleanly without them; each sub-module wraps its imports in try/except and provides
classical fallbacks.

### 2. Single installable package (`qzero`)
All code lives under `src/qzero/`. No flat modules alongside the package. Entry points
resolve cleanly: `qzero = "qzero.cli:main"`.

### 3. Real predictions only
`NetworkTrafficAnalyzer` requires a trained `QZeroPredictor` instance. It will never
return synthetic/random scores — missing model → explicit error message.

### 4. Separation of concerns
- `quantum/` — algorithms only, no I/O
- `preprocessing/` — data transformation only
- `core/` — orchestration: loads data, trains, predicts
- `api/` — HTTP interface, no business logic
- `cli/` — user interface, no business logic

## Configuration

Config is loaded in priority order:
1. Explicit constructor arguments
2. YAML file at `~/.qzero/qzero.yaml`
3. Built-in defaults

```python
from qzero import get_config
cfg = get_config("path/to/config.yaml")
print(cfg.get("n_qubits"))   # 4
```

## Quantum Feature Encoding

Classical features are mapped into quantum Hilbert space via:

```
x_i  →  RY(x_i) gates  →  CNOT entanglement  →  RZ(x_i · x_j) phase
```

The ZZ feature map encodes pairwise correlations, making it sensitive to
anomalous co-activation patterns invisible to linear kernels.
