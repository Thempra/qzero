# QZero - Sistema de Detección de Anomalías de Red

> Análisis de tráfico de red en tiempo real con detección de amenazas mediante promiscuity mode.

## 🎯 ¿Qué es QZero?

QZero es un sistema de seguridad de red que captura y analiza tráfico de red para detectar anomalías y comportamientos sospechosos. Utiliza interfaces promiscuas para ver **todos** los paquetes de una interfaz, no solo los destinados a la máquina.

## 🚀 Características Principales

- **Modo Promiscuo**: Captura todo el tráfico de red
- **Detección Anónima**: Identifica patrones sospechosos automáticamente
- **Análisis en Tiempo Real**: Monitoreo continuo del tráfico
- **Reportes Detallados**: Historial de anomalías con severidad
- **Alertas Integradas**: Notificaciones cuando se detectan amenazas

## 📦 Requisitos

```bash
# Python 3.10+
python3 --version

# Privilegios de root para modo promiscuo
sudo -v
```

## 🛠️ Instalación

```bash
# Clonar el repositorio
git clone <repo-url>
cd qzero

# Instalar dependencias
pip install -e .

# Instalar dependencias del sistema (opcional)
sudo apt install tcpdump
```

## 💻 Uso Básico

### 1. Activar Modo Promiscuo

```bash
# Desde CLI
qzero interface --mode promiscuous --interface eth0 --activate

# O usar directamente Python
python3 -m qzero.cli interface --interface eth0 --activate
```

### 2. Monitorear Tráfico

```bash
# Monitoreo básico
qzero monitor --interface eth0 --promiscuous

# Con salida detallada
qzero monitor --interface eth0 --promiscuous --verbose
```

### 3. Capturar Paquetes

```bash
# Capturar 100 paquetes
qzero monitor --interface eth0 --promiscuous --capture --count 100
```

## 📊 Interfaz Soportadas

| Tipo | Ejemplo |
|------|---------|
| Interfaz física | `eth0` |
| Contenedor | `docker0` |
| Virtualización | `virbr0` |

## 🗂️ Estructura de Datos

```
qzero/
├── logs/
│   └── capture_*.jsonl       # Capturas de paquetes
├── reports/
│   └── monitor-*.json        # Reportes de monitoreo
├── insights/
│   └── anomaly-patterns/     # Análisis de anomalías
└── data/
    └── raw/                  # Datos crudos
```

## 🔧 Análisis de Anomalías

### Umbral de Detección

```bash
# Personalizar umbral
qzero detect --threshold 0.8
```

### Niveles de Severidad

| Nivel | Cantidad de Anomalías |
|-------|----------------------|
| Sistema Estable | 0 |
| Actividad Leve | 1-5 |
| Actividad Moderada | 6-10 |
| Actividad Significativa | >10 |

## 🔔 Alertas

### Configuración de Alertas

```python
from qzero.core.detector import AnomalyDetector

detector = AnomalyDetector()
result = detector.detect()

if result['anomaly_detected']:
    send_alert(f"⚠️ {result['severity']}: {result['message']}")
```

### Integración con Telegram

```bash
# Agregar a crontab
0 * * * * /home/thempra/clawd/cron/qzero-promiscuous-monitor.sh
```

## 📈 Métricas de Detección

- **Tasa de Anomalía**: % de paquetes sospechosos
- **Calidad de Datos**: Puntuación de integridad (0-100)
- **Tendencia**: INCREASING/DECREASING/STABLE
- **Severidad**: LOW/MEDIUM/HIGH/CRITICAL

## 🐛 Troubleshooting

### Problema: "No se pudo activar PROMISC"

```bash
# Verificar permisos
sudo -v

# Instalar tcpdump
sudo apt install tcpdump
```

### Problema: "tcpdump no instalado"

```bash
sudo apt update
sudo apt install tcpdump
```

### Problema: "Interfaz no encontrada"

```bash
# Listar interfaces
ip link show

# Usar interfaz correcta
qzero monitor --interface <nombre>
```

## 📝 Ejemplos de Uso

### Ejemplo 1: Monitoreo Básico

```bash
qzero monitor --interface eth0 --promiscuous
```

### Ejemplo 2: Análisis de PCAP

```bash
qzero pcap --file /path/to/capture.pcap
```

### Ejemplo 3: Detección Personalizada

```bash
qzero detect --mode real-time --threshold 0.8
```

## ⚠️ Seguridad y Privilegios

> **IMPORTANTE**: El modo promiscuo requiere privilegios de root

- Solo usar en entornos controlados
- Limitar el tiempo de monitoreo
- Guardar capturas solo cuando sea necesario
- Analizar con precaución

## 📚 Recursos Adicionales

| Archivo | Descripción |
|---------|-------------|
| `QZERO.md` | Documentación detallada |
| `src/core/detector.py` | Motor de detección |
| `src/interface/promiscuous.py` | Interfaz promiscua |
| `ARCHITECTURE.md` | Arquitectura del sistema |

## 🗺️ Roadmap

- [x] Captura de tráfico en tiempo real
- [x] Detección de anomalías
- [x] Reportes automáticos
- [ ] Integración con bases de datos
- [ ] Exportación a PCAP
- [ ] Análisis de IA
- [ ] Sistema de alertas avanzado

## 🤝 Contribución

Las contribuciones son bienvenidas. Por favor:

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/nombre`)
3. Commit tus cambios (`git commit -m 'feat: nombre de feature'`)
4. Push a la rama (`git push origin feature/nombre`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver LICENSE para más detalles.

---

## 📞 Soporte

Si tienes problemas o preguntas, por favor abre un issue en el repositorio.

*Última actualización: 2026-03-04*
*Versión: 1.0.0*