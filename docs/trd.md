# QZero — TRD (Technical Requirements Document)

**Baseline:** repo `code.thempra.net/apps/qzero` (mirror `github.com/Thempra/qzero`), rama `main`, v3.0.0.

## 1. Stack

| Capa | Elección | Nota |
|---|---|---|
| Lenguaje | Python ≥ 3.10 | `pyproject.toml` + `requirements.txt` |
| Captura | Scapy | sniffing en `src/core/monitor.py` y `src/qzero/agent/agent.py` |
| Features | pandas + NumPy | `FlowExtractor` → DataFrame de 14 features UGRansome |
| ML cuántico | Qiskit ≥ 1.0, qiskit-machine-learning ≥ 0.7 | QSVM + `ZZFeatureMap` (14 → n_qubits, por defecto 4, angle encoding [0,π]) |
| ML profundo | PyTorch ≥ 2.0 (CPU en prod) | QI-VAE (`src/qzero/quantum/qivae.py`) — scorer principal en el agente |
| Baselines | scikit-learn ≥ 1.3 | RF / SVM-RBF / GBM / KNN / MLP (`src/qzero/classical/baseline.py`) |
| API | FastAPI + Uvicorn + Pydantic v2 | `src/qzero/api/app.py` (335 l.), `hub.py`, `schemas.py` |
| Persistencia hub | SQLite stdlib (`sqlite3`) | `QZERO_HUB_DB`, por defecto `data/hub.db`; cero deps externas |
| Dashboard | Streamlit (puerto interno 8501) | `app/dashboard.py` + `app/intel.py`; urllib stdlib contra el hub |
| CLI | Click | `src/qzero/cli/main.py` |
| Testing | pytest + pytest-cov | tests con stubs; `tests/test_postfilter_nmap.py` corre sin scapy/torch |

## 2. Arquitectura de despliegue

- **Hub + dashboard:** contenedores `qzero-api` (:8000) y `qzero` (Streamlit :8501) en **Nuke** vía **Coolify** (docker-compose del repo, `Dockerfile`, `Dockerfile.dashboard`). Traefik del edge enruta `Host(qzero.thempra.net)` + TLS letsencrypt.
- **Agentes:** contenedor `qzero-agent` (`Dockerfile.agent`, `docker-compose.agent.yml`) — hoy en Nuke (`eno1`); escalable a cualquier host con `QZERO_HUB_URL` apuntando al hub.
- **Build del agente:** recompila torch CPU → ~7 min; el primer deploy de un commit puede fallar transitoriamente (`No such container`, OOM) → **reintentar el deploy**, reusa capas.
- **SSH a Nuke:** puerto **2222** con la clave Thempra.
- **Push de despliegue:** auto-deploy solo en `main`. El remoto HTTPS tiene token muerto → push por SSH `git@github.com:Thempra/qzero.git` con `GIT_SSH_COMMAND` a la clave Thempra (y push al mirror propio `code.thempra.net`).

## 3. APIs y contratos internos

### Hub (lo que consume agente y dashboard)
- `POST /api/v1/agents/{agent_id}/alerts` — lote `{alerts:[{timestamp,src,dst,protocol,src_port,dst_port,size,packets,detail,anomaly_score,severity}]}`.
- `POST /api/v1/agents/{agent_id}/heartbeat` — `{agent_name, interface}`.
- `GET /api/v1/hub/summary` — siempre operativo; totales por severidad (fuente de verdad para informes).
- `GET /api/v1/alerts/recent?minutes=N` — ⚠ puede devolver `[]` con `total_alerts` alto; contrastar siempre con `summary`.
- `GET /api/v1/alerts`, `GET /api/v1/agents`, `/health`, `/models`, `POST /analyze`, `/stats`, `/monitor/start|stop`, WS `/ws`.

### Variables de entorno del agente
`QZERO_HUB_URL`, `QZERO_AGENT_ID`, `QZERO_INTERFACE` (default `eth0`), `QZERO_PROMISCUOUS` (0/1), `QZERO_INTERVAL` (5.0 s), `QZERO_MODEL_DIR`, `QZERO_N_QUBITS` (4), `QZERO_ALERT_THRESHOLD` (4.2), `QZERO_BUFFER_DIR`, `QZERO_WHITELIST_PRIVATE` (default 0 — no activar en sensores de LAN).

### Post-filtro (knobs de producción)
`PostFilterConfig`: `whitelist_dns=True`, `whitelist_https_no_payload=True`, `whitelist_local=True`, `whitelist_private=False`, `min_flow_bytes=128`, `min_flow_packets=2`, `https_volume_cap_score=5.0`. Broadcast detectado por `dst.endswith(".255")` **y** `ipaddress.is_multicast` (el primero no lo cubre el segundo).

## 4. Decisiones técnicas clave (no re-decidir sin motivo)
1. **Detección = ML score + post-filtro determinista.** El score QI-VAE correlaciona con **volumen**, no malicia → los topes de severidad van en el filtro, nunca subir el umbral global (perdería señal).
2. **Límites de rate features en `FlowExtractor._to_dataframe`** (única fuente de features): 1 GiB/s y 100k pkt/s. Evita scores de ~1.9e9 en flujos de 1 paquete.
3. **`whitelist_private=False` por defecto.** Un sensor de LAN siempre tiene origen privado; activarlo suppressa TODO (regresión documentada, pitfall #1).
4. **SQLite + threading.RLock** en el hub: suficiente a escala LAN; no introducir Postgres sin necesidad.
5. **Streamlit sin chrome + pills superiores** (no sidebar) como patrón de consola; datos vía urllib, sin estado en el front.
6. **QI-VAE (PyTorch CPU) en el agente** por latencia; QSVM queda para offline/benchmarks.

## 5. Calidad y observabilidad
- Estructura de paquetes: `src/qzero/{quantum,preprocessing,classical,evaluation,core,api,agent,cli}` + `src/core`, `src/detection`, `src/interface` (monitor/PCAP heredados).
- Logging estructurado (`logger.py`). Healthchecks Docker en api (`/health`) y agente (scan de `/proc/*/cmdline`).
- SonarQube en `sast.thempra.net` (`sonar-project.properties`).
- Suite: correr `tests/test_postfilter_nmap.py` localmente; fallos por scapy/torch/dataset ausentes son ambientales, no regresión.
