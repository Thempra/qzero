# Implementación — honestidad de materiales públicos (Fase 0.9)

Rama `fase0/honestidad`, worktree `/home/hermes/qz-docs`. Sin commit, sin push.

## Tabla: cifra falsa → cifra real → artefacto

| Cifra publicada (falsa) | Dónde estaba | Cifra real | Artefacto que la respalda |
|---|---|---|---|
| QSVM 93,2% acc / F1 0.92 / 85,7% zero-day / FPR 2,8% | `docs/PRESENTATION.md:315` | LOATO F1 0.7111; split 80/20 acc 0.8167, F1 0.8991, ROC-AUC **0.3395** | `model-performance-reports/benchmark-pcaps-2026-10-14T23-34-36.md:46,57` |
| QI-VAE 91,5% / F1 0.91 / 88,2% zero-day / FPR 2,4% | `docs/PRESENTATION.md:316` | LOATO F1 **0.1807** (media de 0.1427/0.2409/0.1682/0.1711); split F1 0.1788 | idem `:48,58,71` |
| Baselines RF 89.2 / XGB 91.1 / SVM 87.5 / MLP 90.3 | `docs/PRESENTATION.md:311-314` | RF LOATO F1 0.7071; XGBoost **no existe** en el banco | `:49-51`, `scripts/benchmark-pcaps.py` (lista de modelos) |
| «mean F1, four folds» 0.569 / 0.566 | `docs/index.html:368` | **0.711 / 0.707** (las 0.569/0.566 eran las *accuracies* 0.5667/0.5648) | `benchmark-pcaps-latest.json` → `results.loto.*.f1` |
| «16 050 flows/s» | `docs/index.html:292,369` | Eliminada. Única latencia medida: QI-VAE 0.005 s / 588 flujos (~8,5 µs/flujo) | `benchmark-pcaps-latest.json` → `results.split.strat_80_20["QI-VAE"].inference_time_s` |
| «sub-millisecond inference latency» | `README.md:31` | ~8,5 µs/flujo en QI-VAE; QSVM ~85 ms/flujo (92,86 s / 1 088) | mismo JSON; error era ~85× en el caso QSVM |
| «quantum advantage >17%» / «+13-23%» | `docs/PRESENTATION_SCRIPT.md:160,174`; `docs/PRESENTATION.md:348` | Sin ventaja: +0.0154 F1 sobre predictor trivial siempre-positivo, +0.0040 sobre svm_linear, n=60, IC95 ±0,115 | `benchmark-pcaps-latest.json`, `docs/HONEST-BENCHMARK.md` |
| 85-92% zero-day / FPR <3% | `docs/PRESENTATION.md:104-106`; `:332-350` | **no medido**; se declara no medido | — (sin artefacto: por eso se borra) |
| «quantum-inspired VAE» como motor | `docs/index.html:247,323`; `README.md:24-31` | VAE clásico: `use_quantum_encoder=False`, 6 de 14 features constantes, 98,47% flujos de un paquete | `src/qzero/quantum/qivae.py:51` |

## Contexto adicional del banco (verificado en esta sesión)

Re-extracción de los 5 PCAP con `qzero.preprocessing.flow_extractor.FlowExtractor`:

- 2 942 flujos · **48 filas únicas** · **6 de 14 features con varianza cero**
- **98,47%** de flujos con ≤1 paquete forward (2 897/2 942)
- Las 4 métricas QSVM y svm_linear son idénticas en los 4 folds: acc 0.5667, prec 0.5517, recall 1.0 → ambos predicen POSITIVO en el 100%. F1 mide la mezcla del fold, no detección.

## Ficheros tocados

| Fichero | Cambio |
|---|---|
| `docs/index.html` | lede sin «cuántico» como diferencial; §run: 16 050 flows/s → «scores on CPU, no GPU»; §values: SVM cuántica descrita como experimento offline; tabla #truth: media 0.711/0.707, fila precision·recall, fila ROC-AUC split 0.34, caption con ruta del artefacto, verdict reescrito (banco degenerado, 48 filas únicas, 6 features constantes, 98,5% un paquete, ROC-AUC 0.34); title/meta sin QSVM como reclamo; install/analyze sin «SVM» como motor |
| `docs/PRESENTATION.md` | tabla de resultados sustituida por la real (con fecha y rutas); slide «Key Achievements» rehecha; portada/detección-gap/solución/QSVM/QI-VAE reposicionados a «sin ventaja demostrada» |
| `docs/PRESENTATION_SCRIPT.md` | slides 11 y 12 reescritos con cifras reales; se elimina 17% y 13-23% |
| `README.md` | latencia real + método; nota de honestidad con enlace al benchmark |
| `docs/HONEST-BENCHMARK.md` | **nuevo** — banco completo por fold, split, degeneración, 4 cifras defendibles, cifras retiradas, pendientes |
| `docs/research/impl-honestidad.md` | **nuevo** — este documento |

Sin dependencias externas nuevas en el HTML (sigue autocontenido: fuentes locales en `assets/fonts`, sin CDN).

## Verificación

- `grep -c 'class="es"' docs/index.html`: **64 antes → 65 después** (+1 por el enlace a HONEST-BENCHMARK añadido dentro del `sec-intro` de #truth). Los `<span class="en">` también cuadran: 65/65. No se ha perdido ningún par ES/EN.
- HTML parseado sin etiquetas sin cerrar al final del documento (los dos avisos `stray rect` son del favicon SVG inline, preexistentes).
- Sin dependencias externas nuevas: `grep` de `fonts|cdn|unpkg|jsdelivr` → ninguna CDN; fuentes locales en `assets/fonts`.
- Acento azul `#3B82F6` presente, `#6366f1` ausente (0 ocurrencias).

## Lo NO verificado

1. **Capacidad real de detección del QI-VAE.** F1 0.1807 es honesto pero está medido sobre un banco degenerado: no prueba nada sobre tráfico real.
2. **Zero-day y FPR.** Nunca medidos sobre corpus representativo. Se declaran no medidos, no se sustituyen por otra cifra.
3. **Latencia de API (0,16 s / 0,06 s)** que pedía el encargo: no encontré artefacto que la produzca (ni script, ni JSON, ni test). No la publiqué; usé en su lugar `inference_time_s` del benchmark, que sí existe. Si el dueño tiene esa medición, debe aportar el script antes de publicarla.
4. **`qivae.pkl`**: no está en este worktree (no hay directorio `models/`). La afirmación «state_dict de 36 tensores Linear+BatchNorm, sin circuitos» proviene del encargo y de `qivae.py:51`, no la reconté sobre el binario. El HTML final evita citar el recuento exacto.
5. **IC95 ±0,115** del diferencial QSVM−svm_linear: aproximación binomial sobre n=60 comparaciones informativas, no bootstrap. Marcado como orden de magnitud.
6. **`retrain-20261014-2251.md`** (svm_rbf 0.9574, qivae 0.1399) es sintético-contra-sintético; no se cita en materiales públicos ni se usa para rescatar cifras.
