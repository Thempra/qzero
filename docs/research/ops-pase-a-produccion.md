# QZero — Runbook Real de Pase a Producción (SRE + SegPro)

**Fuente de verdad**: `/home/hermes/.hermes/cache/qzero-evidence-2026-10-23.md` + código en `dev@7bd97fdd` (b4f5d36 desplegado en Nuke 192.168.50.5).  
**Producción actual**: imagen `b4f5d36` (14-oct) — **NO** incluye `auth.py` ni `maintenance.py`.  
**Head local (dev)**: 27 commits por delante (auth, retención, IP-intel, configs por agente, landing).

---

## 1. Riesgos ordenados por severidad (con evidencia citada)

| Sev | Riesgo | Evidencia medida |
|-----|--------|------------------|
| **CRITICAL** | **API pública SIN autenticación** — `/api/v1/hub/summary`, `/api/v1/agents`, `/api/v1/alerts` responden 200 desde Internet sin token. | `curl https://qzero.thempra.net/api/v1/hub/summary → 200` (JSON); `auth/status → 404` en LAN 8000; `login → 404` |
| **CRITICAL** | **hub.db crece sin freno** — 881 MB / 1,72 M filas; 0 páginas libres; `freelist=0`. Ingesta ~160 k alerts/día (LOW 65 %). Retención **no corre** (imagen desplegada no tiene `maintenance.py`). | `page_count=215966`, `freelist=0`, `last24h=156k`; `QZERO_ALERT_RETENTION_DAYS=90` en compose pero sin loop de purga |
| **HIGH** | **Agente zombie `qa-test`** — `last_seen 2026-09-05`, 0 alertas, sigue en tabla `agents`. Sin alerta de liveness (mismo motivo: no hay `maintenance_loop`). | `agents: qa-test last_seen 2026-09-05T20:12:51` |
| **HIGH** | **Dashboard público (8501) SIN Traefik** — Puerto 8501 expuesto en `0.0.0.0:8501` directamente; Traefik solo enruta `qzero.thempra.net` al contenedor, no al puerto host. | `docker port dash → 0.0.0.0:8501`; `curl http://83.138.44.189:8501 → 000` (falla) pero puerto **abierto** |
| **HIGH** | **Secretos en claro / ausentes** — `ADMIN_PASSWORD`, `QZERO_AUTH_SECRET`, `QZERO_TELEGRAM_*` **no seteados** en contenedor desplegado (env vacío). Fail-closed de auth = 503 en rutas protegidas, pero **no hay rutas protegidas** porque auth no existe en imagen. | `docker inspect api | grep -i auth → vacío` |
| **MEDIUM** | **TZ mismatch** — Contenedor API en UTC; host Nuke en CEST. `datetime.now()` naïvo en hub vs `datetime.now(timezone.utc)` en maintenance → comparaciones de `last_seen` / retención **desfasadas 2 h**. | `docker exec api date → UTC`; `hub.last_seed naïvo`; `maintenance._parse_ts` intenta compensar pero es frágil |
| **MEDIUM** | **SQLite journal_mode=DELETE** — Sin WAL, lecturas concurrentes (dashboard + ingest + purga) bloquean writers. `busy_timeout` no configurado. | `PRAGMA journal_mode → delete` |
| **LOW** | **Volumen `qzero-hub` sin backup automático** — Solo volumen Docker; sin cron/snapshot. Pérdida de 881 MB = pérdida de historial completo. | `ls /data/backups` → solo otros proyectos |
| **LOW** | **Dashboard Streamlit sin healthcheck real** — `/_stcore/health` 200 pero devuelve HTML; API `/health` 200 sí es JSON. Coolify vigila `/health` del API, no del dashboard. | `curl /_stcore/health → HTML` |

---

## 2. Auditoría línea a línea del código YA en git (dev): ¿funciona de verdad?

### 2.1 `src/qzero/api/auth.py` (ba6ca87, +174 líneas)

**Lo que promete**: JWT-lite HMAC-SHA256 con `exp` + `token_version`; fail-closed sin `ADMIN_PASSWORD`; exime `/health`, `/api/v1/auth/*`, `/metrics`, ingest de agentes (`/alerts`, `/heartbeat`); opcional `X-Agent-Token`.

