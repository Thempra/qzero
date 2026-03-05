"""
Evaluation metrics for zero-day detection.
"""

import numpy as np
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
    precision_recall_curve,
    average_precision_score,
)


@dataclass
class EvaluationResult:
    """Comprehensive evaluation results."""
    accuracy: float
    precision: float
    recall: float
    f1: float
    roc_auc: float
    average_precision: float
    confusion_matrix: np.ndarray
    false_positive_rate: float
    false_negative_rate: float
    zero_day_detection_rate: Optional[float] = None
    
    def to_dict(self) -> Dict[str, float]:
        return {
            "accuracy": self.accuracy,
            "precision": self.precision,
            "recall": self.recall,
            "f1": self.f1,
            "roc_auc": self.roc_auc,
            "average_precision": self.average_precision,
            "false_positive_rate": self.false_positive_rate,
            "false_negative_rate": self.false_negative_rate,
            "zero_day_detection_rate": self.zero_day_detection_rate,
        }


def evaluate_model(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_proba: Optional[np.ndarray] = None,
) -> EvaluationResult:
    """
    Comprehensive model evaluation.
    
    Args:
        y_true: True labels
        y_pred: Predicted labels
        y_proba: Prediction probabilities (for ROC/PR curves)
    
    Returns:
        EvaluationResult with all metrics
    """
    cm = confusion_matrix(y_true, y_pred)
    
    # Calculate FPR and FNR from confusion matrix
    # For binary: [[TN, FP], [FN, TP]]
    if cm.shape == (2, 2):
        tn, fp, fn, tp = cm.ravel()
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        fnr = fn / (fn + tp) if (fn + tp) > 0 else 0.0
    else:
        # Multi-class: average rates
        fpr = 0.0
        fnr = 0.0
        for i in range(len(cm)):
            fp_i = cm[:, i].sum() - cm[i, i]
            tn_i = cm.sum() - cm[i, :].sum() - cm[:, i].sum() + cm[i, i]
            fn_i = cm[i, :].sum() - cm[i, i]
            tp_i = cm[i, i]
            fpr += fp_i / (fp_i + tn_i) if (fp_i + tn_i) > 0 else 0
            fnr += fn_i / (fn_i + tp_i) if (fn_i + tp_i) > 0 else 0
        fpr /= len(cm)
        fnr /= len(cm)
    
    # ROC-AUC and Average Precision
    roc_auc = 0.0
    avg_precision = 0.0
    if y_proba is not None:
        try:
            if y_proba.ndim == 2 and y_proba.shape[1] == 2:
                roc_auc = roc_auc_score(y_true, y_proba[:, 1])
                avg_precision = average_precision_score(y_true, y_proba[:, 1])
            elif y_proba.ndim == 1:
                roc_auc = roc_auc_score(y_true, y_proba)
                avg_precision = average_precision_score(y_true, y_proba)
            else:
                roc_auc = roc_auc_score(y_true, y_proba, multi_class="ovr")
        except Exception:
            pass
    
    return EvaluationResult(
        accuracy=accuracy_score(y_true, y_pred),
        precision=precision_score(y_true, y_pred, average="weighted", zero_division=0),
        recall=recall_score(y_true, y_pred, average="weighted", zero_division=0),
        f1=f1_score(y_true, y_pred, average="weighted", zero_division=0),
        roc_auc=roc_auc,
        average_precision=avg_precision,
        confusion_matrix=cm,
        false_positive_rate=fpr,
        false_negative_rate=fnr,
    )


