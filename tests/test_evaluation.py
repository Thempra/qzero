"""
Tests for evaluation metrics module.
"""

import pytest
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from qzero.evaluation.metrics import (
    evaluate_model,
    evaluate_zero_day_detection,
    calculate_quantum_advantage,
    EvaluationResult,
)


class TestEvaluateModel:
    """Tests for evaluate_model function."""
    
    def test_perfect_predictions(self):
        """Test metrics with perfect predictions."""
        y_true = np.array([0, 0, 0, 1, 1, 1])
        y_pred = np.array([0, 0, 0, 1, 1, 1])
        
        result = evaluate_model(y_true, y_pred)
        
        assert result.accuracy == 1.0
        assert result.precision == 1.0
        assert result.recall == 1.0
        assert result.f1 == 1.0
        assert result.false_positive_rate == 0.0
        assert result.false_negative_rate == 0.0
    
    def test_worst_predictions(self):
        """Test metrics with completely wrong predictions."""
        y_true = np.array([0, 0, 0, 1, 1, 1])
        y_pred = np.array([1, 1, 1, 0, 0, 0])  # All wrong
        
        result = evaluate_model(y_true, y_pred)
        
        assert result.accuracy == 0.0
        assert result.false_positive_rate == 1.0
        assert result.false_negative_rate == 1.0
    
    def test_partial_predictions(self):
        """Test metrics with mixed results."""
        y_true = np.array([0, 0, 0, 0, 1, 1, 1, 1])
        y_pred = np.array([0, 0, 1, 1, 0, 0, 1, 1])  # 50% correct
        
        result = evaluate_model(y_true, y_pred)
        
        assert result.accuracy == 0.5
        assert 0 < result.precision < 1
        assert 0 < result.recall < 1
    
    def test_confusion_matrix_shape(self):
        """Test that confusion matrix has correct shape."""
        y_true = np.array([0, 0, 1, 1, 2, 2])
        y_pred = np.array([0, 1, 1, 2, 2, 0])
        
        result = evaluate_model(y_true, y_pred)
        
        assert result.confusion_matrix.shape == (3, 3)
    
    def test_with_probabilities(self):
        """Test that ROC-AUC is computed when probabilities provided."""
        np.random.seed(42)
        n = 100
        y_true = np.random.randint(0, 2, n)
        y_proba = np.zeros((n, 2))
        y_proba[np.arange(n), y_true] = 0.8
        y_proba[np.arange(n), 1 - y_true] = 0.2
        y_pred = y_true.copy()  # Perfect predictions
        
        result = evaluate_model(y_true, y_pred, y_proba)
        
        assert result.roc_auc > 0.9
    
    def test_result_to_dict(self):
        """Test EvaluationResult.to_dict method."""
        y_true = np.array([0, 0, 1, 1])
        y_pred = np.array([0, 0, 1, 1])
        
        result = evaluate_model(y_true, y_pred)
        result_dict = result.to_dict()
        
        assert "accuracy" in result_dict
        assert "f1" in result_dict
        assert "false_positive_rate" in result_dict


