"""
Integration tests for the full QZero pipeline.

These tests verify that all components work together correctly.
"""

import pytest
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from preprocessing.data_loader import generate_synthetic_data, DataLoader
from preprocessing.feature_engineering import FeatureEngineer
from classical.baseline import ClassicalBaseline, run_all_baselines
from quantum.qsvm import QSVM, QSVMConfig
from quantum.qivae import QIVAE, QIVAEConfig
from evaluation.metrics import evaluate_model, evaluate_zero_day_detection


class TestFullPipeline:
    """Test the complete QZero pipeline end-to-end."""
    
    @pytest.fixture
    def sample_data(self):
        """Generate small dataset for testing."""
        X, y = generate_synthetic_data(n_samples=500, random_state=42)
        loader = DataLoader()
        return loader.prepare_data(X, y, binary=True, test_size=0.2, val_size=0.1)
    
    @pytest.fixture
    def quantum_data(self, sample_data):
        """Prepare quantum-ready features."""
        engineer = FeatureEngineer(n_qubits=4, reduction_method="pca")
        X_train_q = engineer.fit_transform(sample_data["X_train"], sample_data["y_train"])
        X_val_q = engineer.transform(sample_data["X_val"])
        X_test_q = engineer.transform(sample_data["X_test"])
        return {
            "X_train": X_train_q,
            "X_val": X_val_q,
            "X_test": X_test_q,
            "y_train": sample_data["y_train"],
            "y_val": sample_data["y_val"],
            "y_test": sample_data["y_test"],
        }
    
    def test_data_preparation_shapes(self, sample_data):
        """Verify data preparation produces correct shapes."""
        assert sample_data["X_train"].shape[1] == 14  # UGRansome features
        assert len(sample_data["y_train"]) == sample_data["X_train"].shape[0]
        assert len(sample_data["y_val"]) == sample_data["X_val"].shape[0]
        assert len(sample_data["y_test"]) == sample_data["X_test"].shape[0]
    
    def test_quantum_feature_preparation(self, quantum_data):
        """Verify quantum features have correct dimensions."""
        assert quantum_data["X_train"].shape[1] == 4  # n_qubits
        assert quantum_data["X_train"].min() >= 0.0
        # Allow small floating point tolerance
        assert quantum_data["X_train"].max() <= np.pi + 1e-10
    
    def test_classical_baseline_pipeline(self, sample_data):
        """Test classical baseline runs correctly."""
        results = run_all_baselines(
            sample_data["X_train"],
            sample_data["y_train"],
            sample_data["X_test"],
            sample_data["y_test"],
            models=["random_forest"]
        )
        
        assert len(results) == 1
        assert results[0].accuracy > 0.5  # Better than random
        assert results[0].f1 > 0.0
    
    def test_qsvm_pipeline(self, quantum_data):
        """Test QSVM training and evaluation."""
        config = QSVMConfig(
            n_qubits=4,
            max_samples_quantum=100,  # Small for fast test
            use_classical_fallback=True,
        )
        qsvm = QSVM(config)
        
        result = qsvm.fit_evaluate(
            quantum_data["X_train"][:100],
            quantum_data["y_train"][:100],
            quantum_data["X_test"],
            quantum_data["y_test"]
        )
        
        assert result.accuracy > 0.0
        assert result.f1_score > 0.0
        assert result.train_time > 0
    
    def test_qivae_pipeline(self, sample_data):
        """Test QI-VAE training and evaluation."""
        # Train on normal samples only
        normal_mask = sample_data["y_train"] == 0
        X_train_normal = sample_data["X_train"][normal_mask]
        
        config = QIVAEConfig(
            input_dim=sample_data["X_train"].shape[1],
            latent_dim=4,
            hidden_dims=(32, 16),
            epochs=10,  # Small for fast test
            batch_size=32,
        )
        
        qivae = QIVAE(config)
        result = qivae.fit_evaluate(
            X_train_normal,
            sample_data["X_test"],
            sample_data["y_test"],
            verbose=False,
        )
        
        assert result.train_loss > 0
        assert result.anomaly_threshold > 0
        assert 0.0 <= result.accuracy <= 1.0
    
    def test_evaluation_metrics(self, sample_data):
        """Test evaluation metrics computation."""
        # Get predictions from a simple model
        baseline = ClassicalBaseline("random_forest")
        baseline.fit(sample_data["X_train"], sample_data["y_train"])
        y_pred = baseline.predict(sample_data["X_test"])
        
        # Test standard evaluation
        result = evaluate_model(sample_data["y_test"], y_pred)
        assert 0.0 <= result.accuracy <= 1.0
        assert 0.0 <= result.precision <= 1.0
        assert 0.0 <= result.recall <= 1.0
        assert 0.0 <= result.f1 <= 1.0
        assert result.confusion_matrix.shape[0] == result.confusion_matrix.shape[1]
        
        # Test zero-day evaluation
        zd_metrics = evaluate_zero_day_detection(sample_data["y_test"], y_pred)
        if zd_metrics["zero_day_samples"] > 0:
            assert 0.0 <= zd_metrics["zero_day_detection_rate"] <= 1.0


