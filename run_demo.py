"""Top-level runner that adds `src` to PYTHONPATH and runs the demo.

Use: python run_demo.py
"""
import os
import sys

ROOT = os.path.dirname(__file__)
SRC = os.path.join(ROOT, 'src')
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from agent_app import main


if __name__ == '__main__':
    main.run_demo()
