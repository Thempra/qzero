# QZero - References & Resources

## 📄 Core Papers

### 1. Quantum SVM for Zero-Day Detection (MDPI 2025)

**Title**: Parameterised Quantum SVM with Data-Driven Entanglement for Zero-Day Exploit Detection

**Source**: MDPI Computers, Vol 14, Issue 8, Article 331 (August 2025)

**URL**: https://www.mdpi.com/2073-431X/14/8/331

**Key Points**:
- Uses UGRansome dataset with 14 network traffic attributes
- QSVM with parameterised entanglement
- Compares classical SVM vs QSVM performance
- Targets 3 classes: Anomaly (A), Signature (S), Synthetic Signature (SS)
- Implemented with Qiskit

**Methodology**:
- Feature encoding: Multi-qubit quantum state
- Entanglement: Data-driven parameterised circuits
- Classification: Quantum kernel SVM

---

### 2. QI-VAE for Zero-Day Attack Detection (Nature 2025)

**Title**: Quantum deep learning-enhanced ethereum blockchain for cloud security: intrusion detection, fraud prevention, and secure data migration

**Source**: Nature Scientific Reports (November 2025)

**URL**: https://www.nature.com/articles/s41598-025-22408-1

**Key Points**:
- **QI VAE ZDAD**: Quantum-Inspired Variational Autoencoders for Zero-Day Attack Detection
- **92.3% detection rate** for zero-day attacks
- Reduces false alarms by two-thirds compared to classical methods
- Uses probabilistic latent modeling
- Quantum-inspired representation of features

**Architecture Components**:
1. BAFL SMT - Blockchain-Aware Federated Learning
2. GNN-AID - Graph Neural Networks for Adaptive Intrusion Detection (98.7% accuracy)
3. **QI VAE ZDAD** - Quantum-Inspired VAE for Zero-Day (92.3%)
4. SSCL-BSA - Self-Supervised Contrastive Learning
5. HT SDM - Hierarchical Transformers for Secure Data Migration

---

### 3. UGRansome Dataset Paper (MDPI 2021)

**Title**: UGRansome1819: A Novel Dataset for Anomaly Detection and Zero-Day Threats

**Source**: MDPI Information, Vol 12, Issue 10, Article 405 (September 2021)

**URL**: https://www.mdpi.com/2078-2489/12/10/405

**Key Points**:
- Novel dataset for ransomware and zero-day detection
- Real-world network traffic behaviors
- Includes financial damages, network status, port numbers
- Suitable for ML/DL training and evaluation

**Most Important Features** (by Mean Decrease in Gini):
1. Financial damages (USD and BTC)
2. Network status (flag)
3. Zero-day group (clusters)
4. Normal attacks (threats)
5. Network traffic (netflow bytes)
6. Port number (port)
7. Ransomware-type (family)

---

### 4. Classical ML Baseline (arXiv 2024)

**Title**: Zero-day attack and ransomware detection

**Source**: arXiv:2408.05244 (August 2024)

**URL**: https://arxiv.org/abs/2408.05244

**Key Points**:
- Uses UGRansome dataset
- Compares multiple ML models
- **Results**:
  - Random Forest: Perfect scores (accuracy, precision, recall, F1)
  - XGBoost: Perfect scores
  - SVM: Poor performance
  - Naive Bayes: Poor performance
- Recommends SMOTE for imbalanced data
- Master's thesis from University of Pretoria

---

### 5. Quantum ML for Anomaly Detection (Review)

**Title**: Quantum machine learning algorithms for anomaly detection: A review

**Source**: ScienceDirect, Future Generation Computer Systems (December 2024)

**URL**: https://www.sciencedirect.com/science/article/pii/S0167739X2400596X

**Key Points**:
- Comprehensive review of QML for anomaly detection
- Applications: cybersecurity, fraud detection, particle physics
- Algorithms: QSVM, QNN, Quantum Autoencoders, VQC
- Challenges and future directions

---

## 📊 Datasets

### UGRansome Dataset

**Download**: https://www.kaggle.com/datasets/nkongolo/ugransome-dataset

**Description**:
- Network traffic data with ransomware and zero-day attack patterns
- ~100K samples
- 14+ features
- 3 target classes

**Features**:
| Index | Feature | Type | Description |
|-------|---------|------|-------------|
| 1 | Financial_damages_USD | Numeric | Financial impact in USD |
| 2 | Financial_damages_BTC | Numeric | Financial impact in BTC |
| 3 | Flag | Categorical | Network status |
| 4 | Clusters | Numeric | Zero-day group |
| 5 | Threats | Categorical | Normal attack types |
| 6 | Netflow_bytes | Numeric | Network traffic volume |
| 7 | Port | Numeric | Port number |
| 8 | Family | Categorical | Ransomware type |
| 9 | Protocol | Categorical | Network protocol |
| 10 | IP_address | Categorical | IP address class |
| 11 | Time | Timestamp | Event timestamp |
| ... | ... | ... | ... |

**Target Classes**:
- **A (Anomaly)**: Zero-day/unknown attacks
- **S (Signature)**: Known attack signatures
- **SS (Synthetic Signature)**: Artificially generated signatures

---

## 🔧 Tools & Frameworks

### Qiskit

**URL**: https://qiskit.org/

**Components Needed**:
- `qiskit` - Core quantum circuits
- `qiskit-aer` - Simulators
- `qiskit-machine-learning` - ML algorithms (QSVM, VQC)

**Tutorials**:
- Qiskit ML: https://qiskit.org/ecosystem/machine-learning/
- QSVM Tutorial: https://qiskit.org/ecosystem/machine-learning/tutorials/03_quantum_kernel.html

### Scikit-learn

For classical baselines and preprocessing.

### Pandas/NumPy

For data manipulation.

---

## 📚 Additional Reading

### Quantum Kernels
- Havlíček et al. (2019): "Supervised learning with quantum-enhanced feature spaces"
- Schuld & Killoran (2019): "Quantum Machine Learning in Feature Hilbert Spaces"

### Variational Quantum Algorithms
- Cerezo et al. (2021): "Variational quantum algorithms"
- McClean et al. (2016): "The theory of variational hybrid quantum-classical algorithms"

### Intrusion Detection Systems
- Buczak & Guven (2016): "A Survey of Data Mining and Machine Learning Methods for Cyber Security Intrusion Detection"

---

## 🔗 Quick Links

| Resource | URL |
|----------|-----|
| UGRansome Dataset | https://www.kaggle.com/datasets/nkongolo/ugransome-dataset |
| Qiskit ML Docs | https://qiskit.org/ecosystem/machine-learning/ |
| iQuHACK 2026 | https://iquhack.mit.edu/ |
| MDPI Paper | https://www.mdpi.com/2073-431X/14/8/331 |
| Nature Paper | https://www.nature.com/articles/s41598-025-22408-1 |
| arXiv Baseline | https://arxiv.org/abs/2408.05244 |

---

*Last Updated: 2026-01-27*
