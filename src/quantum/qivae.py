"""
Quantum-Inspired Variational Autoencoder (QI-VAE) for zero-day detection.

This implements a VAE with quantum-inspired components:
- Parameterized quantum circuit as encoder (optional)
- Latent space with quantum measurement-like sampling
- Reconstruction-based anomaly detection

References:
- "Quantum deep learning-enhanced ethereum blockchain for cloud security" (Nature Sci. Reports 2025)
- "Quantum autoencoders for efficient compression of quantum data" (Quantum Sci. Tech. 2019)
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Tuple, List
import time

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from torch.utils.data import DataLoader, TensorDataset
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

try:
    from qiskit import QuantumCircuit
    from qiskit.circuit import Parameter
    from qiskit.primitives import Sampler
    QISKIT_AVAILABLE = True
except ImportError:
    QISKIT_AVAILABLE = False


def check_torch():
    """Raise if PyTorch not available."""
    if not TORCH_AVAILABLE:
        raise ImportError("PyTorch not installed. Run: pip install torch")


@dataclass
class QIVAEConfig:
    """Configuration for QI-VAE."""
    input_dim: int = 14
    latent_dim: int = 4
    hidden_dims: Tuple[int, ...] = (64, 32)
    use_quantum_encoder: bool = False  # Use quantum circuit for encoding
    n_qubits: int = 4  # For quantum encoder
    learning_rate: float = 1e-3
    batch_size: int = 32
    epochs: int = 50
    beta: float = 1.0  # KL divergence weight
    anomaly_threshold_percentile: float = 95.0
    random_state: int = 42


@dataclass
class QIVAEResult:
    """Results from QI-VAE training and evaluation."""
    train_loss: float
    val_loss: float
    reconstruction_errors: np.ndarray
    anomaly_threshold: float
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    train_time: float
    config: QIVAEConfig = field(default_factory=QIVAEConfig)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "train_loss": self.train_loss,
            "val_loss": self.val_loss,
            "anomaly_threshold": self.anomaly_threshold,
            "accuracy": self.accuracy,
            "precision": self.precision,
            "recall": self.recall,
            "f1_score": self.f1_score,
            "train_time": self.train_time,
        }


if TORCH_AVAILABLE:
    
    class Encoder(nn.Module):
        """
        Classical encoder network.
        Maps input to latent mean and log-variance.
        """
        
        def __init__(
            self,
            input_dim: int,
            hidden_dims: Tuple[int, ...],
            latent_dim: int,
        ):
            super().__init__()
            
            # Build encoder layers
            layers = []
            prev_dim = input_dim
            for h_dim in hidden_dims:
                layers.extend([
                    nn.Linear(prev_dim, h_dim),
                    nn.BatchNorm1d(h_dim),
                    nn.LeakyReLU(0.2),
                    nn.Dropout(0.1),
                ])
                prev_dim = h_dim
            
            self.encoder = nn.Sequential(*layers)
            
            # Latent space parameters
            self.fc_mu = nn.Linear(prev_dim, latent_dim)
            self.fc_logvar = nn.Linear(prev_dim, latent_dim)
        
        def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
            """
            Encode input to latent distribution parameters.
            
            Returns:
                Tuple of (mu, logvar)
            """
            h = self.encoder(x)
            mu = self.fc_mu(h)
            logvar = self.fc_logvar(h)
            return mu, logvar
    
    
    class Decoder(nn.Module):
        """
        Classical decoder network.
        Reconstructs input from latent space.
        """
        
        def __init__(
            self,
            latent_dim: int,
            hidden_dims: Tuple[int, ...],
            output_dim: int,
        ):
            super().__init__()
            
            # Build decoder layers (reverse of encoder)
            layers = []
            prev_dim = latent_dim
            for h_dim in reversed(hidden_dims):
                layers.extend([
                    nn.Linear(prev_dim, h_dim),
                    nn.BatchNorm1d(h_dim),
                    nn.LeakyReLU(0.2),
                    nn.Dropout(0.1),
                ])
                prev_dim = h_dim
            
            # Output layer
            layers.append(nn.Linear(prev_dim, output_dim))
            
            self.decoder = nn.Sequential(*layers)
        
        def forward(self, z: torch.Tensor) -> torch.Tensor:
            """Decode latent vector to reconstruction."""
            return self.decoder(z)
    
    
    class QuantumInspiredVAE(nn.Module):
        """
        Quantum-Inspired Variational Autoencoder.
        
        Key quantum-inspired features:
        1. Latent space sampling with quantum measurement-like noise
        2. Optional quantum circuit encoder
        3. Amplitude-like normalization in latent space
        """
        
        def __init__(self, config: QIVAEConfig):
            super().__init__()
            self.config = config
            
            self.encoder = Encoder(
                config.input_dim,
                config.hidden_dims,
                config.latent_dim,
            )
            
            self.decoder = Decoder(
                config.latent_dim,
                config.hidden_dims,
                config.input_dim,
            )
            
            # Quantum-inspired components
            self.latent_transform = nn.Linear(config.latent_dim, config.latent_dim)
        
        def reparameterize(
            self,
            mu: torch.Tensor,
            logvar: torch.Tensor,
            quantum_noise: bool = True,
        ) -> torch.Tensor:
            """
            Reparameterization trick with quantum-inspired noise.
            
            In quantum measurement, outcomes follow Born rule (|amplitude|^2).
            We add a similar nonlinear transformation to the sampling process.
            """
            std = torch.exp(0.5 * logvar)
            eps = torch.randn_like(std)
            
            z = mu + eps * std
            
            if quantum_noise:
                # Quantum-inspired: apply amplitude-like transformation
                # Similar to measuring in computational basis
                z_norm = torch.norm(z, dim=1, keepdim=True)
                z_norm = torch.clamp(z_norm, min=1e-8)
                
                # Normalize like quantum amplitude (unit norm)
                z_normalized = z / z_norm
                
                # Scale by learned transformation (parameterized "rotation")
                z = self.latent_transform(z_normalized) * z_norm
            
            return z
        
        def forward(
            self,
            x: torch.Tensor,
        ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
            """
            Forward pass.
            
            Returns:
                Tuple of (reconstruction, mu, logvar)
            """
            mu, logvar = self.encoder(x)
            z = self.reparameterize(mu, logvar)
            reconstruction = self.decoder(z)
            return reconstruction, mu, logvar
        
        def encode(self, x: torch.Tensor) -> torch.Tensor:
            """Encode to latent space (for inference)."""
            mu, _ = self.encoder(x)
            return mu
        
        def decode(self, z: torch.Tensor) -> torch.Tensor:
            """Decode from latent space."""
            return self.decoder(z)
        
        def reconstruction_error(self, x: torch.Tensor) -> torch.Tensor:
            """
            Compute reconstruction error for anomaly detection.
            Higher error indicates more anomalous samples.
            """
            with torch.no_grad():
                reconstruction, _, _ = self.forward(x)
                error = F.mse_loss(reconstruction, x, reduction='none')
                return error.mean(dim=1)


def vae_loss(
    reconstruction: torch.Tensor,
    x: torch.Tensor,
    mu: torch.Tensor,
    logvar: torch.Tensor,
    beta: float = 1.0,
) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """
    VAE loss: reconstruction + KL divergence.
    
    Args:
        reconstruction: Reconstructed input
        x: Original input
        mu: Latent mean
        logvar: Latent log-variance
        beta: Weight for KL term (beta-VAE)
    
    Returns:
        Tuple of (total_loss, recon_loss, kl_loss)
    """
    check_torch()
    
    # Reconstruction loss (MSE)
    recon_loss = F.mse_loss(reconstruction, x, reduction='mean')
    
    # KL divergence: -0.5 * sum(1 + logvar - mu^2 - exp(logvar))
    kl_loss = -0.5 * torch.mean(1 + logvar - mu.pow(2) - logvar.exp())
    
    total_loss = recon_loss + beta * kl_loss
    
    return total_loss, recon_loss, kl_loss


class QIVAE:
    """
    High-level QI-VAE interface for anomaly detection.
    
    Usage:
        qivae = QIVAE(config)
        qivae.fit(X_train)
        anomaly_scores = qivae.predict_anomaly_scores(X_test)
        predictions = qivae.predict(X_test)
    """
    
    def __init__(self, config: Optional[QIVAEConfig] = None):
        """
        Initialize QI-VAE.
        
        Args:
            config: QI-VAE configuration
        """
        check_torch()
        
        self.config = config or QIVAEConfig()
        self.model: Optional[QuantumInspiredVAE] = None
        self.optimizer = None
        self.anomaly_threshold: float = 0.0
        self._is_fitted = False
        self.train_losses: List[float] = []
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    def _build_model(self) -> None:
        """Build the VAE model."""
        self.model = QuantumInspiredVAE(self.config)
        self.model.to(self.device)
        self.optimizer = torch.optim.Adam(
            self.model.parameters(),
            lr=self.config.learning_rate,
        )
    
    def fit(
        self,
        X_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        verbose: bool = True,
    ) -> float:
        """
        Train the QI-VAE.
        
        For anomaly detection, train only on normal samples.
        
        Args:
            X_train: Training data (preferably normal samples only)
            X_val: Validation data
            verbose: Print training progress
        
        Returns:
            Training time in seconds
        """
        self._build_model()
        
        # Prepare data
        X_tensor = torch.FloatTensor(X_train).to(self.device)
        dataset = TensorDataset(X_tensor)
        dataloader = DataLoader(
            dataset,
            batch_size=self.config.batch_size,
            shuffle=True,
        )
        
        if X_val is not None:
            X_val_tensor = torch.FloatTensor(X_val).to(self.device)
        
        start_time = time.time()
        self.train_losses = []
        
        for epoch in range(self.config.epochs):
            self.model.train()
            epoch_loss = 0.0
            n_batches = 0
            
            for batch in dataloader:
                x = batch[0]
                
                self.optimizer.zero_grad()
                reconstruction, mu, logvar = self.model(x)
                loss, recon_loss, kl_loss = vae_loss(
                    reconstruction, x, mu, logvar, self.config.beta
                )
                
                loss.backward()
                self.optimizer.step()
                
                epoch_loss += loss.item()
                n_batches += 1
            
            avg_loss = epoch_loss / n_batches
            self.train_losses.append(avg_loss)
            
            if verbose and (epoch + 1) % 10 == 0:
                val_str = ""
                if X_val is not None:
                    self.model.eval()
                    with torch.no_grad():
                        val_recon, val_mu, val_logvar = self.model(X_val_tensor)
                        val_loss, _, _ = vae_loss(
                            val_recon, X_val_tensor, val_mu, val_logvar,
                            self.config.beta
                        )
                        val_str = f", Val Loss: {val_loss.item():.4f}"
                
                print(f"Epoch {epoch + 1}/{self.config.epochs}: "
                      f"Loss: {avg_loss:.4f}{val_str}")
        
        train_time = time.time() - start_time
        
        # Set anomaly threshold based on training reconstruction errors
        self._set_anomaly_threshold(X_train)
        
        self._is_fitted = True
        return train_time
    
    def _set_anomaly_threshold(self, X_train: np.ndarray) -> None:
        """Set anomaly threshold based on training data reconstruction errors."""
        errors = self.reconstruction_errors(X_train)
        self.anomaly_threshold = np.percentile(
            errors,
            self.config.anomaly_threshold_percentile
        )
    
    def reconstruction_errors(self, X: np.ndarray) -> np.ndarray:
        """
        Compute reconstruction errors for samples.
        
        Args:
            X: Input samples
        
        Returns:
            Array of reconstruction errors (anomaly scores)
        """
        if not self._is_fitted:
            raise RuntimeError("QIVAE not fitted. Call fit() first.")
        
        self.model.eval()
        X_tensor = torch.FloatTensor(X).to(self.device)
        
        with torch.no_grad():
            errors = self.model.reconstruction_error(X_tensor)
        
        return errors.cpu().numpy()
    
    def predict_anomaly_scores(self, X: np.ndarray) -> np.ndarray:
        """
        Predict anomaly scores (reconstruction errors).
        
        Higher scores indicate more anomalous samples.
        
        Args:
            X: Input samples
        
        Returns:
            Array of anomaly scores
        """
        return self.reconstruction_errors(X)
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Predict binary labels (0=normal, 1=anomaly).
        
        Args:
            X: Input samples
        
        Returns:
            Binary predictions
        """
        errors = self.reconstruction_errors(X)
        return (errors > self.anomaly_threshold).astype(int)
    
    def encode(self, X: np.ndarray) -> np.ndarray:
        """
        Encode samples to latent space.
        
        Args:
            X: Input samples
        
        Returns:
            Latent representations
        """
        if not self._is_fitted:
            raise RuntimeError("QIVAE not fitted. Call fit() first.")
        
        self.model.eval()
        X_tensor = torch.FloatTensor(X).to(self.device)
        
        with torch.no_grad():
            z = self.model.encode(X_tensor)
        
        return z.cpu().numpy()
    
    def evaluate(
        self,
        X_test: np.ndarray,
        y_test: np.ndarray,
        train_time: float = 0.0,
    ) -> QIVAEResult:
        """
        Evaluate QI-VAE on test set.
        
        Args:
            X_test: Test features
            y_test: Test labels (0=normal, 1=anomaly)
            train_time: Training time
        
        Returns:
            QIVAEResult with metrics
        """
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
        
        y_pred = self.predict(X_test)
        errors = self.reconstruction_errors(X_test)
        
        # Validation loss
        self.model.eval()
        X_tensor = torch.FloatTensor(X_test).to(self.device)
        with torch.no_grad():
            val_recon, val_mu, val_logvar = self.model(X_tensor)
            val_loss, _, _ = vae_loss(
                val_recon, X_tensor, val_mu, val_logvar, self.config.beta
            )
        
        return QIVAEResult(
            train_loss=self.train_losses[-1] if self.train_losses else 0.0,
            val_loss=val_loss.item(),
            reconstruction_errors=errors,
            anomaly_threshold=self.anomaly_threshold,
            accuracy=accuracy_score(y_test, y_pred),
            precision=precision_score(y_test, y_pred, zero_division=0),
            recall=recall_score(y_test, y_pred, zero_division=0),
            f1_score=f1_score(y_test, y_pred, zero_division=0),
            train_time=train_time,
            config=self.config,
        )
    
    def fit_evaluate(
        self,
        X_train: np.ndarray,
        X_test: np.ndarray,
        y_test: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        verbose: bool = True,
    ) -> QIVAEResult:
        """Fit and evaluate in one step."""
        train_time = self.fit(X_train, X_val, verbose)
        return self.evaluate(X_test, y_test, train_time)


