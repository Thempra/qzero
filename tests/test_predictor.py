"""
Tests for QZeroPredictor class.
"""

import pytest
import numpy as np
import tempfile
from pathlib import Path

from qzero.core.predictor import QZeroPredictor
from qzero.preprocessing.data_loader import generate_synthetic_data


class TestQZeroPredictorInit:
    """Tests for QZeroPredictor initialization."""

    def test_default_init(self):
        """Test default initialization."""
        predictor = QZeroPredictor()

        assert predictor.n_qubits == 4
        assert predictor.use_qsvm is True
        assert predictor.use_qivae is True
        assert predictor.use_classical is True
        assert predictor.model_fitted is False

    def test_custom_init(self):
        """Test custom initialization."""
        predictor = QZeroPredictor(
            n_qubits=6,
            use_qsvm=False,
            use_qivae=True,
            use_classical=True,
            classical_models=["random_forest"],
        )

        assert predictor.n_qubits == 6
        assert predictor.use_qsvm is False
        assert predictor.use_qivae is True
        assert predictor.classical_models == ["random_forest"]

    def test_repr(self):
        """Test string representation."""
        predictor = QZeroPredictor(n_qubits=4)
        repr_str = repr(predictor)

        assert "QZeroPredictor" in repr_str
        assert "n_qubits=4" in repr_str


class TestQZeroPredictorDataPrep:
    """Tests for data preparation."""

    def test_prepare_data(self):
        """Test data preparation."""
        predictor = QZeroPredictor()
        X, y = generate_synthetic_data(n_samples=500)

        data = predictor.prepare_data(X.values, y.values)

        assert "X_train" in data
        assert "X_test" in data
        assert "y_train" in data
        assert "y_test" in data
        assert predictor.scaler is not None
        assert predictor.feature_engineer is not None

    def test_prepare_data_stores_test_set(self):
        """Test that prepare_data stores test set."""
        predictor = QZeroPredictor()
        X, y = generate_synthetic_data(n_samples=500)

        predictor.prepare_data(X.values, y.values)

        assert predictor.X_test is not None
        assert predictor.y_test is not None
        assert len(predictor.X_test) > 0


class TestQZeroPredictorClassicalOnly:
    """Tests for classical-only training (fast tests)."""

    def test_train_classical_only(self):
        """Test training with only classical models."""
        predictor = QZeroPredictor(
            use_qsvm=False,
            use_qivae=False,
            use_classical=True,
            classical_models=["random_forest"],
        )

        summary = predictor.train_all(
            n_samples=500,
            use_real_data=False,
            use_qsvm=False,
            use_qivae=False,
            use_classical=True,
            classical_models=["random_forest"],
        )

        assert predictor.model_fitted is True
        assert summary["qsvm"] is None
        assert summary["qivae"] is None
        assert summary["classical"] is not None
        assert "random_forest" in summary["classical"]

    def test_predict_after_classical_training(self):
        """Test prediction after classical training."""
        predictor = QZeroPredictor(
            use_qsvm=False,
            use_qivae=False,
            use_classical=True,
            classical_models=["random_forest"],
        )

        predictor.train_all(
            n_samples=500,
            use_qsvm=False,
            use_qivae=False,
        )

        # Generate new test data
        X_new, _ = generate_synthetic_data(n_samples=10)
        predictions = predictor.predict(X_new.values)

        assert predictions.shape[0] == 10
        assert all(p in [0, 1] for p in predictions)


class TestQZeroPredictorErrors:
    """Tests for error handling."""

    def test_predict_before_training_raises(self):
        """Test that predicting before training raises error."""
        predictor = QZeroPredictor()
        X, _ = generate_synthetic_data(n_samples=10)

        with pytest.raises(RuntimeError, match="not trained"):
            predictor.predict(X.values)

    def test_evaluate_before_training_raises(self):
        """Test that evaluating before training raises error."""
        predictor = QZeroPredictor()

        with pytest.raises(RuntimeError, match="not trained"):
            predictor.evaluate()

    def test_compare_models_before_training_raises(self):
        """Test that comparing models before training raises error."""
        predictor = QZeroPredictor()

        with pytest.raises(RuntimeError, match="not trained"):
            predictor.compare_models()


class TestQZeroPredictorSaveLoad:
    """Tests for save/load functionality."""

    def test_save_and_load(self):
        """Test saving and loading models."""
        # Train a predictor
        predictor = QZeroPredictor(
            use_qsvm=False,
            use_qivae=False,
            use_classical=True,
            classical_models=["random_forest"],
        )
        predictor.train_all(n_samples=500, use_qsvm=False, use_qivae=False)

        # Save to temp directory
        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = Path(tmpdir) / "models"
            predictor.save(save_path)

            # Check files exist
            assert (save_path / "scaler.pkl").exists()
            assert (save_path / "feature_engineer.pkl").exists()
            assert (save_path / "training_info.json").exists()


class TestQZeroPredictorTrainingInfo:
    """Tests for training info tracking."""

    def test_training_info_populated(self):
        """Test that training info is populated after training."""
        predictor = QZeroPredictor(
            use_qsvm=False,
            use_qivae=False,
            use_classical=True,
            classical_models=["random_forest"],
        )

        predictor.train_all(n_samples=500, use_qsvm=False, use_qivae=False)

        assert "training_time" in predictor.training_info
        assert "n_samples" in predictor.training_info
        assert "n_features" in predictor.training_info
        assert predictor.training_info["n_samples"] == 500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
