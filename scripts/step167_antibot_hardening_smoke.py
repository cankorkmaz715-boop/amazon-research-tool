#!/usr/bin/env python3
"""Step 167: Anti-bot hardening layer – session rotation, UA/header randomization, jitter, captcha detection."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from amazon_research.monitoring.antibot_hardening import (
        get_current_session_id,
        should_rotate_session,
        rotate_session,
        session_rotation_manager_status,
        get_random_user_agent,
        user_agent_randomizer_status,
        get_header_variation,
        get_headers_for_request,
        header_variation_status,
        get_request_jitter_delay,
        request_jitter_status,
        captcha_detection,
        block_response_classifier,
        get_antibot_status,
        CLASS_CAPTCHA,
        CLASS_BOT_DETECTION,
        CLASS_OK,
    )

    # 1) Session rotation
    s1 = get_current_session_id()
    st = session_rotation_manager_status()
    session_ok = (
        isinstance(s1, str)
        and len(s1) > 0
        and st.get("status") == "OK"
        and "current_session_id" in st
    )
    s2 = rotate_session()
    session_ok = session_ok and s2 != s1 and get_current_session_id() == s2

    # 2) Header randomization (user-agent + header variation)
    ua = get_random_user_agent()
    ua_ok = ua and "Mozilla" in ua
    h = get_header_variation()
    h_ok = "Accept-Language" in h and "Cache-Control" in h and "Connection" in h
    full = get_headers_for_request(include_user_agent=True)
    h_ok = h_ok and "User-Agent" in full and full["User-Agent"]
    rand_status = user_agent_randomizer_status()
    header_ok = ua_ok and h_ok and rand_status.get("status") == "OK" and header_variation_status().get("status") == "OK"

    # 3) Request jitter
    d = get_request_jitter_delay(base_delay=0.5, jitter_max=1.0)
    jitter_ok = isinstance(d, (int, float)) and d >= 0.5 and d <= 1.5
    js = request_jitter_status()
    jitter_ok = jitter_ok and js.get("status") == "OK" and "sample_delay_seconds" in js

    # 4) Captcha detection
    cap_ok_page = captcha_detection(html="<html><body>Hello</body></html>")
    cap_block = captcha_detection(html="<html><body>Please complete the CAPTCHA</body></html>")
    captcha_ok = (
        cap_ok_page.get("detected") is False
        and cap_ok_page.get("status") == "OK"
        and cap_block.get("detected") is True
        and cap_block.get("reason") == "captcha_or_block"
    )

    # Block response classifier
    cls_ok = block_response_classifier(html="<html>normal page</html>")
    cls_cap = block_response_classifier(html="<html>unusual traffic from your network captcha</html>")
    cls_bot = block_response_classifier(html="<html>bot detection page automated access</html>")
    classifier_ok = (
        cls_ok.get("classification") == CLASS_OK
        and cls_cap.get("classification") == CLASS_CAPTCHA
        and cls_bot.get("classification") == CLASS_BOT_DETECTION
    )

    agg = get_antibot_status()
    agg_ok = (
        agg.get("anti_bot_status") == "OK"
        and agg.get("session_rotation") == "OK"
        and agg.get("header_randomization") == "OK"
        and agg.get("request_jitter") == "OK"
        and agg.get("captcha_detection") == "OK"
    )

    print("anti-bot hardening layer OK")
    print("session rotation: OK" if session_ok else "session rotation: FAIL")
    print("header randomization: OK" if header_ok else "header randomization: FAIL")
    print("request jitter: OK" if jitter_ok else "request jitter: FAIL")
    print("captcha detection: OK" if captcha_ok else "captcha detection: FAIL")

    if not (session_ok and header_ok and jitter_ok and captcha_ok and agg_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
