"""
Step 102: Trend data persistence – save and load computed trend signals.
Reuses trend engine output shape; append-friendly for trend evolution tracking.
Compatible with niche scoring, opportunity ranking, board, dashboard.
"""
import json
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("db.trend_persistence")

TARGET_TYPE_ASIN = "asin"
TARGET_TYPE_CLUSTER = "cluster"


def _get_connection():
    from amazon_research.db.connection import get_connection
    return get_connection()


def persist_trend_result(
    target_type: str,
    target_ref: str,
    signals: Dict[str, Any],
    *,
    marketplace: Optional[str] = None,
    asin_id: Optional[int] = None,
    explanation: Optional[str] = None,
) -> Optional[int]:
    """
    Append one trend result. target_type: 'asin' or 'cluster'; target_ref: asin_id string or cluster_id.
    signals: dict matching trend engine shape (e.g. price, review_count, rating, rank with trend/value_first/value_last/points/explanation).
    Returns inserted id or None on error.
    """
    if not signals:
        signals = {}
    if not isinstance(signals, dict):
        return None
    try:
        conn = _get_connection()
        cur = conn.cursor()
        signals_json = json.dumps(signals) if signals else "{}"
        cur.execute(
            """INSERT INTO trend_results (target_type, target_ref, asin_id, marketplace, signals, explanation)
               VALUES (%s, %s, %s, %s, %s::jsonb, %s) RETURNING id""",
            (
                (target_type or TARGET_TYPE_ASIN).strip() or TARGET_TYPE_ASIN,
                (target_ref or "").strip() or "0",
                asin_id,
                (marketplace or "").strip() or None,
                signals_json,
                (explanation or "").strip() or None,
            ),
        )
        row = cur.fetchone()
        rid = row[0] if row else None
        cur.close()
        conn.commit()
        return rid
    except Exception as e:
        logger.debug("persist_trend_result failed: %s", e)
        return None


def get_trend_result_latest(
    target_type: str,
    target_ref: str,
) -> Optional[Dict[str, Any]]:
    """
    Return the most recent trend result for the target, or None.
    Result: id, target_type, target_ref, asin_id, recorded_at, marketplace, signals, explanation.
    """
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            """SELECT id, target_type, target_ref, asin_id, recorded_at, marketplace, signals, explanation
               FROM trend_results
               WHERE target_type = %s AND target_ref = %s
               ORDER BY recorded_at DESC
               LIMIT 1""",
            ((target_type or TARGET_TYPE_ASIN).strip(), (target_ref or "").strip()),
        )
        row = cur.fetchone()
        cur.close()
        if not row:
            return None
        signals = row[6]
        if isinstance(signals, str):
            try:
                signals = json.loads(signals)
            except Exception:
                signals = {}
        return {
            "id": row[0],
            "target_type": row[1],
            "target_ref": row[2],
            "asin_id": row[3],
            "recorded_at": row[4],
            "marketplace": row[5],
            "signals": signals or {},
            "explanation": row[7],
        }
    except Exception as e:
        logger.debug("get_trend_result_latest failed: %s", e)
        return None


def get_trend_result_history(
    target_type: str,
    target_ref: str,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """
    Return trend result history for the target, newest first.
    Each item: id, target_type, target_ref, asin_id, recorded_at, marketplace, signals, explanation.
    """
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            """SELECT id, target_type, target_ref, asin_id, recorded_at, marketplace, signals, explanation
               FROM trend_results
               WHERE target_type = %s AND target_ref = %s
               ORDER BY recorded_at DESC
               LIMIT %s""",
            ((target_type or TARGET_TYPE_ASIN).strip(), (target_ref or "").strip(), max(1, limit)),
        )
        rows = cur.fetchall()
        cur.close()
        out = []
        for row in rows:
            signals = row[6]
            if isinstance(signals, str):
                try:
                    signals = json.loads(signals)
                except Exception:
                    signals = {}
            out.append({
                "id": row[0],
                "target_type": row[1],
                "target_ref": row[2],
                "asin_id": row[3],
                "recorded_at": row[4],
                "marketplace": row[5],
                "signals": signals or {},
                "explanation": row[7],
            })
        return out
    except Exception as e:
        logger.debug("get_trend_result_history failed: %s", e)
        return []