class TestEvaluateZeroDayDetection:
    """Tests for zero-day specific evaluation."""
    
    def test_perfect_zero_day_detection(self):
        """Test when all zero-days are detected."""
        y_true = np.array([0, 0, 0, 1, 1, 1])  # 1 = zero-day
        y_pred = np.array([0, 0, 0, 1, 1, 1])  # All correct
        
        result = evaluate_zero_day_detection(y_true, y_pred)
        
        assert result["zero_day_detection_rate"] == 1.0
        assert result["zero_day_samples"] == 3
        assert result["zero_day_detected"] == 3
    
    def test_no_zero_day_detected(self):
        """Test when no zero-days are detected."""
        y_true = np.array([0, 0, 0, 1, 1, 1])
        y_pred = np.array([0, 0, 0, 0, 0, 0])  # Missed all zero-days
        
        result = evaluate_zero_day_detection(y_true, y_pred)
        
        assert result["zero_day_detection_rate"] == 0.0
        assert result["zero_day_detected"] == 0
    
    def test_no_zero_days_in_data(self):
        """Test when no zero-days exist in the data."""
        y_true = np.array([0, 0, 0, 0])  # No zero-days
        y_pred = np.array([0, 0, 1, 1])
        
        result = evaluate_zero_day_detection(y_true, y_pred)
        
        assert result["zero_day_detection_rate"] is None
        assert result["zero_day_samples"] == 0
    
    def test_partial_zero_day_detection(self):
        """Test partial detection."""
        y_true = np.array([0, 0, 1, 1, 1, 1])
        y_pred = np.array([0, 0, 1, 1, 0, 0])  # Detected 2/4
        
        result = evaluate_zero_day_detection(y_true, y_pred)
        
        assert result["zero_day_detection_rate"] == 0.5
        assert result["zero_day_detected"] == 2
    
    def test_multiclass_detection(self):
        """Test with multiclass predictions."""
        # 0=normal, 1=anomaly/zero-day, 2=signature
        y_true = np.array([0, 0, 1, 1, 2, 2])
        y_pred = np.array([0, 2, 1, 2, 0, 2])  # Detected 1/2 zero-days
        
        result = evaluate_zero_day_detection(y_true, y_pred, zero_day_label=1)
        
        assert result["zero_day_samples"] == 2
        # Both zero-days detected as attack (1 as 1, 1 as 2)
        assert result["zero_day_detection_rate"] == 1.0  # Both predicted as non-normal


class TestQuantumAdvantage:
    """Tests for quantum advantage calculation."""
    
    def test_positive_advantage(self):
        """Test when quantum beats classical."""
        quantum_metrics = {"accuracy": 0.95, "f1": 0.90}
        classical_metrics = {"accuracy": 0.85, "f1": 0.80}
        
        advantage = calculate_quantum_advantage(quantum_metrics, classical_metrics)
        
        assert advantage["accuracy_advantage_pct"] > 0
        assert advantage["f1_advantage_pct"] > 0
    
    def test_negative_advantage(self):
        """Test when classical beats quantum."""
        quantum_metrics = {"accuracy": 0.80, "f1": 0.75}
        classical_metrics = {"accuracy": 0.90, "f1": 0.85}
        
        advantage = calculate_quantum_advantage(quantum_metrics, classical_metrics)
        
        assert advantage["accuracy_advantage_pct"] < 0
        assert advantage["f1_advantage_pct"] < 0
    
    def test_equal_performance(self):
        """Test when both perform equally."""
        metrics = {"accuracy": 0.85, "f1": 0.80}
        
        advantage = calculate_quantum_advantage(metrics, metrics)
        
        assert advantage["accuracy_advantage_pct"] == 0.0
        assert advantage["f1_advantage_pct"] == 0.0
    
    def test_percentage_calculation(self):
        """Test that advantage is calculated as percentage correctly."""
        quantum_metrics = {"accuracy": 0.90}
        classical_metrics = {"accuracy": 0.80}
        
        advantage = calculate_quantum_advantage(quantum_metrics, classical_metrics)
        
        # (0.90 - 0.80) / 0.80 * 100 = 12.5%
        expected = (0.90 - 0.80) / 0.80 * 100
        assert abs(advantage["accuracy_advantage_pct"] - expected) < 0.01


class TestEvaluationIntegration:
    """Integration tests using actual model predictions."""
    
    def test_with_random_forest(self, small_dataset):
        """Test evaluation with actual Random Forest predictions."""
        from sklearn.ensemble import RandomForestClassifier
        
        clf = RandomForestClassifier(n_estimators=50, random_state=42)
        clf.fit(small_dataset["X_train"], small_dataset["y_train"])
        
        y_pred = clf.predict(small_dataset["X_test"])
        y_proba = clf.predict_proba(small_dataset["X_test"])
        
        result = evaluate_model(
            small_dataset["y_test"],
            y_pred,
            y_proba
        )
        
        # Should achieve decent performance on easy synthetic data
        assert result.accuracy > 0.7
        assert result.f1 > 0.6
        
        # Zero-day detection
        zd_result = evaluate_zero_day_detection(small_dataset["y_test"], y_pred)
        
        if zd_result["zero_day_samples"] > 0:
            assert 0 <= zd_result["zero_day_detection_rate"] <= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
