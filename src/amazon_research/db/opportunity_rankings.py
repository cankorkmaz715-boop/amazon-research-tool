"""
Step 188: Opportunity rankings persistence – store ranked opportunity_score with signal components and history.
"""
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("db.opportunity_rankings")


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


def insert_ranking(
    opportunity_ref: str,
    opportunity_score: float,
    rank: Optional[int] = None,
    demand_score: Optional[float] = None,
    competition_score: Optional[float] = None,
    trend_score: Optional[float] = None,
    price_stability: Optional[float] = None,
    listing_density: Optional[float] = None,
    previous_score: Optional[float] = None,
    score_history: Optional[List[Dict[str, Any]]] = None,
    recorded_at: Optional[datetime] = None,
) -> Optional[int]:
    """Append one row to opportunity_rankings. Returns id or None."""
    ref = (opportunity_ref or "").strip()
    if not ref:
        return None
    score = _dec(opportunity_score)
    if score is None:
        return None
    ts = recorded_at or datetime.now(timezone.utc)
    hist = score_history if isinstance(score_history, list) else []
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO opportunity_rankings
               (opportunity_ref, opportunity_score, rank, demand_score, competition_score, trend_score, price_stability, listing_density, previous_score, score_history, recorded_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s) RETURNING id""",
            (
                ref,
                score,
                rank,
                _dec(demand_score),
                _dec(competition_score),
                _dec(trend_score),
                _dec(price_stability),
                _dec(listing_density),
                _dec(previous_score),
                json.dumps(hist),
                ts,
            ),
        )
        row = cur.fetchone()
        rid = row[0] if row else None
        cur.close()
        conn.commit()
        return rid
    except Exception as e:
        logger.debug("insert_ranking failed: %s", e)
        return None


def get_latest_ranking(opportunity_ref: str) -> Optional[Dict[str, Any]]:
    """Return the most recent opportunity_rankings row for the ref, or None."""
    ref = (opportunity_ref or "").strip()
    if not ref:
        return None
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            """SELECT id, opportunity_ref, opportunity_score, rank, demand_score, competition_score, trend_score, price_stability, listing_density, previous_score, score_history, recorded_at
               FROM opportunity_rankings WHERE opportunity_ref = %s ORDER BY recorded_at DESC LIMIT 1""",
            (ref,),
        )
        row = cur.fetchone()
        cur.close()
        if not row:
            return None
        sh = row[10]
        if isinstance(sh, str) and sh:
            try:
                sh = json.loads(sh)
            except Exception:
                sh = []
        return {
            "id": row[0],
            "opportunity_ref": row[1],
            "opportunity_score": float(row[2]) if row[2] is not None else None,
            "rank": row[3],
            "demand_score": float(row[4]) if row[4] is not None else None,
            "competition_score": float(row[5]) if row[5] is not None else None,
            "trend_score": float(row[6]) if row[6] is not None else None,
            "price_stability": float(row[7]) if row[7] is not None else None,
            "listing_density": float(row[8]) if row[8] is not None else None,
            "previous_score": float(row[9]) if row[9] is not None else None,
            "score_history": sh or [],
            "recorded_at": row[11],
        }
    except Exception as e:
        logger.debug("get_latest_ranking failed: %s", e)
        return None


def get_latest_rankings(limit: int = 100) -> List[Dict[str, Any]]:
    """Return latest ranking row per opportunity_ref (most recent recorded_at), ordered by opportunity_score DESC."""
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            """SELECT DISTINCT ON (opportunity_ref) id, opportunity_ref, opportunity_score, rank, demand_score, competition_score, trend_score, price_stability, listing_density, previous_score, score_history, recorded_at
               FROM opportunity_rankings ORDER BY opportunity_ref, recorded_at DESC""",
        )
        rows = cur.fetchall()
        cur.close()
        out = []
        for row in rows[: max(1, limit)]:
            sh = row[10]
            if isinstance(sh, str) and sh:
                try:
                    sh = json.loads(sh)
                except Exception:
                    sh = []
            out.append({
                "id": row[0],
                "opportunity_ref": row[1],
                "opportunity_score": float(row[2]) if row[2] is not None else None,
                "rank": row[3],
                "demand_score": float(row[4]) if row[4] is not None else None,
                "competition_score": float(row[5]) if row[5] is not None else None,
                "trend_score": float(row[6]) if row[6] is not None else None,
                "price_stability": float(row[7]) if row[7] is not None else None,
                "listing_density": float(row[8]) if row[8] is not None else None,
                "previous_score": float(row[9]) if row[9] is not None else None,
                "score_history": sh or [],
                "recorded_at": row[11],
            })
        out.sort(key=lambda x: (x.get("opportunity_score") or 0), reverse=True)
        return out
    except Exception as e:
        logger.debug("get_latest_rankings failed: %s", e)
        return []
