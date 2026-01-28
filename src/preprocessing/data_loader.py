"""
Data loading utilities for QZero.
Includes synthetic data generation for development/testing.
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Tuple, Optional, Dict, Any
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder

# UGRansome feature names (14 features)
UGRANSOME_FEATURES = [
    "flow_duration",
    "total_fwd_packets",
    "total_bwd_packets",
    "total_length_fwd_packets",
    "total_length_bwd_packets",
    "flow_bytes_per_sec",
    "flow_packets_per_sec",
    "fwd_packet_length_mean",
    "bwd_packet_length_mean",
    "fwd_iat_mean",  # Inter-arrival time
    "bwd_iat_mean",
    "fwd_psh_flags",  # PSH flag count
    "bwd_psh_flags",
    "fwd_urg_flags",  # URG flag count
]

# Attack classes in UGRansome
ATTACK_CLASSES = {
    "normal": 0,
    "anomaly": 1,      # Unknown/zero-day attacks
    "signature": 2,    # Known attack patterns
    "synthetic": 3,    # Synthetic signatures
}


def generate_synthetic_data(
    n_samples: int = 10000,
    n_features: int = 14,
    anomaly_ratio: float = 0.15,
    signature_ratio: float = 0.20,
    random_state: int = 42,
) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Generate synthetic network traffic data for development/testing.
    
    Simulates UGRansome-like data with:
    - Normal traffic: Gaussian distribution around baseline
    - Anomalies: Outliers with unusual patterns
    - Signatures: Known attack patterns (clustered)
    
    Args:
        n_samples: Total number of samples
        n_features: Number of features (default 14 for UGRansome)
        anomaly_ratio: Ratio of anomaly samples
        signature_ratio: Ratio of signature attack samples
        random_state: Random seed for reproducibility
    
    Returns:
        Tuple of (features DataFrame, labels Series)
    """
    np.random.seed(random_state)
    
    n_anomaly = int(n_samples * anomaly_ratio)
    n_signature = int(n_samples * signature_ratio)
    n_normal = n_samples - n_anomaly - n_signature
    
    # Normal traffic - centered around typical values
    normal_mean = np.array([
        500,    # flow_duration (ms)
        10,     # total_fwd_packets
        8,      # total_bwd_packets
        1500,   # total_length_fwd_packets
        1200,   # total_length_bwd_packets
        3000,   # flow_bytes_per_sec
        20,     # flow_packets_per_sec
        150,    # fwd_packet_length_mean
        150,    # bwd_packet_length_mean
        50,     # fwd_iat_mean
        60,     # bwd_iat_mean
        1,      # fwd_psh_flags
        1,      # bwd_psh_flags
        0,      # fwd_urg_flags
    ])[:n_features]
    
    normal_std = normal_mean * 0.3  # 30% standard deviation
    X_normal = np.random.normal(normal_mean, normal_std, (n_normal, n_features))
    X_normal = np.maximum(X_normal, 0)  # No negative values
    
    # Anomaly traffic - unusual patterns (zero-day simulation)
    # Higher variance, shifted means, correlated features
    anomaly_shifts = np.random.uniform(-2, 5, n_features)
    X_anomaly = np.random.normal(
        normal_mean * (1 + anomaly_shifts), 
        normal_std * 2, 
        (n_anomaly, n_features)
    )
    # Add some extreme outliers
    outlier_idx = np.random.choice(n_anomaly, size=n_anomaly // 5, replace=False)
    X_anomaly[outlier_idx] *= np.random.uniform(3, 10, (len(outlier_idx), n_features))
    X_anomaly = np.maximum(X_anomaly, 0)
    
    # Signature traffic - known attack patterns (clustered)
    # Create 3 distinct attack clusters
    n_clusters = 3
    signature_centers = [
        normal_mean * np.array([10, 50, 2, 100, 10, 500, 100, 50, 50, 5, 5, 10, 0, 5])[:n_features],  # DDoS-like
        normal_mean * np.array([0.1, 5, 100, 10, 1000, 50, 50, 10, 500, 1, 100, 0, 10, 0])[:n_features],  # Exfiltration-like
        normal_mean * np.array([5, 1, 1, 5000, 5000, 10000, 5, 5000, 5000, 500, 500, 5, 5, 10])[:n_features],  # Ransomware-like
    ]
    
    X_signature = []
    samples_per_cluster = n_signature // n_clusters
    for center in signature_centers:
        cluster_samples = np.random.normal(center, center * 0.1, (samples_per_cluster, n_features))
        X_signature.append(cluster_samples)
    X_signature = np.vstack(X_signature)
    X_signature = np.maximum(X_signature, 0)
    
    # Combine all data
    X = np.vstack([X_normal, X_anomaly, X_signature])
    y = np.array(
        [0] * n_normal + 
        [1] * n_anomaly + 
        [2] * len(X_signature)
    )
    
    # Shuffle
    shuffle_idx = np.random.permutation(len(X))
    X = X[shuffle_idx]
    y = y[shuffle_idx]
    
    # Create DataFrame
    feature_names = UGRANSOME_FEATURES[:n_features]
    df = pd.DataFrame(X, columns=feature_names)
    labels = pd.Series(y, name="label")
    
    return df, labels


class DataLoader:
    """
    Data loader for UGRansome dataset and synthetic data.
    """
    
    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize data loader.
        
        Args:
            data_dir: Path to data directory. If None, uses project default.
        """
        if data_dir is None:
            # Default to project's data directory
            self.data_dir = Path(__file__).parent.parent.parent / "data"
        else:
            self.data_dir = Path(data_dir)
        
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        self._is_fitted = False
    
    def load_ugransome(self, filename: str = "UGRansome.csv") -> Tuple[pd.DataFrame, pd.Series]:
        """
        Load UGRansome dataset from CSV.
        
        Args:
            filename: Name of the CSV file in data/raw/
        
        Returns:
            Tuple of (features DataFrame, labels Series)
        """
        filepath = self.data_dir / "raw" / filename
        
        if not filepath.exists():
            raise FileNotFoundError(
                f"Dataset not found at {filepath}. "
                "Run scripts/download_data.py first or use generate_synthetic_data()"
            )
        
        df = pd.read_csv(filepath)
        
        # Extract features and labels
        # UGRansome has a 'Class' column with attack types
        label_col = "Class" if "Class" in df.columns else "label"
        
        if label_col in df.columns:
            labels = df[label_col]
            features = df.drop(columns=[label_col])
        else:
            raise ValueError(f"Label column '{label_col}' not found in dataset")
        
        return features, labels
    
    def prepare_data(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        test_size: float = 0.2,
        val_size: float = 0.1,
        random_state: int = 42,
        binary: bool = True,
    ) -> Dict[str, Any]:
        """
        Prepare data for training: scale, encode, split.
        
        Args:
            X: Feature DataFrame
            y: Labels Series
            test_size: Test set ratio
            val_size: Validation set ratio (from training set)
            random_state: Random seed
            binary: If True, convert to binary (normal vs attack)
        
        Returns:
            Dictionary with train/val/test splits
        """
        # Convert labels
        if binary:
            # 0 = normal, 1 = any attack
            y_encoded = (y != 0).astype(int)
        else:
            y_encoded = self.label_encoder.fit_transform(y)
        
        # Train/test split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y_encoded, test_size=test_size, random_state=random_state, stratify=y_encoded
        )
        
        # Train/val split
        X_train, X_val, y_train, y_val = train_test_split(
            X_train, y_train, test_size=val_size, random_state=random_state, stratify=y_train
        )
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_val_scaled = self.scaler.transform(X_val)
        X_test_scaled = self.scaler.transform(X_test)
        self._is_fitted = True
        
        return {
            "X_train": X_train_scaled,
            "X_val": X_val_scaled,
            "X_test": X_test_scaled,
            "y_train": y_train.values if hasattr(y_train, 'values') else y_train,
            "y_val": y_val.values if hasattr(y_val, 'values') else y_val,
            "y_test": y_test.values if hasattr(y_test, 'values') else y_test,
            "feature_names": list(X.columns),
            "scaler": self.scaler,
        }
    
    def reduce_dimensions(
        self,
        X: np.ndarray,
        n_components: int = 4,
        method: str = "pca"
    ) -> np.ndarray:
        """
        Reduce dimensions for quantum circuits (limited qubits).
        
        Args:
            X: Feature array
            n_components: Target dimensions (usually 4-8 for NISQ)
            method: "pca" or "select_best"
        
        Returns:
            Reduced feature array
        """
        if method == "pca":
            from sklearn.decomposition import PCA
            reducer = PCA(n_components=n_components)
            return reducer.fit_transform(X)
        elif method == "select_best":
            from sklearn.feature_selection import SelectKBest, f_classif
            # This requires y, so return a reducer instead
            raise NotImplementedError("Use SelectKBest externally with y")
        else:
            raise ValueError(f"Unknown method: {method}")


if __name__ == "__main__":
    # Test synthetic data generation
    print("Generating synthetic data...")
    X, y = generate_synthetic_data(n_samples=1000)
    print(f"Features shape: {X.shape}")
    print(f"Labels distribution: {pd.Series(y).value_counts().to_dict()}")
    print(f"\nFeature stats:\n{X.describe()}")
    
    # Test data preparation
    print("\nPreparing data...")
    loader = DataLoader()
    data = loader.prepare_data(X, y)
    print(f"Train: {data['X_train'].shape}, Val: {data['X_val'].shape}, Test: {data['X_test'].shape}")
