# Ronda 2 — Verificación técnica (evidencia ejecutada)

Fecha: 2026-10-23. Host: Nuke (192.168.50.5), SSH 2222, usuario `thempra`. **Solo lectura.**
Disco local al empezar: `df -h /` → `/dev/sda1 97G 85G 7,3G 93%` (por encima del umbral de 2 G).
Consecuencia: **ninguna consulta se hizo sobre copia local de hub.db**. Todo se ejecutó dentro del
contenedor con `sqlite3` de Python en modo `file:...?mode=ro` (uri=True), vía `docker exec` + script
enviado en base64 a `/tmp` del contenedor. Contenedores usados: `qzero-api-v8pwtcz…-20261014T191712`,
`qzero-agent-4d80pwz…-20261014T195802`. Nada se copió a local.

---

## 1. ¿Qué son los puertos 30004 y 30008?

**Método.** `ss -tln`, `ss -tanp`, `docker ps --format '{{.Names}} {{.Ports}}'`, `docker port` sobre
cada contenedor, `iptables -t nat -L DOCKER`, sonda TCP (`/dev/tcp`) y HTTP a 192.168.50.5 y a
192.168.50.10, más `SQLite` sobre el origen real de los flujos.

**Evidencia.**
```
# en Nuke: nadie escucha 30004/30008
ss -tln | awk '$4 ~ /:300[0-9][0-9]$/'        ->  (vacío)
/dev/tcp/192.168.50.5/30004                   ->  Connection refused
/dev/tcp/192.168.50.5/30008                   ->  Connection refused
docker port <todos> | grep 3000[48]           ->  (vacío)
# el destino real es .10, no .5
ip neigh | grep 192.168.50.10  ->  192.168.50.10 dev eno1 lladdr 6c:bf:b5:02:a8:5b REACHABLE
curl -i http://192.168.50.10:30004/  -> HTTP/1.1 302 Found  Location: /login.html
curl -i http://192.168.50.10:30008/  -> HTTP/1.1 200  <title>Forgejo: Beyond coding…</title>
curl http://192.168.50.10:30008/api/v1/version -> {"version":"17.0.0+gitea-1.22.0"}
# 30004: bundle de login contiene "AdGuard Home" x1932; /control/* responde 401
```
Origen en la BD (agregado, sin filas crudas):
```
SELECT COUNT(*),MAX(anomaly_score) FROM alerts WHERE dst_port=30004 -> (231971, 1917954176.0)
SELECT COUNT(*),MAX(anomaly_score) FROM alerts WHERE dst_port=30008 -> (73532, 1486.9246)
```

**Respuesta.** **30004 = AdGuard Home** (UI web de DNS filtrante; `/control/status` → 401 es su API).
**30008 = Forgejo 17.0.0+gitea-1.22.0** (git self-hosted). Ambos están en **192.168.50.10**, no en
.5. El tráfico `192.168.50.5 → 192.168.50.10:30004/30008` es **DNS al resolver AdGuard y git/Forgejo**,
no un backup. La etiqueta "backup interno" del diseño de consola es **FALSA** (verificado, no inferido).
Sigue siendo tráfico LAN benigno de alto volumen, así que el eje "volumen alto / rareza baja" del
diseño se sostiene; lo que cambia es el rótulo: "resolución DNS" y "git interno".
NO VERIFICADO: versión exacta de AdGuard Home (no expone endpoint público sin auth; el string
`16.13.1` del bundle no es fiable como versión de producto).

**Consecuencia roadmap.** Reescribir el caso de ejemplo de `diseno-consola-propuesta.md:25` con
"AdGuard Home / Forgejo" en vez de "backup". Ningún cambio de arquitectura.

---

## 2. ¿Qué modelo carga el agente: VAE clásico o con circuitos?

**Método.** `docker exec ls -la /app/models`, `du`, `find -printf "%s\t%p"`, `env | grep QZERO`,
unpickle del `.pkl` real (magic + `state_dict` + `config`) y contraste con el código.

