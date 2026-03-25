"""
Step 185: Live discovery safeguards – safety layer for multi-market discovery execution.
Enforces: max targets per cycle, max pages per target, per-market caps, duplicate suppression,
invalid/empty seed rejection, cooldown for recently scanned targets.
Decisions: allow, defer, reject. Rule-based, deterministic. Integrates with multi-market activation,
intelligent crawl scheduler, production loop, scraper reliability, recovery/retry orchestrator.
Extensible for future dynamic crawl budgets.
"""
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from amazon_research.logging_config import get_logger

logger = get_logger("scheduler.live_discovery_safeguards")

# Decisions
DECISION_ALLOW = "allow"
DECISION_DEFER = "defer"
DECISION_REJECT = "reject"

# Default conservative caps (safe for 24/7)
DEFAULT_MAX_TARGETS_PER_CYCLE = 30
DEFAULT_MAX_PAGES_PER_TARGET = 5
DEFAULT_PER_MARKET_CAP = 15
DEFAULT_COOLDOWN_SECONDS = 300  # 5 min

# In-memory: last scanned time per target key (for cooldown when DB not used)
_last_scanned: Dict[str, float] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _target_key(market: str, target_type: str, target_id: str) -> str:
    """Normalize key for duplicate and cooldown tracking."""
    m = (market or "").strip().upper()
    t = (target_type or "").strip().lower()
    tid = (target_id or "").strip()
    return f"{m}|{t}|{tid}"


def _decision(
    market: str,
    target_type: str,
    target_id: str,
    decision: str,
    reason: str,
    max_pages: Optional[int] = None,
) -> Dict[str, Any]:
    return {
        "market": (market or "").strip(),
        "target_type": (target_type or "").strip(),
        "target_id": (target_id or "").strip(),
        "safeguard_decision": decision,
        "safeguard_reason": reason,
        "timestamp": _now_iso(),
        **({"max_pages": max_pages} if max_pages is not None else {}),
    }


def record_target_scanned(market: str, target_type: str, target_id: str) -> None:
    """Record that a target was scanned (for cooldown). Call from worker or discovery storage."""
    global _last_scanned
    key = _target_key(market, target_type, target_id)
    _last_scanned[key] = time.time()


def get_last_scanned_time(market: str, target_type: str, target_id: str) -> Optional[float]:
    """Return last scanned timestamp for target, or None."""
    key = _target_key(market, target_type, target_id)
    return _last_scanned.get(key)


