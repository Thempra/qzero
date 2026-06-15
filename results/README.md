# Benchmark Results

This directory contains benchmark results from `scripts/benchmark.py`.

## Format

Each file is named `benchmark_YYYYMMDD_HHMMSS.json` and contains:
- Config parameters used
- Classical baseline results (RF, SVM, GBM, MLP, etc.)
- QSVM results with quantum kernel metrics
- QI-VAE anomaly detection results
- Quantum advantage calculations

## Usage

```bash
# Run a new benchmark
python scripts/benchmark.py --samples 5000 --qubits 4

# Compare recent results
python scripts/benchmark.py --compare

# Custom configuration
python scripts/benchmark.py --samples 10000 --qsvm-samples 500 --qivae-epochs 100
```
