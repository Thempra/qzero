# 📥 Descarga de PCAPs Etiquetados para QZero

## 🎯 Objetivo
Recopilar ejemplos de PCAPs etiquetados para testing del sistema QZero

## 📊 PCAPs Generados Sintéticamente

Se han creado 5 archivos de PCAP con tráfico etiquetado:

### 1. normal_traffic_*.pcap
- **Tipo**: Tráfico normal
- **Protocolos**: ICMP, TCP, UDP
- **Patrones**: HTTP, SSH, DNS, Ping
- **IPs**: 192.168.1.x (normales)
- **Paquetes**: 600
- **Duración**: 30 segundos (20 pps)

### 2. ddos_traffic_*.pcap
- **Tipo**: DDoS Attack
- **Protocolos**: TCP, UDP
- **Patrones**: SYN Flood, UDP Flood
- **IPs**: 10.0.x.0 (atacantes)
- **Paquetes**: 600
- **Duración**: 30 segundos (20 pps)

### 3. bruteforce_traffic_*.pcap
- **Tipo**: Brute Force Attack
- **Protocolos**: TCP
- **Patrones**: SSH Brute Force, Telnet Brute Force
- **IPs**: 10.0.x.0 (atacantes)
- **Paquetes**: 600
- **Duración**: 30 segundos (20 pps)

### 4. exfiltration_traffic_*.pcap
- **Tipo**: Data Exfiltration
- **Protocolos**: TCP, UDP
- **Patrones**: C2 Communication, Data Transfer
- **IPs**: 10.0.x.0 (atacantes)
- **Paquetes**: 600
- **Duración**: 30 segundos (20 pps)

### 5. malware_traffic_*.pcap
- **Tipo**: Malware Activity
- **Protocolos**: TCP, UDP
- **Patrones**: Crypto Mining, Spider Scanning
- **IPs**: 10.0.x.0 (atacantes)
- **Paquetes**: 600
- **Duración**: 30 segundos (20 pps)

---

## 📁 Ubicación

```
/home/thempra/projects/qzero/data/synthetic-pcaps/
├── normal_traffic_20260220_154302.pcap (600 packets)
├── ddos_traffic_20260220_154303.pcap (600 packets)
├── bruteforce_traffic_20260220_154304.pcap (600 packets)
├── exfiltration_traffic_20260220_154305.pcap (600 packets)
└── malware_traffic_20260220_154306.pcap (600 packets)
```

---

## 🔍 Etiquetado

Cada paquete incluye metadata en sus atributos personalizados:

```python
packet.qzero_label = "normal"  # o "ddos", "bruteforce", "exfiltration", "malware"
packet.qzero_attack_type = "ssh_bruteforce"  # o "syn_flood", etc.
packet.qzero_timestamp = "2026-02-20T15:43:02.123456"
packet.qzero_packet_id = 123
```

---

## 🚀 Cómo Usar

### Generar más PCAPs

```bash
cd /home/thempra/projects/qzero

# Generar solo tráfico normal
python3 scripts/generate-synthetic-pcaps-v2.py --type normal --duration 60 --rate 50

# Generar tráfico DDoS
python3 scripts/generate-synthetic-pcaps-v2.py --type ddos --duration 60 --rate 100

# Generar todos los tipos
python3 scripts/generate-synthetic-pcaps-v2.py --all --duration 60 --rate 50
```

### Analizar PCAPs

```bash
# Usar scapy para ver contenido
python3 << 'EOF'
from scapy.all import *
import sys

pcap_files = [
    "data/synthetic-pcaps/normal_traffic_*.pcap",
    "data/synthetic-pcaps/ddos_traffic_*.pcap",
]

for pattern in pcap_files:
    for pcap_file in Path('.').glob(pattern):
        print(f"\n📁 Analizando: {pcap_file.name}")
        packets = rdpcap(str(pcap_file))

        # Contar por tipo
        labels = {}
        for packet in packets:
            label = getattr(packet, 'qzero_label', 'unknown')
            labels[label] = labels.get(label, 0) + 1

        print(f"   Labels: {labels}")
EOF
```

### Testear QZero con PCAPs

```bash
# Analizar con QZero API
cd /home/thempra/projects/qzero

# Ejecutar API de QZero
python3 -m uvicorn src.api:app --host 0.0.0.0 --port 8000

# En otra terminal, analizar PCAP
curl -X POST http://localhost:8000/analyze -F "file=@data/synthetic-pcaps/normal_traffic_*.pcap"
```

---

## 📦 Datasets Públicos Recomendados

| Dataset | Descripción | URL | Etiquetado |
|---------|-------------|-----|------------|
| ISCX-IDS2012 | Intrusion Detection Evaluation | http://205.174.165.80/CICDataset/ISCX-IDS-2012/ | ✅ Si |
| CIC-IDS2017 | Canadian Institute for Cybersecurity | https://www.unb.ca/cic/datasets/ids2017.html | ✅ Si |
| CSE-CIC-IDS2018 | Canadian Institute for Cybersecurity | https://www.unb.ca/cic/datasets/ids2018.html | ✅ Si |
| NICTA | Network intrusion traffic | https://github.com/ahlawatashutosh/NICTA | ✅ Si |

---

## 🎯 Uso Recomendado para Testing

### Test 1: Detección de Tráfico Normal
```bash
python3 scripts/generate-synthetic-pcaps-v2.py --type normal --duration 60 --rate 30
curl -X POST http://localhost:8000/analyze -F "file=@data/synthetic-pcaps/normal_traffic_*.pcap"
```

### Test 2: Detección de DDoS
```bash
python3 scripts/generate-synthetic-pcaps-v2.py --type ddos --duration 60 --rate 100
curl -X POST http://localhost:8000/analyze -F "file=@data/synthetic-pcaps/ddos_traffic_*.pcap"
```

### Test 3: Detección de Brute Force
```bash
python3 scripts/generate-synthetic-pcaps-v2.py --type bruteforce --duration 60 --rate 30
curl -X POST http://localhost:8000/analyze -F "file=@data/synthetic-pcaps/bruteforce_traffic_*.pcap"
```

### Test 4: Detección de Exfiltration
```bash
python3 scripts/generate-synthetic-pcaps-v2.py --type exfiltration --duration 60 --rate 30
curl -X POST http://localhost:8000/analyze -F "file=@data/synthetic-pcaps/exfiltration_traffic_*.pcap"
```

### Test 5: Detección de Malware
```bash
python3 scripts/generate-synthetic-pcaps-v2.py --type malware --duration 60 --rate 30
curl -X POST http://localhost:8000/analyze -F "file=@data/synthetic-pcaps/malware_traffic_*.pcap"
```

---

**Generado**: 2026-02-20 15:43 (Europe/Madrid)
**Creado por**: QZero Roadmap Executor
**Version**: 1.0