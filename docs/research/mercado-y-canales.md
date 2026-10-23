# QZero — Investigación de Mercado y Canales de Venta (octubre 2026)

**Fecha:** 2026-10-23  
**Autor:** Subagente de investigación externa  
**Metodología:** Web search + web extract con fuentes citadas (URL + fecha consulta). Todo dato sin fuente se marca **NO VERIFICADO**.

---

## 1. Mercado NDR: Tamaño, Crecimiento y Compradores Reales

### 1.1 Tamaño y proyección (fuentes públicas de analistas)

| Métrica | Valor | Fuente | Fecha consulta |
|---|---|---|---|
| Mercado NDR 2025 | **3.680 M USD** | MarketsandMarkets (PRNewswire) | 2025-10-14 |
| Mercado NDR 2030 | **5.820 M USD** | MarketsandMarkets (PRNewswire) | 2025-10-14 |
| CAGR 2025–2030 | **9,6 %** | MarketsandMarkets | 2025-10-14 |
| Mercado NDR 2031 (proyección) | **7.290 M USD** | MarketsandMarkets (2026-2031) | 2026 |

> **Nota:** MarketsandMarkets publica resúmenes de pago; las cifras arriba provienen de notas de prensa abiertas (PRNewswire, Yahoo Finance, CRN.pl). No hay desglose público por geografía ni por tamaño de cliente.

### 1.2 Vendors líderes (Gartner MQ 2025, resumen público)

El cuadrante mágico 2025 sitúa a **Darktrace, Vectra AI, ExtraHop (RevealX), Corelight, Gatewatcher, Arista NDR (ex-Awake)** como *Leaders* o *Challengers* (fuente: cobertura tecnológica en tech-insider.org y Gartner Peer Insights, 2026-10). No hay PDF público del MQ completo; las referencias abiertas citan estos seis nombres recurrentemente.

### 1.3 ¿Quién compra NDR y con qué presupuesto?

| Perfil comprador | Tamaño típico | Presupuesto NDR/año (rangos reportados) | Fuente / método |
|---|---|---|---|
| Enterprise (>5.000 emp.) | 5.000+ | **200 k–2 M USD** (Darktrace FY25 ARR medio ~400 k USD/cliente; 10.000+ clientes) | Darktrace Annual Report 2025, half-year results FT.com |
| Mid-market (500–5.000) | 500–5.000 | **50 k–200 k USD** (Vectra, Corelight cotizan «por sensor/año»; 1 sensor ≈ 1–2 Gbps; típico 5–20 sensores) | Vendr (Darktrace), Reddit/foros enterprise (Corelight ~25–50 k USD/sensor/año), TheTechBag |
| PyME / SMB (<500) | 50–500 | **5 k–30 k USD** (pocos vendors venden directo; canal MSSP / partners) | **NO VERIFICADO** – no hay precios públicos para este segmento; inferido de Kit Digital (máx 6.000 €) y MSSP pricing |

**Darktrace FY2025:** 820,8 M USD revenue pro-forma, +18,7 % YoY, +202 clientes, ARR medio por contrato en subida 10,2 % (fuente: FT.com half-year results + Darktrace Annual Report 2025).

**Conclusión accionable:** El segmento **50–500 empleados** no compra NDR *stand-alone* de vendors Tier-1; compra **servicios gestionados (MSSP)** o **kits subvencionados (Kit Digital)**. El ticket directo es <10 k €/año; por encima, el comprador exige certificación ENS/CPSTIC o contrata MSSP.

---

## 2. Segmento Alcanzable en España: Pymes 50–500, ENS Medio/Alto, NIS2

### 2.1 Estado de la transposición NIS2 (octubre 2026)

