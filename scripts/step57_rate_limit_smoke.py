#!/usr/bin/env python3
"""Step 57: Rate limiting v1 – within limit, over limit blocked, clear result, workspace scope."""
import os
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from dotenv import load_dotenv
    load_dotenv()
    from amazon_research.rate_limit import (
        check_rate_limit,
        record_rate_limit,
        check_and_raise,
        RateLimitExceededError,
    )
    from amazon_research.db import init_db, create_workspace

    init_db()
    ws1 = create_workspace("RateLimit WS 1", slug="step57-rl-ws1")
    ws2 = create_workspace("RateLimit WS 2", slug="step57-rl-ws2")

    # Within limit: limit=3, use 2 -> allowed
    allowed1, _ = check_rate_limit(ws1, "api", 3, 60.0)
    within_ok = allowed1
    record_rate_limit(ws1, "api")
    record_rate_limit(ws1, "api")
    allowed2, _ = check_rate_limit(ws1, "api", 3, 60.0)
    within_ok = within_ok and allowed2

    # Over limit blocked: 3rd record, 4th check -> blocked
    record_rate_limit(ws1, "api")
    allowed3, retry_after = check_rate_limit(ws1, "api", 3, 60.0)
    over_blocked_ok = not allowed3 and retry_after is not None and retry_after >= 1

    # Clear rate-limit result: exception has bucket and retry_after_seconds
    clear_ok = False
    try:
        check_and_raise(ws1, "api", 3, 60.0)
    except RateLimitExceededError as e:
        clear_ok = e.bucket == "api" and e.retry_after_seconds >= 1

    # Workspace/API-key scope: ws2 has separate counter (still under limit)
    allowed_ws2, _ = check_rate_limit(ws2, "api", 3, 60.0)
    scope_ok = allowed_ws2
    # Export bucket is per-workspace too
    record_rate_limit(ws1, "export")
    record_rate_limit(ws1, "export")
    check_and_raise(ws2, "export", 2, 60.0)  # ws2 has 0, limit 2 -> ok
    record_rate_limit(ws2, "export")
    try:
        check_and_raise(ws1, "export", 2, 60.0)  # ws1 has 2, limit 2 -> next would be 3rd, blocked
    except RateLimitExceededError:
        scope_ok = scope_ok and True
    else:
        scope_ok = False

    print("rate limiting v1 OK")
    print("within limit: OK" if within_ok else "within limit: FAIL")
    print("over limit blocked: OK" if over_blocked_ok else "over limit blocked: FAIL")
    print("clear rate-limit result: OK" if clear_ok else "clear rate-limit result: FAIL")
    print("workspace/api-key scope: OK" if scope_ok else "workspace/api-key scope: FAIL")

    if not (within_ok and over_blocked_ok and clear_ok and scope_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
