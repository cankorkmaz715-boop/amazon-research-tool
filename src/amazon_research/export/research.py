"""
Research data export – workspace-scoped CSV and JSON. Reuses API-style data shapes.
Step 45: simple, clean, internal-first. Safe file generation.
"""
import csv
import json
from decimal import Decimal
from datetime import datetime
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger
from amazon_research.db import get_connection

logger = get_logger("export")


def _serialize(value: Any) -> Any:
    """Make value JSON/CSV safe."""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def get_research_data_for_workspace(workspace_id: int) -> List[Dict[str, Any]]:
    """
    Fetch key research data for the workspace: asins with product_metrics and scoring_results.
    Returns list of flat dicts (one per ASIN) with serialized values. workspace_id required (Step 52).
    """
    if workspace_id is None:
        raise ValueError("workspace_id required")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            a.id AS asin_id,
            a.asin,
            a.title,
            a.brand,
            a.category,
            a.product_url,
            a.main_image_url,
            a.created_at AS asin_created_at,
            a.updated_at AS asin_updated_at,
            pm.price,
            pm.currency,
            pm.bsr,
            pm.rating,
            pm.review_count,
            pm.seller_count,
            pm.updated_at AS metrics_updated_at,
            sr.competition_score,
            sr.demand_score,
            sr.opportunity_score,
            sr.scored_at
        FROM asins a
        LEFT JOIN product_metrics pm ON pm.asin_id = a.id
        LEFT JOIN scoring_results sr ON sr.asin_id = a.id
        WHERE a.workspace_id = %s
        ORDER BY a.id
        """,
        (workspace_id,),
    )
    rows = cur.fetchall()
    cur.close()
    keys = [
        "asin_id", "asin", "title", "brand", "category", "product_url", "main_image_url",
        "asin_created_at", "asin_updated_at",
        "price", "currency", "bsr", "rating", "review_count", "seller_count", "metrics_updated_at",
        "competition_score", "demand_score", "opportunity_score", "scored_at",
    ]
    out = []
    for row in rows:
        out.append(dict(zip(keys, [_serialize(v) for v in row])))
    return out


_CSV_FIELDNAMES = [
    "asin_id", "asin", "title", "brand", "category", "product_url", "main_image_url",
    "asin_created_at", "asin_updated_at",
    "price", "currency", "bsr", "rating", "review_count", "seller_count", "metrics_updated_at",
    "competition_score", "demand_score", "opportunity_score", "scored_at",
]


def export_research_csv(workspace_id: int, filepath: str) -> int:
    """
    Export workspace research data to CSV. Returns number of rows written.
    workspace_id required (Step 52). Quota enforced (Step 55).
    """
    if workspace_id is None:
        raise ValueError("workspace_id required")
    from amazon_research.db import check_quota_and_raise
    from amazon_research.rate_limit import check_and_raise, record_rate_limit, get_effective_rate_limit
    check_quota_and_raise(workspace_id, "export_csv")
    check_and_raise(workspace_id, "export", get_effective_rate_limit(workspace_id, "export"), 60.0)
    data = get_research_data_for_workspace(workspace_id)
    fieldnames = list(data[0].keys()) if data else _CSV_FIELDNAMES
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for row in data:
            w.writerow(row)
    if data:
        logger.info("export_research_csv written", extra={"workspace_id": workspace_id, "rows": len(data), "path": filepath})
    from amazon_research.db import record_usage, record_audit, record_billable_event
    from amazon_research.rate_limit import record_rate_limit
    record_usage(workspace_id, "export_csv", {"rows": len(data)})
    record_audit(workspace_id, "export_csv", {"rows": len(data)})
    record_billable_event(workspace_id, "export_csv", {"rows": len(data)})
    record_rate_limit(workspace_id, "export")
    return len(data)


def export_research_json(workspace_id: int, filepath: str) -> int:
    """
    Export workspace research data to JSON. Returns number of items written.
    workspace_id required (Step 52). Quota enforced (Step 55).
    """
    if workspace_id is None:
        raise ValueError("workspace_id required")
    from amazon_research.db import check_quota_and_raise
    from amazon_research.rate_limit import check_and_raise, record_rate_limit, get_effective_rate_limit
    check_quota_and_raise(workspace_id, "export_json")
    check_and_raise(workspace_id, "export", get_effective_rate_limit(workspace_id, "export"), 60.0)
    data = get_research_data_for_workspace(workspace_id)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    logger.info("export_research_json written", extra={"workspace_id": workspace_id, "items": len(data), "path": filepath})
    from amazon_research.db import record_usage, record_audit, record_billable_event
    from amazon_research.rate_limit import record_rate_limit
    record_usage(workspace_id, "export_json", {"rows": len(data)})
    record_audit(workspace_id, "export_json", {"rows": len(data)})
    record_billable_event(workspace_id, "export_json", {"rows": len(data)})
    record_rate_limit(workspace_id, "export")
    return len(data)
