"""
Step 187: Signal results persistence – store demand, competition, trend, price_stability, listing_density per opportunity.
"""
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("db.signal_results")


def _get_connection():
    from amazon_research.db.connection import get_connection
    return get_connection()


def _dec(v: Optional[float]) -> Optional[float]:
    if v is None:
        return None
    try:
        return round(float(v), 4)
    except (TypeError, ValueError):
        return None


def insert_signal_result(
    opportunity_ref: str,
    demand_estimate: Optional[float] = None,
    competition_level: Optional[float] = None,
    trend_signal: Optional[float] = None,
    price_stability: Optional[float] = None,
    listing_density: Optional[float] = None,
    *,
    marketplace: Optional[str] = None,
    signals: Optional[Dict[str, Any]] = None,
    recorded_at: Optional[datetime] = None,
) -> Optional[int]:
    """
    Append one row to signal_results. Returns inserted id or None.
    """
    ref = (opportunity_ref or "").strip()
    if not ref:
        return None
    ts = recorded_at or datetime.now(timezone.utc)
    try:
        conn = _get_connection()
        cur = conn.cursor()
        sig_json = json.dumps(signals if isinstance(signals, dict) else {})
        cur.execute(
            """INSERT INTO signal_results
               (opportunity_ref, marketplace, demand_estimate, competition_level, trend_signal, price_stability, listing_density, signals, recorded_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s) RETURNING id""",
            (
                ref,
                (marketplace or "").strip() or None,
                _dec(demand_estimate),
                _dec(competition_level),
                _dec(trend_signal),
                _dec(price_stability),
                _dec(listing_density),
                sig_json,
                ts,
            ),
        )
        row = cur.fetchone()
        rid = row[0] if row else None
        cur.close()
        conn.commit()
        return rid
    except Exception as e:
        logger.debug("insert_signal_result failed: %s", e)
        return None


def get_signal_result_latest(opportunity_ref: str) -> Optional[Dict[str, Any]]:
    """Return the most recent signal_results row for the opportunity_ref, or None."""
    ref = (opportunity_ref or "").strip()
    if not ref:
        return None
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            """SELECT id, opportunity_ref, marketplace, demand_estimate, competition_level, trend_signal, price_stability, listing_density, signals, recorded_at
               FROM signal_results WHERE opportunity_ref = %s ORDER BY recorded_at DESC LIMIT 1""",
            (ref,),
        )
        row = cur.fetchone()
        cur.close()
        if not row:
            return None
        sig = row[8]
        if isinstance(sig, str) and sig:
            try:
                sig = json.loads(sig)
            except Exception:
                sig = {}
        return {
            "id": row[0],
            "opportunity_ref": row[1],
            "marketplace": row[2],
            "demand_estimate": float(row[3]) if row[3] is not None else None,
            "competition_level": float(row[4]) if row[4] is not None else None,
            "trend_signal": float(row[5]) if row[5] is not None else None,
            "price_stability": float(row[6]) if row[6] is not None else None,
            "listing_density": float(row[7]) if row[7] is not None else None,
            "signals": sig or {},
            "recorded_at": row[9],
        }
    except Exception as e:
        logger.debug("get_signal_result_latest failed: %s", e)
        return None
