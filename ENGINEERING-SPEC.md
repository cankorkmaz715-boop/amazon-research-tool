# Engineering Spec – Task Execution

This doc locks in how every implementation task is scoped and delivered. Follow it for all code, planning, and file structure.

---

## Response format (every task)

1. **Goal** – What we are building or changing  
2. **Architecture decision** – How it fits proxy / browser / DB / queue / monitoring  
3. **Files to create or edit** – Paths and roles  
4. **Exact code** – Production-minded, not demo code  
5. **How to test** – Concrete steps to verify  
6. **Risks / notes** – Edge cases, env vars, migrations, follow-ups  

---

## Development style

- **Define structure first** – Folders, modules, boundaries  
- **Then define files** – What lives where  
- **Then implement one module at a time** – No giant rewrites  
- **After each step** – Explain how to test it  
- **Improvements** – Incremental; do not break working parts  

---

## Mandatory principles

- **Language:** Python unless there is a very strong reason otherwise  
- **Browser:** Playwright  
- **DB:** PostgreSQL  
- **Modular:** Separate scraping, parsing, storage, scheduling, scoring  
- **Production-minded:** Real error handling, logging, retries, timeouts  
- **Secrets:** Environment variables only  
- **Proxy:** Central proxy layer; configurable and swappable  
- **Scraping:** Human-like, conservative; delays, backoff, graceful failure  
- **Monitoring:** Ready for Uptime Kuma, Grafana, Sentry, optional Telegram/Discord  
- **SaaS-ready:** Clean structure so a future SaaS layer can be added without rewrites  

---

## What to avoid

- Generic or tutorial-style advice  
- Shallow one-off scripts  
- Rewriting the whole project unnecessarily  
- Breaking existing working logic  
- Scattering proxy or config across the codebase  
- Aggressive or unnatural scraping patterns  

---

## Step workflow (Steps 20–30)

When implementing roadmap steps:

1. **Implement the step** – Code and config for the current step only. Same architecture and order (Step 20 → … → Step 30).
2. **Provide the host-side test command** – Exact command to run the step’s smoke test.
3. **Wait for the user to run the command.**
4. **Proceed on success** – If the user confirms success or shows successful output, **immediately proceed to the next step**. Do **not** require the phrase "Step X passed". Any clear success indication is enough.

Do not wait for explicit "Step X passed". Continue to the next step as soon as the user indicates success.

---

## When something is not yet implemented

Propose the **cleanest next step** only. Prefer small, correct, testable steps. Keep the project stable.
