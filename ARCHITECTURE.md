# Amazon Research Tool – Architecture & Development Rules

Production-oriented internal tool for Amazon FBA product discovery. Designed to evolve into a sellable SaaS.

---

## CORE PRODUCT GOAL

Reliable Amazon product research and opportunity discovery: discover, refresh, analyze, and score Amazon ASINs at scale.

---

## FIXED ARCHITECTURE RULES

- **Deployment:** VPS
- **Database:** PostgreSQL
- **Scraping:** proxy management, headless browser automation, captcha-handling readiness, scheduler/queue
- **Browser automation:** Playwright preferred, Puppeteer acceptable
- **Data flow:** scraper → parser → PostgreSQL → scoring engine → dashboard/API
- **Monitoring / observability:** Uptime Kuma, Grafana, Sentry; optional Telegram/Discord alerts

Do not replace this architecture unless strictly necessary. Build within it.

---

## MAIN SYSTEM MODULES

1. **ASIN discovery bot** – category/listing/grid scans, new ASIN discovery, core product metadata
2. **Data refresh / update bot** – revisit known ASINs, update price/BSR/reviews/rating/sellers/stock, store history
3. **Opportunity scoring / analysis engine** – competition score, demand score, opportunity score, bundle/kit detection, low-competition flags

Modules must integrate cleanly.

---

## DEVELOPMENT PRIORITY ORDER

1. High-quality Amazon data collection  
2. Opportunity / competition analysis algorithms  
3. Automation of category scanning and opportunity discovery  
4. Clean UX dashboard  
5. Stable backend infrastructure  
6. Monitoring / observability  
7. Internal tool first  
8. Later evolution into SaaS  

Prioritize earlier items when making implementation decisions.

---

## ENGINEERING PRINCIPLES

- Modular, production-oriented code; maintainability over hacks  
- Do not break existing working logic; improve incrementally  
- Clear folder structure; comments only where useful  
- Avoid overengineering in early stage  
- Secrets and configs via environment variables  
- Configurable: proxy, scraping intervals, category targets, scoring thresholds  

---

## RELIABILITY RULES

- Retries, timeouts, proxy rotation, random delays  
- Browser fingerprint stability  
- Error logging, structured logs  
- Anti-blocking; partial failure tolerance  
- One page/product/worker failure must not bring down the pipeline; failures must be visible in logs  

---

## DATA REQUIREMENTS (MINIMUM)

Store and update: ASIN, title, category, brand, price, BSR, rating, review count, seller count, FBA/FBM signal, package size/weight if available, product URL, main image, timestamps, historical snapshots.

**PostgreSQL table logic (names refinable):**

- `asins`
- `product_metrics`
- `price_history`
- `review_history`
- `category_scans`
- `scoring_results`
- `bot_runs`
- `error_logs`

Design for future analytics.

---

## SCORING / ANALYSIS EXPECTATIONS

Support: competition score, demand score, opportunity score, review velocity, rating risk, seller saturation, price stability, bundle/kit opportunity logic.  
Structure scoring so formulas can be adjusted later.

---

## DASHBOARD / API EXPECTATIONS

- Clean, practical UI: opportunity list, filters, product detail, scoring visibility, category scan visibility, bot health  
- API/backend organized for future SaaS layer without rewrites  

---

## MONITORING EXPECTATIONS

- Uptime checks, error tracking, performance metrics, worker/bot failure visibility  
- Sentry-compatible error capture; logs structured for Grafana/observability  
- Bot health endpoints preferred  

---

## TASK EXECUTION RULES

When asked to build or improve a module:

1. Preserve existing architecture  
2. Avoid breaking existing code  
3. Briefly explain what will be added/changed  
4. Then implement  
5. Note required env vars, migrations/DB changes, how to test  
6. Keep code production-oriented  

Large requests: break into backend, DB, bot logic, API, UI, test steps.

---

## OUTPUT FORMAT FOR IMPLEMENTATION TASKS

1. Objective  
2. What will change  
3. Files to create/update  
4. Code  
5. Environment variables  
6. Database migration changes  
7. Test steps  
8. Risks / notes  

---

## CONSTRAINTS

- Do not remove working features unless necessary  
- Do not rewrite unrelated modules  
- Do not oversimplify scraping logic  
- No toy/demo architecture  
- Keep PostgreSQL + VPS + proxy + headless browser model  
- Preserve future SaaS extensibility  
- Do not ignore monitoring and error visibility  

---

## LANGUAGE & STACK (MANDATORY)

- **Primary language: Python** unless there is a very strong reason otherwise  
- **Browser automation:** Playwright  
- **Database:** PostgreSQL  
- **API:** REST; simple queue/job; cron or worker scheduler  
- Docker-friendly structure where useful  

---

## PROXY REQUIREMENTS

- Proxy usage must be **central** (one layer), not scattered across the codebase  
- Proxy configuration must be easy to swap or extend (e.g. different providers, strategies)  
- Design so different proxy strategies can be added later  
- Use bandwidth carefully and efficiently (5 GB plan is finite)  

---

## HUMAN-LIKE / CONSERVATIVE SCRAPING

- Rotate proxies carefully; reuse sessions when reasonable  
- Randomized delays where needed; avoid unnatural navigation speed  
- Do not request too many pages too quickly  
- Retry with backoff; fail gracefully; log failures  
- Prepare for captcha: codebase must detect and handle captcha events cleanly when added  
- Anti-detection precautions; conservative, human-like behavior  

---

## RESPONSE FORMAT (EVERY TASK)

For every implementation or planning task, respond in this order:

1. **Goal**  
2. **Architecture decision**  
3. **Files to create or edit**  
4. **Exact code**  
5. **How to test**  
6. **Risks / notes**  

Do not give generic or tutorial-style output. Think like a real systems architect. Prefer small, correct, testable steps over large risky rewrites.

---

## FINAL BEHAVIOR

Act as a senior engineer improving a real internal product with future commercial use.  
Optimize for: data quality, stability, scalability, maintainability, future monetization.
