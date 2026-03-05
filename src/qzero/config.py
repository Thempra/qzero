"""
Configuración de QZero

Gestor centralizado de configuración
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class QZeroConfig:
    """Gestor de configuración para QZero"""

    def __init__(self, config_file: Optional[str] = None):
        """
        Inicializa la configuración.

        Args:
            config_file: Ruta al archivo de configuración YAML
        """
        self.config_file = Path(config_file) if config_file else None
        self.config_dir = Path.home() / ".qzero"
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self._config: Dict[str, Any] = {}

        # Cargar configuración por defecto
        self._load_defaults()

        # Cargar configuración personalizada si existe
        if self.config_file and self.config_file.exists():
            self._load_custom()

    def _load_defaults(self):
        """Carga configuración por defecto"""
        self._config = {
            # Paths
            "output_dir": str(Path.cwd() / "reports"),
            "log_dir": str(self.config_dir / "logs"),
            "data_dir": str(self.config_dir / "data"),
            "model_dir": str(self.config_dir / "models"),
            "pcap_dir": str(self.config_dir / "pcaps"),

            # Model settings
            "default_threshold": 0.7,
            "default_model": "svm",
            "n_qubits": 4,

            # Monitor settings
            "default_interface": "eth0",
            "promiscuous_mode": False,
            "monitor_interval": 1.0,

            # Daemon settings
            "daemon_interval": 60,
            "log_level": "INFO",

            # Paths absolutos
            "paths": {
                "output_dir": Path.cwd() / "reports",
                "log_dir": self.config_dir / "logs",
                "data_dir": self.config_dir / "data",
                "model_dir": self.config_dir / "models",
                "pcap_dir": self.config_dir / "pcaps"
            }
        }

    def _load_custom(self):
        """Carga configuración personalizada desde archivo"""
        import yaml

        try:
            with open(self.config_file, 'r') as f:
                custom_config = yaml.safe_load(f)

            if custom_config:
                self._config.update(custom_config)
                logger.info(f"Configuración personalizada cargada desde {self.config_file}")
        except Exception as e:
            logger.warning(f"No se pudo cargar configuración personalizada: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """
        Obtiene un valor de configuración.

        Args:
            key: Clave de configuración (puede usar puntos para anidación)
            default: Valor por defecto si la clave no existe

        Returns:
            Valor de configuración
        """
        keys = key.split('.')
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any):
        """
        Establece un valor de configuración.

        Args:
            key: Clave de configuración (puede usar puntos para anidación)
            value: Valor a establecer
        """
        keys = key.split('.')
        config = self._config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value

    def save(self, config_file: Optional[str] = None):
        """
        Guarda la configuración en un archivo.

        Args:
            config_file: Ruta para guardar la configuración
        """
        output_file = Path(config_file) if config_file else self.config_file
        if not output_file:
            output_file = self.config_dir / "qzero.yaml"

        output_file.parent.mkdir(parents=True, exist_ok=True)

        import yaml
        with open(output_file, 'w') as f:
            yaml.dump(self._config, f, default_flow_style=False)

        logger.info(f"Configuración guardada en {output_file}")

    def get_path(self, key: str) -> Path:
        """
        Obtiene un path de configuración como objeto Path.

        Args:
            key: Clave de configuración

        Returns:
            Objeto Path
        """
        path_str = self.get(key)
        return Path(path_str) if path_str else Path.cwd()


# Función global para obtener configuración
_config: Optional[QZeroConfig] = None


def get_config(config_file: Optional[str] = None) -> QZeroConfig:
    """
    Obtiene la instancia global de configuración.

    Args:
        config_file: Ruta al archivo de configuración

    Returns:
        Instancia de QZeroConfig
    """
    global _config
    if _config is None:
        _config = QZeroConfig(config_file)
    return _config


def setup_logging(verbose: bool = False):
    """
    Configura el logging para QZero.

    Args:
        verbose: Modo detallado activado
    """
    level = logging.DEBUG if verbose else logging.INFO
    log_dir = get_config().get_path("log_dir")

    log_dir.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_dir / "qzero.log")
        ]
    )