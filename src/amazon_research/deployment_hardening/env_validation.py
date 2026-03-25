"""
Step 229: Environment validation at startup. Fail fast with readable errors for missing critical vars.
No secrets in messages. Safe defaults only for non-critical vars.
"""
import os
from typing import List


REQUIRED_ENV_VARS = ["DATABASE_URL"]
OPTIONAL_ENV_VARS = ["INTERNAL_API_PORT", "INTERNAL_API_HOST"]
PORT_MIN = 1
PORT_MAX = 65535
DEFAULT_PORT = 8766


def validate_required_env() -> List[str]:
    """
    Validate required environment variables. Returns list of error messages (empty if valid).
    Does not log; caller may log or print before exit.
    """
    errors: List[str] = []
    for key in REQUIRED_ENV_VARS:
        val = os.environ.get(key)
        if not val or not str(val).strip():
            errors.append(f"Missing required environment variable: {key}. Set it in .env or the environment.")
    if "DATABASE_URL" in os.environ:
        url = (os.environ.get("DATABASE_URL") or "").strip()
        if url and not url.startswith(("postgresql://", "postgres://")):
            errors.append("DATABASE_URL must be a PostgreSQL URL (postgresql:// or postgres://).")
    port_val = os.environ.get("INTERNAL_API_PORT", str(DEFAULT_PORT)).strip()
    if port_val:
        try:
            p = int(port_val)
            if p < PORT_MIN or p > PORT_MAX:
                errors.append(f"INTERNAL_API_PORT must be between {PORT_MIN} and {PORT_MAX}.")
        except ValueError:
            errors.append("INTERNAL_API_PORT must be a number.")
    return errors
