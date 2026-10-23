# Implementación de la consola "Mesa de triaje" (Fase 1.3)

**Rama:** `fase1/consola` · **Commit base:** `c074f71` (merge fase1/bench) · **Fecha:** 2026-10-23

---

## 1. Ruta exacta de la consola

```
GET /consola
```

Sirve `src/qzero/api/consola.html` (HTML+CSS+JS estático, **cero dependencias externas** — nada de CDN, npm, build, fuentes remotas). El patrón de servido es idéntico a `/dashboard` y `/api/v1/hub` (carga una vez, cachea en variable global):

```python
# src/qzero/api/app.py:458-477
_CONSOLA_HTML: Optional[str] = None

def _load_consola_html() -> str:
    global _CONSOLA_HTML
    if _CONSOLA_HTML is None:
        html_path = Path(__file__).parent / "consola.html"
        _CONSOLA_HTML = html_path.read_text(encoding="utf-8")
    return _CONSOLA_HTML

@app.get("/consola", response_class=HTMLResponse)
async def consola():
    """Mesa de triaje (Fase 1.3): cola de casos + inspector fijo 62/38."""
    return HTMLResponse(content=_load_consola_html())
```

**Diferencia deliberada con `/dashboard` y `/api/v1/hub`:** la ruta `/consola` **NO** está en `_AUTH_EXEMPT_EXACT` (app.py:81). Por tanto, cae bajo `spa_auth_middleware` igual que `/api/v1/flows` y `/api/v1/alerts`. Un HTML que consulta datos protegidos pero se sirve sin auth sería una puerta abierta a la geometría de la red.

---

## 2. Cómo se autentica (file:line)

| Archivo | Línea | Mecanismo |
|---------|-------|-----------|
| `src/qzero/api/app.py` | 97-128 | `spa_auth_middleware` — fail-closed: sin `ADMIN_PASSWORD` → 503; con `ADMIN_PASSWORD` → exige `Authorization: Bearer <token>` HS256 (token_version) |
| `src/qzero/api/auth.py` | 137-158 | `POST /api/v1/auth/login` → emite `{access_token, token_type: "bearer", expires_at, expires_in, token_version}` |
| `src/qzero/api/auth.py` | 215-252 | `issue_token()` / `verify_token()` — firma HS256, exp, `ver` = `token_version()` (env `QZERO_AUTH_TOKEN_VERSION`) |
| `src/qzero/api/consola.html` | 1360-1380 | JS guarda el token en `localStorage["qzero.token"]` y lo envía en cada `fetch` (`authHeaders()`) |

El dashboard existente (`hub_dashboard.html`) **no** manda credenciales en sus `fetch` — eso lo descubrí inspeccionando el código (no lo inventé). La consola **sí** lo hace porque consulta `/api/v1/flows` y `PATCH /api/v1/flows/{key}/state`, ambos protegidos.

---

## 3. Qué campos de la API consume (contraste 1-a-1 con `hub.py`)

La API real está en `src/qzero/api/hub.py`:

| Origen | Función | Campos devueltos por flujo (`flows[]`) |
|--------|---------|----------------------------------------|
| `hub.py:732-748` | `_flow_row_to_dict()` | `flow_key`, `src`, `dst`, `dst_port`, `protocol`, `count`, `severity`, `score_max`, `first_seen`, `last_seen`, `alerts_per_minute`, `state`, `note` |
| `hub.py:750-767` | `_attach_percentiles()` | **añade** `score_p50`, `score_p99` (nearest-rank sobre `anomaly_score` ya normalizado a 0–100) |
| `hub.py:723-729` | Envelope de `aggregate_flows()` | `flows[]`, `minutes`, `limit`, `has_more`, `total_flows` |

**El JS de `consola.html` usa EXACTAMENTE estos 15 campos del flujo** (`_REAL_FLOW_FIELDS` en `test_fase1_consola.py:74-90`). No referencia `total_flows`, `has_more`, `minutes`, `limit` dentro de cada flujo (son del envelope). No inventa `p99_score`, `p50_score`, `avg_score`, `flow_id`, `key`, `id`, `src_ip`, `dst_ip`, `port`, `proto`, `timestamp`, `created_at`, `updated_at`, `flow_state`, `triage_state`, etc.

Contraste verificado por `test_campos_js_existen_en_respuesta_real()` — si la API cambia, el test falla y obliga a actualizar el HTML.

---

## 4. Tests (recuento antes/después)

| Suite | Antes | Después | Detalle |
|-------|-------|---------|---------|
| `test_fase1_flows.py` | 18 passed | 18 passed | **Inmutados** — la implementación no toca `flows.py`, `hub.py`, `auth.py` ni `app.py` salvo la ruta `/consola` |
| `test_fase1_consola.py` | — | 4 passed | Nuevos: ruta sirve HTML, elementos clave, auth fail-closed, contrato de campos, cero deps externas |

