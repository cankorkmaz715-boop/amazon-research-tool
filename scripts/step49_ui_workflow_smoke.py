#!/usr/bin/env python3
"""Step 49: Research workflow UI integration – discovery, metrics, scores, saved views, watchlists."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from dotenv import load_dotenv
    load_dotenv()
    from amazon_research.db import init_db
    from amazon_research.api import (
        get_products,
        get_metrics,
        get_scores,
        get_saved_views,
        get_watchlists,
        get_watchlist_items,
    )

    init_db()

    # Discovery view: products endpoint returns { data, meta }
    r_products = get_products(limit=5)
    discovery_ok = isinstance(r_products, dict) and "data" in r_products and "meta" in r_products

    # Metrics view: metrics endpoint returns { data, meta }
    r_metrics = get_metrics(limit=5)
    metrics_ok = isinstance(r_metrics, dict) and "data" in r_metrics and "meta" in r_metrics

    # Scores view: scores endpoint returns { data, meta }
    r_scores = get_scores(limit=5)
    scores_ok = isinstance(r_scores, dict) and "data" in r_scores and "meta" in r_scores

    # Saved views integration: saved_views endpoint returns { data, meta }
    r_views = get_saved_views(workspace_id=1, limit=5)
    saved_views_ok = isinstance(r_views, dict) and "data" in r_views and "meta" in r_views

    # Watchlist integration: watchlists and watchlist_items return { data, meta }
    r_watchlists = get_watchlists(workspace_id=1, limit=5)
    r_items = get_watchlist_items(watchlist_id=1, limit=5)
    watchlist_ok = (
        isinstance(r_watchlists, dict) and "data" in r_watchlists and "meta" in r_watchlists
        and isinstance(r_items, dict) and "data" in r_items and "meta" in r_items
    )

    # Workflow UI file exists and contains workflow section labels
    ui_path = os.path.join(ROOT, "internal_ui", "workflow.html")
    ui_ok = os.path.isfile(ui_path)
    if ui_ok:
        with open(ui_path, "r", encoding="utf-8") as f:
            html = f.read()
        ui_ok = (
            "discovery" in html.lower()
            and "metrics" in html.lower()
            and "scores" in html.lower()
            and "saved" in html.lower() and "view" in html.lower()
            and "watchlist" in html.lower()
        )

    print("ui workflow integration OK")
    print("discovery view: OK" if discovery_ok else "discovery view: FAIL")
    print("metrics view: OK" if metrics_ok else "metrics view: FAIL")
    print("scores view: OK" if scores_ok else "scores view: FAIL")
    print("saved views integration: OK" if saved_views_ok else "saved views integration: FAIL")
    print("watchlist integration: OK" if watchlist_ok else "watchlist integration: FAIL")
    if not ui_ok:
        print("workflow UI file: FAIL (missing or missing sections)")
    else:
        print("workflow UI file: OK")

    if not (discovery_ok and metrics_ok and scores_ok and saved_views_ok and watchlist_ok and ui_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
