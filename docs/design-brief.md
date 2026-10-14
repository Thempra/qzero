# QZero — Design Brief (consola SOC)

Estilo: **consola SOC oscura, moderno-formal y sobria** — tipo Wazuh/Elastic/Splunk, sin chrome de Streamlit (branding oculto vía CSS). Sin neón, sin bordes de colores; la jerarquía se marca con fondo y degradados sutiles. Acento **azul** (el verde se reserva para estados OK funcionales, no decorativo).

## 1. Paleta

| Token | Valor | Uso |
|---|---|---|
| `--bg-0` | `#0B0E14` | fondo global |
| `--bg-1` | `#11151F` | tarjetas / paneles |
| `--bg-2` | `#1A2030` | hover, filas alternas, inputs |
| `--border` | `#232A3B` | separadores 1px (nunca de color) |
| `--text-hi` | `#E6EAF2` | títulos, valores KPI |
| `--text-lo` | `#8B94A7` | etiquetas, metadatos |
| `--accent` | `#3B82F6` | acción, enlaces, pill activa, foco |
| `--sev-critical` | `#EF4444` | chip/barras CRITICAL |
| `--sev-high` | `#F97316` | HIGH |
| `--sev-medium` | `#EAB308` | MEDIUM |
| `--sev-low` | `#3B82F6` | LOW (mismo azul de acento) |
| `--ok` | `#22C55E` | solo online/sano (funcional) |

Degradados: solo verticales muy sutiles dentro de tarjetas (`--bg-1 → #0E1220`), para separar bloques sin líneas duras.

## 2. Tipografía y spacing
- UI/números: **Inter**; monoespaciada para IPs, puertos, scores, timestamps: **JetBrains Mono**.
- Escala: KPI 32/600 · títulos de sección 16/600 mayúsculas+letter-spacing 0.06em · cuerpo 14 · metadatos 12.
- Radius 8px tarjetas, 6px chips/botones. Padding de tarjeta 16–20px. Grid de 12 col, gap 16px.

## 3. Componentes

- **Header bar:** logo QZero (izq), badge de entorno (`PROD`), reloj live (mono), indicador `N agentes online` (punto verde/rojo + texto), botón **Refresh** (ghost con icono, spinner al pulsar).
- **Pills de navegación:** pastilla activa = fondo `--accent` texto blanco; inactivas = texto `--text-lo`, hover `--bg-2`. Sin subrayados.
- **KPI card:** valor grande arriba, delta/etiqueta abajo; borde izquierdo de 3px solo en la card CRITICAL (color severidad). Estados: carga (skeleton), sin datos (`—`).
- **Chip de severidad:** píldora sólida tintada (fondo 15 % del color, texto 100 %, radio completo). Mayúsculas 11px.
- **Tabla de alertas:** cabecera sticky, filas 40px, hover `--bg-2`, click expande panel de detalle inline (fondo `--bg-2`, mono para 5-tupla, bloque "Explicación" + "Acción sugerida").
- **Charts:** barras/apilados con los colores de severidad; ejes y gridlines en `--border`/`--text-lo`; tooltip `--bg-2`.
- **Agent card:** nombre (600), interfaz mono, `last_seen` relativo, barra de alerts propias; badge ONLINE/OFFLINE.
- **Empty states:** mensaje explícito + causa ("sin alertas en la ventana" vs "el hub reporta N totales — refresca"), nunca un cuadro vacío mudo.

## 4. Pantalla por pantalla

1. **Overview:** fila de 4 KPIs (total, critical, high, agentes) → grid 2×2: distribución por severidad (donas/barras), timeline 24 h (área, apilado por severidad), salud de agentes (lista compacta), top orígenes. Todo visible sin scroll en 1080p; scroll solo para detalle.
2. **Alerts:** barra de filtros arriba (severity, agente, minutos, búsqueda src/dst) + tabla densa; severidad como chip a la izquierda; src→dst en mono con flecha atenuada; paginación abajo.
3. **Threats:** tarjetas por tipo de amenaza con conteo + mini-sparkline; click filtra Alerts.
4. **Network:** top-talkers src-dst (barras horizontales) + matriz puertos; sin mapa geo en v3.
5. **Agents:** grid de agent cards (3/4 por fila); offline primero (gestión por excepción).
6. **Research:** lista de informes de modelo/entrenamiento; tarjetas ligeras título+fecha+link.

## 5. Prohibiciones
- Nada de verde neón, glow, bordes de colores decorativos ni glassmorphism.
- No sidebar (la navegación son pills superiores).
- No inventar datos en estados vacíos; el dashboard refleja siempre el estado real del hub.
