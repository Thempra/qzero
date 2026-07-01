
import pytest
from src.quantum.qsvm import QSVM, QSVMConfig

def test_qsvm_initialization():
    qsvm = QSVM(config=QSVMConfig(n_qubits=4))
    assert qsvm is not None
    assert qsvm.config.n_qubits == 4

def test_qsvm_train():
    qsvm = QSVM(config=QSVMConfig(n_qubits=4))
    result = qsvm.train(X_train, y_train)
    assert result.accuracy >= 0.8