def evaluate_zero_day_detection(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    zero_day_label: int = 1,
) -> Dict[str, float]:
    """
    Evaluate specifically for zero-day (anomaly) detection.
    
    Zero-day attacks are anomalies - previously unseen patterns.
    This function measures how well the model detects these.
    
    Args:
        y_true: True labels (0=normal, 1=zero-day/anomaly, 2+=known attacks)
        y_pred: Predicted labels
        zero_day_label: Label for zero-day attacks
    
    Returns:
        Dictionary with zero-day specific metrics
    """
    # Filter to only zero-day samples
    zero_day_mask = y_true == zero_day_label
    
    if not zero_day_mask.any():
        return {
            "zero_day_detection_rate": None,
            "zero_day_precision": None,
            "zero_day_samples": 0,
        }
    
    n_zero_day = zero_day_mask.sum()
    
    # Zero-day detection rate (recall for anomalies)
    # True Positives: predicted as attack when actually zero-day
    # For binary case: y_pred == 1 and y_true == 1
    if np.unique(y_pred).max() <= 1:
        # Binary classification
        detected = ((y_pred == 1) & zero_day_mask).sum()
    else:
        # Multi-class: detected if predicted as any attack (not normal)
        detected = ((y_pred != 0) & zero_day_mask).sum()
    
    detection_rate = detected / n_zero_day
    
    # Zero-day precision: of all predicted anomalies, how many were zero-day
    predicted_attacks = y_pred != 0
    if predicted_attacks.sum() > 0:
        precision = ((y_true == zero_day_label) & predicted_attacks).sum() / predicted_attacks.sum()
    else:
        precision = 0.0
    
    return {
        "zero_day_detection_rate": detection_rate,
        "zero_day_precision": precision,
        "zero_day_samples": int(n_zero_day),
        "zero_day_detected": int(detected),
    }


def print_evaluation_report(
    result: EvaluationResult,
    model_name: str = "Model",
    zero_day_metrics: Optional[Dict[str, float]] = None,
) -> None:
    """
    Print formatted evaluation report.
    
    Args:
        result: Evaluation result
        model_name: Name of the model
        zero_day_metrics: Optional zero-day specific metrics
    """
    print("\n" + "=" * 60)
    print(f"EVALUATION REPORT: {model_name}")
    print("=" * 60)
    
    print("\n📊 General Metrics:")
    print(f"  Accuracy:           {result.accuracy:.4f}")
    print(f"  Precision:          {result.precision:.4f}")
    print(f"  Recall:             {result.recall:.4f}")
    print(f"  F1 Score:           {result.f1:.4f}")
    print(f"  ROC-AUC:            {result.roc_auc:.4f}")
    print(f"  Average Precision:  {result.average_precision:.4f}")
    
    print("\n⚠️  Error Rates:")
    print(f"  False Positive Rate: {result.false_positive_rate:.4f}")
    print(f"  False Negative Rate: {result.false_negative_rate:.4f}")
    
    print("\n📈 Confusion Matrix:")
    print(result.confusion_matrix)
    
    if zero_day_metrics and zero_day_metrics.get("zero_day_detection_rate") is not None:
        print("\n🔍 Zero-Day Detection:")
        print(f"  Detection Rate:     {zero_day_metrics['zero_day_detection_rate']:.4f}")
        print(f"  Zero-Day Precision: {zero_day_metrics['zero_day_precision']:.4f}")
        print(f"  Samples:            {zero_day_metrics['zero_day_samples']}")
        print(f"  Detected:           {zero_day_metrics['zero_day_detected']}")
    
    print("\n" + "=" * 60)


def calculate_quantum_advantage(
    quantum_metrics: Dict[str, float],
    classical_metrics: Dict[str, float],
) -> Dict[str, float]:
    """
    Calculate quantum advantage over classical baseline.
    
    Args:
        quantum_metrics: Metrics from quantum model
        classical_metrics: Metrics from classical model
    
    Returns:
        Dictionary with advantage percentages
    """
    advantages = {}
    
    for key in ["accuracy", "f1", "zero_day_detection_rate"]:
        q_val = quantum_metrics.get(key, 0)
        c_val = classical_metrics.get(key, 0)
        
        if c_val > 0 and q_val is not None:
            advantage = (q_val - c_val) / c_val * 100
            advantages[f"{key}_advantage_pct"] = advantage
    
    return advantages


if __name__ == "__main__":
    # Test evaluation
    np.random.seed(42)
    
    # Simulate predictions
    n = 1000
    y_true = np.random.choice([0, 1, 2], n, p=[0.6, 0.15, 0.25])
    y_pred = y_true.copy()
    # Add some errors
    errors = np.random.choice(n, int(n * 0.1), replace=False)
    y_pred[errors] = np.random.choice([0, 1, 2], len(errors))
    
    y_proba = np.zeros((n, 3))
    for i in range(n):
        y_proba[i, y_pred[i]] = 0.8
        y_proba[i] = y_proba[i] / y_proba[i].sum()
    
    # Evaluate
    result = evaluate_model(y_true, y_pred, y_proba)
    zd_metrics = evaluate_zero_day_detection(y_true, y_pred)
    
    print_evaluation_report(result, "Test Model", zd_metrics)
