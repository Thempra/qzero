"""
Tests for quantum module (QSVM and feature maps).
"""

import pytest
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from preprocessing.data_loader import generate_synthetic_data, DataLoader
from preprocessing.feature_engineering import FeatureEngineer

# Conditional imports - tests skip if Qiskit not available
try:
    from qiskit import QuantumCircuit
    from quantum.feature_maps import (
        create_feature_map,
        get_feature_map_info,
        FeatureMapType,
        QISKIT_AVAILABLE,
    )
    from quantum.qsvm import QSVM, QSVMConfig, QSVMResult, QISKIT_ML_AVAILABLE
except ImportError:
    QISKIT_AVAILABLE = False
    QISKIT_ML_AVAILABLE = False


# Skip all tests if Qiskit not available
pytestmark = pytest.mark.skipif(
    not QISKIT_AVAILABLE,
    reason="Qiskit not installed"
)


class TestFeatureMaps:
    """Tests for quantum feature maps."""
    
    def test_zz_feature_map_creation(self):
        """Test ZZFeatureMap creation."""
        fm = create_feature_map(4, FeatureMapType.ZZ, reps=2)
        
        assert fm.num_qubits == 4
        assert fm.num_parameters == 4  # One parameter per qubit per rep
    
    def test_z_feature_map_creation(self):
        """Test ZFeatureMap creation (no entanglement)."""
        fm = create_feature_map(4, FeatureMapType.Z, reps=2)
        
        assert fm.num_qubits == 4
    
    def test_pauli_feature_map_creation(self):
        """Test PauliFeatureMap creation."""
        fm = create_feature_map(4, FeatureMapType.PAULI, reps=2)
        
        assert fm.num_qubits == 4
    
    def test_custom_entangled_feature_map(self):
        """Test custom entangled feature map."""
        fm = create_feature_map(4, FeatureMapType.CUSTOM_ENTANGLED, reps=2)
        
        assert fm.num_qubits == 4
        info = get_feature_map_info(fm)
        assert info["n_gates"] > 0
    
    def test_feature_map_info(self):
        """Test feature map info extraction."""
        fm = create_feature_map(4, FeatureMapType.ZZ, reps=2)
        info = get_feature_map_info(fm)
        
        assert "n_qubits" in info
        assert "depth" in info
        assert "n_parameters" in info
        assert "n_gates" in info
        assert "gate_counts" in info
        
        assert info["n_qubits"] == 4
        assert info["depth"] > 0
    
    def test_different_entanglement_patterns(self):
        """Test different entanglement patterns."""
        for entanglement in ["linear", "full", "circular"]:
            fm = create_feature_map(
                4, FeatureMapType.ZZ, 
                reps=2, 
                entanglement=entanglement
            )
            assert fm.num_qubits == 4
    
    def test_variable_qubit_counts(self):
        """Test feature maps with different qubit counts."""
        for n_qubits in [2, 4, 6, 8]:
            fm = create_feature_map(n_qubits, FeatureMapType.ZZ, reps=2)
            assert fm.num_qubits == n_qubits


