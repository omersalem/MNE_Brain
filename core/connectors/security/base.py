import abc
import logging
import os
import time
from typing import List
from dotenv import load_dotenv

# Ensure .env is loaded in any execution context
load_dotenv()

from core.connectors.security.models import (
    CollectorResult,
    CollectorStatus,
    NormalizedSecurityEvent,
)

logger = logging.getLogger(__name__)


class BaseSecurityCollector(abc.ABC):
    """Base abstract class for all security device log collectors in MNE_Brain."""

    def __init__(self, device_name: str, timeout: int = 120):
        self.device_name = device_name
        self.timeout = timeout

    @abc.abstractmethod
    def _fetch_logs_internal(self, hours_back: int) -> List[NormalizedSecurityEvent]:
        """Fetch and parse logs for the given time window in hours."""
        pass

    def collect_logs(self, hours_back: int = 24) -> CollectorResult:
        """Executes log collection within an isolated fault boundary."""
        start_time = time.time()
        try:
            events = self._fetch_logs_internal(hours_back=hours_back)
            duration = round(time.time() - start_time, 2)
            return CollectorResult(
                device_name=self.device_name,
                status=CollectorStatus.SUCCESS,
                events=events,
                collection_duration_seconds=duration,
            )
        except Exception as exc:
            duration = round(time.time() - start_time, 2)
            logger.error("Error collecting logs from %s: %s", self.device_name, exc, exc_info=True)
            return CollectorResult(
                device_name=self.device_name,
                status=CollectorStatus.FAILED,
                error_message=str(exc),
                events=[],
                collection_duration_seconds=duration,
            )
