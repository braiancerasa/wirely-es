"""Inicia Wirely. En la primera ejecución instala automáticamente todo lo que necesita.

    python start.py                   (o haga doble clic en run_wirely.bat en Windows)
    python start.py mi_circuito.wirely
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from wirely.bootstrap import launch

if __name__ == "__main__":
    launch()
