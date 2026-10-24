"""Start Wirely. On the first run this installs everything it needs automatically.

    python start.py                   (or double-click run_wirely.bat on Windows)
    python start.py my_circuit.wirely
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from wirely.bootstrap import launch

if __name__ == "__main__":
    launch()
