Project: CPA Shipping & Logistics Cost Research Agent

Overview
-- Python backend using Hermes Agent framework to provide search/research tools for CPAs to control shipping/logistics costs.

Brief description
- This project is a lightweight agent-based pipeline that ingests shipping documents (PDFs or JSON samples), extracts structured fields (vendor, amount, route, date), deduplicates and stores records in a local SQLite DB, fetches market indices (FBX/Xeneta) via lightweight scrapers, computes simple statistics and anomaly detection, and emits a JSON report suitable for review or automated alerts. It's designed as a demo/prototype to show how LLMs (via OpenRouter), scrapers, and simple agents can be composed for CPA workflows.

Goal
- Build modular agents: PDF ingestion (GDrive/email), OCR & extraction, format classification, dedupe+DB, cost calculator, market-rate fetcher (FBX/Xeneta), reporting, and a Hermes feedback loop.

Quick start
1. Create a virtualenv and install dependencies:

   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt

2. Set environment variables (optional):
- `OPENROUTER_API_KEY` - OpenRouter key (for LLM tasks). If not set, the demo uses heuristics.
- `APIFY_TOKEN` - Apify token (for market-rate scrapers). If not set, market values are mocked.
- `DATABASE_URL` - DB connection string (sqlite/postgres). If not set, a local sqlite at `src/data/agents.db` is used.
- Google Drive / Gmail credentials: if you want GDrive/Gmail ingestion, follow Google API docs to create OAuth credentials and store them locally; the project contains placeholders for GDrive/Gmail clients.

4. Run the starter app (skeleton):

   python -m agent_app.main

4. Run tests (requires `pytest`):

   pip install pytest
   pytest -q

Files
- `src/agent_app/agents.py` - skeleton implementations for agents
- `src/agent_app/main.py` - CLI entrypoint
- `samples/sample_input.json` - sample document JSON
 - `samples/sample_output.json` - example output report (new format: `meta` + `analysis`)

Notes
- This repository provides a full local pipeline with optional integrations.
- OCR: `pytesseract` is supported but requires installing the Tesseract binary for your OS. On Windows, download the installer from: https://github.com/tesseract-ocr/tesseract
- Hermes: a wrapper `src/agent_app/hermes_integration.py` allows running the pipeline as a Hermes task if you add Hermes configuration.
- Hermes hosted: build the provided `Dockerfile` and deploy the image as a Hermes task that runs `python hermes_task.py`.

Quick Hermes deploy (example):

1. Build image locally:

   docker build -t cpa-agent:latest .

2. Push to registry and create a Hermes hosted task pointing to this image.

If you cannot run Docker locally, enable the GitHub Actions workflow which builds and pushes the image for you. Steps:

1. Create a Personal Access Token with `write:packages` permission and add it to your repo secrets as `CR_PAT`.
2. Push your code to `main`. The workflow `.github/workflows/ci.yml` will run tests and build/push the image to `ghcr.io/${{ github.repository_owner }}/${{ github.repository }}`.

CI artifacts: the workflow now runs the demo and uploads a `cpa-artifacts.zip` containing the generated `reports/` folder and the SQLite DB under `src/data/agents.db`. You can download it from the Actions run summary.

3. Configure environment variables (`OPENROUTER_API_KEY`, `APIFY_TOKEN`) in the Hermes task settings.

The task command should be the default container `CMD` which executes `python hermes_task.py`.
- To enable real LLMs or Apify actors, set the corresponding environment variables and consult adapters in `src/agent_app/adapters.py`.
 - To enable real LLMs or Apify actors, set the corresponding environment variables and consult adapters in `src/agent_app/adapters.py`.
    - `APIFY_TOKEN`: when set the code will attempt to run configured Apify actors for FBX/Xeneta. The actors used by default may require renting/paid usage; if you see "must rent a paid Actor" errors, either rent the actor in Apify Console or set `USE_LOCAL_SCRAPER=true` to force local scraping.
    - `APIFY_FBX_ACTOR_ID` and `APIFY_XENETA_ACTOR_ID`: override the default actor IDs used for fetching market data.
   - Default behavior: local scrapers are preferred. By default the code will call local HTTP scrapers (`scrapers.fetch_fbx_via_http` / `scrapers.fetch_xeneta_via_http`).
   - To force Apify (even when local scrapers are present), set `USE_LOCAL_SCRAPER=false` and provide `APIFY_TOKEN` plus `APIFY_*_ACTOR_ID` in your `.env`.

