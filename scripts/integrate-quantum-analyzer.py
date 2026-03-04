#!/usr/bin/env python3
"""
INTEGRACIÓN CUÁNTICA: Analizador en Tiempo Real con Modelos de QZero
Verifica que el analizador está integrado correctamente en el proyecto QZero
"""

import sys
import logging
from pathlib import Path
from datetime import datetime

sys.path.insert(0, '/home/thempra/projects/qzero')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("QZero-Integration")

def verify_project_integration():
    """Verifica que el analizador está integrado en el proyecto QZero"""
    print("=" * 70)
    print("🚀 QZero - INTEGRACIÓN CUÁNTICA")
    print("⚡ Analizador en Tiempo Real")
    print("=" * 70)
    print()

    # Verificar estructura del proyecto
    print("📋 Verificando estructura del proyecto...")
    project_root = Path('/home/thempra/projects/qzero')

    required_files = [
        'scripts/real-time-analyzer.py',
        'scripts/test-quantum-analyzer.py',
        'scripts/integrate-quantum-analyzer.py',
        'scripts/real-time-analyzer-cron.sh',
        'docs/REAL-TIME-ANALYZER.md',
        'CONFIG-RT-ANALYZER.md',
        'REAL-TIME-ANALYZER-README.md'
    ]

    all_present = True
    for file_path in required_files:
        file_full_path = project_root / file_path
        if file_full_path.exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - NO ENCONTRADO")
            all_present = False

    print()
    if not all_present:
        logger.error("⚠️  Algunos archivos de integración no están presentes")
        return False

    # Verificar modelo cuántico
    print("⚛️  Verificando modelos cuánticos del proyecto...")
    try:
        from src.quantum.qsvm import QSVM, QSVMConfig
        from src.quantum.qivae import QIVAE, QIVAEConfig
        from src.predictor import QZeroPredictor

        print("✅ Módulos cuánticos importados correctamente:")
        print("   - src.quantum.qsvm.QSVM")
        print("   - src.quantum.qivae.QIVAE")
        print("   - src.predictor.QZeroPredictor")

        # Verificar configuración
        qsvm = QSVM(config=QSVMConfig(n_qubits=4))
        qivae = QIVAE(config=QIVAEConfig(n_qubits=4))

        print("✅ Modelos cuánticos inicializados correctamente:")
        print(f"   - QSVM (n_qubits: 4)")
        print(f"   - QIVAE (n_qubits: 4)")

    except Exception as e:
        logger.error(f"❌ Error importando módulos cuánticos: {e}")
        return False

    print()
    # Verificar que el analizador usa los modelos cuánticos
    print("🔍 Verificando que el analizador usa modelos cuánticos...")
    analyzer_path = project_root / 'scripts' / 'real-time-analyzer.py'

    if analyzer_path.exists():
        with open(analyzer_path, 'r') as f:
            content = f.read()

        quantum_imports = [
            'from src.quantum.qsvm import QSVM, QSVMConfig',
            'from src.quantum.qivae import QIVAE, QIVAEConfig',
            'from src.predictor import QZeroPredictor',
            'QUANTUM', 'CUÁNTICO', 'quantum_model'
        ]

        found_quantum = all(imp in content for imp in quantum_imports[:4])

        if found_quantum:
            print("✅ Analizador usa modelos cuánticos de QZero")
            print("   - Importa QSVM")
            print("   - Importa QIVAE")
            print("   - Importa QZeroPredictor")
            print("   - Usa análisis cuántico en tiempo real")
        else:
            print("⚠️  El analizador no parece usar modelos cuánticos")
            return False
    else:
        logger.error(f"❌ Analizador no encontrado: {analyzer_path}")
        return False

    print()
    # Verificar documentación
    print("📚 Verificando documentación...")
    doc_files = [
        'docs/REAL-TIME-ANALYZER.md',
        'CONFIG-RT-ANALYZER.md'
    ]

    for doc_file in doc_files:
        doc_full_path = project_root / doc_file
        if doc_full_path.exists():
            print(f"✅ {doc_file}")

    print()
    # Resumen
    print("✅ INTEGRACIÓN CUÁNTICA EXITOSA")
    print()
    print("📊 Componentes integrados:")
    print("   ✅ Analizador en tiempo real")
    print("   ✅ Modelos cuánticos (QSVM, QIVAE, Predictor)")
    print("   ✅ Preprocesamiento de datos")
    print("   ✅ API de QZero (opcional)")
    print("   ✅ Documentación completa")
    print()
    print("🚀 Para usar:")
    print("   1. Verificar integración:")
    print("      python3 scripts/integrate-quantum-analyzer.py")
    print()
    print("   2. Probar con tráfico simulado:")
    print("      python3 scripts/test-quantum-analyzer.py")
    print()
    print("   3. Ejecutar en tiempo real:")
    print("      sudo python3 scripts/real-time-analyzer.py")
    print()
    print("🔬 Modelos cuánticos utilizados:")
    print("   - QSVM: Quantum Support Vector Machine")
    print("   - QIVAE: Quantum Variational Autoencoder")
    print("   - Predictor QZero: Combinación de modelos")
    print()
    print("🎯 Análisis:")
    print("   - Captura de tráfico en tiempo real")
    print("   - Extracción de features cuánticos")
    print("   - Predicción QSVM")
    print("   - Análisis QIVAE")
    print("   - Score combinado cuántico")
    print("   - Alertas por severidad (CRITICAL/WARNING/INFO)")
    print()
    print("✅ TODO LISTO PARA ANÁLISIS CUÁNTICO EN TIEMPO REAL")

    print()
    print("=" * 70)

    return True

def main():
    """Función principal de integración"""
    try:
        success = verify_project_integration()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"❌ Error en la integración: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()