"""
Step 134: Opportunity recommendation engine – propose which opportunities deserve attention first.
Uses opportunity score, confidence, lifecycle, trend, demand/competition, watchlist intelligence,
alert prioritization. Lightweight, rule-based, explainable. Board, explorer, dashboard compatible.
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from amazon_research.logging_config import get_logger

logger = get_logger("discovery.recommendation_engine")

RECO_HIGH_OPPORTUNITY = "high_opportunity"
RECO_WATCHLIST_ATTENTION = "watchlist_attention"
RECO_LIFECYCLE_RISING = "lifecycle_rising"
RECO_TREND_POSITIVE = "trend_positive"
RECO_DEMAND_VS_COMPETITION = "demand_vs_competition"
RECO_ALERT_PRIORITIZED = "alert_prioritized"
RECO_CONFIDENCE_STABLE = "confidence_stable"


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _entity_key(t: str, r: str) -> Tuple[str, str]:
    return (t or "cluster", r or "")


def get_recommendations(
    workspace_id: Optional[int] = None,
    *,
    limit: int = 30,
    include_watchlist: bool = True,
    include_alerts: bool = True,
) -> List[Dict[str, Any]]:
    """
    Propose which opportunities deserve attention first. Aggregates from opportunity memory,
    watchlist intelligence, and prioritized alerts. Returns list of recommendations sorted by
    priority_score descending. Each item: recommendation_id, target_entity (type, ref),
    recommendation_type, priority_score, explanation, timestamp.
    """
    seen: Set[Tuple[str, str]] = set()
    recos: List[Dict[str, Any]] = []
    now = _ts()

    # 1) From opportunity memory (cluster/niche)
    try:
        from amazon_research.db import list_opportunity_memory
        from amazon_research.discovery import (
            get_opportunity_confidence,
            get_opportunity_lifecycle,
            get_opportunity_explanation,
        )
        mem_list = list_opportunity_memory(limit=limit, workspace_id=workspace_id)
        for mem in mem_list:
            ref = mem.get("opportunity_ref")
            if not ref:
                continue
            key = _entity_key("cluster", ref)
            if key in seen:
                continue
            ctx = mem.get("context") or {}
            opp_score = mem.get("latest_opportunity_score")
            demand = ctx.get("demand_score")
            competition = ctx.get("competition_score")
            priority = 40.0
            rec_type = RECO_HIGH_OPPORTUNITY
            parts: List[str] = []
            if opp_score is not None:
                try:
                    o = float(opp_score)
                    if o >= 65:
                        priority = 55.0 + min(25, (o - 65) * 0.5)
                        parts.append(f"opportunity score {o:.0f}")
                    else:
                        priority = 35.0 + o * 0.2
                except (TypeError, ValueError):
                    pass
            try:
                life = get_opportunity_lifecycle(ref, memory_record=mem)
                lc = life.get("lifecycle_state") or ""
                if lc == "rising":
                    priority += 15
                    rec_type = RECO_LIFECYCLE_RISING
                    parts.append("lifecycle rising")
                elif lc == "stable":
                    priority += 5
                    parts.append("lifecycle stable")
            except Exception:
                pass
            try:
                conf = get_opportunity_confidence(ref, workspace_id=workspace_id, memory_record=mem)
                cs = (conf.get("confidence_score") or 0)
                if isinstance(cs, (int, float)) and cs >= 60:
                    priority += 5
                    parts.append("confidence high")
            except Exception:
                pass
            if demand is not None and competition is not None:
                try:
                    d, c = float(demand), float(competition)
                    if d > c and d - c >= 15:
                        priority += 10
                        if rec_type == RECO_HIGH_OPPORTUNITY:
                            rec_type = RECO_DEMAND_VS_COMPETITION
                        parts.append("demand outweighs competition")
                except (TypeError, ValueError):
                    pass
            expl = get_opportunity_explanation(ref, workspace_id=workspace_id, memory_record=mem)
            trend_sig = (expl.get("main_supporting_signals") or {}).get("trend_signal") or expl.get("main_supporting_signals", {}).get("trend_score")
            if trend_sig:
                priority += 5
                if rec_type == RECO_HIGH_OPPORTUNITY:
                    rec_type = RECO_TREND_POSITIVE
                parts.append("trend signal present")
            priority = max(0.0, min(100.0, priority))
            explanation = "; ".join(parts) if parts else f"Opportunity ref {ref}; score {opp_score}."
            seen.add(key)
            recos.append({
                "recommendation_id": f"rec-{uuid.uuid4().hex[:12]}",
                "target_entity": {"type": "cluster", "ref": ref},
                "recommendation_type": rec_type,
                "priority_score": round(priority, 1),
                "explanation": explanation,
                "timestamp": now,
            })
    except Exception as e:
        logger.debug("get_recommendations opportunity memory failed: %s", e)

    # 2) From watchlist intelligence (add or boost)
    if include_watchlist and workspace_id is not None:
        try:
            from amazon_research.discovery import list_watch_intelligence
            watch_list = list_watch_intelligence(workspace_id, limit=limit)
            for w in watch_list:
                entity = w.get("watched_entity") or {}
                t = (entity.get("type") or "cluster").strip()
                ref = (entity.get("ref") or "").strip()
                if not ref:
                    continue
                key = _entity_key(t, ref)
                imp = w.get("importance_score") or 0
                try:
                    imp = float(imp)
                except (TypeError, ValueError):
                    imp = 50.0
                if key in seen:
                    for r in recos:
                        if _entity_key(r.get("target_entity", {}).get("type"), r.get("target_entity", {}).get("ref")) == key:
                            r["priority_score"] = max(r.get("priority_score") or 0, imp)
                            r["recommendation_type"] = RECO_WATCHLIST_ATTENTION
                            r["explanation"] = (r.get("explanation") or "") + "; watchlist attention."
                            break
                else:
                    seen.add(key)
                    recos.append({
                        "recommendation_id": f"rec-{uuid.uuid4().hex[:12]}",
                        "target_entity": {"type": t, "ref": ref},
                        "recommendation_type": RECO_WATCHLIST_ATTENTION,
                        "priority_score": round(min(100.0, imp), 1),
                        "explanation": w.get("detected_change_summary") or "Watchlist attention.",
                        "timestamp": now,
                    })
        except Exception as e:
            logger.debug("get_recommendations watchlist failed: %s", e)

    # 3) From prioritized alerts (add or boost by target_entity)
    if include_alerts:
        try:
            from amazon_research.discovery import get_prioritized_alerts
            alerts = get_prioritized_alerts(workspace_id=workspace_id, limit_opportunity=15, limit_watch=10, include_operational=False)
            for a in alerts:
                sig = a.get("signal_summary") or {}
                ref = sig.get("target_entity") or sig.get("watched_entity", {}).get("ref") if isinstance(sig.get("watched_entity"), dict) else None
                if not ref and isinstance(sig.get("watched_entity"), dict):
                    ref = sig["watched_entity"].get("ref")
                t = "cluster"
                if isinstance(sig.get("watched_entity"), dict):
                    t = sig["watched_entity"].get("type") or t
                if not ref:
                    continue
                key = _entity_key(t, ref)
                p = a.get("priority_score") or 0
                try:
                    p = float(p)
                except (TypeError, ValueError):
                    p = 50.0
                if key in seen:
                    for r in recos:
                        if _entity_key(r.get("target_entity", {}).get("type"), r.get("target_entity", {}).get("ref")) == key:
                            r["priority_score"] = max(r.get("priority_score") or 0, p)
                            r["recommendation_type"] = RECO_ALERT_PRIORITIZED
                            r["explanation"] = (r.get("explanation") or "") + "; prioritized alert."
                            break
                else:
                    seen.add(key)
                    recos.append({
                        "recommendation_id": f"rec-{uuid.uuid4().hex[:12]}",
                        "target_entity": {"type": t, "ref": ref},
                        "recommendation_type": RECO_ALERT_PRIORITIZED,
                        "priority_score": round(min(100.0, p), 1),
                        "explanation": f"Prioritized alert (score {p:.0f}).",
                        "timestamp": now,
                    })
        except Exception as e:
            logger.debug("get_recommendations alerts failed: %s", e)

    recos.sort(key=lambda x: (-(x.get("priority_score") or 0), x.get("target_entity", {}).get("ref") or ""))
    return recos[:limit]