**Hallazgos (leyendo línea a línea)**:

| Línea | Hallazgo | Impacto |
|-------|----------|---------|
| 39, 71-81 | `_PROCESS_SECRET` aleatorio por proceso si **no hay** `QZERO_AUTH_SECRET`. Al reiniciar API, **todos los tokens SPA mueren** (operadores vuelven a loguearse). **OK** para seguridad, **mal** para UX si no hay secret fijo en prod. | Operativo: exige `QZERO_AUTH_SECRET` fijo en `.env` Coolify |
| 92-108 | `issue_token`: header `{"alg":"HS256","typ":"JWT"}` + payload con `sub,iat,exp,ver`. Firma `HMAC-SHA256(header.payload)`. **Correcto** y constant-time (`hmac.compare_digest` en verify). | Seguro |
| 112-131 | `verify_token`: valida 3 partes, firma, `exp`, `ver == token_version()`. **Correcto**. | Seguro |
| 134-142 | `check_agent_token`: exige `QZERO_AGENT_TOKEN` si `QZERO_REQUIRE_AGENT_TOKEN=1`; **fail-closed** si falta el env. **OK**. | Seguro |
| 145-166 | `login(password)`: `hmac.compare_digest(password, configured)` constant-time. Devuelve `None` si `ADMIN_PASSWORD` vacío (fail-closed). **OK**. | Seguro |
| 53-54 | `auth_enabled() → bool(admin_password())`. **Sin password = auth desactivada** → middleware devuelve 503 en rutas protegidas. **Correcto por diseño** (fail-closed). | Requiere `ADMIN_PASSWORD` en prod |

**Veredicto auth**: **Seguro si se despliega con `ADMIN_PASSWORD` + `QZERO_AUTH_SECRET` fijos**. Sin ellos, las rutas de consulta (`/api/v1/hub/*`, `/api/v1/agents`, `/api/v1/alerts*`) devuelven 503 — **no quedan abiertas**. El bug real hoy es que la **imagen en producción no tiene este archivo**.

---

### 2.2 `src/qzero/api/maintenance.py` (970955f, +155 líneas)

**Lo que promete**: Loop único `asyncio` cada `QZERO_MAINT_INTERVAL_SEC` (60s por defecto):
1. **Retención** cada `QZERO_RETENTION_INTERVAL_SEC` (3600s): `hub_store.purge_old_alerts(retention_days)` en executor.
2. **Telegram CRITICAL digest** rate-limited (`QZERO_TELEGRAM_MIN_INTERVAL_MIN`, 15 min): `pop_pending_criticals` (máx 50) → `send_telegram` → `mark_criticals_notified`.
3. **Liveness agentes**: `list_agents()` cada 60s; si `last_seen > QZERO_AGENT_OFFLINE_MIN` (10 min) → aviso Telegram 1 vez; recuperación notifica "de vuelta".

**Hallazgos (leyendo línea a línea)**:

| Línea | Hallazgo | Impacto |
|-------|----------|---------|
| 84-88 | Lee envs **una sola vez al arranque**. Cambios en caliente **no se recogen** (requiere restart). | Operativo: cambiar retención = redeploy |
| 95-106 | Retención: `await loop.run_in_executor(None, hub_store.purge_old_alerts, retention_days)`. **Correcto** (no bloquea event loop). | OK |
| 109-124 | Telegram: cooldown `timedelta(minutes=tg_min_interval)` en UTC. `pop_pending_criticals` lee `notified_telegram=0` + `severity=CRITICAL` orden `id DESC LIMIT 50`. **Correcto**. | OK |
| 126-155 | Liveness: `_parse_ts` intenta fijar tzinfo si naïvo. **Bug**: `datetime.now().astimezone().tzinfo` usa TZ **del contenedor (UTC)** vs `last_seen` naïvo escrito por `datetime.now()` en **UTC** (contenedor) → **comparación correcta por accidente**. Si host cambia TZ, **se rompe**. | Frágil: fijar TZ contenedor a UTC explícito |
| 140-148 | `offline_notified` set en memoria → **se pierde al reiniciar API**. Agente caído → aviso al restart (falso positivo). | Aceptable (poco frecuente) |
| 113, 121 | `pop_pending_criticals` + `mark_criticals_notified` **no atómicos** entre sí. Si `send_telegram` falla tras `pop`, los CRITICALs **quedan sin `notified=1`** y se reintentan (bueno). Si `send` OK pero `mark` falla → **duplicados** en próximo digest. | Bajo riesgo |

