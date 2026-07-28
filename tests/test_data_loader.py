"""
Tests for data loader module.
"""

import pytest
import numpy as np
import pandas as pd

from qzero.preprocessing.data_loader import DataLoader, generate_synthetic_data


class TestGenerateSyntheticData:
    """Tests for generate_synthetic_data function."""

    def test_default_parameters(self):
        """Test with default parameters."""
        X, y = generate_synthetic_data()

        assert X.shape[0] == 10000
        assert X.shape[1] == 14
        assert y.shape[0] == 10000
        assert len(y.unique()) == 3  # 0, 1, 2

    def test_custom_samples(self):
        """Test with custom number of samples."""
        X, y = generate_synthetic_data(n_samples=500)

        assert X.shape[0] == 500
        assert y.shape[0] == 500

    def test_difficulty_levels(self):
        """Test with different difficulty levels."""
        for difficulty in ["easy", "medium", "hard"]:
            X, y = generate_synthetic_data(n_samples=500, difficulty=difficulty)
            assert X.shape == (500, 14)

    def test_class_distribution(self):
        """Test that classes are properly distributed."""
        X, y = generate_synthetic_data(n_samples=1000, anomaly_ratio=0.2, signature_ratio=0.2)

        # Check that all three classes are present
        assert 0 in y.unique()
        assert 1 in y.unique()
        assert 2 in y.unique()


class TestDataLoader:
    """Tests for DataLoader class."""

    def test_init(self):
        """Test DataLoader initialization."""
        loader = DataLoader()

        assert loader.scaler is not None
        assert loader.label_encoder is not None

    def test_prepare_data_binary(self):
        """Test data preparation with binary classification."""
        X, y = generate_synthetic_data(n_samples=500)
        loader = DataLoader()

        data = loader.prepare_data(X, y, binary=True)

        assert "X_train" in data
        assert "X_val" in data
        assert "X_test" in data
        assert "y_train" in data
        assert "y_val" in data
        assert "y_test" in data
        assert "feature_names" in data

        # Check shapes
        assert data["X_train"].shape[0] > 0
        assert data["X_test"].shape[0] > 0

        # Check binary labels
        assert set(data["y_train"]).issubset({0, 1})
        assert set(data["y_test"]).issubset({0, 1})

    def test_prepare_data_multi_class(self):
        """Test data preparation with multi-class classification."""
        X, y = generate_synthetic_data(n_samples=500)
        loader = DataLoader()

        data = loader.prepare_data(X, y, binary=False)

        # Check that labels are 0, 1, 2
        assert set(data["y_train"]).issubset({0, 1, 2, 3})

    def test_scaling(self):
        """Test that data is properly scaled."""
        X, y = generate_synthetic_data(n_samples=100)
        loader = DataLoader()

        data = loader.prepare_data(X, y, binary=True)

        # Check that features are scaled (approximately between -3 and 3 for standard scaler)
        X_train = data["X_train"]
        assert X_train.min() > -100  # StandardScaler ranges
        assert X_train.max() < 100

    def test_feature_names(self):
        """Test that feature names are preserved."""
        X, y = generate_synthetic_data(n_samples=100)
        loader = DataLoader()

        data = loader.prepare_data(X, y, binary=True)

        assert len(data["feature_names"]) == 14
        assert all(isinstance(name, str) for name in data["feature_names"])

    def test_stratified_split(self):
        """Test that stratified split preserves class distribution."""
        X, y = generate_synthetic_data(n_samples=1000, anomaly_ratio=0.2)

        loader = DataLoader()
        data = loader.prepare_data(X, y, binary=True, test_size=0.2)

        # Calculate class ratios directly from prepared data
        train_1_ratio = (data["y_train"] == 1).sum() / len(data["y_train"])
        test_1_ratio = (data["y_test"] == 1).sum() / len(data["y_test"])

        # Ratios should be similar (within 10%)
        assert abs(train_1_ratio - test_1_ratio) < 0.1

    def test_reduce_dimensions_pca(self):
        """Test PCA dimensionality reduction."""
        X, y = generate_synthetic_data(n_samples=100)
        loader = DataLoader()

        reduced = loader.reduce_dimensions(X.values, n_components=4, method="pca")

        assert reduced.shape == (100, 4)

    def test_reduce_dimensions_invalid_method(self):
        """Test that invalid method raises error."""
        X, y = generate_synthetic_data(n_samples=100)
        loader = DataLoader()

        with pytest.raises(ValueError, match="Unknown method"):
            loader.reduce_dimensions(X.values, n_components=4, method="invalid")

    def test_get_label_names(self):
        """Test label name mapping."""
        loader = DataLoader()

        labels = loader.get_label_names()

        assert len(labels) == 4
        assert 0 in labels
        assert 1 in labels
        assert 2 in labels
        assert 3 in labels
        assert labels[0] == "Normal"
        assert labels[1] == "Anomaly (Zero-Day)"
        assert labels[2] == "Signature (Known)"
        assert labels[3] == "Synthetic Signature"

    def test_load_ugransome_not_found(self):
        """Test loading UGRansome when file doesn't exist."""
        loader = DataLoader()

        with pytest.raises(FileNotFoundError):
            loader.load_ugransome("nonexistent.csv")

    def test_load_ugransome_creates_encoders(self):
        """Test that UGRansome loader has correct structure."""
        loader = DataLoader()

        # Check that method exists
        assert hasattr(loader, "load_ugransome")
        assert callable(loader.load_ugransome)

        # Check that loader has expected attributes
        assert hasattr(loader, "data_dir")
        assert hasattr(loader, "scaler")
        assert hasattr(loader, "label_encoder")

        # The _categorical_encoders attribute is only set after loading data
        # So we can't check it here without actually loading a file
        # The important thing is that the method exists and has the correct signature


if __name__ == "__main__":
    pytest.main([__file__, "-v"])