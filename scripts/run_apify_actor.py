"""Run configured Apify actor via HTTP run-sync-get-dataset-items and save dataset.

Usage: set APIFY_TOKEN (or put in .env), then run:
    python scripts\run_apify_actor.py

Optional env vars to tune input: APIFY_FBX_ACTOR_ID, APIFY_COUNTRY, APIFY_MAX_ITEMS
"""
import os
import json
import time
import requests
from pathlib import Path

# Try to load .env automatically if python-dotenv is installed
try:
    from dotenv import load_dotenv
    dotenv_path = Path(__file__).resolve().parent.parent / '.env'
    if dotenv_path.exists():
        load_dotenv(dotenv_path)
except Exception:
    pass

actor_id = os.environ.get('APIFY_FBX_ACTOR_ID', 'parseforge/shiply-com-freight-marketplace-scraper')
actor_id_for_url = actor_id.replace('/', '~')
token = os.environ.get('APIFY_TOKEN')
if not token:
    raise SystemExit('APIFY_TOKEN not set in environment or .env')

input_data = {
    'country': os.environ.get('APIFY_COUNTRY', 'United Kingdom'),
    'maxItems': int(os.environ.get('APIFY_MAX_ITEMS', '10')),
    'maxConcurrency': int(os.environ.get('APIFY_MAX_CONCURRENCY', '5')),
    'requestDelayMs': int(os.environ.get('APIFY_REQUEST_DELAY_MS', '500')),
}

base = os.environ.get('APIFY_API_BASE', 'https://api.apify.com')
url = f"{base}/v2/acts/{actor_id_for_url}/run-sync-get-dataset-items?token={token}"
print('Calling', url)
resp = requests.post(url, json=input_data, timeout=120)
ts = time.strftime('%Y%m%dT%H%M%SZ')
out_dir = os.path.join(os.path.dirname(__file__), '..', 'reports')
os.makedirs(out_dir, exist_ok=True)
path = os.path.join(out_dir, f'apify_dataset_{actor_id_for_url}_{ts}.json')
if resp.status_code in (200, 201):
    try:
        data = resp.json()
    except Exception:
        data = {'output': resp.text}
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, default=str)
    print('Saved dataset to', path)
    # print short summary
    if isinstance(data, list):
        print('Items:', len(data))
        sample = data[:5]
        print('Sample item keys:', [list(it.keys()) for it in sample if isinstance(it, dict)])
    elif isinstance(data, dict) and 'output' in data and isinstance(data['output'], list):
        items = data['output']
        print('Items:', len(items))
        sample = items[:5]
        print('Sample item keys:', [list(it.keys()) for it in sample if isinstance(it, dict)])
    else:
        print('Response shape:', type(data))
else:
    print('HTTP', resp.status_code, resp.text)
