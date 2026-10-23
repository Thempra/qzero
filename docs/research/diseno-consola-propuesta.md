# QZero — Rediseño conceptual de la consola SOC y la landing

**Estado:** propuesta para decisión. **Fecha:** 2026-10-23. **Autores:** panel de dos roles (A: producto/UX senior en herramientas SOC · B: ingeniería frontend con el stack real).
**Base de evidencia:** `~/.hermes/cache/qzero-evidence-2026-10-23.md` (citado como *dossier §n*), capturas `qzero-dash-25s.png` y `qzero-landing-1440.png` analizadas con visión, y lectura directa del código en `/home/hermes/qzero`.
**Regla de este documento:** toda cifra lleva fuente. Lo que no está medido se marca **NO VERIFICADO** con el método de comprobación.

---

## 1. Concepto

### 1.1 El diagnóstico, en una frase

La consola actual no es una consola: es un **contador de sucesos**. Su portada abre con 1.724.426 alertas y 232.878 CRITICAL (dossier §3.5; captura: 5 tarjetas KPI en `app/dashboard.py:318`). Un operador no puede actuar sobre 232.878 de nada. El propio backend lo confirma por la vía de los hechos: de 1.723.099 filas, el 67,5 % son LOW y **siete flujos** (suma de las cifras del dossier §3.4: 226.031 + 130.893 + 70.834 + 61.962 + 57.261 + 33.000 + 33.000 = **612.981**, el 35,6 % del histórico) explican más de un tercio de todo lo almacenado. Siete flujos. La consola los aplasta en un donut y los cuenta.

La lentitud percibida no es del backend: `summary` responde en 1–2 ms y `recent` en 60–90 ms (dossier §6). Los 20–25 s de primer render (dossier §3.5) son **de la capa Streamlit**: cinco KPI + dos gráficos Plotly + tres tablas `st.dataframe` en un solo script que se re-ejecuta entero, con `enrich_alert()` llamado alerta a alerta (`app/dashboard.py:353`) y `asn_lookup()` abriendo sockets con `timeout=3` dentro del camino de render (`app/intel.py:69`). **Hipótesis de código, no medida aislada**: se comprobaría instrumentando `time.perf_counter()` alrededor de las líneas 210–221 y 353 de `app/dashboard.py`.

### 1.2 La tesis

> **La unidad de trabajo deja de ser la alerta y pasa a ser el caso de flujo.**
> La consola no muestra lo que el motor emitió; muestra **lo que queda por decidir**.

Tres movimientos, y ninguno es cosmético:

1. **Colapsar.** 1.723.099 alertas se agregan por 5-tupla `(src, dst, dst_port)` en *casos*. Un caso tiene: cardinalidad, primera/última vez, distribución de score (p50/p99/máx), y un **estado de ciclo de vida** (`nuevo → en revisión → silenciado | resuelto`). La portada enseña decenas de casos, no millones de alertas. La alerta sobrevive como **evidencia** dentro del caso, no como feed.
2. **Separar rareza de volumen.** Hoy un backup interno (`192.168.50.5 → 192.168.50.10:30004`, 226.031 alertas, score máx 1,9e9 — dossier §3.4) y un escaneo real comparten la misma columna `anomaly_score` sin cota. Se parte en dos ejes legibles: **rareza** (percentil de score normalizado, 0–100) y **volumen** (alertas/min). El backup cae en *volumen alto / rareza baja*: la consola pide confirmación humana, no grita CRITICAL. Esto no arregla el modelo (fuera de alcance, §8); arregla **cómo se lee**.
3. **Decidir.** Cada caso tiene tres acciones: *Silenciar* (allowlist por 5-tupla, con caducidad), *Investigar* (abre el caso, lo marca en revisión), *Escalar*. Un caso tocado sale de la cola. La portada puede llegar a decir **"0 casos pendientes"** — un estado que hoy el producto no sabe expresar.

Nombre de trabajo del concepto: **Mesa de triaje**. No "dashboard". La landing hereda el mismo giro: deja de vender "detecta antes de la firma" (afirmación que el propio repo desmiente: QSVM F1 0,711 vs svm_linear 0,707, dossier §4) y pasa a vender **"de 1,7 M de alertas a una cola que se termina"**, con el caso real del backup como prueba.

### 1.3 Registro del debate A ↔ B (lo que se discutió y cómo se resolvió)

