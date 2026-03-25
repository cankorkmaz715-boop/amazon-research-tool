# VPS Readiness Checklist – Amazon Research Tool

Environment and integration checklist for a Linux (Ubuntu/Debian) VPS. Complete this **before** the proxy manager + Playwright base layer step. No scraping or Playwright logic in this step—only installation and readiness.

---

## 1. Goal

Ensure the VPS has everything installed and configured so that:
- The current Python project foundation runs correctly
- The next step (proxy + Playwright base) can be done without missing system dependencies
- Environment variables, logging, and PostgreSQL connectivity are ready
- Setup is conservative, minimal, and copy-paste friendly

---

## 2. Required now

| Item | Why it is needed |
|------|-------------------|
| **Python 3.10+** | Project is Python-based; config, logging, and all modules require it. |
| **python3-venv** | Isolated virtual environment for dependencies; avoids system Python conflicts. |
| **pip** | Install `requirements.txt` (python-dotenv, psycopg2-binary, playwright). |
| **Playwright system dependencies** | Chromium and other browsers need system libs (e.g. libnss3, libgbm). Installing them now avoids failures when you run `playwright install chromium` in the next step. |
| **PostgreSQL server running** | App expects `DATABASE_URL`; DB is used for storage layer. (Already set up on this VPS.) |
| **.env with DATABASE_URL** | Central config reads from env; missing URL causes startup to fail. |

---

## 3. Optional but recommended

| Item | Why recommended |
|------|------------------|
| **build-essential** | Some Python packages may need to compile C extensions; avoids build failures. |
| **git** | Clone/update code, track changes; useful for deployment and updates. |
| **postgresql-client** | Use `psql` to test DB connection and debug; server is already installed. |
| **curl** | Quick health checks and API tests from the server. |

---

## 4. Not needed yet

| Item | When / why later |
|------|-------------------|
| Node.js / npm | Python is the main app; existing Node server.js is separate. |
| Docker | Not required for current run; add when containerizing. |
| Redis / Celery | Queue/worker layer; add when implementing scheduler/queue. |
| Grafana / Sentry / Uptime Kuma | Monitoring stack; add when adding observability. |
| DataImpulse proxy software on server | Proxy is used via config (URL/auth); no extra install. |
| PM2 / systemd for Python | Add when you need a long-running Python process; current step is “run by hand”. |

---

## 5. Exact install commands (Ubuntu/Debian)

Run as root or with `sudo`. Copy and paste in order.

```bash
# Update package list
sudo apt-get update

# Required: Python, venv, pip
sudo apt-get install -y python3 python3-venv python3-pip

# Required: Playwright system dependencies (for Chromium)
sudo apt-get install -y \
  libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
  libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 \
  libasound2 libpango-1.0-0 libcairo2 libatspi2.0-0

# Optional but recommended
sudo apt-get install -y build-essential git postgresql-client curl
```

**Note:** If you prefer to install Playwright deps via Playwright’s own script (after installing Python and pip), you can skip the manual lib list and run later, from project dir with venv active:

```bash
pip install playwright
playwright install-deps
```

The commands above install the same kind of dependencies so that `playwright install chromium` works without extra steps.

---

## 6. Exact verification commands

Run these after the install step. All should succeed (exit 0 or print a version).

```bash
# Python 3.10+
python3 --version

# venv available
python3 -m venv --help | head -1

# pip available
python3 -m pip --version

# Optional: PostgreSQL client
psql --version

# Optional: curl
curl --version | head -1
```

**Verify PostgreSQL server (if using local DB):**

```bash
# Check PostgreSQL is running (Ubuntu/Debian)
sudo systemctl status postgresql
# or for a specific version:
sudo systemctl status postgresql@16-main
```

**Verify project runs (from project root, after venv and .env):**

```bash
cd /root/amazon-tool
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# Ensure .env exists with DATABASE_URL
export PYTHONPATH="/root/amazon-tool/src:$PYTHONPATH"
python -m amazon_research.main
```

Expected: log lines and “skeleton run complete” without crash.

---

## 7. Minimal server readiness test

Single script you can run to confirm the server is ready for this project. Save as `scripts/check_vps_readiness.sh` and run from project root.

```bash
#!/bin/bash
# Minimal server readiness test – Amazon Research Tool
# Run from project root: bash scripts/check_vps_readiness.sh

set -e
echo "=== VPS Readiness Check ==="

echo -n "Python 3.10+ ... "
python3 --version
python3 -c "import sys; assert sys.version_info >= (3, 10), 'Need Python 3.10+'"
echo "OK"

echo -n "venv ... "
python3 -m venv --help > /dev/null 2>&1 && echo "OK" || { echo "MISSING"; exit 1; }

echo -n "pip ... "
python3 -m pip --version && echo "OK" || { echo "MISSING"; exit 1; }

echo -n ".env exists ... "
[ -f .env ] && echo "OK" || { echo "MISSING (copy .env.example to .env, set DATABASE_URL)"; exit 1; }

echo -n "DATABASE_URL set ... "
grep -q 'DATABASE_URL=' .env && [ -n "$(grep DATABASE_URL .env | cut -d= -f2)" ] && echo "OK" || { echo "MISSING or empty"; exit 1; }

echo -n "Project run (skeleton) ... "
export PYTHONPATH="${PYTHONPATH:-$(pwd)/src}"
python3 -m amazon_research.main > /tmp/amazon_readiness.log 2>&1
grep -q "skeleton run complete" /tmp/amazon_readiness.log && echo "OK" || { echo "FAIL"; cat /tmp/amazon_readiness.log; exit 1; }

echo "=== All checks passed. Server is ready for next step (proxy + Playwright base). ==="
```

**Prerequisites for this script:** Venv created, dependencies installed, and `.env` with valid `DATABASE_URL`. Typical order:

1. Run install commands (§5).
2. Create venv and install Python deps: `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and set `DATABASE_URL`.
4. From project root, with venv activated, run: `export PYTHONPATH="$(pwd)/src" && bash scripts/check_vps_readiness.sh`

---

## 8. Risks / notes

- **Python version:** On older Ubuntu, `python3` might be 3.8/3.9. Use `python3.10` or `python3.11` if available (`apt install python3.10 python3.10-venv python3.10-dev`) and use that interpreter for venv and run.
- **Playwright:** `playwright install chromium` (and optionally `playwright install-deps`) is done in the **next** step when you add the browser layer. This checklist only prepares system deps so that step works.
- **PostgreSQL port:** This VPS uses port **5433** for PostgreSQL (5432 is used by Docker). Ensure `DATABASE_URL` in `.env` uses port 5433; see `POSTGRES-CONNECTION.md`.
- **DataImpulse:** No server-side install. You will only add proxy URL and credentials to `.env` when implementing the proxy manager.
- **Firewall:** Not modified by this checklist. Ensure any app port (e.g. 3000) is allowed if you expose the app later; see previous UFW setup.
