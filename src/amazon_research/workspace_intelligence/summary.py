"""
Step 191: Workspace intelligence summary – normalized aggregate of key signals per workspace.
Single trusted source for dashboard, copilot, and strategy layers. Computed-on-read; structure allows persistence later.
"""
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("workspace_intelligence.summary")

# High-priority score threshold (align with alert engine)
HIGH_PRIORITY_SCORE_THRESHOLD = 70.0
# Recent window for "new" opportunities (hours)
RECENT_WINDOW_HOURS = 24
# Max refs to consider for workspace-scoped rankings
MAX_OPPORTUNITY_REFS = 2000
# Top opportunity refs returned in summary
TOP_OPPORTUNITY_REFS_LIMIT = 20


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _safe_int(v: Any, default: int = 0) -> int:
    if v is None:
        return default
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _safe_float(v: Any, default: float = 0.0) -> float:
    if v is None:
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _default_summary(workspace_id: Optional[int]) -> Dict[str, Any]:
    """Stable default shape when no data is available."""
    return {
        "workspace_id": workspace_id,
        "summary_timestamp": _now_utc().isoformat(),
        "total_tracked_opportunities": 0,
        "active_high_priority_count": 0,
        "new_opportunities_recent_window": 0,
        "average_opportunity_score": 0.0,
        "top_opportunity_refs": [],
        "trend_overview": {},
        "alert_overview": {},
        "category_coverage_overview": {},
        "market_coverage_overview": {},
    }


def _get_opportunity_memory_count(workspace_id: Optional[int]) -> int:
    """Count opportunity_memory rows for workspace. Returns 0 on error."""
    if workspace_id is None:
        return 0
    try:
        from amazon_research.db import get_connection
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """SELECT COUNT(*) FROM opportunity_memory
               WHERE (workspace_id = %s OR workspace_id IS NULL)""",
            (workspace_id,),
        )
        row = cur.fetchone()
        cur.close()
        return _safe_int(row[0] if row else 0)
    except Exception as e:
        logger.warning("workspace_intelligence summary: count opportunity_memory failed workspace_id=%s: %s", workspace_id, e)
        return 0


def _get_memory_rows(workspace_id: Optional[int], limit: int = MAX_OPPORTUNITY_REFS) -> List[Dict[str, Any]]:
    """List opportunity_memory for workspace. Returns [] on error."""
    if workspace_id is None:
        return []
    try:
        from amazon_research.db import list_opportunity_memory
        return list_opportunity_memory(limit=limit, workspace_id=workspace_id) or []
    except Exception as e:
        logger.warning("workspace_intelligence summary: list_opportunity_memory failed workspace_id=%s: %s", workspace_id, e)
        return []


def _get_workspace_rankings(workspace_id: Optional[int]) -> List[Dict[str, Any]]:
    """Rankings for refs that belong to this workspace. Filters get_latest_rankings by workspace refs."""
    mem = _get_memory_rows(workspace_id, limit=MAX_OPPORTUNITY_REFS)
    refs = {m.get("opportunity_ref") for m in mem if m.get("opportunity_ref")}
    if not refs:
        return []
    try:
        from amazon_research.db.opportunity_rankings import get_latest_rankings, get_latest_ranking
        all_rankings = get_latest_rankings(limit=5000)
        return [r for r in (all_rankings or []) if (r.get("opportunity_ref") or "") in refs]
    except Exception as e:
        logger.warning("workspace_intelligence summary: workspace rankings failed workspace_id=%s: %s", workspace_id, e)
        return []


# Required keys for a valid cached summary payload (Step 192)
_SUMMARY_REQUIRED_KEYS = frozenset({
    "workspace_id", "summary_timestamp", "total_tracked_opportunities",
    "active_high_priority_count", "new_opportunities_recent_window",
    "average_opportunity_score", "top_opportunity_refs", "trend_overview",
    "alert_overview", "category_coverage_overview", "market_coverage_overview",
})


