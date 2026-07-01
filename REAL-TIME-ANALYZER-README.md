## 🔬 Real-Time Quantum Analyzer

> Analizador de tráfico en tiempo real con modelos cuánticos QSVM + QIVAE

### 📋 Descripción

El analizador en tiempo real de QZero captura tráfico de red y utiliza modelos cuánticos para detectar anomalías de forma probabilística, reduciendo falsos positivos y detectando comportamientos no lineales que los métodos clásicos no pueden captar.

### ⚡ Características

- **⚛️ Modelo QSVM**: Kernel cuántico para proyección de anomalías
- **⚛️ Modelo QIVAE**: Variational Autoencoder cuántico para reconstrucción
- **⚛️ Detección de 0-days**: Comportamientos no lineales complejos
- **⚛️ Análisis cuántico en tiempo real**: Score combinado QSVM + QIVAE

### 🚀 Instalación

```bash
# Asegurarse de tener los modelos cuánticos entrenados
python3 train_models.py

# Instalar dependencias
pip install scapy

# Ejecutar el analizador
python3 scripts/real-time-analyzer.py
```

### 📊 Modo de Análisis Cuántico

El analizador combina dos modelos cuánticos:

1. **QSVM (Quantum Support Vector Machine)**
   - Detecta fronteras de decisión cuánticas
   - Score cuántico: Puntuación basada en proyección

2. **QIVAE (Quantum Variational Autoencoder)**
   - Aprende distribución normal del tráfico
   - Reconstruction Loss: Pérdida anómala indica nuevo comportamiento

**Score Cuántico Combinado**: Promedio ponderado de QSVM + QIVAE

### 🎯 Alertas

- 🔴 **CRITICAL** (>0.85): Investigación inmediata
- 🟡 **WARNING** (>0.65): Monitorear con atención
- 🟢 **INFO** (≤0.65): Registrar y monitorear

### 📝 Ejemplo de Alerta Cuántica

```json
{
  "timestamp": "2026-02-07T01:37:57.123456",
  "severity": "CRITICAL",
  "src_ip": "192.168.1.100",
  "dst_ip": "10.0.0.50",
  "anomaly_score": 0.9234,
  "reconstruction_loss": 0.8500,
  "qsvm_score": 0.9968,
  "model_used": "quantum_svm_ivae"
}
```

### 🔍 Análisis de Datos

```bash
# Ver incidents en tiempo real
tail -f insights/real-time-incident-log.jsonl

# Contar alertas por severidad
jq 'group_by(.severity) | map({severity: .[0].severity, count: length})' \
  insights/real-time-incident-log.jsonl

# Top IPs con anomalías cuánticas
jq -s 'group_by(.src_ip) | map({ip: .[0].src_ip, count: length}) | sort_by(-.count) | .[:10]' \
  insights/real-time-incident-log.jsonl
```

### 📚 Documentación Completa

Ver [REAL-TIME-ANALYZER.md](docs/REAL-TIME-ANALYZER.md) para detalles completos.