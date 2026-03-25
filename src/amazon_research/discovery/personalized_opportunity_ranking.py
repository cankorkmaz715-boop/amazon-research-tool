"""
Step 153: Personalized opportunity ranking – adjust opportunity ranking using workspace personalization signals.
Preserves base scores for auditability. Rule-based, explainable. Integrates with personalization signals,
opportunity recommendation engine, opportunity board, research dashboard.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("discovery.personalized_opportunity_ranking")


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _float(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def get_personalized_ranking(
    opportunity_ref: str,
    workspace_id: int,
    *,
    base_score: Optional[float] = None,
    memory_record: Optional[Dict[str, Any]] = None,
    personalization_signals: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Produce a personalized ranking entry for one opportunity. Preserves base score; applies
    workspace personalization adjustments. Returns: workspace_id, target_opportunity_id,
    base_opportunity_score, personalized_score, personalization_explanation, timestamp.
    """
    ref = (opportunity_ref or "").strip()
    out: Dict[str, Any] = {
        "workspace_id": workspace_id,
        "target_opportunity_id": ref or None,
        "base_opportunity_score": None,
        "personalized_score": None,
        "personalization_explanation": "",
        "timestamp": _ts(),
    }
    if not ref:
        out["personalization_explanation"] = "Missing opportunity reference."
        return out

    # Base score from memory or argument
    mem = memory_record
    if mem is None:
        try:
            from amazon_research.db import get_opportunity_memory
            mem = get_opportunity_memory(ref)
        except Exception as e:
            logger.debug("get_personalized_ranking get_opportunity_memory: %s", e)
    base = base_score
    if base is None and mem:
        base = _float(mem.get("latest_opportunity_score"))
    if base is None:
        base = 0.0
    base = max(0.0, min(100.0, float(base)))
    out["base_opportunity_score"] = round(base, 1)

    # Personalization signals for workspace
    signals = personalization_signals
    if signals is None:
        try:
            from amazon_research.monitoring import get_workspace_personalization_signals
            signals = get_workspace_personalization_signals(workspace_id)
        except Exception as e:
            logger.debug("get_personalized_ranking get_workspace_personalization_signals: %s", e)
            signals = {}
    signal_set = (signals.get("personalization_signal_set") or {}) if isinstance(signals, dict) else {}
    strengths = (signals.get("signal_strengths") or {}) if isinstance(signals, dict) else {}

    # Opportunity context (label, ref for niche match)
    ctx = (mem or {}).get("context") or {}
    label = (ctx.get("label") or ref or "").strip().lower()
    ref_lower = ref.lower()

    # Confidence for tolerance adjustment
    conf_label = ""
    try:
        from amazon_research.discovery.opportunity_confidence import get_opportunity_confidence
        conf = get_opportunity_confidence(ref, workspace_id=workspace_id, memory_record=mem)
        conf_label = (conf.get("confidence_label") or "").strip().lower()
    except Exception:
        pass

    # Apply adjustments (rule-based)
    delta = 0.0
    explanation_parts: List[str] = []

    # Preferred niche types match
    preferred_niches = [str(x).strip().lower() for x in (signal_set.get("preferred_niche_types") or []) if x]
    if preferred_niches and (label or ref_lower):
        for term in preferred_niches:
            if term and (term in label or term in ref_lower or term in ref):
                strength = (strengths.get("preferred_niche_types") or "low").lower()
                if strength == "high":
                    delta += 12.0
                elif strength == "medium":
                    delta += 6.0
                else:
                    delta += 3.0
                explanation_parts.append(f"niche match '{term}' (+{delta:.0f})")
                break

    # Confidence tolerance
    tolerance = (signal_set.get("confidence_tolerance") or "medium").strip().lower()
    if conf_label == "low":
        if tolerance == "low":
            delta -= 8.0
            explanation_parts.append("low confidence, low tolerance (-8)")
        elif tolerance == "high":
            delta += 2.0
            explanation_parts.append("low confidence, high tolerance (+2)")

    # Preferred opportunity pattern: small boost for high-opportunity pattern when base is already high
    pattern = (signal_set.get("preferred_opportunity_pattern") or "mixed").strip().lower()
    if pattern == "high_opportunity" and base >= 55:
        delta += 3.0
        explanation_parts.append("high-opportunity pattern, strong base (+3)")

    # Clamp personalized score
    personalized = max(0.0, min(100.0, base + delta))
    out["personalized_score"] = round(personalized, 1)
    out["personalization_explanation"] = "; ".join(explanation_parts) if explanation_parts else "No personalization adjustments applied."

    return out


def list_personalized_rankings(
    workspace_id: int,
    *,
    limit: int = 50,
    personalization_signals: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    List opportunities for the workspace with personalized rankings. Uses opportunity memory
    then applies get_personalized_ranking per opportunity. Returns list sorted by personalized_score desc.
    """
    try:
        from amazon_research.db import list_opportunity_memory
        rows = list_opportunity_memory(limit=limit, workspace_id=workspace_id)
    except Exception as e:
        logger.debug("list_personalized_rankings list_opportunity_memory: %s", e)
        return []

    signals = personalization_signals
    if signals is None:
        try:
            from amazon_research.monitoring import get_workspace_personalization_signals
            signals = get_workspace_personalization_signals(workspace_id)
        except Exception:
            signals = {}

    results = []
    for mem in rows:
        ref = mem.get("opportunity_ref")
        if not ref:
            continue
        entry = get_personalized_ranking(
            ref,
            workspace_id,
            memory_record=mem,
            personalization_signals=signals,
        )
        results.append(entry)

    results.sort(key=lambda x: (x.get("personalized_score") or 0.0), reverse=True)
    return results
