# QZero — PRD (Product Requirements Document)

**Versión del producto:** 3.0.0 · **Estado:** en producción (Nuke / Coolify) · **Última actualización:** 2026-10-14

## 1. Resumen de la idea

QZero es un **NDR (Network Detection and Response)** que detecta amenazas de día cero y comportamiento anómalo en el tráfico de red usando machine learning cuántico / cuántico-inspirado (QSVM con feature maps de Qiskit + QI-VAE en PyTorch), en lugar de firmas conocidas. Agentes ligeros de sniffing se instalan en varios hosts, cada uno analiza su tráfico en tiempo real y envía alertas a un **hub central** que las agrega, las enriquece y las muestra en una consola SOC web.

**Problema que resuelve:** los IDS por firma no ven zero-days; los IDS por anomalía clásicos tienen 5–15 % de falsos positivos. QZero combina scoring por anomalía (QI-VAE/QSVM) con un **post-filtro clásico determinista** que elimina el ruido conocido (DNS, multicast, volumen HTTPS legítimo), dejando alertas accionables.

**Para quién:** operador de red / analista de seguridad de Thempra (LAN 192.168.50.0/24 y futuros segmentos), y administradores que despliegan agentes en servidores.

## 2. Funcionalidades (en producción)

### F1 — Agente de sniffing distribuido
- Captura paquetes en una interfaz (Scapy, modo promiscuo opcional) en ventanas de ~5 s (`QZERO_INTERVAL`).
- Extrae flujos agregados con el modelo de 14 features UGRansome (`FlowExtractor`), con límites a las features de tasa para evitar explosión de scores (valores: TRD §5).
- Puntúa cada flujo con el modelo cargado (QI-VAE por defecto; QSVM opcional) y aplica umbral de score (valor por defecto: TRD §4).
- Post-filtro clásico (`PostFilter`): suprime ruido conocido (DNS, multicast/broadcast mínimo, locales, HTTPS sin payload) **sin** suprimir RFC1918 por defecto, y topa la severidad del HTTPS legítimo de alto volumen (knobs y justificación: fuente única en TRD §5).
- Envío de alertas en lote + heartbeat al hub; buffer local en disco si el hub está caído.

### F2 — Hub central de alertas
- API REST FastAPI: ingestión por agente, heartbeat, consulta de alertas/agentes y resumen O(1) por severidad. **Contrato exacto de endpoints: fuente única en `backend-schema.md §3`.**
- Persistencia SQLite (stdlib, sin deps externas) con migraciones idempotentes de esquema.
- Registro de agentes (`first_seen`/`last_seen`) → agentes online/offline.

### F3 — Consola SOC (dashboard)
- SPA Streamlit "QZero Quantum Threat Dashboard" en `/dashboard` (pública vía `qzero.thempra.net`).
- Módulos como pills superiores: Overview, Alerts, Threats, Network, Agents, Research.
- Enriquecimiento de cada alerta (`intel.py`): dirección (in/out), organización de destino (IP→ASN/owner), tipo de amenaza estimado y explicación accionable.
- Jerarquía risk-first: KPIs, distribución por severidad, timelines, salud de agentes.
- API clásica adicional (`/health`, `/analyze`, `/monitor/*`, WS `/ws`…): ver contrato en `backend-schema.md §3`.

### F4 — CLI
- `qzero train | analyze | server | monitor | agent` (Click). `agent` arranca F1 con flags/env vars.

### F5 — Entrenamiento y evaluación
- Dataset UGRansome + sintético; modelos QSVM (Qiskit) y QI-VAE (PyTorch) + baselines clásicos (RF, SVM-RBF, GBM, KNN, MLP).
- Métricas: accuracy, F1, ROC-AUC, FPR/FNR, tasa de detección zero-day; scripts de calibración de umbral (`calibrate_threshold.py`).

## 3. Fuera de alcance (v3)
- Bloqueo/respuesta activa (QZero es **solo detección + alerta**, no IPS).
- Autenticación multiusuario del dashboard (protegido hoy por red/perímetro; ver pregunta abierta Q2).
- Captura cifrada DPI / reensamblado de payloads.
- Multi-inquilino.

## 4. Criterios de éxito
1. Escaneo `nmap -sS` desde un host de la LAN → alertas CRITICAL visibles en el hub en ≤ 2 ventanas de captura.
2. ≥ 70 % de reducción de CRITICALs falsos (volumen CDN/broadcast) sin perder señal real no-HTTPS (medido con `/alerts/recent` antes/después).
3. Agente sobrevive a caída del hub sin perder alertas (buffer + reenvío).
4. `hub/summary` refleja `total_alerts > 0` con agentes RFC1918 activos (regresión del pitfall `whitelist_private`).

## 5. Preguntas abiertas
- **Q1:** ¿Canal de notificación externa de CRITICALs (Telegram) dentro del alcance de v3.1?
- **Q2:** La consola es pública vía `qzero.thempra.net`: ¿se requiere login a nivel app (preferencia del usuario: token SPA + contraseña por env, nunca Basic Auth) antes de exponer más hosts?
- **Q3:** ¿Retención/rotación de `alerts` (hoy crece sin límite en SQLite)?
