# QZero Architecture

> Technical architecture documentation for the Quantum-Enhanced Threat Detection Platform

## Table of Contents

- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Component Details](#component-details)
- [Data Flow](#data-flow)
- [Module Structure](#module-structure)
- [Quantum Components](#quantum-components)
- [Integration Points](#integration-points)

---

## Overview

QZero is a modular quantum machine learning system designed for zero-day attack detection. The architecture follows a **hybrid quantum-classical** approach, combining the pattern recognition capabilities of quantum computing with the efficiency of classical preprocessing and post-processing.

### Design Principles

1. **Modularity**: Each component can be used independently or as part of the full pipeline
2. **Fallback Safety**: Quantum components gracefully degrade to classical equivalents
3. **Scalability**: Supports both simulator-based development and real QPU deployment
4. **Extensibility**: Easy to add new feature maps, models, and metrics

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           QZero System Architecture                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                          DATA LAYER                                     │ │
│  │  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐               │ │
│  │  │  UGRansome   │   │  Synthetic   │   │   NetFlow    │               │ │
│  │  │   Dataset    │   │  Generator   │   │    CSV/PCAP  │               │ │
│  │  └──────┬───────┘   └──────┬───────┘   └──────┬───────┘               │ │
│  │         │                  │                  │                        │ │
│  │         └──────────────────┼──────────────────┘                        │ │
│  │                            ▼                                           │ │
│  │                    ┌──────────────┐                                    │ │
│  │                    │  DataLoader  │                                    │ │
│  │                    └──────┬───────┘                                    │ │
│  └───────────────────────────┼────────────────────────────────────────────┘ │
│                              │                                               │
│  ┌───────────────────────────┼────────────────────────────────────────────┐ │
│  │                    PREPROCESSING LAYER                                  │ │
│  │                           ▼                                             │ │
│  │  ┌──────────────────────────────────────────────────────────────────┐  │ │
│  │  │                    FeatureEngineer                                │  │ │
│  │  │  ┌────────────┐   ┌────────────┐   ┌────────────┐               │  │ │
│  │  │  │ Normalizer │ → │    PCA     │ → │   Scaler   │               │  │ │
│  │  │  │ (Standard) │   │  Reducer   │   │  (0, π)    │               │  │ │
│  │  │  └────────────┘   └────────────┘   └────────────┘               │  │ │
│  │  └──────────────────────────┬───────────────────────────────────────┘  │ │
│  └─────────────────────────────┼──────────────────────────────────────────┘ │
│                                │                                             │
│  ┌─────────────────────────────┼──────────────────────────────────────────┐ │
│  │                       MODEL LAYER                                       │ │
│  │                            │                                            │ │
│  │         ┌──────────────────┼──────────────────┐                        │ │
│  │         │                  │                  │                        │ │
│  │         ▼                  ▼                  ▼                        │ │
│  │  ┌────────────┐    ┌────────────┐    ┌────────────┐                   │ │
│  │  │ Classical  │    │   QSVM     │    │   QI-VAE   │                   │ │
│  │  │ Baselines  │    │  (Kernel)  │    │ (Anomaly)  │                   │ │
│  │  ├────────────┤    ├────────────┤    ├────────────┤                   │ │
│  │  │ • SVM      │    │ • Feature  │    │ • Encoder  │                   │ │
│  │  │ • RF       │    │   Map      │    │ • Decoder  │                   │ │
│  │  │ • XGBoost  │    │ • Quantum  │    │ • Latent   │                   │ │
│  │  │ • MLP      │    │   Kernel   │    │   Space    │                   │ │
│  │  │ • KNN      │    │ • QSVC     │    │ • Recon.   │                   │ │
│  │  └────────────┘    └────────────┘    └────────────┘                   │ │
│  │         │                  │                  │                        │ │
│  └─────────┼──────────────────┼──────────────────┼────────────────────────┘ │
│            │                  │                  │                          │
│  ┌─────────┼──────────────────┼──────────────────┼────────────────────────┐ │
│  │         └──────────────────┼──────────────────┘                        │ │
│  │                    EVALUATION LAYER                                     │ │
│  │                            ▼                                            │ │
│  │  ┌──────────────────────────────────────────────────────────────────┐  │ │
│  │  │                       Metrics Engine                              │  │ │
│  │  │  • Accuracy, Precision, Recall, F1                               │  │ │
│  │  │  • ROC-AUC, Average Precision                                    │  │ │
│  │  │  • Zero-Day Detection Rate                                       │  │ │
│  │  │  • False Positive/Negative Rates                                 │  │ │
│  │  │  • Quantum Advantage Calculation                                 │  │ │
│  │  └──────────────────────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                         API & INTERFACE LAYER                          │ │
│  │  ┌────────────┐    ┌────────────┐    ┌────────────┐                   │ │
│  │  │  FastAPI   │    │ Streamlit  │    │   CLI      │                   │ │
│  │  │  REST API  │    │ Dashboard  │    │  Scripts   │                   │ │
│  │  └────────────┘    └────────────┘    └────────────┘                   │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. Data Layer (`src/preprocessing/`)

#### DataLoader (`data_loader.py`)

Handles all data ingestion and preparation:

```python
class DataLoader:
    """
    Responsibilities:
    - Load UGRansome CSV dataset
    - Generate synthetic data for testing
    - Train/validation/test splitting
    - Label encoding (binary or multi-class)
    - Feature scaling (StandardScaler)
    """
```

**Supported Data Sources:**
| Source | Format | Features | Samples |
|--------|--------|----------|---------|
| UGRansome | CSV | 14 | ~149K |
| Synthetic | Generated | 14 | Configurable |
| NetFlow | CSV | Variable | Variable |

#### FeatureEngineer (`feature_engineering.py`)

Prepares classical data for quantum circuits:

```python
class FeatureEngineer:
    """
    Pipeline:
    1. Dimensionality reduction (PCA/MI/Variance)
    2. Scaling to quantum-compatible range [0, π]
    3. Feature selection for n_qubits constraint
    """
```

### 2. Model Layer

#### Classical Baselines (`src/classical/baseline.py`)

Reference implementations for comparison:

```
┌─────────────────────────────────────────────────────────┐
│                 Classical Baselines                      │
├─────────────────────────────────────────────────────────┤
│  Model               │ Type           │ Use Case        │
├─────────────────────────────────────────────────────────┤
│  SVM (Linear/RBF)    │ Kernel         │ Baseline        │
│  Random Forest       │ Ensemble       │ Feature Import. │
│  Gradient Boosting   │ Ensemble       │ High Accuracy   │
│  Logistic Regression │ Linear         │ Interpretable   │
│  K-NN                │ Instance       │ Simple          │
│  MLP                 │ Neural Network │ Deep Baseline   │
└─────────────────────────────────────────────────────────┘
```

#### QSVM (`src/quantum/qsvm.py`)

Quantum Support Vector Machine using quantum kernel:

```
┌─────────────────────────────────────────────────────────────────┐
│                    QSVM Architecture                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Classical Data x ∈ ℝⁿ                                          │
│         │                                                        │
│         ▼                                                        │
│  ┌─────────────────┐                                            │
│  │   Feature Map   │  φ(x): ℝⁿ → ℋ (Hilbert Space)             │
│  │   (ZZFeatureMap)│                                            │
│  └────────┬────────┘                                            │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────┐                                            │
│  │ Quantum State   │  |φ(x)⟩ = U(x)|0⟩ⁿ                         │
│  │   Preparation   │                                            │
│  └────────┬────────┘                                            │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────┐                                            │
│  │ Kernel Matrix   │  K(xᵢ,xⱼ) = |⟨φ(xᵢ)|φ(xⱼ)⟩|²               │
│  │   Computation   │                                            │
│  └────────┬────────┘                                            │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────┐                                            │
│  │   SVC Fitting   │  Classical SVM with quantum kernel         │
│  │                 │                                            │
│  └─────────────────┘                                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### QI-VAE (`src/quantum/qivae.py`)

Quantum-Inspired Variational Autoencoder for anomaly detection:

```
┌─────────────────────────────────────────────────────────────────┐
│                    QI-VAE Architecture                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Input x ∈ ℝ¹⁴                                                   │
│     │                                                            │
│     ▼                                                            │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                      ENCODER                               │  │
│  │  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐   │  │
│  │  │ Linear  │ → │ BatchNorm│ → │ LeakyReLU│ → │ Dropout │   │  │
│  │  │  64     │   │         │   │  0.2    │   │  0.1    │   │  │
│  │  └─────────┘   └─────────┘   └─────────┘   └─────────┘   │  │
│  │       │                                                    │  │
│  │       ▼                                                    │  │
│  │  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐   │  │
│  │  │ Linear  │ → │ BatchNorm│ → │ LeakyReLU│ → │ Dropout │   │  │
│  │  │  32     │   │         │   │  0.2    │   │  0.1    │   │  │
│  │  └─────────┘   └─────────┘   └─────────┘   └─────────┘   │  │
│  │       │                                                    │  │
│  │       ├──────────────────┐                                │  │
│  │       ▼                  ▼                                │  │
│  │  ┌─────────┐       ┌─────────┐                           │  │
│  │  │  fc_μ   │       │fc_logσ² │                           │  │
│  │  │  (4)    │       │  (4)    │                           │  │
│  │  └────┬────┘       └────┬────┘                           │  │
│  └───────┼─────────────────┼─────────────────────────────────┘  │
│          │                 │                                     │
│          └────────┬────────┘                                     │
│                   │                                              │
│                   ▼                                              │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │           REPARAMETERIZATION (Quantum-Inspired)            │  │
│  │                                                            │  │
│  │    z = μ + ε · σ      (ε ~ N(0,1))                        │  │
│  │                                                            │  │
│  │    # Quantum-inspired amplitude normalization:             │  │
│  │    z_norm = z / ||z||                                     │  │
│  │    z = W · z_norm · ||z||   (W = learned transform)       │  │
│  │                                                            │  │
│  └───────────────────────────────────────────────────────────┘  │
│                   │                                              │
│                   ▼                                              │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                      DECODER                               │  │
│  │  (Mirror of encoder: 4 → 32 → 64 → 14)                    │  │
│  └───────────────────────────────────────────────────────────┘  │
│                   │                                              │
│                   ▼                                              │
│             Output x̂ ∈ ℝ¹⁴                                      │
│                                                                  │
│  Loss = MSE(x, x̂) + β · KL(q(z|x) || p(z))                      │
│                                                                  │
│  Anomaly Score = ||x - x̂||²                                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 3. Quantum Feature Maps (`src/quantum/feature_maps.py`)

Available quantum feature encoding strategies:

```
┌─────────────────────────────────────────────────────────────────┐
│                   Quantum Feature Maps                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Z Feature Map (Diagonal):                                       │
│  ┌───┐                                                          │
│  │ H ├──Rz(x)──                                                 │
│  └───┘                                                          │
│                                                                  │
│  ZZ Feature Map (Entangled):                                     │
│  ┌───┐                                                          │
│  │ H ├──Rz(x₀)──●──────────Rz(x₀x₁)──                          │
│  └───┘          │                                               │
│  ┌───┐          │                                               │
│  │ H ├──Rz(x₁)──⊕──────────Rz(x₁x₂)──                          │
│  └───┘                                                          │
│                                                                  │
│  Custom Entangled Map:                                           │
│  ┌───┐                                                          │
│  │ H ├──Ry(x)──●──Rz(x·x')──CZ──                               │
│  └───┘         │                                                │
│  ┌───┐         │                                                │
│  │ H ├──Ry(x)──⊕──Rz(x·x')──CZ──                               │
│  └───┘                                                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Flow

### Training Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                     Training Data Flow                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Raw Data (CSV/NetFlow)                                          │
│       │                                                          │
│       ▼                                                          │
│  ┌─────────────┐                                                │
│  │ DataLoader  │ ─── Validate, Clean, Encode Labels             │
│  └──────┬──────┘                                                │
│         │                                                        │
│         ▼                                                        │
│  ┌─────────────┐                                                │
│  │ Train/Test  │ ─── Stratified Split (80/20)                   │
│  │   Split     │                                                │
│  └──────┬──────┘                                                │
│         │                                                        │
│         ├─────────────────────────────────────┐                 │
│         │                                     │                 │
│         ▼                                     ▼                 │
│  ┌─────────────┐                      ┌─────────────┐          │
│  │  Classical  │                      │   Quantum   │          │
│  │   Path      │                      │    Path     │          │
│  └──────┬──────┘                      └──────┬──────┘          │
│         │                                     │                 │
│         ▼                                     ▼                 │
│  ┌─────────────┐                      ┌─────────────┐          │
│  │StandardScale│                      │FeatureEngineer│         │
│  └──────┬──────┘                      │ PCA → Scale │          │
│         │                             └──────┬──────┘          │
│         │                                     │                 │
│         ▼                                     ▼                 │
│  ┌─────────────┐                      ┌─────────────┐          │
│  │   Model     │                      │ Quantum     │          │
│  │   .fit()    │                      │ Model.fit() │          │
│  └──────┬──────┘                      └──────┬──────┘          │
│         │                                     │                 │
│         └─────────────────┬───────────────────┘                 │
│                           │                                     │
│                           ▼                                     │
│                    ┌─────────────┐                              │
│                    │  Evaluate   │                              │
│                    │  & Compare  │                              │
│                    └─────────────┘                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Inference Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                     Inference Data Flow                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Network Traffic (Real-time)                                     │
│       │                                                          │
│       ▼                                                          │
│  ┌─────────────┐                                                │
│  │   API       │ ─── POST /analyze                              │
│  │  Endpoint   │                                                │
│  └──────┬──────┘                                                │
│         │                                                        │
│         ▼                                                        │
│  ┌─────────────┐                                                │
│  │ Preprocess  │ ─── Apply fitted scaler/engineer               │
│  └──────┬──────┘                                                │
│         │                                                        │
│         ├────────────────┬────────────────┐                     │
│         │                │                │                     │
│         ▼                ▼                ▼                     │
│  ┌───────────┐   ┌───────────┐   ┌───────────┐                 │
│  │   QSVM    │   │  QI-VAE   │   │  Ensemble │                 │
│  │ .predict()│   │.anomaly() │   │  .vote()  │                 │
│  └─────┬─────┘   └─────┬─────┘   └─────┬─────┘                 │
│        │               │               │                        │
│        └───────────────┼───────────────┘                        │
│                        │                                        │
│                        ▼                                        │
│               ┌─────────────┐                                   │
│               │   Combine   │                                   │
│               │   Results   │                                   │
│               └──────┬──────┘                                   │
│                      │                                          │
│                      ▼                                          │
│               ┌─────────────┐                                   │
│               │    JSON     │                                   │
│               │  Response   │                                   │
│               │ {score, ..} │                                   │
│               └─────────────┘                                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Module Structure

```
qzero/
├── src/
│   ├── __init__.py
│   ├── api.py                    # FastAPI REST endpoints
│   │
│   ├── preprocessing/
│   │   ├── __init__.py
│   │   ├── data_loader.py        # Data ingestion & splitting
│   │   └── feature_engineering.py # Quantum-ready preprocessing
│   │
│   ├── quantum/
│   │   ├── __init__.py
│   │   ├── feature_maps.py       # Quantum encoding circuits
│   │   ├── qsvm.py               # Quantum SVM implementation
│   │   └── qivae.py              # Quantum-Inspired VAE
│   │
│   ├── classical/
│   │   ├── __init__.py
│   │   └── baseline.py           # Classical ML baselines
│   │
│   └── evaluation/
│       ├── __init__.py
│       └── metrics.py            # Evaluation & comparison
│
├── app/
│   └── dashboard.py              # Streamlit dashboard
│
├── scripts/
│   ├── run_pipeline.py           # End-to-end demo
│   ├── benchmark.py              # Full benchmark suite
│   ├── download_data.py          # Dataset download
│   └── generate_report.py        # Report generation
│
├── data/
│   ├── raw/                      # Original datasets
│   └── processed/                # Preprocessed data
│
├── docs/
│   ├── ARCHITECTURE.md           # This file
│   ├── API.md                    # API documentation
│   ├── INSTALLATION.md           # Setup guide
│   └── USAGE.md                  # Usage examples
│
└── tests/
    └── ...                       # Unit tests
```

---

## Quantum Components

### Qiskit Integration

QZero uses **Qiskit 2.1+** with the new functional API:

```python
# Feature Map Creation (Qiskit 2.1+ style)
from qiskit.circuit.library import zz_feature_map

feature_map = zz_feature_map(
    feature_dimension=4,
    reps=2,
    entanglement="linear"
)

# Quantum Kernel
from qiskit_machine_learning.kernels import FidelityQuantumKernel
kernel = FidelityQuantumKernel(feature_map=feature_map)

# QSVM
from qiskit_machine_learning.algorithms import QSVC
qsvm = QSVC(quantum_kernel=kernel)
```

### Backend Options

```
┌─────────────────────────────────────────────────────────────────┐
│                    Supported Backends                            │
├─────────────────────────────────────────────────────────────────┤
│  Backend          │ Qubits │ Use Case      │ Configuration      │
├─────────────────────────────────────────────────────────────────┤
│  AerSimulator     │ 30+    │ Development   │ backend="aer"      │
│  FakeBackend      │ 5-127  │ Noise Testing │ backend="fake_*"   │
│  IBM Quantum      │ 5-127  │ Production    │ backend="ibm_*"    │
│  Classical SVC    │ N/A    │ Fallback      │ auto on failure    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Integration Points

### SIEM Integration

```
┌─────────────────────────────────────────────────────────────────┐
│                   Enterprise Integration                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐   │
│  │ Network │ ──▶ │Logstash │ ──▶ │ QZero   │ ──▶ │  SIEM   │   │
│  │  Tap    │     │/Fluentd │     │  API    │     │ (Splunk)│   │
│  └─────────┘     └─────────┘     └─────────┘     └─────────┘   │
│                                                                  │
│  Protocols: Syslog, NetFlow v9, JSON over HTTP                  │
│  Response: JSON with anomaly scores, classification             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Docker Deployment

```yaml
# docker-compose.yml integration
services:
  qzero-api:
    image: qzero:latest
    ports:
      - "8000:8000"
    environment:
      - QZERO_BACKEND=aer_simulator
    volumes:
      - ./data:/app/data
```

---

## Performance Considerations

### Quantum Limitations (NISQ Era)

| Constraint | Impact | Mitigation |
|------------|--------|------------|
| Limited qubits | Max 4-8 features | PCA reduction |
| Circuit depth | Decoherence | Few reps (1-2) |
| Slow simulation | Training time | Sample subset |
| No error correction | Noise | Classical fallback |

### Recommended Configurations

**Development:**
```python
QSVMConfig(
    n_qubits=4,
    feature_map_reps=2,
    max_samples_quantum=200,
    use_classical_fallback=True
)
```

**Production (Simulator):**
```python
QSVMConfig(
    n_qubits=6,
    feature_map_reps=2,
    max_samples_quantum=500,
    use_classical_fallback=True
)
```

---

*Document Version: 1.0.0 | Last Updated: 2025*
