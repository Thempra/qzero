"""
Quantum feature maps for encoding classical data.

Updated for Qiskit 2.1+ using functional APIs instead of deprecated classes.
"""

import numpy as np
from enum import Enum
from typing import Optional, Callable, Dict, Any, Union

try:
    from qiskit import QuantumCircuit
    from qiskit.circuit import Parameter
    # Try new functional API (Qiskit 2.1+)
    try:
        from qiskit.circuit.library import (
            zz_feature_map,
            z_feature_map,
            pauli_feature_map,
        )
        USE_FUNCTIONAL_API = True
    except ImportError:
        # Fall back to class-based API (older Qiskit)
        from qiskit.circuit.library import (
            ZZFeatureMap,
            ZFeatureMap,
            PauliFeatureMap,
        )
        USE_FUNCTIONAL_API = False
    QISKIT_AVAILABLE = True
except ImportError:
    QISKIT_AVAILABLE = False
    USE_FUNCTIONAL_API = False


class FeatureMapType(Enum):
    """Available quantum feature map types."""
    Z = "z"
    ZZ = "zz"
    ZZZ = "zzz"
    PAULI = "pauli"
    CUSTOM_ENTANGLED = "custom_entangled"


def check_qiskit():
    """Raise if Qiskit not available."""
    if not QISKIT_AVAILABLE:
        raise ImportError(
            "Qiskit not installed. Run: pip install qiskit qiskit-machine-learning"
        )


def create_feature_map(
    n_qubits: int,
    feature_map_type: FeatureMapType = FeatureMapType.ZZ,
    reps: int = 2,
    entanglement: str = "linear",
    data_map_func: Optional[Callable] = None,
) -> "QuantumCircuit":
    """
    Create a quantum feature map for data encoding.
    
    Args:
        n_qubits: Number of qubits (= number of features)
        feature_map_type: Type of feature map
        reps: Number of repetitions
        entanglement: Entanglement pattern ("linear", "full", "circular")
        data_map_func: Custom data mapping function
    
    Returns:
        Qiskit QuantumCircuit for the feature map
    """
    check_qiskit()
    
    if USE_FUNCTIONAL_API:
        return _create_feature_map_functional(
            n_qubits, feature_map_type, reps, entanglement
        )
    else:
        return _create_feature_map_class_based(
            n_qubits, feature_map_type, reps, entanglement
        )


def _create_feature_map_functional(
    n_qubits: int,
    feature_map_type: FeatureMapType,
    reps: int,
    entanglement: str,
) -> "QuantumCircuit":
    """Create feature map using Qiskit 2.1+ functional API."""
    
    if feature_map_type == FeatureMapType.Z:
        return z_feature_map(
            feature_dimension=n_qubits,
            reps=reps,
        )
    
    elif feature_map_type == FeatureMapType.ZZ:
        return zz_feature_map(
            feature_dimension=n_qubits,
            reps=reps,
            entanglement=entanglement,
        )
    
    elif feature_map_type == FeatureMapType.PAULI:
        return pauli_feature_map(
            feature_dimension=n_qubits,
            reps=reps,
            entanglement=entanglement,
            paulis=["Z", "ZZ"],
        )
    
    elif feature_map_type == FeatureMapType.ZZZ:
        return pauli_feature_map(
            feature_dimension=n_qubits,
            reps=reps,
            entanglement=entanglement,
            paulis=["Z", "ZZ", "ZZZ"],
        )
    
    elif feature_map_type == FeatureMapType.CUSTOM_ENTANGLED:
        return _create_custom_entangled_map(n_qubits, reps)
    
    else:
        raise ValueError(f"Unknown feature map type: {feature_map_type}")


