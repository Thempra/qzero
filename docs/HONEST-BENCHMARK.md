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

## Mediciones reproducibles (2026-10-23)

Esta sección añade dos benchmarks que **sí** producen las cifras que publican, con el JSON
crudo al lado. Sustituyen a cualquier número de rendimiento citado antes: los anteriores
(`16 050 flujos/s`, `sub-millisecond inference`) no los generaba ningún script y siguen
retirados.

### Hardware donde se midió

| | |
|---|---|
| CPU | QEMU Virtual CPU version 2.5+ — **4 vCPU** (máquina virtualizada) |
| RAM | 3,82 GB |
| SO | Linux 6.1.0-51-amd64 (glibc 2.36) |
| Python | 3.11.2 |
| torch | 2.4.1+cpu (`torch_num_threads = 4`) |
| numpy | 2.4.6 |

Es una VM de 4 vCPU: **no es hardware de producción ni un servidor dedicado**. Las cifras
absolutas son de esta máquina.

### 1. Rendimiento — `scripts/bench_throughput.py`

```bash
.venv/bin/python scripts/bench_throughput.py --flows 2000 --latency-flows 500 --repeat 3 \
    --model-cache /tmp/qzcache/m.pkl
```

Artefacto: `model-performance-reports/bench-throughput-latest.json`
(ejecución `bench-throughput-2026-10-23T10-49-19.json`).

| Métrica | Valor medido | Clave del JSON |
|---|---|---|
| Flujos extraídos del banco de prueba | 1 957 flujos / 13 908 paquetes | `extraction.flows` |
| **Extracción + inferencia (núcleo, sin I/O)** | **2 059,8 flujos/s** (15 053 pkt/s) | `repeats.flows_per_s_end_to_end` |
| Solo extracción de features | 2 302,4 flujos/s | `repeats.flows_per_s_extraction` |
| Solo inferencia (lotes de 256) | 47 437,8 flujos/s | `repeats.flows_per_s_infer_only` |
| **pcap existente → scores (lectura incluida)** | **326,2 flujos/s** | `repeats.flows_per_s_pcap_to_scores` |
| Latencia por flujo p50 (batch=1) | **1,407 ms** | `inference_latency_per_flow.p50_ms` |
| Latencia por flujo p95 | 1,884 ms | `inference_latency_per_flow.p95_ms` |
| **Latencia por flujo p99** | **2,697 ms** | `inference_latency_per_flow.p99_ms` |
| Latencia por flujo max | 3,718 ms | `inference_latency_per_flow.max_ms` |
| CPU | 102,3 % de un core (25,6 % de la máquina) | `end_to_end.resources` |
| RSS pico | 590 MB | `repeats.rss_mb_peak` |

Tres repeticiones, se publica la **mediana** (`repeats.statistic = median_of_repeats`); los
percentiles se calculan sobre las 1 500 muestras agrupadas. Load average antes de medir:
0,87 con 4 cores; `load_average.contaminated = false`. El script **aborta** si detecta
carga ajena (a menos que se pase `--allow-busy`, que deja marca en el JSON).

El 96 % del tiempo del pipeline es extracción de features (`extract_share_pct`), no
inferencia. La inferencia es barata; el cuello de botella es Scapy.

#### Comparación con las cifras retiradas

| Cifra retirada | Medido aquí | Factor |
|---|---|---|
| 16 050 flujos/s | 2 059,8 flujos/s (extracción+inferencia) | **7,8× peor** |
| "sub-millisecond inference" | p50 = 1,407 ms (ningún percentil baja de 1 ms) | **1,4× por encima de 1 ms** |

Aun así, 2 059,8 flujos/s sigue siendo una cifra **favorable** y hay que leerla con cuidado:
son flujos sintéticos de un solo paquete, sin I/O de pcap y sin concurrencia. El número que
ve un operador que abre un pcap es **326,2 flujos/s**, 6,3× menor, porque `rdpcap` domina.

