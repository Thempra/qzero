# docs/ — Índice de documentación

## Fundacionales (fuente única de cada tema — actualizar aquí, no en documentos secundarios)

| Doc | Tema propiedad (single source of truth) |
|---|---|
| [prd.md](prd.md) | Idea, funcionalidades, alcance, criterios de éxito (✔ §4), preguntas abiertas |
| [trd.md](trd.md) | Stack, deploy, APIs externas, configuración/env vars (✔ §4), knobs del PostFilter (✔ §5), decisiones no re-decidirables (✔ §6) |
| [flow.md](flow.md) | Pipeline del agente, navegación SOC, comportamiento de cada botón |
| [design-brief.md](design-brief.md) | Paleta, tipografía, componentes, aspecto de cada pantalla |
| [backend-schema.md](backend-schema.md) | Tablas/ER SQLite (✔ §1), auth (✔ §2), contrato de endpoints REST/WS (✔ §3), flujos e2e |
| [implementation-plan.md](implementation-plan.md) | Secuencia de construcción + roadmap v3.1 con criterios de aceptación |

Regla: un hecho técnico vive en **un** doc; los demás lo referencian por sección. Cambiar un knob/endpoint ⇒ actualizar solo su doc propietario (y el código, en el mismo commit).

## Operativa (complementaria, no fundacional)

- [ARCHITECTURE.md](ARCHITECTURE.md) — estructura de paquetes y decisiones de diseño v3.
- [CLI_README.md](CLI_README.md), [QUICKSTART.md](QUICKSTART.md), [INSTALLATION.md](INSTALLATION.md), [USAGE.md](USAGE.md), [TROUBLESHOOTING.md](TROUBLESHOOTING.md) — guías de uso.
- [LLM-CALLS.md](LLM-CALLS.md) — puntos de llamada a IA/red reales del proyecto.
- [MANUAL_BLUETEAM.md](MANUAL_BLUETEAM.md), [MANUAL_REDTEAM.md](MANUAL_REDTEAM.md), [PCAPS-ETIQUETADOS.md](PCAPS-ETIQUETADOS.md) — operación blue/red team.
- [PRESENTATION.md](PRESENTATION.md), [PRESENTATION_SCRIPT.md](PRESENTATION_SCRIPT.md), [REFERENCES.md](REFERENCES.md), [papers/](papers/) — divulgación y bibliografía.

## legacy/

Documentos del QZero v1–v2 (época hackathon/IDS-IPS genérico: PROJECT_DEFINITION, REQUIREMENTS, ROADMAP, estructura de módulos antigua, README viejo). Conservados por valor histórico; **no** son fuente de verdad — contradicen a los fundacionales (p. ej. citan módulos `sniffer.py`/`pipeline.py`/`inference.py` que ya no existen). El contrato real es `backend-schema.md §3`; el stack real, `trd.md`.