def _create_feature_map_class_based(
    n_qubits: int,
    feature_map_type: FeatureMapType,
    reps: int,
    entanglement: str,
) -> "QuantumCircuit":
    """Create feature map using older class-based API (Qiskit < 2.1)."""
    import warnings
    # Suppress deprecation warnings for older API
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        
        if feature_map_type == FeatureMapType.Z:
            return ZFeatureMap(
                feature_dimension=n_qubits,
                reps=reps,
            )
        
        elif feature_map_type == FeatureMapType.ZZ:
            return ZZFeatureMap(
                feature_dimension=n_qubits,
                reps=reps,
                entanglement=entanglement,
            )
        
        elif feature_map_type == FeatureMapType.PAULI:
            return PauliFeatureMap(
                feature_dimension=n_qubits,
                reps=reps,
                entanglement=entanglement,
                paulis=["Z", "ZZ"],
            )
        
        elif feature_map_type == FeatureMapType.ZZZ:
            return PauliFeatureMap(
                feature_dimension=n_qubits,
                reps=reps,
                entanglement=entanglement,
                paulis=["Z", "ZZ", "ZZZ"],
            )
        
        elif feature_map_type == FeatureMapType.CUSTOM_ENTANGLED:
            return _create_custom_entangled_map(n_qubits, reps)
        
        else:
            raise ValueError(f"Unknown feature map type: {feature_map_type}")


def _create_custom_entangled_map(n_qubits: int, reps: int = 2) -> "QuantumCircuit":
    """
    Create a custom feature map optimized for anomaly detection.
    
    This map uses:
    - RY rotations for initial encoding
    - CNOT ladder for entanglement
    - RZ rotations for phase encoding
    - Additional CZ gates for correlation capture
    """
    check_qiskit()
    
    qc = QuantumCircuit(n_qubits)
    
    # Create parameters for features
    features = [Parameter(f"x[{i}]") for i in range(n_qubits)]
    
    for rep in range(reps):
        # Layer 1: RY encoding
        for i, f in enumerate(features):
            qc.ry(f, i)
        
        # Layer 2: Entanglement (CNOT ladder)
        for i in range(n_qubits - 1):
            qc.cx(i, i + 1)
        
        # Layer 3: RZ phase encoding (with nonlinear transformation)
        for i, f in enumerate(features):
            # Use product of features for nonlinearity
            if i < n_qubits - 1:
                qc.rz(f * features[(i + 1) % n_qubits], i)
            else:
                qc.rz(f, i)
        
        # Layer 4: Additional correlations via CZ
        for i in range(0, n_qubits - 1, 2):
            qc.cz(i, i + 1)
        
        if rep < reps - 1:
            qc.barrier()
    
    return qc


def get_feature_map_info(
    feature_map_or_type: Union["QuantumCircuit", FeatureMapType],
    n_qubits: int = 4,
    reps: int = 2,
) -> Dict[str, Any]:
    """
    Get information about a feature map circuit.
    
    Args:
        feature_map_or_type: Qiskit circuit or FeatureMapType
        n_qubits: Number of qubits (if type provided)
        reps: Number of reps (if type provided)
    
    Returns:
        Dictionary with circuit information
    """
    check_qiskit()
    
    # If type provided, create the circuit first
    if isinstance(feature_map_or_type, FeatureMapType):
        feature_map = create_feature_map(n_qubits, feature_map_or_type, reps)
    else:
        feature_map = feature_map_or_type
    
    return {
        "n_qubits": feature_map.num_qubits,
        "depth": feature_map.depth(),
        "n_parameters": feature_map.num_parameters,
        "n_gates": len(feature_map.data),
        "gate_counts": dict(feature_map.count_ops()),
    }


if __name__ == "__main__":
    if QISKIT_AVAILABLE:
        print(f"Testing feature maps (functional API: {USE_FUNCTIONAL_API})...")
        
        for fm_type in FeatureMapType:
            try:
                fm = create_feature_map(4, fm_type, reps=2)
                info = get_feature_map_info(fm)
                print(f"\n{fm_type.value}:")
                print(f"  Qubits: {info['n_qubits']}, Depth: {info['depth']}")
                print(f"  Parameters: {info['n_parameters']}, Gates: {info['n_gates']}")
            except Exception as e:
                print(f"\n{fm_type.value}: Error - {e}")
    else:
        print("Qiskit not available. Install with: pip install qiskit")
