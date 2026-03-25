# VPS Readiness Audit – Amazon Scraping / Research Bot

**Server:** vmi3152200 | **Date:** 2026-03-14

---

## 1. System information

| Item   | Status | Details |
|--------|--------|---------|
| **CPU** | OK | 6 cores |
| **RAM** | OK | 11 Gi total, ~10 Gi available |
| **Disk** | OK | 96 G total, 90 G free on `/` (7% used) |
| **OS**   | OK | Linux 6.8.0-100-generic (Ubuntu, x86_64) |

---

## 2. Node.js

| Status | Version |
|--------|---------|
| Installed | **v18.19.1** |

No action needed.

---

## 3. npm

| Status | Version |
|--------|---------|
| Installed | **9.2.0** |

No action needed.

---

## 4. Python

| Status | Version |
|--------|---------|
| Installed | **Python 3.12.3** (`python3`) |

No action needed.

---

## 5. Git

| Status | Version |
|--------|---------|
| Installed | **2.43.0** |

No action needed.

---

## 6. Docker

| Status | Version |
|--------|---------|
| Installed | **29.3.0** (build 5927d80) |

No action needed.

---

## 7. PostgreSQL

| Status | Version |
|--------|---------|
| Not installed | — |

**Install (server + client):**
```bash
sudo apt-get update
sudo apt-get install -y postgresql postgresql-client
```

**Install client only** (if DB is on another host):
```bash
sudo apt-get update
sudo apt-get install -y postgresql-client
```

---

## 8. PM2

| Status | Version |
|--------|---------|
| Installed | **6.0.14** |

No action needed.

---

## 9. Playwright / Puppeteer

| Component | Status | Notes |
|-----------|--------|--------|
| **Playwright** | Available via npx | `npx playwright --version` → **1.58.2**. Not a global/project dependency yet. |
| **Puppeteer** | Not installed | Not in global npm or in `/root/amazon-tool`. |
| **Chromium (system)** | Not in PATH | Playwright/Puppeteer typically ship or install their own browser. |

**Add Playwright to your project:**
```bash
cd /root/amazon-tool
npm install playwright
npx playwright install          # install browser binaries
npx playwright install-deps    # install system deps (e.g. libs for Chromium) – may need sudo
```

**Add Puppeteer to your project:**
```bash
cd /root/amazon-tool
npm install puppeteer
```

**System dependencies for headless Chromium (Ubuntu/Debian):**
```bash
sudo apt-get install -y libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2
```
*(Or run `npx playwright install-deps` after installing Playwright.)*

---

## 10. Network tools

| Tool  | Status   | Version / details |
|-------|----------|-------------------|
| **curl** | Installed | 8.5.0 |
| **wget** | Installed | GNU Wget 1.21.4 |

No action needed.

---

## Summary

| # | Component      | Installed | Action |
|---|----------------|-----------|--------|
| 1 | System (CPU/RAM/Disk) | Yes | None |
| 2 | Node.js        | Yes (v18.19.1) | None |
| 3 | npm            | Yes (9.2.0) | None |
| 4 | Python         | Yes (3.12.3) | None |
| 5 | Git            | Yes (2.43.0) | None |
| 6 | Docker         | Yes (29.3.0) | None |
| 7 | PostgreSQL     | **No** | `sudo apt-get install -y postgresql postgresql-client` |
| 8 | PM2            | Yes (6.0.14) | None |
| 9 | Playwright/Puppeteer | Playwright via npx; Puppeteer not installed | Add to project: `npm install playwright` or `npm install puppeteer`; then browser install/deps as above |
| 10 | curl / wget    | Yes | None |

**Only missing system-level piece:** PostgreSQL (install if your bot needs a local database).
