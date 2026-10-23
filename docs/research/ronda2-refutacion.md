# QZero — Ronda 2: Refutación Cruzada (Red Team)

**Estado:** veredicto ejecutable. **Fecha:** 2026-10-23. **Fuentes:** cuatro informes de la ronda 1 + dossier verificado (`qzero-evidence-2026-10-23.md`).

---

## 1. Tabla propuesta-por-propuesta con veredicto

| Informe | Propuesta | Veredicto | Razones (a-e) |
|---------|-----------|-----------|---------------|
| **Producto P1** | Hotfix auth + retención + purga manual `hub.db` antes del viernes | **SOBREVIVE** | (a) Medido: prod sin auth, 881 MB, 1.7M filas. (b) 0.5 d-hombre (rebuild + deploy + script purge). (c) Reversible: rollback imagen anterior. (d) Si sale mal: fuga de datos sigue activa; riesgo legal RGPD. (e) Resuelve problema del comprador (confianza) y del equipo (deuda operativa). |
| **Producto P2** | Reposicionar "cuántico" → "NDR anomalías + I+D cuántica"; quitar cifras `PRESENTATION.md` | **SOBREVIVE** | (a) Medido: QI-VAE F1 0.18 LOTO, QSVM ROC-AUC 0.34, recall 1.0 = predictor constante. (b) 0.2 d-hombre (patch docs + landing). (c) Reversible: git revert. (d) Si sale mal: credibilidad destruida en calls; riesgo legal (Ley 3/1991 art. 5). (e) Resuelve problema del comprador (expectativas reales). |
| **Producto P3** | Normalizar score (cap + log-scale + baseline por flujo) + portada SOC "críticas hoy sin triage" + allowlist MVP | **SE MODIFICA** | (a) Parcial: score 1e17 medido; "allowlist por flujo" requiere tabla `flow_state` + endpoint `/flows` (no existe). (b) 2 d-hombre agente + 1 d-hombre hub + 2 d-hombre UI = **5 d-hombre**, no "1-2 días". (c) Reversible en código; no en UX si se lanza rota. (d) Si sale mal: portada sigue gritando 232k CRITICAL; allowlist botones muertos. (e) Mezcla problema comprador (legibilidad) + problema interno (score roto). **Modificación**: dividir en P3a (normalizar score en agente, 1 d) y P3b (endpoint `/flows` + tabla `flow_state` + UI triaje, 4 d). P3a esta semana; P3b fase 2. |
| **Producto P4** | Landing "compradable": 3 tiers (0/490/1490€), métricas reales, diagrama SPAN/TAP, badges AI Act | **SE MODIFICA** | (a) Métricas reales: **no existen** (Gbps, CPU/RAM no medidos; throughput 16.050 flujos/s solo en landing sin script fuente). (b) 4 h HTML + **días de medición real**. (c) Reversible. (d) Si sale mal: CISO pide métricas → no hay → pérdida credibilidad. (e) Problema comprador (compra), pero vende vapor. **Modificación**: landing honesta hoy (quitar "Gbps", poner "medición pendiente con método publicado"; añadir pricing 3 tiers; diagrama SPAN/TAP dibujado a mano). Métricas reales → ticket aparte con due date. |
| **Producto P5** | Gate: 3 PoCs pagados en 90 días o pivot a OSS puro | **SOBREVIVE** | (a) Interpretación estratégica, no medición. (b) 0 dev extra; coste comercial (tiempo B). (c) Reversible: si no se cierran, se pivota. (d) Si sale mal: consultora quema 90 días sin ingreso recurrente. (e) Resuelve problema del fundador (foco), no del comprador. **Condición**: PoC = assessment 2 sem (12k€) con criterio de éxito firmado ANTES (ver §6). |
| **Marketing C1-C4** | Eliminar tabla `PRESENTATION.md` entera; C2: "QI-VAE recall 0.10 en ataque no visto" | **SOBREVIVE** | (a) Medido: C1-C4 no tienen fuente en repo; C2 cita JSON real. (b) 0.5 h (borrar tabla, patch landing). (c) Reversible. (d) Si no: riesgo legal + credibilidad cero. (e) Resuelve problema comprador (verdad). |
| **Marketing C5** | Corregir "sub-ms inference" → "85 ms/flujo QSVM; 0.1 ms QI-VAE/PostFilter" | **SOBREVIVE** | (a) Medido: 92.86 s / 1.088 flujos = 85 ms. (b) 0.1 h. (c) Reversible. (d) Si no: mentira cuantificable 85x. (e) Comprador. |
| **Marketing C6** | Publicar script throughput + salida o quitar cifra | **SE MODIFICA** | (a) NO VERIFICADO: `grep -rn '16050'` → solo landing + capturas. (b) 2-4 h escribir script + medir. (c) Reversible. (d) Si no: CISO pide método → no hay. (e) Comprador. **Modificación**: quitar cifra hoy; ticket "publicar script throughput con método" con due date 2 sem. |
| **Marketing C7/C8** | Corregir `#truth`: banco degenerado (recall 1.0 = predictores constantes), F1 medio real 0.711 no 0.569 | **SOBREVIVE** | (a) Medido: reconstrucción aritmética exacta desde JSON. (b) 1 h patch HTML. (c) Reversible. (d) Si no: "manipulan el banco" = muerte credibilidad. (e) Comprador. |
| **Marketing Call 20 min** | Guion con bloque "qué falla" en min 13-16, criterio de éxito firmable | **SOBREVIVE** | (a) Diseño, no medición. (b) 0 dev. (c) Reversible. (d) Si sale mal: call sin estructura → piloto eterno. (e) Comprador (reduce riesgo percibido). **Condición**: criterio de éxito = métricas observables (flujos/día, alertas revisables/día, FPR tolerable) + fecha fin. |
| **Marketing 4 cifras canónicas** | Solo 2.942 flujos, QSVM 0.711 vs SVM 0.707 (degenerado), QI-VAE F1 0.18, API 0.16/0.06 s | **SOBREVIVE** | (a) Medidas en JSON. (b) 0. (c) N/A. (d) Si se dice más: invento. (e) Comprador. |
| **Research** | Benchmark degenerado (48 filas únicas / fold); QSVM ROC-AUC 0.34; NaN fail-open; umbral 8.7x desalineado; plan experimental ≥2.400 flujos | **SOBREVIVE** | (a) Medido en JSON + código (NaN en `reconstruction_errors` → `predict` devuelve 0 = fail-open). (b) Plan experimental: **≥2.400 flujos benignos** para calibrar umbral (dossier: 542 normales en banco). (c) Irreversible en tiempo: 2.400 flujos requieren tráfico real o generación. (d) Si sale mal: modelo en prod sigue con umbral 4.2 arbitrario + NaN silenciados. (e) Problema interno (rigor), pero bloquea venta honesta. |
| **Research** | QI-VAE en prod con F1 0.18 → desactivar (`QZERO_USE_QIVAE=0`); baseline RF/GB | **SOBREVIVE** | (a) Medido: prod usa QI-VAE (`QZERO_USE_QIVAE=1` en docker-compose.agent.yml). (b) 0.1 d (env var + redeploy). (c) Reversible. (d) Si no: FPR real desconocido; backup = CRITICAL. (e) Comprador + interno. |
| **Research** | Plan experimental: ≥25.000 flujos benignos para calibrar (informe research dice ≥2.400 en un sitio, ≥25.000 en otro) | **SE MODIFICA** | (a) Contradicción interna del informe. (b) 25k flujos = **no hay fuente**: 1 agente, `PROMISCUOUS=0`, solo ve tráfico propio host. (c) Irreversible en tiempo. (d) Si se promete: vapor. (e) Problema interno. **Modificación**: objetivo realista = 5.000 flujos benignos reales (requiere `PROMISCUOUS=1` + SPAN en segmento con tráfico variado) + datos sintéticos validados. |
| **Consola (§5)** | Agregación por 5-tupla (`GET /api/v1/flows` + `GROUP BY`), estado caso persistido (`flow_state`), inspector maestro-detalle fijo | **SE MODIFICA** | (a) Endpoint `/flows` **no existe**; tabla `flow_state` **no existe**; requiere auth desplegado primero (escritura). (b) 2 d-hombre hub + 1 d-hombre migración + 3 d-hombre UI = **6 d-hombre mínimo**. (c) Parcial: migración BD no reversible sin backup. (d) Si sale mal: botones "Silenciar/Investigar" muertos; consola escribe sin auth = peor que leer sin auth. (e) Problema comprador (triaje), pero dependencias no resueltas. **Modificación**: fase 1 = `/flows` read-only + UI read-only (cola casos); fase 2 = auth + `flow_state` + escritura. |
| **Consola (§9)** | Disparador: si AC-2 > 1.5 s en 2/3 intentos → migrar shell a HTML estático + Streamlit solo Research | **SOBREVIVE** | (a) Criterio medible (CDP). (b) Migración: ~10 d-hombre (patrón `hub_dashboard.html` ya existe). (c) Reversible con feature flag. (d) Si no: UX inaceptable. (e) Interno (deuda técnica), pero necesario para credibilidad. |
| **Consola (§10 R4)** | Bloqueante: auth antes de fase 2 (escritura silenciado) | **SOBREVIVE** | (a) Medido: prod sin auth, consola pública. (b) 0.5 d (desplegar imagen con `ADMIN_PASSWORD`). (c) Reversible. (d) Si no: escritura expuesta = vulnerabilidad crítica. (e) Comprador + legal. |

