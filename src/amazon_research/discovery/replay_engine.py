"""
Step 126: Research replay engine – reconstruct past research runs or discovery cycles.
Read-focused; uses discovery results, opportunity memory, alerts, worker jobs, cluster cache.
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("discovery.replay_engine")

STEP_TRIGGERED_SCANS = "triggered_scans"
STEP_DISCOVERY_OUTPUTS = "discovery_outputs"
STEP_NICHE_CLUSTER = "niche_cluster"
STEP_RANKING = "ranking"
STEP_ALERTS = "alerts"


def _ts(x: Any) -> Optional[str]:
    if x is None:
        return None
    if hasattr(x, "isoformat"):
        return x.isoformat()
    return str(x)


def get_replay(
    workspace_id: Optional[int] = None,
    limit_jobs: int = 30,
    limit_discovery: int = 30,
    limit_alerts: int = 30,
) -> Dict[str, Any]:
    """
    Reconstruct a replay from recent historical data. Returns:
    replay_id, source_run_id (optional), steps (ordered sequence of step_type, summary, output_summary, timestamp),
    timestamps where relevant. Read-only; no writes.
    """
    replay_id = f"replay-{uuid.uuid4().hex[:12]}"
    steps: List[Dict[str, Any]] = []
    source_run_id = None

    # 1) Triggered scans (from worker_jobs)
    try:
        from amazon_research.db import list_jobs
        jobs = list_jobs(workspace_id=workspace_id, limit=limit_jobs)
        scan_jobs = [j for j in jobs if (j.get("job_type") or "") in ("category_scan", "keyword_scan", "niche_discovery", "opportunity_alert")]
        if scan_jobs:
            created = [j.get("created_at") for j in scan_jobs if j.get("created_at")]
            ts_min = min(created) if created else None
            ts_max = max(created) if created else None
            steps.append({
                "step_id": len(steps) + 1,
                "step_type": STEP_TRIGGERED_SCANS,
                "summary": {"count": len(scan_jobs), "by_type": _count_by(scan_jobs, "job_type")},
                "output_summary": [{"job_id": j.get("id"), "job_type": j.get("job_type"), "status": j.get("status"), "created_at": _ts(j.get("created_at"))} for j in scan_jobs[:10]],
                "timestamp": _ts(ts_max),
                "timestamp_range": [_ts(ts_min), _ts(ts_max)] if ts_min and ts_max else None,
            })
            if source_run_id is None and scan_jobs:
                source_run_id = scan_jobs[0].get("id")
    except Exception as e:
        logger.debug("replay triggered_scans failed: %s", e)

    # 2) Discovery outputs
    try:
        from amazon_research.db import get_discovery_results
        results = get_discovery_results(limit=limit_discovery)
        if results:
            recs = [r.get("recorded_at") for r in results if r.get("recorded_at")]
            ts_min = min(recs) if recs else None
            ts_max = max(recs) if recs else None
            steps.append({
                "step_id": len(steps) + 1,
                "step_type": STEP_DISCOVERY_OUTPUTS,
                "summary": {"count": len(results), "total_asins": sum(len(r.get("asins") or []) for r in results)},
                "output_summary": [{"id": r.get("id"), "source_type": r.get("source_type"), "source_id": (r.get("source_id") or "")[:80], "recorded_at": _ts(r.get("recorded_at"))} for r in results[:10]],
                "timestamp": _ts(ts_max),
                "timestamp_range": [_ts(ts_min), _ts(ts_max)] if ts_min and ts_max else None,
            })
    except Exception as e:
        logger.debug("replay discovery_outputs failed: %s", e)

    # 3) Niche/cluster generation (latest cache)
    try:
        from amazon_research.db import get_cluster_cache
        entry = get_cluster_cache(scope_key="default")
        if entry:
            clusters = entry.get("clusters") or []
            rec_at = entry.get("recorded_at")
            steps.append({
                "step_id": len(steps) + 1,
                "step_type": STEP_NICHE_CLUSTER,
                "summary": {"cluster_count": len(clusters), "recorded_at": _ts(rec_at)},
                "output_summary": [{"cluster_id": c.get("cluster_id"), "label": (c.get("label") or "")[:60], "member_count": len(c.get("member_asins") or [])} for c in clusters[:10]],
                "timestamp": _ts(rec_at),
            })
    except Exception as e:
        logger.debug("replay niche_cluster failed: %s", e)

    # 4) Ranking / opportunity (from opportunity memory)
    try:
        from amazon_research.db import list_opportunity_memory
        mem_list = list_opportunity_memory(limit=limit_discovery, workspace_id=workspace_id)
        if mem_list:
            last_seen = [m.get("last_seen_at") for m in mem_list if m.get("last_seen_at")]
            ts_max = max(last_seen) if last_seen else None
            steps.append({
                "step_id": len(steps) + 1,
                "step_type": STEP_RANKING,
                "summary": {"opportunity_count": len(mem_list)},
                "output_summary": [{"opportunity_ref": m.get("opportunity_ref"), "latest_score": m.get("latest_opportunity_score"), "status": m.get("status")} for m in mem_list[:10]],
                "timestamp": _ts(ts_max),
            })
    except Exception as e:
        logger.debug("replay ranking failed: %s", e)

    # 5) Alerts produced
    try:
        from amazon_research.db import list_opportunity_alerts
        alerts = list_opportunity_alerts(limit=limit_alerts, workspace_id=workspace_id)
        if alerts:
            recs = [a.get("recorded_at") for a in alerts if a.get("recorded_at")]
            ts_max = max(recs) if recs else None
            steps.append({
                "step_id": len(steps) + 1,
                "step_type": STEP_ALERTS,
                "summary": {"count": len(alerts), "by_type": _count_by(alerts, "alert_type")},
                "output_summary": [{"id": a.get("id"), "alert_type": a.get("alert_type"), "target_entity": a.get("target_entity"), "recorded_at": _ts(a.get("recorded_at"))} for a in alerts[:10]],
                "timestamp": _ts(ts_max),
            })
    except Exception as e:
        logger.debug("replay alerts failed: %s", e)

    return {
        "replay_id": replay_id,
        "source_run_id": source_run_id,
        "steps": steps,
        "step_count": len(steps),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _count_by(items: List[Dict[str, Any]], key: str) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for x in items:
        k = x.get(key) or ""
        out[k] = out.get(k, 0) + 1
    return out
