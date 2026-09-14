import logging
from logging.handlers import RotatingFileHandler
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()
from core.security_review.cli import run_security_pipeline
from core.security_review.config import SecurityAgentConfig
from core.security_review.service import SecurityReviewService

logger = logging.getLogger("mne_security_daily_job")


def configure_daily_logging() -> None:
    """Persist scheduled-task diagnostics without logging credential material."""
    log_dir = Path(__file__).resolve().parent.parent.parent / "operations" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    file_handler = RotatingFileHandler(
        log_dir / "daily_security_job.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logging.basicConfig(level=logging.INFO, handlers=[stream_handler, file_handler], force=True)


def run_daily_job(
    config_mgr: Optional[SecurityAgentConfig] = None,
    service: Optional[SecurityReviewService] = None,
    pipeline_fn: Optional[Callable[..., Dict[str, Any]]] = None,
) -> int:
    cfg = config_mgr or SecurityAgentConfig()
    if not cfg.is_enabled():
        logger.info("Daily security review is currently disabled in configuration. Skipping run.")
        return 0

    schedule_time = cfg.get_schedule_time()
    logger.info("Starting scheduled daily (%s) security review...", schedule_time)
    try:
        recipients = cfg.get_recipients()
        logger.info("Target recipient count: %d", len(recipients))
        runner = pipeline_fn or run_security_pipeline
        result = runner(
            dry_run=False,
            send_email=True,
            recipients=recipients,
            service=service,
        )
        if result.get("email_sent"):
            logger.info("Daily security review and email dispatch completed successfully.")
            return 0 if result.get("success", True) else 1
        else:
            logger.error(
                "Daily security review generated reports, but email dispatch failed: %s",
                result.get("email_error") or "no SMTP diagnostic was returned",
            )
            return 1
    except Exception as exc:
        logger.error("Fatal error during daily security review: %s", exc, exc_info=True)
        return 1


if __name__ == "__main__":
    configure_daily_logging()
    exit_code = run_daily_job()
    sys.exit(exit_code)