---

## 2. Contradicciones entre informes (nombradas)

| # | Contradicción | Informes | Gravedad |
|---|---------------|----------|----------|
| **CTD-01** | **Producto vende PoC con motor que Research dice que no detecta** | Producto (P5: PoC 2 sem) vs Research (QI-VAE F1 0.18, QSVM degenerado, NaN fail-open) | **CRÍTICA** — Un PoC de 2 semanas con un motor que marca `normal.pcap` al 100% y backups como CRITICAL 1.9e9 destruye credibilidad en la primera semana. El criterio de éxito "X alertas revisables/día" es inalcanzable sin normalizar score + allowlist (P3) + desactivar QI-VAE. |
| **CTD-02** | **Marketing propone call con CISO; Consola y Research dicen que la demo pública está rota** | Marketing (call min 9-13 enseña `#truth`) vs Consola (prod sin auth, 232k CRITICAL, 20-25 s render) vs Research (benchmark degenerado) | **ALTA** — El call enseña la consola pública (`qzero.thempra.net`) como prueba. Hoy esa URL sirve IPs internas sin login y una portada que grita 232.878 críticas. Un CISO que haga clic durante el call ve el hallazgo, no la demo. **Orden real**: auth + purga + normalizar score + portada triaje → **después** invitar a calls. |
| **CTD-03** | **Consola propone agregación por 5-tupla + estado caso persistido; pero eso requiere auth desplegado + tabla `flow_state` + endpoint `/flows` (ninguno existe en prod)** | Consola (§7 contrato técnico) vs Producto (P1: auth hotfix 0.5 d) vs Research (no menciona dependencias UI) | **ALTA** — El orden de dependencias real es: 1) Deploy auth (imagen con `ADMIN_PASSWORD`), 2) Migración BD `flow_state`, 3) Endpoint `/flows` (SQL `GROUP BY` + índice compuesto), 4) UI triaje read-only, 5) UI escritura (silenciar/investigar). Producto P1 solo cubre paso 1. Consola asume 1-5 listos. |
| **CTD-04** | **Research pide ≥25.000 flujos benignos para calibrar; ops dice que solo hay 1 agente en LAN de lab con `PROMISCUOUS=0`** | Research (plan experimental) vs Dossier (§3.4: 1 agente, `PROMISCUOUS=0`, ve solo tráfico propio host) | **ALTA** — No hay fuente de 25k flujos benignos reales. Opciones: (a) `PROMISCUOUS=1` en SPAN real (requiere acceso red cliente), (b) dataset público (CIC-IDS2017, UGRansome) pero distribución distinta, (c) generador sintético validado. Ninguna está planificada. |
| **CTD-05** | **Producto P4 pide métricas reales (Gbps, CPU/RAM) en landing; Marketing C6 dice que no existen y son NO VERIFICADO; Consola no las mide** | Producto P4 vs Marketing C6 vs Consola (no hay métricas de rendimiento en código) | **MEDIA** — Landing no puede prometer "1 Gbps en 2 vCPU/4GB" sin medición. El script de throughput no existe. Prometerlo = mentira. |
| **CTD-06** | **Producto P3 "allowlist por flujo MVP" vs Consola "tabla `flow_state` + auth" vs Research "post-filtro clásico es lo único que sostiene precisión"** | Producto P3 vs Consola §7 vs Research (postfilter determinista) | **MEDIA** — El allowlist actual (`whitelist_private` en `agent_config`) es **por agente, RFC1918 completo**, no por 5-tupla. El allowlist por flujo que pide Producto y Consola requiere tabla nueva + endpoint + auth. No es MVP de 1 día. |
| **CTD-07** | **Research: QSVM ROC-AUC 0.34 en split (peor que azar); Marketing: landing muestra ROC-AUC 0.57-0.61 en tabla LOTO** | Research (split: QSVM ROC-AUC 0.3395) vs Landing (`docs/index.html:360-378` muestra 0.57/0.61/0.52/0.56 por fold) | **MEDIA** — La landing muestra ROC-AUC **por fold** (ddos/bruteforce/exfil/malware) que promedian ~0.56, no el **split estratificado 80/20** que da 0.3395. El lector no distingue; la landing oculta el split que mata la credibilidad del QSVM. |
| **CTD-08** | **Producto: "3 PoCs en 90 días" gate; Marketing: call 20 min + propuesta 10 páginas; Research: modelo no listo para PoC honesto** | Producto P5 vs Marketing §3-4 vs Research | **MEDIA** — El embudo comercial (call → propuesta → PoC) assume que el PoC es ejecutable y medible. Research dice que no hay banco que discrimine, umbral no calibrado, score sin cota, NaN fail-open. Un PoC honesto hoy = "deployamos, vemos ruido, te decimos que el modelo está en reentrenamiento". Eso no se vende a 12k€. |

