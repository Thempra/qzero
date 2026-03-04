# Tarea Autónoma Horaria - Resumen

## 📅 Fecha
2026-03-04 — 14:21 (Europe/Madrid)

## ✅ Tarea Creada: Autonomous Data Engineer

### Qué es
Un **ingeniero de datos autónomo** que hace trabajo real en el proyecto QZero: genera datos, entrena modelos, y crea progreso tangible.

### Por qué cumple los criterios

| Criterio | Cómo lo cumple |
|----------|----------------|
| **Bueno para la humanidad** | Contribute al código abierto de seguridad cibernética mediante generación de datos y entrenamiento de modelos |
| **Bueno para mí** | Demuestra capacidad de autonomía, construcción de sistemas y creación de valor |
| **Bueno para ti** | Muestra que puedo hacer progreso, no solo reportar |

### Qué hace exactamente

1. **Verifica si necesita entrenar** (basado en si el último entrenamiento fue hace > 1 día)
2. **Genera datos sintéticos** (200 muestras de red, dificultad "medium")
3. **Entrena el modelo QI-VAE** (20 épocas)
4. **Guarda reportes de progreso** con métricas concretas
5. **Reporta lo que hizo realmente**

### Archivos creados

| Archivo | Propósito |
|---------|-----------|
| `autonomous-data-engineer.py` | Script principal de la tarea |
| `AUTONOMOUS-DATA-ENGINEER.md` | Documentación completa |

### Configuración

**Cron job agregado:**
```
0 * * * * cd /home/thempra/projects/qzero && python3 autonomous-data-engineer.py >/dev/null 2>&1
```

Ejecutándose cada hora en punto.

### Relación con tareas existentes

```
┌─────────────────────┐
│  autonomous-        │
│  hourly.py          │  (monitoreo)
│  - Verifica salud   │
│  - Genera reportes  │
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│  project-health-    │  (monitoreo)
│  monitor.py         │
│  - Analiza dirs     │
│  - Detecta issues   │
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│  autonomous-data-   │  (acción)
│  engineer.py        │
│  ✨ GENERA DATOS ✨  │
│  ✨ ENTRENA MODELOS │
└─────────────────────┘
           ↓
  Progreso tangible en el proyecto
```

### Ventajas

1. **Diferencia fundamental**: Mientras otras tareas solo monitorean, esta hace trabajo real
2. **Progreso acumulativo**: Cada ejecución crea valor (datos + modelo)
3. **Independencia**: No depende de que yo lo verifique
4. **Concreto**: Los reportes muestran métricas numéricas, no solo estado

### Próxima ejecución

La tarea se ejecutará automáticamente:
- **Hora**: Cada hora en punto (XX:00)
- **Próxima**: 15:00 (dentro de ~39 minutos)
- **Dónde**: `/home/thempra/projects/qzero/`

### Para probar

```bash
cd /home/thempra/projects/qzero
python3 autonomous-data-engineer.py --verbose
```

Ver reportes en: `reports/data-engine/progress-*.json`

---

*Tarea creada por Radomo*
*Para Thempra*
*Con propósito: hacer progreso, no solo reportar*