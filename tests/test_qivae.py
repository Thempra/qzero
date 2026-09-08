
import pytest
from qzero.quantum.qivae import QIVAE, QIVAEConfig

def test_qivae_initialization():
    qivae = QIVAE(config=QIVAEConfig(n_qubits=4))
    assert qivae is not None
    assert qivae.config.n_qubits == 4
