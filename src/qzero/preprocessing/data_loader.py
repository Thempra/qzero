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
    difficulty: str = "medium",
) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Generate synthetic network traffic data for development/testing.
    
    Simulates UGRansome-like data with:
    - Normal traffic: Gaussian distribution around baseline
    - Anomalies: Outliers with unusual patterns (zero-day simulation)
    - Signatures: Known attack patterns (clustered)
    
    Args:
        n_samples: Total number of samples
        n_features: Number of features (default 14 for UGRansome)
        anomaly_ratio: Ratio of anomaly samples
        signature_ratio: Ratio of signature attack samples
        random_state: Random seed for reproducibility
        difficulty: "easy", "medium", or "hard" - controls class overlap
    
    Returns:
        Tuple of (features DataFrame, labels Series)
    """
    rng = np.random.default_rng(random_state)
    
    # Difficulty settings
    # Higher overlap_factor = more class overlap = harder classification
    difficulty_settings = {
        "easy": {"overlap": 0.1, "noise": 0.05, "outlier_frac": 0.3},
        "medium": {"overlap": 0.5, "noise": 0.20, "outlier_frac": 0.08},
        "hard": {"overlap": 0.8, "noise": 0.30, "outlier_frac": 0.02},
    }
    settings = difficulty_settings.get(difficulty, difficulty_settings["medium"])
    
    n_anomaly = int(n_samples * anomaly_ratio)
    n_signature = int(n_samples * signature_ratio)
    n_normal = n_samples - n_anomaly - n_signature
    
    # Base normal traffic parameters
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
        0.1,    # fwd_urg_flags (small nonzero to avoid div issues)
    ])[:n_features]
    
    # Variance increases with difficulty (more overlap)
    base_std_ratio = 0.3 + settings["overlap"] * 0.4
    normal_std = normal_mean * base_std_ratio
    
    # Generate normal traffic
    X_normal = rng.normal(normal_mean, normal_std, (n_normal, n_features))
    
    # Anomaly traffic - subtle shifts for harder detection
    # The anomaly_shift is reduced with higher difficulty (more overlap with normal)
    shift_magnitude = 2.0 - settings["overlap"] * 1.5  # Less shift = harder
    anomaly_shifts = rng.uniform(0.5, 1 + shift_magnitude, n_features)
    anomaly_std = np.maximum(normal_std * (1.5 - settings["overlap"] * 0.5), 0.01)
    
    X_anomaly = rng.normal(
        normal_mean * anomaly_shifts,
        anomaly_std,
        (n_anomaly, n_features)
    )
    
    # Add some outliers (fewer in harder mode - anomalies blend in more)
    n_outliers = max(1, int(n_anomaly * settings["outlier_frac"]))
    outlier_idx = rng.choice(n_anomaly, size=n_outliers, replace=False)
    outlier_scale = rng.uniform(2, 5 - settings["overlap"] * 2, (n_outliers, n_features))
    X_anomaly[outlier_idx] *= outlier_scale
    
    # Signature traffic - known attack patterns
    # With higher difficulty, signatures are more similar to normal
    n_clusters = 3
    cluster_shift = 2.0 - settings["overlap"]  # Less distinct clusters in hard mode
    
    signature_patterns = [
        # DDoS-like: high packet counts, short duration
        np.array([0.5, 5, 0.5, 3, 0.5, 10, 10, 0.5, 0.5, 0.2, 0.2, 3, 0.5, 2])[:n_features],
        # Exfiltration-like: asymmetric, high outbound
        np.array([2, 1, 5, 0.5, 5, 2, 2, 0.3, 3, 0.5, 3, 0.5, 3, 0.5])[:n_features],
        # Ransomware-like: bursts, high data
        np.array([3, 0.5, 0.5, 10, 10, 15, 0.5, 10, 10, 5, 5, 2, 2, 5])[:n_features],
    ]
    
    X_signature = []
    samples_per_cluster = n_signature // n_clusters
    remaining = n_signature - (samples_per_cluster * n_clusters)
    
    for i, pattern in enumerate(signature_patterns):
        n_cluster = samples_per_cluster + (1 if i < remaining else 0)
        # Interpolate between normal and attack pattern based on difficulty
        center = normal_mean * (1 + (pattern - 1) * cluster_shift)
        center = np.maximum(center, 0.1)  # Ensure positive centers
        cluster_std = np.abs(center) * (0.15 + settings["overlap"] * 0.2)
        cluster_std = np.maximum(cluster_std, 0.01)  # Ensure positive std
        cluster_samples = rng.normal(center, cluster_std, (n_cluster, n_features))
        X_signature.append(cluster_samples)
    
    X_signature = np.vstack(X_signature)
    
    # Add global noise proportional to difficulty
    noise_scale = settings["noise"]
    for X in [X_normal, X_anomaly, X_signature]:
        noise = rng.normal(0, normal_mean * noise_scale, X.shape)
        X += noise
    
    # Ensure no negative values
    X_normal = np.maximum(X_normal, 0)
    X_anomaly = np.maximum(X_anomaly, 0)
    X_signature = np.maximum(X_signature, 0)
    
    # Combine all data
    X = np.vstack([X_normal, X_anomaly, X_signature])
    y = np.array(
        [0] * n_normal + 
        [1] * n_anomaly + 
        [2] * len(X_signature)
    )
    
    # Shuffle
    shuffle_idx = rng.permutation(len(X))
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
    
    def load_ugransome(self, filename: str = "final(2).csv") -> Tuple[pd.DataFrame, pd.Series]:
        """
        Load UGRansome dataset from CSV.
        
        Dataset format (final(2).csv):
        - Time, Protcol, Flag, Family, Clusters, SeddAddress, ExpAddress, 
          BTC, USD, Netflow_Bytes, IPaddress, Threats, Port, Prediction
        - Prediction: A (Anomaly), S (Signature), SS (Synthetic Signature)
        
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
        
        # Clean column names
        df.columns = df.columns.str.strip()
        df = df.rename(columns={"Protcol": "Protocol", "Prediction": "label"})
        
        # Map labels to integers: A=1 (anomaly/zero-day), S=2, SS=3
        # We treat A as zero-day (unseen attacks), S as known signatures
        label_map = {"A": 1, "S": 2, "SS": 3}
        labels = df["label"].map(label_map)
        
        # Handle any unmapped labels (shouldn't happen but be safe)
        if labels.isna().any():
            print(f"Warning: {labels.isna().sum()} unmapped labels found")
            labels = labels.fillna(0).astype(int)
        
        # Drop label and non-feature columns
        drop_cols = ["label"]
        if "Time" in df.columns:
            drop_cols.append("Time")  # Time is likely index/timestamp
            
        features = df.drop(columns=drop_cols)
        
        # Store encoders for each categorical column
        self._categorical_encoders = {}
        
        # Encode categorical columns (object and string dtypes)
        categorical_cols = features.select_dtypes(include=['object', 'string']).columns.tolist()
        for col in categorical_cols:
            encoder = LabelEncoder()
            features[col] = encoder.fit_transform(features[col].astype(str))
            self._categorical_encoders[col] = encoder
        
        # Convert all to numeric (some might be mixed type)
        for col in features.columns:
            features[col] = pd.to_numeric(features[col], errors='coerce')
        
        # Fill any NaN with 0 (shouldn't happen but be safe)
        features = features.fillna(0)
            
        return features, labels
    
    def get_label_names(self) -> Dict[int, str]:
        """Return mapping of label integers to names."""
        return {
            0: "Normal",
            1: "Anomaly (Zero-Day)",
            2: "Signature (Known)",
            3: "Synthetic Signature",
        }
    
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
        
        For UGRansome dataset:
        - Label 1 (A) = Anomaly/Zero-Day (unknown attacks) - what we want to detect
        - Label 2 (S) = Signature (known attacks)
        - Label 3 (SS) = Synthetic Signature (known attacks)
        
        Args:
            X: Feature DataFrame
            y: Labels Series
            test_size: Test set ratio
            val_size: Validation set ratio (from training set)
            random_state: Random seed
            binary: If True, convert to binary (zero-day vs known attacks)
        
        Returns:
            Dictionary with train/val/test splits
        """
        # Convert labels
        if binary:
            # For UGRansome: 1 (Anomaly/Zero-Day) -> 1, others -> 0
            # This makes it: 1 = zero-day (detect), 0 = known attack
            y_encoded = (y == 1).astype(int)
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
        
        # Get feature names (handle both DataFrame and numpy array)
        if hasattr(X, 'columns'):
            feature_names = list(X.columns)
        else:
            feature_names = [f"feature_{i}" for i in range(X.shape[1])]
        
        return {
            "X_train": X_train_scaled,
            "X_val": X_val_scaled,
            "X_test": X_test_scaled,
            "y_train": y_train.values if hasattr(y_train, 'values') else y_train,
            "y_val": y_val.values if hasattr(y_val, 'values') else y_val,
            "y_test": y_test.values if hasattr(y_test, 'values') else y_test,
            "feature_names": feature_names,
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
            reducer = PCA(n_components=n_components, random_state=42)
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