**Evidencia.**
```
/app/models (1,4 MB total):
  763116 classical_random_forest.pkl   447822 classical_gradient_boosting.pkl
   27114 classical_svm_rbf.pkl            2085 feature_engineer.pkl
  121419 qivae.pkl                         752 scaler.pkl
     113 results.json          <-- truncado, JSON inválido
env agente: QZERO_USE_QIVAE=1  QZERO_USE_QSWM=0  QZERO_N_QUBITS=4  QZERO_INTERVAL=5.0
            QZERO_INTERFACE=eno1  QZERO_PROMISCUOUS=0  QZERO_ALERT_THRESHOLD=4.2
magic qivae.pkl = b'\x80\x04\x95\xcc'  -> pickle, no torch.save
type = qzero.quantum.qivae.QIVAE ; clase interna = QuantumInspiredVAE
config = QIVAEConfig(input_dim=14, latent_dim=4, hidden_dims=(64,32),
                     use_quantum_encoder=False, n_qubits=4, epochs=30, beta=1.0)
state_dict (36 tensores) = encoder.encoder.{0,1,4,5} (Linear+BatchNorm), fc_mu, fc_logvar,
                           decoder.*, latent_transform.  Encoder real = <class 'Encoder'>
log arranque: "→ models: qsvm=OFF, qivae=on"   ·  qiskit instalado=True (pero sin uso)
```

**Respuesta.** **VAE clásico.** No hay circuitos: `src/qzero/quantum/qivae.py:51`
(`use_quantum_encoder: bool = False`) y `:274` (`if config.use_quantum_encoder and QISKIT_AVAILABLE`)
significan que la rama cuántica **nunca se construye** en producción. El `state_dict` lo confirma:
36 tensores de `Linear`+`BatchNorm`, cero parámetros de circuito. `QZERO_USE_QIVAE=1` **no** activa
nada cuántico: es un interruptor de "usa el VAE" (`cli/main.py:199`), no de "usa el encoder cuántico".
El único componente realmente cuántico es el **QSVM**, y está **apagado** (`QZERO_USE_QSWM=0`, no
existe `qsvm.pkl` en el modelo). Por tanto el agente que produce las 1,78 M de alertas es
**100 % clásico**. Además `results.json` está corrupto (113 B), por lo que el agente imprime
`Warning: results.json corrupt — ignoring saved metrics.` y `/health` del API responde
`{"status":"healthy","message":"not_trained"}` aun con modelos cargados (`predictor.py:667-673`).

**Consecuencia roadmap.** Cualquier texto de producto que diga "detección cuántica en producción" es
falso hoy. Dos salidas honestas: (a) renombrar a "quantum-inspired VAE" y decirlo; (b) entrenar con
`use_quantum_encoder=True` y medirlo — pero eso exige qiskit-ml en el path de inferencia (hoy solo
está instalado, sin uso) y coste por muestra. Regenerar `results.json` para que `/health` deje de
mentir.

---

## 3. ¿Qué código corre realmente en la imagen del API?

**Método.** `ls -la /app/src/qzero/api/` dentro del contenedor, `grep` de rutas y de
`purge|maintenance|intel` sobre el código montado en la imagen, introspección de imagen/commit, y
comparación con `git log`/`git ls-tree` local.

