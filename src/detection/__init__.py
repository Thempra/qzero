"""Módulo de detección de anomalías en tráfico de red."""

# Importar directamente desde el archivo de nivel superior
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from detection import NetworkTrafficAnalyzer

# Exportar también desde core para compatibilidad con run_detection.py
try:
    from core.detector import AnomalyDetector
    __all__.extend(['AnomalyDetector'])
except ImportError:
    pass

try:
    from core.monitor import StreamMonitor
    __all__.extend(['StreamMonitor'])
except ImportError:
    pass

__all__ = ['NetworkTrafficAnalyzer', 'AnomalyDetector', 'StreamMonitor']