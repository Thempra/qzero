# 🏗️ Arquitectura de QZero v2.0

> **Proyecto unificado y paquetizado**

## 📋 Tabla de Contenidos

1. [Visión General](#visión-general)
2. [Estructura de Archivos](#estructura-de-archivos)
3. [Componentes Principales](#componentes-principales)
4. [Flujo de Trabajo](#flujo-de-trabajo)
5. [Modo de Análisis](#modo-de-análisis)
6. [Configuración](#configuración)
7. [Uso](#uso)

---

## 🎯 Visión General

QZero v2.0 es un sistema **unificado y paquetizado** para detección de anomalías cuánticas en tráfico de red. Está diseñado para ser:

- **Modular**: Componentes independientes que se pueden reutilizar
- **Documentado**: Cada módulo tiene su documentación clara
- **Prueba**: Tests y ejemplos incluidos
- **Producción**: Arquitectura diseñada para despliegue real

---

## 📁 Estructura de Archivos

```
qzero/
├── qzero.py                          # CLI principal
├── README.md                         # Documentación principal
├── ARCHITECTURE.md                   # Esta documentación
├── requirements.txt                  # Dependencias
├── setup.py                          # Paquete Python
│
├── src/                              # Código fuente
│   ├── __init__.py                   # Paquete principal
│   ├── predictor.py                  # Predictor cuántico central
│   ├── detection.py                  # Análisis de tráfico de red
│   ├── api.py                        # API REST
│   └── realtime_monitor.py           # Monitor en tiempo real
│
├── scripts/                          # Scripts auxiliares
│   ├── generate-synthetic-pcaps-v2.py  # Generador de PCAPs
│   ├── test-qzero-pcaps.py            # Suite de pruebas
│   └── [otros scripts]
│
├── data/                             # Datos de entrenamiento
│   ├── synthetic-pcaps/              # PCAPs sintéticos
│   └── [otros datos]
│
├── models/                           # Modelos entrenados
│   ├── qsvm.pkl
│   ├── qivae.pkl
│   └── [otros modelos]
│
├── reports/                          # Reportes generados
├── logs/                             # Logs del sistema
└── insights/                         # Insights y alertas
```

---

## ⚙️ Componentes Principales

### 1. `qzero.py` - CLI Principal

Interfaz unificada para todos los comandos de QZero.

**Comandos:**

```bash
qzero.py train          # Entrenar modelos
qzero.py analyze        # Analizar tráfico
qzero.py server         # Iniciar API REST
qzero.py monitor        # Monitorear en tiempo real
```

### 2. `predictor.py` - Predictor Cuántico

Clase central para entrenar y hacer predicciones con modelos cuánticos.

**Clases:**

- `QZeroPredictor`: Predictor principal con QSVM y QI-VAE

**Métodos:**

```python
from qzero import QZero

qzero = QZero(n_qubits=4)
qzero.train(n_samples=5000)
predictions = qzero.predict(features)
```

### 3. `detection.py` - Análisis de Tráfico

Analiza archivos PCAP y extrae features para detección.

**Clases:**

- `NetworkTrafficAnalyzer`: Analizador de PCAPs

**Métodos:**

```python
from qzero import NetworkTrafficAnalyzer

analyzer = NetworkTrafficAnalyzer(n_qubits=4)
result = analyzer.analyze('traffic.pcap', method='best')
```

### 4. `api.py` - API REST

Servicio FastAPI para integración con otros sistemas.

**Endpoints:**

- `POST /analyze` - Analizar PCAP
- `GET /health` - Health check
- `GET /models` - Modelos entrenados
- `GET /stats` - Estadísticas

### 5. `realtime_monitor.py` - Monitor en Tiempo Real

Captura tráfico de red y analiza en tiempo real.

**Clases:**

- `RealtimeMonitor`: Monitor de tráfico con modo promiscuo

**Métodos:**

```python
from qzero import RealtimeMonitor

monitor = RealtimeMonitor(
    interface='eth0',
    promiscuous=True
)
monitor.start()
```

---

## 🔄 Flujo de Trabajo

### Flujo de Entrenamiento

```
1. Datos (PCAPs o CSV)
   ↓
2. Preprocesamiento (Feature Engineering)
   ↓
3. Modelado Cuántico (QSVM + QI-VAE)
   ↓
4. Evaluación (Métricas)
   ↓
5. Guardado de Modelos
```

### Flujo de Análisis

```
1. Archivo PCAP
   ↓
2. Captura y Extracción de Features
   ↓
3. Predicción Cuántica
   ↓
4. Análisis de Anomalías
   ↓
5. Generación de Alertas
```

### Flujo de Análisis en Tiempo Real

```
1. Captura de Tráfico (Promiscuo)
   ↓
2. Extracción de Features en Tiempo Real
   ↓
3. Análisis Cuántico Periodico
   ↓
4. Generación de Alertas
   ↓
5. Guardado de Logs
```

---

## 🎮 Modo de Análisis

### 1. Análisis por Archivo

**Uso:**

```bash
# Analizar un PCAP
python qzero.py analyze --file traffic.pcap --method best

# Analizar múltiples PCAPs
python qzero-cli-batch.py -f *.pcap
```

**Ventajas:**
- Simple y directo
- Ideal para pruebas
- No requiere configuración de red

### 2. Análisis en Tiempo Real (Promiscuo)

**Uso:**

```bash
# Monitor con modo promiscuo
python qzero.py monitor --interface eth0 --promiscuous

# Monitor sin promiscuo
python qzero.py monitor --interface eth0 --no-promiscuous
```

**Ventajas:**
- Detección inmediata
- Captura todo el tráfico
- Ideal para producción

**Modo Promiscuo:**
- Captura paquetes no destinados a la máquina
- Requiere privilegios de root
- Útil para sniffing de red

### 3. API REST

**Uso:**

```bash
# Iniciar servidor
python qzero.py server --host 0.0.0.0 --port 8000

# Usar API
curl -X POST http://localhost:8000/analyze -F "file=@traffic.pcap"
```

**Ventajas:**
- Integración con otros sistemas
- Arquitectura microservicio
- Escalable

---

## ⚙️ Configuración

### Configuración de Modelos

```python
from qzero import QZeroPredictor

# Configurar predictor
predictor = QZeroPredictor(
    n_qubits=4,                    # Número de qubits
    use_qsvm=True,                 # Usar QSVM
    use_qivae=True,                # Usar QI-VAE
    use_classical=True,            # Usar modelos clásicos
    random_state=42                # Semilla aleatoria
)
```

### Configuración del Monitor

```python
from qzero import RealtimeMonitor

# Configurar monitor
monitor = RealtimeMonitor(
    interface='eth0',               # Interfaz de red
    promiscuous=True,               # Modo promiscuo
    analyze_interval=10,            # Segundos entre análisis
    threshold_warning=0.65,         # Umbral WARNING
    threshold_critical=0.85         # Umbral CRITICAL
)
```

### Configuración de API

```python
from qzero import create_app

# Crear app con predictor
app = create_app()

# Configurar host y puerto
uvicorn.run(app, host='0.0.0.0', port=8000)
```

---

## 🚀 Uso

### Instalación

```bash
# Clonar repositorio
git clone https://github.com/thempra/qzero.git
cd qzero

# Instalar dependencias
pip install -r requirements.txt

# Hacer el script ejecutable
chmod +x qzero.py
```

### Entrenar Modelos

```bash
# Entrenar con datos sintéticos
python qzero.py train --samples 5000 --qubits 4

# Entrenar con datos reales
python qzero.py train --samples 5000 --real-data --qubits 4
```

### Analizar Tráfico

```bash
# Analizar PCAP
python qzero.py analyze --file data/synthetic-pcaps/normal_traffic_*.pcap

# Usar CLI batch
python qzero-cli-batch.py -f data/synthetic-pcaps/*.pcap
```

### Iniciar API REST

```bash
# Iniciar servidor
python qzero.py server --host 0.0.0.0 --port 8000

# O usar el script de API
python -m qzero.src.api
```

### Monitorear en Tiempo Real

```bash
# Con modo promiscuo
python qzero.py monitor --interface eth0 --promiscuous

# Con intervalo personalizado
python qzero.py monitor --interface eth0 --interval 5

# Sin modo promiscuo
python qzero.py monitor --interface eth0 --no-promiscuous
```

---

## 📊 Datos de Ejemplo

### PCAPs Sintéticos

QZero incluye scripts para generar PCAPs sintéticos con diferentes tipos de tráfico:

```bash
# Generar todos los tipos
python scripts/generate-synthetic-pcaps-v2.py --all --duration 30 --rate 20

# Generar solo tráfico normal
python scripts/generate-synthetic-pcaps-v2.py --type normal --duration 60

# Generar tráfico DDoS
python scripts/generate-synthetic-pcaps-v2.py --type ddos --rate 100
```

**Tipos de tráfico:**

- `normal`: Tráfico normal (HTTP, SSH, DNS, ICMP)
- `ddos`: DDoS attack (SYN flood, UDP flood)
- `bruteforce`: Brute force attack (SSH, Telnet)
- `exfiltration`: Data exfiltration (C2, data transfer)
- `malware`: Malware activity (crypto mining, spider scan)

---

## 🎯 Casos de Uso

### Caso 1: Detección de Anomalías

```python
from qzero import QZero

# Inicializar
qzero = QZero(n_qubits=4)

# Entrenar
qzero.train(n_samples=5000)

# Analizar tráfico
result = qzero.analyze_traffic('suspicious.pcap', method='best')

# Ver resultados
print(f"Anomalías detectadas: {result['n_anomalies_detected']}")
```

### Caso 2: API para SIEM

```bash
# Iniciar API
python qzero.py server

# Integrar con Splunk
curl -X POST http://localhost:8000/analyze -F "file=@alerts.pcap" | jq
```

### Caso 3: Monitor en Producción

```bash
# Iniciar monitor
sudo python qzero.py monitor --interface eth0 --promiscuous
```

---

## 🔧 Dependencias

### Python 3.7+

### Paquetes Requeridos

```txt
numpy
pandas
scapy
fastapi
uvicorn
scikit-learn
```

### Instalación

```bash
pip install -r requirements.txt
```

---

## 📝 Licencia

MIT License - Ver LICENSE para más detalles.

---

**Version:** 2.0.0
**Autor:** QZero Development Team
**Última actualización:** 2026-02-26