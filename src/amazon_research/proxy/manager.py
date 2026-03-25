"""
Proxy manager – central proxy configuration. All bots use this layer.
Step 31: rotation pool (deterministic round-robin); one proxy per session, credentials from env.
"""
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("proxy")

# Deterministic rotation: advance per new session (shared across manager instances)
_rotation_index = 0


class ProxyManager:
    """
    Central proxy management. Optional pool for rotation; one proxy per browser session.
    Builds Playwright proxy dict from config. Credentials only from env.
    """

    def __init__(
        self,
        server: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        pool: Optional[List[Dict[str, str]]] = None,
        **kwargs: Any,
    ) -> None:
        if pool is not None:
            self._pool = pool
            self._enabled = len(pool) > 0
        else:
            self._server = server
            self._username = username or kwargs.get("username")
            self._password = password or kwargs.get("password")
            self._enabled = bool(self._server and self._username and self._password)
            self._pool = [{"server": self._server, "username": self._username, "password": self._password}] if self._enabled else []

    @classmethod
    def from_config(cls) -> "ProxyManager":
        """Build from central config (env). Pool of 1 or 2 when PROXY_HOST_2 set. Credentials from env."""
        from amazon_research.config import get_config
        cfg = get_config()
        servers: List[str] = [f"http://{cfg.proxy_host}:{cfg.proxy_port}"]
        if getattr(cfg, "proxy_host_2", None) and getattr(cfg, "proxy_port_2", None):
            servers.append(f"http://{cfg.proxy_host_2}:{cfg.proxy_port_2}")
        elif getattr(cfg, "proxy_host_2", None):
            servers.append(f"http://{cfg.proxy_host_2}:{cfg.proxy_port}")
        pool = [
            {"server": s, "username": cfg.proxy_username or "", "password": cfg.proxy_password or ""}
            for s in servers
            if cfg.proxy_username and cfg.proxy_password
        ]
        if not pool:
            return cls(server=servers[0] if servers else None, username=cfg.proxy_username, password=cfg.proxy_password)
        return cls(pool=pool)

    def get_next_for_session(self) -> "ProxyManager":
        """Advance to next proxy in pool (deterministic round-robin). Call once per new browser session. Returns self."""
        global _rotation_index
        if self._pool:
            _rotation_index += 1
        return self

    def get_playwright_proxy(self) -> Optional[Dict[str, str]]:
        """
        Return proxy dict for current session (current pool entry). None if proxy disabled.
        """
        if not self._enabled or not self._pool:
            return None
        idx = _rotation_index % len(self._pool)
        entry = self._pool[idx]
        if not entry.get("username") or not entry.get("password"):
            return None
        return {"server": entry["server"], "username": entry["username"], "password": entry["password"]}

    def pool_size(self) -> int:
        return len(self._pool)

    def is_enabled(self) -> bool:
        return self._enabled
