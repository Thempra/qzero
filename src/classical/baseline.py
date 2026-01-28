"""
Classical ML baselines for zero-day detection.
Compare quantum approaches against these.
"""

import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
import time

from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
    classification_report,
)


@dataclass
class ModelResult:
    """Results from model training and evaluation."""
    name: str
    accuracy: float
    precision: float
    recall: float
    f1: float
    roc_auc: float
    train_time: float
    inference_time: float
    confusion_matrix: np.ndarray
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "accuracy": self.accuracy,
            "precision": self.precision,
            "recall": self.recall,
            "f1": self.f1,
            "roc_auc": self.roc_auc,
            "train_time": self.train_time,
            "inference_time": self.inference_time,
        }


class ClassicalBaseline:
    """
    Classical ML baseline models for intrusion detection.
    """
    
    MODELS = {
        "svm_linear": lambda: SVC(kernel="linear", probability=True, random_state=42),
        "svm_rbf": lambda: SVC(kernel="rbf", probability=True, random_state=42),
        "random_forest": lambda: RandomForestClassifier(
            n_estimators=100, max_depth=10, random_state=42, n_jobs=-1
        ),
        "gradient_boosting": lambda: GradientBoostingClassifier(
            n_estimators=100, max_depth=5, random_state=42
        ),
        "logistic_regression": lambda: LogisticRegression(
            max_iter=1000, random_state=42, n_jobs=-1
        ),
        "knn": lambda: KNeighborsClassifier(n_neighbors=5, n_jobs=-1),
        "mlp": lambda: MLPClassifier(
            hidden_layer_sizes=(64, 32), max_iter=500, random_state=42
        ),
    }
    
    def __init__(self, model_name: str = "random_forest"):
        """
        Initialize baseline model.
        
        Args:
            model_name: One of the available model names
        """
        if model_name not in self.MODELS:
            raise ValueError(
                f"Unknown model: {model_name}. "
                f"Available: {list(self.MODELS.keys())}"
            )
        
        self.model_name = model_name
        self.model = self.MODELS[model_name]()
        self._is_fitted = False
    
    def fit(self, X_train: np.ndarray, y_train: np.ndarray) -> float:
        """
        Train the model.
        
        Args:
            X_train: Training features
            y_train: Training labels
        
        Returns:
            Training time in seconds
        """
        start = time.time()
        self.model.fit(X_train, y_train)
        train_time = time.time() - start
        self._is_fitted = True
        return train_time
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict labels."""
        if not self._is_fitted:
            raise RuntimeError("Model not fitted. Call fit() first.")
        return self.model.predict(X)
    
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Predict probabilities."""
        if not self._is_fitted:
            raise RuntimeError("Model not fitted. Call fit() first.")
        return self.model.predict_proba(X)
    
    def evaluate(
        self,
        X_test: np.ndarray,
        y_test: np.ndarray,
        train_time: float = 0.0,
    ) -> ModelResult:
        """
        Evaluate model on test set.
        
        Args:
            X_test: Test features
            y_test: Test labels
            train_time: Training time (for result)
        
        Returns:
            ModelResult with all metrics
        """
        start = time.time()
        y_pred = self.predict(X_test)
        inference_time = time.time() - start
        
        # Get probabilities for ROC-AUC
        try:
            y_proba = self.predict_proba(X_test)
            if y_proba.shape[1] == 2:
                roc_auc = roc_auc_score(y_test, y_proba[:, 1])
            else:
                roc_auc = roc_auc_score(y_test, y_proba, multi_class="ovr")
        except Exception:
            roc_auc = 0.0
        
        return ModelResult(
            name=self.model_name,
            accuracy=accuracy_score(y_test, y_pred),
            precision=precision_score(y_test, y_pred, average="weighted", zero_division=0),
            recall=recall_score(y_test, y_pred, average="weighted", zero_division=0),
            f1=f1_score(y_test, y_pred, average="weighted", zero_division=0),
            roc_auc=roc_auc,
            train_time=train_time,
            inference_time=inference_time,
            confusion_matrix=confusion_matrix(y_test, y_pred),
        )
    
    def fit_evaluate(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_test: np.ndarray,
        y_test: np.ndarray,
    ) -> ModelResult:
        """Fit and evaluate in one step."""
        train_time = self.fit(X_train, y_train)
        return self.evaluate(X_test, y_test, train_time)


def run_all_baselines(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
    models: Optional[List[str]] = None,
) -> List[ModelResult]:
    """
    Run all baseline models and return results.
    
    Args:
        X_train, y_train: Training data
        X_test, y_test: Test data
        models: List of model names to run (default: all)
    
    Returns:
        List of ModelResult for each model
    """
    if models is None:
        models = list(ClassicalBaseline.MODELS.keys())
    
    results = []
    for model_name in models:
        print(f"Training {model_name}...")
        try:
            baseline = ClassicalBaseline(model_name)
            result = baseline.fit_evaluate(X_train, y_train, X_test, y_test)
            results.append(result)
            print(f"  Accuracy: {result.accuracy:.4f}, F1: {result.f1:.4f}")
        except Exception as e:
            print(f"  Error: {e}")
    
    return results


def print_comparison_table(results: List[ModelResult]) -> None:
    """Print comparison table of all results."""
    print("\n" + "=" * 80)
    print("CLASSICAL BASELINE COMPARISON")
    print("=" * 80)
    print(f"{'Model':<25} {'Accuracy':>10} {'Precision':>10} {'Recall':>10} {'F1':>10} {'ROC-AUC':>10}")
    print("-" * 80)
    
    for r in sorted(results, key=lambda x: x.f1, reverse=True):
        print(f"{r.name:<25} {r.accuracy:>10.4f} {r.precision:>10.4f} {r.recall:>10.4f} {r.f1:>10.4f} {r.roc_auc:>10.4f}")
    
    print("=" * 80)


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(__file__).rsplit("/", 2)[0])
    
    from preprocessing.data_loader import generate_synthetic_data, DataLoader
    
    print("Generating synthetic data...")
    X, y = generate_synthetic_data(n_samples=5000)
    
    print("Preparing data...")
    loader = DataLoader()
    data = loader.prepare_data(X, y, binary=True)
    
    print("\nRunning all baselines...")
    results = run_all_baselines(
        data["X_train"], data["y_train"],
        data["X_test"], data["y_test"]
    )
    
    print_comparison_table(results)
