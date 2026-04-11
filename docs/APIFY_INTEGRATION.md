Apify Integration

This project can use Apify actors to fetch market indices (FBX/Xeneta) instead of local HTTP scraping.

How it works

- The `MarketRateFetcherAgent` in `src/agent_app/agents.py` will prefer Apify when `APIFY_TOKEN` is present and `USE_LOCAL_SCRAPER` is not explicitly set.
- The Apify adapter is implemented in `src/agent_app/adapters.py` and uses the `apify-client` Python package.
- The default actor for FBX scraping is configured via `APIFY_FBX_ACTOR_ID` (defaults to `parseforge/shiply-com-freight-marketplace-scraper`).
- If you want Xeneta rates fetched by the same actor, set `APIFY_XENETA_ACTOR_ID` to the same actor ID or leave it unset — code will fallback to `APIFY_FBX_ACTOR_ID`.

Usage

1. Add your Apify token to `.env` (do NOT share this token by email). Example:

   APIFY_TOKEN=apify_api_...YOUR_TOKEN...

2. Optionally set actor IDs in `.env`:

   APIFY_FBX_ACTOR_ID=parseforge/shiply-com-freight-marketplace-scraper
   APIFY_XENETA_ACTOR_ID=parseforge/xeneta-scraper

3. Run the demo (PowerShell):

   .\scripts\run_with_apify.ps1

Notes & Security

- Do not commit `.env` to source control. Use a secrets manager for sharing tokens.
- To force local scraping, set `USE_LOCAL_SCRAPER=true` in the environment or `.env`.
- The system will fall back to local scraping or mocked values if Apify calls fail.
