# Análisis de Anomalías en Tráfico QZero

**Fecha:** 2026-02-05 06:27:32

**Fuente de datos:** `data_20260202-160501.json`

---

## Resumen Ejecutivo

- **Registros analizados:** 50
- **Registros anómalos:** 0
- **Registros normales:** 33
- **Tasa de anomalías:** 0.00%

## Desglose de Anomalías

### Missing Features

- **Detalles:** ['total_bytes', 'total_packets']

---

## Insights

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
      "mean": 4581.47,
      "std_dev": 2922.27,
      "threshold": 8766.82
    },
    "total_fwd_packets": {
      "mean": 403.45,
      "std_dev": 242.71,
      "threshold": 728.14
    },
    "total_backward_packets": {
      "mean": 512.23,
      "std_dev": 244.15,
      "threshold": 732.44
    },
    "flow_bytes_per_sec": {
      "mean": 48423.3,
      "std_dev": 32534.88,
      "threshold": 97604.65
    },
    "flow_packets_per_sec": {
      "mean": 446.25,
      "std_dev": 294.68,
      "threshold": 884.05
    }
  }
}

---

🟢 **Missing Features** (LOW)

Missing 2 expected features

**Datos:**

[
  "total_bytes",
  "total_packets"
]

---

## Recomendaciones

✅ **No se detectaron anomalías**. El dataset parece limpio y consistente.

🔧 **Características faltantes detectadas**. Considera:
- Incluir la característica `total_bytes`
- Incluir la característica `total_packets`

---

___

Generado por: QZero Advanced Anomaly Analyzer
