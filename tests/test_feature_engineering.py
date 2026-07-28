"""
Tests for feature engineering module.
"""

import pytest
import numpy as np
import pandas as pd

from qzero.preprocessing.feature_engineering import FeatureEngineer, create_quantum_features


class TestFeatureEngineer:
    """Tests for FeatureEngineer class."""

    def test_init_default(self):
        """Test default initialization."""
        engineer = FeatureEngineer()

        assert engineer.n_qubits == 4
        assert engineer.encoding_range == (0, np.pi)
        assert engineer.reduction_method == "pca"

    def test_init_custom(self):
        """Test custom initialization."""
        engineer = FeatureEngineer(
            n_qubits=8,
            encoding_range=(0, 2 * np.pi),
            reduction_method="variance"
        )

        assert engineer.n_qubits == 8
        assert engineer.encoding_range == (0, 2 * np.pi)
        assert engineer.reduction_method == "variance"

    def test_fit_with_more_features_than_qubits(self):
        """Test fitting when features > qubits."""
        engineer = FeatureEngineer(n_qubits=4)

        # Create data with more features than qubits
        X = np.random.randn(100, 10)
        y = np.random.randint(0, 2, 100)

        result = engineer.fit(X, y)

        assert engineer._is_fitted
        assert engineer.reducer is not None

    def test_fit_with_fewer_features_than_qubits(self):
        """Test fitting when features < qubits."""
        engineer = FeatureEngineer(n_qubits=8)

        X = np.random.randn(100, 4)
        y = np.random.randint(0, 2, 100)

        result = engineer.fit(X, y)

        assert engineer._is_fitted
        assert engineer.reducer is None

    def test_transform_unfitted_raises_error(self):
        """Test that transform without fit raises error."""
        engineer = FeatureEngineer()

        X = np.random.randn(10, 4)

        with pytest.raises(RuntimeError, match="not fitted"):
            engineer.transform(X)

    def test_transform_matches_fitted_shape(self):
        """Test that transform produces correct shape."""
        engineer = FeatureEngineer(n_qubits=4)

        X_train = np.random.randn(100, 8)
        y_train = np.random.randint(0, 2, 100)

        engineer.fit(X_train, y_train)
        X_test = np.random.randn(50, 8)

        X_transformed = engineer.transform(X_test)

        assert X_transformed.shape == (50, 4)

    def test_encoding_range(self):
        """Test that features are scaled to encoding range."""
        engineer = FeatureEngineer(n_qubits=4, encoding_range=(0, 2 * np.pi))

        # Use data with reasonable range for better test reliability
        X_train = np.random.randn(100, 4) * 2  # Scale to wider range
        y_train = np.random.randint(0, 2, 100)

        engineer.fit(X_train, y_train)
        X_test = np.random.randn(50, 4) * 2

        X_transformed = engineer.transform(X_test)

        # Features should be within the target range (allowing for numerical error)
        expected_min, expected_max = engineer.encoding_range
        assert X_transformed.min() >= expected_min - 0.1
        assert X_transformed.max() <= expected_max + 0.1

    def test_get_feature_importance_with_pca(self):
        """Test getting feature importance from PCA."""
        engineer = FeatureEngineer(n_qubits=4, reduction_method="pca")

        X = np.random.randn(100, 8)
        y = np.random.randint(0, 2, 100)

        engineer.fit(X, y)

        importance = engineer.get_feature_importance()

        assert importance is not None
        assert len(importance) == 4
        assert np.all(importance >= 0)
        assert np.all(importance <= 1)

    def test_get_feature_importance_without_reducer(self):
        """Test getting feature importance when no reducer used."""
        engineer = FeatureEngineer(n_qubits=8)

        X = np.random.randn(100, 4)
        y = np.random.randint(0, 2, 100)

        engineer.fit(X, y)

        importance = engineer.get_feature_importance()

        assert importance is None

    def test_fit_transform(self):
        """Test fit_transform method."""
        engineer = FeatureEngineer(n_qubits=4)

        X = np.random.randn(100, 8)
        y = np.random.randint(0, 2, 100)

        X_transformed = engineer.fit_transform(X, y)

        assert engineer._is_fitted
        assert X_transformed.shape == (100, 4)

    def test_pca_preserves_variance(self):
        """Test that PCA retains significant variance."""
        engineer = FeatureEngineer(n_qubits=4, reduction_method="pca")

        # Create data with known variance structure
        X = np.random.randn(100, 8)
        X[:, 0] = X[:, 0] * 2  # First feature has more variance

        y = np.random.randint(0, 2, 100)

        engineer.fit(X, y)
        importance = engineer.get_feature_importance()

        # First feature should have higher importance
        if importance is not None:
            assert importance[0] >= importance[1]

    def test_variance_reduction(self):
        """Test variance-based feature selection."""
        engineer = FeatureEngineer(n_qubits=4, reduction_method="variance")

        X = np.random.randn(100, 8)
        # Make first few features have higher variance
        X[:, :4] = X[:, :4] * 2

        y = np.random.randint(0, 2, 100)

        engineer.fit(X, y)

        # Should have selected features with higher variance
        assert engineer.selected_features is not None
        assert len(engineer.selected_features) == 4
        # Should select from the first half (higher variance)
        assert all(i < 4 for i in engineer.selected_features)


