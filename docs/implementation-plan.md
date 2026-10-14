# QZero — Plan de implementación

Estado: **v3.0.0 en producción** (hub+dashboard en Nuke/Coolify, agente en `eno1`). Este plan cubre (A) el orden canónico de reconstrucción —para fork/rebuild desde cero— y (B) la hoja de ruta incremental v3.1 sobre lo existente. Cada paso tiene criterio de aceptación verificable.

## A. Secuencia de construcción (dependencias estrictas)

### Fase 1 — Datos y features
1. **Cargar UGRansome + sintético** (`data_loader.py`). ✔ *Check:* `pytest tests/ -k data_loader` pasa; DataFrame con 14 columnas estándar.
2. **Feature engineering** (PCA/MI → n_qubits, angle encoding [0,π]) ✔ *Check:* salida acotada en [0,π]; test unitario.
3. **FlowExtractor** con caps de tasa (1 GiB/s, 100k pkt/s) en `_to_dataframe`. ✔ *Check:* flujo de 1 paquete produce `bytes_per_sec ≤ 2^30`; test con pcap sintético.

### Fase 2 — Modelos
4. **QI-VAE** (PyTorch) + umbral calibrado (`calibrate_threshold.py`). ✔ *Check:* score en dataset de prueba acotado (sin valores >1e6 en tráfico real de muestra).
5. **QSVM + feature maps** (Qiskit) + baselines clásicos. ✔ *Check:* informe `model-performance-reports/` con F1/ROC-AUC/FPR comparado vs baselines.

### Fase 3 — Post-filtro (aquí vive la precisión real)
6. **PostFilter** completo: suppressiones (DNS, local, broadcast 1–2 pkt, HTTPS sin payload), `whitelist_private=False`, `severity_for` con tope HTTPS (`https_volume_cap_score=5.0`, comprobar 443 en **src y dst**). ✔ *Check:* `tests/test_postfilter_nmap.py` verde; broadcast unicástico NO suprimido (SYN de nmap sobrevive).

### Fase 4 — Hub
7. **HubStore SQLite** + migraciones idempotentes + endpoints ingest/heartbeat/query/summary. ✔ *Check:* `curl` batch → `summary.total_alerts` sube; reopen de BD existente no rompe (migración in-place).

### Fase 5 — Agente
8. **Loop de captura** (scapy → extract → score → filter → POST lote + heartbeat + buffer en disco). ✔ *Check:* QA end-to-end: baseline `summary` → `sudo nmap -sS -Pn -T4 -F target` → alertas CRITICAL visibles en ≤2 ventanas; muestreo previo de FP: CRITICAL cae ~70–80 % vs sin filtro sin perder señal no-HTTPS.

### Fase 6 — Dashboard
9. **Consola SOC** según `flow.md` + `design-brief.md` (pills, KPIs, chips, detalle intel). ✔ *Check:* screenshot vs design brief; ventana vacía muestra aviso, no "0 amenazas" falso.

### Fase 7 — Deploy
10. **Coolify**: `qzero-api` + `qzero` (Traefik `Host(qzero.thempra.net)`, TLS) y `qzero-agent`. ✔ *Check:* `/health` 200; merge a `main` + push por SSH (token HTTPS muerto); si el 1er build falla (`No such container`/OOM) reintentar deploy; healthchecks Docker en verde.

## B. Hoja de ruta v3.1 (incremental, en orden)

| # | Tarea | Depende de | Aceptación |
|---|---|---|---|
| 1 | Rotación/retención de `alerts` (p. ej. `QZERO_ALERT_RETENTION_DAYS`, borrado por lotes en heartbeat) | — | BD < umbral tras config; test con BD falsa antigua |
| 2 | Notificación externa de CRITICALs a Telegram (rate-limited, resumen no por-alerta) | 1 | Mensaje real al trigger nmap; sin spam en tormenta de FP (verificar con sample real) |
| 3 | Auth app-level del dashboard (login token SPA, `ADMIN_PASSWORD` por env fail-closed, refresh por `token_version`; NUNCA Basic Auth) + `X-Agent-Token` opcional en ingest | — | 401 sin token; agente viejo sigue si `QZERO_REQUIRE_AGENT_TOKEN=0` |
| 4 | Enriquecimiento persistido (cache org/ASN por IP en tabla `ip_intel`) | 1 | `/alerts/recent` sin latencia de WHOIS; dashboard sin llamadas externas síncronas |
| 5 | Umbral/severidad **por agente** (override en heartbeat) | 1 | DMZ con IP pública puede activar `whitelist_private=True` por agente sin afectar LAN |
| 6 | Reentrenamiento programado + informe automático (cron → `model-performance-reports/`) | — | Informe nuevo fechado; diff de F1 vs modelo en producción |

## Reglas de ejecución
- Construir estrictamente en orden A1→A10 (o B1→B6); si la realidad fuerza un cambio, actualizar el doc afectado **en el mismo commit**.
- Desplegar solo desde `main` (auto-deploy); nunca fusionar dev→main sin pedirlo.
- Toda "mejora de detección" se valida con el workflow QA del skill `qzero-ndr`: baseline → trigger nmap → comparar antes/después con datos reales.
