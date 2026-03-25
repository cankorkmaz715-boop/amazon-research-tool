"""
Category scan planner v1. Step 74 – select ready seeds, priority/readiness rules, queue-friendly scan tasks.
Built on category seed manager; lightweight and deterministic.
"""
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger
from amazon_research.db.category_seeds import get_ready_category_seeds

logger = get_logger("planner.category_scan_planner")


def build_scan_plan(
    workspace_id: Optional[int] = None,
    marketplace: Optional[str] = None,
    max_tasks: int = 5,
    order_by_last_scanned: bool = True,
) -> Dict[str, Any]:
    """
    Build a queue-friendly list of category scan tasks from ready seeds.
    Priority: active seeds only, ordered by last_scanned_at ASC NULLS FIRST (least recently scanned first).
    Each task has seed_id, category_url, marketplace, label for the category scanner and post-scan update.
    """
    seeds = get_ready_category_seeds(
        workspace_id=workspace_id,
        marketplace=marketplace,
        limit=max_tasks,
        order_by_last_scanned=order_by_last_scanned,
    )
    tasks: List[Dict[str, Any]] = []
    for s in seeds:
        tasks.append({
            "seed_id": s["id"],
            "category_url": s["category_url"],
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
        "category_scan_plan built",
        extra={"task_count": len(tasks), "workspace_id": workspace_id, "marketplace": marketplace},
    )
    return plan
