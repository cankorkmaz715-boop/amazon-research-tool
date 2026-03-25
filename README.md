# Amazon Research Tool

Internal Amazon product research and opportunity discovery. Step-by-step build: this repo is **foundation only** (skeleton, config, logging, placeholders). No bot or scraping logic yet.

## Foundation scope

- Clean folder structure
- Central config (environment variables)
- Central logging
- Placeholder modules: proxy, browser, db, bots (discovery / refresh / scoring), scheduler, monitoring
- Ready for next step: proxy layer + Playwright base

## Requirements

- Python 3.10+
- PostgreSQL (for later; URL in `.env` for config validation)
- No Playwright required for this step (placeholder only)

## Setup

### 1. Virtual environment

```bash
cd /root/amazon-tool
python3 -m venv .venv
source .venv/bin/activate   # Linux/macOS
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

(Playwright and `playwright install` come in the next step.)

### 3. Environment

```bash
cp .env.example .env
# Set at least:
#   DATABASE_URL=postgresql://user:password@host:port/dbname
```

Use the value from `POSTGRES-CONNECTION.md` if you use the existing VPS PostgreSQL.

## Run

From repo root with venv active:

```bash
export PYTHONPATH="/root/amazon-tool/src:$PYTHONPATH"
python -m amazon_research.main
```

Expected: log lines for config loaded, db init, health_check, then "skeleton run complete". No crash.

## Test the foundation

1. **Env and config**  
   - Ensure `.env` has `DATABASE_URL` (and optionally `LOG_LEVEL=DEBUG`, `LOG_FORMAT=console`).  
   - Run `python -m amazon_research.main`.  
   - Expect: "config loaded", "db init done", "health_check", "skeleton run complete".

2. **Logging**  
   - Set `LOG_LEVEL=DEBUG`, run again.  
   - Expect: more verbose logs. Set `LOG_FORMAT=console` for readable output.

3. **Imports**  
   From repo root (so `.env` is loaded by load_dotenv):
   ```bash
   PYTHONPATH=src python -c "
   from dotenv import load_dotenv; load_dotenv()
   from amazon_research.config import get_config
   from amazon_research.logging_config import setup_logging, get_logger
   from amazon_research.proxy import ProxyManager
   from amazon_research.browser import BrowserSession
   from amazon_research.db import init_db
   from amazon_research.bots import AsinDiscoveryBot, DataRefreshBot, ScoringEngine
   from amazon_research.scheduler import SchedulerRunner
   from amazon_research.monitoring import health_check
   setup_logging()
   get_config()
   init_db()
   print('Imports OK')
   print(health_check())
   "
   ```  
   Expect: `Imports OK` and `{'status': 'ok', 'service': 'amazon_research'}`.

4. **Health check**  
   - In code: `from amazon_research.monitoring import health_check; print(health_check())`  
   - Expect: `{'status': 'ok', 'service': 'amazon_research'}`.

## Project layout (foundation)

```
amazon-tool/
├── README.md
├── requirements.txt
├── .env.example
├── .env
├── src/
│   └── amazon_research/
│       ├── __init__.py
│       ├── config.py
│       ├── logging_config.py
│       ├── main.py
│       ├── proxy/
│       │   ├── __init__.py
│       │   └── manager.py
│       ├── browser/
│       │   ├── __init__.py
│       │   └── automation.py
│       ├── db/
│       │   ├── __init__.py
│       │   └── connection.py
│       ├── bots/
│       │   ├── __init__.py
│       │   ├── asin_discovery.py
│       │   ├── data_refresh.py
│       │   └── scoring_engine.py
│       ├── scheduler/
│       │   ├── __init__.py
│       │   └── runner.py
│       └── monitoring/
│           ├── __init__.py
│           └── hooks.py
```

## Next step

Implement proxy layer + Playwright base (real browser session, proxy injection, timeouts). No scraping logic yet.
