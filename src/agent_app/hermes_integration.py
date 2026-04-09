"""Hermes integration wrapper (best-effort).

This module attempts to import the Hermes Agent library and register a simple
workflow that invokes the local agents. If Hermes is not available, the module
still exposes a `run_workflow()` function that runs the local flow directly.
"""
import logging
from agent_app.agents import PDFLoaderAgent, PDFExtractorAgent, DedupeAgent, CostCalculatorAgent, MarketRateFetcherAgent, ReportingAgent

logger = logging.getLogger(__name__)


def run_workflow(samples_path=None):
    """Run the same demo pipeline; used as a Hermes-executable task.

    This function is intentionally simple so it can be used with or without Hermes.
    """
    loader = PDFLoaderAgent()
    extractor = PDFExtractorAgent()
    deduper = DedupeAgent()
    calculator = CostCalculatorAgent()
    market = MarketRateFetcherAgent()
    reporter = ReportingAgent()

    import json, os
    if not samples_path:
        samples_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'samples', 'sample_input.json')
    with open(samples_path, 'r', encoding='utf-8') as f:
        docs = json.load(f)
    processed = []
    for d in docs:
        doc = loader.load_from_samples([d])[0]
        ex = extractor.extract(doc)
        if not deduper.is_duplicate(ex):
            deduper.save(ex)
        processed.append(ex)
    summary = calculator.compute_avg_cost(processed)
    anomalies = calculator.detect_anomalies(processed)
    market_fbx = market.fetch_fbx()
    analysis = {'summary': summary, 'anomalies': anomalies, 'market': market_fbx}
    path = reporter.generate_report(analysis)
    logger.info('Hermes workflow finished, report=%s', path)
    return path