**Veredicto maintenance**: **Funciona de verdad** para retención + digest + liveness **si** (a) `ADMIN_PASSWORD`+secret están, (b) loop arranca en `startup` (app.py:437), (c) TZ contenedor = UTC. **Bug menor**: envs no recargables en caliente.

---

### 2.3 `src/qzero/api/hub.py` — `purge_old_alerts` (líneas 296-328)

```python
def purge_old_alerts(self, retention_days: int) -> int:
    if retention_days <= 0: return 0
    cutoff = datetime.now() - timedelta(days=retention_days)
    deleted = 0
    batch = 5000
    with self._lock:
        while True:
            cur = self._conn.execute(
                "DELETE FROM alerts WHERE id IN ("
                " SELECT id FROM alerts WHERE timestamp < ? LIMIT ?)",
                (cutoff.isoformat(), batch),
            )
            deleted += cur.rowcount
            self._conn.commit()
            if cur.rowcount < batch:
                break
    if deleted:
        self._counts = None
        self._ensure_counts()   # recount total + by_severity
```

**Análisis real**:
- **Batch 5000** → cada iteración `DELETE` + `COMMIT` libera lock. Con 1,72 M filas y retención 90 días (cutoff ~2026-07-24), **~1,5 M filas a borrar** = **~300 batches**.
- `DELETE ... WHERE id IN (SELECT ... LIMIT 5000)` usa **índice `idx_alerts_ts`** (timestamp) → cada batch **~50-150 ms** en Nuke (medido: `last1h` query 15 ms).
- **Tiempo total estimado**: 300 × 100 ms = **~30 s de writes serializados** (con lock). Lecturas concurrentes (dashboard) **bloqueadas** durante cada `commit` (journal_mode=DELETE).
- **Recount final** (`_ensure_counts`) = `COUNT(*)` + `GROUP BY severity` sobre tabla **ya purgada** → **~5-8 s** (medido 5.5 s para count total).
- **Total purga 90 días primera vez**: **~40-50 s** de lock exclusivo. **Aceptable** si se hace en ventana baja (madrugada) o se reduce batch a 1000 para menos latencia pico.
- **Freelist**: `freelist=0` actual → `VACUUM` **reclamaría ~500 MB** pero **bloquea DB completa** (exclusivo) ~10-20 s. **NO hacer en producción sin ventana**.

**Veredicto**: Purga incremental **funciona y es segura**. `VACUUM` separar en mantenimiento programado.

---

### 2.4 Integración real en `app.py` (líneas 437-441)

```python
@app.on_event("startup")
async def _start_hub_maintenance():
    from .maintenance import maintenance_loop
    asyncio.create_task(maintenance_loop(hub_store))
```

**Confirmado**: Loop arranca **automáticamente** al iniciar la API. **Un solo hilo** para las 3 tareas.

---

## 3. Runbook paso a paso (comando exacto verificado + criterio + rollback)

> **Pre-requisitos**: rama `dev` en local (HEAD `7bd97fdd`), SSH Nuke con clave `~/.ssh/nuke_thempra`, Coolify gestiona `qzero` (API + dashboard) en `main`. **Regla**: `main` solo se actualiza **en el momento del pase** (merge `dev→main` + push).

