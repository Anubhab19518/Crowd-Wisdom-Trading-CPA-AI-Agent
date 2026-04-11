# ADR 0001: Architecture Decisions for CPA Shipping & Logistics Agent

Date: 2026-04-10

Status: Accepted

Context
- Project provides an agent-based backend to help CPAs control shipping/logistics costs by ingesting PDFs, extracting structured data, deduping, computing cost statistics, fetching market rates, and reporting.

Decisions
- Framework: use a lightweight Hermes-compatible layout and provide `hermes_task.py` and `Dockerfile` so the project can run on Hermes hosted. This keeps the workflow portable and containerized.
- LLM: Wire OpenRouter for all LLM-required tasks (classification/extraction). Use a free model where available; controlled by `OPENROUTER_MODEL` env var.
- Scrapers: Prefer local HTTP scrapers for market indices (FBX/Xeneta) to avoid reliance on paid Apify actors. Provide an `ApifyAdapter` as an optional fallback when `APIFY_TOKEN` is provided. When an Apify dataset fixture file exists (`reports/apify_dataset_*.json`), prefer using the fixture for reproducible runs.
- Apify integration details: `ApifyAdapter.run_actor()` prefers the HTTP `run-sync-get-dataset-items` endpoint and treats HTTP 200 and 201 as success. If the run response contains `defaultDatasetId`, the adapter fetches the dataset items and returns them. The `MarketRateFetcherAgent` exposes `apify_items` in the snapshot return value.
- Mapping scraped items: map raw Apify scraped listings into the report under `analysis.processed` when samples are skipped, and persist deduplicated records to the local DB.
- OCR: Support `pytesseract` (optional) and `pdfplumber` for text extraction. Tesseract binary is required for `pytesseract` to work.
- Storage: Use SQLite for local persistence (`src/data/agents.db`) with SQLAlchemy ORM for simplicity and portability. The `DedupeAgent` computes a `record_hash` and upserts records to avoid duplicates.
- LLM anomalies: Enrich reporting by asking an LLM for a short JSON anomalies summary when `OPENROUTER_API_KEY` is set; save the parsed JSON under `analysis.llm_anomalies` when parseable.
- Demo runner defaults: `run_demo.py` forces `SKIP_SAMPLE_INPUT=1` so the demo prefers Apify/scraped data or fixtures over `samples/sample_input.json`. To run with samples, set `SKIP_SAMPLE_INPUT=0`.
- CI/CD: Provide GitHub Actions to run tests, build Docker image, run the demo, and upload artifacts so users without Docker can still produce outputs.

Consequences
- Users can run the full pipeline locally with minimal setup or deploy to Hermes hosted using the Docker image.
- Runs are reproducible when `reports/apify_dataset_*.json` fixtures are present; otherwise, live Apify calls will be attempted when `APIFY_TOKEN` is set.
- The demo defaults to skipping the sample input to prioritize live/fixture-driven runs. This can be overridden by setting `SKIP_SAMPLE_INPUT=0`.
- Relying on Apify actors may incur costs or require renting specific actors on Apify; fallback to fixtures/local scrapers is retained for local development and CI.
- Sensitive credentials must be kept out of source control (`.env` ignored). The repo includes `.env.example` as template.
