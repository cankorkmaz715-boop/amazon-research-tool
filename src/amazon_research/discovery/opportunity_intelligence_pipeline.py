"""
Step 190: Opportunity intelligence pipeline – connect discovery, ingestion, signals, ranking, and alerts.
Flow: crawler → ingestion → signals → ranking → alerts.
Produces pipeline execution logs; validates data flow; scheduler-compatible.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("discovery.opportunity_intelligence_pipeline")

PIPELINE_STAGE_INGESTION = "ingestion"
PIPELINE_STAGE_SIGNALS = "signals"
PIPELINE_STAGE_RANKING = "ranking"
PIPELINE_STAGE_ALERTS = "alerts"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_pipeline(
    limit_discovery: int = 50,
    limit_opportunities: int = 50,
    limit_rankings: int = 50,
    score_threshold: float = 70.0,
    workspace_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Run the full opportunity intelligence pipeline in order:
    ingestion (discovery_results → opportunity_memory) → signals (opportunity_memory → signal_results)
    → ranking (signal_results + opportunity_memory → opportunity_rankings) → alerts (opportunity_rankings → opportunity_alerts).
    Returns execution log with discovery_count, signal_computation, ranking_updates, alerts_generated.
    """
    started_at = _now_iso()
    log: Dict[str, Any] = {
        "started_at": started_at,
        "discovery_count": 0,
        "signal_computation": 0,
        "ranking_updates": 0,
        "alerts_generated": 0,
        "stages": [],
        "data_flow_ok": True,
    }

    # 1) Ingestion: discovery_results → opportunity_memory
    try:
        from amazon_research.discovery.live_opportunity_ingestion import ingest_latest_discovery_results
        ing = ingest_latest_discovery_results(limit=limit_discovery, workspace_id=workspace_id)
        discovery_count = ing.get("results_processed", 0) or ing.get("ingested_count", 0)
        log["discovery_count"] = discovery_count
        log["stages"].append({
            "stage": PIPELINE_STAGE_INGESTION,
            "results_processed": ing.get("results_processed", 0),
            "ingested_count": ing.get("ingested_count", 0),
            "ok": True,
        })
    except Exception as e:
        logger.debug("pipeline ingestion: %s", e)
        log["stages"].append({"stage": PIPELINE_STAGE_INGESTION, "ok": False, "error": str(e)})
        log["data_flow_ok"] = False

    # 2) Signals: opportunity_memory → signal_results
    try:
        from amazon_research.discovery.opportunity_signal_enrichment import enrich_opportunities_from_memory
        sig = enrich_opportunities_from_memory(limit=limit_opportunities, workspace_id=workspace_id)
        signal_count = sig.get("stored", 0)
        log["signal_computation"] = signal_count
        log["stages"].append({
            "stage": PIPELINE_STAGE_SIGNALS,
            "processed": sig.get("processed", 0),
            "stored": signal_count,
            "ok": True,
        })
    except Exception as e:
        logger.debug("pipeline signals: %s", e)
        log["stages"].append({"stage": PIPELINE_STAGE_SIGNALS, "ok": False, "error": str(e)})
        log["data_flow_ok"] = False

    # 3) Ranking: signal_results + opportunity_memory → opportunity_rankings
    try:
        from amazon_research.discovery.opportunity_ranking_engine import run_ranking
        rank = run_ranking(
            opportunity_refs=None,
            limit=limit_opportunities,
            use_blending=True,
            persist=True,
        )
        ranking_count = rank.get("stored_count", 0)
        log["ranking_updates"] = ranking_count
        log["stages"].append({
            "stage": PIPELINE_STAGE_RANKING,
            "rankings_count": len(rank.get("rankings") or []),
            "stored_count": ranking_count,
            "ok": True,
        })
    except Exception as e:
        logger.debug("pipeline ranking: %s", e)
        log["stages"].append({"stage": PIPELINE_STAGE_RANKING, "ok": False, "error": str(e)})
        log["data_flow_ok"] = False

    # 4) Alerts: opportunity_rankings → opportunity_alerts
    try:
        from amazon_research.discovery.opportunity_alert_engine import run_and_persist_alerts
        al = run_and_persist_alerts(
            score_threshold=score_threshold,
            limit_rankings=limit_rankings,
            workspace_id=workspace_id,
        )
        alert_count = al.get("alert_count", 0) or al.get("saved_count", 0)
        log["alerts_generated"] = alert_count
        log["stages"].append({
            "stage": PIPELINE_STAGE_ALERTS,
            "alert_count": alert_count,
            "saved_count": al.get("saved_count", 0),
            "ok": True,
        })
    except Exception as e:
        logger.debug("pipeline alerts: %s", e)
        log["stages"].append({"stage": PIPELINE_STAGE_ALERTS, "ok": False, "error": str(e)})
        log["data_flow_ok"] = False

    log["finished_at"] = _now_iso()
    logger.info(
        "opportunity_intelligence_pipeline run",
        extra={
            "discovery_count": log["discovery_count"],
            "signal_computation": log["signal_computation"],
            "ranking_updates": log["ranking_updates"],
            "alerts_generated": log["alerts_generated"],
        },
    )
    return log


def validate_data_flow(
    workspace_id: Optional[int] = None,
    sample_limit: int = 5,
) -> Dict[str, Any]:
    """
    Validate that data flows consistently: opportunity_memory refs appear in signal_results and opportunity_rankings.
    Returns validation result with consistency flags and sample refs.
    """
    out: Dict[str, Any] = {
        "memory_has_refs": False,
        "signals_cover_refs": True,
        "rankings_cover_refs": True,
        "sample_refs": [],
        "ok": False,
    }
    try:
        from amazon_research.db import list_opportunity_memory
        from amazon_research.db.signal_results import get_signal_result_latest
        from amazon_research.db.opportunity_rankings import get_latest_ranking
        mem_list = list_opportunity_memory(limit=sample_limit, workspace_id=workspace_id)
        refs = [m.get("opportunity_ref") for m in (mem_list or []) if m.get("opportunity_ref")]
        out["memory_has_refs"] = len(refs) > 0
        out["sample_refs"] = refs[:5]
        for ref in refs[:3]:
            sig = get_signal_result_latest(ref)
            if ref and not sig:
                out["signals_cover_refs"] = False
            rank = get_latest_ranking(ref)
            if ref and not rank:
                out["rankings_cover_refs"] = False
        # OK if no refs (nothing to validate) or refs exist and both signals/rankings cover them
        out["ok"] = (len(refs) == 0) or (out["memory_has_refs"] and out["signals_cover_refs"] and out["rankings_cover_refs"])
    except Exception as e:
        out["error"] = str(e)
    return out


def get_pipeline_run_for_scheduler(
    workspace_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Single entry point for scheduler: run pipeline with default limits and return execution log.
    """
    return run_pipeline(
        limit_discovery=50,
        limit_opportunities=50,
        limit_rankings=50,
        score_threshold=70.0,
        workspace_id=workspace_id,
    )
