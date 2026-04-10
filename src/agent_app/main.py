"""Starter CLI to run agents (skeleton)

Usage:
    python -m agent_app.main
"""
import os
import logging
import json
from pathlib import Path
from dotenv import load_dotenv
from agent_app.agents import (
    PDFLoaderAgent, PDFExtractorAgent, DedupeAgent,
    CostCalculatorAgent, MarketRateFetcherAgent, ReportingAgent,
)

load_dotenv()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# console handler
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
fmt = logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s')
ch.setFormatter(fmt)
logger.addHandler(ch)
# file handler
try:
    os.makedirs('logs', exist_ok=True)
    fh = logging.FileHandler(os.path.join('logs', 'demo.log'))
    fh.setLevel(logging.INFO)
    fh.setFormatter(fmt)
    logger.addHandler(fh)
except Exception:
    logger.debug('Unable to create log file handler')

SAMPLES_DIR = Path(__file__).resolve().parents[2] / 'samples'

def run_demo():
    logger.info("Starting demo run (skeleton)")
    # instantiate agents
    loader = PDFLoaderAgent()
    extractor = PDFExtractorAgent()
    deduper = DedupeAgent()
    calculator = CostCalculatorAgent()
    market = MarketRateFetcherAgent()
    reporter = ReportingAgent()

    # load sample input (JSON) and run the processing flow
    sample_file = SAMPLES_DIR / 'sample_input.json'
    if not sample_file.exists():
        logger.warning("No sample_input.json found in samples/")
        return

    with open(sample_file, 'r', encoding='utf-8') as f:
        docs = json.load(f)

    logger.info("Loaded %d sample documents", len(docs))

    processed = []
    saved_ids = []
    for d in docs:
        logger.info("Processing sample doc id=%s", d.get('id'))
        docs_loaded = loader.load_from_samples([d])
        if not docs_loaded:
            continue
        doc = docs_loaded[0]
        extracted = extractor.extract(doc)
        is_dup = deduper.is_duplicate(extracted)
        if is_dup:
            logger.info("Duplicate detected for doc %s - skipping save", extracted.get('doc_id'))
        else:
            rec_id = deduper.save(extracted)
            saved_ids.append(rec_id)
            logger.info("Saved record id=%s", rec_id)
        processed.append(extracted)

    # Analysis
        stats = calculator.compute_stats(processed)
    anomalies = calculator.detect_anomalies(processed)
    market_fbx = market.fetch_fbx()
    market_xeneta = market.fetch_xeneta()

        analysis = {
            'stats': stats,
            'anomalies': anomalies,
            'market': {'fbx': market_fbx, 'xeneta': market_xeneta},
            'processed_count': len(processed),
            'processed': processed,
            'saved_record_ids': saved_ids,
        }

    report_path = reporter.generate_report(analysis)
    logger.info("Generated report: %s", report_path)

if __name__ == '__main__':
    run_demo()
