"""
Tests for classical baseline module.
"""

import pytest
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from preprocessing.data_loader import generate_synthetic_data, DataLoader
from classical.baseline import ClassicalBaseline, run_all_baselines, ModelResult


class TestClassicalBaseline:
    """Tests for ClassicalBaseline class."""
    
    @pytest.fixture
    def sample_data(self):
        """Generate sample data for tests."""
        X, y = generate_synthetic_data(n_samples=500)
        loader = DataLoader()
        return loader.prepare_data(X, y, binary=True)
    
    def test_available_models(self):
        """Test that all models can be instantiated."""
        for model_name in ClassicalBaseline.MODELS.keys():
            baseline = ClassicalBaseline(model_name)
            assert baseline.model_name == model_name
    
    def test_invalid_model_raises(self):
        """Test that invalid model name raises error."""
        with pytest.raises(ValueError):
            ClassicalBaseline("invalid_model")
    
    def test_fit_returns_time(self, sample_data):
        """Test that fit returns training time."""
        baseline = ClassicalBaseline("logistic_regression")
        
        train_time = baseline.fit(
            sample_data["X_train"],
            sample_data["y_train"]
        )
        
        assert isinstance(train_time, float)
        assert train_time > 0
    
    def test_predict_after_fit(self, sample_data):
        """Test prediction after fitting."""
        baseline = ClassicalBaseline("random_forest")
        baseline.fit(sample_data["X_train"], sample_data["y_train"])
        
        predictions = baseline.predict(sample_data["X_test"])
        
        assert len(predictions) == len(sample_data["X_test"])
        assert set(predictions).issubset({0, 1})
    
    def test_predict_before_fit_raises(self, sample_data):
        """Test that predict before fit raises error."""
        baseline = ClassicalBaseline("svm_linear")
        
        with pytest.raises(RuntimeError):
            baseline.predict(sample_data["X_test"])
    
    def test_evaluate_returns_result(self, sample_data):
        """Test that evaluate returns ModelResult."""
        baseline = ClassicalBaseline("knn")
        train_time = baseline.fit(sample_data["X_train"], sample_data["y_train"])
        
        result = baseline.evaluate(
            sample_data["X_test"],
            sample_data["y_test"],
            train_time
        )
        
        assert isinstance(result, ModelResult)
        assert 0 <= result.accuracy <= 1
        assert 0 <= result.f1 <= 1
        assert result.train_time == train_time
    
    def test_fit_evaluate_combined(self, sample_data):
        """Test fit_evaluate convenience method."""
        baseline = ClassicalBaseline("gradient_boosting")
        
        result = baseline.fit_evaluate(
            sample_data["X_train"],
            sample_data["y_train"],
            sample_data["X_test"],
            sample_data["y_test"]
        )
        
        assert isinstance(result, ModelResult)
        assert result.train_time > 0


class TestRunAllBaselines:
    """Tests for run_all_baselines function."""
    
    @pytest.fixture
    def sample_data(self):
        """Generate sample data for tests."""
        X, y = generate_synthetic_data(n_samples=300)
        loader = DataLoader()
        return loader.prepare_data(X, y, binary=True)
    
    def test_runs_specified_models(self, sample_data):
        """Test that specified models are run."""
        models = ["logistic_regression", "knn"]
        
        results = run_all_baselines(
            sample_data["X_train"],
            sample_data["y_train"],
            sample_data["X_test"],
            sample_data["y_test"],
            models=models
        )
        
        assert len(results) == 2
        result_names = {r.name for r in results}
        assert result_names == set(models)
    
    def test_results_have_metrics(self, sample_data):
        """Test that all results have required metrics."""
        results = run_all_baselines(
            sample_data["X_train"],
            sample_data["y_train"],
            sample_data["X_test"],
            sample_data["y_test"],
            models=["random_forest"]
        )
        
        result = results[0]
        required_attrs = [
            "accuracy", "precision", "recall", "f1",
            "roc_auc", "train_time", "confusion_matrix"
        ]
        
        for attr in required_attrs:
            assert hasattr(result, attr), f"Missing attribute: {attr}"


class TestModelResult:
    """Tests for ModelResult dataclass."""
    
    def test_to_dict(self):
        """Test to_dict conversion."""
        result = ModelResult(
            name="test",
            accuracy=0.9,
            precision=0.85,
            recall=0.88,
            f1=0.86,
            roc_auc=0.92,
            train_time=1.5,
            inference_time=0.1,
            confusion_matrix=np.array([[10, 2], [3, 15]])
        )
        
        d = result.to_dict()
        
        assert d["name"] == "test"
        assert d["accuracy"] == 0.9
        assert "confusion_matrix" not in d  # Not included in dict


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
