"""
Tests for preprocessing module.
"""

import pytest
import numpy as np
import pandas as pd
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from preprocessing.data_loader import (
    generate_synthetic_data,
    DataLoader,
    UGRANSOME_FEATURES,
)
from preprocessing.feature_engineering import FeatureEngineer, create_quantum_features


class TestSyntheticDataGeneration:
    """Tests for synthetic data generation."""
    
    def test_generates_correct_shape(self):
        """Test that synthetic data has correct dimensions."""
        X, y = generate_synthetic_data(n_samples=1000, n_features=14)
        
        # Allow small variance due to signature clustering
        assert abs(X.shape[0] - 1000) < 10
        assert X.shape[1] == 14
        assert len(y) == X.shape[0]
    
    def test_generates_all_classes(self):
        """Test that all classes are present."""
        X, y = generate_synthetic_data(n_samples=1000)
        
        unique_classes = set(y.unique())
        assert 0 in unique_classes  # Normal
        assert 1 in unique_classes  # Anomaly
        assert 2 in unique_classes  # Signature
    
    def test_feature_names_match(self):
        """Test that feature columns match expected names."""
        X, y = generate_synthetic_data(n_samples=100, n_features=14)
        
        assert list(X.columns) == UGRANSOME_FEATURES
    
    def test_no_negative_values(self):
        """Test that all values are non-negative (valid network traffic)."""
        X, y = generate_synthetic_data(n_samples=1000)
        
        assert (X.values >= 0).all()
    
    def test_reproducibility(self):
        """Test that same seed produces same data."""
        X1, y1 = generate_synthetic_data(n_samples=100, random_state=42)
        X2, y2 = generate_synthetic_data(n_samples=100, random_state=42)
        
        pd.testing.assert_frame_equal(X1, X2)
        pd.testing.assert_series_equal(y1, y2)
    
    def test_class_ratios(self):
        """Test that class ratios are approximately correct."""
        X, y = generate_synthetic_data(
            n_samples=10000,
            anomaly_ratio=0.15,
            signature_ratio=0.20,
        )
        
        counts = y.value_counts(normalize=True)
        
        # Allow 5% tolerance
        assert abs(counts.get(0, 0) - 0.65) < 0.05  # Normal
        assert abs(counts.get(1, 0) - 0.15) < 0.05  # Anomaly
        assert abs(counts.get(2, 0) - 0.20) < 0.05  # Signature
    
    def test_difficulty_levels(self):
        """Test that difficulty parameter produces valid data."""
        for difficulty in ["easy", "medium", "hard"]:
            X, y = generate_synthetic_data(n_samples=500, difficulty=difficulty)
            
            # Basic validity checks
            assert X.shape[0] == len(y)
            assert (X.values >= 0).all()
            assert len(y.unique()) == 3  # All classes present
    
    def test_difficulty_affects_classification(self):
        """Test that harder difficulty makes classification harder."""
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.model_selection import train_test_split
        from sklearn.preprocessing import StandardScaler
        
        accuracies = {}
        for difficulty in ["easy", "hard"]:
            X, y = generate_synthetic_data(n_samples=1000, difficulty=difficulty, random_state=42)
            y_binary = (y != 0).astype(int)
            
            X_train, X_test, y_train, y_test = train_test_split(
                X.values, y_binary.values, test_size=0.2, random_state=42
            )
            scaler = StandardScaler()
            X_train = scaler.fit_transform(X_train)
            X_test = scaler.transform(X_test)
            
            clf = RandomForestClassifier(n_estimators=50, random_state=42)
            clf.fit(X_train, y_train)
            accuracies[difficulty] = clf.score(X_test, y_test)
        
        # Hard difficulty should result in lower accuracy
        assert accuracies["hard"] < accuracies["easy"]


class TestDataLoader:
    """Tests for DataLoader class."""
    
    def test_prepare_data_shapes(self):
        """Test that prepare_data returns correct shapes."""
        X, y = generate_synthetic_data(n_samples=1000)
        loader = DataLoader()
        
        data = loader.prepare_data(X, y, test_size=0.2, val_size=0.1)
        n_samples = len(X)
        
        total = len(data["X_train"]) + len(data["X_val"]) + len(data["X_test"])
        assert total == n_samples
        
        # Approximate sizes (stratification may vary slightly)
        assert 0.65 < len(data["X_train"]) / n_samples < 0.78
        assert 0.15 < len(data["X_test"]) / n_samples < 0.25
    
    def test_scaling(self):
        """Test that features are scaled."""
        X, y = generate_synthetic_data(n_samples=1000)
        loader = DataLoader()
        
        data = loader.prepare_data(X, y)
        
        # After StandardScaler, mean should be ~0 and std ~1
        assert abs(data["X_train"].mean()) < 0.1
        assert abs(data["X_train"].std() - 1.0) < 0.2
    
    def test_binary_labels(self):
        """Test binary label conversion."""
        X, y = generate_synthetic_data(n_samples=1000)
        loader = DataLoader()
        
        data = loader.prepare_data(X, y, binary=True)
        
        unique = np.unique(data["y_train"])
        assert set(unique) == {0, 1}


class TestFeatureEngineer:
    """Tests for FeatureEngineer class."""
    
    def test_reduces_dimensions(self):
        """Test that dimensions are reduced correctly."""
        X, y = generate_synthetic_data(n_samples=500)
        engineer = FeatureEngineer(n_qubits=4)
        
        X_reduced = engineer.fit_transform(X.values, y.values)
        
        assert X_reduced.shape[0] == len(X)
        assert X_reduced.shape[1] == 4
    
    def test_encoding_range(self):
        """Test that output is in encoding range."""
        X, y = generate_synthetic_data(n_samples=500)
        engineer = FeatureEngineer(n_qubits=4, encoding_range=(0, np.pi))
        
        X_reduced = engineer.fit_transform(X.values, y.values)
        
        assert X_reduced.min() >= 0
        # Allow small floating point tolerance
        assert X_reduced.max() <= np.pi + 1e-10
    
    def test_different_reduction_methods(self):
        """Test different reduction methods."""
        X, y = generate_synthetic_data(n_samples=500)
        n_samples = len(X)
        
        for method in ["pca", "mutual_info", "variance"]:
            engineer = FeatureEngineer(n_qubits=4, reduction_method=method)
            X_reduced = engineer.fit_transform(X.values, y.values)
            
            assert X_reduced.shape == (n_samples, 4), f"Failed for method: {method}"


class TestCreateQuantumFeatures:
    """Tests for quantum feature creation."""
    
    def test_angle_encoding(self):
        """Test angle encoding range."""
        X = np.random.randn(100, 4)
        X_q = create_quantum_features(X, n_qubits=4, method="angle")
        
        assert X_q.min() >= 0
        # Allow small epsilon for floating point precision
        assert X_q.max() <= 2 * np.pi + 1e-10
    
    def test_amplitude_encoding(self):
        """Test amplitude encoding normalization."""
        X = np.random.randn(100, 4)
        X_q = create_quantum_features(X, n_qubits=4, method="amplitude")
        
        norms = np.linalg.norm(X_q, axis=1)
        np.testing.assert_array_almost_equal(norms, np.ones(100), decimal=5)
    
    def test_basis_encoding(self):
        """Test basis encoding binarization."""
        X = np.random.randn(100, 4)
        X_q = create_quantum_features(X, n_qubits=4, method="basis")
        
        assert set(np.unique(X_q)) == {0.0, 1.0}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
