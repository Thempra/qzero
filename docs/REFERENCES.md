# References & Bibliography

This project builds upon cutting-edge research in Quantum Machine Learning and Cybersecurity. Below are the key papers and datasets used.

## 📄 Key Papers

### 1. Quantum Support Vector Machines (QSVM)
*   **"Parameterised Quantum SVM with Data-Driven Entanglement for Zero-Day Exploit Detection"** (MDPI Computers, 2025)
    *   *Significance:* Demonstrates that QSVMs can achieve ~89% detection on zero-day attacks, outperforming some classical baselines in low-data regimes.
    *   [Link to Paper](https://www.mdpi.com/2073-431X/14/8/331)

*   **"Quantum support vector machine for big data classification"** (Rebentrost et al., Phys. Rev. Lett., 2014)
    *   *Significance:* The foundational paper proving exponential speedup for SVM on quantum computers (logarithmic time complexity).
    *   [arXiv:1307.0471](https://arxiv.org/abs/1307.0471) | 📁 `docs/papers/1307.0471_Quantum_SVM_Big_Data.pdf`

### 2. Quantum Variational Autoencoders (QVAE)
*   **"Quantum Variational Autoencoder"** (Khoshaman et al., 2018)
    *   *Significance:* Introduces the concept of using Quantum Boltzmann Machines in the latent space of a VAE to model complex probability distributions.
    *   [arXiv:1802.05779](https://arxiv.org/abs/1802.05779) | 📁 `docs/papers/1802.05779_Quantum_VAE.pdf`

*   **"$\zeta$-QVAE: A Quantum Variational Autoencoder utilizing Regularized Mixed-state Latent Representations"** (2024)
    *   *Significance:* A fully quantum VAE framework that handles mixed states, crucial for noisy intermediate-scale quantum (NISQ) devices.
    *   [arXiv:2402.17749](https://arxiv.org/abs/2402.17749) | 📁 `docs/papers/2402.17749_Zeta_QVAE.pdf`

---

## 🛡️ QML for Cybersecurity (Additional Papers)

### 3. Intrusion Detection Systems
*   **"QML-IDS: Quantum Machine Learning Intrusion Detection System"** (Abreu et al., 2024)
    *   *Significance:* Combines VQCs, QSVMs, and QCNNs for enhanced intrusion detection. Direct comparison methodology for QZero.
    *   [arXiv:2410.16308](https://arxiv.org/abs/2410.16308) | 📁 `docs/papers/2410.16308_QML_IDS.pdf`

*   **"Evaluating the Potential of Quantum Machine Learning in Cybersecurity: A Case-Study on PCA-based Intrusion Detection Systems"** (2025)
    *   *Significance:* Quantifies future impact of fault-tolerant QML on network intrusion detection.
    *   [arXiv:2502.11173](https://arxiv.org/abs/2502.11173) | 📁 `docs/papers/2502.11173_QML_Cybersecurity_PCA_IDS.pdf`

*   **"Cyber Threat Detection Enabled by Quantum Computing"** (2024)
    *   *Significance:* Hybrid MLP encoder + QSVM/VQC heads. Evaluated on NSL-KDD for intrusion detection.
    *   [arXiv:2512.18493](https://arxiv.org/abs/2512.18493) | 📁 `docs/papers/2512.18493_Cyber_Threat_Quantum.pdf`

### 4. Surveys & Taxonomies
*   **"Quantum Machine Learning for Cybersecurity: A Taxonomy and Future Directions"** (2024)
    *   *Significance:* Comprehensive survey covering QSVM, QNN, QCNN, QGAN across intrusion detection, malware, federated learning, and cloud security.
    *   [arXiv:2512.15286](https://arxiv.org/abs/2512.15286) | 📁 `docs/papers/2512.15286_QML_Cybersecurity_Taxonomy.pdf`

### 5. Malware & Specific Threats
*   **"Quantum AI Algorithm Development for Enhanced Cybersecurity: A Hybrid Approach to Malware Detection"** (Joshi et al., 2025)
    *   *Significance:* Hybrid quantum-classical architecture for malware detection.
    *   [arXiv:2509.05370](https://arxiv.org/abs/2509.05370) | 📁 `docs/papers/2509.05370_Quantum_AI_Malware.pdf`

*   **"Quantum Machine Learning Approaches for Coordinated Stealth Attack Detection"** (2025)
    *   *Significance:* QML for detecting stealth attacks in distributed generation systems.
    *   [arXiv:2601.00873](https://arxiv.org/abs/2601.00873) | 📁 `docs/papers/2601.00873_QML_Stealth_Attack.pdf`

*   **"PhishVQC: Optimizing Phishing URL Detection with VQC"** (2025)
    *   *Significance:* VQC with RealAmplitude and EfficientSU2 ansätze for phishing detection. Feature selection methodology.
    *   [arXiv:2503.01799](https://arxiv.org/abs/2503.01799) | 📁 `docs/papers/2503.01799_PhishVQC.pdf`

---

## 🎯 Zero-Day Attack Detection

*   **"Analysis of Zero Day Attack Detection Using MLP and XAI"** (2025)
    *   *Significance:* ML/DL analysis with explainable AI for zero-day detection.
    *   [arXiv:2501.16638](https://arxiv.org/abs/2501.16638) | 📁 `docs/papers/2501.16638_Zero_Day_MLP_XAI.pdf`

*   **"Interoperability and Explicable AI-based Zero-Day Attacks Detection Process in Smart Community"** (2024)
    *   *Significance:* Zero-day detection for smart communities with cross-platform interoperability.
    *   [arXiv:2408.02921](https://arxiv.org/abs/2408.02921) | 📁 `docs/papers/2408.02921_XAI_Zero_Day_Smart_Community.pdf`

*   **"Towards an Effective Zero-Day Attack Detection Using Outlier-Based Deep Learning"** (Hindy et al., 2020)
    *   *Significance:* Establishes outlier-based deep learning baseline for unseen attack detection.
    *   [arXiv:2006.15344](https://arxiv.org/abs/2006.15344) | 📁 `docs/papers/2006.15344_Zero_Day_Outlier_DeepLearning.pdf`

---

## 🦠 Ransomware Detection

*   **"A Non-Monotonic Relationship: Hybrid Quantum Classifiers for Unseen Ransomware Detection"** (2025)
    *   *Significance:* VQC + PCA for ransomware detection. **Highly relevant to QZero architecture**.
    *   [arXiv:2509.07924](https://arxiv.org/abs/2509.07924) | 📁 `docs/papers/2509.07924_Hybrid_VQC_Ransomware.pdf`

*   **"Ransomware Detection and Classification Using Random Forest: UGRansome2024"** (2024)
    *   *Significance:* Classical ML baseline on UGRansome dataset. Direct comparison target.
    *   [arXiv:2404.12855](https://arxiv.org/abs/2404.12855) | 📁 `docs/papers/2404.12855_UGRansome_Random_Forest.pdf`

---

## 📊 Datasets

### UGRansome (2018-2019)
*   **Description:** A dataset specifically designed for anomaly detection and zero-day threats, containing NetFlow data labeled with various ransomware families and "signature" vs "anomaly" classes.
*   **Source:** [Kaggle - UGRansome Dataset](https://www.kaggle.com/datasets/nkongolo/ugransome-dataset)
*   **Original Paper:** [UGRansome1819: A Novel Dataset for Anomaly Detection and Zero-Day Threats](https://www.mdpi.com/2078-2489/12/10/405) (MDPI Information, 2021)
*   **Usage in QZero:** Used for training both the baseline classical models and the quantum feature extractors.

---

## 🛠️ Technologies & Frameworks

*   **Qiskit (IBM):** Main SDK for quantum circuit construction and simulation.
    *   [Documentation](https://qiskit.org/documentation/)
*   **PyTorch:** Used for the classical components of the hybrid Neural Networks (QI-VAE).
    *   [Qiskit Machine Learning Connector](https://qiskit.org/ecosystem/machine-learning/)
*   **FastAPI:** High-performance API framework for the production sidecar.

---

## 📁 Downloaded Papers

All papers are available in `docs/papers/`. See [`docs/papers/INDEX.md`](papers/INDEX.md) for a complete index with summaries.

**Total papers downloaded:** 15

---
*Note: Some papers may require academic access. arXiv papers are freely available.*
*Last updated: 2025-01-29*
