"""Adapters for external services: OpenRouter LLM and Apify.

These adapters are optional and use environment variables when available.
"""
import os
import logging
import requests

logger = logging.getLogger(__name__)


class OpenRouterAdapter:
    """Simple OpenRouter HTTP adapter. Requires OPENROUTER_API_KEY env var."""
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get('OPENROUTER_API_KEY')
        self.base = os.environ.get('OPENROUTER_API_URL', 'https://api.openrouter.ai')

    def available(self) -> bool:
        return bool(self.api_key)

    def generate(self, prompt: str, model: str = 'gpt-neo-2.7b') -> str:
        if not self.available():
            raise RuntimeError('OpenRouter API key not set')
        url = f"{self.base}/v1/chat/completions"
        headers = {'Authorization': f'Bearer {self.api_key}', 'Content-Type': 'application/json'}
        payload = {
            'model': model,
            'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': 512,
        }
        r = requests.post(url, headers=headers, json=payload, timeout=30)
        r.raise_for_status()
        data = r.json()
        # response shape may vary; try common fields
        try:
            return data['choices'][0]['message']['content']
        except Exception:
            return str(data)


class ApifyAdapter:
    """Simple Apify adapter using `apify-client` if token provided, else no-op."""
    def __init__(self, token: str = None):
        self.token = token or os.environ.get('APIFY_TOKEN')

    def available(self) -> bool:
        return bool(self.token)

    def run_actor(self, actor_id: str, input_data: dict) -> dict:
        if not self.available():
            raise RuntimeError('APIFY_TOKEN not set')
        # Prefer the HTTP run-sync-get-dataset-items endpoint to obtain dataset items directly.
        try:
            import requests
            actor_id_for_url = actor_id.replace('/', '~')
            base = os.environ.get('APIFY_API_BASE', 'https://api.apify.com')
            token = self.token
            url = f"{base}/v2/acts/{actor_id_for_url}/run-sync-get-dataset-items?token={token}"
            r = requests.post(url, json=input_data or {}, timeout=120)
            if r.status_code in (200, 201):
                try:
                    return r.json()
                except Exception:
                    return {'output': r.text}
        except Exception:
            logger.debug('HTTP run-sync-get-dataset-items failed, will try apify-client', exc_info=True)

        # Try to use apify-client if installed as a fallback
        try:
            from apify_client import ApifyClient
            client = ApifyClient(self.token)
            actor = client.actor(actor_id)
            try:
                run = actor.call(run_input=input_data)
            except TypeError:
                try:
                    run = actor.call(input=input_data)
                except TypeError:
                    run = actor.call(input_data)
            # If apify-client returned a run metadata dict, try to fetch dataset items via HTTP
            if isinstance(run, dict):
                # If defaultDatasetId present, fetch dataset items via HTTP
                dataset_id = run.get('defaultDatasetId') or run.get('defaultDatasetId')
                if dataset_id:
                    try:
                        import requests
                        base = os.environ.get('APIFY_API_BASE', 'https://api.apify.com')
                        token = self.token
                        url = f"{base}/v2/datasets/{dataset_id}/items?token={token}"
                        r = requests.get(url, timeout=60)
                        if r.status_code in (200, 201):
                            try:
                                return r.json()
                            except Exception:
                                return {'output': r.text}
                    except Exception:
                        logger.debug('Failed to fetch dataset items via HTTP after apify-client run', exc_info=True)
            return run
        except Exception:
            logger.debug('Apify client call failed; attempting HTTP run-sync fallbacks', exc_info=True)
            # As a fallback, try HTTP endpoints to get dataset items or run-sync output
            try:
                actor_id_for_url = actor_id.replace('/', '~')
                base = os.environ.get('APIFY_API_BASE', 'https://api.apify.com')
                token = self.token
                # Try run-sync-get-dataset-items
                url = f"{base}/v2/acts/{actor_id_for_url}/run-sync-get-dataset-items?token={token}"
                r = requests.post(url, json=input_data or {}, timeout=120)
                if r.status_code in (200, 201):
                    try:
                        return r.json()
                    except Exception:
                        return {'output': r.text}
                # Try run-sync
                url2 = f"{base}/v2/acts/{actor_id_for_url}/run-sync?token={token}"
                r2 = requests.post(url2, json=input_data or {}, timeout=120)
                if r2.status_code in (200, 201):
                    try:
                        return r2.json()
                    except Exception:
                        return {'output': r2.text}
                # Last: start run and return run metadata
                url3 = f"{base}/v2/acts/{actor_id_for_url}/runs?token={token}"
                r3 = requests.post(url3, json=input_data or {}, timeout=30)
                try:
                    return r3.json()
                except Exception:
                    return {'output': r3.text}
            except Exception:
                logger.exception('HTTP fallback to Apify endpoints also failed')
                raise
