"""
CLI de QZero - Entrypoint principal
"""
import sys
from pathlib import Path

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Ejecutar el CLI directamente
if __name__ == '__main__':
    # Modificar sys.argv para eliminar el primer argumento (qzero)
    sys.argv = sys.argv[1:]

    # Importar y ejecutar el main del CLI
    from qzero import main
    sys.exit(main())