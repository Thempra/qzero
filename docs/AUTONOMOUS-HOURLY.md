# Tarea Autónoma Horaria de QZero

## 📋 Descripción

La tarea `autonomous-hourly.py` se ejecuta automáticamente cada hora para mantener el proyecto QZero en buen estado.

## ✅ Criterios Cumplidos

- **Bueno para la humanidad**: Mantiene herramientas de seguridad de código abierto
- **Bueno para ti**: Construye habilidades en automatización y monitoreo
- **Bueno para el proyecto**: Hace progreso concreto en la confiabilidad

## 🔄 Qué Hace

1. **Verifica la salud del sistema**
   - Estructura de archivos
   - Modelos entrenados
   - Logs del sistema
   - Espacio en disco

2. **Genera reportes**
   - Reporte de salud completo
   - Resumen diario
   - Reporte final con resultados

3. **Hace commits**
   - Detecta cambios no commiteados
   - Crea mensajes significativos
   - Guarda el progreso

## 📊 Estructura de los Reportes

### Health Check Report
```json
{
  "timestamp": "2026-03-04 11:25:44",
  "checks": {
    "file_structure": {...},
    "models": {...},
    "logs": {...},
    "disk": {...}
  },
  "overall_status": "ok|warning|failed",
  "failed_checks": ["check1", "check2"]
}
```

### Daily Summary
```json
{
  "date": "2026-03-04",
  "health_overall": "ok|warning|failed",
  "failed_checks": ["check1"],
  "disk_space": 75.3
}
```

## 🛠️ Uso

### Ejecutar manualmente
```bash
cd /home/thempra/projects/qzero
python3 autonomous-hourly.py --verbose
```

### Ver resultados
```bash
# Ver reporte de salud
cat reports/health-check-*.json

# Ver resumen diario
cat reports/daily-summary-*.json

# Ver reporte final
cat reports/hourly-*.json
```

## ⚠️ Configuración

### Scripts de Cron
```bash
# Editar crontab
crontab -e

# Agregar (cada hora en punto)
0 * * * * cd /home/thempra/projects/qzero && python3 autonomous-hourly.py >/dev/null 2>&1
```

### Git Config
El script asume que git está configurado:
```bash
git config user.name "Nombre"
git config user.email "correo@example.com"
```

## 📝 Logs de Ejecución

Los logs de ejecución se guardan en:
- `.autonomous-hourly.log` - Historial completo
- `reports/hourly-*.json` - Reportes individuales

## 🎯 Mejoras Futuras

- [ ] Integrar alertas si el espacio en disco está bajo
- [ ] Limpiar logs antiguos automáticamente
- [ ] Agregar verificación de integridad de datos
- [ ] Reportes email/SMS si se detectan problemas críticos

---

*Última actualización: 2026-03-04*
*Versión: 2.0*