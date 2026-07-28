"""
Tests for real UGRansome dataset loading and processing.
"""

import pytest
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from qzero.preprocessing.data_loader import DataLoader


class TestRealDataset:
    """Tests for the real UGRansome dataset."""
    
    @pytest.fixture
    def loader(self):
        """Create DataLoader instance."""
        return DataLoader()
    
    @pytest.fixture
    def dataset_path(self):
        """Path to the real dataset."""
        return Path(__file__).parent.parent / "data" / "raw" / "final(2).csv"
    
    def test_dataset_exists(self, dataset_path):
        """Verify the dataset file exists."""
        assert dataset_path.exists(), f"Dataset not found at {dataset_path}"
    
    @pytest.mark.skipif(
        not (Path(__file__).parent.parent / "data" / "raw" / "final(2).csv").exists(),
        reason="Real dataset not available"
    )
    def test_load_ugransome(self, loader):
        """Test loading the real UGRansome dataset."""
        X, y = loader.load_ugransome()
        
        # Check shapes
        assert len(X) == len(y), "Features and labels must have same length"
        assert len(X) > 100000, f"Expected >100k samples, got {len(X)}"
        assert X.shape[1] == 12, f"Expected 12 features, got {X.shape[1]}"
        
        # Check label values
        unique_labels = set(y.unique())
        assert unique_labels == {1, 2, 3}, f"Unexpected labels: {unique_labels}"
        
        # Check label distribution
        label_counts = y.value_counts()
        assert label_counts[1] > 40000, "Anomaly count seems low"
        assert label_counts[2] > 60000, "Signature count seems low"
        assert label_counts[3] > 30000, "Synthetic signature count seems low"
    
    @pytest.mark.skipif(
        not (Path(__file__).parent.parent / "data" / "raw" / "final(2).csv").exists(),
        reason="Real dataset not available"
    )
    def test_data_types(self, loader):
        """Test that all features are numeric after loading."""
        X, y = loader.load_ugransome()
        
        # All columns should be numeric
        for col in X.columns:
            assert np.issubdtype(X[col].dtype, np.number), f"Column {col} is not numeric"
        
        # No NaN values
        assert not X.isna().any().any(), "Found NaN values in features"
        assert not y.isna().any(), "Found NaN values in labels"
    
    @pytest.mark.skipif(
        not (Path(__file__).parent.parent / "data" / "raw" / "final(2).csv").exists(),
        reason="Real dataset not available"
    )
    def test_prepare_real_data(self, loader):
        """Test preparing the real dataset for training."""
        X, y = loader.load_ugransome()
        
        # Use a subset for faster testing
        X_subset = X.head(10000)
        y_subset = y.head(10000)
        
        data = loader.prepare_data(X_subset, y_subset, binary=True)
        
        # Check splits
        assert "X_train" in data
        assert "X_val" in data
        assert "X_test" in data
        assert "y_train" in data
        assert "y_val" in data
        assert "y_test" in data
        
        # Check dimensions
        total = len(data["X_train"]) + len(data["X_val"]) + len(data["X_test"])
        assert total == 10000, f"Total samples mismatch: {total}"
        
        # Binary labels: note that UGRansome only has attack types (A, S, SS)
        # so in binary mode we distinguish between anomaly (zero-day) vs known
        # Label 1 (Anomaly) -> 0 (to detect), Labels 2,3 -> 1 (known attacks)
        all_labels = np.concatenate([data["y_train"], data["y_val"], data["y_test"]])
        unique_labels = set(np.unique(all_labels))
        assert len(unique_labels) <= 2, f"Binary should have at most 2 classes, got {unique_labels}"
    
    @pytest.mark.skipif(
        not (Path(__file__).parent.parent / "data" / "raw" / "final(2).csv").exists(),
        reason="Real dataset not available"
    )
    def test_multiclass_labels(self, loader):
        """Test multiclass label preparation."""
        X, y = loader.load_ugransome()
        
        X_subset = X.head(5000)
        y_subset = y.head(5000)
        
        data = loader.prepare_data(X_subset, y_subset, binary=False)
        
        # Should have 3 classes (1, 2, 3 -> encoded to 0, 1, 2)
        all_labels = np.concatenate([data["y_train"], data["y_val"], data["y_test"]])
        unique = set(np.unique(all_labels))
        assert len(unique) == 3, f"Expected 3 classes, got {len(unique)}"
    
    @pytest.mark.skipif(
        not (Path(__file__).parent.parent / "data" / "raw" / "final(2).csv").exists(),
        reason="Real dataset not available"
    )
    def test_label_names(self, loader):
        """Test that label names are available."""
        names = loader.get_label_names()
        
        assert 0 in names
        assert 1 in names
        assert 2 in names
        assert 3 in names
        assert "Anomaly" in names[1] or "Zero-Day" in names[1]


class TestRealDataIntegration:
    """Integration tests with real data and models."""
    
    @pytest.fixture
    def real_data(self):
        """Load and prepare real dataset."""
        loader = DataLoader()
        X, y = loader.load_ugransome()
        # Use small subset for speed
        return loader.prepare_data(X.head(2000), y.head(2000), binary=True)
    
    @pytest.mark.skipif(
        not (Path(__file__).parent.parent / "data" / "raw" / "final(2).csv").exists(),
        reason="Real dataset not available"
    )
    def test_classical_on_real_data(self, real_data):
        """Test classical baseline on real data."""
        from classical.baseline import ClassicalBaseline
        
        model = ClassicalBaseline(model_name="random_forest")
        result = model.fit_evaluate(
            real_data["X_train"],
            real_data["y_train"],
            real_data["X_test"],
            real_data["y_test"],
        )
        
        # Should achieve reasonable accuracy on real data
        # Note: ModelResult uses 'f1' not 'f1_score'
        assert result.accuracy > 0.5, f"Accuracy too low: {result.accuracy}"
        assert result.f1 > 0.4, f"F1 too low: {result.f1}"
    
    @pytest.mark.skipif(
        not (Path(__file__).parent.parent / "data" / "raw" / "final(2).csv").exists(),
        reason="Real dataset not available"
    )
    def test_feature_engineering_real_data(self, real_data):
        """Test feature engineering on real data."""
        from preprocessing.feature_engineering import FeatureEngineer
        
        engineer = FeatureEngineer(n_qubits=4, reduction_method="pca")
        X_train_q = engineer.fit_transform(real_data["X_train"], real_data["y_train"])
        X_test_q = engineer.transform(real_data["X_test"])
        
        assert X_train_q.shape[1] == 4, f"Expected 4 qubits, got {X_train_q.shape[1]}"
        assert X_test_q.shape[1] == 4
        assert not np.isnan(X_train_q).any(), "NaN in quantum features"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
