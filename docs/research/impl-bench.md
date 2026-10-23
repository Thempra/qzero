# Implementación — benchmark honesto (Fases 1.6 y 1.7)

Rama: `fase1/bench`. Fecha: 2026-10-23.
Todo lo de abajo salió de ejecuciones reales en esta máquina (VM QEMU, 4 vCPU).
Los JSON crudos están en `model-performance-reports/`.

---

## 1. Qué se entregó

| Fichero | Qué hace |
|---|---|
| `scripts/bench_throughput.py` | Mide flujos/s, latencia p50/p95/p99 por flujo y CPU/RSS. Escribe JSON crudo. Sin privilegios. |
| `scripts/bench_detection.py` | Mide el banco (filas únicas, varianza cero, flujos de 1 paquete), matriz de confusión completa, baseline trivial y stump de 1 feature. Emite veredicto propio. |
| `tests/test_fase1_bench.py` | 29 tests: importabilidad y aritmética (percentiles, matriz de confusión, varianza cero, métricas, baseline, stump) sobre datos de juguete con respuesta conocida. |
| `docs/HONEST-BENCHMARK.md` | Sección nueva **"Mediciones reproducibles (2026-10-23)"**. |

No se tocó el motor de scoring, la API ni la landing.

---

## 2. Hardware

| | |
|---|---|
| CPU | QEMU Virtual CPU version 2.5+ — **4 vCPU**, virtualizada |
| RAM | 3,82 GB |
| SO | Linux 6.1.0-51-amd64, glibc 2.36 |
| Python / torch / numpy | 3.11.2 / 2.4.1+cpu (`torch_num_threads=4`) / 2.4.6 |

No es hardware de producción. Las cifras absolutas valen para esta VM.

---

## 3. Rendimiento medido

Comando exacto:

```bash
.venv/bin/python scripts/bench_throughput.py --flows 2000 --latency-flows 500 --repeat 3 \
    --model-cache /tmp/qzcache/m.pkl
```

JSON: `model-performance-reports/bench-throughput-2026-10-23T10-49-19.json`
(copia estable `bench-throughput-latest.json`).

Salida real (fragmento, repetición 3/3 y resumen):

```
[bench]   13908 paquetes -> 1957 flujos en 0.85 s = 2302.4 flujos/s (16362.6 pkt/s)
[bench]   p50=1.388 ms  p95=1.965 ms  p99=2.744 ms  max=3.237 ms
[bench]   1957 flujos en 1.2557 s = 1558.4 flujos/s (extracción 81.38% del tiempo)
[bench]   con I/O de pcap (lectura+escritura): 13.3731 s = 146.3 flujos/s
[bench]   pcap ya existente -> scores (solo lectura): 6.3051 s = 310.4 flujos/s
[bench]   CPU 148.2% de un core (37.1% de la máquina), RSS pico 591 MB

[bench] mediana de 3 repeticiones: 2059.8 flujos/s e2e, p99 2.697 ms

[bench] RESUMEN DEFENDIBLE
  flujos/s pcap -> scores (solo lectura): 326.2
  flujos/s extracción + inferencia   : 2059.8
  flujos/s solo inferencia (lotes)   : 47437.8
  flujos/s solo extracción           : 2302.4
  latencia por flujo p50/p95/p99: 1.407 / 1.884 / 2.697 ms
```

| Métrica | Valor |
|---|---|
| Extracción + inferencia (sin I/O) | **2 059,8 flujos/s** |
| pcap existente → scores (con `rdpcap`) | **326,2 flujos/s** |
| Solo extracción | 2 302,4 flujos/s |
| Solo inferencia (lotes 256) | 47 437,8 flujos/s |
| Latencia p50 / p95 / **p99** | 1,407 / 1,884 / **2,697 ms** |
| Latencia max | 3,718 ms |
| CPU | 102,3 % de un core (25,6 % de la máquina) |
| RSS pico | 590 MB |
| Load average antes | 0,87 con 4 cores → `contaminated: false` |

Mediana de 3 repeticiones (`repeats.statistic = median_of_repeats`); percentiles sobre
las 1 500 muestras agrupadas. Se publica la mediana, no el mejor caso.

