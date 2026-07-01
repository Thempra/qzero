# QZero Real-Time Quantum Analyzer

> Analizador de tráfico de red en tiempo real usando modelos cuánticos del proyecto QZero

## 📋 Descripción

El analizador en tiempo real de QZero captura tráfico de red desde una interfaz de red y utiliza **modelos cuánticos cuantos** (QSVM y QIVAE) para detectar anomalías de forma cuántica. Distingue comportamiento anómalo que los métodos clásicos no pueden captar.

## ⚡ Características Cuánticas

- **⚡ Modelo QSVM**: Kernel cuántico para proyección de anomalías desconocidas
- **⚡ Modelo QIVAE**: Variational Autoencoder cuántico para reconstrucción de tráfico normal
- **⚡ Detección de 0-days**: Identifica comportamiento no lineal anómalo
- **⚡ Reducción de falsos positivos**: Probabilística, no basada en firmas

## 🚀 Instalación

### Requisitos

```bash
# Instalar scapy
pip install scapy

# Asegurarse de tener el proyecto QZero completo
cd /home/thempra/projects/qzero
```

### Ejecutar con modelos cuánticos

```bash
# Iniciar el analizador
python3 scripts/real-time-analyzer.py

# O usando el wrapper (requiere sudo para captura de paquetes)
sudo scripts/real-time-analyzer-cron.sh start
```

## 📊 Modo de Análisis

El analizador usa dos modelos cuánticos en paralelo:

### 1. QSVM (Quantum Support Vector Machine)
- **Propósito**: Detecta fronteras de decisión cuánticas
- **Ventaja**: Distingue comportamientos no lineales complejos
- **Score cuántico**: Puntuación basada en proyección al espacio cuántico

### 2. QIVAE (Quantum Variational Autoencoder)
- **Propósito**: Aprende la distribución normal del tráfico y detecta reconstrucción anómala
- **Ventaja**: Identifica tráfico "nuevo" no representado en el entrenamiento
- **Reconstruction Loss**: Pérdida de reconstrucción anómala indica nuevo comportamiento

### Combina los dos para:
- **Score cuántico combinado**: Media ponderada de QSVM + QIVAE
- **Mayor precisión**: Reducción de falsos positivos
- **Detección de 0-days**: Comportamientos no lineales complejos

## ⚙️ Configuración

```python
CONFIG = {
    'interface': 'ens18',  # Interfaz de red a monitorear
    'api_url': 'http://localhost:8000',  # URL de QZero API
    'analyze_interval': 5,  # Segundos entre análisis
    'flow_window': 30,  # Ventana de flujos (segundos)
    'threshold_critical': 0.85,  # Umbral CRITICAL (QSVM + QIVAE)
    'threshold_warning': 0.65,  # Umbral WARNING
    'max_flows_per_batch': 100,  # Flujos por batch
    'max_packet_size': 1500,  # Tamaño max paquete
    'alert_mode': True,  # Generar alertas cuánticas
    'save_incidents': True,  # Guardar incidents
}
```

## 🎯 Alertas Cuánticas

El analizador genera alertas con las siguientes severidades:

### 🔴 CRITICAL (> 0.85)
- **Anomalía cuántica de alto riesgo**
- Posible explotación 0-day
- Exfiltración con comportamiento no lineal
- **Acción**: Investigación inmediata con análisis cuántico profundo

### 🟡 WARNING (> 0.65)
- **Anomalía cuántica moderada**
- Comportamiento sospechoso no lineal
- **Acción**: Monitorear con atención

### 🟢 INFO (≤ 0.65)
- **Comportamiento anómalo leve**
- Puede ser tráfico legítimo con noise cuántico
- **Acción**: Registrar y monitorear

## 📝 Formato de Incidentes Cuánticos

```json
{
  "timestamp": "2026-02-07T01:37:57.123456",
  "severity": "CRITICAL",
  "src_ip": "192.168.1.100",
  "dst_ip": "10.0.0.50",
  "protocol": 6,
  "flow_key": ("192.168.1.100", "10.0.0.50", 6),
  "anomaly_score": 0.9234,
  "quantum_anomaly_score": 0.9234,
  "reconstruction_loss": 0.8500,
  "qsvm_score": 0.9968,
  "packet_count": 15,
  "alert_count_for_ip": 3,
  "message": "CRITICAL Anomaly detected from 192.168.1.100 with quantum score 0.9234",
  "model_used": "quantum_svm_ivae"
}
```

## 🔬 Análisis de Datos Cuánticos

### Contar por severidad cuántica:
```bash
jq 'group_by(.severity) | map({severity: .[0].severity, count: length})' \
  insights/real-time-incident-log.jsonl
```

### Top IPs con anomalías cuánticas:
```bash
jq -s 'group_by(.src_ip) | map({ip: .[0].src_ip, count: length}) | sort_by(-.count) | .[:10]' \
  insights/real-time-incident-log.jsonl
```

### Anomalías críticas con reconstrucción loss:
```bash
jq 'select(.severity == "CRITICAL") | {src_ip: .src_ip, reconstruction_loss: .reconstruction_loss, qsvm_score: .qsvm_score}' \
  insights/real-time-incident-log.jsonl | tail -n 20
```

## 🧪 Prueba con Modelos Cuánticos

```bash
# Script de prueba (requiere modelos cuánticos entrenados)
python3 scripts/test-quantum-analyzer.py
```

## 🔄 Ejecución Periódica

```bash
# Ejecutar cada 6 horas
0 */6 * * * /home/thempra/projects/qzero/scripts/real-time-analyzer-cron.sh restart
```

## ⚠️ Requisitos de Privilegios

**IMPORTANTE**: Captura de paquetes requiere privilegios de root:

```bash
sudo /home/thempra/projects/qzero/scripts/real-time-analyzer-cron.sh start
```

## 🐛 Troubleshooting

### "Modelos cuánticos no disponibles"
- Revisa si los modelos están entrenados en `/home/thempra/projects/qzero/models/`
- Ejecuta `python3 train_models.py` para entrenar modelos cuánticos

### "Operation not permitted" al capturar paquetes
- Necesitas ejecutar con `sudo`
- O usa captura de PCAP como alternativa

### Sin alertas cuánticas
- Aumenta el tráfico de prueba
- Ajusta los umbrales en la configuración
- Verifica que los modelos cuánticos estén cargados

## 📈 Ventajas del Análisis Cuántico

| Característica | Clásico | Cuántico (QZero) |
|----------------|---------|------------------|
| Detección 0-days | Baja | ✅ Alta |
| Falsos positivos | Alta | ✅ Baja |
| Comportamiento no lineal | ❌ No detecta | ✅ Diferencia |
| Exfiltración cifrada | ❌ Difícil detectar | ✅ Diferencia |
| Latencia | Baja | ✅ Aceptable |

## 📚 Referencias

- **QZero**: Quantum-Enhanced Threat Detection Platform
- **QSVM**: Quantum Support Vector Machine
- **QIVAE**: Quantum Variational Autoencoder
- **Scapy**: Packet Manipulation Library

## 🔗 Integración

El analizador se integra completamente con:
- API de QZero para análisis cuántico
- Dashboard de QZero para visualización
- Sistema de alertas cuántico
- Logs de anomalías cuánticas

---

**Versión**: 1.0.0 (Cuántico)
**Última actualización**: 2026-02-07
**Modelos**: QSVM + QIVAE
**Estado**: ✅ Integrado en el proyecto QZero