Submission
- Add your GitHub repo link and include API tokens as required by the assignment deliverables.

Run locally (quick)
1. The .env should look something like this:

   - `OPENROUTER_API_KEY` — OpenRouter API key (for LLM tasks)
   - `OPENROUTER_MODEL` — recommended: `meta-llama/llama-3.3-70b-instruct:free`
   - `APIFY_TOKEN` — Apify API token (optional; local scrapers are used by default)

2. Create and activate virtualenv, install deps:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

3. (Optional) fetch provided data sources (clones GitHub repos into `src/data/sources`):

```powershell
python scripts/fetch_sources.py
```

4. Run the demo pipeline locally (loads `samples/sample_input.json` and writes a report into `reports/`):

```powershell
python -u run_demo.py
```

Run the concise summary script (reads the generated report and prints stats):

```powershell
python scripts/run_demo_summary.py
```

5. Run tests:

```powershell
pip install pytest
pytest -q
```

6. Build Docker image locally (optional):

```powershell
docker build -t cpa-agent:latest .
docker run --env-file .env cpa-agent:latest
```

- Notes
- The demo prefers local scrapers (`USE_LOCAL_SCRAPER=true`) to avoid paid Apify actors. Set `USE_LOCAL_SCRAPER=false` to attempt Apify actor calls when `APIFY_TOKEN` is set.

Evaluation & Submission Checklist
- Deliverables included in this repo:
   - **Python code**: full demo pipeline under `src/agent_app/` (loaders, extractor, dedupe, calculator, market fetcher, reporter, Hermes wrapper).
   - **Sample input**: `samples/sample_input.json`.
   - **Sample output**: `samples/sample_output.json` and generated reports under `reports/` after running the demo.
   - **Tests**: `tests/test_flow.py` demonstrates an end-to-end run.

- Evaluation criteria mapping:
   - **Working functionality**: run `python -u run_demo.py` or `python scripts/run_demo_summary.py` to generate reports; CI runs tests automatically.
   - **Code clarity and organization**: the pipeline is modular under `src/agent_app/`; use `agent_app.main` as the main driver.
   - **Agent tooling**: adapters and placeholders exist in `src/agent_app/adapters.py` for external agent-building tools; to integrate 3rd-party agent platforms (cursor.com / Antigravity) add an adapter that implements the same `generate()` or `run_actor()` pattern used by `OpenRouterAdapter`/`ApifyAdapter`.

Extra credit features present:
- **Scale**: containerization via `Dockerfile` and CI workflow make scaling and deployment straightforward.
- **Logging & Error handling**: `src/agent_app/main.py` configures console+file logging; `run_demo.py` has top-level exception logging to aid debugging.

If you want, I can add a short adapter example for one of the listed platforms (cursor.com/Antigravity) — tell me which and I will scaffold the adapter and README integration steps.

Report format

The generated report is a JSON file with the following top-level structure:

```json
{
   "meta": { "generated_at": "...Z", "generator": "agent_app/ReportingAgent", "generator_version": "1.0" },
   "analysis": {
       "stats": { "avg_cost": 11150.0, "count": 2, "median": 11150.0, "std": 1350.0 },
       "anomalies": [ {"doc_id": "doc-123", "amount": 99999.0, "z_score": 4.2} ],
       "market": { "fbx": {...}, "xeneta": {...} },
       "processed_count": 2,
       "processed": [ { ...extracted record... } ],
       "saved_record_ids": [1,2]
   }
}
```

The project writes a local SQLite DB at `src/data/agents.db` by default.
- CI builds and runs the demo and uploads `cpa-artifacts.zip` (reports + DB) as a workflow artifact.