class TestPipelineReproducibility:
    """Test that pipeline results are reproducible."""
    
    def test_synthetic_data_reproducibility(self):
        """Same seed should produce same data."""
        X1, y1 = generate_synthetic_data(n_samples=100, random_state=42)
        X2, y2 = generate_synthetic_data(n_samples=100, random_state=42)
        
        np.testing.assert_array_equal(X1.values, X2.values)
        np.testing.assert_array_equal(y1.values, y2.values)
    
    def test_feature_engineering_reproducibility(self):
        """Same input should produce same output."""
        X, y = generate_synthetic_data(n_samples=100, random_state=42)
        loader = DataLoader()
        data = loader.prepare_data(X, y, binary=True, test_size=0.2)
        
        engineer1 = FeatureEngineer(n_qubits=4, reduction_method="pca")
        X1 = engineer1.fit_transform(data["X_train"], data["y_train"])
        
        engineer2 = FeatureEngineer(n_qubits=4, reduction_method="pca")
        X2 = engineer2.fit_transform(data["X_train"], data["y_train"])
        
        np.testing.assert_array_almost_equal(X1, X2)


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_small_dataset(self):
        """Pipeline should handle very small datasets."""
        X, y = generate_synthetic_data(n_samples=50, random_state=42)
        loader = DataLoader()
        data = loader.prepare_data(X, y, binary=True, test_size=0.3)
        
        baseline = ClassicalBaseline("random_forest")
        result = baseline.fit_evaluate(
            data["X_train"], data["y_train"],
            data["X_test"], data["y_test"]
        )
        assert result.accuracy >= 0  # Should not crash
    
    def test_imbalanced_data(self):
        """Pipeline should handle imbalanced datasets."""
        X, y = generate_synthetic_data(
            n_samples=200,
            anomaly_ratio=0.05,  # Very few anomalies
            random_state=42
        )
        loader = DataLoader()
        data = loader.prepare_data(X, y, binary=True, test_size=0.2)
        
        baseline = ClassicalBaseline("random_forest")
        result = baseline.fit_evaluate(
            data["X_train"], data["y_train"],
            data["X_test"], data["y_test"]
        )
        # F1 should still be computed
        assert result.f1 >= 0
    
    def test_qsvm_dimension_mismatch(self):
        """QSVM should raise on dimension mismatch."""
        X_wrong = np.random.rand(50, 8)  # 8 features, not 4
        y = np.random.randint(0, 2, 50)
        
        qsvm = QSVM(QSVMConfig(n_qubits=4))
        
        with pytest.raises(ValueError, match="dimensions"):
            qsvm.fit(X_wrong, y)


class TestQualityThresholds:
    """Test that models meet minimum quality thresholds."""
    
    @pytest.fixture
    def standard_data(self):
        """Standard test dataset."""
        X, y = generate_synthetic_data(n_samples=1000, random_state=42)
        loader = DataLoader()
        return loader.prepare_data(X, y, binary=True, test_size=0.2)
    
    def test_random_forest_quality(self, standard_data):
        """Random forest should achieve >80% accuracy on synthetic data."""
        baseline = ClassicalBaseline("random_forest")
        result = baseline.fit_evaluate(
            standard_data["X_train"], standard_data["y_train"],
            standard_data["X_test"], standard_data["y_test"]
        )
        assert result.accuracy > 0.80, f"RF accuracy {result.accuracy} below threshold"
        assert result.f1 > 0.70, f"RF F1 {result.f1} below threshold"
    
    def test_qivae_quality(self, standard_data):
        """QI-VAE should achieve reasonable anomaly detection."""
        normal_mask = standard_data["y_train"] == 0
        X_train_normal = standard_data["X_train"][normal_mask]
        
        config = QIVAEConfig(
            input_dim=standard_data["X_train"].shape[1],
            latent_dim=4,
            epochs=30,
        )
        
        qivae = QIVAE(config)
        result = qivae.fit_evaluate(
            X_train_normal,
            standard_data["X_test"],
            standard_data["y_test"],
            verbose=False,
        )
        
        # For anomaly detection, recall is most important
        assert result.recall > 0.30, f"QI-VAE recall {result.recall} below threshold"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
