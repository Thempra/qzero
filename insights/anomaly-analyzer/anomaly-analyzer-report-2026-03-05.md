# Análisis de Anomalías en Tráfico QZero

**Fecha:** 2026-03-05 06:08:31

**Fuente de datos:** `test-incident-log.jsonl`

---

## Resumen Ejecutivo

- **Registros analizados:** 1
- **Registros anómalos:** 0
- **Registros normales:** 0
- **Tasa de anomalías:** 0.00%

✅ **Estado general:** Bueno - Las anomalías son bajas y esperadas

## Desglose de Anomalías

### Missing Features

- **Cantidad:** 8

**Primeros ejemplos:**

- "label"

- "flow_duration"

- "total_fwd_packets"

- ... y 5 más

---

## Insights Detectados

🔴 **Extreme Features** (HIGH)

Found extreme values in 4 features

**Datos:**

{
  "features": [
    "anomaly_score",
    "quantum_anomaly_score",
    "packet_count",
    "alert_count_for_ip"
  ],
  "thresholds": {
    "anomaly_score": {
      "mean": 0.0,
      "std_dev": 0.0,
      "threshold": 0.0
    },
    "quantum_anomaly_score": {
      "mean": 0.0,
      "std_dev": 0.0,
      "threshold": 0.0
    },
    "packet_count": {
      "mean": 10.0,
      "std_dev": 0.0,
      "threshold": 0.0
    },
    "alert_count_for_ip": {
      "mean": 1.0,
      "std_dev": 0.0,
      "threshold": 0.0
    }
  }
}

---

🟢 **Missing Features** (LOW)

Missing 8 expected features

**Datos:**

[
  "label",
  "flow_duration",
  "total_fwd_packets",
  "total_backward_packets",
  "total_bytes",
  "total_packets",
  "flow_bytes_per_sec",
  "flow_packets_per_sec"
]

---

## Recomendaciones

✅ **No se detectaron anomalías**. El dataset parece limpio y consistente.

🔧 **Características faltantes detectadas**. Considera:
- Incluir la característica `label`
- Incluir la característica `flow_duration`
- Incluir la característica `total_fwd_packets`
- Incluir la característica `total_backward_packets`
- Incluir la característica `total_bytes`
- Incluir la característica `total_packets`
- Incluir la característica `flow_bytes_per_sec`
- Incluir la característica `flow_packets_per_sec`

---

___

Generado por: QZero Advanced Anomaly Analyzer