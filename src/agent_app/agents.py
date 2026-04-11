"""Agents skeleton for CPA Shipping & Logistics Cost Research

Each agent is implemented as a small class with clear responsibilities.
This file contains scaffolding and interfaces to be filled in.
"""
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import logging
import hashlib
import os
import datetime
from sqlalchemy.orm import Session

from agent_app import db
from agent_app.adapters import ApifyAdapter, OpenRouterAdapter
from agent_app import prompts
import os

logger = logging.getLogger(__name__)


@dataclass
class Document:
    id: str
    source: str
    filename: Optional[str]
    raw_text_snippet: Optional[str]
    metadata: Dict[str, Any]


class PDFLoaderAgent:
    """Load PDFs from GDrive or Email.

    For the demo, this loader can accept pre-parsed JSON documents (samples/).
    """
    def __init__(self, gdrive_client=None, email_client=None):
        self.gdrive = gdrive_client
        self.email = email_client

    def load_from_samples(self, docs: List[Dict[str, Any]]) -> List[Document]:
        results = []
        for d in docs:
            md = d.get('metadata', {}) or {}
            # prefer explicit top-level date if present
            if d.get('date') and not md.get('date'):
                md['date'] = d.get('date')
            results.append(Document(
                id=d.get('id'),
                source=d.get('source'),
                filename=d.get('filename'),
                raw_text_snippet=d.get('raw_text_snippet'),
                metadata=md
            ))
        return results


class FileSystemLoaderAgent(PDFLoaderAgent):
    """Load PDF-like JSON or extract text from files in a local folder."""
    def load_from_folder(self, folder: str) -> List[Document]:
        docs = []
        for fname in os.listdir(folder):
            path = os.path.join(folder, fname)
            if os.path.isdir(path):
                continue
            if fname.lower().endswith('.json'):
                try:
                    import json
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            for d in data:
                                docs.append(Document(
                                    id=d.get('id'), source=d.get('source'), filename=d.get('filename'),
                                    raw_text_snippet=d.get('raw_text_snippet'), metadata=d.get('metadata', {})))
                        elif isinstance(data, dict):
                            docs.append(Document(
                                id=data.get('id'), source=data.get('source'), filename=data.get('filename'),
                                raw_text_snippet=data.get('raw_text_snippet'), metadata=data.get('metadata', {})))
                except Exception:
                    logger.exception('Failed to load json %s', path)
            elif fname.lower().endswith('.pdf'):
                # minimal PDF text extraction using pdfplumber
                try:
                    import pdfplumber
                    text_parts = []
                    with pdfplumber.open(path) as pdf:
                        for p in pdf.pages:
                            text_parts.append(p.extract_text() or '')
                    text = '\n'.join(text_parts).strip()
                    docs.append(Document(id=fname, source='filesystem', filename=fname, raw_text_snippet=(text[:200] if text else None), metadata={'path': path}))
                except Exception:
                    logger.exception('Failed to extract pdf %s', path)
        return docs


