"""
Central predictor for QZero using QSVM and QI-VAE models.
Provides a unified interface for anomaly detection.
"""

import numpy as np
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, Literal
import pickle
import time

from ..preprocessing.data_loader import DataLoader, generate_synthetic_data
from ..preprocessing.feature_engineering import FeatureEngineer
from ..quantum.qsvm import QSVM, QSVMConfig
from ..quantum.qivae import QIVAE, QIVAEConfig
from ..classical.baseline import ClassicalBaseline
from ..evaluation.metrics import (
    evaluate_model,
    evaluate_zero_day_detection,
    print_evaluation_report,
)


class QZeroPredictor:
    """
    Central predictor for QZero zero-day detection system.

    This class provides a unified interface that:
    1. Preprocesses input data
    2. Runs multiple models (QSVM, QI-VAE, classical baselines)
    3. Aggregates results
    4. Returns anomaly scores and predictions

    Usage:
        predictor = QZeroPredictor()
        predictor.train(X_train, y_train)

        # Single prediction
        result = predictor.predict(X_test)

        # Get anomaly score
        score = predictor.get_anomaly_score(X_sample)

        # Get model comparison
        comparison = predictor.compare_models(X_test, y_test)
    """

    def __init__(
        self,
        data_dir: Optional[Path] = None,
        n_qubits: int = 4,
        use_qsvm: bool = True,
        use_qivae: bool = True,
        use_classical: bool = True,
        classical_models: Optional[list] = None,
        random_state: int = 42,
    ):
        """
        Initialize QZero predictor.

        Args:
            data_dir: Path to data directory
            n_qubits: Number of qubits for quantum models
            use_qsvm: Whether to use QSVM
            use_qivae: Whether to use QI-VAE
            use_classical: Whether to use classical models
            classical_models: List of classical model names to use
            random_state: Random seed
        """
        self.data_dir = data_dir or (Path(__file__).parent.parent / "data")
        self.n_qubits = n_qubits
        self.use_qsvm = use_qsvm
        self.use_qivae = use_qivae
        self.use_classical = use_classical
        self.classical_models = classical_models or [
            "random_forest",
            "svm_rbf",
            "gradient_boosting",
        ]
        self.random_state = random_state

        # Data storage
        self.X_train = None
        self.y_train = None
        self.X_test = None
        self.y_test = None
        self.scaler = None
        self.feature_engineer = None

        # Model storage
        self.qsvm_model: Optional[QSVM] = None
        self.qivae_model: Optional[QIVAE] = None
        self.classical_models_dict: Dict[str, ClassicalBaseline] = {}

        # Training metadata
        self.training_info = {}
        self.model_fitted = False

    def _load_or_generate_data(
        self,
        n_samples: int = 10000,
        use_real_data: bool = False,
        filename: str = "final(2).csv",
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Load data or generate synthetic data.

        Args:
            n_samples: Number of samples for synthetic data
            use_real_data: Whether to use real UGRansome dataset
            filename: UGRansome filename

        Returns:
            Tuple of (features, labels)
        """
        if use_real_data:
            try:
                loader = DataLoader(self.data_dir)
                X, y = loader.load_ugransome(filename)
                print(f"Loaded real dataset: {X.shape[0]} samples, {X.shape[1]} features")
                return X.values, y.values
            except Exception as e:
                print(f"Could not load real dataset ({e}), falling back to synthetic")
                use_real_data = False

        print(f"Generating synthetic data: {n_samples} samples")
        X, y = generate_synthetic_data(
            n_samples=n_samples,
            random_state=self.random_state,
        )
        return X.values, y.values

    def prepare_data(
        self,
        X: np.ndarray,
        y: np.ndarray,
        test_size: float = 0.2,
        val_size: float = 0.1,
        binary: bool = True,
    ) -> Dict[str, Any]:
        """
        Prepare data for training.

        Args:
            X: Features
            y: Labels
            test_size: Test set ratio
            val_size: Validation set ratio
            binary: Convert to binary classification

        Returns:
            Dictionary with train/val/test splits
        """
        print("Preparing data...")
        loader = DataLoader(self.data_dir)

        # Store original data
        self.X_train = X
        self.y_train = y

        # Prepare splits
        data = loader.prepare_data(X, y, test_size=test_size, val_size=val_size, binary=binary)

        # Store test data
        self.X_test = data["X_test"]
        self.y_test = data["y_test"]

        # Scale features
        self.scaler = data["scaler"]

        # Prepare feature engineer
        self.feature_engineer = FeatureEngineer(
            n_qubits=self.n_qubits,
            reduction_method="pca",
        )

        return data

    def train_qsvm(
        self,
        X_train_q: np.ndarray,
        y_train: np.ndarray,
        max_samples: int = 200,
    ) -> Optional[Any]:
        """
        Train QSVM model.

        Args:
            X_train_q: Quantum-ready features
            y_train: Training labels
            max_samples: Maximum samples for quantum training

        Returns:
            QSVMResult or None if Qiskit not available
        """
        if not self.use_qsvm:
            return None

        print("Training QSVM...")
        config = QSVMConfig(
            n_qubits=self.n_qubits,
            max_samples_quantum=max_samples,
            use_classical_fallback=True,
            random_state=self.random_state,
        )
        self.qsvm_model = QSVM(config)

        result = self.qsvm_model.fit_evaluate(
            X_train_q[:max_samples],
            y_train[:max_samples],
            self.X_test_q,
            self.y_test,
        )

        self.qsvm_result = result
        print(f"QSVM trained: Accuracy={result.accuracy:.4f}, F1={result.f1_score:.4f}")
        return result

    def train_qivae(
        self,
        X_train_normal: np.ndarray,
        epochs: int = 30,
    ) -> Optional[Any]:
        """
        Train QI-VAE model for anomaly detection.

        Args:
            X_train_normal: Training data (normal samples only)
            epochs: Number of training epochs

        Returns:
            QIVAEResult or None if PyTorch not available
        """
        if not self.use_qivae:
            return None

        print("Training QI-VAE...")
        config = QIVAEConfig(
            input_dim=self.X_train.shape[1],
            latent_dim=4,
            hidden_dims=(64, 32),
            epochs=epochs,
            batch_size=32,
            beta=1.0,
            random_state=self.random_state,
        )
        self.qivae_model = QIVAE(config)

        result = self.qivae_model.fit_evaluate(
            X_train_normal,
            self.X_test,
            self.y_test,
            verbose=False,
        )

        self.qivae_result = result
        print(f"QI-VAE trained: Accuracy={result.accuracy:.4f}, F1={result.f1_score:.4f}")
        return result

    def train_classical_baselines(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
    ) -> Dict[str, Any]:
        """
        Train classical baseline models.

        Args:
            X_train: Training features
            y_train: Training labels

        Returns:
            Dictionary of model results
        """
        if not self.use_classical:
            return {}

        print("Training classical baselines...")
        results = {}

        for model_name in self.classical_models:
            try:
                baseline = ClassicalBaseline(model_name)
                result = baseline.fit_evaluate(X_train, y_train, self.X_test, self.y_test)
                self.classical_models_dict[model_name] = baseline
                results[model_name] = result
                print(f"  {model_name}: Acc={result.accuracy:.4f}, F1={result.f1:.4f}")
            except Exception as e:
                print(f"  {model_name} failed: {e}")

        self.classical_results = results
        return results

    def train_all(
        self,
        n_samples: int = 5000,
        use_real_data: bool = False,
        use_qsvm: bool = True,
        use_qivae: bool = True,
        use_classical: bool = True,
        classical_models: Optional[list] = None,
    ) -> Dict[str, Any]:
        """
        Complete training pipeline.

        Args:
            n_samples: Number of samples (if synthetic)
            use_real_data: Whether to use real UGRansome dataset
            use_qsvm: Train QSVM
            use_qivae: Train QI-VAE
            use_classical: Train classical models
            classical_models: List of classical model names

        Returns:
            Training summary
        """
        print("=" * 70)
        print("QZero - Complete Training Pipeline")
        print("=" * 70)

        start_time = time.time()

        # Load data
        X, y = self._load_or_generate_data(n_samples=n_samples, use_real_data=use_real_data)

        # Prepare data
        data = self.prepare_data(X, y, binary=True)

        # Prepare quantum features
        X_train_q = self.feature_engineer.fit_transform(data["X_train"], data["y_train"])
        self.X_test_q = self.feature_engineer.transform(data["X_test"])

        # Train models
        qsvm_result = self.train_qsvm(X_train_q, data["y_train"]) if use_qsvm else None
        qivae_result = self.train_qivae(data["X_train"][data["y_train"] == 0]) if use_qivae else None
        classical_results = self.train_classical_baselines(data["X_train"], data["y_train"]) if use_classical else {}

        # Compile results
        training_time = time.time() - start_time
        self.training_info = {
            "training_time": training_time,
            "n_samples": len(X),
            "n_features": X.shape[1],
            "n_classes": len(np.unique(y)),
            "use_qsvm": use_qsvm,
            "use_qivae": use_qivae,
            "use_classical": use_classical,
        }

        self.model_fitted = True

        summary = {
            "training_time": training_time,
            "qsvm": qsvm_result.__dict__ if qsvm_result else None,
            "qivae": qivae_result.__dict__ if qivae_result else None,
            "classical": {
                name: r.__dict__ for name, r in classical_results.items()
            } if classical_results else None,
        }

        print("\n" + "=" * 70)
        print("Training Complete!")
        print("=" * 70)
        print(f"Total training time: {training_time:.2f}s")
        print("=" * 70)

        return summary

    def predict(
        self,
        X: np.ndarray,
        method: Optional[Literal["qsvm", "qivae", "best"]] = None,
    ) -> np.ndarray:
        """
        Make predictions on new data.

        Args:
            X: Input features (must be same shape as training data)
            method: Prediction method ("qsvm", "qivae", "best") or None for ensemble

        Returns:
            Predicted labels
        """
        if not self.model_fitted:
            raise RuntimeError("Model not trained. Call train_all() first.")

        if self.scaler is not None:
            X = self.scaler.transform(X)

        if method == "qsvm" and self.qsvm_model:
            return self.qsvm_model.predict(X)
        elif method == "qivae" and self.qivae_model:
            return self.qivae_model.predict(X)
        elif method == "best":
            # Prefer QI-VAE, then QSVM, then first classical model.
            # Fall back gracefully when result objects are absent (e.g. after load()).
            if self.qivae_model and (
                self.qivae_result is None or self.qivae_result.f1_score > 0
            ):
                return self.qivae_model.predict(X)
            elif self.qsvm_model and (
                self.qsvm_result is None or self.qsvm_result.f1_score > 0
            ):
                return self.qsvm_model.predict(X)
            elif self.classical_models_dict:
                return list(self.classical_models_dict.values())[0].predict(X)
            else:
                raise RuntimeError("No models available for prediction")
        else:
            # Ensemble vote
            predictions = []
            if self.qsvm_model:
                predictions.append(self.qsvm_model.predict(X))
            if self.qivae_model:
                predictions.append(self.qivae_model.predict(X))
            if self.classical_models_dict:
                predictions.append(np.mean([m.predict(X) for m in self.classical_models_dict.values()], axis=0))

            if predictions:
                return np.mean(predictions, axis=0).round().astype(int)
            else:
                raise RuntimeError("No models available for prediction")

    def get_anomaly_score(
        self,
        X: np.ndarray,
        method: str = "qivae",
    ) -> np.ndarray:
        """
        Get anomaly scores for new data.

        Args:
            X: Input features
            method: Method to use ("qivae", "qsvm")

        Returns:
            Anomaly scores (0-1)
        """
        if not self.model_fitted:
            raise RuntimeError("Model not trained. Call train_all() first.")

        if self.scaler is not None:
            X = self.scaler.transform(X)

        if method == "qivae" and self.qivae_model:
            return self.qivae_model.reconstruction_errors(X)
        elif method == "qsvm" and self.qsvm_model:
            # Use probability of class 1 (anomaly)
            try:
                proba = self.qsvm_model.model.predict_proba(X)
                if proba.shape[1] == 2:
                    return proba[:, 1]
                else:
                    return proba[:, 1]  # Anomaly class
            except:
                # Fallback to predictions
                return self.qsvm_model.predict(X).astype(float)
        else:
            raise ValueError(f"Unknown method: {method}")
    def get_threshold(self) -> float:
        """
        Get anomaly threshold from QIVAE model.

        Returns:
            Threshold value for anomaly detection.
        """
        if self.qivae_model:
            return self.qivae_model.anomaly_threshold
        return 0.5  # Default fallback

    def evaluate(self) -> Dict[str, Any]:
        """
        Evaluate all models on test data.

        Returns:
            Dictionary of evaluation results
        """
        if not self.model_fitted:
            raise RuntimeError("Model not trained. Call train_all() first.")

        results = {}

        # QSVM evaluation
        if self.qsvm_result:
            zd_metrics = evaluate_zero_day_detection(
                self.y_test,
                self.qsvm_model.predict(self.X_test_q),
            )
            results["qsvm"] = {
                **self.qsvm_result.__dict__,
                "zero_day_detection": zd_metrics,
            }

        # QI-VAE evaluation
        if self.qivae_result:
            zd_metrics = evaluate_zero_day_detection(
                self.y_test,
                self.qivae_model.predict(self.X_test),
            )
            results["qivae"] = {
                **self.qivae_result.__dict__,
                "zero_day_detection": zd_metrics,
            }

        # Classical evaluation
        if self.classical_results:
            for name, result in self.classical_results.items():
                zd_metrics = evaluate_zero_day_detection(
                    self.y_test,
                    self.classical_models_dict[name].predict(self.X_test),
                )
                results[name] = {
                    **result.__dict__,
                    "zero_day_detection": zd_metrics,
                }

        return results

    def compare_models(self) -> str:
        """
        Compare all models and return formatted comparison.

        Returns:
            Formatted comparison string
        """
        if not self.model_fitted:
            raise RuntimeError("Model not trained. Call train_all() first.")

        comparison = []
        comparison.append("=" * 70)
        comparison.append("QZero Model Comparison")
        comparison.append("=" * 70)
        comparison.append(f"{'Model':<25} {'Accuracy':>12} {'Precision':>12} {'Recall':>12} {'F1':>12} {'Zero-Day %':>12}")
        comparison.append("-" * 70)

        # QSVM
        if self.qsvm_result:
            zd_pct = (
                self.qsvm_result.zero_day_detection_rate * 100
                if hasattr(self.qsvm_result, "zero_day_detection_rate")
                else self.qsvm_result.f1_score * 100
            )
            comparison.append(
                f"{'QSVM':<25} {self.qsvm_result.accuracy:>12.4f} {self.qsvm_result.precision:>12.4f} {self.qsvm_result.recall:>12.4f} {self.qsvm_result.f1_score:>12.4f} {zd_pct:>11.1f}%"
            )

        # QI-VAE
        if self.qivae_result:
            zd_pct = (
                self.qivae_result.zero_day_detection_rate * 100
                if hasattr(self.qivae_result, "zero_day_detection_rate")
                else self.qivae_result.f1_score * 100
            )
            comparison.append(
                f"{'QI-VAE':<25} {self.qivae_result.accuracy:>12.4f} {self.qivae_result.precision:>12.4f} {self.qivae_result.recall:>12.4f} {self.qivae_result.f1_score:>12.4f} {zd_pct:>11.1f}%"
            )

        # Classical
        for name, result in self.classical_results.items():
            zd_pct = (
                result.zero_day_detection_rate * 100
                if hasattr(result, "zero_day_detection_rate")
                else result.f1_score * 100
            )
            comparison.append(
                f"{'Classical':<25} {result.accuracy:>12.4f} {result.precision:>12.4f} {result.recall:>12.4f} {result.f1:>12.4f} {zd_pct:>11.1f}%"
            )

        comparison.append("=" * 70)

        return "\n".join(comparison)

    def save(self, path: Path):
        """
        Save trained models and data.

        Args:
            path: Directory to save models
        """
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)

        # Save scaler and feature engineer
        import pickle
        pickle.dump(self.scaler, open(path / "scaler.pkl", "wb"))
        pickle.dump(self.feature_engineer, open(path / "feature_engineer.pkl", "wb"))

        # Save models
        if self.qsvm_model:
            pickle.dump(self.qsvm_model, open(path / "qsvm.pkl", "wb"))

        if self.qivae_model:
            pickle.dump(self.qivae_model, open(path / "qivae.pkl", "wb"))

        if self.classical_models_dict:
            for name, model in self.classical_models_dict.items():
                pickle.dump(model, open(path / f"classical_{name}.pkl", "wb"))

        # Save evaluation results (so load() doesn't need test data to re-evaluate)
        import json
        results_to_save = {}
        if hasattr(self, "qsvm_result") and self.qsvm_result:
            results_to_save["qsvm"] = self.qsvm_result.to_dict()
        if hasattr(self, "qivae_result") and self.qivae_result:
            results_to_save["qivae"] = self.qivae_result.to_dict()
        if hasattr(self, "classical_results"):
            results_to_save["classical"] = {
                k: v.to_dict() for k, v in self.classical_results.items()
            }

        # Atomic-ish write: write to temp then rename so a crash never leaves a
        # truncated/corrupt results.json that breaks load() on the next boot.
        def _atomic_json_write(target: Path, obj) -> None:
            tmp = path.with_name(target.name + ".tmp")
            with open(tmp, "w") as f:
                json.dump(obj, f, indent=2)
            tmp.replace(target)

        _atomic_json_write(path / "results.json", results_to_save)
        _atomic_json_write(path / "training_info.json", self.training_info)

        print(f"Models saved to {path}")

    def load(self, path: Path):
        """
        Load trained models and data.

        Args:
            path: Directory to load models from
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Model directory not found: {path}")

        import pickle

        # Load scaler and feature engineer
        self.scaler = pickle.load(open(path / "scaler.pkl", "rb"))
        self.feature_engineer = pickle.load(open(path / "feature_engineer.pkl", "rb"))

        import json

        # Load models (no re-evaluation — test data is not available at load time)
        if (path / "qsvm.pkl").exists():
            self.qsvm_model = pickle.load(open(path / "qsvm.pkl", "rb"))
            self.qsvm_result = None

        if (path / "qivae.pkl").exists():
            self.qivae_model = pickle.load(open(path / "qivae.pkl", "rb"))
            self.qivae_result = None

        # Restore saved evaluation results (produced during save())
        if (path / "results.json").exists():
            try:
                with open(path / "results.json") as f:
                    saved = json.load(f)
            except Exception:
                saved = {}
                print("Warning: results.json corrupt — ignoring saved metrics.")

            if "qsvm" in saved and self.qsvm_model:
                from ..quantum.qsvm import QSVMResult, QSVMConfig
                d = saved["qsvm"]
                self.qsvm_result = QSVMResult(
                    accuracy=d.get("accuracy", 0.0),
                    f1_score=d.get("f1_score", 0.0),
                    train_time=d.get("train_time", 0.0),
                    kernel_computation_time=d.get("kernel_computation_time", 0.0),
                    n_support_vectors=d.get("n_support_vectors", 0),
                    used_quantum=d.get("used_quantum", False),
                )

            if "qivae" in saved and self.qivae_model:
                import numpy as np
                from ..quantum.qivae import QIVAEResult, QIVAEConfig
                d = saved["qivae"]
                self.qivae_result = QIVAEResult(
                    train_loss=d.get("train_loss", 0.0),
                    val_loss=d.get("val_loss", 0.0),
                    reconstruction_errors=np.array([]),
                    anomaly_threshold=d.get("anomaly_threshold", 0.5),
                    accuracy=d.get("accuracy", 0.0),
                    precision=d.get("precision", 0.0),
                    recall=d.get("recall", 0.0),
                    f1_score=d.get("f1_score", 0.0),
                    train_time=d.get("train_time", 0.0),
                )

        # Restore classical model results
        self.classical_results = {}

        if (path / "training_info.json").exists():
            with open(path / "training_info.json") as f:
                self.training_info = json.load(f)

        self.model_fitted = True

        print(f"Models loaded from {path}")

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"QZeroPredictor(n_qubits={self.n_qubits}, "
            f"qsvm={'enabled' if self.use_qsvm else 'disabled'}, "
            f"qivae={'enabled' if self.use_qivae else 'disabled'}, "
            f"classical={'enabled' if self.use_classical else 'disabled'})"
        )