**Evidencia.**
```
imagen = v8pwtcz…_qzero-api:b4f5d36d1219c257a23426f265c4a79146cede1c
SOURCE_COMMIT=b4f5d36  (= 2026-10-14 20:46:21 "chore: reorganización del repo")
created = 2026-10-14T19:41:20Z
/app/src/qzero/api/ -> __init__.py app.py dashboard.html hub.py hub_dashboard.html monitor.py schemas.py
grep -c 'maintenance|intel' app.py        -> 0
grep -c 'purge'             hub.py        -> 0
rutas en la imagen (15): / /health /models /analyze /stats /dashboard /monitor/start
  /monitor/stop /api/v1/hub/summary /api/v1/agents /api/v1/alerts /api/v1/alerts/recent
  /api/v1/hub /api/v1/agents/{id}/alerts /api/v1/agents/{id}/heartbeat
curl 127.0.0.1:8000/api/v1/intel/8.8.8.8 -> 404 ; /api/v1/auth/status -> 404 ; login -> 404
```
Git (local, todos del 2026-10-14):
```
970955f  Hito 1   retención/digest/liveness  -> crea maintenance.py + hub.purge_old_alerts
f356888  Hito 2.6 config por agente          -> agent_config, GET/PUT /config
dffbb1c  Hito 3.8 cache ip_intel             -> crea intel.py + GET /api/v1/intel/{ip}
ba6ca87  Hito 3.7 auth app-level             -> crea auth.py (22:09, POSTERIOR al deploy 20:46)
```

**Respuesta.** La imagen se construyó desde **b4f5d36** y por tanto **no contiene ninguno de los
cuatro hitos**. Faltan, literalmente: `src/qzero/api/auth.py` (existe en git desde **ba6ca87**,
2026-10-14 22:09), `src/qzero/api/maintenance.py` (**970955f**), `src/qzero/api/intel.py`
(**dffbb1c**) y, dentro de ficheros que sí están, las rutas `/api/v1/auth/*`, `/api/v1/intel/{ip}`,
`GET|PUT /api/v1/agents/{id}/config`, el hook `@app.on_event("startup") → maintenance_loop` y
`HubStore.purge_old_alerts / agent_config / notified_telegram`. Hay **27 commits** entre b4f5d36 y
main. Conclusión: **no hay retención, no hay auth, no hay config por agente, no hay intel en prod**.

**Consecuencia roadmap.** El "Hito 4 despliegue" no es un paso futuro: es el bloqueante real de todo
lo demás. Rebuild + redeploy desde main y re-verificar. Nada de lo auditado en §4 y §5 está hoy
ejecutándose.

---

## 4. Auditoría de `auth.py` y `maintenance.py` (lo más importante)

**Método.** Lectura completa de `src/qzero/api/auth.py` (174 líneas) y
`src/qzero/api/maintenance.py` (155 líneas) + `app.py:65-135` (middleware) + `hub.py:302-358`,
contraste con el comportamiento en runtime y prueba de `hmac.compare_digest` con no-ASCII.

### 4.1 Naturaleza del esquema

- **No hay hash de password.** No existe bcrypt/argon2/pbkdf2/scrypt en ningún punto:
  `auth.py:48-54` lee `ADMIN_PASSWORD` en claro del entorno y `auth.py:155-156` compara **texto plano
  contra texto plano**. La password vive en `docker inspect`, en `/proc/1/environ` y en la UI de
  Coolify. No hay sal, no hay coste, no hay "hash".
- **Comparación en tiempo constante: sí** para el password (`hmac.compare_digest`, `auth.py:155`) y
  para la firma del token (`auth.py:122`) y el agent token (`auth.py:142`). Correcto en la forma.
- **Token: JWT casero ("JWT-lite")**, HS256 con `hmac`/`hashlib` de stdlib, `header.payload.sig` en
  base64url (`auth.py:96-109`). Lleva `sub`, `iat`, `exp` y `ver`. TTL fijo 12 h
  (`auth.py:34`). Revocación solo global por `QZERO_AUTH_TOKEN_VERSION` (`auth.py:129`).
  Se verifica `exp` (`:127`) y `ver` (`:129`); **no** se valida `alg`, `iss`, `aud`, `nbf` — sin
  impacto porque la clave no se deriva del header.
- **Rate limit: NO EXISTE.** `grep -rn 'rate_limit|ratelimit|slowapi|throttle' src/qzero/api/` → 0
  resultados. `POST /api/v1/auth/login` es fuerza-bruteable sin límite, sin lockout y sin log de
  fallos (`login()` solo loguea el éxito, `auth.py:159`).