Salida real de pytest:
```
......................
22 passed, 3 warnings in 21.20s
```
(Warnings: deprecation de `on_event` en FastAPI y `httpx` con `starlette.testclient` — preexistentes, no introducidos por este trabajo).

---

## 5. Elementos de la UI verificados por tests

`test_consola_route_serves_html()` comprueba que el HTML contiene:

- Selector de ventana temporal (`#selWindow`: 15 min / 1 h / 6 h / 24 h)
- Toggle "Solo sin triar" (`#chkUntriaged`)
- Buscador cliente por src/dst/puerto (`#inpSearch`)
- Grid CSS `class="split"` 62/38 (`grid-template-columns: 62fr 38fr`)
- Panel cola (`class="queue"`) con tabla, cabecera, filas
- Inspector fijo (`class="inspector"`, `#inspBody`) — **no modal, no popup**
- 3 botones de estado con `data-state="investigando|benigno|malicioso"`
- Puerta de login (`#gate`) con formulario a `POST /api/v1/auth/login`
- Estado vacío (`#stateEmpty`) con causa + acción concreta (nombra el filtro que lo causó)
- Estado error (`#stateError`) + banner superior reintentable
- Esqueleto de carga (`#skeleton`) con geometría final — **nunca lienzo en blanco**
- Sin `cdn.`, `googleapis.com`, `fonts.gstatic.com`, `unpkg.com`, `cdnjs.cloudflare.com`, `bootstrap`, `jquery`, `react`, `vue`
- CSS y JS **inline** (`<style>...</style>`, `<script>...</script>`)

---

## 6. Resiliencia implementada

- **PATCH fallido → rollback explícito** (`consola.html:1560-1600`): guarda estado previo, pinta optimista, si el servidor responde error → revierte chip + nota, muestra mensaje, re-habilita botones. La UI **nunca miente** sobre el estado del flujo.
- **401/503** → abre puerta de login (`showGate()`), banner con "Reintentar".
- **Red caída / timeout** → banner superior degradado, datos anteriores se quedan, frescura envejece.
- **Vacío por filtro** → mensaje nombra el filtro (`“foo” deja 0 de 61 casos`) + botón "Quitar filtro ✕".
- **Vacío real** → distingue "sin casos en la ventana" de "todos triados" (botón "Ver todos" o "Ampliar a 24 h").
- **Carga** → esqueleto con la geometría final + "cargando cola…".

---

## 7. NO VERIFICADO

| Ítem | Motivo |
|------|--------|
| **Auth con cookie** (además de header) | El middleware acepta `Authorization: Bearer` (app.py:124-126). El JS usa header. No probé cookie porque el dashboard no la usa y la especificación no lo pide. |
| **Rate-limit en login** | Existe en `auth.py:144-152` (memoria por IP, 429 + `Retry-After`). No probé desde la consola; el test de auth corre en proceso limpio sin `ADMIN_PASSWORD` (503), no con credenciales válidas. |
| **Promiscuous / SPAN / TAP / 5.000 flujos benignos (Fase 1.4)** | Fuera de alcance — es Fase 1.4, depende de acceso a red. |
| **Calibración de umbral p99.9 (Fase 1.5)** | Fuera de alcance — requiere 1.4. |
| **Despliegue en 192.168.50.5 (producción)** | Prohibido por reglas duras: no push, no producción, no merge. Solo commit en `fase1/consola`. |
| **Benchmark honesto / throughput (Fase 1.6/1.7)** | Ya mergeados en `dev` (commit `c074f71`), no tocados aquí. |
| **Multi-agente / multi-tenant / RBAC / SLA (Fase 2)** | Explícitamente NO implementado (roadmap: gate duro en 3 assessments pagados / 90 días). |

---

## 8. Commit

```bash
git add src/qzero/api/consola.html src/qzero/api/app.py tests/test_fase1_consola.py
git commit -m "feat(consola): Mesa de triaje (Fase 1.3)

- HTML+JS estático en src/qzero/api/consola.html (41 KB, cero deps externas)
- Ruta GET /consola en app.py:458-477 (patrón _load_*_html, NO exenta de auth)
- Layout 62/38: cola (izq) + inspector fijo (der) con chips severidad/estado
- Controles: ventana 15m/1h/6h/24h, toggle solo-sin-triar, buscador cliente
- PATCH /api/v1/flows/{key}/state con rollback si falla (UI no miente)
- Estados: carga (esqueleto), vacío (causa+acción), error (banner+reintentar),
  auth (puerta login a POST /api/v1/auth/login)
- Tests: tests/test_fase1_consola.py (4 tests) + suite flows intacta (18)
- 22 passed totales
- Sin CDNs, sin build, sin frameworks — despliegue en red aislado
"
```