| # | Propone A (producto/UX) | Responde B (frontend) | Veredicto |
|---|---|---|---|
| 1 | Reescribir la consola en HTML+JS servido por FastAPI; Streamlit no da para esto. | Ya existe el patrón: `src/qzero/api/app.py:373` sirve `hub_dashboard.html` (103 líneas) desde la API. Pero duplicar la consola significa mantener dos UIs y perder `st.dataframe`/Plotly gratis. | **Híbrido con alambre de disparo** (§9). Streamlit primero, con criterios de aceptación duros; si en la fase 2 no se cumple p95 ≤ 1,5 s, se migra el *shell* a HTML estático servido por FastAPI y Streamlit queda solo para Research. |
| 2 | Sidebar con navegación persistente. | Contradice `docs/design-brief.md` §5 ("No sidebar") y obliga a re-maquetar el CSS de `#MainMenu` ya oculto (`app/dashboard.py:67`). | **Rechazado**: navegación superior de 4 pills. Menos secciones, no más barra. |
| 3 | Panel de detalle en modal/overlay. | Streamlit no tiene modal nativo; `st.dialog` existe (≥1.34) pero rompe "campos de detalle siempre visibles" (preferencia del dueño) y pierde el contexto de la fila. | **Rechazado**: maestro-detalle en dos columnas fijas (62/38), el detalle **siempre pintado**, con el último caso seleccionado o el primero de la cola. Cero clics para ver detalle. |
| 4 | Filtros como multiselect en la cabecera de la tabla. | `st.multiselect` dispara rerun global y no comunica cuánto ocultó. | **Aceptado con cambio**: un único control *Preset de triaje* (Todo / Accionable / En revisión / Silenciados) + chips de filtro activos con `✕`, y un **contador de resultado que cambia** ("14 de 61 casos"). El filtro oculta visiblemente o no es filtro. |
| 5 | Agregación en pandas sobre las 500 alertas de `/alerts/recent`. | `app/dashboard.py:353` ya hace eso y es parte del coste de render; 500 filas solo cubren una ventana arbitraria (la API topa en `limit=500`, `src/qzero/api/app.py:359`). Agregar en el cliente es agregar la muestra, no la realidad. | **Rechazado**: se añade `GET /api/v1/flows` con `GROUP BY src,dst,dst_port` en SQL (§7). Sin endpoint nuevo no hay portada honesta. |
| 6 | Gráficos Plotly con la toolbar dentro de la tarjeta. | La toolbar ya sale en la captura y compite con el título (dossier §3.5), y `threat_type_bar` usa una escala continua naranja→amarillo→índigo (`app/dashboard.py:251-253`) que codifica magnitud con color decorativo. | **Aceptado**: `config={"displayModeBar": False}`, y como máximo **dos** gráficos en portada. El resto, tabla. |
| 7 | Tokens del `design-brief.md` tal cual. | El CSS real no los cumple: acento `#6366f1` (índigo) en `app/dashboard.py:80,100` vs `#3B82F6` del brief; `LOW` pintado `#eab308` amarillo (`app/dashboard.py:58`) cuando el brief reserva el azul para LOW. Por eso el donut de la captura es un sol amarillo del 67,5 %. | **Aceptado**: se fija la paleta en §5 y se corrige la deriva. El amarillo deja de existir como color de severidad. |
| 8 | Estado vacío con ilustración. | Peso de assets y cero información. | **Rechazado**: estado vacío = frase + causa + acción concreta (§6). |

---

## 2. Arquitectura de información

Seis módulos actuales (`Overview / Alerts / Threats / Network / Agents / Research`, `app/dashboard.py:277`) se reducen a **cuatro**, porque *Threats* y *Network* son dos cortes del mismo ledger y su separación obliga al operador a reconstruir el caso a mano.

```
MESA DE TRIAJE (portada)
├── Barra de estado: frescura de datos · agentes online · preset de triaje
├── Cola de casos (izq. 62 %)  ── filas = casos, no alertas
│   └── chips: severidad · rareza · volumen · estado
└── Inspector (der. 38 %)      ── SIEMPRE visible
    ├── identidad del caso (5-tupla, mono)
    ├── por qué puntuó (explicación determinista de app/intel.py)
    ├── evidencia: últimas N alertas del caso
    └── acciones: Investigar · Silenciar · Escalar

CASO (drill-down de una fila)
├── cabecera con estado y acciones
├── serie temporal del caso (alertas/min, 24 h)
├── tabla de alertas del caso (paginada, server-side)
└── destinos resueltos (org/ASN si el enriquecimiento está fresco)

FLOTA
├── agentes con ciclo de vida: activo ·silencioso · cuarentena
└── por agente: interfaz, alertas/día, último heartbeat, umbral efectivo

MOTOR (antes "Research")
├── benchmarks con sus cifras reales y su fecha
└── estado del modelo en producción (y si no hay: lo dice)
```