### 4.2 Middleware: qué protege exactamente (`app.py:84-117`)

Exento siempre: prefijos `/health`, `/api/v1/auth/`, `/metrics`; exactos `/`, `/dashboard`, `/hub`,
`/api/v1/hub`, `/ws`; y `POST` sobre `/api/v1/agents/{id}` que acabe en `/alerts` o `/heartbeat`.
Todo lo demás exige `Authorization: Bearer <token>`.

| Ruta | Método | Protegida |
|---|---|---|
| `/health` | GET | NO (exenta) |
| `/api/v1/auth/status`, `/api/v1/auth/login` | GET/POST | NO |
| `/` , `/dashboard`, `/hub`, `/api/v1/hub` | GET | NO |
| `/ws` | WS | **NO** (y el middleware HTTP ni se aplica a websockets) |
| `POST /api/v1/agents/{id}/alerts` | POST | NO (solo `X-Agent-Token` si `QZERO_REQUIRE_AGENT_TOKEN`) |
| `POST /api/v1/agents/{id}/heartbeat` | POST | NO (idem) |
| `GET /api/v1/hub/summary`, `/api/v1/agents`, `/api/v1/alerts`, `/api/v1/alerts/recent` | GET | SÍ |
| `GET|PUT /api/v1/agents/{id}/config` | GET/PUT | SÍ |
| `GET /api/v1/intel/{ip}` | GET | SÍ |
| `POST /analyze`, `/monitor/start`, `/monitor/stop`, `GET /models`, `/stats` | varios | SÍ |

### 4.3 BUGS REALES (file:line, por gravedad)

1. **`app.py:98-99` — fail-open, no fail-closed.** Si `ADMIN_PASSWORD` no está y
   `QZERO_REQUIRE_AGENT_TOKEN` no está, el middleware hace `return await call_next(request)` y
   **deja pasar todo**. El docstring (`auth.py:5-6`, `app.py:66-68`) promete "503, nunca open".
   Verificado hoy en prod: `curl /api/v1/alerts` → **200** con payload completo. El diseño
   "parecería seguro" y sería abierto si alguien olvida una env var.
2. **`app.py:81,90-92` + `auth.py:59` — ingest y heartbeat sin autenticación por defecto.** Cualquiera
   en la LAN puede inyectar alertas CRITICAL falsas (que entran en el digest de Telegram y en la
   consola) y latir por un agente inexistente o caído, **anulando la detección de agentes muertos de
   `maintenance.py:126-148`**. `QZERO_REQUIRE_AGENT_TOKEN` está sin definir en prod.
3. **`hub.py:316` — la retención bloquea el ingest.** El `while True` del purge está **dentro** de
   `with self._lock:`, y el mismo `RLock` serializa `ingest_alert_batch` (`hub.py:161`) y todas las
   consultas. Durante un purge, el agente recibe timeouts. Medido: 7,6 s por lote de 5 000.
4. **`auth.py:155-156` — `TypeError` con no-ASCII.** `hmac.compare_digest` sobre `str` exige ASCII:
   `TypeError: comparing strings with non-ASCII characters is not supported`. Una password con `ñ`/`€`
   (o un intento con no-ASCII) produce **500** en el login en vez de 401. Reproducido localmente.
5. **`hub.py:353-358` — `mark_criticals_notified` marca de más.** El `UPDATE` no tiene `LIMIT` ni
   `IN (ids)`: si hay >50 CRITICAL pendientes, `pop_pending_criticals` devuelve 50 (`hub.py:347`) y
   este `UPDATE` marca **todas** como notificadas. Las demás **se pierden en silencio**.
6. **`hub.py:302-335` — sin `VACUUM` y `auto_vacuum=0`.** Medido en la BD real:
   `PRAGMA auto_vacuum=(0)`, `journal_mode='delete'`, `page_count=222239`, `freelist_count=0`.
   Tras un purge sintético el fichero **no baja de tamaño** (101,9 MB antes y después). Borrar filas
   no libera disco: el riesgo de "disco lleno" sigue intacto.
