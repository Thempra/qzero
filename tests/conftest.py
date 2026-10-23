"""
Shared pytest fixtures for QZero tests.
"""

import os

# Fail-closed es el default DURO del producto: una app sin ADMIN_PASSWORD
# responde 503 en las rutas protegidas (app.py, middleware SPA). Decenas de
# tests construyen TestClient(app) sin credenciales, así que la suite declara
# aquí su opt-out. Vive en conftest.py —NUNCA en el código de producción— para
# que no exista ninguna ruta por la que un despliegue real quede abierto.
# Los tests que verifican el comportamiento fail-closed lo desactivan a
# propósito (ver tests/test_fase0_auth_extra.py).
os.environ.setdefault("QZERO_AUTH_ENFORCE", "0")

import pytest  # noqa: E402
import numpy as np  # noqa: E402

from qzero.preprocessing.data_loader import generate_synthetic_data, DataLoader  # noqa: E402
from qzero.preprocessing.feature_engineering import FeatureEngineer  # noqa: E402


@pytest.fixture(scope="session")
def small_dataset():
    """Small dataset for fast tests (500 samples)."""
    X, y = generate_synthetic_data(n_samples=500, random_state=42)
    loader = DataLoader()
    return loader.prepare_data(X, y, binary=True, test_size=0.2, val_size=0.1)


@pytest.fixture(scope="session")
def medium_dataset():
    """Medium dataset for thorough tests (2000 samples)."""
    X, y = generate_synthetic_data(n_samples=2000, random_state=42)
    loader = DataLoader()
    return loader.prepare_data(X, y, binary=True, test_size=0.2, val_size=0.1)


@pytest.fixture(scope="session")
def hard_dataset():
    """Hard difficulty dataset for realistic benchmarking."""
    X, y = generate_synthetic_data(n_samples=1000, difficulty="hard", random_state=42)
    loader = DataLoader()
    return loader.prepare_data(X, y, binary=True, test_size=0.2, val_size=0.1)


@pytest.fixture(scope="session")
def quantum_small_dataset(small_dataset):
    """Quantum-ready features from small dataset (4 qubits)."""
    engineer = FeatureEngineer(n_qubits=4, reduction_method="pca")
    X_train_q = engineer.fit_transform(small_dataset["X_train"], small_dataset["y_train"])
    X_val_q = engineer.transform(small_dataset["X_val"])
    X_test_q = engineer.transform(small_dataset["X_test"])
    
    return {
        "X_train": X_train_q,
        "X_val": X_val_q,
        "X_test": X_test_q,
        "y_train": small_dataset["y_train"],
        "y_val": small_dataset["y_val"],
        "y_test": small_dataset["y_test"],
        "n_qubits": 4,
    }


@pytest.fixture
def normal_only_data(small_dataset):
    """Dataset with only normal samples (for anomaly detection training)."""
    normal_mask = small_dataset["y_train"] == 0
    return {
        "X_train_normal": small_dataset["X_train"][normal_mask],
        "X_test": small_dataset["X_test"],
        "y_test": small_dataset["y_test"],
    }


@pytest.fixture
def tiny_dataset():
    """Minimal dataset for quick validation (100 samples)."""
    X, y = generate_synthetic_data(n_samples=100, random_state=42)
    loader = DataLoader()
    return loader.prepare_data(X, y, binary=True, test_size=0.3)
