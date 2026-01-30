"""
Feature engineering for quantum-ready preprocessing.
"""

import numpy as np
import pandas as pd
from typing import Optional, Tuple, List
from sklearn.preprocessing import MinMaxScaler
from sklearn.decomposition import PCA
from sklearn.feature_selection import SelectKBest, mutual_info_classif


class FeatureEngineer:
    """
    Feature engineering pipeline optimized for quantum circuits.
    
    Quantum circuits typically need:
    - Normalized features in [0, π] or [-π, π] for angle encoding
    - Low dimensionality (4-8 features for NISQ devices)
    - Uncorrelated features for efficient encoding
    """
    
    def __init__(
        self,
        n_qubits: int = 4,
        encoding_range: Tuple[float, float] = (0, np.pi),
        reduction_method: str = "pca",
    ):
        """
        Initialize feature engineer.
        
        Args:
            n_qubits: Number of qubits (determines feature dimensions)
            encoding_range: Range for quantum angle encoding
            reduction_method: "pca", "mutual_info", or "variance"
        """
        self.n_qubits = n_qubits
        self.encoding_range = encoding_range
        self.reduction_method = reduction_method
        
        self.scaler = MinMaxScaler(feature_range=encoding_range)
        self.reducer = None
        self.selected_features: Optional[List[int]] = None
        self._is_fitted = False
        self._data_shift = 0.0  # Track data shift for proper transformation
    
    def fit(self, X: np.ndarray, y: Optional[np.ndarray] = None) -> "FeatureEngineer":
        """
        Fit the feature engineering pipeline.
        
        Args:
            X: Training features
            y: Training labels (required for mutual_info)
        
        Returns:
            self
        """
        # Step 1: Dimensionality reduction
        if X.shape[1] > self.n_qubits:
            if self.reduction_method == "pca":
                self.reducer = PCA(n_components=self.n_qubits)
                X_reduced = self.reducer.fit_transform(X)
            elif self.reduction_method == "mutual_info":
                if y is None:
                    raise ValueError("y required for mutual_info reduction")
                selector = SelectKBest(mutual_info_classif, k=self.n_qubits)
                selector.fit(X, y)
                self.selected_features = selector.get_support(indices=True).tolist()
                X_reduced = X[:, self.selected_features]
            elif self.reduction_method == "variance":
                # Select features with highest variance
                variances = np.var(X, axis=0)
                self.selected_features = np.argsort(variances)[-self.n_qubits:].tolist()
                X_reduced = X[:, self.selected_features]
            else:
                raise ValueError(f"Unknown reduction method: {self.reduction_method}")
        else:
            X_reduced = X
        
        # Step 2: Shift data to make it non-negative if encoding range starts at 0
        if self.encoding_range[0] == 0:
            self._data_shift = -X_reduced.min()
            X_shifted = X_reduced + self._data_shift
        else:
            self._data_shift = 0.0
            X_shifted = X_reduced
        
        # Step 3: Scale to encoding range
        self.scaler.fit(X_shifted)
        
        self._is_fitted = True
        return self
    
    def transform(self, X: np.ndarray, clip: bool = True) -> np.ndarray:
        """
        Transform features for quantum encoding.
        
        Args:
            X: Feature array
            clip: If True, clip values to encoding range (default True for quantum safety)
        
        Returns:
            Transformed features in encoding range
        """
        if not self._is_fitted:
            raise RuntimeError("FeatureEngineer not fitted. Call fit() first.")
        
        # Reduce dimensions
        if self.reducer is not None:
            X_reduced = self.reducer.transform(X)
        elif self.selected_features is not None:
            X_reduced = X[:, self.selected_features]
        else:
            X_reduced = X
        
        # Shift data
        X_shifted = X_reduced + self._data_shift
        
        # Scale to encoding range
        X_scaled = self.scaler.transform(X_shifted)
        
        # Clip to encoding range for quantum circuit safety
        if clip:
            X_scaled = np.clip(X_scaled, self.encoding_range[0], self.encoding_range[1])
        
        return X_scaled
    
    def fit_transform(self, X: np.ndarray, y: Optional[np.ndarray] = None) -> np.ndarray:
        """Fit and transform in one step."""
        return self.fit(X, y).transform(X)
    
    def get_feature_importance(self) -> Optional[np.ndarray]:
        """
        Get feature importance from reducer.
        
        Returns:
            Feature importance array or None
        """
        if self.reducer is not None and hasattr(self.reducer, 'explained_variance_ratio_'):
            return self.reducer.explained_variance_ratio_
        return None


def create_quantum_features(
    X: np.ndarray,
    n_qubits: int = 4,
    method: str = "angle",
) -> np.ndarray:
    """
    Create quantum-ready features from classical data.
    
    Args:
        X: Input features (already reduced to n_qubits dimensions)
        n_qubits: Number of qubits
        method: Encoding method ("angle", "amplitude", "basis")
    
    Returns:
        Quantum-ready feature array
    """
    if X.shape[1] != n_qubits:
        raise ValueError(f"Expected {n_qubits} features, got {X.shape[1]}")
    
    if method == "angle":
        # Scale to [0, 2π] for rotation gates
        scaler = MinMaxScaler(feature_range=(0, 2 * np.pi))
        return scaler.fit_transform(X)
    
    elif method == "amplitude":
        # Normalize each sample to unit vector (for amplitude encoding)
        norms = np.linalg.norm(X, axis=1, keepdims=True)
        norms[norms == 0] = 1  # Avoid division by zero
        return X / norms
    
    elif method == "basis":
        # Binarize features for basis encoding
        median = np.median(X, axis=0)
        return (X > median).astype(float)
    
    else:
        raise ValueError(f"Unknown encoding method: {method}")


if __name__ == "__main__":
    # Test feature engineering
    from data_loader import generate_synthetic_data
    
    print("Testing feature engineering pipeline...")
    X, y = generate_synthetic_data(n_samples=1000)
    
    engineer = FeatureEngineer(n_qubits=4, reduction_method="pca")
    X_quantum = engineer.fit_transform(X.values, y.values)
    
    print(f"Original shape: {X.shape}")
    print(f"Quantum-ready shape: {X_quantum.shape}")
    print(f"Value range: [{X_quantum.min():.4f}, {X_quantum.max():.4f}]")
    print(f"Expected range: {engineer.encoding_range}")
    
    importance = engineer.get_feature_importance()
    if importance is not None:
        print(f"PCA explained variance: {importance}")
