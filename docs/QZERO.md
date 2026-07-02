# QZero - Documentación de Características

## 🎯 Visión General

QZero es un sistema de detección de anomalías y monitoreo de seguridad con capacidad de análisis en tiempo real, diseñado para detectar amenazas desde el primer momento mediante interfaces promiscuas de red.

## 🚀 Modo Promiscuo - Características Clave

### ¿Qué es el Modo Promiscuo?

El modo promiscuo permite capturar **todos** los paquetes de una interfaz de red, no solo los destinados a la máquina. Esto es fundamental para:

- 🔍 **Análisis de tráfico completo**
- ⚡ **Detección de amenazas en tiempo real**
- 🎯 **Monitoreo de comportamiento**
- 🛡️ **Investigación forense**

### Comandos de Uso

#### 1. Activar Modo Promiscuo
```bash
# Desde CLI
qzero interface --mode promiscuous --interface eth0 --activate

# Desde script
python3 -m qzero.cli interface --interface eth0 --activate
```

#### 2. Monitor en Tiempo Real
```bash
# Monitor promiscuo activo
qzero monitor --interface eth0 --promiscuous

# Con salida detallada
qzero monitor --interface eth0 --promiscuous --verbose
```

#### 3. Capturar Paquetes
```bash
# Capturar N paquetes
qzero monitor --interface eth0 --promiscuous --capture --count 100
```

## 📊 Interfaces Soportadas

### Interfaz de Red Física
```bash
qzero monitor --interface eth0 --promiscuous
```

### Interfaz de Contenedor
```bash
qzero monitor --interface docker0 --promiscuous
```

### Interfaz de Virtualización
```bash
qzero monitor --interface virbr0 --promiscuous
```

## 🔧 Requisitos de Sistema

### Requisitos Previos
```bash
# Python 3.10+
python3 --version

# Privilegios de root para modo promiscuo
sudo -v
```

### Instalación de Dependencias
```bash
# Python dependencies
pip install -e .

# Sistema
sudo apt install tcpdump
```

## 📁 Estructura de Datos

### Directorios de Captura
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

### Formato de Captura
```json
{
  "timestamp": "2026-02-26T12:00:00.000000",
  "src_mac": "AA:BB:CC:DD:EE:FF",
  "dst_mac": "11:22:33:44:55:66",
  "protocol": "ETH",
  "size": 1500
}
```

## 🛡️ Seguridad y Privilegios

### Alertas de Seguridad
- ⚠️ **Advertencia**: El modo promiscuo requiere privilegios de root
- 🔒 **Seguridad**: Capturas guardadas con permisos restrictivos
- 📝 **Logueo**: Todas las actividades se registran

### Precauciones
1. Solo usar en entornos controlados
2. Limitar el tiempo de monitoreo
3. Guardar capturas solo cuando sea necesario
4. Analizar con precaución

## 📈 Métricas de Detección

### Parámetros Clave
- **Tasa de Anomalía**: % de paquetes sospechosos
- **Calidad de Datos**: Puntuación de integridad (0-100)
- **Tendencia**: INCREASING/DECREASING/STABLE
- **Severidad**: LOW/MEDIUM/HIGH/CRITICAL

### Umbral de Detección
```bash
# Personalizar umbral
qzero detect --threshold 0.8
```

## 🔔 Alertas

### Configuración de Alertas
```python
# Detectar solo anomalías críticas
if result['severity'] == 'CRITICAL':
    send_alert("⚠️ AMENAZA CRÍTICA DETECTADA")
```

### Integración con Telegram
```python
from qzero.core.detector import AnomalyDetector

detector = AnomalyDetector()
result = detector.detect()

if result['anomaly_detected']:
    send_to_telegram(result)
```

## 🔄 Cron Jobs

### Ejecución Automática
```bash
# Editar crontab
crontab -e

# Agregar:
0 * * * * /home/thempra/clawd/cron/qzero-promiscuous-monitor.sh
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

## 🐛 Troubleshooting

### Problema: "No se pudo activar PROMISC"
**Solución**: 
```bash
# Verificar permisos
sudo -v

# Instalar tcpdump si es necesario
sudo apt install tcpdump
```

### Problema: "tcpdump no instalado"
**Solución**:
```bash
sudo apt update
sudo apt install tcpdump
```

### Problema: "Interfaz no encontrada"
**Solución**:
```bash
# Listar interfaces
ip link show

# Usar interfaz correcta
qzero monitor --interface <nombre>
```

## 📚 Recursos Adicionales

### Documentación
- [README.md](README.md) - Instalación básica
- [src/core/detector.py](src/core/detector.py) - Detalles del detector
- [src/interface/promiscuous.py](src/interface/promiscuous.py) - Interfaz promiscua

### Guías
- [Análisis de Trafico](data/raw) - Ejemplos de capturas
- [Reportes](reports) - Ejemplos de reportes
- [Insights](insights) - Análisis detallados

---

*Última actualización: 2026-02-26*
*Versión: 1.0.0*
