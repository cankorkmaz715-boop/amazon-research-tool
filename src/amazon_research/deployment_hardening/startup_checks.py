"""
Step 229: Startup sanity checks – env validation and optional DB connectivity.
Used by startup_sanity_check script and optionally by server entrypoints.
"""
from typing import List, Tuple

from amazon_research.deployment_hardening.env_validation import validate_required_env


def run_startup_checks(skip_db_connect: bool = True) -> Tuple[bool, List[str]]:
    """
    Run env validation. Optionally check DB connect (skip_db_connect=False).
    Returns (ok, list of error messages). ok is True only when errors is empty.
    """
    errors = validate_required_env()
    if errors:
        return False, errors
    if not skip_db_connect:
        db_ok, db_msg = _check_db_connect()
        if not db_ok:
            errors.append(db_msg)
    return (len(errors) == 0, errors)


def _check_db_connect() -> Tuple[bool, str]:
    """Try to init_db and return (success, error_message)."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        from amazon_research.db import init_db
        init_db()
        return True, ""
    except Exception as e:
        return False, f"Database connection check failed: {e}"
