"""
Step 208: Memory pressure – read current process RSS where feasible.
Lightweight; no crash on failure; returns None if unavailable.
"""
from typing import Optional

from amazon_research.logging_config import get_logger

logger = get_logger("resource_guard.memory_guard")


def get_process_memory_mb() -> Optional[float]:
    """
    Current process RSS in MB. Uses /proc/self/status (Linux) or psutil if available.
    Returns None on failure; caller should fall back per policy.
    """
    try:
        # Linux: VmRSS in kB
        with open("/proc/self/status", "r") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    parts = line.split()
                    if len(parts) >= 2:
                        kb = int(parts[1])
                        return round(kb / 1024.0, 2)
                    break
    except (FileNotFoundError, OSError, ValueError) as e:
        logger.debug("resource_guard memory read failure (proc): %s", e)
    except Exception as e:
        logger.warning("resource_guard metric read failure memory: %s", e, exc_info=False)

    try:
        import psutil
        proc = psutil.Process()
        return round(proc.memory_info().rss / (1024 * 1024), 2)
    except ImportError:
        pass
    except Exception as e:
        logger.warning("resource_guard metric read failure memory (psutil): %s", e, exc_info=False)
    return None