Regla transversal: **todo número de la UI viaja con su fuente y su hora**. "Datos de hace 12 s" es un dato de producto, no un detalle.

---

## 3. Wireframes textuales, pantalla por pantalla

### 3.1 Portada — Mesa de triaje (1440×900, sin scroll para lo esencial)

```
┌───────────────────────────────────────────────────────────────────────────────┐
│ ◈ QZero · TRIAJE      PROD   [hace 8 s ⟳]    ● 1/2 agentes   [Actualizar]     │  h=56
├───────────────────────────────────────────────────────────────────────────────┤
│ [Triage] [Flota] [Motor]                                    preset: (●) Accionable  ( ) Todo  ( ) Silenciados │
├──────────────────────────────────────────────┬────────────────────────────────┤
│ Pendientes 12 · En revisión 3 · Silenciados 9│  CASO 192.168.50.5 → 192.168.50.10:30004 │
│ Histórico 1.723.099 (nota al pie, no KPI)    │  INTERNAL · TCP · interno                  │
│                                              │  ── Lectura ──────────────────────────────  │
│ ┌── Casos ────────────────────────────────┐  │  Volumen ████████████ alto (226.031)        │
│ │ SEV   RAREZA  FLUJO                 VOL │  │  Rareza  ██░░░░░░░░░░ bajo                  │
│ │ ───   ──────  ───────────────────── ─── │  │  → "Volumen sin rareza: patrón de réplica   │
│ │ HIGH  72 ▮▮▮  10.0.1.7:51544→…:443  811 │  │     o backup. No es firma de ataque."       │
│ │ CRIT  98 ▮▮▮▮ 45.9.1.2→10.0.1.9:22   19 │  │  ── Evidencia (12 de 226.031) ─────────────  │
│ │ MED   41 ▮▮   10.0.1.4:…→8.8.8.8:53   6 │  │  22:57:01  score 1.9e9  TCP 1.4 MB          │
│ │ ...                                      │  │  22:56:59  score 1.8e9  TCP 1.4 MB          │
│ └─────────────────────────────────────────┘  │  ── Acciones ──────────────────────────────  │
│ Mostrando 12 de 61 casos · filtro: Accionable ✕│  [Investigar] [Silenciar 7 d ▾] [Escalar]  │
└──────────────────────────────────────────────┴────────────────────────────────┘
```

Decisiones que se ven en el dibujo: (a) el KPI "232.878 críticas" desaparece de la portada y queda como *nota al pie del histórico*; (b) la cola son casos; (c) el inspector está poblado **antes** de que el usuario toque nada; (d) el filtro activo se anuncia con su efecto ("12 de 61").

### 3.2 Caso

```
┌ ✔ Caso #A41 · 192.168.50.5 → 192.168.50.10:30004        [En revisión]  [Cerrar]
├ Serie 24 h (alertas/min, pico marcado) ────────────────────────────────
├ Alertas del caso: 226.031 · mostrando 1–50        [◀ ▶]  pág. 1 / 4.521
│  ts (UTC)          sev   score    proto  bytes
│  22:57:01.412      HIGH  1.9e9    TCP    1.4 MB
├ Por qué: explicación determinista del clasificador (app/intel.py)
└ Nota de triaje (texto libre, se guarda con el caso)
```

### 3.3 Flota

```
┌ Agentes ────────────────────────────────────────────────────────────────
│ ● Nuke      eno1   1.724.426 alertas   hb hace 8 s    umbral 4,2
│ ○ qa-test   —      0 alertas           hb hace 47 d   CUARENTENA (¿borrar?)
│ ────────────────────────────────────────────────────────────────────────
│ 1 activo · 1 en cuarentena · 0 silenciosos
```
El zombie deja de contarse como "offline" y entra en un estado explícito con la acción de borrado al lado (dossier §3.4).

### 3.4 Motor

Benchmarks reales con su fecha, la comparación QSVM/svm_linear en la misma tabla, y una línea explícita si `production` está vacío (dossier §4, `retrain-latest.json`). Nada de porcentajes de `docs/PRESENTATION.md` que ningún informe respalda (dossier §4).