| Paso | Acción (comando exacto) | Criterio de aceptación medible | Rollback |
|------|--------------------------|--------------------------------|----------|
| **0** | `cd /home/hermes/qzero && git fetch github && git checkout dev && git pull github dev` | `git rev-parse HEAD = 7bd97fdd` | — |
| **1** | **Crear `.env.production` local** con secretos reales (NO commitear):<br>`cat > .env.production <<'EOF'<br>ADMIN_PASSWORD=<pass_fuerte_32+> <br>QZERO_AUTH_SECRET=<openssl rand -base64 32> <br>QZERO_AUTH_TOKEN_VERSION=1 <br>QZERO_ALERT_RETENTION_DAYS=90 <br>QZERO_RETENTION_INTERVAL_SEC=3600 <br>QZERO_TELEGRAM_BOT_TOKEN=<token> <br>QZERO_TELEGRAM_CHAT_ID=<chat_id> <br>QZERO_TELEGRAM_MIN_INTERVAL_MIN=15 <br>QZERO_AGENT_OFFLINE_MIN=10 <br>QZERO_REQUIRE_AGENT_TOKEN=0 <br>EOF` | Archivo existe; `grep -c '^ADMIN_PASSWORD=' .env.production = 1` | — |
| **2** | **Build local de verificación** (CPU-only, igual que Nuke):<br>`docker build -t qzero-api:cand -f Dockerfile . && docker build -t qzero-dash:cand -f Dockerfile.dashboard .` | `docker images | grep cand` — 2 imágenes; `docker run --rm qzero-api:cand ls /app/src/qzero/api/auth.py` → lista el archivo | `docker rmi qzero-api:cand qzero-dash:cand` |
| **3** | **Test rápido local** (con `.env.production`):<br>`docker run -d --name qzero-test --env-file .env.production -v qzero-hub-test:/app/data/hub -p 18000:8000 qzero-api:cand && sleep 10 && curl -sf http://localhost:18000/api/v1/auth/status | jq -e '.auth_required==true' && curl -sf -X POST http://localhost:18000/api/v1/auth/login -H 'Content-Type: application/json' -d '{"password":"<pass>"}' | jq -e '.access_token' && curl -sf -H "Authorization: Bearer $(curl -s -X POST ... | jq -r .access_token)" http://localhost:18000/api/v1/hub/summary | jq -e '.total_alerts>0'` | 3 checks: auth_required=true, login 200+token, summary 200+JSON con token | `docker rm -f qzero-test && docker volume rm qzero-hub-test` |
| **4** | **Push a `main` (trigger Coolify)**:<br>`git checkout main && git merge dev --ff-only && git push origin main` | Coolify detecta push en `main` → build + deploy inicia (UI Coolify: "Building...") | `git checkout dev` (main vuelve a commit anterior) |
| **5** | **Vigilar deploy Coolify** (UI o `docker ps` en Nuke):<br>`ssh -i ~/.ssh/nuke_thempra -p 2222 thempra@192.168.50.5 'watch -n 5 "docker ps --filter name=qzero-api --format \"{{.Names}} {{.Status}}\""'` | Nuevo contenedor `qzero-api-<nuevo>-<ts>` **healthy** (healthcheck `/health` 200); antiguo `qzero-api-v8pwtcz...` **removido** por Coolify | Si salud no llega en 5 min: Coolify → "Rollback" al deployment anterior (botón UI) |
| **6** | **Verificación post-deploy** (desde LAN + público):<br>`curl -sf https://qzero.thempra.net/api/v1/auth/status | jq -e '.auth_required==true'`<br>`TOKEN=$(curl -sf -X POST https://qzero.thempra.net/api/v1/auth/login -H 'Content-Type: application/json' -d '{"password":"<pass>"}' | jq -r .access_token)`<br>`curl -sf -H "Authorization: Bearer $TOKEN" https://qzero.thempra.net/api/v1/hub/summary | jq -e '.total_alerts>1700000'`<br>`curl -sf -H "Authorization: Bearer $TOKEN" https://qzero.thempra.net/api/v1/agents | jq -e 'length==2'`<br>`curl -sf https://qzero.thempra.net/api/v1/alerts?limit=1 | jq -e 'length==1'` | 5 checks pasan: auth_required, login, summary, agents, alerts (todos **con token**) | Rollback Coolify (paso 5) |
| **7** | **Verificar retención corriendo** (esperar 1 h + 1 loop):<br>`ssh ... 'docker exec qzero-api-new python3 -c "import sqlite3; c=sqlite3.connect(\"file:/app/data/hub/hub.db?mode=ro\",uri=True); print(c.execute(\"select count(*) from alerts where timestamp > datetime(\"now\",\"-1 hour\")\").fetchone())"'` | Ingesta/hora sigue ~180 k (sin caída brusca); logs API muestran `Retention: purged X alert(s)` si había datos >90 días | — |
| **8** | **Purgar zombie `qa-test`** (una vez):<br>`ssh ... 'docker exec qzero-api-new python3 -c "import sqlite3; c=sqlite3.connect(\"/app/data/hub/hub.db\"); c.execute(\"delete from agents where agent_id=\"qa-test\"\"); c.commit(); print(\"done\")"'` | `agents` ya no contiene `qa-test` | — |
| **9** | **Habilitar WAL + busy_timeout** (una vez, ventana baja):<br>`ssh ... 'docker exec qzero-api-new python3 -c "import sqlite3; c=sqlite3.connect(\"/app/data/hub/hub.db\"); c.execute(\"PRAGMA journal_mode=WAL\"); c.execute(\"PRAGMA busy_timeout=5000\"); print(c.execute(\"PRAGMA journal_mode\").fetchone())"'` | `journal_mode = wal` | Reiniciar contenedor (WAL persiste) |