**El 96 % del tiempo es extracción de features**, no inferencia: el cuello de botella es
Scapy, no el modelo cuántico.

### Comparación con lo retirado

| Cifra retirada | Medido | Factor |
|---|---|---|
| 16 050 flujos/s | 2 059,8 flujos/s | **7,8× peor** |
| "sub-millisecond inference" | p50 = 1,407 ms; ningún percentil < 1 ms | **1,4× por encima de 1 ms** |

---

## 4. Un artefacto de medición que hubo que corregir

La primera versión del script medía paquetes recién construidos con Scapy. Esos objetos son
perezosos: `bytes(pkt)` dispara la serialización y **el 88,8 % del tiempo atribuido a
"extracción" era serialización**, no extracción de features. En producción `rdpcap` ya
entrega paquetes disecados.

| Medición | 2 784 paquetes |
|---|---|
| Solo `bytes(p)` | 1,503 s |
| `FlowExtractor` sobre paquetes sin diseccionar | 1,693 s |
| `rdpcap` de un pcap temporal | 1,373 s |
| `FlowExtractor` sobre paquetes disecados | **0,247 s** |

Diferencia: ~7×. El script ahora hace round-trip pcap real (fichero temporal, borrado
siempre) y publica la cifra contaminada solo como referencia
(`extraction_unbuilt_packets`, con `note` explicando que no es el camino de producción).

### Contaminación por otras cargas

Durante las primeras ejecuciones, otro proceso de la máquina (`bench_flows.py`, de otra
sesión) comía un core entero. Esa ejecución dio **1 532,9 flujos/s** frente a los 2 059,8
posteriores con la máquina en reposo — un 26 % de diferencia por carga ajena. Por eso el
script:

- **aborta** si el load average 1m supera 0,9·nproc (`--allow-busy` lo salta),
- registra `load_average.before/after/contaminated` en el JSON.

La cifra publicada es de una ventana con load 0,87.

---

## 5. Detección medida

Comando: `.venv/bin/python scripts/bench_detection.py --epochs 40`
JSON: `model-performance-reports/bench-detection-latest.json`

### El banco es degenerado

| Propiedad | Medido | Umbral |
|---|---|---|
| Flujos | 2 942 | — |
| Filas únicas (14 features) | **48 (1,63 %)** | ≥ 5 % |
| Features con varianza cero | **6 de 14** | ≤ 2 |
| Flujos con ≤1 paquete forward | **98,47 %** | ≤ 50 % |
| Mejor stump de 1 feature | **0,8334** (`flow_duration`) | gap ≤ 0,05 |

Features con varianza cero: `total_bwd_packets`, `total_length_bwd_packets`,
`bwd_packet_length_mean`, `bwd_iat_mean`, `bwd_psh_flags`, `fwd_urg_flags`.

### Matriz de confusión completa (QI-VAE, test = 589 flujos)

| | TN | FP | FN | TP | Acc | Prec | Recall | F1 | ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|
| QI-VAE | 100 | 9 | 428 | 52 | **0,2581** | 0,8525 | 0,1083 | 0,1922 | 0,5635 |
| Baseline mayoritaria | 0 | 109 | 0 | 480 | **0,8149** | 0,8149 | 1,0000 | 0,8980 | — |

**El baseline trivial gana al modelo por 56 puntos de accuracy.** Recall 0,108: detecta 52
de 480 anomalías. Un solo feature llega a 0,8334 de accuracy porque la etiqueta está
codificada en el tamaño/patrón del paquete
(`scripts/generate-synthetic-pcaps-v2.py:47-49`).

Recall por clase (ejecución 10:51): normal 0,083 · ddos 0,092 · bruteforce 0,117 ·
exfiltration 0,133 · malware 0,092.

Reproducibilidad parcial: dos ejecuciones con semilla 42 y 40 épocas dieron accuracy 0,2547
y 0,2581 (±0,4 puntos; torch no es determinista bit a bit aquí). Ninguna conclusión cambia:
el baseline gana por más de 55 puntos en ambas, y los números del banco son idénticos.

