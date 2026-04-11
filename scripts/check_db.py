"""Check DB path and presence for debugging."""
import sys, os
ROOT = os.path.dirname(os.path.dirname(__file__))
SRC = os.path.join(ROOT, 'src')
if SRC not in sys.path:
    sys.path.insert(0, SRC)
from agent_app import db
p = db.get_db_path()
print('db url:', p)
if p.startswith('sqlite:///'):
    path = p.replace('sqlite:///','')
    print('sqlite file path:', path)
    print('exists:', os.path.exists(path))
    print('dir exists:', os.path.exists(os.path.dirname(path)))
    if os.path.exists(os.path.dirname(path)):
        print('dir listing:', os.listdir(os.path.dirname(path)))
else:
    print('non-sqlite DB configured')
