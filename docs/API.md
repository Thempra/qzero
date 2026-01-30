# QZero API Reference

> REST API documentation for the Quantum Zero-Day Detection Platform

## Table of Contents

- [Overview](#overview)
- [Base URL](#base-url)
- [Authentication](#authentication)
- [Endpoints](#endpoints)
- [Data Models](#data-models)
- [Error Handling](#error-handling)
- [Examples](#examples)
- [Python SDK](#python-sdk)

---

## Overview

QZero exposes a RESTful API built with **FastAPI** for analyzing network traffic and detecting zero-day threats. The API accepts CSV files containing network flow data and returns anomaly scores with classification results.

### Features

- **File Upload**: Analyze network traffic from CSV files
- **Real-time Scoring**: Get quantum anomaly scores instantly
- **JSON Responses**: Clean, structured response format
- **OpenAPI/Swagger**: Auto-generated documentation at `/docs`

---

## Base URL

```
# Local development
http://localhost:8000

# Docker deployment
http://<host>:8000

# Production (example)
https://api.qzero.io/v1
```

---

## Authentication

> ⚠️ **Current Version**: No authentication required (development mode)

For production deployments, implement one of:
- API Key header: `X-API-Key: your-key`
- Bearer token: `Authorization: Bearer <token>`
- OAuth 2.0 for enterprise integration

---

## Endpoints

### Health Check

Check if the API is running and get backend information.

```http
GET /
```

#### Response

```json
{
    "status": "online",
    "backend": "quantum-simulator",
    "version": "1.0.0"
}
```

#### Example

```bash
curl http://localhost:8000/
```

---

### Analyze Traffic

Analyze network traffic data for anomalies and zero-day threats.

```http
POST /analyze
```

#### Request

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file` | File (CSV) | Yes | Network traffic data file |

#### Headers

```
Content-Type: multipart/form-data
```

#### Request Body

Upload a CSV file with network flow features. Expected columns:

| Column | Type | Description |
|--------|------|-------------|
| `flow_duration` | float | Duration of the flow in ms |
| `total_fwd_packets` | int | Forward packet count |
| `total_bwd_packets` | int | Backward packet count |
| `total_length_fwd_packets` | int | Total forward bytes |
| `total_length_bwd_packets` | int | Total backward bytes |
| `flow_bytes_per_sec` | float | Flow rate (bytes/s) |
| `flow_packets_per_sec` | float | Flow rate (packets/s) |
| `fwd_packet_length_mean` | float | Mean forward packet size |
| `bwd_packet_length_mean` | float | Mean backward packet size |
| `fwd_iat_mean` | float | Forward inter-arrival time |
| `bwd_iat_mean` | float | Backward inter-arrival time |
| `fwd_psh_flags` | int | PSH flag count (forward) |
| `bwd_psh_flags` | int | PSH flag count (backward) |
| `fwd_urg_flags` | int | URG flag count |

#### Response

```json
{
    "filename": "traffic_sample.csv",
    "total_flows": 1000,
    "anomalies_detected": 47,
    "quantum_anomaly_score": 0.87,
    "status": "CRITICAL"
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `filename` | string | Name of analyzed file |
| `total_flows` | integer | Number of network flows analyzed |
| `anomalies_detected` | integer | Count of detected anomalies |
| `quantum_anomaly_score` | float | Quantum model confidence (0.0-1.0) |
| `status` | string | Threat level: `SAFE`, `WARNING`, `CRITICAL` |

#### Status Levels

| Status | Score Range | Action |
|--------|-------------|--------|
| `SAFE` | 0.0 - 0.5 | Normal traffic, no action needed |
| `WARNING` | 0.5 - 0.85 | Suspicious patterns, investigate |
| `CRITICAL` | 0.85 - 1.0 | High probability zero-day, isolate immediately |

#### Example

```bash
curl -X POST http://localhost:8000/analyze \
    -F "file=@network_traffic.csv"
```

---

### Interactive Documentation

FastAPI provides automatic interactive documentation:

```http
GET /docs      # Swagger UI
GET /redoc     # ReDoc interface
GET /openapi.json  # OpenAPI schema
```

---

## Data Models

### AnalysisResult

Pydantic model for analysis response:

```python
from pydantic import BaseModel

class AnalysisResult(BaseModel):
    filename: str
    total_flows: int
    anomalies_detected: int
    quantum_anomaly_score: float
    status: str

    class Config:
        json_schema_extra = {
            "example": {
                "filename": "traffic.csv",
                "total_flows": 5000,
                "anomalies_detected": 127,
                "quantum_anomaly_score": 0.92,
                "status": "CRITICAL"
            }
        }
```

### Input CSV Schema

Example CSV structure:

```csv
flow_duration,total_fwd_packets,total_bwd_packets,total_length_fwd_packets,total_length_bwd_packets,flow_bytes_per_sec,flow_packets_per_sec,fwd_packet_length_mean,bwd_packet_length_mean,fwd_iat_mean,bwd_iat_mean,fwd_psh_flags,bwd_psh_flags,fwd_urg_flags
500.5,10,8,1500,1200,3000.0,20.0,150.0,150.0,50.0,60.0,1,1,0
250.3,50,5,8000,500,15000.0,100.0,160.0,100.0,10.0,100.0,5,1,2
```

---

## Error Handling

### Error Response Format

```json
{
    "detail": "Error message describing what went wrong"
}
```

### HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| `200` | OK | Request successful |
| `400` | Bad Request | Invalid input (e.g., non-CSV file) |
| `422` | Unprocessable Entity | Validation error |
| `500` | Internal Server Error | Server-side error |

### Common Errors

#### Invalid File Type

```http
POST /analyze
Content-Type: multipart/form-data

file=data.xlsx  # Wrong format
```

Response (400):
```json
{
    "detail": "Only CSV files supported in this version"
}
```

#### Missing Required Columns

Response (500):
```json
{
    "detail": "Missing required columns: flow_duration, total_fwd_packets"
}
```

---

## Examples

### Python (requests)

```python
import requests

# Health check
response = requests.get("http://localhost:8000/")
print(response.json())

# Analyze file
with open("traffic.csv", "rb") as f:
    response = requests.post(
        "http://localhost:8000/analyze",
        files={"file": ("traffic.csv", f, "text/csv")}
    )

result = response.json()
print(f"Status: {result['status']}")
print(f"Anomaly Score: {result['quantum_anomaly_score']}")

if result['status'] == 'CRITICAL':
    print("⚠️ ALERT: Potential zero-day detected!")
```

### Python (httpx - async)

```python
import httpx
import asyncio

async def analyze_traffic(filepath: str):
    async with httpx.AsyncClient() as client:
        with open(filepath, "rb") as f:
            response = await client.post(
                "http://localhost:8000/analyze",
                files={"file": ("data.csv", f)}
            )
        return response.json()

# Run
result = asyncio.run(analyze_traffic("network.csv"))
print(result)
```

### cURL

```bash
# Health check
curl http://localhost:8000/

# Analyze file
curl -X POST http://localhost:8000/analyze \
    -H "Content-Type: multipart/form-data" \
    -F "file=@/path/to/traffic.csv"

# Pretty print JSON
curl -s -X POST http://localhost:8000/analyze \
    -F "file=@traffic.csv" | python -m json.tool
```

### JavaScript (fetch)

```javascript
// Health check
const health = await fetch('http://localhost:8000/');
console.log(await health.json());

// Analyze file
const formData = new FormData();
formData.append('file', fileInput.files[0]);

const response = await fetch('http://localhost:8000/analyze', {
    method: 'POST',
    body: formData
});

const result = await response.json();

if (result.status === 'CRITICAL') {
    alert(`⚠️ Zero-day detected! Score: ${result.quantum_anomaly_score}`);
}
```

### PowerShell

```powershell
# Health check
Invoke-RestMethod -Uri "http://localhost:8000/"

# Analyze file
$file = Get-Item ".\traffic.csv"
$form = @{
    file = $file
}
$response = Invoke-RestMethod -Uri "http://localhost:8000/analyze" `
    -Method Post -Form $form

Write-Host "Status: $($response.status)"
Write-Host "Score: $($response.quantum_anomaly_score)"
```

---

## Python SDK

### Direct Module Usage

Instead of HTTP, you can use QZero modules directly:

```python
from src.preprocessing.data_loader import DataLoader, generate_synthetic_data
from src.preprocessing.feature_engineering import FeatureEngineer
from src.quantum.qsvm import QSVM, QSVMConfig
from src.quantum.qivae import QIVAE, QIVAEConfig
from src.classical.baseline import ClassicalBaseline

# Load data
loader = DataLoader()
X, y = generate_synthetic_data(n_samples=1000)
data = loader.prepare_data(X, y, binary=True)

# Train QSVM
config = QSVMConfig(n_qubits=4, max_samples_quantum=200)
engineer = FeatureEngineer(n_qubits=4)

X_train_q = engineer.fit_transform(data["X_train"], data["y_train"])
X_test_q = engineer.transform(data["X_test"])

qsvm = QSVM(config)
result = qsvm.fit_evaluate(X_train_q, data["y_train"], X_test_q, data["y_test"])

print(f"QSVM Accuracy: {result.accuracy:.4f}")
print(f"QSVM F1 Score: {result.f1_score:.4f}")
```

### QI-VAE for Anomaly Detection

```python
from src.quantum.qivae import QIVAE, QIVAEConfig

# Configure
config = QIVAEConfig(
    input_dim=14,
    latent_dim=4,
    hidden_dims=(64, 32),
    epochs=50,
    batch_size=32,
    anomaly_threshold_percentile=95.0
)

# Train on normal data only
qivae = QIVAE(config)
normal_mask = data["y_train"] == 0
X_normal = data["X_train"][normal_mask]

qivae.fit(X_normal, verbose=True)

# Detect anomalies
anomaly_scores = qivae.predict_anomaly_scores(data["X_test"])
predictions = qivae.predict(data["X_test"])

print(f"Detected {predictions.sum()} anomalies")
```

### Classical Baselines

```python
from src.classical.baseline import run_all_baselines, print_comparison_table

# Run all classical models
results = run_all_baselines(
    data["X_train"], data["y_train"],
    data["X_test"], data["y_test"],
    models=["random_forest", "svm_rbf", "gradient_boosting", "mlp"]
)

# Print comparison
print_comparison_table(results)

# Get best model
best = max(results, key=lambda r: r.f1)
print(f"Best model: {best.name} (F1: {best.f1:.4f})")
```

---

## Rate Limiting

> ⚠️ **Not Implemented**: Rate limiting should be added for production

Recommended limits:
- `/analyze`: 10 requests/minute per IP
- `/`: 100 requests/minute per IP

---

## Versioning

API versioning will be introduced in future releases:

```
/v1/analyze  # Current (implicit)
/v2/analyze  # Future
```

---

## Changelog

### v1.0.0 (Current)
- Initial release
- `/analyze` endpoint for CSV files
- Health check endpoint
- Quantum anomaly scoring (simulated)

### Planned Features
- [ ] Batch analysis endpoint
- [ ] Streaming analysis (WebSocket)
- [ ] Model selection parameter
- [ ] Detailed per-flow results
- [ ] Authentication/API keys
- [ ] Rate limiting

---

*Document Version: 1.0.0 | Last Updated: 2025*
