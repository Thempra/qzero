# Error tracking — BugSink

QZero reporta sus errores a **BugSink** (`https://tracker.thempra.net`) por el
protocolo de Sentry. Proyecto en el tracker: **`qzero`** (id 6, team Thempra).

## Qué se envía

| Origen | Qué llega |
|---|---|
| API (`qzero-api`) | Excepciones no controladas en cualquier ruta, vía handler global |
| API | Fallos de retención, del digest de Telegram y de la consulta de agentes |
| API | Muerte del loop de mantenimiento (el `while True` que solo sale si algo lo rompe) |
| Agente (`qzero-agent`) | Errores de captura/análisis (`_analyze_window`) |

No se envían trazas de rendimiento (`traces_sample_rate=0.0`) ni datos
personales (`send_default_pii=False`).

## Configuración

Solo dos variables, y el tracker queda desactivado si falta la primera:

```bash
BUGSINK_DSN=https://<clave-publica>@tracker.thempra.net/6
APP_ENV=production        # environment en el tracker (por defecto QZERO_ENV)
QZERO_RELEASE=<sha>       # opcional, correlaciona errores con el commit
```

El DSN **no se versiona**: lleva la clave pública del proyecto, que basta para
inyectar eventos falsos. Se pasa por entorno, igual que `ADMIN_PASSWORD`.

En `docker-compose.yml` ya está cableado:

```yaml
- BUGSINK_DSN=${BUGSINK_DSN:-}
- APP_ENV=${QZERO_ENV:-production}
```

Para desplegar en Coolify: añadir `BUGSINK_DSN` a las variables del servicio
`qzero-api`. El agente lo lee del entorno del sistema (no está en compose).

## Filtro de ruido

`observability._ignorar` descarta `DisallowedHost`, `ClientDisconnected`,
`ConnectionResetError`, `BrokenPipeError` y `CancelledError`. Sin ese filtro el
tracker se llena de clientes que cortan la conexión y los fallos reales se
pierden entre ellos.

## Diseño

- **`init_sentry()` se llama al arrancar, no al importar.** Los tests importan
  `qzero.api.app` constantemente; inicializar al importar haría que cada
  `pytest` intentara hablar con un host externo.
- **Nunca tumba el proceso.** `sentry_capture()` envuelve todo en `try/except`
  y hace `flush(timeout=2)`: si el tracker no responde, se pierde el evento,
  no el servicio.
- **Captura explícita donde alguien se traga la excepción.** El loop de
  mantenimiento y el agente ya loguean y siguen; ahí `logger.warning` no basta
  porque nadie mira los logs hasta que algo se rompe de verdad.

## Verificación

```bash
# el módulo no se activa sin DSN
PYTHONPATH=src .venv/bin/python -c \
  "from qzero.api.observability import init_sentry; print(init_sentry())"   # False

# envío real
BUGSINK_DSN=... PYTHONPATH=src .venv/bin/python -c "
from qzero.api.observability import init_sentry, sentry_capture
init_sentry()
sentry_capture(RuntimeError('prueba'))"
```

Y comprobar el contador del proyecto:

```bash
curl -sS -H "Authorization: Bearer $BUGSINK_API_TOKEN" \
  https://tracker.thempra.net/api/canonical/0/projects/6/ \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['stored_event_count'])"
```

Tests: `tests/test_bugsink.py` (7 casos). Cubren desactivado sin DSN, DSN con
espacios, no-op al capturar desactivado, SDK que falla al enviar, 500 JSON del
handler global, y que la muerte del mantenimiento se reporta pero una
cancelación por apagado **no**.

## Nota sobre la API de BugSink

La API de gestión **no** está en `/api/0/` (devuelve
`Unimplemented API endpoint`), sino en `/api/canonical/0/`:

```bash
GET  /api/canonical/0/projects/          # lista
POST /api/canonical/0/projects/          # crear: {"team": "<uuid>", "name": "..."}
GET  /api/canonical/0/projects/<id>/     # incluye el DSN
GET  /api/canonical/0/teams/             # para el uuid del team
```

Los issues no se consultan por API en esta versión (endpoint no implementado);
se ven en la web del tracker.
