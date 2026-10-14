# QZero — Plan de implementación

Estado: **v3.0.0 en producción** (hub+dashboard en Nuke/Coolify, agente en `eno1`). Este plan cubre (A) el orden canónico de reconstrucción —para fork/rebuild desde cero— y (B) la hoja de ruta incremental v3.1 sobre lo existente. Cada paso tiene criterio de aceptación verificable.

## A. Secuencia de construcción (dependencias estrictas)

### Fase 1 — Datos y features
1. **Cargar UGRansome + sintético** (`data_loader.py`). ✔ *Check:* `pytest tests/ -k data_loader` pasa; DataFrame con 14 columnas estándar.
2. **Feature engineering** (PCA/MI → n_qubits, angle encoding [0,π]) ✔ *Check:* salida acotada en [0,π]; test unitario.
3. **FlowExtractor** con caps de tasa (valores: TRD §5) en `_to_dataframe`. ✔ *Check:* flujo de 1 paquete produce `bytes_per_sec ≤ 2^30`; test con pcap sintético.

### Fase 2 — Modelos
4. **QI-VAE** (PyTorch) + umbral calibrado (`calibrate_threshold.py`). ✔ *Check:* score en dataset de prueba acotado (sin valores >1e6 en tráfico real de muestra).
5. **QSVM + feature maps** (Qiskit) + baselines clásicos. ✔ *Check:* informe `model-performance-reports/` con F1/ROC-AUC/FPR comparado vs baselines.

### Fase 3 — Post-filtro (aquí vive la precisión real)
6. **PostFilter** completo con los knobs de TRD §5 (`whitelist_private=False`, tope HTTPS, comprobar 443 en **src y dst**). ✔ *Check:* `tests/test_postfilter_nmap.py` verde; broadcast unicástico NO suprimido (SYN de nmap sobrevive).

### Fase 4 — Hub
7. **HubStore SQLite** + migraciones idempotentes + endpoints ingest/heartbeat/query/summary. ✔ *Check:* `curl` batch → `summary.total_alerts` sube; reopen de BD existente no rompe (migración in-place).

### Fase 5 — Agente
8. **Loop de captura** (scapy → extract → score → filter → POST lote + heartbeat + buffer en disco). ✔ *Check:* QA end-to-end según criterios de éxito PRD §4 (baseline `summary` → trigger `nmap -sS -Pn -T4 -F` → CRITICALs en ≤2 ventanas; −70–80 % CRITICALs FP sin perder señal no-HTTPS).

### Fase 6 — Dashboard
9. **Consola SOC** según `flow.md` + `design-brief.md` (pills, KPIs, chips, detalle intel). ✔ *Check:* screenshot vs design brief; ventana vacía muestra aviso, no "0 amenazas" falso.

### Fase 7 — Deploy
10. **Coolify**: `qzero-api` + `qzero` (Traefik `Host(qzero.thempra.net)`, TLS) y `qzero-agent`. ✔ *Check:* `/health` 200; merge a `main` + push por SSH (token HTTPS muerto); si el 1er build falla (`No such container`/OOM) reintentar deploy; healthchecks Docker en verde.

## B. Hoja de ruta v3.1 (incremental, en orden)

Contexto (lo último landed): post-filtro anti-FP (−73 % CRITICALs), caps de rate, Sonar limpio, cobertura 42→75 %, CI con escáneres→DefectDojo + Sonar + deploy Coolify condicional, docs fundacionales deduplicadas.

### Hito 1 — Operación confiable (semanas 1–2)
| # | Tarea | Estado/Notas | Aceptación |
|---|---|---|---|
| 1 | Rotación/retención de `alerts` (`QZERO_ALERT_RETENTION_DAYS`, borrado por lotes en heartbeat) — bloquea el riesgo de BD SQLite infinita en el volumen Nuke | pendiente | BD < umbral tras config; test con BD falsa antigua |
| 2 | Notificación de CRITICALs a Telegram (rate-limited, resumen no por-alerta) | **parcial**: `logger.send_telegram_alert` ya existe; falta cablearlo desde el hub + anti-spam | Mensaje real al trigger nmap; sin spam en tormenta de FP |
| 3 | Supervisión del agente: systemd/healthcheck con reinicio + alerta si heartbeat cesa > N min | pendiente | Agente matado a mano → online de nuevo solo + nota en Agents |

### Hito 2 — Credibilidad del modelo (semanas 3–5)
| # | Tarea | Notas | Aceptación |
|---|---|---|---|
| 4 | Reentrenamiento programado por cron + informe automático a `model-performance-reports/` | pendiente | Informe fechado; diff de F1 vs modelo en producción |
| 5 | **Benchmark cuántico vs clásico** con pcaps etiquetados propios: QSVM vs QI-VAE vs baselines en detección real, no solo UGRansome | cierre la promesa pendiente del PRD/PROJECT_DEFINITION; alimenta paper y PRESENTATION | Tabla de resultados reproducible por script; conclusiones en informe |
| 6 | Umbral/severidad **por agente** (override en heartbeat) — una DMZ con IP pública puede activar `whitelist_private=True` sin afectar a la LAN | depende de 1 | Config por agente persistida; test con 2 agentes ficticios |

### Hito 3 — Platformización (semanas 6–8)
| # | Tarea | Notas | Aceptación |
|---|---|---|---|
| 7 | Auth app-level del dashboard (flujo: `backend-schema.md §2`: token SPA, `ADMIN_PASSWORD` env fail-closed, `token_version`; NUNCA Basic Auth) + `X-Agent-Token` opcional en ingest | desbloquea meter más hosts/segmentos (PRD Q2) | 401 sin token; agente viejo sigue si `QZERO_REQUIRE_AGENT_TOKEN=0` |
| 8 | Enriquecimiento persistido: cache org/ASN por IP en tabla `ip_intel` | quita WHOIS síncrono del `/alerts/recent` | Latencia estable; sin llamadas externas en el render |
| 9 | API pública consultiva `/api/v1/*` versionada + doc OpenAPI en `/docs` | contrato actual ya en backend-schema §3 | Cliente externo real consume alertas sin leer código |

### Hito 4 — Expansión (post-v3.1, a decidir)
- Agente Windows/macOS (hoy Linux/Docker) y modo mirror/span sin agente (sniffer pasivo en el router).
- Integración con el stack Thempra: alertas al CECOM / canal Zulip por-usuario (preferencia: filtros por usuario, no globales).
- Playbooks de respuesta semi-automática (sigue sin haber bloqueo activo: PRD §3 lo mantiene fuera).

**Criterio de salida de v3.1:** hitos 1–2 verdes con el QA del workflow nmap (PRD §4) repetido tras cada hito; entonces tag `v3.1.0`.

## Reglas de ejecución
- Construir estrictamente en orden A1→A10 (o B por hitos, 1→9); si la realidad fuerza un cambio, actualizar el doc afectado **en el mismo commit**.
- Desplegar solo desde `main` (auto-deploy); nunca fusionar dev→main sin pedirlo.
- Toda "mejora de detección" se valida con el workflow QA del skill `qzero-ndr`: baseline → trigger nmap → comparar antes/después con datos reales.
