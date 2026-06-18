# Análisis de Anomalías en Tráfico QZero

**Fecha:** 2026-02-04 14:16:29

**Fuente de datos:** `augmented-20260202-150501.json`

---

## Resumen Ejecutivo

- **Registros analizados:** 50
- **Registros anómalos:** 2
- **Registros normales:** 34
- **Tasa de anomalías:** 0.00%

---

## Insights

🟡 **High Anomaly Count** (MEDIUM)

Detected 2 anomalous records

**Datos:**

2

🔴 **Extreme Features** (HIGH)

Found extreme values in 5 features

**Datos:**

{
  "features": [
    "flow_duration",
    "total_fwd_packets",
    "total_backward_packets",
    "flow_bytes_per_sec",
    "flow_packets_per_sec"
  ],
  "thresholds": {
    "flow_duration": {
      "mean": 5124.18,
      "std_dev": 2846.91,
      "threshold": 8540.74
    },
    "total_fwd_packets": {
      "mean": 723.47,
      "std_dev": 856.49,
      "threshold": 2569.46
    },
    "total_backward_packets": {
      "mean": 468.22,
      "std_dev": 285.82,
      "threshold": 857.46
    },
    "flow_bytes_per_sec": {
      "mean": 41816.28,
      "std_dev": 26973.7,
      "threshold": 80921.1
    },
    "flow_packets_per_sec": {
      "mean": 444.64,
      "std_dev": 299.76,
      "threshold": 899.29
    }
  }
}

🟢 **Missing Features** (LOW)

Missing 2 expected features

**Datos:**

[
  "total_bytes",
  "total_packets"
]

---

Generado por: QZero Anomaly Impact Analyzer