7. **`maintenance.py:100-101` — `last_purge = now` antes de purgar.** Si el purge lanza excepción
   (`:105-106` la traga), no se reintenta hasta dentro de otra hora.
8. **`maintenance.py:55-62` — `_parse_ts` asume que el escritor usa la tz local.** `_report_agent`
   escribe `datetime.now()` naive (`hub.py:130`) y aquí se compara contra
   `datetime.now(timezone.utc)`. Hoy cuadra porque el contenedor está en UTC (`date` → UTC, sin
   `/etc/timezone`); con `TZ=Europe/Madrid` la liveness se desplaza 2 h y dispara falsos "agente
   caído".
9. **`auth.py:70-81` — secreto efímero si falta `QZERO_AUTH_SECRET`.** `secrets.token_bytes(32)` por
   proceso. Con `--workers 1` es inocuo; al escalar a >1 worker cada worker firma distinto y los
   tokens fallan de forma aleatoria (401 intermitentes).
10. **`app.py:57-62` + `:96` — CORS `allow_origins=["*"]` y el middleware propio es el más externo**,
    así que un `OPTIONS` preflight cross-origin a una ruta protegida recibiría 401 antes de CORS.
    Solo afecta a SPAs en otro origen (la consola es same-origin), pero rompe el patrón si se separa.
11. **`maintenance.py:67-79` — inyección de Markdown en Telegram.** `build_critical_digest` mete
    `src/dst/agent_name` (controlados por el agente) en `parse_mode="Markdown"`: un `*` o `_` rompe el
    mensaje y permite manipular el digest.

**Respuesta.** Al desplegarlo **no quedaría seguro: quedaría "pareciendo" seguro**. Hay constant-time
compare y `exp`, que es lo que un revisor mira primero, pero (a) la password no está hasheada, (b) no
hay rate limit, (c) el modo por defecto es **fail-open**, y (d) el data-plane (ingest + heartbeat +
`/ws`) queda sin autenticar. Lo que sí está bien: gestión de `exp`, `token_version` para revocar en
bloque, y `compare_digest` usado de forma consistente.

**Consecuencia roadmap.** Antes de exponer nada: hashear con `hashlib.scrypt` (stdlib, sin deps),
rate-limit por IP en `/api/v1/auth/login`, y cambiar `app.py:98` a fail-closed real. Después: token de
agente obligatorio (generado, no opcional) y proteger `/ws`.

---

## 5. ¿Funcionaría la retención?

**Método.** Lectura de `hub.py:302-335` + `maintenance.py:84-106` (sin suponer flags: se leyó el
parseo de env), benchmarks de purge **dentro del contenedor** sobre BD sintética en `/tmp`
(no en el volumen), y agregados de la BD real.

**Evidencia.**
```
maintenance.py:84  retention_days = int(_env("QZERO_ALERT_RETENTION_DAYS", "90") or 0)
maintenance.py:86  purge_sec      = int(_env("QZERO_RETENTION_INTERVAL_SEC", "3600"))
hub.py:315         batch = 5000   ; hub.py:316 with self._lock:  ; hub.py:324 commit() por lote
BD real: 1.778.916 filas · 910.225.408 B · 512 B/fila · 203.344 filas/últimas 24 h (~8.473/h)
         MIN(timestamp)=2026-09-05 · MAX=2026-10-23T06:17
         COUNT(< now-90d) = 0        COUNT(< now-30d) = 349.955
bench (200k filas, esquema real, journal=delete, synchronous=FULL):
         100.002 borradas en 159,5 s = 627 filas/s · 21 lotes · 7.597 ms/lote
         extrapolación a 349.955 filas -> ~558 s (~9,3 min) · freelist 8.104 · tamaño SIN CAMBIAR
```

