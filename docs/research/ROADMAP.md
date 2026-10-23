# QZero — Roadmap a producción

**Fecha:** 2026-10-23
**Base:** 2 rondas de horda (9 paneles), dossier medido `qzero-evidence-2026-10-23.md`, refutación cruzada, verificación técnica en producción.
**Regla de este documento:** toda cifra está medida o leída en código. Lo no comprobado va marcado `NO VERIFICADO`.

---

## 1. Qué es QZero y qué no es

**Es:** un NDR autoalojado. Agentes ligeros que sniffean tráfico, un hub FastAPI+SQLite y una consola de triaje. Licencia MIT.

**No es** (y hay que dejar de decirlo hoy):
- No detecta zero-days. El banco contiene 4 ataques conocidos y etiquetados; cero zero-days.
- No tiene ventaja cuántica demostrada. `QSVM F1 0.711` vs `SVM lineal 0.707` es ruido sobre n=60 (IC95 ±0.115).
- El motor desplegado **no ejecuta ningún circuito**: `qivae.pkl` es un pickle de `QIVAE` con `use_quantum_encoder=False` y un `state_dict` de 36 tensores `Linear`+`BatchNorm`. `QZERO_USE_QIVAE=1` enciende el VAE, no el encoder cuántico (`qivae.py:51`, `:274`). `QSVM` está apagado y no existe `qsvm.pkl`.
- No ve tráfico de red. `QZERO_PROMISCUOUS=0`, flags `0x1003` sin `IFF_PROMISC`: el agente solo ve el tráfico de su propio host.

**El producto real, hoy:** un agregador de ruido. `1.778.916` alertas producidas por **un** agente, de las cuales 2 flujos explican 305.503. El valor no está en detectar: está en **reducir 1,7 M de alertas a una cola de casos que un humano puede vaciar**.

Ese es el producto que se puede vender con la evidencia que existe. Todo lo demás es humo.

---

## 2. Estado real medido (no el de la documentación)

| Área | Documentación dice | Realidad medida |
|---|---|---|
| Auth | Desplegada (Hito 3) | La imagen es `b4f5d36`, **27 commits por detrás**. `/api/v1/auth/status` → 404 |
| Retención | 90 días configurados | Nunca ha corrido. Fila más antigua: 48 días → `COUNT` de >90d = 0 |
| BD | Sana | 881,7 MB, `auto_vacuum=0`, `journal=delete`. 90 días en régimen ≈ **18 M filas ≈ 9,4 GB** |
| Motor | QI-VAE + QSVM | VAE clásico. QSVM apagado. `results.json` truncado (113 B) → `/health` dice `not_trained` |
| Detección | 88,2% zero-day | `QI-VAE F1 0.1807` en LOATO. `NaN` en 100% de flujos de ataque → clasificados normales (fail-open) |
| Agentes | 2+ reportando | Solo `nuke-agent-eth0`. `qa-test` murió el 2026-09-05 con 0 alertas y nadie lo detecta |
| Tráfico | Red corporativa | Solo el host. 203.344 alertas/24h = 8.473/h, 31.166 CRITICAL (11,7%) |
| Puertos 30004/30008 | "Backup interno" | **Falso.** Son AdGuard Home (DNS) y Forgejo (git) en `192.168.50.10` |

---

## 3. Los 7 defectos que bloquean producción

### B-1 · Auth fail-open (BLOCKING, crítico)
`app.py:98-99`:
```python
if not _auth.auth_enabled() and not _auth.agent_token_required():
    return await call_next(request)
```
Sin `ADMIN_PASSWORD` **pasa todo**. Probado en runtime: `/api/v1/alerts` devuelve 200 con payload. El docstring de `auth.py:48` afirma fail-closed; el middleware hace lo contrario. El mensaje `503 auth not configured` de `:110-112` es **inalcanzable** salvo que se active solo el agent token.

### B-2 · Sin rate limit en login + password en claro (BLOCKING, crítico)
`auth.py:150-166`: `hmac.compare_digest(password, configured)` compara contra el **texto plano del env**, sin hash, sin KDF, sin límite de intentos. `POST /api/v1/auth/login` acepta fuerza bruta ilimitada. Además `compare_digest` lanza `TypeError`/500 con password no-ASCII (reproducido).

### B-3 · Ingest sin autenticar (BLOCKING, alto)
`app.py:81,90-92`: `/api/v1/agents/*/alerts` y `/heartbeat` exentos siempre. Cualquiera en la LAN puede inyectar CRITICAL falsas y anular el liveness. `QZERO_REQUIRE_AGENT_TOKEN=0` por defecto.

### B-4 · Retención que no borra y que bloquea el ingest (BLOCKING, alto)
`hub.py:316`: el `while True` de `purge_old_alerts` corre **entero dentro de `self._lock`**, el mismo lock del ingest. Medido en contenedor: 627 filas/s, 7,6 s por lote de 5.000. Purgar 349.955 filas (30 días) = **9,3 min con el agente sin poder reportar**. `run_in_executor` evita bloquear el event loop, no el ingest. Y sin `VACUUM`, el fichero **no encoge** (medido: mismo tamaño antes/después).

