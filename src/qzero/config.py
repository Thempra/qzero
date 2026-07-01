"""
QZero Configuration Module

Centralized configuration management for QZero.
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
import json


@dataclass
class QZeroConfig:
    """Configuración centralizada de QZero."""

    # Rutas
    workspace: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent)
    src_path: Path = field(default_factory=lambda: Path(__file__).parent)

    # Directorios de datos
    data_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent / "data")
    raw_data_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent / "data" / "raw")
    synthetic_data_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent / "data" / "synthetic")
    simulated_threats_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent / "data" / "simulated-threats")
    synthetic_pcaps_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent / "data" / "synthetic-pcaps")
    threat_intelligence_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent / "data" / "threat-intelligence")

    # Directorios de reportes
    reports_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent / "reports")
    hourly_monitor_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent / "reports" / "hourly-monitor")
    api_health_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent / "reports" / "api-health")
    integrity_reports_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent / "integrity-reports")
    anomaly_risk_reports_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent / "anomaly-risk-reports")
    context_compressed_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent / "context-compressed")

    # Directorios de insights
    insights_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent / "insights")

    # Directorios de logs
    logs_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent / "logs")
    archived_logs_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent / "logs" / "archived")

    # Directorios de entrenamiento
    training_health_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent / "training-health")
    training_status_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent / "training-status")

    # Directorios de seguridad
    security_reports_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent / "security-reports")

    # Directorios de tasks
    tasks_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent / "tasks")

    # Archivos de configuración
    config_file: Path = field(default_factory=lambda: Path(__file__).parent.parent / "qzero-config.yaml")

    # Configuración de modelos
    n_qubits: int = 4
    use_qsvm: bool = True
    use_qivae: bool = True
    use_classical: bool = True

    # Configuración de entrenamiento
    train_samples: int = 5000
    train_epochs: int = 50
    batch_size: int = 32
    learning_rate: float = 0.001

    # Configuración de análisis
    default_threshold: float = 0.7
    promiscuous_mode: bool = True
    sample_interval: int = 1  # segundos

    # Configuración de logging
    verbose: bool = False
    log_level: str = "INFO"

    # Configuración de API
    api_port: int = 8000
    api_host: str = "0.0.0.0"
    api_reload: bool = True

    # Configuración de daemon
    daemon_interval: int = 3600  # 1 hora
    enable_daemon: bool = True

    # Directorio de salida para análisis
    output_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent / "output")

    def __post_init__(self):
        """Crear directorios si no existen."""
        for dir_path in [
            self.data_dir,
            self.raw_data_dir,
            self.synthetic_data_dir,
            self.simulated_threats_dir,
            self.synthetic_pcaps_dir,
            self.threat_intelligence_dir,
            self.reports_dir,
            self.hourly_monitor_dir,
            self.api_health_dir,
            self.integrity_reports_dir,
            self.anomaly_risk_reports_dir,
            self.context_compressed_dir,
            self.insights_dir,
            self.logs_dir,
            self.archived_logs_dir,
            self.training_health_dir,
            self.training_status_dir,
            self.security_reports_dir,
            self.tasks_dir,
            self.output_dir
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)

    @classmethod
    def load(cls, config_file: Optional[Path] = None) -> 'QZeroConfig':
        """Cargar configuración desde archivo."""
        if config_file is None:
            config_file = cls().config_file

        config = cls()

        if config_file.exists():
            with open(config_file, 'r') as f:
                data = json.load(f)

            # Cargar configuración del archivo
            for key, value in data.items():
                if hasattr(config, key):
                    setattr(config, key, value)

        return config

    def save(self, config_file: Optional[Path] = None):
        """Guardar configuración en archivo."""
        if config_file is None:
            config_file = self.config_file

        data = {}
        for key, value in self.__dict__.items():
            if not key.startswith('_'):
                data[key] = value

        with open(config_file, 'w') as f:
            json.dump(data, f, indent=2)

    def get(self, key: str, default: Any = None) -> Any:
        """Obtener valor de configuración por clave."""
        return getattr(self, key, default)

    def set(self, key: str, value: Any):
        """Establecer valor de configuración."""
        if hasattr(self, key):
            setattr(self, key, value)


# Singleton
_config: Optional[QZeroConfig] = None


def get_config(config_file: Optional[Path] = None) -> QZeroConfig:
    """Obtener instancia única de configuración."""
    global _config
    if _config is None:
        _config = QZeroConfig.load(config_file)
    return _config


def reset_config():
    """Resetear la configuración (útil para testing)."""
    global _config
    _config = None