@pytest.mark.skipif(
    not QISKIT_ML_AVAILABLE,
    reason="Qiskit ML not installed"
)
class TestQSVM:
    """Tests for QSVM classifier."""
    
    @pytest.fixture
    def quantum_data(self):
        """Generate quantum-ready data (4 features)."""
        X, y = generate_synthetic_data(n_samples=200)
        loader = DataLoader()
        data = loader.prepare_data(X, y, binary=True)
        
        # Reduce to 4 dimensions for quantum
        engineer = FeatureEngineer(n_qubits=4)
        X_train_q = engineer.fit_transform(data["X_train"], data["y_train"])
        X_test_q = engineer.transform(data["X_test"])
        
        return {
            "X_train": X_train_q,
            "X_test": X_test_q,
            "y_train": data["y_train"],
            "y_test": data["y_test"],
        }
    
    def test_qsvm_config_defaults(self):
        """Test QSVMConfig default values."""
        config = QSVMConfig()
        
        assert config.n_qubits == 4
        assert config.feature_map_reps == 2
        assert config.use_classical_fallback is True
    
    def test_qsvm_initialization(self):
        """Test QSVM initialization."""
        config = QSVMConfig(n_qubits=4)
        qsvm = QSVM(config)
        
        assert qsvm.config.n_qubits == 4
        assert qsvm._is_fitted is False
    
    def test_qsvm_fit(self, quantum_data):
        """Test QSVM fitting."""
        config = QSVMConfig(n_qubits=4, max_samples_quantum=50)
        qsvm = QSVM(config)
        
        train_time = qsvm.fit(
            quantum_data["X_train"][:100],
            quantum_data["y_train"][:100]
        )
        
        assert train_time > 0
        assert qsvm._is_fitted is True
    
    def test_qsvm_predict(self, quantum_data):
        """Test QSVM prediction."""
        config = QSVMConfig(n_qubits=4, max_samples_quantum=50)
        qsvm = QSVM(config)
        
        qsvm.fit(
            quantum_data["X_train"][:50],
            quantum_data["y_train"][:50]
        )
        
        predictions = qsvm.predict(quantum_data["X_test"][:20])
        
        assert len(predictions) == 20
        assert set(predictions).issubset({0, 1})
    
    def test_qsvm_predict_before_fit_raises(self, quantum_data):
        """Test that predict before fit raises error."""
        qsvm = QSVM()
        
        with pytest.raises(RuntimeError):
            qsvm.predict(quantum_data["X_test"])
    
    def test_qsvm_dimension_mismatch_raises(self, quantum_data):
        """Test that dimension mismatch raises error."""
        config = QSVMConfig(n_qubits=6)  # Expect 6 features
        qsvm = QSVM(config)
        
        with pytest.raises(ValueError):
            # Data has 4 features
            qsvm.fit(quantum_data["X_train"], quantum_data["y_train"])
    
    def test_qsvm_evaluate(self, quantum_data):
        """Test QSVM evaluation."""
        config = QSVMConfig(n_qubits=4, max_samples_quantum=50)
        qsvm = QSVM(config)
        
        result = qsvm.fit_evaluate(
            quantum_data["X_train"][:50],
            quantum_data["y_train"][:50],
            quantum_data["X_test"][:20],
            quantum_data["y_test"][:20],
        )
        
        assert isinstance(result, QSVMResult)
        assert 0 <= result.accuracy <= 1
        assert 0 <= result.f1_score <= 1
        assert result.train_time > 0
    
    def test_qsvm_result_to_dict(self, quantum_data):
        """Test QSVMResult to_dict conversion."""
        config = QSVMConfig(n_qubits=4, max_samples_quantum=30)
        qsvm = QSVM(config)
        
        result = qsvm.fit_evaluate(
            quantum_data["X_train"][:30],
            quantum_data["y_train"][:30],
            quantum_data["X_test"][:10],
            quantum_data["y_test"][:10],
        )
        
        d = result.to_dict()
        
        assert "accuracy" in d
        assert "f1_score" in d
        assert "used_quantum" in d
    
    def test_classical_fallback(self, quantum_data):
        """Test classical fallback when quantum fails."""
        config = QSVMConfig(n_qubits=4, use_classical_fallback=True)
        qsvm = QSVM(config)
        
        # Should work even if quantum kernel computation fails
        qsvm._build_classical_fallback()
        qsvm.model.fit(
            quantum_data["X_train"][:50],
            quantum_data["y_train"][:50]
        )
        qsvm._is_fitted = True
        
        predictions = qsvm.predict(quantum_data["X_test"][:10])
        assert len(predictions) == 10
        assert qsvm._used_quantum is False


class TestQSVMIntegration:
    """Integration tests for full QSVM pipeline."""
    
    @pytest.mark.slow
    def test_full_pipeline_synthetic_data(self):
        """Test complete pipeline with synthetic data."""
        # Generate data
        X, y = generate_synthetic_data(n_samples=300)
        
        # Prepare
        loader = DataLoader()
        data = loader.prepare_data(X, y, binary=True)
        
        # Reduce dimensions
        engineer = FeatureEngineer(n_qubits=4)
        X_train_q = engineer.fit_transform(data["X_train"], data["y_train"])
        X_test_q = engineer.transform(data["X_test"])
        
        # Train QSVM
        config = QSVMConfig(
            n_qubits=4,
            max_samples_quantum=100,  # Limit for speed
        )
        qsvm = QSVM(config)
        
        result = qsvm.fit_evaluate(
            X_train_q[:100],
            data["y_train"][:100],
            X_test_q[:50],
            data["y_test"][:50],
        )
        
        # Should achieve reasonable accuracy on synthetic data
        assert result.accuracy > 0.5  # Better than random
        assert result.f1_score > 0.4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
