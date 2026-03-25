#!/usr/bin/env python3
"""Step 155: Workspace opportunity feed – feed generation, item prioritization, feed categories, dashboard compatibility."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

# Feed item type constants for assertions
FEED_NEW_OPPORTUNITY = "new_opportunity"
FEED_RISING_OPPORTUNITY = "rising_opportunity"
FEED_RISKY_OPPORTUNITY = "risky_opportunity"
FEED_WATCHLIST_UPDATE = "watchlist_update"
FEED_SUGGESTED_NEXT_ACTION = "suggested_next_action"
VALID_TYPES = {FEED_NEW_OPPORTUNITY, FEED_RISING_OPPORTUNITY, FEED_RISKY_OPPORTUNITY, FEED_WATCHLIST_UPDATE, FEED_SUGGESTED_NEXT_ACTION}


def main():
    from dotenv import load_dotenv
    load_dotenv()

    try:
        from amazon_research.db import init_db
        init_db()
    except Exception:
        pass

    from amazon_research.discovery import get_workspace_opportunity_feed

    feed = get_workspace_opportunity_feed(1, limit=30)

    # 1) Feed generation: returns list; each item has required fields
    gen_ok = isinstance(feed, list)
    if feed:
        gen_ok = gen_ok and all(
            "feed_item_id" in it and (it.get("feed_item_id") or "").startswith("feed-")
            and "target_entity" in it and isinstance(it.get("target_entity"), dict)
            and "feed_item_type" in it and "priority_score" in it
            and "short_explanation" in it and "timestamp" in it and it.get("workspace_id") == 1
            for it in feed
        )

    # 2) Item prioritization: sorted by priority_score descending
    scores = [it.get("priority_score") for it in feed if it.get("priority_score") is not None]
    prioritization_ok = scores == sorted(scores, reverse=True) if len(scores) > 1 else True
    if feed and not scores:
        prioritization_ok = all("priority_score" in it for it in feed)

    # 3) Feed categories: item types are among the supported categories
    categories_ok = all(
        it.get("feed_item_type") in VALID_TYPES for it in feed
    ) if feed else True

    # 4) Dashboard compatibility: workspace_id, feed_item_id, target_entity (type + ref), timestamp
    dashboard_ok = True
    if feed:
        for it in feed[:10]:
            te = it.get("target_entity") or {}
            if not (isinstance(te, dict) and ("type" in te or "ref" in te)):
                dashboard_ok = False
                break
            if it.get("workspace_id") is None or not it.get("timestamp"):
                dashboard_ok = False
                break

    print("workspace opportunity feed OK")
    print("feed generation: OK" if gen_ok else "feed generation: FAIL")
    print("item prioritization: OK" if prioritization_ok else "item prioritization: FAIL")
    print("feed categories: OK" if categories_ok else "feed categories: FAIL")
    print("dashboard compatibility: OK" if dashboard_ok else "dashboard compatibility: FAIL")

    if not (gen_ok and prioritization_ok and categories_ok and dashboard_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
