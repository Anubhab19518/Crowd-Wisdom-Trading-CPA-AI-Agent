import os
import json
from pathlib import Path

from agent_app.hermes_integration import run_workflow


def test_run_workflow_creates_report(tmp_path):
    # copy sample to tmp and run; locate repo root by searching for samples/
    current = Path(__file__).resolve()
    repo_root = None
    for p in current.parents:
        if (p / 'samples' / 'sample_input.json').exists():
            repo_root = p
            break
    if repo_root is None:
        repo_root = Path.cwd()
    sample = repo_root / 'samples' / 'sample_input.json'
    dest = tmp_path / 'sample_input.json'
    dest.write_text(sample.read_text(encoding='utf-8'), encoding='utf-8')
    report = run_workflow(str(dest))
    assert report is not None
    assert os.path.exists(report)
