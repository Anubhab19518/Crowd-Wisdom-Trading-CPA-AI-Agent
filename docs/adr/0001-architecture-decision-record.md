# ADR 0001: Architecture Decisions for CPA Shipping & Logistics Agent

Date: 2026-04-10

Status: Accepted

Context
- Project provides an agent-based backend to help CPAs control shipping/logistics costs by ingesting PDFs, extracting structured data, deduping, computing cost statistics, fetching market rates, and reporting.

Decisions
- Framework: use a lightweight Hermes-compatible layout and provide `hermes_task.py` and `Dockerfile` so the project can run on Hermes hosted. This keeps the workflow portable and containerized.
- LLM: Wire OpenRouter for all LLM-required tasks (classification/extraction). Use a free model where available; controlled by `OPENROUTER_MODEL` env var.
- Scrapers: Prefer local HTTP scrapers for market indices (FBX/Xeneta) to avoid reliance on paid Apify actors. Provide an `ApifyAdapter` as optional fallback when `APIFY_TOKEN` is provided.
- OCR: Support `pytesseract` (optional) and `pdfplumber` for text extraction. Tesseract binary is required for `pytesseract` to work.
- Storage: Use SQLite for local persistence (`src/data/agents.db`) with SQLAlchemy ORM for simplicity and portability.
- CI/CD: Provide GitHub Actions to run tests, build Docker image, run the demo, and upload artifacts so users without Docker can still produce outputs.

Consequences
- Users can run the full pipeline locally with minimal setup or deploy to Hermes hosted using the Docker image.
- Sensitive credentials must be kept out of source control (`.env` ignored). The repo includes `.env.example` as template.