class PDFExtractorAgent:
    """Extract text and structured fields from PDF-like documents and classify format.

    This demo uses simple heuristics: look for keywords to classify, and use
    metadata if present to extract amounts, vendor, route, date.
    """
    def __init__(self, ocr_tool=None):
        self.ocr = ocr_tool

    def classify_format(self, doc: Document) -> str:
        # If OpenRouter is available, ask it to classify the document format
        try:
            or_adapter = OpenRouterAdapter()
            if or_adapter.available():
                prompt = f"Classify this document format in one word (invoice, bill_of_lading, packing_list, other).\nText:\n{doc.raw_text_snippet or ''}\nFilename:{doc.filename or ''}\nReturn only the label."
                resp = or_adapter.generate(prompt, model=os.environ.get('OPENROUTER_MODEL'))
                lab = (resp or '').strip().lower()
                if lab:
                    # normalize common words
                    if 'invoice' in lab:
                        return 'invoice'
                    if 'bill' in lab or 'bol' in lab:
                        return 'bill_of_lading'
                    return lab.split()[0]
        except Exception:
            logger.debug('OpenRouter classify failed or not available')

        text = (doc.raw_text_snippet or '').lower()
        if 'invoice' in text or 'invoice' in (doc.filename or '').lower():
            return 'invoice'
        if 'bill of lading' in text or 'bol' in (doc.filename or '').lower():
            return 'bill_of_lading'
        return 'unknown'

    def extract(self, doc: Document) -> Dict[str, Any]:
        # Prefer structured metadata if present
        extracted = {
            'doc_id': doc.id,
            'source': doc.source,
            'filename': doc.filename,
            'text': doc.raw_text_snippet,
            'format': self.classify_format(doc),
            'vendor': None,
            'amount': None,
            'currency': None,
            'route': None,
            'date': None,
        }
        md = doc.metadata or {}
        extracted.update({
            'vendor': md.get('vendor') or md.get('shipper'),
            'amount': md.get('amount'),
            'currency': md.get('currency'),
            'route': md.get('route'),
            'date': md.get('date'),
        })
        # Use OpenRouter LLM to extract structured fields if available
        try:
            or_adapter = OpenRouterAdapter()
            if or_adapter.available():
                prompt = (
                    "Extract JSON with keys: vendor, amount, currency, route, date from the following document. "
                    "If a value is missing, set it to null. Return only a JSON object.\n\n"
                    f"Text:\n{doc.raw_text_snippet or ''}\nFilename:{doc.filename or ''}\nMetadata:{md}\n"
                )
                resp = or_adapter.generate(prompt, model=os.environ.get('OPENROUTER_MODEL'))
                # attempt to parse JSON from response
                import json, re
                jtext = resp
                m = re.search(r"\{.*\}", jtext, re.S)
                if m:
                    j = json.loads(m.group(0))
                    for k in ('vendor', 'amount', 'currency', 'route', 'date'):
                        if k in j and j[k] is not None:
                            extracted[k] = j[k]
        except Exception:
            logger.debug('OpenRouter extraction not used or failed')

        # If amount not in metadata or LLM result, try to parse from text heuristically
        if extracted.get('amount') is None and extracted.get('text'):
            import re
            m = re.search(r"\b(?:amount|total)[:\s\$]*([0-9,.]+)", (extracted.get('text') or '').lower())
            if m:
                try:
                    val = float(m.group(1).replace(',', ''))
                    extracted['amount'] = val
                except Exception:
                    pass
        return extracted


class DedupeAgent:
    """Detect duplicates and upsert into DB using a simple hash key."""
    def __init__(self, db_engine=None):
        self.engine = db_engine or db.get_engine()

    def _record_hash(self, extracted: Dict[str, Any]) -> str:
        key = f"{extracted.get('vendor')}|{extracted.get('amount')}|{extracted.get('date')}|{extracted.get('route')}"
        return hashlib.sha256(key.encode('utf-8')).hexdigest()

    def is_duplicate(self, extracted: Dict[str, Any]) -> bool:
        h = self._record_hash(extracted)
        with db.get_session(self.engine) as session:
            exists = session.query(db.Record).filter_by(record_hash=h).first() is not None
        return exists

    def save(self, extracted: Dict[str, Any]) -> int:
        h = self._record_hash(extracted)
        now = datetime.datetime.utcnow()
        with db.get_session(self.engine) as session:
            rec = session.query(db.Record).filter_by(record_hash=h).first()
            if rec:
                return rec.id
            rec = db.Record(
                doc_id=extracted.get('doc_id'),
                source=extracted.get('source'),
                vendor=extracted.get('vendor'),
                amount=extracted.get('amount'),
                currency=extracted.get('currency'),
                route=extracted.get('route'),
                date=extracted.get('date'),
                raw_text=extracted.get('text'),
                record_hash=h,
                created_at=now,
            )
            session.add(rec)
            session.commit()
            session.refresh(rec)
            return rec.id


