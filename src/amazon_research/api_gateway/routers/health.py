"""
Step 231: Health endpoint – small safe payload, timestamp, optional DB sanity.
"""
from datetime import datetime, timezone

from fastapi import APIRouter

from amazon_research.logging_config import get_logger

logger = get_logger("api_gateway.health")

router = APIRouter()


@router.get("/health")
def get_health():
    """Return service status and timestamp. Optionally include db_ok if safe."""
    payload = {
        "status": "ok",
        "service": "api_gateway",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    try:
        from amazon_research.db import get_connection
        conn = get_connection()
        if conn is not None:
            try:
                cur = conn.cursor()
                cur.execute("SELECT 1")
                cur.fetchone()
                cur.close()
                payload["db_ok"] = True
            except Exception:
                payload["db_ok"] = False
        else:
            payload["db_ok"] = False
    except RuntimeError:
        payload["db_ok"] = False  # DB not initialized
    except Exception:
        payload["db_ok"] = False
    logger.debug("health check", extra={"db_ok": payload.get("db_ok")})
    return payload