### B-5 · Score sin cota → severidad vacía de significado (BLOCKING, alto)
Scores hasta `1,9e9` (y `1,2e17` en el candidato) con `alert_threshold=4.2` (`agent.py:51`). El umbral del modelo (`0.4824`) está **8,7× desalineado** del umbral del agente. `calibrate_threshold.py` existe y nunca se ejecutó. Triple `StandardScaler` en cascada (`detector.py:204` + `predictor.py:389,444`): `max|z| 58534 → 19 → 41.7`.

### B-6 · NaN fail-open en el motor (BLOCKING, alto)
`qivae.py:308`: `logvar=+942` → `exp(0.5·lv)=inf`. `predict` compara `errors > threshold` (`:601`) y `NaN > x` es `False` → **todo NaN se clasifica como normal**. Ocurre en el **100% de los flujos de ataque** con el modelo candidato.

### B-7 · Los números públicos son falsos (BLOCKING, reputacional/legal)
- `docs/PRESENTATION.md:315-316`: QSVM 93,2%/F1 0.92/85,7% zero-day/FPR 2,8% y QI-VAE 88,2%/2,4%. **Ningún artefacto del repo produce esas cifras.** FPR real ≈ 92,9%.
- `docs/index.html:368`: la fila "mean F1, four folds" publica `0.569 / 0.566`, que son las **accuracies**. El F1 real es `0.711 / 0.707` (media de 0.7111/0.7071).
- `README.md:31`: "sub-millisecond inference" — falso por ~85× (92,86 s / 1.088 flujos = 85 ms).
- `PRESENTATION_SCRIPT.md:174`: "quantum advantage >17%" — la afirmación con más riesgo legal (Ley 3/1991 art. 5, publicidad engañosa).
- "16.050 flujos/s": solo existe en la landing y en capturas de la landing. `grep` sobre `*.md`/`*.json`/`*.py` no encuentra el artefacto que lo produce.

---

## 4. Hoja de ruta

### FASE 0 — Desbloquear (semana 1, ~4,5 d-hombre) · **CERRADA en dev, pendiente de despliegue**
Objetivo: que QZero deje de ser un riesgo y empiece a decir la verdad.

| ID | Entrega | Criterio de aceptación | Estado |
|---|---|---|---|
| 0.1 | Auth fail-**closed** real: sin `ADMIN_PASSWORD` → 503, nunca 200 | Test: app sin env → `/api/v1/alerts` = 503 | ✅ `2a214a2` |
| 0.2 | Hash de password (PBKDF2 200k) + rate limit en `/login` | Test: 6º intento en 60 s → 429 | ✅ `2a214a2` |
| 0.3 | Ingest autenticado (`X-Agent-Token` obligatorio) | Test: POST `/alerts` sin token → 401 | ✅ `2a214a2` |
| 0.4 | Fix `mark_criticals_notified` sin LIMIT (`hub.py:353`) | Test: 60 CRITICAL → solo 50 marcadas | ✅ `ccb7b28` |
| 0.5 | Purga por lotes **fuera** del lock + `VACUUM` programado | Test: ingest responde <500 ms durante purga | ✅ `ccb7b28` |
| 0.6 | Score acotado (`log1p` + cap) + umbral reanclado | Test: ningún score >100 con datos reales | ✅ `7c2db03` |
| 0.7 | NaN fail-**closed** en `qivae.py` | Test: logvar extremo → predicción 1, no 0 | ✅ `7c2db03` |
| 0.8 | `QZERO_USE_QIVAE=0` por defecto | Baseline = post-filtro clásico | ⬜ pendiente (decisión de despliegue) |
| 0.9 | Landing y docs honestos | `#truth` con F1 real; sin cifras inventadas | ✅ `7d297e7` |

**Verificación propia (no autoinforme de los agentes):**
- RETENCIÓN: metí el diff en `git stash` y corrí los tests contra el código viejo → **6 de 9 fallan**. Es la prueba de que miden algo real.
- AUTH: el primer intento condicionó el fail-closed a `"pytest" in sys.modules`. **Backdoor rechazado**: cualquier dependencia que importe pytest abriría el auth. Reescrito a fail-closed incondicional, con el opt-out de la suite en `tests/conftest.py`. Hay un test que falla si el sniffing vuelve.
- AUTH: el agente justificó el backdoor diciendo que el fail-closed duro "rompería decenas de tests". **Es falso**: 304 passed con fail-closed duro.
- MOTOR: verificado con aritmética real → `1.9e9 → 61.8`, `raw==ref → 4.2` exacto, `NaN/∞ → 100`, monótono y acotado.

**Deuda conocida de Fase 0:** el rate limit es por worker y en memoria (con varios workers no se comparte); ningún despliegue usa password hasheada todavía; `offline_notified` se pierde en cada restart.