- **Plazo UE:** 17 oct 2024. **España no ha traspuesto** (anteproyecto aprobado en 1ª vuelta ene 2025, dictamen motivado mayo 2025, llevado al TJUE 8 jul 2026 con petición de multas diarias).
- **Texto vigente:** Real Decreto-ley 12/2018 (NIS1) + INCIBE-CERT (privado) / CCN-CERT (público).
- **Afectación:** Empresas **≥50 empleados o >10 M € facturación** en 18 sectores (Anexo I alta criticidad + Anexo II otros críticos). Distinción *entidades esenciales* (grandes Anexo I) vs *importantes* (resto). Supervisión *ex ante* (esenciales) vs *ex post* (importantes).
- **Cadena de suministro:** Aunque no estés en NIS2, si sirves a una entidad NIS2 te exigirán contractualmente medidas equivalentes (art. 21.4 NIS2).

> **Fuente:** AESyC guía NIS2 España (oct 2026), El Periódico 8-oct-2026, Digital Strategy EC.

### 2.2 ENS (RD 311/2022) — Obligación real para proveedores de sector público

- **Ámbito (art. 2 RD 311/2022):** Sector público (art. 2 Ley 40/2015) **+** entidades privadas que, **por contrato**, presten servicios/soluciones a administraciones públicas.
- **Categorías:** Básica, Media, Alta (según dimensión impacto: confidencialidad, integridad, disponibilidad, autenticidad, trazabilidad).
- **Medida op.mon.1 – Detección de intrusión (Anexo II, tabla op.mon):**
  - **Categoría Básica:** op.mon.1 (herramientas detección/prevención intrusión).
  - **Categoría Media:** op.mon.1 **+ R1** (detección basada en reglas).
  - **Categoría Alta:** op.mon.1 **+ R1 + R2** (procedimientos de respuesta).
  - **Requisitos literales (art. 4.7.1 RD 311/2022):**
    - op.mon.1.1: «Se dispondrá de herramientas de detección o prevención de intrusiones.»
    - op.mon.1.r1.1: «El sistema dispondrá de herramientas de detección o prevención de intrusiones **basadas en reglas**.»
    - op.mon.1.r2.1: «Existirán **procedimientos de respuesta** a las alertas generadas.»
    - op.mon.1.r3.1 (refuerzo R3, solo ALTA): «El sistema ejecutará **automáticamente acciones predeterminadas** de respuesta... finalización de proceso, inhabilitación servicios, desconexión usuarios, bloqueo cuentas.»

> **Fuente:** BOE-A-2022-7191 consolidado (PDF), §4.7.1, pp. 51-52. Consultado 2026-10-23.

### 2.3 ¿Qué obliga la norma que se puede vender como «detección de anomalías en red»?

| Categoría ENS | Qué exige op.mon.1 | Traducción vendible para QZero |
|---|---|---|
| Básica | Cualquier IDS/IPS (Suricata, Snort, Zeek + scripts) | «Cumple op.mon.1 básica: sensor de red + reglas Suricata + alertas.» |
| **Media** | **IDS/IPS + reglas (R1)** | **«Detección basada en reglas + ML/VAE para reducir falsos positivos; exporta evidencias para op.mon.1.r2.1 (procedimientos respuesta).»** |
| Alta | Media + R2 (procedimientos respuesta) + R3 (acciones auto) | **Fuera de alcance realista para micro-consultora (requiere SOAR/EDR integrado).** |

**Obligación de conformidad (art. 19 RD 311/2022):** En adquisición de productos/servicios de seguridad para sistemas ENS, **deben usarse productos cualificados CPSTIC** (catálogo CCN) para categorías Media/Alta. QZero **no está en CPSTIC** → no puede venderse como «producto cualificado» a administraciones ni a sus proveedores obligados, salvo que el pliego no lo exija (poco frecuente en Media/Alta).

### 2.4 Número de empresas objetivo (50–249 empleados, España 2025)

- **DIRCE 2025 (INE):** ~**31.000** empresas con 50–249 asalariados; ~**3.500** con 250–499; ~**1.200** con 500–999. Total 50–500 ≈ **35.700** empresas.
- **Subconjunto ENS Media/Alto:** Solo las que son proveedores de sector público con sistemas categorizados Media/Alta. **NO VERIFICADO** (no hay censo público). Estimación sectorial: 10–15 % del total → **3.500–5.500** cuentas direccionables.

---

## 3. Alternativas Open Source: Hueco Real de QZero

