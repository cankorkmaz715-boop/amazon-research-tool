"""
Step 234: Real opportunity feed – map repository rows to stable dashboard/API item shape.
Preserves payload shape expected by dashboard and GET /api/workspaces/{id}/opportunities.
"""
from typing import Any, Dict, List

from amazon_research.opportunity_feed.opportunity_feed_types import SOURCE_REAL, stable_feed_item


def _label_from_context(context: Dict[str, Any], ref: str) -> str:
    if not context:
        return ref or ""
    title = context.get("title") or context.get("label") or context.get("product_title")
    if isinstance(title, str) and title.strip():
        return title.strip()[:200]
    asin = context.get("asin") or ""
    market = context.get("market") or ""
    if asin or market:
        return f"{market}:{asin}" if market and asin else (asin or market or ref)
    return ref or ""


def _market_from_context(context: Dict[str, Any]) -> str:
    if not context:
        return ""
    m = context.get("market") or context.get("locale") or ""
    return m[:20] if isinstance(m, str) else ""


def _category_from_context(context: Dict[str, Any]) -> str:
    if not context:
        return ""
    c = context.get("category") or context.get("category_id") or ""
    return str(c)[:100] if c else ""


def _risk_notes(ranking: Dict[str, Any]) -> List[str]:
    if not ranking or not isinstance(ranking, dict):
        return []
    notes = []
    comp = ranking.get("competition_score")
    if comp is not None:
        try:
            if float(comp) > 70:
                notes.append("High competition score")
        except (TypeError, ValueError):
            pass
    return notes


def _priority_from_score(score: float) -> str:
    if score is None:
        return "low"
    try:
        s = float(score)
        if s >= 70:
            return "high"
        if s >= 50:
            return "medium"
    except (TypeError, ValueError):
        pass
    return "low"


def _strategy_status_from_score(score: float) -> str:
    if score is None:
        return "monitor"
    try:
        s = float(score)
        if s >= 70:
            return "act_now"
        if s >= 50:
            return "monitor"
    except (TypeError, ValueError):
        pass
    return "deprioritize"


def map_to_feed_items(rows: List[Dict[str, Any]], source_type: str = SOURCE_REAL) -> List[Dict[str, Any]]:
    """
    Map repository output (list_real_opportunities_for_workspace) to stable feed items.
    Each item has opportunity_id, title, label, score, opportunity_score, priority_level,
    strategy_status, rationale, recommended_action, risk_notes, market, category, source_type.
    """
    out: List[Dict[str, Any]] = []
    for r in rows:
        ref = (r.get("opportunity_ref") or "").strip()
        if not ref:
            continue
        ctx = r.get("context") or {}
        rank = r.get("ranking") or {}
        score = r.get("latest_opportunity_score")
        label = _label_from_context(ctx, ref)
        priority = _priority_from_score(score)
        status = _strategy_status_from_score(score)
        rationale = "Real opportunity from pipeline; score and ranking data."
        if score is not None:
            rationale = f"Score {score:.0f}; classified as {status}."
        recommended = "Review and decide" if status == "act_now" else ("Monitor metrics" if status == "monitor" else "No action unless signals change")
        risk_notes = _risk_notes(rank)
        item = stable_feed_item(
            opportunity_id=ref,
            title=label,
            label=label,
            score=score,
            priority_level=priority,
            strategy_status=status,
            rationale=rationale,
            recommended_action=recommended,
            risk_notes=risk_notes,
            market=_market_from_context(ctx) or None,
            category=_category_from_context(ctx) or None,
            source_type=source_type,
        )
        item["opportunity_score"] = score
        # Step 235: pass through calibration fields when present (normalized_score, ranking_position, supporting_signal_hints)
        if r.get("normalized_score") is not None:
            item["normalized_score"] = r.get("normalized_score")
        if r.get("ranking_position") is not None:
            item["ranking_position"] = r.get("ranking_position")
        if r.get("supporting_signal_hints") is not None:
            item["supporting_signal_hints"] = list(r.get("supporting_signal_hints") or [])
        if r.get("priority_band") is not None:
            item["priority_band"] = r.get("priority_band")
        out.append(item)
    return out
