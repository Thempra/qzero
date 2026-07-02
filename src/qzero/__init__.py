"""
QZero — Quantum-Algorithm-Based Threat Detection
=================================================

Quick start::

    from qzero import QZero

    qzero = QZero(n_qubits=4)
    qzero.train(n_samples=5000)
    result = qzero.analyze_traffic("traffic.pcap")
"""

__version__ = "3.0.0"
__author__ = "Thempra"
__license__ = "MIT"

from .config import QZeroConfig, get_config, setup_logging
from .core.predictor import QZeroPredictor
from .core.detector import NetworkTrafficAnalyzer


def create_app():
    """Return the FastAPI application (requires: pip install fastapi uvicorn)."""
    from .api.app import create_app as _create_app
    return _create_app()


class QZero:
    """
    Unified interface for the QZero threat detection platform.

    Orchestrates training, prediction, PCAP analysis, and the REST API.

    Args:
        n_qubits: Number of qubits for quantum models (default 4).
        use_qsvm: Enable Quantum SVM (requires qiskit-machine-learning).
        use_qivae: Enable Quantum-Inspired VAE (requires torch).
    """

    def __init__(
        self,
        n_qubits: int = 4,
        use_qsvm: bool = True,
        use_qivae: bool = True,
    ):
        self.predictor = QZeroPredictor(
            n_qubits=n_qubits,
            use_qsvm=use_qsvm,
            use_qivae=use_qivae,
        )

    def train(self, n_samples: int = 5000, use_real_data: bool = False) -> dict:
        """
        Train all configured models.

        Args:
            n_samples: Synthetic samples to generate (ignored with use_real_data).
            use_real_data: Use the UGRansome real-world dataset.

        Returns:
            Training summary dictionary.
        """
        return self.predictor.train_all(
            n_samples=n_samples,
            use_real_data=use_real_data,
        )

    def predict(self, X, method: str = "best"):
        """Run predictions on pre-extracted features."""
        return self.predictor.predict(X, method=method)

    def analyze_traffic(self, pcap_file: str, method: str = "best") -> dict:
        """
        Analyze network traffic from a PCAP file.

        Args:
            pcap_file: Path to the PCAP file.
            method: Detection method ('qsvm', 'qivae', 'best').

        Returns:
            Analysis result dictionary.
        """
        analyzer = NetworkTrafficAnalyzer(predictor=self.predictor)
        return analyzer.analyze(pcap_file, method=method)

    def get_api(self):
        """Return the FastAPI application wired to this predictor's models."""
        import qzero.api.app as _api
        _api._predictor = self.predictor
        return create_app()

    def save(self, path: str):
        """Persist trained models to disk."""
        from pathlib import Path
        self.predictor.save(Path(path))

    def load(self, path: str):
        """Load previously saved models from disk."""
        from pathlib import Path
        self.predictor.load(Path(path))
        return self


__all__ = [
    "QZero",
    "QZeroPredictor",
    "NetworkTrafficAnalyzer",
    "QZeroConfig",
    "get_config",
    "setup_logging",
    "create_app",
    "__version__",
]