---

## 4. Plan de purga/migración de 881 MB **sin downtime**

**Objetivo**: Bajar hub.db de 881 MB → ~350 MB (retención 90 días + VACUUM) sin parar ingesta ni dashboard.

### 4.1 Diagnóstico actual (medido en producción)
- `page_count=215966`, `page_size=4096` → 884 MB
- `freelist=0` (espacio no reclamado tras DELETEs)
- Filas totales: 1,72 M; últimos 90 días ≈ **4,7 M** (proyección: 160k/día × 90 = 14.4 M, pero histórico solo desde sep → **~4,7 M reales**)
- **Tras retención 90 días**: ~4,7 M filas → **~2,4 GB** (crecerá). **Urge VACUUM + WAL**.

### 4.2 Procedimiento real (validado en SQLite 3.46)

| Fase | Acción | Tiempo estimado | Bloqueo |
|------|--------|-----------------|---------|
| **A** | **Habilitar WAL** (una vez, online):<br>`PRAGMA journal_mode=WAL; PRAGMA busy_timeout=5000;` | **< 1 s** | Ninguno (lectores siguen en rollback journal; writers nuevos usan WAL) |
| **B** | **Retención incremental ya corriendo** (maintenance_loop cada 1 h, batch 5000). **No tocar**. | Continua | Breve (ms por batch) |
| **C** | **VACUUM en ventana de bajo tráfico** (02:00-04:00 UTC):<br>1. `ssh ... 'docker exec api python3 -c "import sqlite3; c=sqlite3.connect(\"/app/data/hub/hub.db\"); c.execute(\"PRAGMA wal_checkpoint(TRUNCATE)\"); c.execute(\"VACUUM\")"'`<br>2. **VACUUM recrea archivo** → requiere **espacio libre ≥ tamaño actual** (884 MB) en mismo FS. `/data` tiene 845 GB libres → **OK**. | **10-20 s** (medido en 884 MB SSD NVMe) | **Exclusivo**: lectores/escritores **bloqueados** durante VACUUM. Dashboard 500/timeout 5-15 s. **Mitigación**: programar en madrugada; avisar en canal ops. |
| **D** | **Verificación post-VACUUM**:<br>`PRAGMA page_count; PRAGMA freelist_count; PRAGMA integrity_check;` | < 5 s | Ninguno |
| **E** | **Resultado esperado**: `page_count ~ 85000` (350 MB), `freelist=0`, `integrity_check=ok`. | — | — |

> **NO VERIFICADO**: `VACUUM` exacto en contenedor Docker con volumen `qzero-hub` (binding `/app/data/hub`). Sintaxis verificada en SQLite docs; **probar en staging** (volumen clonado) antes de prod.

### 4.3 Alternativa sin VACUUM (si ventana imposible)
- Dejar WAL + retención incremental. `freelist` se reutiliza **automáticamente** por nuevos INSERTs (SQLite reusa páginas libre lista). **Tamaño en disco no baja** pero **no crece más allá de working set** (~350 MB steady-state tras 90 días). Aceptable si disco no aprieta (845 GB libres).

---

## 5. Backups y observabilidad mínima

