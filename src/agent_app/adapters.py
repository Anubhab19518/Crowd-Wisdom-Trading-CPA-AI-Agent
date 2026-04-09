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
        # Try to use apify-client if installed
        try:
            from apify_client import ApifyClient
            client = ApifyClient(self.token)
            # This is a best-effort call; actual API may require different usage
            actor = client.actor(actor_id)
            # apify-client ActorClient.call may expect keyword args; try common variants
            try:
                run = actor.call(run_input=input_data)
            except TypeError:
                try:
                    run = actor.call(input=input_data)
                except TypeError:
                    # final fallback: call with positional (older clients)
                    run = actor.call(input_data)
            return run
        except Exception:
            logger.exception('Apify client call failed')
            raise
