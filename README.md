# QZero 🛡️⚛️

**Quantum Zero-Day Detection System**

> Detecting the unknown with quantum-enhanced machine learning

[![iQuHACK 2026](https://img.shields.io/badge/iQuHACK-2026-blue)](https://iquhack.mit.edu/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Qiskit](https://img.shields.io/badge/Qiskit-1.0+-purple.svg)](https://qiskit.org/)

## 🎯 Overview

QZero is a quantum machine learning system for detecting zero-day attacks and ransomware in network traffic. It leverages Quantum Support Vector Machines (QSVM) and Quantum-Inspired Variational Autoencoders (QI-VAE) to identify previously unseen attack patterns that evade traditional signature-based detection.

### Why Quantum?

Traditional intrusion detection systems fail against zero-day attacks because they rely on known signatures. Quantum machine learning offers:

- **Exponential feature space**: Quantum kernels can capture complex patterns in high-dimensional data
- **Enhanced anomaly detection**: QI-VAE models probabilistic latent spaces more effectively
- **Potential speedup**: Grover-like advantages in search and classification

## 📊 Key Results (from literature)

| Method | Detection Rate | False Positive Rate | Source |
|--------|---------------|---------------------|--------|
| QI-VAE ZDAD | **92.3%** | 0.8% | Nature Sci. Reports 2025 |
| QSVM (UGRansome) | 89.7% | 1.2% | MDPI 2025 |
| Classical SVM | 78.4% | 3.1% | Baseline |
| Random Forest | 99.4%* | 0.5% | arXiv 2024 |

*Note: Classical RF achieves high accuracy on known patterns but struggles with true zero-days

## 🏗️ Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Network Data   │────▶│  Feature Encoder │────▶│  Quantum Layer  │
│  (UGRansome)    │     │  (Classical)     │     │  (Qiskit)       │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                          │
┌─────────────────┐     ┌──────────────────┐              │
│   Alert/Action  │◀────│   Classifier     │◀─────────────┘
│                 │     │   (Hybrid)       │
└─────────────────┘     └──────────────────┘
```

### Components

1. **Feature Encoder**: Preprocesses network traffic features (14 attributes from UGRansome)
2. **Quantum Feature Map**: ZZFeatureMap / PauliFeatureMap for quantum encoding
3. **Variational Ansatz**: RealAmplitudes / EfficientSU2 for parameterized quantum circuits
4. **QSVM Classifier**: Quantum kernel-based classification
5. **QI-VAE Detector**: Quantum-inspired variational autoencoder for anomaly detection

## 📁 Project Structure

```
qzero/
├── README.md
├── docs/
│   ├── PROJECT_DEFINITION.md    # Full project specification
│   ├── ARCHITECTURE.md          # Technical architecture
│   └── REFERENCES.md            # Papers and resources
├── data/
│   ├── raw/                     # Original datasets
│   └── processed/               # Preprocessed features
├── src/
│   ├── preprocessing/           # Data preprocessing
│   ├── quantum/                 # Quantum circuits and models
│   ├── classical/               # Classical ML baselines
│   └── evaluation/              # Metrics and benchmarks
├── notebooks/
│   ├── 01_data_exploration.ipynb
│   ├── 02_classical_baseline.ipynb
│   ├── 03_qsvm_implementation.ipynb
│   └── 04_qivae_implementation.ipynb
├── papers/                      # Reference papers
├── requirements.txt
└── LICENSE
```

## 🚀 Quick Start

```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/qzero.git
cd qzero

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Download dataset
python scripts/download_data.py

# Run classical baseline
python src/classical/baseline.py

# Run quantum experiments
python src/quantum/qsvm_train.py
```

## 📚 Dataset

**UGRansome** - A novel dataset for anomaly detection and zero-day threats

- **Source**: [Kaggle](https://www.kaggle.com/datasets/nkongolo/ugransome-dataset)
- **Features**: 14 network traffic attributes
- **Classes**: Anomaly (A), Signature (S), Synthetic Signature (SS)
- **Size**: ~100K samples

### Features

| # | Feature | Description |
|---|---------|-------------|
| 1 | Flow Duration | Connection duration |
| 2 | Total Fwd Packets | Forward packet count |
| 3 | Total Bwd Packets | Backward packet count |
| 4 | Flow Bytes/s | Data transfer rate |
| 5 | Flow Packets/s | Packet rate |
| ... | ... | ... |

## 🔬 Methodology

### 1. Quantum Support Vector Machine (QSVM)

```python
from qiskit.circuit.library import ZZFeatureMap, RealAmplitudes
from qiskit_machine_learning.kernels import FidelityQuantumKernel

# Quantum feature map
feature_map = ZZFeatureMap(feature_dimension=14, reps=2)

# Quantum kernel
kernel = FidelityQuantumKernel(feature_map=feature_map)

# Train QSVM
qsvm = QSVC(quantum_kernel=kernel)
qsvm.fit(X_train, y_train)
```

### 2. Quantum-Inspired Variational Autoencoder (QI-VAE)

```python
# Encoder circuit
encoder = QuantumCircuit(n_qubits)
encoder.compose(feature_map, inplace=True)
encoder.compose(ansatz, inplace=True)

# Latent space measurement
# Reconstruction loss + KL divergence
```

## 📈 Evaluation Metrics

- **Accuracy**: Overall classification accuracy
- **Precision**: True positives / (True positives + False positives)
- **Recall**: True positives / (True positives + False negatives)
- **F1-Score**: Harmonic mean of precision and recall
- **Zero-Day Detection Rate**: Ability to detect unseen attack patterns
- **False Positive Rate**: Critical for real-world deployment

## 🎓 iQuHACK 2026

This project is being developed for [MIT iQuHACK 2026](https://iquhack.mit.edu/) (January 30 - February 1, 2026).

**Team**: TBD
**Track**: TBD (IBM Quantum / IonQ / QuEra / Virtual)

## 📖 References

1. **QSVM for Zero-Day Detection** - MDPI Computers 2025
   - "Parameterised Quantum SVM with Data-Driven Entanglement for Zero-Day Exploit Detection"
   
2. **QI-VAE ZDAD** - Nature Scientific Reports 2025
   - "Quantum deep learning-enhanced ethereum blockchain for cloud security"
   - 92.3% zero-day detection rate
   
3. **UGRansome Dataset** - MDPI Information 2021
   - "UGRansome1819: A Novel Dataset for Anomaly Detection and Zero-Day Threats"

4. **Classical Baseline** - arXiv 2024
   - "Zero-day attack and ransomware detection"

## 🤝 Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

**QZero** - *Detecting the threats of tomorrow, today* ⚛️🛡️
