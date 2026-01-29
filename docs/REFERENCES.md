# References & Bibliography

This project builds upon cutting-edge research in Quantum Machine Learning and Cybersecurity. Below are the key papers and datasets used.

## 📄 Key Papers

### 1. Quantum Support Vector Machines (QSVM)
*   **"Parameterised Quantum SVM with Data-Driven Entanglement for Zero-Day Exploit Detection"** (MDPI Computers, 2025)
    *   *Significance:* Demonstrates that QSVMs can achieve ~89% detection on zero-day attacks, outperforming some classical baselines in low-data regimes.
    *   [Link to Paper](https://www.mdpi.com/2073-431X/14/8/331)

*   **"Quantum support vector machine for big data classification"** (Rebentrost et al., Phys. Rev. Lett., 2014)
    *   *Significance:* The foundational paper proving exponential speedup for SVM on quantum computers (logarithmic time complexity).
    *   [arXiv:1307.0471](https://arxiv.org/abs/1307.0471)

### 2. Quantum Variational Autoencoders (QVAE)
*   **"Quantum Variational Autoencoder"** (Khoshaman et al., 2018)
    *   *Significance:* Introduces the concept of using Quantum Boltzmann Machines in the latent space of a VAE to model complex probability distributions.
    *   [arXiv:1802.05779](https://arxiv.org/abs/1802.05779)

*   **"$\zeta$-QVAE: A Quantum Variational Autoencoder utilizing Regularized Mixed-state Latent Representations"** (2024)
    *   *Significance:* A fully quantum VAE framework that handles mixed states, crucial for noisy intermediate-scale quantum (NISQ) devices.
    *   [arXiv:2402.17749](https://arxiv.org/abs/2402.17749)

## 📊 Datasets

### UGRansome (2018-2019)
*   **Description:** A dataset specifically designed for anomaly detection and zero-day threats, containing NetFlow data labeled with various ransomware families and "signature" vs "anomaly" classes.
*   **Source:** [Kaggle - UGRansome Dataset](https://www.kaggle.com/datasets/nkongolo/ugransome-dataset)
*   **Usage in QZero:** Used for training both the baseline classical models and the quantum feature extractors.

## 🛠️ Technologies & Frameworks

*   **Qiskit (IBM):** Main SDK for quantum circuit construction and simulation.
    *   [Documentation](https://qiskit.org/documentation/)
*   **PyTorch:** Used for the classical components of the hybrid Neural Networks (QI-VAE).
    *   [Qiskit Machine Learning Connector](https://qiskit.org/ecosystem/machine-learning/)
*   **FastAPI:** High-performance API framework for the production sidecar.

---
*Note: Some papers may require academic access.*
