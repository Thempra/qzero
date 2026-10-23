# Honest benchmark — QZero, 2026-10-14

This page exists because the public materials used to quote numbers that no script in this
repository produces. Everything below is traceable to a file you can open and re-run.

**Script:** `scripts/benchmark-pcaps.py`
**Corpus:** 5 labeled PCAPs in `data/synthetic-pcaps/` (600 packets each)
**Artifacts:**
- `model-performance-reports/benchmark-pcaps-2026-10-14T23-34-36.md` (human-readable, generated)
- `model-performance-reports/benchmark-pcaps-latest.json` (machine-readable, same run)
**Run:** 2026-10-14T23:34:36, seed 42, CPU only, Python 3.11.2, Qiskit 2.5.2, torch 2.4.1+cpu

## What was measured

| | |
|---|---|
| Flows extracted | **2 942** (normal 542, ddos 600, bruteforce 600, exfiltration 600, malware 600) |
| Features | 14 flow-level numeric features |
| Protocol 1 | LOATO — leave-one-attack-type-out, 4 folds, test = hidden attack + all normal |
| Protocol 2 | Stratified 80/20 split, single fold |
| Protocol 3 | Multiclass OVR (only random_forest and svm_rbf reported) |
| QSVM | 4 qubits, real quantum kernel (Qiskit `ZZFeatureMap` + `FidelityQuantumKernel`), training capped at 120 samples |

## LOATO, per fold

| Fold (hidden attack) | QSVM F1 | QSVM ROC-AUC | QSVM infer | svm_linear F1 | svm_linear ROC-AUC | svm_linear infer |
|---|---|---|---|---|---|---|
| ddos | 0.7111 | 0.5664 | 92.86 s | 0.7071 | 0.6106 | 0.0229 s |
| bruteforce | 0.7111 | 0.8426 | 74.27 s | 0.7071 | 0.2477 | 0.0340 s |
| exfiltration | 0.7111 | 0.5162 | 64.00 s | 0.7071 | 0.6087 | 0.0226 s |
| malware | 0.7111 | 0.5586 | 63.02 s | 0.7071 | 0.6119 | 0.0226 s |
| **mean** | **0.7111** | 0.6210 | — | **0.7071** | 0.5197 | — |

Source: `benchmark-pcaps-latest.json` → `results.loto`.

## Stratified 80/20 split (the only non-degenerate test)

| Model | F1 | Precision | Recall | ROC-AUC |
|---|---|---|---|---|
| QSVM | 0.8991 | 0.8167 | 1.0000 | **0.3395** |
| QI-VAE | 0.1788 | 0.8421 | 0.1000 | 0.6178 |
| svm_linear | 0.9014 | 0.8205 | 1.0000 | 0.6055 |
| random_forest | 0.9014 | 0.8205 | 1.0000 | 0.6706 |

The QSVM's ROC-AUC of **0.3395 is worse than a coin flip**. Its F1 of 0.8991 comes entirely
from predicting the majority class 100% of the time.

## Why the LOATO F1 is not a detection score

`accuracy 0.5667 · precision 0.5517 · recall 1.0000 · F1 0.7111`

Those four numbers are **identical in all four QSVM folds and all four svm_linear folds**.
Recall 1.00 with precision equal to the class prevalence means both models predict POSITIVE
on 100% of flows. F1 is then a deterministic function of the fold's class mix — it measures
the composition of the split, not the ability to detect anything.

## The bank itself does not discriminate

Verified by re-extracting the flows from the shipped PCAPs with
`qzero.preprocessing.flow_extractor.FlowExtractor`:

| Property | Value |
|---|---|
| Flows | 2 942 |
| Unique rows (all 14 features) | **48** |
| Zero-variance features | **6 of 14** (`total_bwd_packets`, `total_length_bwd_packets`, `bwd_packet_length_mean`, `bwd_iat_mean`, `bwd_psh_flags`, `fwd_urg_flags`) |
| Flows with ≤1 forward packet | **98.47%** (2 897 / 2 942) |
| Distinct `flow_duration` values | 46 |

These are synthetic captures generated packet-by-packet; there is no bidirectional
conversation structure, so almost every flow is a single packet with no response. A
benchmark on this corpus cannot rank two classifiers by detection ability. **It must be
rebuilt on real traffic before any model comparison is published again.**

## The four defensible figures

| # | Figure | Artifact |
|---|---|---|
| 1 | **2 942 flows** from 5 labeled PCAPs | `benchmark-pcaps-latest.json` → `flows_per_class`; `docs/assets/ledger.json` |
| 2 | **QSVM F1 0.7111 vs svm_linear 0.7071** — equal in practice, and degenerate (see above) | `benchmark-pcaps-latest.json` → `results.loto.*.*.f1` |
| 3 | **QI-VAE F1 0.1807** (LOATO mean of 0.1427 / 0.2409 / 0.1682 / 0.1711) — the deployed model is the weak one | `benchmark-pcaps-latest.json` → `results.loto.*["QI-VAE"].f1` |
| 4 | **Inference latency:** QI-VAE 0.005 s for 588 flows (~8.5 µs/flow); QSVM 92.86 s for 1 088 flows (~85 ms/flow) | `benchmark-pcaps-latest.json` → `inference_time_s` (validate against `test_size`) |

## Withdrawn claims

The following appeared in `docs/PRESENTATION.md`, `docs/PRESENTATION_SCRIPT.md`,
`README.md` and `docs/index.html`. **None is produced by any artifact in this repository.**
They have been removed:

- QSVM accuracy 93.2% / F1 0.92 / zero-day 85.7% / FPR 2.8%
- QI-VAE accuracy 91.5% / F1 0.91 / zero-day 88.2% / FPR 2.4%
- "+13–23% improvement in zero-day detection"
- "quantum advantage > 17%" / "+17% detection improvement"
- "16 050 flows/s"
- "sub-millisecond inference latency"
- Random Forest 89.2% / XGBoost 91.1% / Classical SVM 87.5% / MLP 90.3% baseline table —
  XGBoost is not even benchmarked by `scripts/benchmark-pcaps.py`

## Not verified / open

- Whether the QI-VAE is usable at all on real traffic. Its F1 0.1807 is measured on a
  degenerate bank; the number is honest but it is not evidence of detection capability.
- Zero-day detection and FPR on any representative corpus: **never measured**.
- The `retrain-20261014-2251.md` report shows higher F1s (svm_rbf 0.9574, qivae 0.1399) on
  5 000 *synthetic* samples. Those are train-on-synthetic / test-on-synthetic numbers and
  are not comparable to the PCAP benchmark. They are not cited in public materials.
- `qsvm.pkl` does not exist in the repo; the QSVM cannot be loaded for inference from a
  shipped artifact. It is a benchmark-only path.
- The 95% CI ±0.115 quoted for the QSVM/svm_linear difference is a binomial-proportion
  approximation on n=60 informative comparisons, not a bootstrap. Treat it as an order of
  magnitude.
