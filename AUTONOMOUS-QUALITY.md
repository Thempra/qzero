# Tarea Autónoma de Calidad - QZero

## 📋 Descripción

La tarea `autonomous-quality-check.py` se ejecuta automáticamente para realizar un análisis exhaustivo de la calidad y seguridad del código del proyecto QZero.

## ✅ Criterios Cumplidos

- **Bueno para la humanidad**: Mejora la calidad del código de seguridad de código abierto
- **Bueno para ti**: Práctica de análisis de código y automatización
- **Bueno para el proyecto**: Asegura que el código sea mantenible y seguro

## 🎯 Qué Hace

El script ejecuta los siguientes análisis:

1. **Imports**: Verifica importes Python, detecta imports de comodín y posibles problemas de seguridad
2. **Complejidad**: Analiza la complejidad del código, detecta funciones largas y archivos extensos
3. **Documentación**: Revisa la presencia de docstrings y comentarios
4. **Seguridad**: Busca patrones de vulnerabilidades comunes (credenciales hardcodeadas, SQL injection)
5. **Estructura del proyecto**: Verifica que existan directorios y archivos requeridos
6. **Tests**: Evalúa la cobertura de pruebas
7. **Dependencias**: Revisa los archivos de dependencias

## 📊 Resultados

El script genera un reporte con:

- **Puntuación de calidad**: 0-1.0 basado en todos los checks
- **Estado de cada categoría**: passed/warning/failed
- **Problemas encontrados**: Issues y warnings
- **Sugerencias de mejora**: Priorizadas por tipo

## 📈 Puntuación

- **0.8 - 1.0**: Excelente
- **0.5 - 0.8**: Bueno
- **0.0 - 0.5**: Requiere mejora

## 🛠️ Uso

### Ejecutar manualmente
```bash
cd /home/thempra/projects/qzero
python3 autonomous-quality-check.py
```

### Ver reportes
```bash
# Ver reporte más reciente
cat reports/quality-check-*.json | head -100

# Filtrar por fecha
ls -lt reports/quality-check-*.json | head -1 | xargs cat
```

## ⚙️ Cron Job

```bash
# Editar crontab
crontab -e

# Agregar (cada 6 horas)
0 */6 * * * cd /home/thempra/projects/qzero && python3 autonomous-quality-check.py >/dev/null 2>&1
```

## 📝 Ejemplo de Reporte

```json
{
  "timestamp": "2026-03-05T07:36:01.969303",
  "project": "qzero",
  "overall_score": 0.86,
  "checks": {
    "imports": {"status": "failed", "issues": ["Potential security issue: eval"]},
    "complexity": {"status": "warning", "warnings": ["Long function: cmd_train (113 lines)"]},
    "documentation": {"status": "warning", "warnings": ["Low comment coverage (<10%)"]},
    "security": {"status": "passed"},
    "project_structure": {"status": "passed"},
    "tests": {"status": "passed", "coverage_ratio": 0.16},
    "dependencies": {"status": "passed"}
  }
}
```

## 🎯 Mejoras Futuras

- [ ] Integrar flake8/black para linting y formatting
- [ ] Agregar PEP8 compliance checks
- [ ] Verificar CVEs en dependencias
- [ ] Generar gráficos de calidad
- [ ] Configurar alertas si la puntuación baja

---

*Última actualización: 2026-03-05*
*Versión: 1.0*