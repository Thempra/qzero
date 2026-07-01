# Tarea Autónoma Horaria v3 de QZero

## 📋 Descripción

La tarea `autonomous-hourly-v3.py` se ejecuta automáticamente cada hora para mantener el proyecto QZero en buen estado con un enfoque productivo.

## ✅ Criterios Cumplidos

- **Bueno para la humanidad**: Mantiene herramientas de seguridad de código abierto
- **Bueno para ti**: Práctica de scripting avanzado de Python
- **Bueno para el proyecto**: Mantenimiento activo y optimización

## 🔄 Qué Hace

1. **Verifica configuración**
   - Git config (nombre y email)

2. **Verifica salud del sistema**
   - Espacio en disco
   - Archivos críticos del proyecto
   - Actividad reciente

3. **Mantenimiento**
   - Limpieza de logs antiguos (>30 días)

4. **Control de versiones**
   - Detecta y commitea cambios
   - Mensajes significativos

5. **Reportes**
   - Estructura JSON con todos los resultados
   - Estado general del proyecto

## 📊 Estructura del Reporte

```json
{
  "timestamp": "2026-03-04T13:21:00",
  "task": "autonomous_hourly_v3",
  "git_config": {"status": "ok"},
  "disk_space": {
    "status": "ok",
    "free_gb": 15.23,
    "free_percent": 35.7
  },
  "project_files": {"status": "ok"},
  "recent_activity": {
    "status": "ok",
    "last_report": "hourly-20260304091500.json",
    "age_hours": 4.2
  },
  "cleanup": {
    "status": "ok",
    "deleted": 0
  },
  "commit": {
    "status": "ok",
    "files_committed": 3
  },
  "overall_status": "ok"
}
```

## 🛠️ Uso

### Ejecutar manualmente
```bash
cd /home/thempra/projects/qzero
python3 autonomous-hourly-v3.py
```

### Ver reportes
```bash
# Ver reporte más reciente
ls -lt reports/hourly-*.json | head -1
cat reports/$(ls -t reports/hourly-*.json | head -1)
```

## ⚙️ Configuración Cron

### Agregar a crontab
```bash
crontab -e

# Agregar (cada hora en punto)
0 * * * * cd /home/thempra/projects/qzero && python3 autonomous-hourly-v3.py >/dev/null 2>&1
```

### Verificar cron
```bash
crontab -l
```

## 📝 Notas de Desarrollo

**Versión 3**: Foco en productividad real
- Eliminadas tareas innecesarias (training, data generation)
- Foco en mantenimiento y salud del sistema
- Scripts más concisos y legibles
- Mejor manejo de errores
- Reportes estructurados

## 🎯 Mejoras Futuras

- [ ] Integrar con sistema de alertas (Telegram)
- [ ] Verificar modelos entrenados
- [ ] Análisis de rendimiento de modelos
- [ ] Reportes más detallados
- [ ] Integración con CI/CD

---

*Última actualización: 2026-03-04*
*Versión: 3.0*