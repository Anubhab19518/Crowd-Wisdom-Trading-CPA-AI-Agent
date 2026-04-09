"""Fetch target data sources for the assignment.

Clones GitHub repos and (optionally) downloads Kaggle datasets if Kaggle API
credentials are available via `KAGGLE_USERNAME` and `KAGGLE_KEY` env vars.

Usage: python scripts/fetch_sources.py
"""
import os
import subprocess
import sys
import logging
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'src' / 'data' / 'sources'
OUT.mkdir(parents=True, exist_ok=True)

REPOS = [
    'https://github.com/aaronjmars/MiroShark.git',
    'https://github.com/opendatalab/mineru.git',
    'https://github.com/docling-project/docling.git',
]

KAGGLE_DATASETS = [
    # slug form: owner/dataset-name
    'sanelehlabisa/acclr-dataset',
    'ayoubcherguelaine/company-documents-dataset',
]

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def _git_clone(url, dest):
    if dest.exists():
        logger.info('Destination %s exists, skipping clone', dest)
        return
    try:
        subprocess.check_call(['git', 'clone', url, str(dest)])
        logger.info('Cloned %s', url)
    except Exception:
        logger.exception('Git clone failed for %s, attempting to download zip', url)
        # fallback to download zip
        try:
            import requests
            api_zip = url.rstrip('.git') + '/archive/refs/heads/main.zip'
            r = requests.get(api_zip, timeout=30)
            r.raise_for_status()
            fname = dest.with_suffix('.zip')
            with open(fname, 'wb') as f:
                f.write(r.content)
            logger.info('Downloaded zip for %s to %s', url, fname)
        except Exception:
            logger.exception('Failed to download repo %s', url)


def fetch_repos():
    for repo in REPOS:
        name = repo.split('/')[-1].replace('.git', '')
        dest = OUT / name
        _git_clone(repo, dest)


def fetch_kaggle():
    # requires KAGGLE_USERNAME and KAGGLE_KEY in env
    if not os.environ.get('KAGGLE_USERNAME') or not os.environ.get('KAGGLE_KEY'):
        logger.info('Kaggle credentials not found in env; skipping Kaggle downloads')
        return
    try:
        from kaggle.api.kaggle_api_extended import KaggleApi
        api = KaggleApi()
        api.authenticate()
        for ds in KAGGLE_DATASETS:
            outdir = OUT / 'kaggle' / ds.replace('/', '_')
            outdir.mkdir(parents=True, exist_ok=True)
            logger.info('Downloading kaggle dataset %s to %s', ds, outdir)
            api.dataset_download_files(ds, path=str(outdir), unzip=True, quiet=False)
    except Exception:
        logger.exception('Kaggle download failed; ensure kaggle package installed and credentials set')


def main():
    logger.info('Fetching GitHub repos...')
    fetch_repos()
    logger.info('Attempting Kaggle dataset downloads...')
    fetch_kaggle()
    logger.info('Done. Sources stored under %s', OUT)


if __name__ == '__main__':
    main()
