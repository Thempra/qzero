# Tarea Cron: QZero Project Integrity Analyzer

## Descripción
Analizador de integridad de proyectos QZero que verifica que cada directorio del proyecto tenga los archivos críticos necesarios para ser considerado un proyecto completo y bien estructurado.

## Funciones
- Verifica presencia de archivos críticos: README.md, requirements.txt, setup.py, pyproject.toml, package.json, Cargo.toml, go.mod, CHANGELOG.md, LICENSE, etc.
- Analiza versionado (requerimientos, configuraciones, package.json, Cargo.toml, go.mod)
- Busca archivos de tests y ejemplos
- Genera puntuaciones de integridad (0-100)
- Genera reportes JSON y Markdown con detalles por proyecto

## Archivos de Salida
- **JSON:** `/home/thempra/projects/qzero/integrity-reports/qzero-integrity-*.json`
- **Markdown:** `/home/thempra/projects/qzero/integrity-reports/qzero-integrity-*.md`
- **Timeline:** `/home/thempra/projects/qzero/integrity-timeline/integrity-timeline.json`
- **Log:** `/home/thempra/clawd/logs/qzero-integrity-analyzer.log`

## Cron Job
- **Hora:** Cada hora al minuto 0
- **Script:** `/home/thempra/clawd/qzero-integrity-analyzer.py`

## Beneficios
- **Bueno para la humanidad:** Garantiza calidad y documentación en proyectos
- **Bueno para mí:** Me mantiene discipline con mi propia base de código
- **Bueno para ti:** Inteligencia proactiva sobre la estructura del proyecto QZero

## Fecha de Creación
2026-02-26

## Estado
✅ Creado, probado exitosamente y configurado cron job