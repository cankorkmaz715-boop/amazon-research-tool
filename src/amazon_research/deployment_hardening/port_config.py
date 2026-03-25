"""
Step 229: Port and bind host configuration for production and reverse proxy.
Predictable binding; safe defaults. No secrets.
"""
import os

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8766
PORT_ENV = "INTERNAL_API_PORT"
HOST_ENV = "INTERNAL_API_HOST"
PORT_MIN = 1
PORT_MAX = 65535


def get_bind_host() -> str:
    """Return bind host for the HTTP server. Default 0.0.0.0 for reverse proxy."""
    host = (os.environ.get(HOST_ENV) or DEFAULT_HOST).strip()
    return host if host else DEFAULT_HOST


def get_bind_port() -> int:
    """Return bind port. Uses INTERNAL_API_PORT env or default 8766. Clamped to valid range."""
    raw = (os.environ.get(PORT_ENV) or str(DEFAULT_PORT)).strip()
    try:
        p = int(raw)
    except (ValueError, TypeError):
        return DEFAULT_PORT
    return max(PORT_MIN, min(PORT_MAX, p))
