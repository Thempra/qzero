# QZero — App Flow (flujos, navegación y triggers)

Dos sistemas con flujo propio: el **agente** (sin UI, flujo de datos) y la **consola SOC** (flujo de usuario).

## 1. Flujo del agente (pipeline de datos, continuo)

```
[arranque] → cargar modelo (QZERO_MODEL_DIR) → registrar (heartbeat)
   → LOOP cada QZERO_INTERVAL (5 s):
      1. Sniff ventana de paquetes (Scapy, interfaz, promiscuo opcional)
      2. FlowExtractor: paquetes → flujos (14 features, caps de tasa)
      3. Modelo: anomaly_score por flujo
      4. score < QZERO_ALERT_THRESHOLD → descartar
      5. PostFilter.should_suppress(flow, score) → SUPRIMIDA (a log) o continúa
      6. PostFilter.severity_for(flow, score) → LOW/MEDIUM/HIGH/CRITICAL
         (reglas de supresión y topes de severidad: fuente única en TRD §5)
      7. POST /api/v1/agents/{id}/alerts (lote, con detail: bytes/s, pkts/s, org)
         - fallo de red → escribir en QZERO_BUFFER_DIR y reintentar
      8. POST .../heartbeat
```

**Trigger externo clave:** tráfico anómalo (p. ej. `nmap -sS`) → en ≤2 ventanas aparece como alerta CRITICAL en el hub.

## 2. Flujo del hub (ingestión)

1. `POST /alerts` → validar payload → INSERT por alerta + upsert `agents.last_seen` → recalcular contadores → 200 `{ingested, total}`.
2. `summary` → consulta O(1) de totales por severidad.
3. Migración de esquema automática al abrir la BD (columnas `packets`, `detail`).

## 3. Flujo del usuario — Consola SOC (`qzero.thempra.net` → `/dashboard`)

### Navegación (pills superiores, sin sidebar)
`Overview · Alerts · Threats · Network · Agents · Research` + barra cabecera: marca, badge de entorno, reloj live, **agentes online**, control global de refresh.

### Pantalla por pantalla

**Overview (landing):**
- KPIs: total alertas, CRITICAL/HIGH/LOW del periodo, agentes online/total.
- Distribución por severidad (chart), timeline de alertas, salud de agentes.
- *Botón Refresh:* re-fetch `hub/summary` + `alerts/recent` y re-render (st.rerun).
- *Selector de ventana (minutes):* cambia `?minutes=N` de `alerts/recent`; si viene `[]` pero `summary.total>0`, mostrar aviso "agente inactivo / ventana vacía", nunca "sin amenazas".

**Alerts:**
- Tabla filtrable por severidad / agente / rango horario; cada fila: timestamp, src→dst, puertos, proto, paquetes, score, severidad (chip de color).
- *Click en fila / expand:* detalle enriquecido por `intel.py` — dirección in/out, organización del IP remoto, tipo de amenaza, explicación ("scan de puertos desde X hacia Y en el puerto Z") y recomendación.

**Threats:** agrupado por tipo de amenaza detectada (scan, exfil sospechosa, puerto insólito…), conteos y drill-down a Alerts filtrada.

**Network:** heat/top-talkers por par src-dst y por puerto; entrada para diagnosticar ruido.

**Agents:** tarjeta por agente: nombre, interfaz, first_seen, last_seen, alerts propias; badge online si heartbeat < umbral, offline si excede.

**Research:** enlaces/informes de rendimiento del modelo (model-performance-reports, training-health).

### Reglas de interacción
- Toda acción es *read-only* sobre el hub: el dashboard **no** modifica ni borra alertas.
- El refresh global es el único "botón de acción" persistente; el resto son filtros/expand.
- Sin auth en v3 (perímetro de red). Si se activa (PRD Q2), el flujo completo es propiedad de `backend-schema.md §2` — no duplicarlo aquí.
