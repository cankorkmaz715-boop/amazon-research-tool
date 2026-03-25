"""
Keyword scan planner v1. Step 78 – select ready keyword seeds, priority/readiness rules, queue-friendly scan tasks.
Built on keyword seed manager; lightweight and deterministic.
"""
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger
from amazon_research.db.keyword_seeds import get_ready_keyword_seeds

logger = get_logger("planner.keyword_scan_planner")


def build_keyword_scan_plan(
    workspace_id: Optional[int] = None,
    marketplace: Optional[str] = None,
    max_tasks: int = 5,
    order_by_last_scanned: bool = True,
) -> Dict[str, Any]:
    """
    Build a queue-friendly list of keyword scan tasks from ready seeds.
    Priority: active seeds only, ordered by last_scanned_at ASC NULLS FIRST (least recently scanned first).
    Each task has seed_id, keyword, marketplace, label for the keyword scanner and post-scan update.
    """
    seeds = get_ready_keyword_seeds(
        workspace_id=workspace_id,
        marketplace=marketplace,
        limit=max_tasks,
        order_by_last_scanned=order_by_last_scanned,
    )
    tasks: List[Dict[str, Any]] = []
    for s in seeds:
        tasks.append({
            "seed_id": s["id"],
            "keyword": s["keyword"],
            "marketplace": s.get("marketplace") or "DE",
            "label": s.get("label"),
            "last_scanned_at": s.get("last_scanned_at"),
        })
    plan = {
        "tasks": tasks,
        "task_count": len(tasks),
        "workspace_id": workspace_id,
        "marketplace": marketplace,
    }
    logger.info(
        "keyword_scan_plan built",
        extra={"task_count": len(tasks), "workspace_id": workspace_id, "marketplace": marketplace},
    )
    return plan