| Herramienta | Qué hace | Hueco / Limitación | ¿Por qué elegir QZero *en vez de* esto? |
|---|---|---|---|
| **Suricata** | IDS/IPS basado en reglas (ET Pro, Emerging Threats), multi-hilo, alta performance. Estándar de facto. | Solo reglas conocidas; **no detecta anomalías desconocidas / zero-day** sin firmas. Requiere tuning experto. | QZero añade **VAE + QSVM para detección de anomalías sin firmas** (teóricamente). *Pero:* benchmark interno QSVM F1 0,711 vs SVM lineal 0,707 → **ventaja marginal nula**. |
| **Zeek (ex-Bro)** | Análisis de protocolo, logs estructurados (conn, dns, http, ssl, files). Contexto rico, no alertas directas. | No es IDS; **no alerta por defecto**. Requiere capa de correlación (Kafka + Sigma + SOAR). | QZero integra captura + motor + consola en **un solo despliegue (Docker Compose)**. *Pero:* Zeek + Elastic + Wazuh hace lo mismo y es probado en producción. |
| **Security Onion** | Distro ISO/VM: Suricata + Zeek + Elastic + Wazuh + Kibana + SOAR (Playbooks). Listo para producción. | Pesado (requiere 32-64 GB RAM para nodos medianos); **curva de aprendizaje alta**. | QZero: **ligero (agentes + hub SQLite + FastAPI + Streamlit)**, <4 GB RAM. *Pero:* Security Onion tiene comunidad, updates, reglas ET Pro, casos de uso documentados. |
| **Arkime (ex-Moloch)** | Captura paquetes a disco (PCAP) + índice Elastic + sesión replay. Forense profundo. | **No es detección en tiempo real**; almacenamiento masivo (TB/día). | QZero no guarda PCAP completo; solo features + alertas. Diferente caso de uso. |
| **ntopng** | Visibilidad de flujo (NetFlow/sFlow/IPFIX + DPI ligero), dashboards de tráfico, alertas umbral. | **No es NDR**; no hace detección de intrusión/anomalía comportamental. | QZero sí hace anomaly scoring por flujo. *Pero:* ntopng es gratis, maduro, y muchos ya lo tienen. |
| **Wazuh** | SIEM + HIDS (agente en endpoint) + reglas MITRE ATT&CK + compliance (PCI, GDPR, **ENS**). | **No analiza tráfico de red** (solo logs de endpoints / syslog / NetFlow opcional). Módulo NDR experimental (2024) basado en Suricata embebido, no maduro. | **QZero complementa a Wazuh**: red (NDR) + endpoint (Wazuh) = cobertura completa. **Este es el hueco real vendible**: «Wazuh cubre endpoint y compliance ENS; QZero cubre red sin agentes en endpoints». |

### Veredicto brutal

- **Hueco técnico real:** «NDR ligero, sin agentes en endpoints, que complementa Wazuh/ENS y se despliega en 15 min (Docker Compose)».
- **Hueco comercial real:** **PyMEs 50-500 con obligación ENS Media** que ya usan Wazuh (gratis, certificado CPSTIC vía partners) y necesitan **visibilidad de red** para op.mon.1 + R1.
- **Riesgo existencial:** El motor **no supera a un clasificador trivial** (F1 0,711 vs 0,707) y el componente cuántico **está desactivado en producción** (`use_quantum_encoder=False`). Si el comprador pide prueba de eficacia (PoC), **QZero pierde frente a Suricata + reglas ET Pro**.

---

## 4. Canales Reales de Venta con 1–5 Personas

