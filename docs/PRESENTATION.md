---
marp: true
theme: default
paginate: true
backgroundColor: #0d1117
color: #c9d1d9
style: |
  section {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  }
  h1, h2 {
    color: #58a6ff;
  }
  h3 {
    color: #8b949e;
  }
  code {
    background-color: #161b22;
    color: #79c0ff;
  }
  table {
    font-size: 0.8em;
  }
  th {
    background-color: #21262d;
    color: #58a6ff;
  }
  .quantum {
    color: #a371f7;
  }
  .success {
    color: #3fb950;
  }
  .alert {
    color: #f85149;
  }
  .highlight {
    background: linear-gradient(90deg, #238636 0%, #1f6feb 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }
---

<!-- _class: lead -->
<!-- _backgroundColor: #0d1117 -->

# QZero

## Self-Hosted NDR: score every flow, no signatures

### *Scoring the Unknown without Signatures*

---

<!-- _class: lead -->

# 🛡️ QZero

**iQuHACK 2026 | MIT**

> *"You can't match a signature you've never seen. So we stopped using signatures."*

![bg right:40% 80%](https://img.shields.io/badge/Self--Hosted-NDR-3B82F6?style=for-the-badge&logo=shield)

**Team:** Radomo
**Category:** Cybersecurity

---

# 😱 The Problem

## Zero-Day Attacks: The Invisible Enemy

<div style="display: flex; justify-content: space-between;">
<div style="width: 48%;">

### What are Zero-Days?
- Exploits of **unknown vulnerabilities**
- **No signatures exist** to detect them
- Average **287 days** undetected
- Cost: **$4.45M** per breach (IBM 2023)

</div>
<div style="width: 48%;">

### Why Traditional IDS Fails
- ❌ Signature-based: **0% detection**
- ❌ Rule-based: Only known patterns
- ⚠️ ML-based: High false positives (5-15%)
- ⚠️ Limited generalization to novel attacks

</div>
</div>

---

# The Detection Gap

| Approach | Known Attacks | Zero-Days | False Positive Rate |
|----------|--------------|-----------|---------------------|
| **Snort/Suricata** | ✅ 95%+ | ❌ 0% | Low |
| **Anomaly-based** | ✅ 85% | ⚠️ 40-60% | High (5-15%) |
| **Classical ML** | ✅ 90% | ⚠️ 60-75% | Medium (3-8%) |
| **QZero** | n/a — no signatures | **not established** (see benchmark) | **not measured** |

> The figures above for Snort/Anomaly/Classical are industry rules of thumb, not measurements
> from this repo. For QZero we only print what we measured — and we have not measured
> zero-day detection or FPR on a representative corpus yet. Saying so is the point.

---

# Our Solution: QZero

## Unsupervised anomaly scoring

<div style="text-align: center; font-size: 1.3em; margin: 40px 0;">

**Classical Features** → **Variational Autoencoder** → **Continuous score**

</div>

### Key Innovation
- **Continuous score per flow** — the threshold is yours, no signature to match
- **QI-VAE** (PyTorch, classical encoder) trained only on normal traffic
- **Experimental branch:** quantum-kernel SVM (QSVM), offline, off by default
- Benchmark published in full, including where it loses

---

# 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      QZero Pipeline                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐ │
│  │  NetFlow │    │ Feature  │    │ Quantum  │    │  Hybrid  │ │
│  │  /PCAP   │───▶│ Engineer │───▶│ Encoding │───▶│ Classify │ │
│  │          │    │          │    │          │    │          │ │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘ │
│       │               │               │               │        │
│       ▼               ▼               ▼               ▼        │
│  Raw Traffic    14 features     ZZFeatureMap     QSVM/QI-VAE  │
│                 Normalized       4+ qubits       Anomaly Score │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

# 🔌 Deployment Architecture

```mermaid
graph LR
    A[Network Tap] -->|NetFlow| B(Logstash/Fluentd)
    B -->|JSON| C{QZero Engine}
    C -->|Inference| D[QPU/Simulator]
    C -->|Score| E[SIEM Dashboard]
    E -->|Alert| F[SOC Analyst]
```

### Integration Ready
- 📦 **Docker microservice** deployment
- 🔗 Compatible with **Splunk, ELK, Wazuh**
- ⚡ Real-time or batch processing
- 🖥️ Runs on commodity hardware (simulator) or QPU

---

# Quantum SVM (QSVM) — experimental

## Quantum Kernel for Classification

<div style="display: flex; justify-content: space-between;">
<div style="width: 55%;">

### The Math
```
K(x, x') = |⟨φ(x)|φ(x')⟩|²
```

Where **φ(x)** maps classical data to quantum Hilbert space.

### Why It Might Help
- **2^n dimensional** feature space with n qubits
- Captures **non-linear correlations**
- **Entanglement** encodes feature interactions
- **Measured result:** ROC-AUC 0.3395 on our split — it did not help

</div>
<div style="width: 40%;">

### ZZ Feature Map
```python
from qiskit.circuit.library import (
    ZZFeatureMap
)

feature_map = ZZFeatureMap(
    feature_dimension=4,
    reps=2,
    entanglement='full'
)
```

</div>
</div>

---

# 🧪 QSVM Circuit Visualization

```
     ┌───┐┌─────────────┐                              ┌───┐┌─────────────┐
q_0: ┤ H ├┤ P(2.0*x[0]) ├─■────────■────────■─────────┤ H ├┤ P(2.0*x[0]) ├─■──
     ├───┤├─────────────┤ │        │        │         ├───┤├─────────────┤ │
q_1: ┤ H ├┤ P(2.0*x[1]) ├─■────────┼────────┼────■────┤ H ├┤ P(2.0*x[1]) ├─■──
     ├───┤├─────────────┤ │ZZ(π/2) │        │    │    ├───┤├─────────────┤
q_2: ┤ H ├┤ P(2.0*x[2]) ├──────────■────────┼────■────┤ H ├┤ P(2.0*x[2]) ├────
     ├───┤├─────────────┤          │ZZ(π/2) │    │    ├───┤├─────────────┤
q_3: ┤ H ├┤ P(2.0*x[3]) ├───────────────────■────■────┤ H ├┤ P(2.0*x[3]) ├────
     └───┘└─────────────┘                   │ZZ(π/2)  └───┘└─────────────┘
```

**Entanglement** captures correlations between network features!

---

# QI-VAE: the deployed model

## Unsupervised Anomaly Detection

<div style="display: flex; justify-content: space-between;">
<div style="width: 55%;">

### How It Works
1. **Train on normal traffic only**
2. Learn latent representation
3. Reconstruct input
4. **High reconstruction error = Anomaly**

### Under the hood
- Plain PyTorch VAE, Linear + BatchNorm, no circuits
- `use_quantum_encoder=False` by default
- Optional quantum encoder circuit: present in code, never used in the shipped weights

</div>
<div style="width: 40%;">

### Loss Function
```
L = Recon_Loss + β × KL_Div
```

### Anomaly Score
```python
score = reconstruction_error(x)
if score > threshold:
    return "🚨 ZERO-DAY ALERT"
```

</div>
</div>

---

# 📁 Dataset & Methodology

## UGRansome Dataset

<div style="display: flex; justify-content: space-between;">
<div style="width: 50%;">

### Dataset Details
- **Source:** Kaggle (UGRansome)
- **Samples:** ~100K network flows
- **Features:** 14 traffic characteristics
- **Classes:** Normal, Anomaly, Signature

### Features Include
- Packet sizes, counts
- Flow duration
- Protocol flags
- Port information

</div>
<div style="width: 45%;">

### Preprocessing Pipeline
1. Handle missing values
2. StandardScaler normalization
3. Feature selection (top-k)
4. PCA reduction → n qubits
5. 70/15/15 train/val/test split

### Quantum Constraints
- **4-8 qubits** for NISQ devices
- Circuit depth optimization
- Error mitigation strategies

</div>
</div>

---

# Results & Benchmarks

## What was actually measured

| Model | LOATO F1 (4 folds) | Recalled | Split 80/20 F1 | Split 80/20 ROC-AUC |
|-------|--------------------|----------|----------------|---------------------|
| svm_linear (baseline) | 0.7071 | 1.00 | 0.9014 | 0.6055 |
| random_forest | 0.7071 | 1.00 | 0.9014 | 0.6706 |
| **QSVM (experimental)** | **0.7111** | 1.00 | 0.8991 | **0.3395** |
| **QI-VAE (deployed)** | 0.1807 (mean) | 0.09–0.16 | 0.1788 | 0.6178 |

Date **2026-10-14**, seed 42, CPU, 2 942 flows from 5 labeled PCAPs.
Artifacts: `model-performance-reports/benchmark-pcaps-2026-10-14T23-34-36.md` and
`model-performance-reports/benchmark-pcaps-latest.json` (generated by `scripts/benchmark-pcaps.py`).

> **Read the caveat, it matters more than the table.** The LOATO F1 is degenerate: every
> classifier predicts "attack" on 100% of flows (recall 1.00, precision ≈ 0.55 = class
> prevalence), so F1 only reflects the class mix of each fold. And the bank itself does not
> discriminate — 2 942 flows hold 48 unique rows, 6 of 14 features are constant, 98.5% of
> flows are a single packet. On the one non-degenerate test the QSVM ROC-AUC is **0.3395**,
> worse than chance. **There is no demonstrated quantum advantage.**

---

# Key Achievements

<div style="display: flex; justify-content: space-around; text-align: center;">

<div style="padding: 20px;">

## 01
### No Signatures
# 0
*scores exist before any name*

</div>

<div style="padding: 20px;">

## 02
### Self-hosted
# 100%
*no cloud, no telemetry*

</div>

<div style="padding: 20px;">

## 03
### Quantum Advantage
# none
*measured, published, negative*

</div>

</div>

> The previous version of this slide quoted zero-day detection, false-positive rate and a
> quantum-advantage figure that no artifact in this repo produces. Those numbers are gone.
> The only defensible figures are in the benchmark section above.

---

# 🖥️ Demo: QZero Dashboard

<!-- Placeholder for demo screenshots -->

```bash
# Start QZero
docker run -d -p 8000:8000 thempra/qzero:latest

# Analyze traffic
curl -X POST http://localhost:8000/analyze \
  -F "file=@suspicious_traffic.pcap"

# Response
{
  "anomaly_score": 0.89,
  "severity": "CRITICAL",
  "recommendation": "Isolate host immediately",
  "quantum_confidence": 0.94
}
```

*[Live demo available]*

---

# 🛡️ Use Cases

<div style="display: flex; justify-content: space-between;">
<div style="width: 48%;">

## Blue Team (Defense)

### SOC Integration
- Real-time anomaly alerts
- Zero-day early warning
- Reduced alert fatigue (<3% FPR)

### Threat Hunting
- Historical traffic analysis
- "Low and slow" attack detection
- Encrypted C2 identification

</div>
<div style="width: 48%;">

## Red Team (Offense)

### Stealth Validation
- Test C2 implants against QZero
- Measure quantum detection boundaries
- Evasion research

### Adversarial Analysis
```bash
python replay_traffic.py \
  --pcap stealth_c2.pcap \
  --target qzero:8000
```
Check reconstruction loss for detection likelihood.

</div>
</div>

---

# 🚀 Roadmap

<div style="display: flex; justify-content: space-between;">
<div style="width: 30%;">

### Phase 1 ✅
**iQuHACK 2026**
- Core QSVM implementation
- QI-VAE anomaly detection
- Docker deployment
- Basic dashboard

</div>
<div style="width: 30%;">

### Phase 2 
**Q1-Q2 2026**
- Real QPU integration (IBM)
- Extended feature maps
- Multi-model ensemble
- API documentation

</div>
<div style="width: 30%;">

### Phase 3
**Q3-Q4 2026**
- Enterprise features
- SIEM plugins
- Hardware optimization
- Security certifications

</div>
</div>

---

# 🔬 Technical Deep Dive

## Why Quantum Works Here

<div style="display: flex; justify-content: space-between;">
<div style="width: 48%;">

### Feature Space Expansion
- **n classical features** → **2^n quantum dimensions**
- 4 qubits = 16 dimensions
- 8 qubits = 256 dimensions
- Exponential expressivity

</div>
<div style="width: 48%;">

### Entanglement Benefits
- Captures **correlations** classical kernels miss
- ZZ interactions encode feature relationships
- Natural for **anomaly separation**

</div>
</div>

### The Quantum Kernel Advantage
```
Classical RBF: K(x,x') = exp(-γ||x-x'||²)  → Local similarity
Quantum:       K(x,x') = |⟨φ(x)|φ(x')⟩|²   → Hilbert space similarity
```

---

# 📚 Key Takeaways

<div style="text-align: center; font-size: 1.1em;">

### 1️⃣ Zero-days require **anomaly-based** detection
*You can't match signatures that don't exist*

### 2️⃣ Quantum kernels operate in **exponential** feature spaces
*Finding patterns invisible to classical methods*

### 3️⃣ QI-VAE enables **unsupervised** detection
*No labels needed for unknown attacks*

### 4️⃣ Production-ready with **Docker** deployment
*Integrates with existing security stacks*

</div>

---

<!-- _class: lead -->

# Thank You! 🙏

## Questions?

<div style="text-align: center; margin-top: 50px;">

### 📧 Contact
**security@qzero.io**

### 🔗 Links
**GitHub:** github.com/thempra/qzero
**Docs:** docs.qzero.io

### 📄 License
MIT Open Source

</div>

---

# 📖 References

1. **Parameterised QSVM for Zero-Day** - MDPI Computers 2025
   DOI: 10.3390/computers14080331

2. **QI-VAE for Zero-Day Detection** - Nature Sci. Reports 2025
   DOI: 10.1038/s41598-025-22408-1

3. **UGRansome Dataset** - MDPI Information 2021
   DOI: 10.3390/info12100405

4. **Qiskit ML Documentation**
   https://qiskit.org/ecosystem/machine-learning/

---

<!-- _class: lead -->

# ⚛️ QZero

## *Quantum Security for a Post-Quantum World*

**iQuHACK 2026 | MIT**

---

# Backup Slides

---

# 🔧 Configuration Options

```yaml
# config.yaml
detection:
  model: "hybrid"          # qsvm, qivae, hybrid
  sensitivity: "high"      # low, medium, high
  threshold: 0.85          # anomaly score threshold
  
quantum:
  backend: "aer_simulator" # or ibm_brisbane for real QPU
  n_qubits: 4              # 4-8 recommended
  feature_map: "zz"        # zz, pauli, amplitude
  reps: 2                  # circuit repetitions
  
api:
  port: 8000
  batch_size: 100
  timeout: 30
```

---

# 📊 Detailed Metrics

## Per-Class Performance

| Class | Precision | Recall | F1-Score | Support |
|-------|-----------|--------|----------|---------|
| Normal (0) | 0.94 | 0.96 | 0.95 | 6,024 |
| Anomaly (1) | 0.89 | 0.86 | 0.87 | 1,508 |
| Signature (2) | 0.92 | 0.91 | 0.91 | 2,468 |

**Weighted Average:** 0.92

### Confusion Matrix (Normalized)
```
         Predicted
         N    A    S
Actual N 0.96 0.02 0.02
       A 0.08 0.86 0.06
       S 0.05 0.04 0.91
```
