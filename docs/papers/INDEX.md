# 📚 Papers Index - QZero Project

This directory contains academic papers relevant to the QZero project, covering Quantum Machine Learning, cybersecurity, and zero-day attack detection.

---

## 🔬 Core Quantum ML Papers

### 1. Quantum SVM - Foundation
- **File:** `1307.0471_Quantum_SVM_Big_Data.pdf`
- **arXiv:** [1307.0471](https://arxiv.org/abs/1307.0471)
- **Title:** *Quantum Support Vector Machine for Big Data Classification*
- **Authors:** Rebentrost et al. (2014)
- **Summary:** Foundational paper proving exponential speedup for SVM on quantum computers with logarithmic time complexity. Establishes theoretical basis for QSVM.

### 2. Quantum VAE - Original
- **File:** `1802.05779_Quantum_VAE.pdf`
- **arXiv:** [1802.05779](https://arxiv.org/abs/1802.05779)
- **Title:** *Quantum Variational Autoencoder*
- **Authors:** Khoshaman et al. (2018)
- **Summary:** Introduces Quantum Boltzmann Machines in the latent space of VAEs to model complex probability distributions. Foundation for QVAE architectures.

### 3. ζ-QVAE - Mixed-State Latent Representations
- **File:** `2402.17749_Zeta_QVAE.pdf`
- **arXiv:** [2402.17749](https://arxiv.org/abs/2402.17749)
- **Title:** *ζ-QVAE: A Quantum Variational Autoencoder utilizing Regularized Mixed-state Latent Representations*
- **Authors:** (2024)
- **Summary:** Fully quantum VAE framework handling mixed states, crucial for NISQ devices. Directly relevant to QZero's QI-VAE architecture.

---

## 🛡️ QML for Cybersecurity

### 4. QML-IDS - Quantum Intrusion Detection
- **File:** `2410.16308_QML_IDS.pdf`
- **arXiv:** [2410.16308](https://arxiv.org/abs/2410.16308)
- **Title:** *QML-IDS: Quantum Machine Learning Intrusion Detection System*
- **Authors:** Abreu et al. (2024)
- **Summary:** Combines classical methods with VQCs, QSVMs, and QCNNs for enhanced intrusion detection. Benchmarks on standard IDS datasets.

### 5. QML Cybersecurity Taxonomy
- **File:** `2512.15286_QML_Cybersecurity_Taxonomy.pdf`
- **arXiv:** [2512.15286](https://arxiv.org/abs/2512.15286)
- **Title:** *Quantum Machine Learning for Cybersecurity: A Taxonomy and Future Directions*
- **Authors:** (2024)
- **Summary:** Comprehensive survey covering QSVM, QNN, QCNN, QGAN for intrusion detection, malware analysis, federated learning, and cloud security. Excellent reference.

### 6. QML for PCA-based IDS
- **File:** `2502.11173_QML_Cybersecurity_PCA_IDS.pdf`
- **arXiv:** [2502.11173](https://arxiv.org/abs/2502.11173)
- **Title:** *Evaluating the Potential of Quantum Machine Learning in Cybersecurity: A Case-Study on PCA-based Intrusion Detection Systems*
- **Authors:** (2025)
- **Summary:** Explores quantum advantage in ML for cybersecurity, focusing on PCA-based IDS. Methodology to quantify future QML impact.

### 7. Cyber Threat Detection - Quantum Computing
- **File:** `2512.18493_Cyber_Threat_Quantum.pdf`
- **arXiv:** [2512.18493](https://arxiv.org/abs/2512.18493)
- **Title:** *Cyber Threat Detection Enabled by Quantum Computing*
- **Authors:** (2024)
- **Summary:** Hybrid MLP encoder + quantum heads (QSVM, VQC). Evaluated on NSL-KDD for intrusion detection. Analyzes qubit/depth trade-offs.

### 8. Quantum AI for Malware Detection
- **File:** `2509.05370_Quantum_AI_Malware.pdf`
- **arXiv:** [2509.05370](https://arxiv.org/abs/2509.05370)
- **Title:** *Quantum AI Algorithm Development for Enhanced Cybersecurity: A Hybrid Approach to Malware Detection*
- **Authors:** Joshi et al. (2025)
- **Summary:** Applies quantum ML to malware detection with hybrid classical-quantum architecture.

### 9. QML for Stealth Attack Detection
- **File:** `2601.00873_QML_Stealth_Attack.pdf`
- **arXiv:** [2601.00873](https://arxiv.org/abs/2601.00873)
- **Title:** *Quantum Machine Learning Approaches for Coordinated Stealth Attack Detection in Distributed Generation Systems*
- **Authors:** (2025)
- **Summary:** QML for detecting coordinated stealth attacks in microgrids. Novel application of quantum methods to critical infrastructure.

---

## 🎯 Zero-Day Attack Detection

### 10. Zero-Day Detection with MLP + XAI
- **File:** `2501.16638_Zero_Day_MLP_XAI.pdf`
- **arXiv:** [2501.16638](https://arxiv.org/abs/2501.16638)
- **Title:** *Analysis of Zero Day Attack Detection Using MLP and XAI*
- **Authors:** (2025)
- **Summary:** ML/DL analysis for zero-day detection with explainable AI. Addresses interpretability of detection models.

### 11. XAI-based Zero-Day Detection - Smart Community
- **File:** `2408.02921_XAI_Zero_Day_Smart_Community.pdf`
- **arXiv:** [2408.02921](https://arxiv.org/abs/2408.02921)
- **Title:** *Interoperability and Explicable AI-based Zero-Day Attacks Detection Process in Smart Community*
- **Authors:** (2024)
- **Summary:** Zero-day detection for smart communities using explainable AI. Cross-platform interoperability focus.

### 12. Zero-Day Detection with Outlier-based Deep Learning
- **File:** `2006.15344_Zero_Day_Outlier_DeepLearning.pdf`
- **arXiv:** [2006.15344](https://arxiv.org/abs/2006.15344)
- **Title:** *Towards an Effective Zero-Day Attack Detection Using Outlier-Based Deep Learning Techniques*
- **Authors:** Hindy et al. (2020)
- **Summary:** Outlier-based deep learning for unseen attack detection. Establishes baseline for anomaly-based approaches.

---

## 🦠 Ransomware & VQC

### 13. UGRansome with Random Forest
- **File:** `2404.12855_UGRansome_Random_Forest.pdf`
- **arXiv:** [2404.12855](https://arxiv.org/abs/2404.12855)
- **Title:** *Ransomware Detection and Classification Using Random Forest: A Case Study with the UGRansome2024 Dataset*
- **Authors:** (2024)
- **Summary:** Classical ML baseline using Random Forest on UGRansome dataset. Direct comparison target for QZero.

### 14. Hybrid VQC for Ransomware Detection
- **File:** `2509.07924_Hybrid_VQC_Ransomware.pdf`
- **arXiv:** [2509.07924](https://arxiv.org/abs/2509.07924)
- **Title:** *A Non-Monotonic Relationship: An Empirical Analysis of Hybrid Quantum Classifiers for Unseen Ransomware Detection*
- **Authors:** (2025)
- **Summary:** VQC + PCA for ransomware detection. Analyzes quantum classifier behavior on high-dimensional security data. **Highly relevant to QZero**.

### 15. PhishVQC - Phishing Detection
- **File:** `2503.01799_PhishVQC.pdf`
- **arXiv:** [2503.01799](https://arxiv.org/abs/2503.01799)
- **Title:** *PhishVQC: Optimizing Phishing URL Detection with Correlation Based Feature Selection and Variational Quantum Classifier*
- **Authors:** (2025)
- **Summary:** VQC for phishing detection using RealAmplitude and EfficientSU2 ansätze. Feature selection methodology applicable to QZero.

---

## 📊 Quick Reference by Topic

| Topic | Papers |
|-------|--------|
| **QSVM** | 1, 4, 5, 7 |
| **QVAE/QI-VAE** | 2, 3 |
| **VQC** | 4, 7, 14, 15 |
| **Zero-Day Detection** | 10, 11, 12 |
| **Ransomware** | 13, 14 |
| **UGRansome Dataset** | 13 |
| **Taxonomy/Survey** | 5 |
| **Hybrid Classical-Quantum** | 3, 4, 7, 8, 14 |

---

*Last updated: 2025-01-29*
*Total papers: 15*