**Respuesta.** **Hoy la retención no borraría nada**: el default es 90 días y la fila más antigua
tiene 48 días (`COUNT(< now-90d) = 0`). Y cuando empiece a borrar, **no resuelve el problema de disco**:
no hay `VACUUM` y `auto_vacuum=0`, así que el fichero se queda en 885 MB (verificado: mismo tamaño
antes/después del purge). Peor: con **90 días de retención en régimen estable** el hub acumularía
~90 × 203 k ≈ **18 M filas ≈ 9,4 GB** — tres veces el tamaño actual. La retención, tal como está
configurada, **agrava** el crecimiento en vez de contenerlo.

¿Bloquea al agente? **Sí.** El `while True` corre entero dentro de `with self._lock:` (`hub.py:316`),
el mismo `RLock` que usa `ingest_alert_batch` (`hub.py:161`). Un purge de las 350 k filas de más de 30
días tendría al agente esperando **~9 minutos** con el lock tomado (7,6 s por lote medidos), y cada
lote hace `commit()` con `synchronous=FULL`. Además `run_in_executor` (`maintenance.py:103`) lo mueve
a un hilo, pero **no** libera el lock: solo evita bloquear el event loop, no el ingest.

**Consecuencia roadmap.** Tres arreglos, en este orden: (1) `QZERO_ALERT_RETENTION_DAYS` a 7–14 días
(medido: 30 días = 350 k filas, 512 B/fila → 7 días ≈ 82 k filas ≈ 42 MB, sostenible); (2) sacar el
`DELETE` del lock o partirlo en lotes con `commit()` y `await asyncio.sleep(0)` entre lotes;
(3) `PRAGMA auto_vacuum=INCREMENTAL` + `PRAGMA incremental_vacuum` periódico (o un `VACUUM` mensual
fuera de horario) — sin esto el disco nunca baja. La retención **no** es la solución al 93 % de disco.

---

## 6. Agente: cuántos reportan, intervalo, interfaz, promiscuo, alertas/hora

**Método.** `docker inspect` (env y estado), `docker logs`, `/sys/class/net/eno1/*`, y SQLite en
remoto (agregados + `GROUP BY` por hora, sin volcar filas).

**Evidencia.**
```
agents: nuke-agent-eth0 | Nuke | eno1 | last_seen 2026-10-23T06:17:29  (activo)
        qa-test         | ''   | ''   | last_seen 2026-09-05T20:12:51  (muerto hace 48 días, sin alertas)
alerts GROUP BY agent_id -> sólo nuke-agent-eth0: 1.778.916
env: QZERO_INTERVAL=5.0  QZERO_INTERFACE=eno1  QZERO_PROMISCUOUS=0
     QZERO_ALERT_THRESHOLD=4.2  QZERO_TRAIN_SAMPLES=2000  QZERO_USE_QIVAE=1  QZERO_USE_QSWM=0
     QZERO_HUB_URL=http://localhost:8000  (red=host, CapAdd=[CAP_NET_ADMIN,CAP_NET_RAW])
/sys/class/net/eno1/operstate=up ; flags=0x1003 (UP|BROADCAST|MULTICAST, sin 0x100 PROMISC)
state: StartedAt 2026-10-21T01:04:08Z  RestartCount=6
últimas 24 h: 203.344 alertas = 8.473/h  (pico 02:00 = 7.822/h, valle 17:00 = 5.746/h)
severidad 24 h: LOW 132.721 · HIGH 33.970 · CRITICAL 31.166 · MEDIUM 5.583
global:         LOW 1.200.998 · HIGH 287.877 · CRITICAL 240.866 · MEDIUM 51.897
```

