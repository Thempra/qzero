#!/usr/bin/env bash

# Setup script para QZero
# Instala dependencias y configura el proyecto

set -e

echo "📦 Iniciando setup de QZero..."

# Verificar Python 3.10+
echo "🔍 Verificando Python 3..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 no instalado"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}')
echo "✅ Python $PYTHON_VERSION detectado"

# Instalar dependencias
echo "🔧 Instalando dependencias de Python..."
pip install --upgrade pip
pip install -e .

# Instalar dependencias del sistema
echo "🔧 Instalando dependencias del sistema..."
sudo apt update
sudo apt install -y tcpdump

# Crear estructura de directorios
echo "📁 Creando estructura de directorios..."
mkdir -p logs data/{raw,simulated-threats,synthetic-pcaps,threat-intelligence} insights/{daily-health,ai-local-trends,anomaly-patterns} reports configs

# Crear logs de cron
mkdir -p ./logs

echo "✅ Setup completado exitosamente"

# Instrucciones de uso
echo ""
echo "🚀 Comandos disponibles:"
echo "   qzero monitor --interface eth0 --promiscuous"
echo "   qzero detect --mode real-time"
echo "   qzero pcap --file capture.pcap"
echo ""
echo "📖 Más información en: QZERO.md"
