# Benchmark pcaps propios: QSVM vs QI-VAE vs baselines clásicos

- **Fecha:** 2026-10-14T23:34:36
- **Duración del benchmark:** 1599.0s
- **Semilla fija:** 42 (todos los modelos y splits deterministas)
- **Python:** 3.11.2 | numpy 2.4.6 | scikit-learn 1.9.0 | qiskit 2.5.2 | qiskit-machine-learning 0.9.1 | torch 2.4.1+cpu

## Dataset

Flujos extraídos de los pcaps etiquetados propios (`data/synthetic-pcaps/`)
con `FlowExtractor` (14 features de flujo estilo UGRansome, los mismos que
usa producción). Etiquetas binarias: normal=0, cualquier ataque=1.

| Clase | Flujos |
|---|---|
| normal | 542 |
| ddos | 600 |
| bruteforce | 600 |
| exfiltration | 600 |
| malware | 600 |

## Protocolo

1. **LOATO** (leave-one-attack-type-out): 4 folds binarios; en cada fold se
   oculta un ataque completo (simula zero-day). Test = ataque oculto + flujos
   normales. El QI-VAE se entrena **solo con flujos normales** del train
   (detección por error de reconstrucción, como en producción).
2. **Split estratificado 80/20** (seed 42) como sanity check.
3. **Multiclase OVR** (5 clases) con random_forest y svm_rbf sobre el split.

- QSVM: kernel de fidelidad Qiskit, 4 qubits, PCA a 4 dimensiones y codificación
  en ángulos [0, π]. Por coste del kernel en CPU (~0.5 s/par de muestras), se entrena
  con máx. 120 muestras y se evalúa sobre 60 flujos de test
  submuestreados de forma estratificada con seed fija (resto de modelos: test completo).
- QI-VAE: 40 épocas, latente 4, hidden (64, 32), beta=1.0.
- Escalado StandardScaler ajustado solo en train en cada fold.

### LOATO — media±std sobre 4 folds (test F1)

Cada fold oculta ddos / bruteforce / exfiltration / malware por turnos.

| Modelo | F1 | Precision | Recall | ROC-AUC | Accuracy | Train (s) | Infer (s) |
|---|---|---|---|---|---|---|---|
| QSVM | 0.7111±0.0000 | 0.5517±0.0000 | 1.0000±0.0000 | 0.6210±0.1294 | 0.5667±0.0000 | 71.8022±6.1341 | 73.5399±11.9947 |
| QI-VAE | 0.1807±0.0365 | 0.4491±0.0609 | 0.1133±0.0250 | 0.5556±0.0633 | 0.4623±0.0161 | 119.8501±130.3912 | 0.0458±0.0412 |
| svm_linear | 0.7071±0.0000 | 0.5469±0.0000 | 1.0000±0.0000 | 0.5197±0.1571 | 0.5648±0.0000 | 0.3656±0.1079 | 0.0255±0.0049 |
| svm_rbf | 0.7071±0.0000 | 0.5469±0.0000 | 1.0000±0.0000 | 0.6249±0.1295 | 0.5648±0.0000 | 0.7131±0.1441 | 0.0787±0.0166 |
| random_forest | 0.7071±0.0000 | 0.5469±0.0000 | 1.0000±0.0000 | 0.6671±0.0972 | 0.5648±0.0000 | 0.4669±0.0649 | 0.0708±0.0184 |
| logistic_regression | 0.7071±0.0000 | 0.5469±0.0000 | 1.0000±0.0000 | 0.6669±0.0973 | 0.5648±0.0000 | 0.0212±0.0152 | 0.0007±0.0001 |
| knn | 0.7071±0.0000 | 0.5469±0.0000 | 1.0000±0.0000 | 0.5415±0.0000 | 0.5648±0.0000 | 0.0186±0.0219 | 0.0950±0.0263 |
| mlp | 0.7071±0.0000 | 0.5469±0.0000 | 1.0000±0.0000 | 0.6671±0.0972 | 0.5648±0.0000 | 0.4045±0.0209 | 0.0083±0.0064 |

### Split estratificado 80/20 — métricas del test

| Modelo | F1 | Precision | Recall | ROC-AUC | Accuracy | Train (s) | Infer (s) |
|---|---|---|---|---|---|---|---|
| QSVM | 0.8991 | 0.8167 | 1.0000 | 0.3395 | 0.8167 | 62.4854 | 67.7899 |
| QI-VAE | 0.1788 | 0.8421 | 0.1000 | 0.6178 | 0.2513 | 4.9213 | 0.0050 |
| svm_linear | 0.9014 | 0.8205 | 1.0000 | 0.6055 | 0.8217 | 0.2317 | 0.0094 |
| svm_rbf | 0.9014 | 0.8205 | 1.0000 | 0.4312 | 0.8217 | 0.5169 | 0.0282 |
| random_forest | 0.9014 | 0.8205 | 1.0000 | 0.6706 | 0.8217 | 0.4231 | 0.0610 |
| logistic_regression | 0.9014 | 0.8205 | 1.0000 | 0.6706 | 0.8217 | 0.0057 | 0.0006 |
| knn | 0.9014 | 0.8205 | 1.0000 | 0.5183 | 0.8217 | 0.0059 | 0.0676 |
| mlp | 0.9014 | 0.8205 | 1.0000 | 0.6701 | 0.8217 | 0.3498 | 0.0014 |

### F1 por ataque oculto (LOATO)

| Modelo | ddos | bruteforce | exfiltration | malware |
|---|---|---|---|---|
| QSVM | 0.711 | 0.711 | 0.711 | 0.711 |
| QI-VAE | 0.143 | 0.241 | 0.168 | 0.171 |
| svm_linear | 0.707 | 0.707 | 0.707 | 0.707 |
| svm_rbf | 0.707 | 0.707 | 0.707 | 0.707 |
| random_forest | 0.707 | 0.707 | 0.707 | 0.707 |
| logistic_regression | 0.707 | 0.707 | 0.707 | 0.707 |
| knn | 0.707 | 0.707 | 0.707 | 0.707 |
| mlp | 0.707 | 0.707 | 0.707 | 0.707 |

### Multiclase OVR (5 clases, split estratificado)

| Modelo | Accuracy | F1 macro |
|---|---|---|
| random_forest | 0.3311 | 0.1881 |
| svm_rbf | 0.3311 | 0.1881 |

## Veredicto

- Mejor modelo cuántico (F1 medio LOATO): **QSVM** = 0.7111
- Mejor baseline clásico: **svm_linear** = 0.7071
- QSVM usó kernel cuántico real: **SÍ**

El mejor modelo cuántico-inspirado iguala o supera al mejor baseline clásico en F1 medio bajo validación LOATO.

### Tiempos (referencia)

Los tiempos están en las tablas anteriores (train/infer en segundos, medias LOATO).
El dataset es pequeño (~2.9k flujos), por lo que los tiempos absolutos son bajos;
la comparación relativa entrenamiento cuántico vs clásico sí es representativa.

---
**Generado por:** `scripts/benchmark-pcaps.py` (ejecución real, sin datos inventados)
