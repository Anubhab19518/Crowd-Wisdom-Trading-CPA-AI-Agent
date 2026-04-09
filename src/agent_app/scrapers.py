"""Lightweight scrapers for market indices (FBX, Xeneta) without Apify.

These scrapers attempt simple HTTP fetch + regex/HTML parsing. They are
best-effort; if they fail they return a mocked value.
"""
import logging
import requests
import re
from bs4 import BeautifulSoup
import datetime

logger = logging.getLogger(__name__)


def _find_first_number(text: str):
    m = re.search(r"\b([0-9]{1,4}(?:\.[0-9]{1,2})?)\b", text)
    if m:
        try:
            return float(m.group(1))
        except Exception:
            return None
    return None


def fetch_fbx_via_http(date=None):
    urls = [
        'https://fbx.freightos.com/',
        'https://www.freightos.com/freight-resources/freightos-baltic-index/',
    ]
    headers = {'User-Agent': 'Mozilla/5.0 (compatible; CPA-Agent/1.0)'}
    for url in urls:
        try:
            r = requests.get(url, headers=headers, timeout=10)
            r.raise_for_status()
            text = r.text
            # try extracting number near FBX keywords
            if 'FBX' in text or 'Freightos Baltic' in text or 'Baltic' in text:
                # parse HTML and search for numbers
                soup = BeautifulSoup(text, 'html.parser')
                # look for numeric tokens in visible text
                body = soup.get_text(separator=' ', strip=True)
                val = _find_first_number(body)
                if val:
                    return {'date': date or str(datetime.date.today()), 'fbx_index': val, 'source': url}
            # fallback: pick first number in page
            val = _find_first_number(text)
            if val:
                return {'date': date or str(datetime.date.today()), 'fbx_index': val, 'source': url}
        except Exception:
            logger.debug('FBX scrape failed for %s', url, exc_info=True)
    # fallback mocked
    return {'date': date or str(datetime.date.today()), 'fbx_index': 1234.56, 'source': 'mock'}


def fetch_xeneta_via_http(date=None):
    urls = [
        'https://www.xeneta.com/insights',
        'https://www.xeneta.com/',
    ]
    headers = {'User-Agent': 'Mozilla/5.0 (compatible; CPA-Agent/1.0)'}
    for url in urls:
        try:
            r = requests.get(url, headers=headers, timeout=10)
            r.raise_for_status()
            text = r.text
            soup = BeautifulSoup(text, 'html.parser')
            body = soup.get_text(separator=' ', strip=True)
            val = _find_first_number(body)
            if val:
                return {'date': date or str(datetime.date.today()), 'xeneta_index': val, 'source': url}
        except Exception:
            logger.debug('Xeneta scrape failed for %s', url, exc_info=True)
    return {'date': date or str(datetime.date.today()), 'xeneta_index': 987.65, 'source': 'mock'}
