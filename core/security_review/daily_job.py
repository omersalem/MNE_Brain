import logging
import sys
from dotenv import load_dotenv

load_dotenv()
from core.security_review.cli import run_security_pipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("mne_security_daily_job")


def run_daily_job():
    logger.info("Starting scheduled daily 07:00 AM security review...")
    try:
        result = run_security_pipeline(dry_run=False, send_email=True)
        if result.get("email_sent"):
            logger.info("Daily security review and email dispatch completed successfully.")
            sys.exit(0)
        else:
            logger.warning("Daily security review generated reports, but email dispatch failed or was skipped.")
            sys.exit(0)
    except Exception as exc:
        logger.error("Fatal error during daily security review: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    run_daily_job()
