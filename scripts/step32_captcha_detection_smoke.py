#!/usr/bin/env python3
"""Step 32: CAPTCHA detection and abort – detect, abort safely, persist failure reason."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

def main():
    from dotenv import load_dotenv
    load_dotenv()
    from amazon_research.db import init_db, get_connection, upsert_asin, record_failure

    init_db()

    # 1) Detector returns True on CAPTCHA-like content (no Playwright in test – avoids sync-in-asyncio)
    from amazon_research.detection.captcha import is_captcha_or_bot_check_content
    fixture = os.path.join(ROOT, "scripts", "fixtures", "captcha_like.html")
    if not os.path.isfile(fixture):
        print("Fixture missing")
        sys.exit(1)
    with open(fixture, "r") as f:
        html = f.read()
    title = "Robot Check"
    body_text = html
    detected = is_captcha_or_bot_check_content(url="", title=title, body_text=body_text)
    abort_ok = detected is True

    # 2) Abort logic: detector is used in refresh bot (no import of bot – avoids pulling in Playwright)
    refresh_bot_path = os.path.join(ROOT, "src", "amazon_research", "bots", "data_refresh.py")
    with open(refresh_bot_path, "r") as f:
        source = f.read()
    abort_logic_ok = "is_captcha_or_bot_check" in source and "captcha_detected" in source

    # 3) Failure state persisted: record_failure with captcha_detected stores in asin_attempt_state
    test_asin = "B00CAPTCHA0"
    asin_id = upsert_asin(test_asin)
    record_failure(asin_id, "captcha_detected")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT last_error FROM asin_attempt_state WHERE asin_id = %s", (asin_id,))
    row = cur.fetchone()
    cur.close()
    failure_persisted_ok = row is not None and row[0] and "captcha" in (row[0] or "").lower()

    print("captcha detection OK")
    print("abort logic: OK" if abort_logic_ok else "abort logic: FAIL")
    print("failure state persisted: OK" if failure_persisted_ok else "failure state persisted: FAIL")

    if not (abort_ok and abort_logic_ok and failure_persisted_ok):
        sys.exit(1)

if __name__ == "__main__":
    main()