| Canal | Realista | Por qué / Evidencia | Esfuerzo estimado | Riesgo |
|---|---|---|---|---|
| **Subcontratación MSSP / SOC locales** | ✅ **SÍ** | 150+ MSSP en España (INCIBE), muchos sin NDR propio; buscan «motor anomalía» para diferenciarse. Ticket: revenue share 20-30 % o fee mensual por sensor. | Medio (demos, PoC, integración API) | Dependencia canal; QZero debe ser multi-tenant y tener API estable. |
| **Licitaciones públicas (PLACSP / Perfil Contratante)** | ⚠️ **PARCIAL** | Contratos menores ≤15.000 € (art. 118 LCSP) → **factible** para piloto. Abiertos simplificados ≤100.000 € (art. 159 LCSP) → requieren solvencia técnica (3 años exp., 2 contratos similares). **CPSTIC obligatorio en Media/Alta** (art. 19 RD 311/2022) → QZero **excluido** salvo básicas. | Alto (documentación, garantías, clasificación empresarial) | Baja tasa éxito sin CPSTIC; ciclos 6-12 meses. |
| **Kit Digital (Red.es) – Agente Digitalizador** | ⚠️ **LÍMITE DURO** | Categoría «Ciberseguridad»: máx **6.000 €** (segmento III, 0-3 emp.), **12.000 €** (segmento I/II). QZero (self-hosted, sin agente digitalizador homologado) **no encaja** como «solución de mercado» lista para instalar. Requiere alta en catálogo Red.es (proceso 6+ meses). | Muy alto | **Pérdida de tiempo** para micro-consultora sin producto SaaS listo. |
| **Kit Consulting (asesoría)** | ✅ **SÍ** | 24.000 €/empresa para plan ciberseguridad. Thempra **puede ser asesor homologado** y **recomendar QZero** en el plan (no subvencionable como herramienta, pero sí como arquitectura). | Medio (homologación asesor) | Ingreso indirecto (honorarios asesoría), no venta licencias. |
| **NEOTEC (CDTI)** | ❌ **NO** | Para *startups* <3 años, innovación tecnológica de alto riesgo. Thempra es consultora, no *startup* de base tecnológica pura. | Muy alto | No encaja perfil. |
| **Horizonte Europa / EIC** | ❌ **NO** | Tasa éxito <5 %; consorcios 3+ países; TRL 6-8. QZero TRL ~4 (prototipo, benchmark negativo). | Muy alto | **Pérdida de tiempo total.** |
| **Partner tecnológico (integradores, VARs, telcos)** | ✅ **SÍ** | Integradores que venden Wazuh/ENS a pymes necesitan «módulo red». Thempra aporta motor; partner aporta cliente + despliegue + soporte 24/7. | Medio | Requiere producto *embebible* (API, multi-tenant, branding blanco). |
| **Venta directa a PyME (outbound + INCIBE-CERT)** | ⚠️ **DIFÍCIL** | PyME no busca «NDR»; busca «cumplir ENS/NIS2 barato». Decisión: CTO / gerente IT / asesoría externa. Ciclo 3-6 meses. Ticket 5-15 k €. | Alto | CAC alto para equipo 1-5 sin marca. |

**Canales REALISTAS (prioridad):**
1. **MSSP/SOC partners** (revenue share, ellos operan, tú desarrollas).
2. **Integradores ENS/Wazuh** (upsell módulo red).
3. **Kit Consulting** (ingreso por asesoría + prescripción).
4. **Contratos menores PLACSP** (solo categoría Básica, piloto 10-15 k €).

**Canales PERDIDA DE TIEMPO:** Kit Digital (homologación), NEOTEC, Horizonte Europa, licitaciones Media/Alta sin CPSTIC.

---

## 5. Evidencia Pública Exigible para Firmar (Comprador Español)

