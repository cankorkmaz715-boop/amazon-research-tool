#!/usr/bin/env python3
"""Step 112: Operational health monitor – worker, queue, crawler, latency, scheduler health."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

VALID = ("healthy", "warning", "critical")


def main():
    from dotenv import load_dotenv
    load_dotenv()

    from amazon_research.monitoring import get_operational_health

    out = get_operational_health()
    components = out.get("components") or {}
    overall = out.get("overall")

    worker_ok = (
        "worker" in components
        and components["worker"].get("status") in VALID
        and "message" in components["worker"]
    )
    queue_ok = (
        "queue" in components
        and components["queue"].get("status") in VALID
        and "message" in components["queue"]
    )
    crawler_ok = (
        "crawler" in components
        and components["crawler"].get("status") in VALID
        and "message" in components["crawler"]
    )
    latency_ok = (
        "latency" in components
        and components["latency"].get("status") in VALID
        and "message" in components["latency"]
    )
    scheduler_ok = (
        "scheduler" in components
        and components["scheduler"].get("status") in VALID
        and "message" in components["scheduler"]
    )

    print("operational health monitor OK")
    print("worker health: OK" if worker_ok else "worker health: FAIL")
    print("queue health: OK" if queue_ok else "queue health: FAIL")
    print("crawler health: OK" if crawler_ok else "crawler health: FAIL")
    print("latency health: OK" if latency_ok else "latency health: FAIL")
    print("scheduler health: OK" if scheduler_ok else "scheduler health: FAIL")

    if not (worker_ok and queue_ok and crawler_ok and latency_ok and scheduler_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