def get_workspace_intelligence_summary_prefer_cached(
    workspace_id: Optional[int],
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Return workspace intelligence summary: cache (if valid and not expired) -> persisted snapshot -> compute.
    On persistence or compute path, warms the cache. Safe fallback at each step; payload shape stable (Step 191/192).
    """
    if workspace_id is None:
        return _default_summary(workspace_id)
    # Step 196: workspace config for cache enable/ttl
    ws_config: Dict[str, Any] = {}
    try:
        from amazon_research.workspace_configuration import get_workspace_configuration_with_defaults
        ws_config = get_workspace_configuration_with_defaults(workspace_id) or {}
    except Exception:
        pass
    cache_enabled = ws_config.get("intelligence_cache_enabled", True)
    cache_ttl = ws_config.get("intelligence_cache_ttl_seconds", 300)
    try:
        from amazon_research.workspace_intelligence.metrics import record_read, record_cache_hit, record_cache_miss, record_snapshot_hit, record_compute_fallback
        record_read()
    except Exception:
        pass
    # 1) Cache hit (only if workspace has cache enabled)
    if cache_enabled:
        try:
            from amazon_research.workspace_intelligence.cache import get_cached_summary, set_cached_summary
            cached = get_cached_summary(workspace_id)
            if cached and _SUMMARY_REQUIRED_KEYS.issubset(cached.keys()):
                try:
                    record_cache_hit()
                except Exception:
                    pass
                return cached
            try:
                record_cache_miss()
            except Exception:
                pass
        except Exception as e:
            logger.warning(
                "workspace_intelligence summary cache read failed workspace_id=%s: %s",
                workspace_id,
                e,
            )
    else:
        try:
            record_cache_miss()
        except Exception:
            pass
    # 2) Persistence fallback
    try:
        from amazon_research.db.workspace_intelligence_snapshots import get_latest_workspace_intelligence_snapshot
        snap = get_latest_workspace_intelligence_snapshot(workspace_id)
        if snap and isinstance(snap.get("summary_json"), dict):
            payload = snap.get("summary_json") or {}
            if _SUMMARY_REQUIRED_KEYS.issubset(payload.keys()):
                generated_at = snap.get("generated_at")
                if generated_at and hasattr(generated_at, "isoformat"):
                    payload = dict(payload)
                    payload["summary_timestamp"] = generated_at.isoformat()
                if cache_enabled:
                    try:
                        from amazon_research.workspace_intelligence.cache import set_cached_summary
                        set_cached_summary(workspace_id, payload, ttl_seconds=cache_ttl)
                    except Exception:
                        pass
                try:
                    record_snapshot_hit()
                except Exception:
                    pass
                logger.info(
                    "workspace_intelligence persistence fallback workspace_id=%s",
                    workspace_id,
                    extra={"workspace_id": workspace_id},
                )
                return payload
    except Exception as e:
        logger.warning(
            "workspace_intelligence summary prefer_cached persistence failed workspace_id=%s: %s",
            workspace_id,
            e,
        )
    # 3) Compute fallback and warm cache
    try:
        record_compute_fallback()
    except Exception:
        pass
    logger.info(
        "workspace_intelligence compute fallback workspace_id=%s",
        workspace_id,
        extra={"workspace_id": workspace_id},
    )
    out = get_workspace_intelligence_summary(workspace_id, **kwargs)
    if cache_enabled:
        try:
            from amazon_research.workspace_intelligence.cache import set_cached_summary
            set_cached_summary(workspace_id, out, ttl_seconds=cache_ttl)
        except Exception:
            pass
    return out


def get_workspace_intelligence_summary(
    workspace_id: Optional[int],
    *,
    recent_window_hours: int = RECENT_WINDOW_HOURS,
    top_refs_limit: int = TOP_OPPORTUNITY_REFS_LIMIT,
) -> Dict[str, Any]:
    """
    Build normalized workspace intelligence summary. Resilient: safe defaults when data sources are empty.
    Returns stable payload: workspace_id, summary_timestamp, total_tracked_opportunities,
    active_high_priority_count, new_opportunities_recent_window, average_opportunity_score,
    top_opportunity_refs, trend_overview, alert_overview, category_coverage_overview, market_coverage_overview.
    """
    logger.info("workspace_intelligence summary build start workspace_id=%s", workspace_id)
    _build_start = time.time()
    out = _default_summary(workspace_id)
    if workspace_id is None:
        logger.warning("workspace_intelligence summary: workspace_id is None")
        return out

    try:
        # Total tracked
        out["total_tracked_opportunities"] = _get_opportunity_memory_count(workspace_id)
        mem_rows = _get_memory_rows(workspace_id)
        cutoff = _now_utc() - timedelta(hours=recent_window_hours)
        active_count = 0
        new_count = 0
        categories: Dict[str, int] = {}
        markets: Dict[str, int] = {}

        for m in mem_rows:
            ref = (m.get("opportunity_ref") or "").strip()
            if ref:
                market = ref.split(":")[0] if ":" in ref else "DE"
                markets[market] = markets.get(market, 0) + 1
            ctx = m.get("context") or {}
            if isinstance(ctx, dict):
                sid = (ctx.get("source_id") or "").strip() or (ctx.get("source_type") or "").strip()
                if sid:
                    categories[sid] = categories.get(sid, 0) + 1
            status = (m.get("status") or "").strip()
            raw_score = m.get("latest_opportunity_score")
            has_high_score = raw_score is not None and _safe_float(raw_score) >= HIGH_PRIORITY_SCORE_THRESHOLD
            if status in ("strengthening", "recurring") or has_high_score:
                active_count += 1
            first_seen = m.get("first_seen_at")
            if first_seen:
                if hasattr(first_seen, "replace") and getattr(first_seen, "tzinfo", None) is None:
                    first_seen = first_seen.replace(tzinfo=timezone.utc) if first_seen else None
                if first_seen and first_seen >= cutoff:
                    new_count += 1

        out["active_high_priority_count"] = active_count
        out["new_opportunities_recent_window"] = new_count
        out["category_coverage_overview"] = {"categories": list(categories.keys())[:50], "count_by_id": categories}
        out["market_coverage_overview"] = {"markets": list(markets.keys()), "count_by_market": markets}

        # Rankings: average score and top refs
        rankings = _get_workspace_rankings(workspace_id)
        if rankings:
            scores = [_safe_float(r.get("opportunity_score")) for r in rankings]
            out["average_opportunity_score"] = round(sum(scores) / len(scores), 2) if scores else 0.0
            sorted_rankings = sorted(rankings, key=lambda r: _safe_float(r.get("opportunity_score")), reverse=True)
            out["top_opportunity_refs"] = [r.get("opportunity_ref") for r in sorted_rankings[:top_refs_limit] if r.get("opportunity_ref")]
            # Trend overview from ranking trend_score
            trend_vals = [_safe_float(r.get("trend_signal")) for r in rankings if r.get("trend_signal") is not None]
            if trend_vals:
                out["trend_overview"] = {"avg_trend_signal": round(sum(trend_vals) / len(trend_vals), 4), "count_with_trend": len(trend_vals)}
        else:
            # Fallback average from memory latest_opportunity_score
            mem_scores = [_safe_float(m.get("latest_opportunity_score")) for m in mem_rows if m.get("latest_opportunity_score") is not None]
            if mem_scores:
                out["average_opportunity_score"] = round(sum(mem_scores) / len(mem_scores), 2)
            out["top_opportunity_refs"] = [m.get("opportunity_ref") for m in mem_rows[:top_refs_limit] if m.get("opportunity_ref")]

        # Alert overview
        try:
            from amazon_research.db import list_opportunity_alerts
            alerts = list_opportunity_alerts(limit=500, workspace_id=workspace_id) or []
            by_type: Dict[str, int] = {}
            for a in alerts:
                t = (a.get("alert_type") or "unknown").strip() or "unknown"
                by_type[t] = by_type.get(t, 0) + 1
            out["alert_overview"] = {"total_alerts": len(alerts), "by_type": by_type}
        except Exception as e:
            logger.warning("workspace_intelligence summary: alert overview failed workspace_id=%s: %s", workspace_id, e)
            out["alert_overview"] = {"total_alerts": 0, "by_type": {}}

        out["summary_timestamp"] = _now_utc().isoformat()
        logger.info("workspace_intelligence summary build success workspace_id=%s", workspace_id)
        try:
            from amazon_research.workspace_intelligence.metrics import record_summary_build_duration
            record_summary_build_duration(time.time() - _build_start)
        except Exception:
            pass
        return out
    except Exception as e:
        logger.warning("workspace_intelligence summary build failure workspace_id=%s: %s", workspace_id, e)
        out["summary_timestamp"] = _now_utc().isoformat()
        return out


def refresh_workspace_intelligence_summary(
    workspace_id: Optional[int],
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Refresh (recompute) workspace intelligence summary, persist snapshot, warm cache, and return summary.
    No crash if persist or cache fails; returns computed summary in any case. Step 193 scheduler uses this.
    """
    summary = get_workspace_intelligence_summary(workspace_id, **kwargs)
    if workspace_id is not None:
        try:
            from amazon_research.db.workspace_intelligence_snapshots import save_workspace_intelligence_snapshot
            save_workspace_intelligence_snapshot(workspace_id, summary)
        except Exception as e:
            logger.warning(
                "workspace_intelligence refresh persist failed workspace_id=%s: %s",
                workspace_id,
                e,
            )
        try:
            from amazon_research.workspace_intelligence.cache import set_cached_summary
            set_cached_summary(workspace_id, summary)
        except Exception as e:
            logger.warning(
                "workspace_intelligence refresh cache warm failed workspace_id=%s: %s",
                workspace_id,
                e,
            )
    return summary