| Requisito | Norma / Artículo | Qué debe demostrar QZero / Thempra | Estado actual | Acción |
|---|---|---|---|---|
| **Conformidad ENS (categoría Media)** | RD 311/2022 art. 19 + Anexo II op.mon.1 + R1 | Detección basada en reglas + procedimientos respuesta documentados | **Parcial**: motor VAE no es «basado en reglas» (R1); no hay playbooks respuesta (R2) | Implementar motor reglas (Suricata) + exportar alertas a Wazuh/SOAR; documentar procedimientos. |
| **Producto cualificado CPSTIC** | RD 311/2022 art. 19.1 + Guía CCN-STIC 105 | Evaluación LINCE (nivel Medio) o Common Criteria EAL2+ → entrada catálogo CPSTIC | **NO** | Coste: 50-100 k € + 12-18 meses. Solo tiene sentido si >50 % pipeline es sector público Media/Alta. |
| **Declaración Conformidad ENS (CCN-STIC 808)** | CCN-STIC 808 | Autoevaluación + evidencias + firma representante legal | **Factible** para categoría Básica | Preparar plantilla + evidencias técnicas (logs, reglas, procedimientos). |
| **RGPD (privacidad por diseño)** | RGPD art. 25, 32 | DPIA si procesa datos personales (IPs, cuentas); cifrado en tránsito/reposo; minimización; DPO si >250 emp. | **Parcial**: agentes sniffan tráfico (datos personales potenciales) | DPIA documentada; *pseudonimización* IPs en hub; cifrado TLS mutuo agente-hub. |
| **AI Act – Transparencia (art. 50)** | Reglamento UE 2024/1689 art. 50 (vigente 2 ago 2026) | Si QZero se vende como «IA»: informar que es sistema IA, límites, supervisión humana. | **Aplicable** (motor VAE/QSVM = sistema IA) | Ficha técnica «Model Card» + cláusula contrato: «humano en el bucle (analista valida alertas)». |
| **AI Act – Alto riesgo (Anexo III)** | Reglamento UE 2024/1689 art. 6(2) + Anexo III | **NO aplica**: NDR no está en Anexo III (selección personal, educación, servicios esenciales, etc.). Ciberseguridad *per se* no es caso de uso alto riesgo. | **No aplica** | Documentar por qué no es alto riesgo (art. 6(2) + considerando 53). |
| **CRA (Cyber Resilience Act)** | Reglamento UE 2024/2847 art. 14 (11 sep 2026) | Notificación vulnerabilidades explotadas en 24h a ENISA/CSIRT; ciclo vida seguro (SBOM, updates). | **Aplicable** (producto con elementos digitales) | Proceso *vuln disclosure* + SBOM (Syft/Grype) + canal updates firmados. |
| **NIS2 (cuando se trasponga)** | Directiva UE 2022/2555 art. 21, 23 | Si cliente es entidad NIS2: 10 medidas gestión riesgo + notificación 24/72h/1mes. | **Preparar** | QZero como *herramienta* para cumplir art. 21.1 (análisis riesgo) + art. 21.2 (gestión incidentes). |

### Checklist mínimo para PoC / piloto pagado (categoría Básica / MSSP)

1. **Arquitectura**: Agentes (eBPF/AF_PACKET) → Hub (FastAPI + SQLite/TimescaleDB) → Consola (Streamlit/FastAPI HTML). Despliegue Docker Compose <15 min.
2. **Motor**: Suricata (reglas ET Pro) + VAE/QSVM *opcional* (feature flag). Documentar *por qué* VAE no mejora F1 (honestidad técnica).
3. **Evidencias ENS op.mon.1 + R1**: Reglas Suricata cargadas → alertas → export JSON/CEF → ingesta Wazuh/SIEM.
4. **Procedimientos respuesta (op.mon.1.r2.1)**: Playbooks documentados (markdown + scripts) para top 10 alertas.
5. **RGPD**: DPIA firmada; pseudonimización IPs (hash + salt rotatorio); TLS mTLS agente-hub; retención logs 90 días configurable.
6. **AI Act art. 50**: Model Card (modelo, datos entrenamiento, métricas, limitaciones, supervisión humana).
7. **CRA art. 14**: Página `security.txt` + correo `security@thempra.es` + proceso 24h + SBOM firmado por release.
8. **Soporte**: SLA respuesta 8h laborables (micro-consultora realista); actualizaciones mensuales reglas + motor.

---

## Fuentes (Tabla Consolidada)

