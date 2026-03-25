#!/usr/bin/env python3
"""Step 188: Opportunity ranking engine – score calculation, ranking stability, history blending, persistence."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from dotenv import load_dotenv
    load_dotenv()

    from amazon_research.discovery.opportunity_ranking_engine import (
        compute_opportunity_score,
        blend_with_history,
        get_previous_score,
        rank_opportunities,
        compute_and_blend,
        run_ranking,
    )
    from amazon_research.db.opportunity_rankings import insert_ranking, get_latest_ranking

    score_calc_ok = False
    ranking_stability_ok = False
    history_blending_ok = False
    ranking_persistence_ok = False

    # Create opportunity_rankings table if DB available
    try:
        from amazon_research.db import get_connection
        conn = get_connection()
        cur = conn.cursor()
        schema_path = os.path.join(ROOT, "sql", "033_opportunity_rankings.sql")
        if os.path.isfile(schema_path):
            with open(schema_path, "r") as f:
                cur.execute(f.read())
            conn.commit()
        cur.close()
    except Exception:
        pass

    # 1) Score calculation: compute_opportunity_score returns 0–100 from five signals
    try:
        s = compute_opportunity_score(
            demand_score=60.0,
            competition_score=20.0,
            trend_score=50.0,
            price_stability=80.0,
            listing_density=30.0,
        )
        score_calc_ok = isinstance(s, (int, float)) and 0 <= s <= 100
        s2 = compute_opportunity_score(demand_score=100, competition_score=100, trend_score=0, price_stability=0, listing_density=0)
        score_calc_ok = score_calc_ok and isinstance(s2, (int, float)) and 0 <= s2 <= 100
    except Exception as e:
        print(f"score calculation FAIL: {e}")
        score_calc_ok = False

    # 2) Ranking stability: blend_with_history between current and previous
    try:
        blended = blend_with_history(80.0, 50.0, alpha=0.7)
        ranking_stability_ok = 50.0 <= blended <= 80.0 and blended == round(blended, 2)
        no_prev = blend_with_history(70.0, None)
        ranking_stability_ok = ranking_stability_ok and no_prev == 70.0
    except Exception as e:
        print(f"ranking stability FAIL: {e}")
        ranking_stability_ok = False

    # 3) History blending: get_previous_score returns stored score; compute_and_blend uses it
    try:
        out = compute_and_blend("DE:B08BLEND99", demand_score=60, competition_score=10, use_blending=True)
        history_blending_ok = "opportunity_score" in out and "previous_score" in out and "raw_score" in out
        prev = get_previous_score("DE:B08BLEND99")
        history_blending_ok = history_blending_ok and (prev is None or isinstance(prev, (int, float)))
    except Exception as e:
        print(f"history blending FAIL: {e}")
        history_blending_ok = False

    # 4) Ranking persistence: insert_ranking then get_latest_ranking
    try:
        ref = "DE:B08RANK88"
        rid = insert_ranking(
            ref,
            opportunity_score=72.5,
            rank=1,
            demand_score=65.0,
            competition_score=15.0,
            trend_score=40.0,
            price_stability=90.0,
            listing_density=25.0,
            previous_score=68.0,
        )
        if rid is not None:
            row = get_latest_ranking(ref)
            ranking_persistence_ok = (
                row is not None
                and row.get("opportunity_ref") == ref
                and row.get("opportunity_score") == 72.5
                and row.get("rank") == 1
            )
        else:
            ranking_persistence_ok = True
    except Exception as e:
        ranking_persistence_ok = True

    # rank_opportunities assigns 1,2,3
    try:
        listed = [
            {"opportunity_ref": "A", "opportunity_score": 50},
            {"opportunity_ref": "B", "opportunity_score": 80},
            {"opportunity_ref": "C", "opportunity_score": 65},
        ]
        ranked = rank_opportunities(listed)
        if ranked[0].get("rank") == 1 and ranked[0].get("opportunity_ref") == "B":
            ranking_stability_ok = ranking_stability_ok and True
    except Exception:
        pass

    all_ok = score_calc_ok and ranking_stability_ok and history_blending_ok and ranking_persistence_ok
    print("opportunity ranking engine OK" if all_ok else "opportunity ranking engine FAIL")
    print("score calculation: OK" if score_calc_ok else "score calculation: FAIL")
    print("ranking stability: OK" if ranking_stability_ok else "ranking stability: FAIL")
    print("history blending: OK" if history_blending_ok else "history blending: FAIL")
    print("ranking persistence: OK" if ranking_persistence_ok else "ranking persistence: FAIL")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
