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
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
            logger.info("Saved record id=%s", rec_id)
        processed.append(extracted)

    # Analysis
    summary = calculator.compute_avg_cost(processed)
    anomalies = calculator.detect_anomalies(processed)
    market_fbx = market.fetch_fbx()
    market_xeneta = market.fetch_xeneta()

    analysis = {
        'summary': summary,
        'anomalies': anomalies,
        'market': {'fbx': market_fbx, 'xeneta': market_xeneta},
        'processed_count': len(processed),
    }

    report_path = reporter.generate_report(analysis)
    logger.info("Generated report: %s", report_path)

if __name__ == '__main__':
    run_demo()
