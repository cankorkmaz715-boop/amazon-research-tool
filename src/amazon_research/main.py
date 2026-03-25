"""
Entrypoint: load config, setup logging, init DB, run placeholder health check.
Run from repo root with: PYTHONPATH=src python -m amazon_research.main
"""


def main() -> None:
    from dotenv import load_dotenv
    load_dotenv()

    from amazon_research.logging_config import setup_logging, get_logger
    setup_logging()
    log = get_logger("main")

    from amazon_research.config import get_config
    cfg = get_config()
    log.info("config loaded", extra={"environment": cfg.environment})

    from amazon_research.monitoring import init_sentry
    init_sentry()

    from amazon_research.db import init_db
    init_db()
    log.info("db init done")

    from amazon_research.monitoring import health_check
    health = health_check()
    log.info("health_check", extra=health)

    log.info("skeleton run complete")


if __name__ == "__main__":
    main()
