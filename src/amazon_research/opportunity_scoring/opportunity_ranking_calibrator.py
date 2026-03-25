"""
Step 235: Rank and calibrate opportunity rows for dashboard/API.
Sort by normalized score desc, assign ranking_position, add supporting_signal_hints.
Deterministic; uses existing ranking data only.
"""
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

from amazon_research.opportunity_scoring.opportunity_score_mapper import (
    score_to_normalized,
    score_to_priority_band,
    build_supporting_signal_hints,
)

logger = get_logger("opportunity_scoring.calibrator")


def calibrate_opportunity_rows(
    rows: List[Dict[str, Any]],
    workspace_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Sort opportunity rows by score (desc), assign ranking_position (1-based),
    add normalized_score, priority_band, supporting_signal_hints.
    Preserves all existing keys; adds/overwrites only calibration fields.
    Returns new list; does not mutate input. Safe when rows empty or signals partial.
    """
    if not rows:
        return []
    out: List[Dict[str, Any]] = []
    for r in rows:
        ref = (r.get("opportunity_ref") or "").strip()
        raw_score = r.get("latest_opportunity_score")
        ranking = r.get("ranking")
        norm = score_to_normalized(raw_score)
        band = score_to_priority_band(raw_score)
        hints = build_supporting_signal_hints(ranking)
        out.append({
            **r,
            "normalized_score": norm,
            "priority_band": band,
            "supporting_signal_hints": hints,
        })
    # Sort: normalized_score desc, then opportunity_ref asc for stability
    out.sort(
        key=lambda x: (
            -(x.get("normalized_score") or 0),
            (x.get("opportunity_ref") or ""),
        ),
    )
    for i, row in enumerate(out, start=1):
        row["ranking_position"] = i
    if workspace_id is not None:
        logger.debug(
            "opportunity_scoring calibrated workspace_id=%s count=%s",
            workspace_id,
            len(out),
            extra={"workspace_id": workspace_id, "count": len(out)},
        )
    return out
