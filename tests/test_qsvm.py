
import pytest
from qzero.quantum.qsvm import QSVM, QSVMConfig


def test_qsvm_initialization():
    qsvm = QSVM(config=QSVMConfig(n_qubits=4))
    assert qsvm is not None
    assert qsvm.config.n_qubits == 4


def test_qsvm_fit():
    """TODO: requires synthetic data fixture to call qsvm.fit()."""
    pass
