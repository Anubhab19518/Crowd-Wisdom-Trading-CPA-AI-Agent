"""Run the demo pipeline and print a concise summary to the console.

Usage: python scripts/run_demo_summary.py
"""
from pathlib import Path
import json
import os
import sys
from dotenv import load_dotenv

# ensure src on path
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

load_dotenv(dotenv_path=ROOT / '.env')

from agent_app.hermes_integration import run_workflow
from sqlalchemy import create_engine, text


def main():
    samples = ROOT / 'samples' / 'sample_input.json'
    print('Running demo pipeline...')
    report_path = run_workflow(str(samples))
    print(f'Generated report: {report_path}')

    # print report summary
    try:
        with open(report_path, 'r', encoding='utf-8') as f:
            report = json.load(f)
    except Exception as e:
        print('Failed to read report:', e)
        return

    # new report shape: { meta: {...}, analysis: {...} }
    analysis = report.get('analysis', {})
    stats = analysis.get('stats', {})
    anomalies = analysis.get('anomalies', []) or []
    market = analysis.get('market', {}) or {}

    print('\n--- Report Summary ---')
    print('Processed count:', analysis.get('processed_count'))
    print('Average cost:', stats.get('avg_cost'))
    print('Median cost:', stats.get('median'))
    print('Std dev:', stats.get('std'))
    print('Records with anomalies:', len(anomalies))
    print('Market snapshot:', market)
    print('Saved record ids:', analysis.get('saved_record_ids'))

    # DB info
    db_url = os.environ.get('DATABASE_URL') or f"sqlite:///{ROOT / 'src' / 'data' / 'agents.db'}"
    print('\n--- DB Info ---')
    print('DB URL:', db_url)
    try:
        eng = create_engine(db_url)
        with eng.connect() as conn:
            rows = conn.execute(text('select count(*) from records')).scalar()
            print('Records in DB:', rows)
    except Exception as e:
        print('Failed to query DB:', e)


if __name__ == '__main__':
    main()