class CostCalculatorAgent:
    """Compute averages and simple anomaly detection using z-score."""
    def compute_stats(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        import statistics
        vals = [r.get('amount') for r in records if r.get('amount') is not None]
        if not vals:
            return {'avg_cost': None, 'count': 0, 'median': None, 'std': None}
        avg = sum(vals) / len(vals)
        median = statistics.median(vals)
        std = statistics.pstdev(vals) if len(vals) > 1 else 0.0
        return {'avg_cost': avg, 'count': len(vals), 'median': median, 'std': std}

    def detect_anomalies(self, records: List[Dict[str, Any]], threshold: float = 2.0) -> List[Dict[str, Any]]:
        import math
        vals = [r.get('amount') for r in records if r.get('amount') is not None]
        if len(vals) < 2:
            return []
        mean = sum(vals) / len(vals)
        var = sum((v - mean) ** 2 for v in vals) / len(vals)
        std = math.sqrt(var)
        anomalies = []
        for r in records:
            a = r.get('amount')
            if a is None:
                continue
            if std == 0:
                continue
            z = (a - mean) / std
            if abs(z) > threshold:
                anomalies.append({'doc_id': r.get('doc_id'), 'amount': a, 'z_score': z})
        return anomalies


class MarketRateFetcherAgent:
    """Fetch FBX/Xeneta via Apify if available, else return a mocked value."""
    def __init__(self, apify_client=None):
        self.apify = apify_client

    def fetch_fbx(self, date=None) -> Dict[str, Any]:
        # If a local Apify fixture is provided, prefer it for deterministic runs
        fixture_path = os.environ.get('APIFY_FIXTURE_PATH')
        if not fixture_path:
            # look for latest saved apify_dataset file in reports/
            try:
                from glob import glob
                from pathlib import Path
                rpt_dir = str(Path(__file__).resolve().parents[2] / 'reports')
                pattern = os.path.join(rpt_dir, 'apify_dataset_*')
                matches = glob(pattern)
                if matches:
                    # choose newest
                    matches.sort(key=lambda p: os.path.getmtime(p), reverse=True)
                    fixture_path = matches[0]
            except Exception:
                fixture_path = None
        if fixture_path and os.path.exists(fixture_path):
            try:
                import json
                with open(fixture_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                items = None
                if isinstance(data, list):
                    items = data
                elif isinstance(data, dict) and 'output' in data and isinstance(data['output'], list):
                    items = data['output']
                if items:
                    quotes = [it.get('quotesCount') for it in items if isinstance(it, dict) and isinstance(it.get('quotesCount'), (int, float))]
                    mileages = [it.get('mileage') for it in items if isinstance(it, dict) and isinstance(it.get('mileage'), (int, float))]
                    avg_quotes = (sum(quotes) / len(quotes)) if quotes else None
                    avg_mileage = (sum(mileages) / len(mileages)) if mileages else None
                    proxy = avg_quotes if avg_quotes is not None else avg_mileage
                    return {
                        'date': date or str(datetime.date.today()),
                        'fbx_index': float(proxy) if proxy is not None else None,
                        'source': f'fixture:{os.path.basename(fixture_path)}',
                        'apify_items_count': len(items),
                        'apify_avg_quotes': avg_quotes,
                        'apify_avg_mileage': avg_mileage,
                        'apify_sample': items[:5]
                    }
            except Exception:
                logger.exception('Failed to load APIFY fixture %s', fixture_path)
        # Default behavior: auto-detect. If APIFY_TOKEN is present and USE_LOCAL_SCRAPER is not
        # explicitly set, prefer Apify. Set USE_LOCAL_SCRAPER to 'true' to force local scraping.
        env_use = os.environ.get('USE_LOCAL_SCRAPER')
        apify_token = os.environ.get('APIFY_TOKEN')
        if env_use is None:
            use_local = False if apify_token else True
        else:
            use_local = str(env_use).lower() in ('1', 'true', 'yes')

        if use_local:
            try:
                return scrapers.fetch_fbx_via_http(date)
            except Exception:
                logger.exception('Local FBX scrape failed; will attempt Apify if configured')

        if apify_token:
            try:
                ap = ApifyAdapter(apify_token)
                if ap.available():
                    actor_id = os.environ.get('APIFY_FBX_ACTOR_ID', 'parseforge/shiply-com-freight-marketplace-scraper')
                    # provide a richer input matching the parseforge actor's form fields
                    # The parseforge actor does not accept a `date` property in input schema.
                    # Do not pass `date` to avoid validation errors from the actor.
                    input_data = {
                        'country': os.environ.get('APIFY_COUNTRY', 'United Kingdom'),
                        'maxItems': int(os.environ.get('APIFY_MAX_ITEMS', '10')),
                        'maxConcurrency': int(os.environ.get('APIFY_MAX_CONCURRENCY', '5')),
                        'requestDelayMs': int(os.environ.get('APIFY_REQUEST_DELAY_MS', '500')),
                    }
                    run = ap.run_actor(actor_id, input_data)

                    def _search_for_key(obj, keys):
                        if isinstance(obj, dict):
                            for k, v in obj.items():
                                if k in keys:
                                    return v
                                res = _search_for_key(v, keys)
                                if res is not None:
                                    return res
                        elif isinstance(obj, list):
                            for item in obj:
                                res = _search_for_key(item, keys)
                                if res is not None:
                                    return res
                        return None

                    # try common locations for the index
                    val = None
                    if isinstance(run, dict) and 'output' in run:
                        # If actor returned a dataset-style output (list of items)
                        out = run['output']
                        if isinstance(out, list):
                            items = out
                        else:
                            items = None
                        val = _search_for_key(out, ('fbx_index', 'index', 'value')) if out is not None else None
                    else:
                        items = run if isinstance(run, list) else None
                        val = _search_for_key(run, ('fbx_index', 'index', 'value'))

                    # If dataset items exist, compute simple numeric summaries from known fields
                    if items:
                        count = len(items)
                        quotes = [it.get('quotesCount') for it in items if isinstance(it, dict) and isinstance(it.get('quotesCount'), (int, float))]
                        mileages = [it.get('mileage') for it in items if isinstance(it, dict) and isinstance(it.get('mileage'), (int, float))]
                        avg_quotes = (sum(quotes) / len(quotes)) if quotes else None
                        avg_mileage = (sum(mileages) / len(mileages)) if mileages else None
                        # choose a proxy metric for FBX: prefer avg_quotes if available, else avg_mileage
                        proxy = avg_quotes if avg_quotes is not None else avg_mileage
                        return {
                            'date': date or str(datetime.date.today()),
                            'fbx_index': float(proxy) if proxy is not None else None,
                            'source': f'apify:{actor_id}',
                            'apify_items_count': count,
                            'apify_avg_quotes': avg_quotes,
                            'apify_avg_mileage': avg_mileage,
                            'apify_sample': items[:5],
                            'apify_items': items
                        }

                    if val is not None:
                        try:
                            v = float(val)
                            return {'date': date or str(datetime.date.today()), 'fbx_index': v, 'source': f'apify:{actor_id}'}
                        except Exception:
                            pass
            except Exception:
                logger.exception('Apify FBX fetch failed; falling back to mock')

        return {'date': date or str(datetime.date.today()), 'fbx_index': 1234.56, 'source': 'mock'}

    def fetch_xeneta(self, date=None) -> Dict[str, Any]:
        # If a local Apify fixture is provided, prefer it for deterministic runs
        fixture_path = os.environ.get('APIFY_FIXTURE_PATH')
        if not fixture_path:
            try:
                from glob import glob
                from pathlib import Path
                rpt_dir = str(Path(__file__).resolve().parents[2] / 'reports')
                pattern = os.path.join(rpt_dir, 'apify_dataset_*')
                matches = glob(pattern)
                if matches:
                    matches.sort(key=lambda p: os.path.getmtime(p), reverse=True)
                    fixture_path = matches[0]
            except Exception:
                fixture_path = None
        if fixture_path and os.path.exists(fixture_path):
            try:
                import json
                with open(fixture_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                items = None
                if isinstance(data, list):
                    items = data
                elif isinstance(data, dict) and 'output' in data and isinstance(data['output'], list):
                    items = data['output']
                if items:
                    quotes = [it.get('quotesCount') for it in items if isinstance(it, dict) and isinstance(it.get('quotesCount'), (int, float))]
                    mileages = [it.get('mileage') for it in items if isinstance(it, dict) and isinstance(it.get('mileage'), (int, float))]
                    avg_quotes = (sum(quotes) / len(quotes)) if quotes else None
                    avg_mileage = (sum(mileages) / len(mileages)) if mileages else None
                    proxy = avg_quotes if avg_quotes is not None else avg_mileage
                    return {
                        'date': date or str(datetime.date.today()),
                        'xeneta_index': float(proxy) if proxy is not None else None,
                        'source': f'fixture:{os.path.basename(fixture_path)}',
                        'apify_items_count': len(items),
                        'apify_avg_quotes': avg_quotes,
                        'apify_avg_mileage': avg_mileage,
                        'apify_sample': items[:5],
                        'apify_items': items
                    }
            except Exception:
                logger.exception('Failed to load APIFY fixture %s', fixture_path)

        # Default behavior: auto-detect. If APIFY_TOKEN is present and USE_LOCAL_SCRAPER is not
        # explicitly set, prefer Apify. Set USE_LOCAL_SCRAPER to 'true' to force local scraping.
        env_use = os.environ.get('USE_LOCAL_SCRAPER')
        apify_token = os.environ.get('APIFY_TOKEN')
        if env_use is None:
            use_local = False if apify_token else True
        else:
            use_local = str(env_use).lower() in ('1', 'true', 'yes')

        if use_local:
            try:
                return scrapers.fetch_xeneta_via_http(date)
            except Exception:
                logger.exception('Local Xeneta scrape failed; will attempt Apify if configured')

        if apify_token:
            try:
                ap = ApifyAdapter(apify_token)
                if ap.available():
                    # allow using the same actor as FBX if desired
                    actor_id = os.environ.get('APIFY_XENETA_ACTOR_ID') or os.environ.get('APIFY_FBX_ACTOR_ID', 'parseforge/shiply-com-freight-marketplace-scraper')
                    input_data = {
                        # actor input does not support `date`; use other filters if needed
                        'country': os.environ.get('APIFY_COUNTRY', 'United Kingdom'),
                        'maxItems': int(os.environ.get('APIFY_MAX_ITEMS', '10')),
                        'maxConcurrency': int(os.environ.get('APIFY_MAX_CONCURRENCY', '5')),
                        'requestDelayMs': int(os.environ.get('APIFY_REQUEST_DELAY_MS', '500')),
                    }
                    run = ap.run_actor(actor_id, input_data)

                    def _search_for_key(obj, keys):
                        if isinstance(obj, dict):
                            for k, v in obj.items():
                                if k in keys:
                                    return v
                                res = _search_for_key(v, keys)
                                if res is not None:
                                    return res
                        elif isinstance(obj, list):
                            for item in obj:
                                res = _search_for_key(item, keys)
                                if res is not None:
                                    return res
                        return None

                    val = None
                    if isinstance(run, dict) and 'output' in run:
                        out = run['output']
                        items = out if isinstance(out, list) else None
                        val = _search_for_key(out, ('xeneta_index', 'index', 'value')) if out is not None else None
                    else:
                        items = run if isinstance(run, list) else None
                        val = _search_for_key(run, ('xeneta_index', 'index', 'value'))

                    if items:
                        count = len(items)
                        quotes = [it.get('quotesCount') for it in items if isinstance(it, dict) and isinstance(it.get('quotesCount'), (int, float))]
                        mileages = [it.get('mileage') for it in items if isinstance(it, dict) and isinstance(it.get('mileage'), (int, float))]
                        avg_quotes = (sum(quotes) / len(quotes)) if quotes else None
                        avg_mileage = (sum(mileages) / len(mileages)) if mileages else None
                        proxy = avg_quotes if avg_quotes is not None else avg_mileage
                        return {
                            'date': date or str(datetime.date.today()),
                            'xeneta_index': float(proxy) if proxy is not None else None,
                            'source': f'apify:{actor_id}',
                            'apify_items_count': count,
                            'apify_avg_quotes': avg_quotes,
                            'apify_avg_mileage': avg_mileage,
                            'apify_sample': items[:5],
                            'apify_items': items
                        }

                    if val is not None:
                        try:
                            v = float(val)
                            return {'date': date or str(datetime.date.today()), 'xeneta_index': v, 'source': f'apify:{actor_id}'}
                        except Exception:
                            pass
            except Exception:
                logger.exception('Apify Xeneta fetch failed, falling back to mock')

        return {'date': date or str(datetime.date.today()), 'xeneta_index': 987.65, 'source': 'mock'}


class ReportingAgent:
    """Generate JSON report from analysis dictionary and save to disk."""
    def __init__(self, out_dir: str = None):
        self.out_dir = out_dir or 'reports'
        os.makedirs(self.out_dir, exist_ok=True)

    def generate_report(self, analysis: Dict[str, Any]) -> str:
        # If OpenRouter is configured, ask it to analyze the analysis and return anomalies/summaries
        try:
            or_adapter = OpenRouterAdapter()
            if or_adapter.available():
                import json
                prompt = (
                    "Given the following analysis JSON, identify any anomalies, unexpected patterns, "
                    "and concise recommendations. Return only a JSON object with keys: anomalies (list), "
                    "summary (string).\n\nAnalysis:\n" + json.dumps(analysis, default=str)
                )
                resp = or_adapter.generate(prompt, model=os.environ.get('OPENROUTER_MODEL'))
                # try to parse JSON from response
                try:
                    import re, json
                    m = re.search(r"\{.*\}", resp, re.S)
                    if m:
                        j = json.loads(m.group(0))
                        # attach to analysis
                        analysis['llm_anomalies'] = j
                except Exception:
                    logger.debug('Failed to parse OpenRouter response for anomalies')
        except Exception:
            logger.debug('OpenRouter anomaly analysis not available')
        ts = datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
        path = os.path.join(self.out_dir, f'report_{ts}.json')
        # augment analysis with metadata
        meta = {
            'generated_at': datetime.datetime.utcnow().isoformat() + 'Z',
            'generator': 'agent_app/ReportingAgent',
            'generator_version': '1.0'
        }
        payload = {'meta': meta, 'analysis': analysis}
        with open(path, 'w', encoding='utf-8') as f:
            import json
            json.dump(payload, f, indent=2, default=str)
        return path


class FeedbackLoopAgent:
    """Simple feedback sink that stores feedback in DB for later model retraining."""
    def __init__(self, db_engine=None):
        self.engine = db_engine or db.get_engine()

    def feed(self, feedback: Dict[str, Any]):
        with db.get_session(self.engine) as session:
            fb = db.Feedback(payload=feedback, created_at=datetime.datetime.utcnow())
            session.add(fb)
            session.commit()
        logger.info("Stored feedback")

