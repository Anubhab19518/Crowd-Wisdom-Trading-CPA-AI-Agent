"""Test script: call ApifyAdapter.run_actor and print results for debugging."""
import sys
import os
import traceback
from dotenv import load_dotenv
ROOT = os.path.dirname(os.path.dirname(__file__))
SRC = os.path.join(ROOT, 'src')
if SRC not in sys.path:
    sys.path.insert(0, SRC)
load_dotenv()
from agent_app.adapters import ApifyAdapter
import json

def main():
    try:
        ap = ApifyAdapter()
        print('APIFY_TOKEN present:', bool(os.environ.get('APIFY_TOKEN')))
        print('ApifyAdapter.available():', ap.available())
        actor = os.environ.get('APIFY_FBX_ACTOR_ID') or os.environ.get('APIFY_FBX_ACTOR')
        print('Actor id:', actor)
        res = ap.run_actor(actor, {'maxItems': 2})
        print('Returned type:', type(res))
        print(json.dumps(res, indent=2, ensure_ascii=False))
    except Exception:
        traceback.print_exc()

if __name__ == '__main__':
    main()