def evaluate_target(
    market: str,
    target_type: str,
    target_id: str,
    context: Optional[Dict[str, Any]] = None,
    last_scanned_override: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Evaluate one target against safeguards. Returns structured decision: market, target_type, target_id,
    safeguard_decision (allow/defer/reject), safeguard_reason, timestamp, optional max_pages.
    """
    ctx = context or {}
    max_targets = int(ctx.get("max_targets_per_cycle") or DEFAULT_MAX_TARGETS_PER_CYCLE)
    per_market_cap = int(ctx.get("per_market_cap") or DEFAULT_PER_MARKET_CAP)
    cooldown_sec = float(ctx.get("cooldown_seconds") or DEFAULT_COOLDOWN_SECONDS)
    max_pages = int(ctx.get("max_pages_per_target") or DEFAULT_MAX_PAGES_PER_TARGET)
    cycle_count = int(ctx.get("cycle_target_count", 0))
    per_market: Dict[str, int] = dict(ctx.get("per_market_counts") or {})
    seen_keys: Set[str] = set(ctx.get("seen_target_keys") or [])

    market = (market or "").strip().upper()
    target_type = (target_type or "").strip().lower()
    target_id = (target_id or "").strip()
    key = _target_key(market, target_type, target_id)

    # Invalid/empty seed rejection
    if not target_id:
        return _decision(market, target_type, target_id, DECISION_REJECT, "empty_target_id")

    # Duplicate target suppression
    if key in seen_keys:
        return _decision(market, target_type, target_id, DECISION_REJECT, "duplicate_target")

    # Per-market cap
    if per_market.get(market, 0) >= per_market_cap:
        return _decision(market, target_type, target_id, DECISION_DEFER, "per_market_cap_exceeded")

    # Max targets per cycle
    if cycle_count >= max_targets:
        return _decision(market, target_type, target_id, DECISION_DEFER, "max_targets_per_cycle_reached")

    # Cooldown for recently scanned targets
    last_ts = last_scanned_override if last_scanned_override is not None else get_last_scanned_time(market, target_type, target_id)
    if last_ts is not None and cooldown_sec > 0:
        elapsed = time.time() - last_ts
        if elapsed < cooldown_sec:
            return _decision(market, target_type, target_id, DECISION_DEFER, "cooldown_active")

    return _decision(
        market, target_type, target_id, DECISION_ALLOW, "ok",
        max_pages=max_pages,
    )


def evaluate_safeguards(
    candidates: List[Dict[str, Any]],
    context: Optional[Dict[str, Any]] = None,
    last_scanned_map: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Evaluate a list of candidates through the safeguard layer. Updates context in place for cycle/market counts.
    Returns: decisions (list of decision dicts), allowed (list of candidate items that passed),
    deferred (list), rejected (list). Allowed items include safeguard_decision and max_pages when relevant.
    """
    ctx = context or {}
    max_targets = int(ctx.get("max_targets_per_cycle") or DEFAULT_MAX_TARGETS_PER_CYCLE)
    per_market_cap = int(ctx.get("per_market_cap") or DEFAULT_PER_MARKET_CAP)
    cooldown_sec = float(ctx.get("cooldown_seconds") or DEFAULT_COOLDOWN_SECONDS)
    max_pages = int(ctx.get("max_pages_per_target") or DEFAULT_MAX_PAGES_PER_TARGET)

    cycle_count = int(ctx.get("cycle_target_count", 0))
    per_market: Dict[str, int] = dict(ctx.get("per_market_counts") or {})
    seen_keys: Set[str] = set(ctx.get("seen_target_keys") or [])
    last_scanned_map = last_scanned_map or {}

    decisions: List[Dict[str, Any]] = []
    allowed: List[Dict[str, Any]] = []
    deferred: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []

    for c in candidates:
        market = (c.get("market") or "").strip().upper()
        target_type = (c.get("target_type") or "keyword").strip().lower()
        target_id = (c.get("target_id") or "").strip()
        key = _target_key(market, target_type, target_id)
        last_ts = last_scanned_map.get(key) or get_last_scanned_time(market, target_type, target_id)

        run_ctx = {
            "max_targets_per_cycle": max_targets,
            "per_market_cap": per_market_cap,
            "cooldown_seconds": cooldown_sec,
            "max_pages_per_target": max_pages,
            "cycle_target_count": cycle_count,
            "per_market_counts": dict(per_market),
            "seen_target_keys": set(seen_keys),
        }
        dec = evaluate_target(market, target_type, target_id, run_ctx, last_scanned_override=last_ts)
        decisions.append(dec)

        if dec["safeguard_decision"] == DECISION_ALLOW:
            cycle_count += 1
            per_market[market] = per_market.get(market, 0) + 1
            seen_keys.add(key)
            out = dict(c)
            out["safeguard_decision"] = DECISION_ALLOW
            out["safeguard_reason"] = dec["safeguard_reason"]
            out["timestamp"] = dec["timestamp"]
            if dec.get("max_pages") is not None:
                out["max_pages"] = dec["max_pages"]
            allowed.append(out)
        elif dec["safeguard_decision"] == DECISION_DEFER:
            deferred.append(dec)
        else:
            rejected.append(dec)

    return {
        "decisions": decisions,
        "allowed": allowed,
        "deferred": deferred,
        "rejected": rejected,
        "counts": {"allowed": len(allowed), "deferred": len(deferred), "rejected": len(rejected)},
    }


def get_default_safeguard_context() -> Dict[str, Any]:
    """Return default caps for integration with production loop and multi-market activation."""
    return {
        "max_targets_per_cycle": DEFAULT_MAX_TARGETS_PER_CYCLE,
        "max_pages_per_target": DEFAULT_MAX_PAGES_PER_TARGET,
        "per_market_cap": DEFAULT_PER_MARKET_CAP,
        "cooldown_seconds": DEFAULT_COOLDOWN_SECONDS,
        "cycle_target_count": 0,
        "per_market_counts": {},
        "seen_target_keys": set(),
    }


def filter_activation_targets_with_safeguards(
    activation_targets: List[Dict[str, Any]],
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Run multi-market activation targets through safeguards. Returns same structure as evaluate_safeguards;
    allowed list can be passed to to_scheduler_tasks_multi_market or enqueue.
    """
    return evaluate_safeguards(activation_targets, context=context)


def get_safeguarded_activation_targets(
    markets: Optional[List[str]] = None,
    workspace_id: Optional[int] = None,
    limit_per_type: int = 5,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Get multi-market activation targets and run through safeguards. Integration with multi-market activation.
    Returns evaluate_safeguards result (decisions, allowed, deferred, rejected, counts).
    """
    try:
        from amazon_research.scheduler.multi_market_activation import get_multi_market_activation
        candidates = get_multi_market_activation(markets=markets, workspace_id=workspace_id, limit_per_type=limit_per_type)
    except Exception as e:
        logger.debug("get_safeguarded_activation_targets get_multi_market_activation: %s", e)
        return {"decisions": [], "allowed": [], "deferred": [], "rejected": [], "counts": {"allowed": 0, "deferred": 0, "rejected": 0}}
    ctx = context or get_default_safeguard_context()
    return filter_activation_targets_with_safeguards(candidates, context=ctx)
