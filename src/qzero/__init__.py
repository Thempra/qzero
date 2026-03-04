"""
QZero - Sistema Unificado de Detección de Anomalías
"""

__version__ = "2.0.0"
__author__ = "Thempra"
__email__ = "thempra@overxet.com"

from .config import QZeroConfig, get_config, reset_config

__all__ = [
    "QZeroConfig",
    "get_config",
    "reset_config"
]