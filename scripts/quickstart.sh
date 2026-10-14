#!/bin/bash
# QZero Quick Start Script
# Installs and runs QZero with minimal configuration

set -e

echo "🚀 QZero Quick Start"
echo "===================="
echo ""

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker first."
    echo "Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose not found. Please install Docker Compose."
    exit 1
fi

echo "✅ Docker and Docker Compose found"
echo ""

# Build and start containers
echo "🔨 Building QZero containers..."
docker-compose up -d --build

echo ""
echo "⏳ Waiting for containers to start..."
sleep 5

# Check status
echo ""
echo "📊 Container Status:"
docker-compose ps

echo ""
echo "========================================"
echo "🎉 QZero is running!"
echo "========================================"
echo ""
echo "Access the API at: http://localhost:8000"
echo "Access the Dashboard at: http://localhost:8501"
echo ""
echo "Quick Commands:"
echo "  • Analyze a PCAP file:"
echo "    curl -X POST http://localhost:8000/analyze -F \"file=@traffic.pcap\""
echo ""
echo "  • Run batch analysis:"
echo "    python qzero-cli-batch.py -f *.pcap"
echo ""
echo "  • Start real-time detection:"
echo "    python qzero-cli.py detect --stream netflow"
echo ""
echo "📚 Read the full docs at: https://github.com/thempra/qzero"
echo ""
echo "Need help? Check the DASHBOARD_README.md"