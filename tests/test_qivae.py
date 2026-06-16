"""
Tests for Quantum-Inspired Variational Autoencoder (QI-VAE) module.
"""

import pytest
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from preprocessing.data_loader import generate_synthetic_data, DataLoader

# Conditional imports - tests skip if PyTorch not available
try:
    import torch
    from quantum.qivae import (
        QIVAE,
        QIVAEConfig,
        QIVAEResult,
        QuantumInspiredVAE,
        Encoder,
        Decoder,
        vae_loss,
        TORCH_AVAILABLE,
    )
except ImportError:
    TORCH_AVAILABLE = False


# Skip all tests if PyTorch not available
pytestmark = pytest.mark.skipif(
    not TORCH_AVAILABLE,
    reason="PyTorch not installed"
)


class TestQIVAEConfig:
    """Tests for QIVAEConfig dataclass."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = QIVAEConfig()
        
        assert config.input_dim == 14
        assert config.latent_dim == 4
        assert config.hidden_dims == (64, 32)
        assert config.learning_rate == 1e-3
        assert config.batch_size == 32
        assert config.epochs == 75
        assert config.beta == 0.5
        assert config.anomaly_threshold_percentile == 85.0
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = QIVAEConfig(
            input_dim=20,
            latent_dim=8,
            hidden_dims=(128, 64, 32),
            epochs=100,
            beta=0.5,
        )
        
        assert config.input_dim == 20
        assert config.latent_dim == 8
        assert config.hidden_dims == (128, 64, 32)
        assert config.epochs == 100
        assert config.beta == 0.5


class TestEncoder:
    """Tests for Encoder network."""
    
    def test_encoder_output_shape(self):
        """Test encoder produces correct output shapes."""
        encoder = Encoder(
            input_dim=14,
            hidden_dims=(64, 32),
            latent_dim=4,
        )
        
        x = torch.randn(32, 14)
        mu, logvar = encoder(x)
        
        assert mu.shape == (32, 4)
        assert logvar.shape == (32, 4)
    
    def test_encoder_different_dims(self):
        """Test encoder with different dimensions."""
        for input_dim in [10, 14, 20]:
            for latent_dim in [2, 4, 8]:
                encoder = Encoder(
                    input_dim=input_dim,
                    hidden_dims=(32, 16),
                    latent_dim=latent_dim,
                )
                
                x = torch.randn(16, input_dim)
                mu, logvar = encoder(x)
                
                assert mu.shape == (16, latent_dim)
                assert logvar.shape == (16, latent_dim)


class TestDecoder:
    """Tests for Decoder network."""
    
    def test_decoder_output_shape(self):
        """Test decoder produces correct output shape."""
        decoder = Decoder(
            latent_dim=4,
            hidden_dims=(64, 32),
            output_dim=14,
        )
        
        z = torch.randn(32, 4)
        reconstruction = decoder(z)
        
        assert reconstruction.shape == (32, 14)
    
    def test_decoder_different_dims(self):
        """Test decoder with different dimensions."""
        for latent_dim in [2, 4, 8]:
            for output_dim in [10, 14, 20]:
                decoder = Decoder(
                    latent_dim=latent_dim,
                    hidden_dims=(32, 16),
                    output_dim=output_dim,
                )
                
                z = torch.randn(16, latent_dim)
                output = decoder(z)
                
                assert output.shape == (16, output_dim)


class TestQuantumInspiredVAE:
    """Tests for QuantumInspiredVAE model."""
    
    @pytest.fixture
    def model(self):
        """Create a QI-VAE model for testing."""
        config = QIVAEConfig(input_dim=14, latent_dim=4)
        return QuantumInspiredVAE(config)
    
    def test_forward_shapes(self, model):
        """Test forward pass output shapes."""
        x = torch.randn(32, 14)
        reconstruction, mu, logvar = model(x)
        
        assert reconstruction.shape == (32, 14)
        assert mu.shape == (32, 4)
        assert logvar.shape == (32, 4)
    
    def test_encode(self, model):
        """Test encoding to latent space."""
        x = torch.randn(32, 14)
        z = model.encode(x)
        
        assert z.shape == (32, 4)
    
    def test_decode(self, model):
        """Test decoding from latent space."""
        z = torch.randn(32, 4)
        reconstruction = model.decode(z)
        
        assert reconstruction.shape == (32, 14)
    
    def test_reconstruction_error(self, model):
        """Test reconstruction error computation."""
        model.eval()  # Set to eval mode
        x = torch.randn(32, 14)
        errors = model.reconstruction_error(x)
        
        assert errors.shape == (32,)
        assert (errors >= 0).all()  # MSE should be non-negative
    
    def test_reparameterize_deterministic(self, model):
        """Test reparameterization with quantum noise disabled."""
        mu = torch.zeros(16, 4)
        logvar = torch.zeros(16, 4)  # std = 1
        
        torch.manual_seed(42)
        z1 = model.reparameterize(mu, logvar, quantum_noise=False)
        
        torch.manual_seed(42)
        z2 = model.reparameterize(mu, logvar, quantum_noise=False)
        
        torch.testing.assert_close(z1, z2)


class TestVAELoss:
    """Tests for VAE loss function."""
    
    def test_loss_components(self):
        """Test that loss has correct components."""
        x = torch.randn(32, 14)
        reconstruction = torch.randn(32, 14)
        mu = torch.randn(32, 4)
        logvar = torch.randn(32, 4)
        
        total, recon, kl = vae_loss(reconstruction, x, mu, logvar)
        
        # All losses should be scalar tensors
        assert total.dim() == 0
        assert recon.dim() == 0
        assert kl.dim() == 0
        
        # Reconstruction loss should be non-negative
        assert recon >= 0
    
    def test_kl_zero_for_standard_normal(self):
        """Test KL divergence is near zero for standard normal."""
        x = torch.randn(100, 14)
        reconstruction = x  # Perfect reconstruction
        mu = torch.zeros(100, 4)
        logvar = torch.zeros(100, 4)  # std = 1
        
        _, _, kl = vae_loss(reconstruction, x, mu, logvar)
        
        # KL should be close to 0 for standard normal prior
        assert kl.abs() < 0.1
    
    def test_beta_weighting(self):
        """Test that beta correctly weights KL term."""
        x = torch.randn(32, 14)
        reconstruction = torch.randn(32, 14)
        mu = torch.randn(32, 4) * 2  # Non-zero mean
        logvar = torch.randn(32, 4)
        
        _, recon1, kl1 = vae_loss(reconstruction, x, mu, logvar, beta=1.0)
        total2, recon2, kl2 = vae_loss(reconstruction, x, mu, logvar, beta=2.0)
        
        # KL should be the same, but total should differ
        torch.testing.assert_close(kl1, kl2)
        torch.testing.assert_close(recon1, recon2)
        
        expected_total = recon2 + 2.0 * kl2
        torch.testing.assert_close(total2, expected_total)


class TestQIVAE:
    """Tests for high-level QIVAE interface."""
    
    @pytest.fixture
    def sample_data(self):
        """Generate sample data for tests."""
        X, y = generate_synthetic_data(n_samples=300)
        loader = DataLoader()
        data = loader.prepare_data(X, y, binary=True)
        return data
    
    @pytest.fixture
    def qivae(self, sample_data):
        """Create and train a QIVAE model."""
        config = QIVAEConfig(
            input_dim=sample_data["X_train"].shape[1],
            latent_dim=4,
            epochs=5,  # Few epochs for fast testing
            batch_size=32,
        )
        qivae = QIVAE(config)
        
        # Train on normal samples only
        normal_mask = sample_data["y_train"] == 0
        X_normal = sample_data["X_train"][normal_mask]
        qivae.fit(X_normal, verbose=False)
        
        return qivae
    
    def test_qivae_initialization(self):
        """Test QIVAE initialization."""
        config = QIVAEConfig(input_dim=14, latent_dim=4)
        qivae = QIVAE(config)
        
        assert qivae.config.input_dim == 14
        assert qivae._is_fitted is False
    
    def test_fit_returns_time(self, sample_data):
        """Test that fit returns training time."""
        config = QIVAEConfig(
            input_dim=sample_data["X_train"].shape[1],
            epochs=2,
        )
        qivae = QIVAE(config)
        
        normal_mask = sample_data["y_train"] == 0
        train_time = qivae.fit(
            sample_data["X_train"][normal_mask],
            verbose=False
        )
        
        assert isinstance(train_time, float)
        assert train_time > 0
        assert qivae._is_fitted is True
    
    def test_predict_anomaly_scores(self, qivae, sample_data):
        """Test anomaly score prediction."""
        scores = qivae.predict_anomaly_scores(sample_data["X_test"])
        
        assert len(scores) == len(sample_data["X_test"])
        assert (scores >= 0).all()  # MSE should be non-negative
    
    def test_predict_binary(self, qivae, sample_data):
        """Test binary prediction."""
        predictions = qivae.predict(sample_data["X_test"])
        
        assert len(predictions) == len(sample_data["X_test"])
        assert set(predictions).issubset({0, 1})
    
    def test_predict_before_fit_raises(self, sample_data):
        """Test that predict before fit raises error."""
        qivae = QIVAE()
        
        with pytest.raises(RuntimeError):
            qivae.predict(sample_data["X_test"])
    
    def test_encode(self, qivae, sample_data):
        """Test encoding to latent space."""
        z = qivae.encode(sample_data["X_test"])
        
        assert z.shape == (len(sample_data["X_test"]), 4)
    
    def test_encode_before_fit_raises(self, sample_data):
        """Test that encode before fit raises error."""
        qivae = QIVAE()
        
        with pytest.raises(RuntimeError):
            qivae.encode(sample_data["X_test"])
    
    def test_anomaly_threshold_set(self, qivae):
        """Test that anomaly threshold is set after training."""
        assert qivae.anomaly_threshold > 0
    
    def test_train_losses_recorded(self, qivae):
        """Test that training losses are recorded."""
        assert len(qivae.train_losses) > 0
        assert all(isinstance(l, float) for l in qivae.train_losses)
    
    def test_evaluate_returns_result(self, qivae, sample_data):
        """Test that evaluate returns QIVAEResult."""
        result = qivae.evaluate(
            sample_data["X_test"],
            sample_data["y_test"],
            train_time=1.0
        )
        
        assert isinstance(result, QIVAEResult)
        assert 0 <= result.accuracy <= 1
        assert 0 <= result.f1_score <= 1
        assert result.train_time == 1.0
    
    def test_result_to_dict(self, qivae, sample_data):
        """Test QIVAEResult to_dict conversion."""
        result = qivae.evaluate(
            sample_data["X_test"],
            sample_data["y_test"]
        )
        
        d = result.to_dict()
        
        assert "accuracy" in d
        assert "precision" in d
        assert "recall" in d
        assert "f1_score" in d
        assert "anomaly_threshold" in d


class TestQIVAEIntegration:
    """Integration tests for full QI-VAE pipeline."""
    
    @pytest.mark.slow
    def test_full_pipeline(self):
        """Test complete anomaly detection pipeline."""
        # Generate data
        X, y = generate_synthetic_data(n_samples=500)
        
        # Prepare
        loader = DataLoader()
        data = loader.prepare_data(X, y, binary=True)
        
        # Train on normal samples only (anomaly detection setup)
        normal_mask = data["y_train"] == 0
        X_train_normal = data["X_train"][normal_mask]
        
        # Configure and train
        config = QIVAEConfig(
            input_dim=data["X_train"].shape[1],
            latent_dim=4,
            hidden_dims=(32, 16),
            epochs=20,
            batch_size=32,
            anomaly_threshold_percentile=90.0,
        )
        
        qivae = QIVAE(config)
        result = qivae.fit_evaluate(
            X_train_normal,
            data["X_test"],
            data["y_test"],
            verbose=False,
        )
        
        # Should achieve reasonable performance
        assert result.accuracy > 0.3  # Better than always predicting one class
        assert result.train_time > 0
        assert len(result.reconstruction_errors) == len(data["X_test"])
    
    def test_latent_space_structure(self):
        """Test that latent space has meaningful structure."""
        # Generate data with clear separation
        X, y = generate_synthetic_data(n_samples=500)
        loader = DataLoader()
        data = loader.prepare_data(X, y, binary=True)
        
        # Train
        config = QIVAEConfig(
            input_dim=data["X_train"].shape[1],
            latent_dim=4,
            epochs=30,
        )
        
        qivae = QIVAE(config)
        normal_mask = data["y_train"] == 0
        qivae.fit(data["X_train"][normal_mask], verbose=False)
        
        # Encode test data
        z = qivae.encode(data["X_test"])
        
        # Latent space should have reasonable statistics
        assert z.shape[1] == 4
        assert np.isfinite(z).all()
        assert z.std() > 0.1  # Should have some variance


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
