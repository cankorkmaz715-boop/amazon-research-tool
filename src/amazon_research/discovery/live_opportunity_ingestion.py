"""
Step 186: Live opportunity ingestion – store discovered opportunities from crawler into opportunity memory.
Receives discovery outputs from ASIN discovery bot, category discovery, keyword discovery.
Normalizes to unified structure; stores into opportunity_memory with market, asin, source_type,
discovery_timestamp, discovery_context. Prevents duplicate insertion via upsert by (market, asin).
Lightweight, safe for long-running operation. Compatible with multi-market activation, discovery engine,
scheduler production loop, opportunity scoring engine.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("discovery.live_opportunity_ingestion")

# Source types aligned with discovery_storage
SOURCE_TYPE_CATEGORY = "category"
SOURCE_TYPE_KEYWORD = "keyword"
SOURCE_TYPE_GRAPH = "graph"
SOURCE_TYPE_AUTOMATED = "automated"


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _opportunity_ref(market: str, asin: str) -> str:
    """Composite ref for multi-market deduplication: same ASIN in different markets are separate."""
    m = (market or "").strip().upper() or "DE"
    a = (asin or "").strip().upper()
    return f"{m}:{a}" if a else ""


def normalize_discovery_output(
    source_type: str,
    source_id: str,
    marketplace: str,
    asins: List[str],
    recorded_at: Optional[datetime] = None,
    scan_metadata: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Normalize discovery output into a unified opportunity structure.
    Returns list of dicts: market, asin, source_type, discovery_timestamp, discovery_context.
    """
    market = (marketplace or "DE").strip().upper()
    st = (source_type or "").strip().lower() or SOURCE_TYPE_KEYWORD
    sid = (source_id or "").strip()
    ts = recorded_at or _now_utc()
    if hasattr(ts, "isoformat"):
        ts_iso = ts.isoformat()
    else:
        ts_iso = str(ts)
    ctx = {"source_id": sid, "scan_metadata": (scan_metadata or {})}
    out: List[Dict[str, Any]] = []
    seen: set = set()
    for a in asins or []:
        asin = (a or "").strip().upper()
        if not asin or asin in seen:
            continue
        seen.add(asin)
        out.append({
            "market": market,
            "asin": asin,
            "source_type": st,
            "discovery_timestamp": ts_iso,
            "discovery_context": dict(ctx),
        })
    return out


def ingest_one(
    market: str,
    asin: str,
    source_type: str,
    discovery_timestamp: str,
    discovery_context: Optional[Dict[str, Any]] = None,
    workspace_id: Optional[int] = None,
) -> Optional[int]:
    """
    Store one opportunity into opportunity_memory. Uses composite ref market:asin for deduplication.
    Upsert: insert if new, else update last_seen_at and context. Returns row id or None.
    """
    ref = _opportunity_ref(market, asin)
    if not ref:
        return None
    context = {
        "market": (market or "DE").strip(),
        "asin": (asin or "").strip().upper(),
        "source_type": (source_type or "").strip().lower(),
        "discovery_timestamp": discovery_timestamp,
        "discovery_context": dict(discovery_context or {}),
    }
    try:
        from amazon_research.db.opportunity_memory import record_opportunity_seen
        return record_opportunity_seen(ref, context=context, workspace_id=workspace_id)
    except Exception as e:
        logger.debug("ingest_one failed for %s: %s", ref, e)
        return None


def ingest_from_normalized(opportunities: List[Dict[str, Any]], workspace_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Ingest a list of normalized opportunity dicts (market, asin, source_type, discovery_timestamp, discovery_context).
    Returns summary: ingested_count, skipped_count, ids (list of row ids).
    """
    ingested = 0
    skipped = 0
    ids: List[Optional[int]] = []
    for o in opportunities or []:
        market = (o.get("market") or "DE").strip()
        asin = (o.get("asin") or "").strip()
        if not asin:
            skipped += 1
            ids.append(None)
            continue
        rid = ingest_one(
            market=market,
            asin=asin,
            source_type=o.get("source_type") or SOURCE_TYPE_KEYWORD,
            discovery_timestamp=o.get("discovery_timestamp") or _now_utc().isoformat(),
            discovery_context=o.get("discovery_context"),
            workspace_id=workspace_id,
        )
        if rid is not None:
            ingested += 1
            ids.append(rid)
        else:
            skipped += 1
            ids.append(None)
    return {"ingested_count": ingested, "skipped_count": skipped, "ids": ids}


def ingest_from_discovery_result(
    discovery_result: Dict[str, Any],
    workspace_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Ingest one discovery result (from get_discovery_results or save_discovery_result output).
    Expects: source_type, source_id, marketplace, asins, recorded_at, scan_metadata.
    """
    st = discovery_result.get("source_type") or SOURCE_TYPE_KEYWORD
    sid = discovery_result.get("source_id") or ""
    market = (discovery_result.get("marketplace") or "DE").strip().upper()
    asins = discovery_result.get("asins")
    if not isinstance(asins, list):
        asins = []
    recorded_at = discovery_result.get("recorded_at")
    scan_metadata = discovery_result.get("scan_metadata") if isinstance(discovery_result.get("scan_metadata"), dict) else {}
    opportunities = normalize_discovery_output(st, sid, market, asins, recorded_at=recorded_at, scan_metadata=scan_metadata)
    return ingest_from_normalized(opportunities, workspace_id=workspace_id)


def ingest_from_discovery_output(
    source_type: str,
    source_id: str,
    marketplace: str,
    asins: List[str],
    scan_metadata: Optional[Dict[str, Any]] = None,
    workspace_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Ingest raw discovery output (e.g. from worker after category_scan/keyword_scan).
    Normalizes and stores into opportunity_memory. Prevents duplicates via upsert.
    """
    opportunities = normalize_discovery_output(
        source_type, source_id, marketplace, asins,
        recorded_at=_now_utc(), scan_metadata=scan_metadata,
    )
    return ingest_from_normalized(opportunities, workspace_id=workspace_id)


def ingest_latest_discovery_results(
    limit: int = 50,
    workspace_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Read latest discovery results from DB and ingest into opportunity_memory.
    Integration point for scheduler production loop (e.g. after discovery cycle).
    """
    try:
        from amazon_research.db import get_discovery_results
        results = get_discovery_results(limit=limit)
    except Exception as e:
        logger.debug("ingest_latest_discovery_results get_discovery_results: %s", e)
        return {"ingested_count": 0, "skipped_count": 0, "results_processed": 0, "ids": []}
    total_ingested = 0
    total_skipped = 0
    all_ids: List[Optional[int]] = []
    for r in results:
        summary = ingest_from_discovery_result(r, workspace_id=workspace_id)
        total_ingested += summary.get("ingested_count", 0)
        total_skipped += summary.get("skipped_count", 0)
        all_ids.extend(summary.get("ids") or [])
    return {
        "ingested_count": total_ingested,
        "skipped_count": total_skipped,
        "results_processed": len(results),
        "ids": all_ids,
    }