#### Qué NO mide este script

- Gbps de red sostenidos: **NO MEDIDO** — no hay NIC dedicada ni permisos de captura en esta
  VM; una captura en loopback mediría la pila local, no el producto.
- Drops del kernel en captura: **NO MEDIDO** — requiere `af_packet` con privilegios y NIC real.
- Throughput con el modelo desplegado: **NO MEDIDO** — `models/qivae.pkl` no está publicado
  en el repo, así que el script entrena un QI-VAE de la misma arquitectura (declarado en
  `model.source = trained-in-bench`).
- Concurrencia multi-hilo/multi-flujo: **NO MEDIDO** — un proceso, un hilo de inferencia.
- Latencias de red o tiempo entre llegada del paquete y scoring: fuera del alcance.

### 2. Detección — `scripts/bench_detection.py`

```bash
.venv/bin/python scripts/bench_detection.py --epochs 40
```

Artefacto: `model-performance-reports/bench-detection-latest.json`.

| Propiedad del banco | Medido | Umbral del veredicto |
|---|---|---|
| Flujos | 2 942 | — |
| Filas únicas (14 features) | **48 (1,63 %)** | ≥ 5 % |
| Features con varianza cero | **6 de 14** | ≤ 2 |
| Flujos con ≤1 paquete forward | **98,47 %** | ≤ 50 % |
| Mejor stump de 1 feature | accuracy **0,8334** (`flow_duration`) | gap ≤ 0,05 |

Matriz de confusión completa (QI-VAE, test = 589 flujos) y baseline trivial:

| | TN | FP | FN | TP | Accuracy | F1 | ROC-AUC |
|---|---|---|---|---|---|---|---|
| QI-VAE | 100 | 9 | 428 | 52 | **0,2581** | 0,1922 | 0,5635 |
| Baseline "siempre clase mayoritaria" | 0 | 109 | 0 | 480 | **0,8149** | 0,8980 | — |

**El baseline trivial gana al modelo por 56 puntos de accuracy.** El modelo tiene recall
0,108: detecta 52 de 480 anomalías. Y un solo feature (`flow_duration`) alcanza 0,8334 de
accuracy, por encima del modelo y casi del baseline, porque la etiqueta está codificada en
el tamaño/patrón del paquete en `scripts/generate-synthetic-pcaps-v2.py`.

> **Reproducibilidad parcial.** Dos ejecuciones con la misma semilla (42) y las mismas 40
> épocas dieron accuracy 0,2547 y 0,2581 (TN/FP/FN/TP: 100/9/430/50 y 100/9/428/52). El
> entrenamiento de torch no es determinista bit a bit en esta VM. La variación es de ±0,4
> puntos de accuracy y **no cambia ninguna conclusión**: en ambas el baseline trivial gana
> por más de 55 puntos y el veredicto es `degenerate: true`. Los números del banco (48
> filas únicas, 6 features de varianza cero, 98,47 % de un paquete) son idénticos en ambas.

El script emite su propio veredicto en `verdict.statement`:
`BANCO DEGENERADO: los números de detección de este JSON NO permiten afirmar capacidad de
detección ni comparar clasificadores.`

#### Qué NO mide el benchmark de detección

- Detección sobre tráfico benigno real: **NO MEDIDO** — no hay corpus real en el repo, y
  sin benigno real no hay FPR defendible.
- Zero-day: **NO MEDIDO** — el banco sintético no contiene ataques no vistos.
- Detección con el modelo de producción: **NO MEDIDO** — no existe `models/qivae.pkl`
  versionado; el script entrena uno y lo declara.

**Conclusión publicable: con este banco no se puede medir detección.** Cualquier F1 que
salga de él —incluido el 0,71 citado antes— mide la composición del split, no la capacidad
del modelo. Para publicar detección hace falta un corpus con tráfico benigno real y
conversación bidireccional.

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