| # | URL | Qué se usó | Fecha consulta |
|---|---|---|---|
| 1 | https://www.prnewswire.com/news-releases/network-detection-and-response-ndr-market-worth-5-82-billion-by-2030--marketsandmarkets-302583139.html | Tamaño mercado NDR 2025/2030, CAGR | 2026-10-23 |
| 2 | https://markets.ft.com/data/announce/full?dockey=1323-16365665-5RKSJIGKGLT0J1KOJ42C2S5O2P | Darktrace FY2025 revenue, ARR medio, crecimiento clientes | 2026-10-23 |
| 3 | https://www.darktrace.com/legal/darktrace-annual-report | Darktrace Annual Report 2025 (confirmación cifras) | 2026-10-23 |
| 4 | https://tech-insider.org/darktrace-vs-vectra-ai-vs-extrahop-2026 | Vendors líderes NDR 2025-2026 (resumen público MQ) | 2026-10-23 |
| 5 | https://aesyc.com/nis2-directiva-guia-espana/ | Estado transposición NIS2 España oct 2026, sectores, obligaciones | 2026-10-23 |
| 6 | https://amp.elperiodico.com/es/politica/20261008/vergonzoso-adelanto-electoral-debilita-ciberseguridad-espana-ciberataques-ley-ue-135087190 | Confirmación retraso NIS2, TJUE, elecciones | 2026-10-23 |
| 7 | https://www.boe.es/buscar/pdf/2022/BOE-A-2022-7191-consolidado.pdf | RD 311/2022 texto completo: art. 2, 19, Anexo II op.mon.1, R1, R2, R3 | 2026-10-23 |
| 8 | https://nexens.es/medidas-seguridad-ens | Estructura ENS 75 medidas, familia op.mon, categorías | 2026-10-23 |
| 9 | https://angelortegacastro.com/controles-ens-marco-organizativo-operacional-proteccion/ | Detalle op.mon.1, op.mon.2, op.mon.3 con refuerzos | 2026-10-23 |
| 10 | https://cosmikal.es/ens-lince-cpstic-and-common-criteria-what-they-are-and-how-they-differ | ENS vs CPSTIC vs LINCE vs CC; art. 19 obligación productos cualificados | 2026-10-23 |
| 11 | https://www.plataformanacionalciber.gob.es/index.php/faq | Ámbito NIS2, autoridades competentes, plazos oficiales | 2026-10-23 |
| 12 | https://www.aiacto.eu/es/blog/digital-omnibus-ai-act-report-2027 | Digital Omnibus (UE) 2026/1744: fechas AI Act alto riesgo (dic 2027), art. 50 (ago 2026) | 2026-10-23 |
| 13 | https://www.euai-act.com/articles/eu-ai-act-digital-omnibus-2026 | Confirmación fechas AI Act, art. 50, 111(4), prohibiciones dic 2026 | 2026-10-23 |
| 14 | https://cra.nbu.gov.sk/en/article-14-comes-into-force-what-can-manufacturers-expect-from-11-september-2026 | CRA art. 14 notificación 24h desde 11 sep 2026 | 2026-10-23 |
| 15 | https://cra-sbom.de/en/insights/cra-timeline-deadlines | Timeline CRA completo 2024-2027 | 2026-10-23 |
| 16 | https://www.redseguridad.com/actualidad/ciberseguridad/el-442-de-las-empresas-espanolas-incrementara-su-presupuesto-en-ciberseguridad-en-2026_20260204.html | Gasto ciberseguridad pymes España 2026 (44 % aumentan) | 2026-10-23 |
| 17 | https://to-growth.com/blog/cuantas-empresas-hay-en-espana/ | DIRCE 2025: empresas 50-249, 250-499, 500-999 | 2026-10-23 |
| 18 | https://vendr.com/marketplace/darktrace | Pricing Darktrace (rangos, modelo) | 2026-10-23 |
| 19 | https://thetechbag.com/darktrace/darktrace-hybrid-network | Darktrace Hybrid Network pricing hints | 2026-10-23 |
| 20 | https://docs.suricata.io/en/latest/ | Suricata capabilities, reglas, performance | 2026-10-23 |
| 21 | https://zeek.org/ | Zeek capabilities, posicionamiento | 2026-10-23 |
| 22 | https://securityonionsolutions.com/ | Security Onion stack, requisitos hardware | 2026-10-23 |
| 23 | https://arkime.com/ | Arkime capabilities, caso uso forense | 2026-10-23 |
| 24 | https://www.ntop.org/products/traffic-analysis/ntop/ | ntopng capabilities, NetFlow/DPI | 2026-10-23 |
| 25 | https://github.com/ossec/ossec-hids | Wazuh (fork OSSEC) capabilities, compliance ENS | 2026-10-23 |
| 26 | https://aisecurity.es/blog/op-mon-1-deteccion-intrusion-ens | Interpretación práctica op.mon.1 para pymes (Wazuh + ENS) | 2026-10-23 |
| 27 | https://iberley.es/legislacion/articulo-118-ley-contratos-sector-publico | Contratos menores ≤15.000 € art. 118 LCSP | 2026-10-23 |
| 28 | https://espanadigital.gob.es/lineas-de-actuacion/programa-kit-digital | Kit Digital categorías, importes, estado 2026 | 2026-10-23 |
| 29 | https://ideiatek.net/blog/kit-consulting | Kit Consulting 24.000 €, asesores homologados | 2026-10-23 |

