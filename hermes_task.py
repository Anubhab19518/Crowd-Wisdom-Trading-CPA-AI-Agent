"""Entrypoint intended for Hermes-hosted tasks.

Usage: the Hermes hosted task should run `python hermes_task.py` inside the container.
This script loads environment variables and runs the pipeline.
"""
import os
from dotenv import load_dotenv

# load .env if present
load_dotenv()

from agent_app.hermes_integration import run_workflow

if __name__ == '__main__':
    samples = os.environ.get('SAMPLES_PATH')
    run_workflow(samples)