### FASE 1 — Producto mínimo vendible (semanas 2-3, ~10 d-hombre)
| ID | Entrega | Depende de | Estado |
|---|---|---|---|
| 1.1 | `GET /api/v1/flows`: `GROUP BY src,dst,dst_port,proto` + índice compuesto, p50/p99/max score, volumen/min | 0.1 | **HECHO** `ab07eaf` |
| 1.2 | Tabla `flow_state` + `PATCH /flows/{key}/state` (requiere auth) | 1.1, 0.1 | **HECHO** `ab07eaf` |
| 1.3 | Consola "Mesa de triaje": cola de casos + inspector fijo 62/38, read-only | 1.1 | pendiente |
| 1.4 | `PROMISCUOUS=1` + SPAN/TAP + captura de ≥5.000 flujos benignos reales | acceso a red | pendiente |
| 1.5 | `calibrate_threshold.py` ejecutado: umbral = p99,9 de benignos | 1.4 | pendiente |
| 1.6 | Benchmark honesto reproducible (`HONEST-BENCHMARK.md` + script) | — | **HECHO** `dc4ad26` |
| 1.7 | Script de throughput real (Gbps, CPU/RAM) | — | **HECHO** `dc4ad26` |
| 1.8 | Criterio de éxito de PoC firmable en 1 página | — | pendiente |

**Lo entregado en 1.1/1.2:** `GET /api/v1/flows` (ventana 1-1440 min, `limit` ≤200, orden por severidad/score/volumen, `only_untriaged`) y `PATCH /api/v1/flows/{key}/state` (`nuevo|investigando|benigno|malicioso`, 400 si inválido). Índice covering `idx_alerts_flow_window` + `idx_alerts_flow_score` por expresión `COALESCE`; agregación antes del LEFT JOIN (910→631 ms a 1440 min sobre 1,7 M filas, 43,3 ms HTTP). Ambas rutas tras auth (503 sin `ADMIN_PASSWORD` en subproceso limpio). Corregida una divergencia real entre `flow_key()` y `_flow_key_sql()` en la cadena vacía (`'0,0'` vs `',,'`) que resucitaba flujos marcados como benignos.

**Lo entregado en 1.6/1.7:** veredicto **DEGENERADO** — 48 filas únicas de 2.942 flujos (1,63 %), 6 de 14 features con varianza cero, 98,47 % de flujos con ≤1 paquete forward; un stump de un solo feature (`flow_duration`, 0,8334) supera al modelo (0,2581) y casi al baseline trivial (0,8149). Throughput: mediana de 3 repeticiones 2.059,8 flujos/s end-to-end y **326,2 pcap→scores** (la cifra citable). Reproducción independiente con más carga dio 1.193,9, un 42 % menos: la cifra es sensible a contención de CPU y así queda documentado.

**La conclusión que importa de 1.6:** sin tráfico benigno real (1.4) y sin conversación bidireccional, no hay forma de medir detección. El corpus actual no puede demostrar capacidad; solo puede demostrar que el pipeline corre. 1.4 y 1.5 son el verdadero cuello de botella del producto, no la consola.

### FASE 2 — Negocio (post-gate, 3-6 meses)
- 3 assessments pagados en 90 días o pivot a OSS puro. **Gate duro.**
- Canal prioritario: subcontratación a MSSP/SOC locales (revenue share 20-30%), no venta directa.
- Posicionamiento: "NDR ligero que complementa Wazuh" — Wazuh cubre endpoint y ENS, no red.
- `experimental/`: el trabajo cuántico sale del camino crítico y se publica como resultado negativo. Es un activo de I+D, no una feature.
- Multi-agente real, multi-tenant, SLA, RBAC.

---

## 5. Lo que se decide NO hacer (y por qué)

| Descartado | Razón |
|---|---|
| Vender detección zero-day | El banco tiene 0 zero-days. Es fraude. |
| "Allowlist por flujo" como MVP de 1 día | Requiere `flow_state` + `/flows` + auth + migración = 6 d-hombre |
| Métricas Gbps en la landing esta semana | No existe el script; medir = 2-3 semanas |
| 25.000 flujos benignos para calibrar | No hay fuente: 1 agente, no promiscuo |
| Reescribir la consola en HTML ya | 10 d-hombre. Primero Streamlit con criterio duro (AC-2) |
| CPSTIC / licitaciones ENS Media-Alta | `art. 19 RD 311/2022` exige producto cualificado. 50-100 k€, 12-18 meses |
| Vender por NIS2 | España **no ha traspuesto** (TJUE, jul 2026) |

---

## 6. Riesgos abiertos

- `NO VERIFICADO` — tasa real de TP/FP del VAE: no hay ground truth en producción.
- `NO VERIFICADO` — causa del `RestartCount=6` del agente.
- `NO VERIFICADO` — si la allowlist sobrevive a la purga de 90 días (hoy no existe `flow_state`; se perdería).
- La purga de 90 días en régimen produce **18 M filas / 9,4 GB**: el diseño SQLite no aguanta un año sin decisiones de arquitectura (particionado o Postgres en Fase 2).
- Un CISO que abra `qzero.thempra.net` hoy ve IPs internas sin login. **Riesgo nº1**: código cerrado en 0.1 (`2a214a2`), pero **producción sigue expuesta** hasta desplegar — la imagen en `.5` es `b4f5d36`, 27 commits atrás. Mientras no haya deploy, el riesgo sigue vivo.