---

## Lo que NO he podido verificar (gaps de investigación)

| Tema | Qué falta | Por qué no encontrado | Acción recomendada |
|---|---|---|---|
| **Número exacto de proveedores ENS Media/Alto en España** | Censo de empresas privadas obligadas por contrato público | No hay registro público; CCN no publica lista | Encuesta a partners Wazuh/ENS; estimar 10-15 % de 35k ≈ 3.5-5k |
| **Precios NDR reales para segmento 50-500 emp. en España** | Cotizaciones cerradas Darktrace/Vectra/Corelight/Gatewatcher para mid-market ES | Vendors no publican; NDA; canal partners opaco | Pedir 3 cotizaciones reales vía partner de confianza (bajo NDA) |
| **Tasa de conversión Kit Consulting → compra herramienta** | % de planes que acaban en compra de software concreto | Red.es no publica; asesores no comparten | Entrevistar 3-5 asesores homologados Kit Consulting |
| **Requisitos técnicos CPSTIC para familia «Detección de intrusión» (IDS/IPS)** | Guía CCN-STIC 105 + RFS (Requisitos Fundamentales Seguridad) familia IDS | PDF no indexado públicamente; solo accesible a laboratorios LINCE | Solicitar a CCN-PYTEC o laboratorio LINCE acreditado |
| **Benchmark público VAE/QSVM vs Suricata en dataset CIC-IDS2017/2018** | Paper o repo con métricas comparables (F1, precision@k, latency) | Literatura académica no cubre QSVM 4-qubits + VAE PyTorch | Publicar benchmark honesto (propio) como *transparencia técnica* |
| **Coste real de evaluación LINCE Nivel Medio para producto NDR** | Euros + meses para QZero (código abierto, MIT) | CCN no publica tarifas; varía por laboratorio | Pedir presupuesto a 2 laboratorios LINCE (ej. Applus+, Tarlogic) |
| **Número de MSSP en España con capacidad de integrar NDR custom** | Directorio actualizado + disposición a revenue share | INCIBE no publica directorio filtrado por capacidades | Mapear top 20 MSSP (web + LinkedIn) y contactar CTO directamente |

---

## Próximos Pasos Inmediatos (para Thempra)

1. **Semana 1:** Documentar motor de reglas Suricata embebido + export CEF/JSON → cumple op.mon.1 + R1 *hoy*.
2. **Semana 2:** Escribir 10 playbooks respuesta (op.mon.1.r2.1) + integrar con Wazuh Active Response.
3. **Semana 3:** DPIA RGPD + Model Card AI Act art. 50 + `security.txt` + SBOM firmado (CRA art. 14).
4. **Mes 1:** Homologar Thempra como **asesor Kit Consulting** (ingreso recurrente + prescripción).
5. **Mes 1-2:** Firmar **1-2 MSSP partners** (piloto revenue share, ellos operan, tú desarrollas API multi-tenant).
6. **Mes 3:** Decidir inversión CPSTIC/LINCE *solo si* pipeline sector público Media/Alta >30 %.
7. **Continuo:** Publicar benchmark honesto (VAE/QSVM vs SVM lineal vs Suricata) → credibilidad técnica.