if QISKIT_AVAILABLE:
    
    def create_quantum_encoder_circuit(
        n_qubits: int,
        n_features: int,
        reps: int = 2,
    ) -> QuantumCircuit:
        """
        Create a parameterized quantum circuit for encoding.
        
        This circuit can be used as an alternative encoder in hybrid models.
        
        Args:
            n_qubits: Number of qubits
            n_features: Number of input features
            reps: Number of circuit repetitions
        
        Returns:
            Parameterized QuantumCircuit
        """
        qc = QuantumCircuit(n_qubits)
        
        # Input parameters (features)
        inputs = [Parameter(f"x_{i}") for i in range(n_features)]
        
        # Trainable parameters
        params = []
        
        for r in range(reps):
            # Encoding layer: RY rotations based on input
            for i in range(min(n_qubits, n_features)):
                qc.ry(inputs[i], i)
            
            # Entanglement layer: CNOT ladder
            for i in range(n_qubits - 1):
                qc.cx(i, i + 1)
            
            # Variational layer: RZ rotations (trainable)
            layer_params = [Parameter(f"θ_{r}_{i}") for i in range(n_qubits)]
            params.extend(layer_params)
            for i, p in enumerate(layer_params):
                qc.rz(p, i)
            
            if r < reps - 1:
                qc.barrier()
        
        return qc


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(__file__).rsplit("/", 3)[0])
    
    from src.preprocessing.data_loader import generate_synthetic_data, DataLoader
    
    print("Testing QI-VAE for anomaly detection...")
    
    # Generate synthetic data
    print("\n1. Generating synthetic data...")
    X, y = generate_synthetic_data(n_samples=2000)
    
    # Prepare data
    print("2. Preparing data...")
    loader = DataLoader()
    data = loader.prepare_data(X, y, binary=True)
    
    # For anomaly detection, train on normal samples only
    normal_mask = data["y_train"] == 0
    X_train_normal = data["X_train"][normal_mask]
    print(f"   Training on {len(X_train_normal)} normal samples")
    
    # Configure and train QI-VAE
    print("\n3. Training QI-VAE...")
    config = QIVAEConfig(
        input_dim=data["X_train"].shape[1],
        latent_dim=4,
        hidden_dims=(64, 32),
        epochs=30,
        batch_size=32,
        beta=1.0,
        anomaly_threshold_percentile=95.0,
    )
    
    qivae = QIVAE(config)
    result = qivae.fit_evaluate(
        X_train_normal,
        data["X_test"],
        data["y_test"],
        verbose=True,
    )
    
    print("\n" + "=" * 60)
    print("QI-VAE RESULTS")
    print("=" * 60)
    print(f"Training Loss:      {result.train_loss:.4f}")
    print(f"Validation Loss:    {result.val_loss:.4f}")
    print(f"Anomaly Threshold:  {result.anomaly_threshold:.4f}")
    print(f"Accuracy:           {result.accuracy:.4f}")
    print(f"Precision:          {result.precision:.4f}")
    print(f"Recall:             {result.recall:.4f}")
    print(f"F1 Score:           {result.f1_score:.4f}")
    print(f"Training Time:      {result.train_time:.2f}s")
    print("=" * 60)
    
    # Analyze latent space
    print("\n4. Analyzing latent space...")
    z_test = qivae.encode(data["X_test"])
    print(f"   Latent shape: {z_test.shape}")
    print(f"   Latent mean: {z_test.mean(axis=0)}")
    print(f"   Latent std: {z_test.std(axis=0)}")
