import sys
from pathlib import Path

# Permite importar main, agente y almacenamiento desde backend/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
