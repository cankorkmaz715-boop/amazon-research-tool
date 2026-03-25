#!/usr/bin/env python3
"""Step 34: Alerting v1 – optional pipeline failure webhook; disabled when env missing."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

def main():
    os.environ.pop("ALERT_WEBHOOK_URL", None)
    from dotenv import load_dotenv
    load_dotenv()

    from amazon_research.monitoring import send_pipeline_failure_alert

    # Alert hook exists and is callable (ready)
    hook_ok = callable(send_pipeline_failure_alert)

    # Disabled-by-default: call with no webhook set must not raise
    try:
        send_pipeline_failure_alert({"ok": False, "stopped_at": "refresh", "error": "test", "stages_completed": ["discovery"]})
        disabled_ok = True
    except Exception:
        disabled_ok = False

    print("alerting v1 OK")
    print("alert hook: ready" if hook_ok else "alert hook: FAIL")
    print("disabled-by-default: OK" if disabled_ok else "disabled-by-default: FAIL")

    if not (hook_ok and disabled_ok):
        sys.exit(1)

if __name__ == "__main__":
    main()
