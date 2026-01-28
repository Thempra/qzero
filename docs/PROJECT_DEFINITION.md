# QZero - Project Definition

## Executive Summary

**QZero** is a quantum machine learning system designed to detect zero-day attacks and ransomware in network traffic. Unlike traditional signature-based intrusion detection systems (IDS), QZero uses quantum-enhanced algorithms to identify previously unseen attack patterns.

**Target Event**: MIT iQuHACK 2026 (January 30 - February 1, 2026)

**Category**: Cybersecurity × Quantum Computing

---

## Problem Statement

### The Zero-Day Challenge

Zero-day attacks exploit previously unknown vulnerabilities, making them invisible to traditional security systems that rely on signature matching. By definition, you cannot detect something you've never seen before using conventional methods.

**Current limitations**:
- Signature-based IDS: 0% detection of true zero-days
- Anomaly-based IDS: High false positive rates (5-15%)
- ML-based IDS: Limited generalization to novel attack patterns

### Why Quantum?

Quantum machine learning offers potential advantages:

1. **Exponential Feature Space**: Quantum kernels operate in 2^n dimensional Hilbert space
2. **Complex Pattern Recognition**: Entanglement captures correlations classical kernels miss
3. **Probabilistic Modeling**: Natural fit for anomaly/outlier detection
4. **Potential Speedup**: Quadratic advantage in certain classification tasks

---

## Technical Approach

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        QZero Pipeline                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │  Raw     │    │ Feature  │    │ Quantum  │    │ Hybrid   │  │
│  │  Data    │───▶│ Engineer │───▶│ Encoding │───▶│ Classify │  │
│  │          │    │          │    │          │    │          │  │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘  │
│       │               │               │               │         │
│       ▼               ▼               ▼               ▼         │
│  UGRansome      Normalization    ZZFeatureMap      QSVM/       │
│  Dataset        PCA/Selection    14→n qubits       QI-VAE      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Component 1: Data Preprocessing

**Dataset**: UGRansome (Kaggle)
- 14 network traffic features
- 3 target classes: Anomaly (A), Signature (S), Synthetic Signature (SS)
- ~100K samples

**Preprocessing Steps**:
1. Handle missing values
2. Normalize features (StandardScaler)
3. Feature selection (top-k by importance)
4. Dimensionality reduction for qubit constraints
5. Train/validation/test split (70/15/15)

### Component 2: Quantum Feature Encoding

**Challenge**: Map classical features to quantum states

**Options**:

| Feature Map | Qubits | Expressibility | Entanglement |
|-------------|--------|----------------|--------------|
| ZZFeatureMap | n | High | Full |
| PauliFeatureMap | n | Medium | Configurable |
| AmplitudeEncoding | log(n) | Very High | Implicit |

**Selected**: ZZFeatureMap with 2 repetitions
- Reason: Good balance of expressibility and circuit depth
- Encodes correlations between features via ZZ interactions

```python
from qiskit.circuit.library import ZZFeatureMap

feature_map = ZZFeatureMap(
    feature_dimension=n_features,
    reps=2,
    entanglement='full'
)
```

### Component 3: Quantum Classifier (QSVM)

**Quantum Kernel**:
```
K(x, x') = |⟨φ(x)|φ(x')⟩|²
```

Where φ(x) is the quantum feature map.

**Implementation**:
```python
from qiskit_machine_learning.kernels import FidelityQuantumKernel
from qiskit_machine_learning.algorithms import QSVC

kernel = FidelityQuantumKernel(feature_map=feature_map)
qsvm = QSVC(quantum_kernel=kernel)
```

### Component 4: Quantum-Inspired VAE (QI-VAE)

**Purpose**: Detect anomalies by modeling "normal" traffic distribution

**Architecture**:
1. Quantum encoder: Maps input to latent space
2. Measurement: Collapses to classical latent vector
3. Classical decoder: Reconstructs input
4. Anomaly score: Reconstruction error

**Loss Function**:
```
L = Reconstruction_Loss + β * KL_Divergence
```

**Zero-Day Detection**:
- Train on "normal" traffic only
- High reconstruction error → potential zero-day

---