El script emite su veredicto en `verdict.statement`:
> BANCO DEGENERADO: los números de detección de este JSON NO permiten afirmar capacidad de
> detección ni comparar clasificadores.

### Modelo

`models/qivae.pkl` **no existe** en el repo (no está versionado). El script entrena un
QI-VAE con la arquitectura de `scripts/benchmark-pcaps.py` (latent 4, hidden 64/32, 40
épocas, solo normales del train) y lo declara en `model.source = trained-in-bench`. No se
está midiendo el modelo de producción porque no hay artefacto que cargar.

---

## 6. Tests

```
$ .venv/bin/python -m pytest tests/test_fase0_score.py tests/test_fase1_bench.py -q
43 passed in 1.66s
```

```
$ .venv/bin/python -m pytest tests/test_flow_extractor.py tests/test_detection.py tests/test_predictor.py -q
19 passed, 1 skipped in 4.71s
```

`tests/test_fase1_bench.py` incluye un test de regresión que nació de un fallo real: la
matriz de confusión descartaba en silencio las clases >1 (2=dDoS, 3=exfiltración,
4=malware), con lo que los totales no sumaban `n` y la accuracy salía inflada. Ahora
binariza con `!= 0` y el test `test_confusion_matrix_binarizes_multiclass_labels` lo fija.

---

## 7. NO MEDIDO

Nada de esta lista se estimó ni se extrapoló: no se midió.

| Qué | Por qué |
|---|---|
| **Gbps de red sostenidos** | No hay NIC dedicada ni permisos de captura en esta VM QEMU. Una captura en loopback mediría la pila local, no el producto. |
| **Drops de captura del kernel** | Requiere `af_packet` con privilegios y una NIC real. |
| **Throughput con el modelo desplegado en producción** | `models/qivae.pkl` no está publicado/versionado. Se usa uno entrenado aquí; sirve para coste de inferencia, no para calidad. |
| **Concurrencia multi-hilo / multi-flujo** | El pipeline medido es un proceso y un hilo de inferencia. |
| **Detección sobre tráfico benigno real / FPR defendible** | No hay corpus real en el repo. Sin benigno real, el FPR no significa nada. |
| **Zero-day** | El banco sintético no contiene ataques no vistos. |
| **Latencia de red / tiempo entre llegada del paquete y scoring** | Fuera del alcance del pipeline medido (empieza en el pcap). |
| **Comparación de clasificadores** | El banco no la permite (ver §5). El F1 de 0,71 citado antes mide la composición del split. |

---

## 8. Conclusión

- **Rendimiento: sí se puede medir y se midió.** 2 059,8 flujos/s de extracción+inferencia
  y p99 de 2,697 ms en esta VM de 4 vCPU. Con lectura de pcap incluida, 326,2 flujos/s.
  Las dos cifras retiradas eran falsas por 7,8× y por cruzar el milisegundo.
- **Detección: no se puede medir con este banco, y eso es el resultado.** El baseline
  trivial (0,8149) supera al modelo (0,2547); 48 filas únicas para 2 942 flujos; 6 features
  con varianza cero; la etiqueta está en el tamaño del paquete. Publicar cualquier F1 de
  aquí sería repetir el error que este documento existe para evitar.
- **Qué haría falta para medir detección de verdad:** un corpus con tráfico benigno real y
  conversación bidireccional; sin él, no hay FPR ni zero-day defendibles.

## 9. Reproducir de cero

```bash
# rendimiento (entrena el modelo la primera vez, ~60 s)
.venv/bin/python scripts/bench_throughput.py --flows 2000 --latency-flows 500 --repeat 3

# detección (~3 min con 40 épocas)
.venv/bin/python scripts/bench_detection.py --epochs 40

# tests
.venv/bin/python -m pytest tests/test_fase0_score.py tests/test_fase1_bench.py -q
```

Los pcaps temporales del round-trip se escriben en `tempfile.mkdtemp(prefix="qz-bench-")` y
se borran siempre; solo quedan los JSON de `model-performance-reports/` (96 K).
