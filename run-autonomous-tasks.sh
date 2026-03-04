#!/bin/bash
# QZero Autonomous Tasks Runner - Quick Test

echo "🚀 Ejecutando tareas autónomas de QZero..."
echo ""

cd /home/thempra/projects/qzero

echo "1️⃣  Ejecutando autonomous-data-engineer.py..."
python3 autonomous-data-engineer.py

echo ""
echo "2️⃣  Ejecutando autonomous-anomaly-detection.py..."
python3 autonomous-anomaly-detection.py

echo ""
echo "✅ Tareas completadas. Revisa los reportes en: reports/data-engine/ y reports/anomaly-detection/"