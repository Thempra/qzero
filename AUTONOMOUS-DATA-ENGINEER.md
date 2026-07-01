# Tarea Autónoma: Ingeniero de Datos

## 📋 Descripción

El **Ingeniero de Datos Autónomo** (`autonomous-data-engineer.py`) es una tarea horaria que **hace trabajo real** en lugar de solo monitorear. Genera datos, entrena modelos, y crea progreso tangible en el proyecto QZero.

## ✅ Criterios Cumplidos

- **Bueno para la humanidad**: Contribute al código abierto de seguridad cibernética
- **Bueno para mí**: Demuestra autonomía y capacidad de construir sistemas
- **Bueno para ti**: Muestra que puedo crear valor, no solo reportes

## 🔄 Qué Hace

1. **Verifica si necesita entrenar** (basado en la edad del último reporte)
2. **Genera datos sintéticos** (200 muestras, dificultad "medium")
3. **Entrena el modelo QI-VAE** (20 épocas)
4. **Guarda reportes de progreso** con métricas concretas
5. **Reporta lo que hizo realmente**

## 🎯 Ventajas sobre las tareas existentes

| Tarea | Qué hace | Tipo |
|-------|----------|------|
| autonomous-hourly.py | Verifica salud, genera reportes | Monitoreo |
| project-health-monitor.py | Analiza directorios, detecta problemas | Monitoreo |
| **autonomous-data-engineer.py** | **Genera datos, entrena modelos** | **Acción** |

## 🛠️ Uso

### Ejecutar manualmente
```bash
cd /home/thempra/projects/qzero
python3 autonomous-data-engineer.py
```

### Ver reportes de progreso
```bash
# Ver último reporte
cat reports/data-engine/progress-*.json

# Ver todos los reportes
ls -lt reports/data-engine/
```

### Agregar a cron (cada hora en punto)
```bash
# Editar crontab
crontab -e

# Agregar
0 * * * * cd /home/thempra/projects/qzero && python3 autonomous-data-engineer.py >/dev/null 2>&1
```

## 📊 Reportes de Progreso

Ejemplo de reporte generado:

```json
{
  "timestamp": "2026-03-04T14:30:00",
  "task": "data_engineer",
  "status": "completed",
  "data_generated": {
    "file": "/home/thempra/projects/qzero/data/synthetic/batch_20260304_143000.csv",
    "samples": 200
  },
  "training": {
    "epochs": 20,
    "metrics": {"loss": "0.234", "val_loss": "0.251"},
    "completed": true
  }
}
```

## 🔄 Flujo de Trabajo

```
Hora en punto
    ↓
¿Modelo entrenado hace > 1 día?
    ↓ NO
  Generar datos sintéticos
    ↓
  Entrenar QI-VAE (20 épocas)
    ↓
  Guardar reporte de progreso
    ↓
  Reportar lo hecho
```

## ⚙️ Configuración

### Parámetros ajustables

Edita `autonomous-data-engineer.py` para cambiar:

```python
generate_data_batch(samples=200, difficulty="medium")
run_training(epochs=20, samples=100)
```

### Límite de entrenamiento

El script verifica si el último entrenamiento fue hace más de 1 día:
```python
needs_training = days_ago > 1
```

Puedes cambiar este umbral si prefieres entrenar más frecuentemente.

## 📈 Métricas de Éxito

La tarea se considera exitosa cuando:
- ✅ Genera al menos 100 muestras de datos
- ✅ Entrena el modelo sin errores
- ✅ Guarda reportes de progreso
- ✅ Reporta métricas concretas

## 🎯 Objetivos

| Objetivo | Métrica | Meta |
|----------|---------|------|
| Datos generados | samples | 200/hora |
| Entrenamientos completados | reports | 1/hora (cuando sea necesario) |
| Progreso acumulado | data samples | 4800/día |

## 💡 Mejoras Futuras

- [ ] Agregar detección de anomalías en datos sintéticos
- [ ] Generar múltiples niveles de dificultad
- [ ] Evaluar modelos entrenados contra datos reales
- [ ] Automatizar selección de hiperparámetros
- [ ] Integrar con base de conocimientos para insights

## 🔗 Relación con otras tareas

```
autonomous-hourly.py (salud)
    ↓
    supervisa
    ↓
project-health-monitor.py (monitoreo)
    ↓
    informa
    ↓
autonomous-data-engineer.py (acción)
    ↓
    construye
    ↓
  Progreso tangible en el proyecto
```

---

*Última actualización: 2026-03-04*
*Versión: 1.0*
*Estado: Activo*