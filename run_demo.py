"""Top-level runner that adds `src` to PYTHONPATH and runs the demo.

Use: python run_demo.py
"""
import os
import sys

ROOT = os.path.dirname(__file__)
SRC = os.path.join(ROOT, 'src')
if SRC not in sys.path:
    sys.path.insert(0, SRC)

# Force skipping sample input when running this top-level demo runner
os.environ.setdefault('SKIP_SAMPLE_INPUT', '1')

from agent_app import main


if __name__ == '__main__':
    try:
        main.run_demo()
    except Exception as e:
        # best-effort logging to file/console
        import logging, traceback
        logging.getLogger('run_demo').exception('Unhandled error in run_demo: %s', e)
        traceback.print_exc()
        raise