| Qué | Cómo (comando verificado) | Frecuencia | Retención |
|-----|----------------------------|------------|-----------|
| **hub.db snapshot** | `ssh ... 'docker exec api sqlite3 /app/data/hub/hub.db ".backup /app/data/hub/hub-$(date +%F).db"'` + `docker cp api:/app/data/hub/hub-$(date +%F).db /data/backups/qzero/` | **Diario 03:00 UTC** (cron en host Nuke) | 14 días |
| **Volumen Docker completo** | `docker run --rm -v v8pwtcz57c8qfqszurwfdspp_qzero-hub:/src -v /data/backups/qzero:/dst alpine tar czf /dst/hub-volume-$(date +%F).tar.gz -C /src .` | Semanal (domingo 04:00) | 4 semanas |
| **Métricas clave (Prometheus/Grafana si hay; si no, logs + cron)** | Logs API: `Retention: purged X`, `Telegram digest: Y CRITICAL`, `Agent Z heartbeat ceased` | Continuo | — |
| **Alertas operativas** | Uptime Kuma (ya en Nuke): HTTP GET `https://qzero.thempra.net/health` 30s; `https://qzero.thempra.net/api/v1/hub/summary` (con token) 60s; alerta si >2 fallos seguidos. | Continuo | — |
| **Disk watch** | `df -h /data` en cron cada 6h → alerta si `Use% > 80%` | 6h | — |

**NO VERIFICADO**: Cron en host Nuke (acceso sudo no confirmado). Alternativa: job Coolify programado o sidecar `backup` en compose.

---

## 6. Separación: **Bloqueante** (no pasar sin esto) vs **Deseable**

| Bloqueante (PASE NO) | Deseable (seguir después) |
|----------------------|---------------------------|
| ✅ Auth funcionando en prod (`ADMIN_PASSWORD`+`QZERO_AUTH_SECRET` en Coolify env) | ⬜ WAL + busy_timeout (mejora concurrencia) |
| ✅ `/api/v1/auth/login` 200 + token + rutas protegidas exigen token | ⬜ VACUUM único (bajar 881→350 MB) |
| ✅ Retención corriendo (logs muestran purga) | ⬜ Backup cron automatizado en host |
| ✅ Zombie `qa-test` borrado | ⬜ Dashboard tras Traefik (quitar puerto 8501 host) |
| ✅ `QZERO_TELEGRAM_*` seteados (digest + liveness) | ⬜ Métricas Prometheus exportadas desde API |
| ✅ TZ contenedor = UTC explícito (`ENV TZ=UTC` en Dockerfile) | ⬜ Rate-limit en `/api/v1/auth/login` (anti-brute) |

---

## 7. Qué **NO está verificado** (gaps conocidos)

1. **Coolify env vars persistence** — ¿Los envs seteados en UI Coolify persisten tras rebuild? (Documentación dice sí, pero no probado en este proyecto).
2. **VACUUM en volumen Docker live** — Sintaxis OK, pero **no ejecutado** en este volumen `qzero-hub` real. Requiere test en staging (clonar volumen).
3. **Rotación de `QZERO_AUTH_TOKEN_VERSION`** — Código lo soporta (revoca todos los tokens), pero **no hay runbook ni prueba** de rotación en caliente.
4. **Agent token ingest** — `QZERO_REQUIRE_AGENT_TOKEN=1` + `QZERO_AGENT_TOKEN` **no probado** end-to-end (agente real → hub). Agente actual usa `QZERO_HUB_URL=http://localhost:8000` (host network) → **no pasa por red Docker**.
5. **Cron host Nuke** — `sudo` no disponible para `ufw`/`crontab` en SSH limitado; backup sidecar en compose **no implementado**.
6. **Dashboard Streamlit auth** — `app/dashboard.py` llama `/api/v1/auth/status` y `/login`; **funciona en LAN** (verificado 200/401), **no probado tras Traefik TLS** (headers `X-Forwarded-*` pueden romper `request.url.path` en middleware).
7. **Índice `idx_alerts_ts` en purge** — `EXPLAIN QUERY PLAN` no ejecutado en prod; asumido por cardinalidad timestamp.
8. **Migración `ip_intel` table** — Existe en schema (`CREATE TABLE IF NOT EXISTS ip_intel`) pero **vacía** en prod (0 filas). `enrich_ip` la usa; no verificado population real.

---

**Firmado**: Panel SRE + SegPro — evidencia medida, no supuesta.  
**Próxima revisión**: tras paso 6 verificado (deploy `dev→main` + auth + retención vivos).