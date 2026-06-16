# QZero CLI

Simple command-line interface for running QZero detection and evaluation.

## Installation

```bash
# Activate virtual environment
cd /home/thempra/projects/qzero
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Train Models

Train classical baselines and quantum models with synthetic or real data.

```bash
# Train with default settings (1000 synthetic samples)
python qzero-cli.py train

# Train with fewer samples for faster testing
python qzero-cli.py train --samples 200 --epochs 10

# Train with real UGRansome dataset
python qzero-cli.py train --real-data

# Compare multiple classical models
python qzero-cli.py train --models random_forest,svm_rbf,logistic_regression

# Train with custom parameters
python qzero-cli.py train \
  --samples 1000 \
  --difficulty medium \
  --n-qubits 4 \
  --hidden-dims 64,32 \
  --epochs 50 \
  --batch-size 32 \
  --anomaly-threshold 95.0 \
  --output-file results.json
```

### Real-Time Detection

Run detection on streaming data.

```bash
# Detect with NetFlow stream (default)
python qzero-cli.py detect --stream netflow

# Detect with PCAP stream
python qzero-cli.py detect --stream pcap

# Detect with log stream
python qzero-cli.py detect --stream logs

# Use classical model instead of QI-VAE
python qzero-cli.py detect --stream netflow --model classical

# Custom number of samples
python qzero-cli.py detect --stream netflow --model qivae --max-samples 50
```

### Help

```bash
# Show all commands
python qzero-cli.py --help

# Show train command options
python qzero-cli.py train --help

# Show detect command options
python qzero-cli.py detect --help
```

## Output

### Training Output

```
============================================================
QZero Training & Evaluation
============================================================

Generating synthetic data (200 samples)...
Generated 200 samples with 14 features
Class distribution: Normal=170, Anomaly=30

Feature engineering...
Reduced to 4 features (for 4 qubits)
Train: 160 | Test: 40

============================================================
Classical Baselines
============================================================
Model                      Accuracy    Precision    Recall    F1       ROC-AUC
--------------------------------------------------------------------------------
random_forest              0.9500      0.9600       0.9250    0.9420   0.9800
svm_rbf                    0.9250      0.9400       0.8750    0.9060   0.9550
...
============================================================

============================================================
Quantum-Inspired VAE (QI-VAE)
============================================================
Training on 170 normal samples
Epoch 1/10: Loss: 0.3456, Val Loss: 0.3123
Epoch 2/10: Loss: 0.3124, Val Loss: 0.2891
...

============================================================
QI-VAE Results
============================================================
Training Loss:      0.2891
Validation Loss:    0.2673
Anomaly Threshold:  0.9543
Accuracy:           0.8750
Precision:          0.8500
Recall:             0.8250
F1 Score:           0.8375
Training Time:      12.34s
============================================================
```

### Detection Output

```
============================================================
QZero Real-Time Detection
============================================================

Stream: NetFlow (mock data)
Model: QI-VAE (4 qubits)

Processing 50 samples...

============================================================
Detection Statistics
============================================================
Total samples:     50
Anomalies:         7
Anomaly rate:      14.00%
Mean score:        0.723
Max score:         0.964
Critical alerts:   2
============================================================

Top 5 anomalies by score:
  1. Score: 0.9640 | Anomaly | CRITICAL
  2. Score: 0.8750 | Anomaly | HIGH
  3. Score: 0.8200 | Anomaly | HIGH
  4. Score: 0.6800 | Normal | MEDIUM
  5. Score: 0.5100 | Normal | LOW
```

## Parameters

### Training Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--samples` | 1000 | Number of samples to use |
| `--real-data` | False | Use real UGRansome dataset instead of synthetic |
| `--difficulty` | medium | Difficulty level for synthetic data |
| `--n-qubits` | 4 | Number of qubits for quantum models |
| `--hidden-dims` | 64,32 | Hidden layer dimensions for QI-VAE |
| `--epochs` | 50 | Training epochs |
| `--batch-size` | 32 | Batch size for training |
| `--anomaly-threshold` | 95.0 | Anomaly threshold percentile |
| `--models` | (all) | Classical models to run (comma-separated) |
| `--output-file` | (none) | Save results to JSON file |

### Detection Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--stream` | netflow | Stream type (netflow, pcap, logs) |
| `--model` | qivae | Model type (qivae, classical) |
| `--n-qubits` | 4 | Number of qubits for QI-VAE |
| `--max-samples` | 100 | Maximum samples to process |

## Examples

### Quick Start

```bash
# Train a model quickly for testing
python qzero-cli.py train --samples 200 --epochs 5

# Run a quick detection
python qzero-cli.py detect --stream netflow --max-samples 20
```

### Full Evaluation

```bash
# Train with real data and save results
python qzero-cli.py train \
  --real-data \
  --samples 500 \
  --epochs 50 \
  --output-file qzero_results.json
```

### Model Comparison

```bash
# Compare all classical baselines
python qzero-cli.py train --models random_forest,svm_rbf,logistic_regression,gradient_boosting,knn,mlp
```

## Integration

### Using Results in Python

```python
import json

# Load results
with open('qzero_results.json', 'r') as f:
    results = json.load(f)

# Access QI-VAE results
qivae = results['qivae']
print(f"QI-VAE F1 Score: {qivae['f1_score']}")
print(f"Training Time: {qivae['train_time']}s")

# Access classical results
classical = results['classical']
for model_result in classical:
    print(f"{model_result['name']}: {model_result['f1']:.4f}")
```

## Notes

- For real data, ensure `data/raw/final(2).csv` exists in the project directory
- QI-VAE training is faster when trained only on normal samples
- Quantum models (QSVM) are computationally expensive - use smaller samples for testing
- Default stream handlers generate mock data for demonstration