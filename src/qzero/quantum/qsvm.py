"""
Quantum Support Vector Machine for zero-day detection.
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Tuple
import time

try:
    from qiskit import QuantumCircuit
    from qiskit.circuit.library import RealAmplitudes
    from qiskit_machine_learning.kernels import FidelityQuantumKernel
    from qiskit_machine_learning.algorithms import QSVC
    QISKIT_ML_AVAILABLE = True
except ImportError:
    QISKIT_ML_AVAILABLE = False

from sklearn.svm import SVC
from sklearn.metrics import accuracy_score, f1_score

from .feature_maps import create_feature_map, FeatureMapType


def check_qiskit_ml():
    """Raise if Qiskit ML not available."""
    if not QISKIT_ML_AVAILABLE:
        raise ImportError(
            "Qiskit ML not installed. Run: pip install qiskit qiskit-machine-learning"
        )


@dataclass
class QSVMConfig:
    """Configuration for QSVM."""
    n_qubits: int = 4
    feature_map_type: FeatureMapType = FeatureMapType.ZZ
    feature_map_reps: int = 2
    entanglement: str = "linear"
    use_classical_fallback: bool = True
    max_samples_quantum: int = 500  # Limit for quantum kernel computation
    random_state: int = 42


@dataclass
class QSVMResult:
    """Results from QSVM training and evaluation."""
    accuracy: float
    f1_score: float
    train_time: float
    kernel_computation_time: float
    n_support_vectors: int
    used_quantum: bool
    config: QSVMConfig = field(default_factory=QSVMConfig)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "accuracy": self.accuracy,
            "f1_score": self.f1_score,
            "train_time": self.train_time,
            "kernel_computation_time": self.kernel_computation_time,
            "n_support_vectors": self.n_support_vectors,
            "used_quantum": self.used_quantum,
        }


class QSVM:
    """
    Quantum Support Vector Machine implementation.
    
    Uses quantum kernel methods for classification.
    Falls back to classical RBF kernel if Qiskit unavailable.
    """
    
    def __init__(self, config: Optional[QSVMConfig] = None):
        """
        Initialize QSVM.
        
        Args:
            config: QSVM configuration
        """
        self.config = config or QSVMConfig()
        self.feature_map = None
        self.kernel = None
        self.model = None
        self._is_fitted = False
        self._used_quantum = False
        self._kernel_time = 0.0
    
    def _build_quantum_kernel(self) -> None:
        """Build the quantum kernel using Qiskit."""
        check_qiskit_ml()
        
        # Create feature map
        self.feature_map = create_feature_map(
            n_qubits=self.config.n_qubits,
            feature_map_type=self.config.feature_map_type,
            reps=self.config.feature_map_reps,
            entanglement=self.config.entanglement,
        )
        
        # Create quantum kernel
        self.kernel = FidelityQuantumKernel(feature_map=self.feature_map)
        
        # Create QSVM classifier
        self.model = QSVC(quantum_kernel=self.kernel)
        self._used_quantum = True
    
    def _build_classical_fallback(self) -> None:
        """Build classical SVM as fallback."""
        # RBF kernel approximates quantum kernel behavior
        self.model = SVC(
            kernel="rbf",
            probability=True,
            random_state=self.config.random_state,
        )
        self._used_quantum = False
    
    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        sample_limit: Optional[int] = None,
    ) -> float:
        """
        Train the QSVM.
        
        Args:
            X_train: Training features (must match n_qubits dimensions)
            y_train: Training labels
            sample_limit: Max samples for quantum training
        
        Returns:
            Training time in seconds
        """
        # Validate dimensions
        if X_train.shape[1] != self.config.n_qubits:
            raise ValueError(
                f"Feature dimensions ({X_train.shape[1]}) must match "
                f"n_qubits ({self.config.n_qubits})"
            )
        
        # Limit samples for quantum
        limit = sample_limit or self.config.max_samples_quantum
        if len(X_train) > limit:
            rng = np.random.default_rng(len(X_train))
            indices = rng.choice(len(X_train), limit, replace=False)
            X_train = X_train[indices]
            y_train = y_train[indices]
        
        start = time.time()
        
        try:
            if QISKIT_ML_AVAILABLE:
                self._build_quantum_kernel()
                
                # Compute kernel matrix
                kernel_start = time.time()
                # The kernel is computed during fit
                self.model.fit(X_train, y_train)
                self._kernel_time = time.time() - kernel_start
            else:
                raise ImportError("Qiskit not available")
                
        except (ImportError, Exception) as e:
            if self.config.use_classical_fallback:
                print(f"Quantum kernel failed ({e}), using classical fallback")
                self._build_classical_fallback()
                self.model.fit(X_train, y_train)
            else:
                raise
        
        train_time = time.time() - start
        self._is_fitted = True
        return train_time
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict labels."""
        if not self._is_fitted:
            raise RuntimeError("QSVM not fitted. Call fit() first.")
        return self.model.predict(X)
    
    def evaluate(
        self,
        X_test: np.ndarray,
        y_test: np.ndarray,
        train_time: float = 0.0,
    ) -> QSVMResult:
        """
        Evaluate QSVM on test set.
        
        Args:
            X_test: Test features
            y_test: Test labels
            train_time: Training time
        
        Returns:
            QSVMResult with metrics
        """
        y_pred = self.predict(X_test)
        
        n_sv = 0
        if hasattr(self.model, 'n_support_'):
            n_sv = sum(self.model.n_support_)
        elif hasattr(self.model, 'support_vectors_'):
            n_sv = len(self.model.support_vectors_)
        
        return QSVMResult(
            accuracy=accuracy_score(y_test, y_pred),
            f1_score=f1_score(y_test, y_pred, average="weighted"),
            train_time=train_time,
            kernel_computation_time=self._kernel_time,
            n_support_vectors=n_sv,
            used_quantum=self._used_quantum,
            config=self.config,
        )
    
    def fit_evaluate(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_test: np.ndarray,
        y_test: np.ndarray,
    ) -> QSVMResult:
        """Fit and evaluate in one step."""
        train_time = self.fit(X_train, y_train)
        return self.evaluate(X_test, y_test, train_time)
    
    def get_kernel_matrix(
        self,
        X1: np.ndarray,
        X2: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """
        Compute kernel matrix.
        
        Args:
            X1: First data array
            X2: Second data array (if None, compute K(X1, X1))
        
        Returns:
            Kernel matrix
        """
        if not self._used_quantum or self.kernel is None:
            raise RuntimeError("Quantum kernel not available")
        
        if X2 is None:
            X2 = X1
        
        return self.kernel.evaluate(X1, X2)


def compare_quantum_classical(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
    n_qubits: int = 4,
) -> Tuple[QSVMResult, QSVMResult]:
    """
    Compare quantum QSVM with classical SVM.
    
    Returns:
        Tuple of (quantum_result, classical_result)
    """
    # Quantum QSVM
    print("Training QSVM (quantum)...")
    qsvm_quantum = QSVM(QSVMConfig(
        n_qubits=n_qubits,
        use_classical_fallback=False,
    ))
    try:
        quantum_result = qsvm_quantum.fit_evaluate(X_train, y_train, X_test, y_test)
    except ImportError:
        quantum_result = None
        print("  Qiskit not available")
    
    # Classical SVM (for comparison)
    print("Training SVM (classical)...")
    qsvm_classical = QSVM(QSVMConfig(
        n_qubits=n_qubits,
        use_classical_fallback=True,
    ))
    # Force classical
    qsvm_classical._build_classical_fallback()
    train_time = time.time()
    qsvm_classical.model.fit(X_train, y_train)
    train_time = time.time() - train_time
    qsvm_classical._is_fitted = True
    classical_result = qsvm_classical.evaluate(X_test, y_test, train_time)
    
    return quantum_result, classical_result


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(__file__).rsplit("/", 3)[0])
    
    from qzero.preprocessing.data_loader import generate_synthetic_data, DataLoader
    from qzero.preprocessing.feature_engineering import FeatureEngineer
    
    print("Generating synthetic data...")
    X, y = generate_synthetic_data(n_samples=1000)
    
    print("Preparing data...")
    loader = DataLoader()
    data = loader.prepare_data(X, y, binary=True)
    
    print("Engineering features for quantum (4 qubits)...")
    engineer = FeatureEngineer(n_qubits=4)
    X_train_q = engineer.fit_transform(data["X_train"], data["y_train"])
    X_test_q = engineer.transform(data["X_test"])
    
    print(f"Quantum-ready shapes: train={X_train_q.shape}, test={X_test_q.shape}")
    
    print("\nRunning QSVM...")
    config = QSVMConfig(n_qubits=4, max_samples_quantum=200)
    qsvm = QSVM(config)
    result = qsvm.fit_evaluate(X_train_q, data["y_train"], X_test_q, data["y_test"])
    
    print(f"\nResults:")
    print(f"  Used quantum: {result.used_quantum}")
    print(f"  Accuracy: {result.accuracy:.4f}")
    print(f"  F1 Score: {result.f1_score:.4f}")
    print(f"  Training time: {result.train_time:.2f}s")
    print(f"  Support vectors: {result.n_support_vectors}")
