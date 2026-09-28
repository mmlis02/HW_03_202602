# Permite importar el paquete compartido `comun/` (en la raíz del repositorio) desde cada tarea.
import sys
from pathlib import Path

_RAIZ = str(Path(__file__).resolve().parents[2])
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)
