# Production Deployment Hardening (Step 229)

Minimal operational notes for running the Amazon research app on a VPS or production-like environment.

## Required environment

- **DATABASE_URL** (required) – PostgreSQL connection URL, e.g. `postgresql://user:password@host:5432/dbname`
- Copy `.env.example` to `.env` and set at least `DATABASE_URL`.

## Optional environment

- **INTERNAL_API_PORT** – Port for the internal API (default: `8766`)
- **INTERNAL_API_HOST** – Bind address (default: `0.0.0.0` for reverse proxy)

## Build

No separate build step. Ensure dependencies are installed:

```bash
pip install -r requirements.txt
```

## Start commands

**API + UI only (single process):**

```bash
PYTHONPATH=src python scripts/serve_internal_api.py
```

**Full platform (scheduler + workers + API; e.g. systemd):**

```bash
PYTHONPATH=src python -m amazon_research.runtime_service
```

Or use the systemd unit: `deploy/amazon-research.service` (adjust paths and ExecStart as needed).

## Ports and proxy target

- **Backend + UI:** single process binds to `0.0.0.0:8766` (or `INTERNAL_API_PORT`).
- **Reverse proxy (e.g. Nginx):** proxy to `http://127.0.0.1:8766` (or the port you set). No separate frontend port; the same server serves API and static UI.

## Sanity check

Run before or after deploy to confirm env and optional DB connectivity:

```bash
PYTHONPATH=src python scripts/startup_sanity_check.py
```

With DB connection check:

```bash
PYTHONPATH=src python scripts/startup_sanity_check.py --db
```

Exit 0 = OK; exit 1 = configuration or DB error (messages on stderr).

## Failure behavior

- Missing **DATABASE_URL**: server and sanity check fail fast with a clear message.
- Invalid **INTERNAL_API_PORT**: validation reports the error; server uses default if validation is skipped.
- DB unreachable: first request or `--db` sanity check will fail; no silent ignore.