### 3.5 Landing (`docs/index.html`, 563 líneas, hoy 7 secciones)

Se mantiene el orden de anclas (`#run`, `#how`, `#screens`, `#truth`, `#install`, `docs/index.html:242-406`) y se sustituye el contenido del hero y se añaden dos bloques. La zona muerta que reporta la visión (70–80 % de la altura total sin contenido pintado) es en parte artefacto de captura headless, pero el ritmo vertical es real: hay que meter contenido en el tramo medio.

```
1. HERO   "1.723.099 alertas. 7 flujos. Una cola de 12 casos."
          subtítulo: NDR autoalojado que agrega por flujo y pide decisión,
          no que dice "crítico" 232.878 veces. CTA único.
2. PRUEBA (nuevo, ocupa el hueco muerto) — "El caso del backup": la misma
          captura del inspector, con el flujo de 226.031 alertas clasificado
          volumen-alto/rareza-baja. Honesto y específico: nadie más lo enseña.
3. QUÉ NO HACE  tres líneas: sin IPS, sin multi-tenant, sin firma.
4. #run   demo de scoring real (se conserva: es el activo más fuerte)
5. #how   tres pasos
6. #screens  seis pantallas → cuatro (coherente con §2)
7. #truth  tabla de benchmarks (se conserva; es la mejor sección de la página)
8. #install  comandos + "abrir consola en vivo"
9. CIERRE  CTA
```
Se añade, junto a `#install`, el diagrama de captura (SPAN/TAP vs inline) que hoy no existe y que un CISO pregunta en la primera reunión (dossier §3.6).

---

## 4. Tokens visuales

| Token | Valor | Uso | Nota |
|---|---|---|---|
| `--bg-0` | `#0B0E14` | fondo | ya en `.streamlit/config.toml` |
| `--bg-1` | `#11151F` | tarjetas | |
| `--bg-2` | `#1A2030` | hover, fila seleccionada, inputs | |
| `--border` | `#232A3B` | separador 1 px | nunca de color |
| `--text-hi` | `#E6EAF2` | títulos y valores | |
| `--text-lo` | `#8B94A7` | etiquetas, metadatos | |
| `--accent` | `#3B82F6` | acción, pill activa, foco | corrige el `#6366f1` actual (`app/dashboard.py:80,100`) |
| `--sev-critical` | `#EF4444` | chip CRITICAL | |
| `--sev-high` | `#F97316` | chip HIGH | |
| `--sev-medium` | `#EAB308` | chip MEDIUM | único uso legítimo del amarillo |
| `--sev-low` | `#3B82F6` | chip LOW | alinea con brief; elimina el amarillo dominante del donut |
| `--ok` | `#22C55E` | solo heartbeat/sano | funcional, no decorativo |
| `--grad-card` | `linear-gradient(180deg,#11151F,#0E1220)` | fondo de tarjeta | degradado = marca de bloque, sin borde |
| `--grad-inset` | `linear-gradient(90deg,#141A26,#101622)` | inspector | separa sin línea dura |
| `--radius-card` / `--radius-chip` | `8px` / `6px` | | |
| tipografía | Inter (UI) · JetBrains Mono (IPs, puertos, score, ts) | | `tabular-nums` obligatorio en cifras |
| escala | 32/600 KPI · 16/600 sección (mayúsculas, `letter-spacing .06em`) · 14 cuerpo · 12 meta | | |

Dos reglas de color que hoy se incumplen y se corrigen: **ningún color codifica magnitud** (adiós escala continua naranja→índigo de `app/dashboard.py:251-253`), y **ningún estado se comunica solo por color** (§7, A11y).

---

## 5. Estados: vacío, error, carga, degradado

