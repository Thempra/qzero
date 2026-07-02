"""Módulo de detección de anomalías en tráfico de red."""

# Importar directamente desde el archivo .py (evita circular import)
import sys
from pathlib import Path
import importlib.util

detection_file = Path(__file__).parent.parent / "detection.py"
spec = importlib.util.spec_from_file_location("detection", detection_file)
detection_module = importlib.util.module_from_spec(spec)
sys.modules['detection'] = detection_module
spec.loader.exec_module(detection_module)

NetworkTrafficAnalyzer = detection_module.NetworkTrafficAnalyzer

# Exportar también desde core para compatibilidad con run_detection.py
__all__ = ['NetworkTrafficAnalyzer']

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