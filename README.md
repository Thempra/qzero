# QZero - Sistema de Detección de Anomalías y Monitoreo de Seguridad

QZero es un sistema completo de detección de anomalías y monitoreo de seguridad con capacidad de análisis en tiempo real, usando interfaces promiscuas de red para detectar amenazas desde el primer momento.

## 🎯 Características

### ✅ Core Features
- **Análisis de Anomalías**: Detección de patrones inusuales en datos
- **Modo Promiscuo**: Captura de tráfico de red sin filtro
- **Análisis en Tiempo Real**: Monitoreo continuo de actividad
- **Detección de Amenazas**: Identificación de patrones de seguridad
- **Reportes Detallados**: Insights completos con métricas

### 📊 Análisis en Tiempo Real
- Monitor de red con interfaz promiscua
- Captura de paquetes y análisis de tráfico
- Detección de anomalías en vivo
- Alertas en tiempo real

### 🔧 Interfaces Soportadas
- Interfaz de contenedor
- Interfaz de red física
- Interfaz de virtualización

## 🚀 Instalación

```bash
# Instalar en modo desarrollo
pip install -e .

# Requisitos de red para modo promiscuo
sudo apt install tcpdump
```

## 📖 Uso

### CLI Principal
```bash
# Iniciar monitor en tiempo real
qzero monitor --interface eth0 --promiscuous

# Analizar pcap
qzero pcap --file capture.pcap

# Ejecutar detección
qzero detect --mode real-time
```

### Modo Promiscuo
```bash
# Activar modo promiscuo en interfaz
qzero interface --mode promiscuous --interface eth0

# Monitor promiscuo activo
qzero monitor --promiscuous --interface eth0
```

## 📁 Estructura

```
qzero/
├── src/
│   ├── cli/           # Interfaz de línea de comandos
│   ├── core/          # Núcleo del sistema
│   ├── interface/     # Interfaces de red
│   ├── analysis/      # Módulos de análisis
│   └── storage/       # Almacenamiento de datos
├── data/              # Datos y PCAPs
├── insights/          # Reportes y análisis
├── cron/              # Scripts de cron
└── reports/           # Reportes generados
```

## 🛡️ Seguridad

- Modo promiscuo requiere privilegios elevados
- Capturas de red se guardan en `data/raw/`
- Análisis de PCAPs con Scapy
- Integración con sistema de alertas

## 📈 Métricas

- Ratio de anomalías: X%
- Calidad de datos: Y/100
- Tendencia: UP/DOWN/STABLE
- Alertas activas: N

## 📝 Licencia

MIT License - See LICENSE for details

## 🤝 Contribuir

Contribuciones son bienvenidas. Por favor, abre un issue o PR.