| Estado | Texto y forma | Regla |
|---|---|---|
| Vacío real (sin casos) | "No hay casos pendientes. 61 alertas en la última hora quedaron silenciadas; 0 superaron el umbral de triaje." + `[Ver silenciados]` | Nunca un cuadro en blanco. Siempre causa + siguiente acción. |
| Vacío por filtro | "`Accionable` deja 0 de 61 casos. `[Quitar filtro ✕]`" | El vacío **nombra el filtro que lo causó** (hoy: `st.caption("Sin coincidencias.")`, `app/dashboard.py:458`). |
| Cargando (primer render) | Esqueleto con la geometría final (filas grises de 40 px, chips en gris) + "cargando cola…" y contador de segundos | Prohibido lienzo vacío 20 s. |
| Refresco (datos en vuelo) | La tabla anterior se queda, con `--ok` pulsando en la barra de frescura | Nunca blanquear lo que ya se ve. |
| Error de API | Banda superior: "Sin datos del hub desde hace 3 min · último dato 23:07:41" + `[Reintentar]`; los números pasan a `—`, no a 0 | Distinguir *cero* de *desconocido*. Hoy 0 y fallo se pintan igual. |
| Degradado | "Enriquecimiento no disponible: destinos sin org/ASN" en la barra, y la columna Destino muestra `—` | Ya existe el `st.info` (`app/dashboard.py:367`) pero se pinta en el cuerpo y desplaza la maqueta. |
| Sesión/auth | Login en el cuerpo centrado, no en `st.sidebar.form` (`app/dashboard.py:182`) | Coherencia con "no sidebar". |

---

## 6. Criterios de aceptación medibles

| ID | Criterio | Cómo se mide | Umbral |
|---|---|---|---|
| AC-1 | Primer pintado con datos, en frío | CDP `settleMs`, 5 pasadas, mediana | **≤ 2,5 s** (hoy 20–25 s, dossier §3.5) |
| AC-2 | Cambio de preset de triaje | CDP, del clic al DOM estable | **p95 ≤ 1,5 s** |
| AC-3 | Portada sin scroll en 1440×900 | captura + comprobación de `scrollHeight` | `scrollHeight ≤ clientHeight` |
| AC-4 | Casos visibles en portada | contar filas renderizadas | **≤ 30**, y 0 cifras de 7 dígitos como KPI |
| AC-5 | Filtro oculta visiblemente | aplicar y contar | el contador pasa de `N de M` a `n de M` con `n < N`, en el mismo viewport; el chip `✕` es clicable |
| AC-6 | Detalle siempre visible | cargar portada y fotografiar sin interacción | inspector con contenido en el **primer** frame tras AC-1 |
| AC-7 | Trazabilidad | inspección | todo número tiene endpoint + timestamp de origen a ≤ 1 clic o visible en la barra de frescura |
| AC-8 | Sin cromo Streamlit | captura | 0 elementos `#MainMenu`, footer, toolbar de Plotly, "Running…" visibles |
| AC-9 | Contraste | cálculo WCAG sobre tokens | texto ≥ 4,5:1; texto grande ≥ 3:1 |
| AC-10 | No solo color | revisión manual | cada severidad lleva texto (`CRIT`) además del color; probado en deuteranopía simulada |
| AC-11 | Endpoint de agregación | `curl -w %{time_total}` | `/api/v1/flows?minutes=1440` **≤ 300 ms** con 1,7 M filas |
| AC-12 | Cero fugas de detalle técnico | `grep` en config | `showErrorDetails` deja de ser `"full"` (`.streamlit/config.toml:15`) |
| AC-13 | Landing: sin hueco muerto | full-page screenshot | ninguna franja > 600 px sin contenido pintado a 1440 px de ancho |

---

## 7. Contrato técnico mínimo (lo que B exige para poder firmar)

1. **`GET /api/v1/flows`** en `src/qzero/api/hub.py`: `SELECT src,dst,dst_port,COUNT(*) n,MIN(ts),MAX(ts),AVG/MAX(anomaly_score) FROM alerts WHERE timestamp>=? GROUP BY 1,2,3 ORDER BY n DESC LIMIT 200`. Con `idx_alerts_ts` ya existente (SCHEMA, `hub.py:44`). Sin esto, la portada sigue agregando una muestra de 500 (`app/dashboard.py:221`).
2. **Estado de caso persistido**: tabla `flow_state(flow_key, state, note, silenced_until, updated_at)`. Es la única escritura nueva; sin ella "Investigar/Silenciar" son botones muertos.
3. **Enriquecimiento fuera del render**: `asn_lookup` (`app/intel.py:58`) no puede estar en el camino crítico; usar la tabla `ip_intel` ya codificada (dossier §3.1: existe en git, **no desplegada**) o un worker.
4. **`st.fragment(run_every=…)`** para la barra de frescura y `st.dataframe(on_select="rerun")` para la selección de fila: exige subir el pin de `streamlit>=1.30.0` (`requirements.txt:43`) a **≥1.42**.
5. **Caché**: `ttl` de 2–3 s (`app/dashboard.py:210-221`) pasa a 10 s + refresco explícito; el precio de la frescura se paga en el backend (1–2 ms, dossier §6), no en cada interacción.