---

## 3. Grafo de dependencias real (qué antes de qué, con porqué técnico)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ FASE 0 — ESTA SEMANA (bloqueantes duros, 4.5 d-hombre totales)              │
├─────────────────────────────────────────────────────────────────────────────┤
│ 0.1  Desplegar imagen con ADMIN_PASSWORD + JWT fail-closed (auth)           │
│      └─> Porqué: prod expone IPs internas a Internet (RGPD); escritura     │
│          silenciado en consola futura requiere auth.                        │
│      └─> Coste: 0.5 d (rebuild docker + deploy Coolify + rotar claves)     │
│                                                                              │
│ 0.2  Ejecutar purga retention 90d (`hub.purge_old_alerts(90)`) + cron      │
│      └─> Porqué: 881 MB, 170k/día → disco lleno en ~2 meses; PRD lo exige. │
│      └─> Coste: 0.5 d (script + cron systemd)                              │
│                                                                              │
│ 0.3  Desactivar QI-VAE en agente prod (`QZERO_USE_QIVAE=0`)                │
│      └─> Porqué: F1 0.18 en ataque no visto; NaN en reconstruction_errors  │
│          → fail-open (predice 0 = normal); backup = CRITICAL 1.9e9.        │
│      └─> Coste: 0.1 d (env var + redeploy agente)                          │
│                                                                              │
│ 0.4  Eliminar tabla `PRESENTATION.md` + corregir `#truth` (C7/C8)          │
│      └─> Porqué: cifras 88%/93%/2.4% FPR son inventadas; F1 medio 0.569   │
│          es accuracy, no F1; banco LOTO degenerado (recall 1.0).           │
│      └─> Coste: 1 h (patch MD + HTML + push → GitHub Pages)                │
│                                                                              │
│ 0.5  Normalizar score en agente: cap + log1p + baseline por flujo (P3a)    │
│      └─> Porqué: score 1e17 rompe UI, triaje, severidad; umbral 4.2        │
│          vs "normal 3.0-3.7" = 8.7x desalineado (Research).                │
│      └─> Coste: 1 d (cambio en `_analyze_window` + `_flow_alert` + test)   │
│                                                                              │
│ 0.6  Landing honesta: quitar "Gbps/CPU", añadir pricing 3 tiers,           │
│      diagrama SPAN/TAP a mano, badge "medición throughput pendiente"       │
│      └─> Porqué: CISO no compra "gratis"; métricas no existen.             │
│      └─> Coste: 4 h                                                         │
│                                                                              │
│ 0.7  Borrar/zombie `qa-test` (marcar decommissioned o borrar de BD)        │
│      └─> Porqué: contamina KPI "1/2 agentes online".                       │
│      └─> Coste: 0.1 d                                                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ FASE 1 — ANTES DE PRIMERA CALL/POC (2-3 semanas, ~10 d-hombre)             │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1.1  Endpoint `GET /api/v1/flows` (SQL GROUP BY 5-tupla + idx compuesto)   │
│      └─> Porqué: Consola portada necesita casos agregados, no 500 alertas  │
│          de `/alerts/recent`. Sin esto, "Mesa de triaje" es vapor.         │
│      └─> Depende: 0.1 (auth) + 0.2 (purga ok)                              │
│      └─> Coste: 2 d (hub.py + índice `(dst_port,src,dst)` + test perf)     │
│                                                                              │
│ 1.2  Tabla `flow_state(flow_key, state, note, silenced_until, updated_at)` │
│      + migración + endpoint `PATCH /flows/{key}/state` (auth required)     │
│      └─> Porqué: Botones "Silenciar/Investigar/Escalar" escriben; sin      │
│          auth = vuln; sin tabla = botones muertos.                         │
│      └─> Depende: 1.1 + 0.1 (auth)                                         │
│      └─> Coste: 2 d (migración SQLite + API + test)                        │
│                                                                              │
│ 1.3  UI Mesa de triaje read-only (cola casos + inspector fijo)             │
│      └─> Porqué: Portada deja de gritar 232k CRITICAL; muestra casos.      │
│      └─> Depende: 1.1 (`/flows`)                                           │
│      └─> Coste: 3 d (dashboard.py: Streamlit ≥1.42, st.fragment,          │
│          maestro-detalle, presets, estados vacío/carga/error)              │
│                                                                              │
│ 1.4  Script throughput real + publicación método + cifra en landing        │
│      └─> Porqué: Marketing C6; CISO pregunta "¿aguanta mi 10 Gbps?".       │
│      └─> Coste: 2 d (generador tráfico + medición + doc)                   │
│                                                                              │
│ 1.5  Calibración umbral con ≥5.000 flujos benignos reales                  │
│      └─> Porqué: Research pide ≥2.400/25.000; ops: 1 agente PROMISCUOUS=0  │
│          → no hay fuente. Solución: `PROMISCUOUS=1` en SPAN segmento       │
│          variado (requiere acceso red) O dataset público validado.         │
│      └─> Coste: 3-5 d (acceso red + captura + calibrate_threshold.py)      │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ FASE 2 — POVOT / PRODUCTO (post-gate 3 PoCs, 6-9 meses)                   │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2.1  UI escritura (silenciar/investigar) + auth RBAC mínimo                │
│ 2.2  Benchmark honesto reproducible (nuevo protocolo no degenerado)        │
│ 2.3  Paper/preprint "Why quantum kernels didn't beat RF on our traffic"    │
│ 2.4  Multi-agente real (promiscuous + SPAN en ≥3 segmentos)                │
│ 2.5  Modelo candidato reentrenado con datos reales + eval zero-day real    │
│ 2.6  SaaS self-hosted: multi-tenant, billing, portal, SLA, updates firmados│
└─────────────────────────────────────────────────────────────────────────────┘
```

**Regla de oro**: **no hay escritura en consola sin auth desplegado**; **no hay portada triaje sin `/flows`**; **no hay PoC vendible sin score normalizado + QI-VAE off + allowlist por flujo read-only**.

---

## 4. Decisiones que quedan en pie (10) y las que hay que descartar (5)

### ✅ 10 DECISIONES QUE QUEDAN EN PIE

1. **Camino Servicios primero** (Producto P5): 3 PoCs pagados en 90 días o pivot a OSS puro. Gate real, no aspiracional.
2. **Hotfix auth + retención + purga YA** (Producto P1 + P2 + Research): 4.5 d-hombre, bloquea todo lo demás.
3. **Desactivar QI-VAE en prod** (Research + Producto P3a): env var + redeploy; baseline = Random Forest / Gradient Boosting.
4. **Eliminar cifras `PRESENTATION.md` y corregir `#truth`** (Marketing C1-C4, C7/C8): riesgo legal + credibilidad.
5. **Solo 4 cifras canónicas en pitch** (Marketing §2.2): 2.942 flujos, QSVM 0.711 vs SVM 0.707 (degenerado), QI-VAE F1 0.18, API latency.
6. **Call 20 min con bloque "qué falla" y criterio de éxito firmable** (Marketing §3): reduce riesgo percibido; evita piloto eterno.
7. **Reposicionar "cuántico" a I+D con resultado negativo publicado** (Producto P2 + Marketing §1.3): activo frente a fondos, irrelevante para CISO.
8. **Outbound consultora + content técnico honesto + GitHub OSS híbrido** (Producto §2.5): canales realistas para equipo 1-5 personas.
9. **Grafo dependencias: auth → purga → /flows → flow_state → UI triaje read-only → UI escritura** (Consola §7 + CTD-03): orden técnico innegociable.
10. **Benchmark honesto como activo de marca** (Marketing §1.1 + Research): publicar LOATO + split + "banco no discrimina" aumenta credibilidad.

