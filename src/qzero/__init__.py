"""
QZero - Sistema de Detección de Anomalías y Monitoreo de Seguridad
"""

__version__ = "2.2.0"
__author__ = "Thempra"
__license__ = "MIT"

from .config import get_config, QZeroConfig, setup_logging
from .daemons import QZeroDaemon, BaseDaemonTask

__all__ = [
    'get_config',
    'QZeroConfig',
    'setup_logging',
    'QZeroDaemon',
    'BaseDaemonTask'
]