## Implementation Plan

### Phase 1: Foundation (Pre-hackathon)

- [x] Project setup and documentation
- [ ] Download and explore UGRansome dataset
- [ ] Implement classical baselines (SVM, RF, XGBoost)
- [ ] Set up Qiskit environment
- [ ] Basic quantum circuit tests

### Phase 2: QSVM Implementation (Day 1)

- [ ] Feature preprocessing pipeline
- [ ] ZZFeatureMap implementation
- [ ] Quantum kernel computation
- [ ] QSVM training and evaluation
- [ ] Hyperparameter tuning

### Phase 3: QI-VAE Implementation (Day 2)

- [ ] Variational quantum encoder
- [ ] Classical decoder network
- [ ] Training loop with hybrid optimization
- [ ] Anomaly detection threshold tuning
- [ ] Zero-day evaluation

### Phase 4: Integration & Demo (Day 3)

- [ ] Pipeline integration
- [ ] Real-time demo interface
- [ ] Performance benchmarking
- [ ] Documentation and presentation
- [ ] Submission

---

## Success Metrics

### Primary Metrics

| Metric | Target | Stretch Goal |
|--------|--------|--------------|
| Zero-Day Detection Rate | >85% | >92% |
| False Positive Rate | <3% | <1.5% |
| Overall Accuracy | >90% | >95% |

### Secondary Metrics

- Circuit depth (minimize for NISQ compatibility)
- Training time vs classical baseline
- Qubit count (feasibility on real hardware)

---

## Technical Requirements

### Software

```
python>=3.10
qiskit>=1.0
qiskit-machine-learning>=0.7
qiskit-aer>=0.13
numpy>=1.24
pandas>=2.0
scikit-learn>=1.3
matplotlib>=3.7
jupyter>=1.0
```

### Hardware Options

1. **Simulator** (Qiskit Aer): Up to 30+ qubits
2. **IBM Quantum**: 127-qubit devices (if access granted)
3. **IonQ**: Trapped ion (if sponsor challenge)
4. **Local**: CPU/GPU for classical preprocessing

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Circuit too deep for NISQ | High | High | Use error mitigation, reduce reps |
| Training too slow | Medium | Medium | Use simulator, reduce dataset |
| Poor quantum advantage | Medium | Low | Focus on novelty, not speedup |
| Hardware access issues | Low | High | Prepare simulator fallback |

---

## Team Roles (TBD)

- **Quantum Lead**: Circuit design, Qiskit implementation
- **ML Lead**: Classical baselines, preprocessing
- **Data Lead**: Dataset analysis, feature engineering
- **Integration Lead**: Pipeline, demo, documentation

---

## References

### Papers

1. **QSVM for Zero-Day** (MDPI 2025)
   - DOI: 10.3390/computers14080331
   - Key: Parameterised QSVM, UGRansome dataset

2. **QI-VAE ZDAD** (Nature Sci. Reports 2025)
   - DOI: 10.1038/s41598-025-22408-1
   - Key: 92.3% zero-day detection

3. **UGRansome Dataset** (MDPI 2021)
   - DOI: 10.3390/info12100405
   - Key: Dataset description

4. **Classical Baseline** (arXiv 2024)
   - arXiv: 2408.05244
   - Key: RF/XGBoost benchmarks

### Code Resources

- Qiskit Textbook: https://qiskit.org/textbook
- Qiskit ML Tutorials: https://qiskit.org/ecosystem/machine-learning/
- UGRansome Kaggle: https://www.kaggle.com/datasets/nkongolo/ugransome-dataset

---

## Timeline

```
Week of Jan 27: Preparation
├── Mon-Wed: Dataset exploration, classical baselines
├── Thu-Fri: Qiskit setup, basic QSVM tests
└── Weekend: Documentation, pre-hackathon prep

iQuHACK (Jan 30 - Feb 1):
├── Day 1 (Fri): QSVM implementation
├── Day 2 (Sat): QI-VAE implementation  
└── Day 3 (Sun): Integration, demo, submission
```

---

*Document Version: 1.0*
*Last Updated: 2026-01-27*
*Author: Radomo (QZero Team)*