### ❌ 5 DECISIONES QUE HAY QUE DESCARTAR SIN MÁS DEBATE

1. **"Allowlist por flujo MVP en 1 día" (Producto P3b)**: Requiere `flow_state` + auth + endpoint `/flows` + migración BD = **6 d-hombre mínimo**, no MVP. El allowlist actual (`whitelist_private` por agente) es lo que hay; documentarlo y usarlo.
2. **"Métricas Gbps/CPU/RAM en landing esta semana" (Producto P4)**: No existen, no hay script, medir requiere generador de tráfico + metodología = **2-3 semanas**. Prometerlas = mentira. Poner "medición pendiente con método publicado".
3. **"25.000 flujos benignos para calibrar" (Research plan experimental)**: Fuente no existe (1 agente, `PROMISCUOUS=0`). Objetivo irreal. Sustituir por: 5.000 flujos reales (requiere SPAN acceso red) + sintético validado.
4. **"Reescribir consola en HTML+JS ya" (Consola debate A↔B #1)**: Streamlit ≥1.42 + `st.fragment` + `st.dataframe(on_select="rerun")` da p95 ≤ 1.5 s si backend ≤300 ms. Migrar shell = 10 d-hombre. Probar Streamlit primero con criterio duro (AC-2).
5. **"Vender PoC de detección zero-day" (Producto P5 + Marketing call)**: El motor **no detecta zero-days** (banco: 4 ataques conocidos, 0 zero-days; QI-VAE F1 0.18). Vender detección = fraude. Vender **assessment de anomalía + triaje + baseline de ruido** = honesto y vendible.

---

## 5. Preguntas que nadie respondió y que bloquean el roadmap

| # | Pregunta | Quién debe responder | Bloquea |
|---|----------|---------------------|---------|
| **Q-BLK-01** | **¿Dónde se consiguen 5.000 flujos benignos reales esta semana?** (1 agente, `PROMISCUOUS=0`, lab LAN). Sin esto, umbral sigue arbitrario (4.2 vs baseline 3.0-3.7 = 8.7x). | Fundador (acceso red cliente / SPAN) | Fase 1.5, calibración, PoC honesto |
| **Q-BLK-02** | **¿Se despliega `PROMISCUOUS=1` en segmento real antes del primer PoC?** Si no, el agente ve solo tráfico del host (backups, SSH, Grafana) → cero valor de detección de red. | Fundador / DevOps | PoC vendible, credibilidad técnica |
| **Q-BLK-03** | **¿Quién hace el script de throughput y cuándo?** (Marketing C6, Producto P4). Sin script, landing miente o call improvisa. | Dev (A) | Landing honesta, call CISO Q4 |
| **Q-BLK-04** | **¿El criterio de éxito del PoC (assessment 2 sem) se firma ANTES de cobrar 12k€?** Marketing §3.1 dice sí; Producto P5 no lo especifica. Si no se firma: piloto eterno, sin ingreso, sin gate. | Fundador (B) + Head Product (A) | Gate 90 días, unit economics |
| **Q-BLK-05** | **¿Qué pasa con `qa-test` zombie y los 232k CRITICAL históricos?** Borrar filas de `alerts` (purga) no borra la allowlist futura (`flow_state`); ¿la allowlist sobrevive a retención 90d? | Dev (A) | Consola §10 R3, triaje honesto |
| **Q-BLK-06** | **¿El modelo en prod (4-ago, QI-VAE) se reentrena con datos reales del cliente en el PoC?** Dossier: `retrain-latest.json` → `"real": false`. Si no: PoC usa modelo sintético de hace 2.5 meses. | Dev (A) | Credibilidad PoC, Research plan experimental |
| **Q-BLK-07** | **¿CI gate de pytest obligatorio antes de merge a `dev`/`main`?** Hoy: workflow SonarQube/DefectDojo, pytest solo si existe marcador y `|| true`. Sin gate, drift prod/git persiste. | Dev (A) | Producto P1 (hotfix), confianza deploy |
| **Q-BLK-08** | **¿Se publica el benchmark honesto (LOADO + split + "banco degenerado") ANTES del primer call?** Marketing §5.1 dice benchmark público reproducible = prioridad 1. Si no: call enseña landing con cifras corregidas pero sin banco reproducible. | Head Product (A) | Credibilidad call, Marketing guardrails |

---

## 6. Alcance mínimo defendible: qué se entrega en 2 semanas (honesto y útil)

**Objetivo**: Un artefacto que un CISO pueda evaluar en 30 min, que no mienta, y que demuestre capacidad de ejecución (no de detección mágica).

### ENTREGABLE: "QZero Assessment Kit v0.1" (2 semanas, ~12 d-hombre)

| Componente | Qué incluye | Qué NO incluye | Honestidad |
|------------|-------------|----------------|------------|
| **1. Sensor desplegable** | Docker compose 1 agente + hub + dashboard; `ADMIN_PASSWORD`; `QZERO_USE_QIVAE=0`; `QZERO_ALERT_RETENTION_DAYS=90`; `PROMISCUOUS=1` (documentado: requiere SPAN/TAP) | Multi-agente, auto-descubrimiento, alta disponibilidad | "Un sensor, un hub, una consola. Escala horizontal: manual hoy." |
| **2. Score normalizado** | Cap 100, `log1p(score)/log1p(baseline_flow)`, baseline por flujo (media móvil 1h), severidad con `https_volume_cap_score` | Umbral calibrado por cliente (requiere 5k flujos benignos) | "Umbral 4.2 por defecto; calibración = servicio del assessment." |
| **3. Consola triaje read-only** | Endpoint `/api/v1/flows` (agregado 5-tupla, p50/p99/max score, vol/min), portada "Mesa de triaje" (cola casos ≤30, inspector fijo, presets Accionable/Todo/Silenciados), estados vacío/carga/error | Escritura (silenciar/investigar), auth RBAC, multi-usuario | "Solo lectura. Escritura = fase 2 tras auth + flow_state." |
| **4. Allowlist por agente (RFC1918)** | `whitelist_private` en `agent_config` (ya codificado, Hito 2.6), configurable desde hub | Allowlist por 5-tupla (requiere flow_state) | "Suprime ruido conocido de red privada; no por flujo individual." |
| **5. Benchmark honesto público** | `docs/HONEST-BENCHMARK.md` generado desde JSON: LOATO (QI-VAE F1 0.18, QSVM 0.711 degenerado), split (ROC-AUC QSVM 0.34), tabla por fold, método, fecha, "no discriminan". | Cifras zero-day, FPR, "ventaja cuántica" | "El banco no discrimina. Lo publicamos para que lo veas." |
| **6. Landing honesta** | Hero: "1.7M alertas → 12 casos. Triaje, no ruido." Pricing 3 tiers. Diagrama SPAN/TAP. Badge "Throughput: medición pendiente con método publicado". Enlace a `HONEST-BENCHMARK.md`. | Métricas Gbps/CPU inventadas, logos clientes, "enterprise-ready" | "Autoalojado, MIT, sin nube. Soporte = servicio aparte." |
| **7. Criterio de éxito PoC (firmable)** | Hoja 1 página: (a) Segmento + SPAN definido, (b) 5.000 flujos benignos capturados en semana 1, (c) Umbral calibrado (FPR objetivo ≤5% en benignos), (d) Alertas revisables/día ≤20 en semana 2, (e) Go/No-go firmado día 14. | Promesa de detección zero-day, SLA, respuesta activa | "Criterio observable, medible, sin magia." |
| **8. Demo grabada (3 min)** | Grabación **después** de 1-4: consola triaje con caso backup (volumen alto, rareza baja) + flujo externo sospechoso. Sin narrador, solo UI. | Demo en vivo (consola pública sigue cerrada tras auth) | "Grabada con motor honesto (QI-VAE off, score normalizado)." |

### CRONOGRAMA 2 SEMANAS (12 d-hombre, 1-2 personas)

| Día | Entrega | Owner | Dependencia |
|-----|---------|-------|-------------|
| 1-2 | 0.1-0.7 (hotfix completo: auth, purga, QI-VAE off, score norm, landing, zombie) | Dev | — |
| 3-4 | 1.1 Endpoint `/flows` + índice compuesto + test perf ≤300 ms | Dev | 0.1, 0.2 |
| 5-6 | 1.2 Tabla `flow_state` + migración + `PATCH /flows/{key}/state` (auth) | Dev | 1.1, 0.1 |
| 7-9 | 1.3 UI Mesa de triaje read-only (Streamlit ≥1.42, AC-1..AC-10) | Dev | 1.1 |
| 10 | 1.4 Script throughput + medición + doc | Dev | — |
| 11 | 5 Benchmark honesto + 6 Landing honesta + 7 Criterio PoC | Head Product | 0.4, 1.4 |
| 12 | 8 Demo grabada + package Assessment Kit (README + docker-compose + criterio) | Head Product | 1.3, 7 |

### QUÉ DICE EL KIT AL CISO (y qué no)

> **"Esto es un sensor de anomalías de red autoalojado. Agrega alertas por flujo (5-tupla) y te da una cola de casos que se puede vaciar. El motor clásico (Random Forest) bate al cuántico en nuestro banco; el cuántico está en `experimental/`. No detectamos zero-days; reducimos el ruido para que tú decidas. El assessment de 2 semanas calibra el umbral en TU red y te entrega una baseline de ruido. Si al día 14 la cola de casos revisables es ≤20/día, hablamos de suscripción. Si no, te llevas el binario MIT y el criterio de éxito firmado."**

**Eso es defendible. Lo demás es humo.**

---

**Fin del documento.**  
**Archivo**: `/home/hermes/qzero/docs/research/ronda2-refutacion.md`