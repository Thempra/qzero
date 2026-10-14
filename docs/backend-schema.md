# QZero — Backend Schema

Motor: **SQLite** (stdlib `sqlite3`, un único writer, `threading.RLock`, `check_same_thread=False`). Ruta por `QZERO_HUB_DB` (default `data/hub.db`). Migraciones idempotentes al abrir la BD (`ALTER TABLE ADD COLUMN` para `packets`, `detail`).

## 1. Modelado de datos (hub)

```
agents 1 ──── * alerts        (relación lógica por agent_id; sin FK física)
```

### Tabla `agents`
| Columna | Tipo | Notas |
|---|---|---|
| agent_id | TEXT **PK** | lo pone el agente (`QZERO_AGENT_ID` o hostname) |
| agent_name | TEXT | nombre display, vía heartbeat |
| interface | TEXT | interfaz sniffada (p. ej. `eno1`) |
| first_seen | TEXT (ISO8601 UTC) | alta inicial |
| last_seen | TEXT (ISO8601 UTC) | actualizado en heartbeat e ingest |
| total_alerts | INTEGER DEFAULT 0 | recalculado en `ingest_alert_batch` → `_ensure_counts` |

### Tabla `alerts`
| Columna | Tipo | Notas |
|---|---|---|
| id | INTEGER **PK AUTOINCREMENT** | |
| agent_id | TEXT | agente emisor |
| agent_name | TEXT | denormalizado (el hub responde sin JOINs) |
| timestamp | TEXT ISO8601 | instante del flujo (fin de ventana) |
| src / dst | TEXT | IPs (5-tupla del flujo) |
| protocol | INTEGER | número IP proto (6=TCP, 17=UDP) |
| src_port / dst_port | INTEGER | |
| size | INTEGER | bytes del flujo |
| packets | INTEGER DEFAULT 0 | nº paquetes (discriminador FP de volumen) |
| detail | TEXT JSON | extras: `bytes_per_sec`, `packets_per_sec`, proto nombre, meta del flujo |
| anomaly_score | REAL | score QI-VAE/QSVM post-caps |
| severity | TEXT | `LOW`/`MEDIUM`/`HIGH`/`CRITICAL` (post `severity_for`) |
| notified_telegram | INTEGER DEFAULT 0 | 1 = ya incluida en un digest Telegram enviado (Hito 1) |

Índices: `idx_alerts_ts(timestamp)`, `idx_alerts_sev(severity)`.

**Nota de esquema:** no hay FK ni normalización de agente a propósito (cero JOINs, ingest barato). Rotación **sí implementada** (Hito 1): `hub.purge_old_alerts()` borra por lotes lo anterior a `QZERO_ALERT_RETENTION_DAYS` (0 = desactivado) desde el loop de mantenimiento del hub.

## 2. Autenticación

**v3 actual: sin auth en el data-plane.** Confianza de red: agentes → hub dentro de la LAN/VPN Thempra; dashboard expuesto por Traefik con TLS (protección de perímetro). El hub **no** valida `agent_id`: cualquiera que alcance la API puede ingestar (riesgo aceptado en LAN, documentado).

**Fluxo de identidad de agente (pseudo-auth):**
1. Agente arranca con `QZERO_AGENT_ID` (persistente).
2. `POST /api/v1/agents/{id}/heartbeat {agent_name, interface}` → upsert `agents`.
3. Offline = `now - last_seen > umbral` (criterio del dashboard, no del hub).

**Si se activa auth (decisión pendiente PRD Q2, seguir la preferencia del usuario):** login a nivel app — `POST /api/v1/auth/login` con `ADMIN_PASSWORD` (env docker-compose, **fail-closed**, nunca hardcodeada) → token SPA (JWT con exp + refresh vía `token_version`), nunca Basic Auth de nginx. Los agentes usarían `X-Agent-Token` estático por agente (env del contenedor).

## 3. Endpoints (contrato)

| Método/Ruta | Body/Query | Respuesta |
|---|---|---|
| POST `/api/v1/agents/{id}/alerts` | `{alerts:[alert]}` | `{ingested,total}` |
| POST `/api/v1/agents/{id}/heartbeat` | `{agent_name,interface}` | `{ok,last_seen}` |
| GET `/api/v1/hub/summary` | — | `{total_alerts, by_severity{...}, agents_online}` (O(1), siempre fiable) |
| GET `/api/v1/alerts?limit&severity&agent_id` | — | lista |
| GET `/api/v1/alerts/recent?minutes=N` | — | lista ⚠ puede venir `[]` con totales>0 |
| GET `/api/v1/agents` | — | lista de agentes |
| GET `/health`, `/models`, `/stats`, POST `/analyze`, POST `/monitor/start|stop`, WS `/ws` | — | API clásica del predictor/monitor local |

## 4. Flujos de datos end-to-end

1. **Ingesta:** agente (buffer en `QZERO_BUFFER_DIR` si el hub cae → reintentos) → `ingest_alert_batch` → INSERT+upsert en una transacción → contadores.
2. **Consulta:** dashboard Streamlit → `urllib` contra `QZERO_API_URL` (interno `http://qzero-api:8000`) → `intel.py` enriquece (ASN/org, dirección, tipo de amenaza) — el enriquecimiento es **presentación**, nunca se persiste.
3. **Modelo offline:** `qzero train` → artefactos en `model_dir` (QI-VAE state_dict, scaler, metadata, umbral calibrado) → montado en el agente vía `QZERO_MODEL_DIR`. El hub no carga modelos; `/analyze` del API clásico sí (predictor en memoria).
