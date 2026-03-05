# Tarea Autónoma Horaria de Anomalías de QZero

## 📋 Descripción

La tarea `autonomous-anomaly-detection.py` se ejecuta automáticamente cada hora para detectar y reportar anomalías en los datos de QZero y enviar alertas para problemas críticos.

## ✅ Criterios Cumplidos

- **Bueno para la humanidad**: Monitoreo de seguridad proactivo y detección temprana de amenazas
- **Bueno para ti**: Práctica de análisis de seguridad y operación autónoma
- **Bueno para mí**: Conciencia de seguridad del proyecto y sistema de alertas tempranas

## 🔄 Qué Hace

1. **Analiza actividad reciente**
   - Insights y reportes creados recientemente
   - Patrones anómalos en archivos generados

2. **Revisa reportes de seguridad**
   - Busca alertas CRÍTICAS, ALERTAS, AMENAZAS
   - Keywords de vulnerabilidad

3. **Analiza actividad de red**
   - Cambios en configuración de red (< 7 días)
   - Archivos de configuración modificados

4. **Evalúa rendimiento de modelos**
   - Accuracy bajo de 0.7
   - Loss alto > 1.0

5. **Verifica integridad de datos**
   - Archivos JSON corruptos
   - Datos faltantes o vacíos

6. **Revisa configuración de Telegram**
   - Verifica que alertas estén habilitadas

7. **Genera reportes**
   - Reporte JSON completo con todas las anomalías
   - Nivel de riesgo global

8. **Envía alertas a Telegram**
   - Solo para riesgo CRÍTICO o ALTO

9. **Limpia reportes antiguos**
   - Elimina reportes de más de 30 días

## 📊 Estructura del Reporte

```json
{
  "timestamp": "2026-03-04T17:25:00",
  "task": "autonomous_anomaly_detection",
  "summary": {
    "overall_risk": "MEDIUM|HIGH|CRITICAL|LOW|NONE",
    "total_anomalies": 5,
    "anomalies_by_severity": {
      "CRITICAL": 1,
      "HIGH": 0,
      "MEDIUM": 2,
      "LOW": 2
    }
  },
  "recent_activity": {
    "files_analyzed": 150,
    "total_size_mb": 125.4
  },
  "anomalies": {
    "insight_activity": [...],
    "security_reports": [...],
    "network_activity": [...],
    "model_performance": [...],
    "data_integrity": [...],
    "telegram_config": [...]
  },
  "recommendations": [...]
}
```

## 🚨 Niveles de Riesgo

| Riesgo | Anomalías CRÍTICAS | Anomalías ALTAS | Acción |
|--------|-------------------|----------------|--------|
| CRÍTICO | ≥ 1 | ≥ 1 | REVISAR INMEDIATAMENTE |
| ALTO | 0 | ≥ 1 | REVISAR PRONTO |
| MEDIO | 0 | 0 | MONITOREAR |
| BAJO | 0 | 0 | REVISAR PRONTO |
| NINGUNO | 0 | 0 | NORMAL |

## 🛠️ Uso

### Ejecutar manualmente
```bash
cd /home/thempra/projects/qzero
python3 autonomous-anomaly-detection.py
```

### Ver reportes
```bash
# Ver reporte más reciente
ls -lt reports/anomaly-detection/anomaly-report-*.json | head -1
cat reports/anomaly-detection/$(ls -t reports/anomaly-detection/anomaly-report-*.json | head -1)
```

## ⚙️ Configuración Cron

### Agregar a crontab
```bash
crontab -e

# Agregar (cada hora en punto)
0 * * * * cd /home/thempra/projects/qzero && python3 autonomous-anomaly-detection.py >/dev/null 2>&1
```

### Verificar cron
```bash
crontab -l
```

## 📝 Notas de Desarrollo

**Versión 1**: Foco en detección de anomalías de seguridad
- Escanea actividad reciente de insights
- Busca alertas de seguridad críticas
- Evalúa rendimiento de modelos
- Verifica integridad de datos
- Envía alertas a Telegram

**Funcionalidades adicionales**:
- Limpieza automática de reportes antiguos
- Reportes estructurados en JSON
- Recomendaciones automáticas

## 🎯 Mejoras Futuras

- [ ] Análisis de patrones de anomalías temporales
- [ ] Integración con sistemas de detección de intrusiones reales
- [ ] Gráficos de tendencias de anomalías
- [ ] Thresholds personalizados por tipo de anomalía
- [ ] Integración con otras herramientas de monitoreo

## 🔧 Configuración de Telegram

Para habilitar alertas a Telegram, crear archivo `configs/telegram.json`:

```json
{
  "enabled": true,
  "token": "TU_TELEGRAM_BOT_TOKEN",
  "chat_id": "TU_CHAT_ID"
}
```

**Cómo obtener tu token y chat_id**:
1. Busca el bot @BotFather en Telegram
2. Usa `/newbot` para crear un bot nuevo
3. Copia el token que te da BotFather
4. Envía un mensaje al bot y usa `/start`
5. Envía `/my_id` al bot para obtener tu chat_id

---

*Última actualización: 2026-03-04*
*Versión: 1.0*