---

## 8. Qué NO se hace (y por qué)

- **No** se toca el modelo, el umbral 4,2 ni el post-filtro. El score sin cota (1,9e9, dossier §3.4) es un defecto de motor; aquí se **normaliza para leer**, no se corrige. Mezclar ambas cosas haría la propuesta no evaluable.
- **No** respuesta activa / IPS, ni bloqueo real desde la UI: fuera de alcance declarado en PRD v3. Enviar a un `fail2ban` es fase posterior.
- **No** multiusuario, RBAC ni auditoría de acciones. Un solo operador. (Consecuencia asumida: "Silenciar" es global.)
- **No** mapa geográfico, ni topología animada, ni grafos de fuerza. Cero valor de decisión por píxel.
- **No** tiempo real por WebSocket. Sondeo de 10 s: el feed ya es de alta latencia semántica.
- **No** modo claro, ni selector de tema, ni animaciones de entrada.
- **No** sidebar (contradice `docs/design-brief.md` §5 y ya hay CSS que la oculta).
- **No** emojis como iconos (hoy: `🟢 online`, `❓ ¿Qué es y qué hacer?`, `🔬 Research`, `📊/🤖/⚛️` en pestañas — `app/dashboard.py:385,475,640,673`).
- **No** infinite scroll ni virtualización de 1,7 M filas: paginación server-side.
- **No** se reescriben las seis pantallas de la landing con capturas nuevas hasta que la consola nueva exista; las actuales (`docs/assets/*.webp`) muestran la UI vieja.
- **No** se publican cifras de `docs/PRESENTATION.md`. Si la landing necesita un número, sale de `model-performance-reports/` con fecha.

---

## 9. Plan de aterrizaje y alambre de disparo

| Fase | Alcance | Archivos | Salida medible |
|---|---|---|---|
| 0 | Instrumentar el render actual (dónde se van los 20 s) | `app/dashboard.py` (perf_counter temporal) | tabla de tiempos por bloque |
| 1 | Endpoint `/v1/flows` + tabla `flow_state` | `src/qzero/api/hub.py`, `app.py` | AC-11 verde |
| 2 | Portada Mesa de triaje (cola + inspector fijo) sobre Streamlit ≥1.42 | `app/dashboard.py`, `.streamlit/config.toml` | AC-1, AC-2, AC-3, AC-4, AC-6 |
| 3 | Presets de triaje + estados vacío/error/carga | `app/dashboard.py` | AC-5, §5 completo |
| 4 | Flota con cuarentena · Motor con cifras reales | `app/dashboard.py` | zombie fuera de "offline" |
| 5 | Landing: hero nuevo + bloque de prueba + diagrama de captura | `docs/index.html` | AC-13 |
| **Disparo** | Si al cerrar la fase 3 AC-2 > 1,5 s en 2 de 3 intentos | — | migrar el shell a HTML estático servido por `app.py` (patrón `hub_dashboard.html`), Streamlit solo Motor |

---

## 10. Riesgos abiertos (no maquillados)

1. **El caso "backup benigno" es interpretación del dossier** (§3.4: "flujos de volumen legítimo (backups, réplica, Grafana)"), **NO VERIFICADO** contra los procesos reales de Nuke. Comprobación: `ss -tnp` en `192.168.50.5` filtrando `:30004` y `:30008`. Si resulta ser un servicio legítimo, la landing puede usarlo; si no, el bloque 2 cambia a un caso sin veredicto.
2. **`/api/v1/flows` sobre SQLite sin índice compuesto** puede no cumplir 300 ms con 1,7 M filas. Mitigación: índice `(dst_port, src, dst)` o tabla materializada por ventana. Medir antes de prometer.
3. **El estado de caso en SQLite** convive con retención de 90 d (`QZERO_ALERT_RETENTION_DAYS`, dossier §5): un caso silenciado cuyo flujo purga pierde la evidencia. Decisión pendiente: la allowlist debe sobrevivir a la purga.
4. **La consola es pública sin login** (dossier §3.3) y esta propuesta añade acciones de escritura (silenciar). Publicar escritura sin auth es peor que publicar lectura: **bloqueante** antes de fase 2. `auth.py` existe en git y no está desplegado (dossier §3.1).
