# QZero — Quantum-Algorithm-Based Threat Detection

> Real-time network anomaly detection powered by Quantum SVM and Quantum-Inspired Variational Autoencoders.

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## Overview

QZero detects zero-day network threats by combining two quantum-inspired learning paradigms:

| Model | Type | Role |
|-------|------|------|
| **QSVM** | Quantum Support Vector Machine | Binary classification (normal vs. threat) |
| **QI-VAE** | Quantum-Inspired Variational Autoencoder | Unsupervised anomaly scoring via reconstruction error |
| **Classical baselines** | Random Forest, SVM-RBF, Gradient Boosting | Benchmark comparison |

The system ingests raw PCAP traffic, extracts flow-level features, maps them onto quantum feature spaces (ZZ-feature maps, angle encoding), and produces per-packet anomaly scores with sub-millisecond inference latency.

---

## Architecture

```
src/qzero/
├── quantum/            # Quantum algorithms
│   ├── qsvm.py         # Quantum kernel SVM (Qiskit + classical fallback)
│   ├── qivae.py        # Quantum-Inspired VAE (PyTorch)
│   └── feature_maps.py # ZZ, Z, Pauli feature maps
│
├── preprocessing/      # Data pipeline
│   ├── data_loader.py  # UGRansome loader + synthetic data generator
│   └── feature_engineering.py  # PCA / MI reduction + quantum angle encoding
│
├── classical/          # Baseline models
│   └── baseline.py     # RF, SVM-RBF, GBM, KNN, MLP
│
├── evaluation/         # Metrics
│   └── metrics.py      # Accuracy, F1, ROC-AUC, FPR/FNR, zero-day detection rate
│
├── core/               # Business logic
│   ├── predictor.py    # QZeroPredictor: orchestrates training & inference
│   └── detector.py     # NetworkTrafficAnalyzer: PCAP -> features -> predictions
│
├── api/                # REST API (FastAPI)
│   ├── app.py          # Endpoints: /analyze, /health, /models, /stats
│   └── schemas.py      # Pydantic request/response models
│
├── cli/                # Command-line interface (Click)
│   └── main.py         # qzero train | analyze | server | monitor
│
├── config.py           # Centralized configuration
└── logger.py           # Structured logging
```

---

## Installation

```bash
git clone https://github.com/thempra/qzero.git
cd qzero

# Core (classical fallback always available)
pip install -e .

# Quantum models
pip install -e ".[quantum]"     # Adds qiskit + torch

# Real-time monitoring
pip install -e ".[realtime]"    # Adds scapy + psutil

# Everything
pip install -e ".[all]"
```

---

## Quick Start

### Python API

```python
from qzero import QZero

# Initialize and train
qzero = QZero(n_qubits=4)
qzero.train(n_samples=5000)

# Analyze a PCAP file
result = qzero.analyze_traffic("capture.pcap", method="best")
print(f"Anomalies found: {result['results']['n_anomalies_detected']}")
print(f"Anomaly rate:    {result['results']['anomaly_percentage']:.1f}%")
```

### CLI

```bash
# Train models on synthetic data
qzero train --samples 5000 --qubits 4 --save-dir ./models

# Analyze a PCAP (loads pre-trained models)
qzero analyze capture.pcap --model-dir ./models --method best --output result.json

# Start REST API
qzero server --host 0.0.0.0 --port 8000 --model-dir ./models

# Real-time monitoring (requires root for promiscuous mode)
sudo qzero monitor --interface eth0 --promiscuous --interval 10 --model-dir ./models
```

### REST API

```bash
# Start the API server
qzero server

# Analyze a PCAP via HTTP
curl -X POST http://localhost:8000/analyze \
     -F "file=@capture.pcap" \
     -F "method=best" | python -m json.tool

# Health check
curl http://localhost:8000/health
```

---

## Models

### Quantum SVM (QSVM)

Uses a **ZZ feature map** to encode classical network features into a quantum Hilbert space. The quantum kernel `K(x, x') = |<φ(x)|φ(x')>|²` captures non-linear correlations invisible to classical kernels.

- Backend: [Qiskit Machine Learning](https://qiskit-extensions.github.io/qiskit-machine-learning/)
- Fallback: classical SVM with RBF kernel when Qiskit is unavailable
- Input: 4–8 PCA-reduced features in `[0, π]`

### Quantum-Inspired VAE (QI-VAE)

A Variational Autoencoder with **quantum-inspired latent space** sampling:
- Amplitude normalization in latent space (Born rule analogy)
- Trained only on normal traffic samples
- Anomaly score = reconstruction error; threshold set at training time

- Backend: PyTorch
- Input: full feature vector (14 UGRansome features)

---

## Data

QZero ships with a synthetic data generator that simulates the [UGRansome dataset](https://www.kaggle.com/datasets/nishithsanghvi/ugr16) profile:

```python
from qzero.preprocessing import generate_synthetic_data

X, y = generate_synthetic_data(
    n_samples=10000,
    anomaly_ratio=0.15,   # 15% anomalies
    difficulty="medium",  # easy | medium | hard
)
```

To use the real UGRansome dataset, place `final(2).csv` in the `data/` directory and pass `use_real_data=True` to `qzero.train()`.

---

## Evaluation

```python
from qzero import QZeroPredictor

predictor = QZeroPredictor()
predictor.train_all(n_samples=5000)

results = predictor.evaluate()
print(predictor.compare_models())
```

Example output:

```
======================================================================
QZero Model Comparison
======================================================================
Model                      Accuracy    Precision       Recall       F1   Zero-Day %
----------------------------------------------------------------------
QSVM                         0.9312       0.9108       0.9501   0.9300       93.0%
QI-VAE                       0.9187       0.8943       0.9412   0.9172       91.7%
Random Forest                0.9421       0.9301       0.9543   0.9420       94.2%
======================================================================
```

---

## Configuration

```python
from qzero import get_config

cfg = get_config()
cfg.set("n_qubits", 6)
cfg.set("default_threshold", 0.75)
cfg.save()
```

Or via a YAML file at `~/.qzero/qzero.yaml`.

---

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Lint
flake8 src/qzero/
```

---

## References

- Havlicek et al. (2019). *Supervised learning with quantum-enhanced feature spaces.* Nature.
- Romero et al. (2017). *Quantum autoencoders for efficient compression of quantum data.* Quantum Sci. Technol.
- UGRansome Dataset — network traffic anomaly benchmark.

---

## License

MIT — see [LICENSE](LICENSE).