**Respuesta.** **Un solo agente reporta de verdad** (`nuke-agent-eth0`: 1.778.916 de 1.778.916
alertas). `qa-test` es un resto de pruebas de 2026-09-05 con 0 alertas — y hoy **no se detectaría**
como caído, porque la liveness (`maintenance.py`) no está desplegada (§3). Intervalo: **5,0 s**.
Interfaz: **eno1**, `state=up`. **NO promiscuo** (`QZERO_PROMISCUOUS=0`, flags `0x1003` sin
`IFF_PROMISC`) — solo ve tráfico del propio host, lo que explica que casi todo sea
`192.168.50.5 → *`. Volumen: **~8.473 alertas/hora**, 203.344 en 24 h, **11,7 % de ellas CRITICAL**
(31.166). Con `QZERO_ALERT_THRESHOLD=4.2` y el `PostFilter` capando TLS a HIGH
(`preprocessing/postfilter.py:176-184`), las 31 k CRITICAL/24 h son casi todas tráfico interno
voluminoso — justo el caso de 30004/30008 de §1.

**Consecuencia roadmap.** 240 k CRITICAL acumuladas y 8,5 k alertas/h hacen imposible un digest "una
por alerta": el digest por lotes es obligatorio, y el "caso a revisar" de la consola debe agrupar por
(src,dst,dport) — en 1 h, `192.168.50.5→192.168.50.10:30004` sola genera 4.804 alertas. El
`RestartCount=6` del agente merece investigación aparte.

---

## Resumen de bugs confirmados (por gravedad)

| # | Fichero:línea | Bug | Impacto |
|---|---|---|---|
| 1 | `app.py:98-99` | Fail-**open**: sin `ADMIN_PASSWORD` deja pasar todo (verificado: 200 en `/api/v1/alerts`) | Crítico — auth inexistente por defecto |
| 2 | `app.py:81,90-92` | Ingest de alertas y heartbeat sin token por defecto | Crítico — inyección de alertas, liveness anulada |
| 3 | `auth.py:48-56,155` | Password en claro, **sin hash**, comparable desde el entorno | Alto — filtración vía `docker inspect` |
| 4 | `hub.py:316` | Purge entero dentro de `self._lock` (mismo lock que el ingest) | Alto — agente bloqueado ~9 min |
| 5 | `auth.py` (todo el módulo) | Sin rate limit ni lockout en `/api/v1/auth/login` | Alto — fuerza bruta ilimitada |
| 6 | `hub.py:302-335` | Sin `VACUUM`; `auto_vacuum=0` ⇒ el fichero nunca encoge | Alto — el disco sigue creciendo |
| 7 | `hub.py:353-358` | `mark_criticals_notified` sin `LIMIT` descarta CRITICAL >50 | Medio — pérdida silenciosa de alertas |
| 8 | `auth.py:155-156` | `TypeError`/500 con password no-ASCII | Medio — login roto / DoS trivial |
| 9 | `maintenance.py:100-101` | `last_purge` se actualiza antes de purgar | Medio — un fallo retrasa la purga 1 h |
| 10 | `predictor.py:667-673` | `results.json` truncado (113 B) ⇒ `/health` dice `not_trained` con modelos cargados | Medio — healthcheck miente |
| 11 | `maintenance.py:55-62` | `_parse_ts` asume tz del escritor = local | Bajo — falsos "agente caído" si cambia `TZ` |
| 12 | `auth.py:70-81` | Secreto efímero por proceso si falta `QZERO_AUTH_SECRET` | Bajo (latente con >1 worker) |
| 13 | `app.py:57-62` + `:96` | CORS `*` con middleware propio externo rompe preflight cross-origin | Bajo |
| 14 | `maintenance.py:67-79` | Markdown no escapado en el digest de Telegram | Bajo |

**NO VERIFICADO / pendiente.** Versión exacta de AdGuard Home (requiere auth). Tasa real de detección
(TP/FP) del VAE: no hay ground truth en `hub.db`. Causa del `RestartCount=6` del agente. Y todo §4/§5
es **código en git, no en producción**: hasta que no se redeploye desde main, la imagen viva sigue sin
auth, sin retención y sin liveness.
