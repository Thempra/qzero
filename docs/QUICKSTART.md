# QZero Quick Start

> Get up and running with QZero in 2 minutes

## 🚀 One-Command Setup

```bash
chmod +x scripts/quickstart.sh
./scripts/quickstart.sh
```

This script will:
- ✅ Check Docker and Docker Compose
- ✅ Build QZero containers
- ✅ Start all services
- ✅ Display access URLs and basic commands

## 📋 Prerequisites

- **Docker** (v20.10+)
- **Docker Compose** (v2.0+)
- **~10GB free disk space**

### Install Docker

**Linux:**
```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```

**macOS/Windows:**
Download from [https://www.docker.com/products/docker](https://www.docker.com/products/docker)

## 🎯 Quick Access URLs

Once started:

| Service | URL |
|---------|-----|
| **API** | http://localhost:8000 |
| **Dashboard** | http://localhost:8501 |
| **API Docs** | http://localhost:8000/docs |

## 📖 Basic Usage

### Analyze Traffic

```bash
# Upload a PCAP file
curl -X POST http://localhost:8000/analyze \
  -F "file=@traffic.pcap"
```

### Command Line

```bash
# Single file
python qzero-cli-batch.py -f suspicious.pcap --model qivae

# Multiple files
python qzero-cli-batch.py -f *.pcap

# Real-time detection
python qzero-cli.py detect --stream netflow
```

### Dashboard

1. Open http://localhost:8501 in your browser
2. Generate synthetic data or upload your own
3. View anomaly scores and visualizations
4. Compare quantum vs classical models

## 🔧 Configuration

Edit `config.yaml` to customize:

```yaml
detection:
  model: "qivae"      # Options: qsvm, qivae, hybrid
  sensitivity: "high" # Threshold: 0.85
  backend: "aer_simulator"
```

## 🛑 Stop the Project

```bash
docker-compose down
```

## 📚 Documentation

- **Full README**: See [README.md](./README.md)
- **Dashboard Guide**: See [DASHBOARD_README.md](./DASHBOARD_README.md)
- **CLI Docs**: See [CLI_README.md](./CLI_README.md)

## ❓ Troubleshooting

### Port already in use?
```bash
# Find what's using port 8000
sudo lsof -i :8000

# Use different port
docker run -p 8080:8000 thempra/qzero:latest
```

### Containers not starting?
```bash
# Check logs
docker-compose logs -f

# Rebuild
docker-compose up -d --build --force-recreate
```

### Need to run locally (not Docker)?
```bash
# Install dependencies
pip install -r requirements.txt

# Run models
python train_models.py

# Run detection
python qzero-cli.py detect --stream netflow
```

## 🤝 Contributing

Want to help? Check the [GitHub repo](https://github.com/thempra/qzero) for issues and pull requests.

## 📄 License

MIT - See [LICENSE](./LICENSE) for details.