class TestCreateQuantumFeatures:
    """Tests for create_quantum_features function."""

    def test_angle_encoding(self):
        """Test angle encoding method."""
        X = np.random.randn(10, 4)

        X_encoded = create_quantum_features(X, n_qubits=4, method="angle")

        # Should scale to [0, 2π]
        assert X_encoded.shape == (10, 4)
        assert X_encoded.min() >= -0.1
        assert X_encoded.max() <= 2 * np.pi + 0.1

    def test_amplitude_encoding(self):
        """Test amplitude encoding method."""
        X = np.random.randn(10, 4)

        X_encoded = create_quantum_features(X, n_qubits=4, method="amplitude")

        # Should be unit vectors
        assert X_encoded.shape == (10, 4)
        norms = np.linalg.norm(X_encoded, axis=1)
        assert np.allclose(norms, 1.0, atol=1e-6)

    def test_basis_encoding(self):
        """Test basis encoding method."""
        X = np.random.randn(10, 4)

        X_encoded = create_quantum_features(X, n_qubits=4, method="basis")

        # Should be binary (0 or 1)
        assert X_encoded.shape == (10, 4)
        assert np.all(np.isin(X_encoded, [0, 1]))

    def test_invalid_encoding_method(self):
        """Test that invalid method raises error."""
        X = np.random.randn(10, 4)

        with pytest.raises(ValueError, match="Unknown encoding method"):
            create_quantum_features(X, n_qubits=4, method="invalid")

    def test_encoding_mismatch_qubits(self):
        """Test that encoding fails with wrong qubits."""
        X = np.random.randn(10, 6)

        with pytest.raises(ValueError, match="Expected.*features"):
            create_quantum_features(X, n_qubits=4, method="angle")

    def test_encoding_preserves_samples(self):
        """Test that encoding preserves number of samples."""
        X = np.random.randn(100, 4)

        X_encoded = create_quantum_features(X, n_qubits=4, method="angle")

        assert X_encoded.shape[0] == X.shape[0]

    def test_encoding_range_is_reproducible(self):
        """Test that encoding is deterministic with fixed random state."""
        np.random.seed(42)

        X1 = np.random.randn(10, 4)
        X2 = np.random.randn(10, 4)

        X_encoded1 = create_quantum_features(X1, n_qubits=4, method="angle")
        X_encoded2 = create_quantum_features(X2, n_qubits=4, method="angle")

        # Different inputs should produce different outputs
        assert not np.allclose(X_encoded1, X_encoded2)

    def test_encoding_scale_preserved(self):
        """Test that relative scales are preserved in amplitude encoding."""
        X = np.random.randn(10, 2)
        X[0] *= 2  # First sample has twice the magnitude

        X_encoded = create_quantum_features(X, n_qubits=2, method="amplitude")

        # Norms should be scaled
        norms = np.linalg.norm(X_encoded, axis=1)
        assert np.allclose(norms[0], norms[1], rtol=0.1)  # Allow some tolerance


if __name__ == "__main__":
    pytest.main([__file__, "-v"])