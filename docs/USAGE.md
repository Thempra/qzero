# QZero Usage Guide

> Practical examples and tutorials for the Quantum Zero-Day Detection Platform

## Table of Contents

- [Quick Start](#quick-start)
- [Data Preparation](#data-preparation)
- [Classical Baselines](#classical-baselines)
- [Quantum QSVM](#quantum-qsvm)
- [QI-VAE Anomaly Detection](#qi-vae-anomaly-detection)
- [Full Pipeline](#full-pipeline)
- [Dashboard](#dashboard)
- [API Usage](#api-usage)
- [Advanced Examples](#advanced-examples)
- [Best Practices](#best-practices)

---

## Quick Start

### 30-Second Demo

```bash
# Navigate to project
cd qzero

# Activate environment
source venv/bin/activate

# Run complete pipeline
python scripts/run_pipeline.py
```

This will:
1. Generate synthetic network traffic data
2. Train classical baseline models
3. Train quantum QSVM
4. Train QI-VAE for anomaly detection
5. Compare all results

---

## Data Preparation

### Generate Synthetic Data

Perfect for testing and development:

```python
from src.preprocessing.data_loader import generate_synthetic_data, DataLoader

# Generate 5000 samples
X, y = generate_synthetic_data(
    n_samples=5000,
    anomaly_ratio=0.15,      # 15% anomalies (zero-day)
    signature_ratio=0.20,    # 20% known attacks
    difficulty="medium"      # "easy", "medium", "hard"
)

print(f"Data shape: {X.shape}")
print(f"Class distribution: {y.value_counts().to_dict()}")
# Output:
# Data shape: (5000, 14)
# Class distribution: {0: 3250, 1: 750, 2: 1000}
# 0 = Normal, 1 = Zero-Day, 2 = Signature
```

### Load Real UGRansome Dataset

```python
from src.preprocessing.data_loader import DataLoader

loader = DataLoader()

# Load from data/raw/final(2).csv
X, y = loader.load_ugransome()

print(f"Samples: {len(X)}")
print(f"Features: {X.columns.tolist()}")
print(f"Labels: {loader.get_label_names()}")
# Output:
# Samples: ~149000
# Features: ['Protocol', 'Flag', 'Family', ...]
# Labels: {0: 'Normal', 1: 'Anomaly (Zero-Day)', 2: 'Signature (Known)', ...}
```

### Prepare Data for Training

```python
from src.preprocessing.data_loader import DataLoader, generate_synthetic_data

# Generate or load data
X, y = generate_synthetic_data(n_samples=2000)

# Initialize loader
loader = DataLoader()

# Prepare with train/val/test splits
data = loader.prepare_data(
    X, y,
    test_size=0.2,      # 20% test
    val_size=0.1,       # 10% validation (from train)
    binary=True         # Convert to binary classification
)

print(f"Training set: {data['X_train'].shape}")
print(f"Validation set: {data['X_val'].shape}")
print(f"Test set: {data['X_test'].shape}")
print(f"Feature names: {data['feature_names']}")
```

### Feature Engineering for Quantum

```python
from src.preprocessing.feature_engineering import FeatureEngineer

# Reduce to 4 features for 4-qubit circuits
engineer = FeatureEngineer(
    n_qubits=4,
    encoding_range=(0, 3.14159),  # [0, π] for rotation encoding
    reduction_method="pca"        # "pca", "mutual_info", "variance"
)

# Fit and transform
X_quantum = engineer.fit_transform(data['X_train'], data['y_train'])
X_test_quantum = engineer.transform(data['X_test'])

print(f"Original: {data['X_train'].shape[1]} features")
print(f"Quantum-ready: {X_quantum.shape[1]} features")
print(f"Value range: [{X_quantum.min():.4f}, {X_quantum.max():.4f}]")

# Check explained variance (PCA)
importance = engineer.get_feature_importance()
if importance is not None:
    print(f"PCA explained variance: {importance.sum():.2%}")
```

---

## Classical Baselines

### Train a Single Model

```python
from src.classical.baseline import ClassicalBaseline

# Available models: svm_linear, svm_rbf, random_forest, 
#                   gradient_boosting, logistic_regression, knn, mlp

# Train Random Forest
rf = ClassicalBaseline("random_forest")
train_time = rf.fit(data['X_train'], data['y_train'])

# Evaluate
result = rf.evaluate(data['X_test'], data['y_test'], train_time)

print(f"Model: {result.name}")
print(f"Accuracy: {result.accuracy:.4f}")
print(f"Precision: {result.precision:.4f}")
print(f"Recall: {result.recall:.4f}")
print(f"F1 Score: {result.f1:.4f}")
print(f"ROC-AUC: {result.roc_auc:.4f}")
print(f"Training time: {result.train_time:.2f}s")
print(f"Confusion Matrix:\n{result.confusion_matrix}")
```

### Compare All Baselines

```python
from src.classical.baseline import run_all_baselines, print_comparison_table

# Run all models
results = run_all_baselines(
    data['X_train'], data['y_train'],
    data['X_test'], data['y_test'],
    models=["random_forest", "svm_rbf", "gradient_boosting", "mlp"]
)

# Print comparison table
print_comparison_table(results)

# Get best model
best = max(results, key=lambda r: r.f1)
print(f"\nBest model: {best.name} (F1: {best.f1:.4f})")
```

**Example Output:**
```
================================================================================
CLASSICAL BASELINE COMPARISON
================================================================================
Model                     Accuracy   Precision     Recall         F1    ROC-AUC
--------------------------------------------------------------------------------
gradient_boosting           0.9150      0.9162     0.9150     0.9148     0.9685
random_forest               0.9100      0.9115     0.9100     0.9098     0.9652
mlp                         0.8925      0.8942     0.8925     0.8918     0.9523
svm_rbf                     0.8750      0.8778     0.8750     0.8742     0.9412
================================================================================
```

---

## Quantum QSVM

### Basic QSVM Training

```python
from src.quantum.qsvm import QSVM, QSVMConfig
from src.preprocessing.feature_engineering import FeatureEngineer

# Prepare quantum-ready features (must match n_qubits)
engineer = FeatureEngineer(n_qubits=4)
X_train_q = engineer.fit_transform(data['X_train'], data['y_train'])
X_test_q = engineer.transform(data['X_test'])

# Configure QSVM
config = QSVMConfig(
    n_qubits=4,                    # Number of qubits
    feature_map_type="ZZ",         # Feature map: Z, ZZ, ZZZ, PAULI
    feature_map_reps=2,            # Circuit repetitions
    entanglement="linear",         # Entanglement pattern
    max_samples_quantum=200,       # Limit for speed
    use_classical_fallback=True    # Fall back to RBF if quantum fails
)

# Create and train QSVM
qsvm = QSVM(config)
train_time = qsvm.fit(X_train_q[:200], data['y_train'][:200])

# Predict
y_pred = qsvm.predict(X_test_q)

# Evaluate
result = qsvm.evaluate(X_test_q, data['y_test'], train_time)

print(f"Used quantum: {result.used_quantum}")
print(f"Accuracy: {result.accuracy:.4f}")
print(f"F1 Score: {result.f1_score:.4f}")
print(f"Training time: {result.train_time:.2f}s")
print(f"Kernel computation time: {result.kernel_computation_time:.2f}s")
```

### Comparing Quantum vs Classical

```python
from src.quantum.qsvm import compare_quantum_classical

quantum_result, classical_result = compare_quantum_classical(
    X_train_q[:100], data['y_train'][:100],
    X_test_q[:50], data['y_test'][:50],
    n_qubits=4
)

print("\n=== Comparison ===")
print(f"Quantum QSVM:  Acc={quantum_result.accuracy:.4f}, F1={quantum_result.f1_score:.4f}")
print(f"Classical SVM: Acc={classical_result.accuracy:.4f}, F1={classical_result.f1_score:.4f}")

advantage = (quantum_result.f1_score - classical_result.f1_score) / classical_result.f1_score * 100
print(f"Quantum advantage: {advantage:+.2f}%")
```

### Different Feature Maps

```python
from src.quantum.feature_maps import FeatureMapType, create_feature_map, get_feature_map_info

# Create different feature maps
for fm_type in [FeatureMapType.Z, FeatureMapType.ZZ, FeatureMapType.PAULI]:
    fm = create_feature_map(n_qubits=4, feature_map_type=fm_type, reps=2)
    info = get_feature_map_info(fm)
    
    print(f"\n{fm_type.value.upper()} Feature Map:")
    print(f"  Qubits: {info['n_qubits']}")
    print(f"  Depth: {info['depth']}")
    print(f"  Parameters: {info['n_parameters']}")
    print(f"  Gates: {info['gate_counts']}")
```

---

## QI-VAE Anomaly Detection

### Basic Training

```python
from src.quantum.qivae import QIVAE, QIVAEConfig

# Configure QI-VAE
config = QIVAEConfig(
    input_dim=data['X_train'].shape[1],  # 14 features
    latent_dim=4,                         # Latent space size
    hidden_dims=(64, 32),                 # Encoder/decoder layers
    epochs=50,                            # Training epochs
    batch_size=32,                        # Batch size
    learning_rate=1e-3,                   # Learning rate
    beta=1.0,                             # KL divergence weight
    anomaly_threshold_percentile=95.0     # Threshold percentile
)

# Create QI-VAE
qivae = QIVAE(config)

# Train on NORMAL data only (unsupervised anomaly detection)
normal_mask = data['y_train'] == 0
X_train_normal = data['X_train'][normal_mask]

print(f"Training on {len(X_train_normal)} normal samples...")
train_time = qivae.fit(X_train_normal, verbose=True)
```

### Anomaly Detection

```python
# Get anomaly scores (reconstruction error)
anomaly_scores = qivae.predict_anomaly_scores(data['X_test'])

print(f"Score range: [{anomaly_scores.min():.4f}, {anomaly_scores.max():.4f}]")
print(f"Threshold: {qivae.anomaly_threshold:.4f}")

# Binary predictions
predictions = qivae.predict(data['X_test'])
print(f"Detected anomalies: {predictions.sum()} / {len(predictions)}")

# Evaluate
result = qivae.evaluate(data['X_test'], data['y_test'], train_time)

print(f"\n=== QI-VAE Results ===")
print(f"Accuracy:  {result.accuracy:.4f}")
print(f"Precision: {result.precision:.4f}")
print(f"Recall:    {result.recall:.4f}")
print(f"F1 Score:  {result.f1_score:.4f}")
```

### Analyze Latent Space

```python
import matplotlib.pyplot as plt
import numpy as np

# Encode test samples to latent space
z_test = qivae.encode(data['X_test'])

# Visualize (first 2 dimensions)
plt.figure(figsize=(10, 6))
scatter = plt.scatter(
    z_test[:, 0], z_test[:, 1],
    c=data['y_test'],
    cmap='coolwarm',
    alpha=0.7
)
plt.colorbar(scatter, label='Class (0=Normal, 1=Anomaly)')
plt.xlabel('Latent Dim 1')
plt.ylabel('Latent Dim 2')
plt.title('QI-VAE Latent Space Visualization')
plt.savefig('latent_space.png')
plt.show()
```

---

## Full Pipeline

### Run Complete Experiment

```python
from src.preprocessing.data_loader import generate_synthetic_data, DataLoader
from src.preprocessing.feature_engineering import FeatureEngineer
from src.classical.baseline import run_all_baselines, print_comparison_table
from src.quantum.qsvm import QSVM, QSVMConfig
from src.quantum.qivae import QIVAE, QIVAEConfig
from src.evaluation.metrics import evaluate_zero_day_detection

# 1. Generate data
print("📊 Generating data...")
X, y = generate_synthetic_data(n_samples=3000, difficulty="medium")
loader = DataLoader()
data = loader.prepare_data(X, y, binary=True)

# 2. Classical baselines
print("\n🤖 Training classical models...")
classical_results = run_all_baselines(
    data['X_train'], data['y_train'],
    data['X_test'], data['y_test']
)
print_comparison_table(classical_results)

# 3. QSVM
print("\n⚛️ Training QSVM...")
engineer = FeatureEngineer(n_qubits=4)
X_train_q = engineer.fit_transform(data['X_train'], data['y_train'])
X_test_q = engineer.transform(data['X_test'])

qsvm = QSVM(QSVMConfig(n_qubits=4, max_samples_quantum=200))
qsvm_result = qsvm.fit_evaluate(
    X_train_q[:200], data['y_train'][:200],
    X_test_q, data['y_test']
)
print(f"QSVM: Acc={qsvm_result.accuracy:.4f}, F1={qsvm_result.f1_score:.4f}")

# 4. QI-VAE
print("\n🌌 Training QI-VAE...")
normal_mask = data['y_train'] == 0
qivae = QIVAE(QIVAEConfig(input_dim=data['X_train'].shape[1], epochs=30))
qivae_result = qivae.fit_evaluate(
    data['X_train'][normal_mask],
    data['X_test'],
    data['y_test'],
    verbose=False
)
print(f"QI-VAE: Acc={qivae_result.accuracy:.4f}, F1={qivae_result.f1_score:.4f}")

# 5. Final summary
print("\n" + "="*60)
print("FINAL RESULTS")
print("="*60)
best_classical = max(classical_results, key=lambda r: r.f1)
print(f"Best Classical: {best_classical.name} (F1={best_classical.f1:.4f})")
print(f"QSVM:          F1={qsvm_result.f1_score:.4f}")
print(f"QI-VAE:        F1={qivae_result.f1_score:.4f}")
```

---

## Dashboard

### Launch Streamlit Dashboard

```bash
# Start the dashboard
streamlit run app/dashboard.py

# With custom port
streamlit run app/dashboard.py --server.port 8501

# Access at http://localhost:8501
```

### Dashboard Features

1. **Data Tab**: Generate/load data, visualize distributions
2. **Classical Tab**: Train and compare classical models
3. **Quantum Tab**: Configure and run QSVM
4. **Results Tab**: Side-by-side comparison

---

## API Usage

### Start the API Server

```bash
# Development mode (with reload)
uvicorn src.api:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn src.api:app --host 0.0.0.0 --port 8000 --workers 4
```

### Analyze Traffic via API

```python
import requests

# Prepare CSV file
csv_data = """flow_duration,total_fwd_packets,total_bwd_packets,total_length_fwd_packets,total_length_bwd_packets,flow_bytes_per_sec,flow_packets_per_sec,fwd_packet_length_mean,bwd_packet_length_mean,fwd_iat_mean,bwd_iat_mean,fwd_psh_flags,bwd_psh_flags,fwd_urg_flags
500,10,8,1500,1200,3000,20,150,150,50,60,1,1,0
200,50,5,8000,500,15000,100,160,100,10,100,5,1,2
"""

# Save to file
with open("traffic.csv", "w") as f:
    f.write(csv_data)

# Send to API
with open("traffic.csv", "rb") as f:
    response = requests.post(
        "http://localhost:8000/analyze",
        files={"file": ("traffic.csv", f, "text/csv")}
    )

result = response.json()
print(f"Status: {result['status']}")
print(f"Anomaly Score: {result['quantum_anomaly_score']}")
print(f"Anomalies Detected: {result['anomalies_detected']}")
```

---

## Advanced Examples

### Custom Feature Map

```python
from qiskit import QuantumCircuit
from qiskit.circuit import Parameter

def custom_feature_map(n_qubits: int) -> QuantumCircuit:
    """Custom feature map for network traffic."""
    qc = QuantumCircuit(n_qubits)
    params = [Parameter(f"x[{i}]") for i in range(n_qubits)]
    
    # Hadamard layer
    for i in range(n_qubits):
        qc.h(i)
    
    # Encoding layer with RY
    for i, p in enumerate(params):
        qc.ry(p * 2, i)
    
    # Entanglement layer
    for i in range(n_qubits - 1):
        qc.cx(i, i + 1)
    
    # Second encoding with RZ
    for i, p in enumerate(params):
        qc.rz(p, i)
    
    return qc

# Use custom feature map
fm = custom_feature_map(4)
print(fm.draw())
```

### Ensemble Model

```python
import numpy as np
from src.classical.baseline import ClassicalBaseline
from src.quantum.qsvm import QSVM, QSVMConfig

class EnsembleDetector:
    """Combine classical and quantum predictions."""
    
    def __init__(self):
        self.models = {
            'rf': ClassicalBaseline('random_forest'),
            'gb': ClassicalBaseline('gradient_boosting'),
            'qsvm': QSVM(QSVMConfig(n_qubits=4))
        }
    
    def fit(self, X_classical, X_quantum, y):
        self.models['rf'].fit(X_classical, y)
        self.models['gb'].fit(X_classical, y)
        self.models['qsvm'].fit(X_quantum[:200], y[:200])
    
    def predict(self, X_classical, X_quantum):
        predictions = np.column_stack([
            self.models['rf'].predict(X_classical),
            self.models['gb'].predict(X_classical),
            self.models['qsvm'].predict(X_quantum)
        ])
        # Majority vote
        return (predictions.mean(axis=1) > 0.5).astype(int)

# Usage
ensemble = EnsembleDetector()
ensemble.fit(data['X_train'], X_train_q, data['y_train'])
y_ensemble = ensemble.predict(data['X_test'], X_test_q)
```

### Export Results

```python
import pandas as pd
import json
from datetime import datetime

def export_results(classical_results, qsvm_result, qivae_result, filename="results"):
    """Export experiment results."""
    
    # Prepare data
    results = {
        "timestamp": datetime.now().isoformat(),
        "classical": [r.to_dict() for r in classical_results],
        "qsvm": qsvm_result.to_dict(),
        "qivae": qivae_result.to_dict()
    }
    
    # Save JSON
    with open(f"{filename}.json", "w") as f:
        json.dump(results, f, indent=2)
    
    # Save CSV summary
    summary = pd.DataFrame([
        {"model": r.name, "accuracy": r.accuracy, "f1": r.f1, "type": "classical"}
        for r in classical_results
    ] + [
        {"model": "QSVM", "accuracy": qsvm_result.accuracy, 
         "f1": qsvm_result.f1_score, "type": "quantum"},
        {"model": "QI-VAE", "accuracy": qivae_result.accuracy,
         "f1": qivae_result.f1_score, "type": "quantum"}
    ])
    summary.to_csv(f"{filename}.csv", index=False)
    
    print(f"Results saved to {filename}.json and {filename}.csv")

# Usage
export_results(classical_results, qsvm_result, qivae_result)
```

---

## Best Practices

### 1. Data Preparation

- ✅ Always normalize/scale features before quantum encoding
- ✅ Use PCA to reduce to `n_qubits` dimensions
- ✅ Keep test set separate until final evaluation
- ❌ Don't train on anomalies for QI-VAE

### 2. QSVM Tips

- ✅ Start with small sample sizes (100-200)
- ✅ Use `use_classical_fallback=True` for reliability
- ✅ Prefer `ZZFeatureMap` for network data
- ❌ Don't use >8 qubits on simulators (too slow)

### 3. QI-VAE Tips

- ✅ Train on normal traffic only
- ✅ Set threshold at 95th percentile
- ✅ Use `beta=1.0` for balanced KL loss
- ❌ Don't use very deep networks (overfitting)

### 4. Production

- ✅ Use Docker for deployment
- ✅ Enable classical fallback
- ✅ Monitor anomaly score distributions
- ✅ Log all predictions for analysis
- ❌ Don't rely solely on quantum results

---

*Document Version: 1.0.0 | Last Updated: 2025*
