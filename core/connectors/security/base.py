import abc
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Union
from dotenv import load_dotenv

load_dotenv()

from core.connectors.security.models import (
    CollectorRequest,
    CollectorResult,
    CollectorStatus,
    NormalizedSecurityEvent,
)
from core.security_review.contracts import (
    CollectorDiagnostic,
    DiagnosticStage,
    DiagnosticStatus,
)

logger = logging.getLogger(__name__)

DEVICE_TO_CANONICAL = {
    "FortiGate": "fortigate_core",
    "FortiAnalyzer": "fortianalyzer",
    "F5 BIG-IP": "f5_bigip",
    "Cisco FMC": "cisco_fmc",
    "Sophos Email": "sophos_email",
    "Active Directory": "active_directory",
    "Exchange": "exchange_2019",
}


class BaseSecurityCollector(abc.ABC):
    """Base abstract class for all security device log collectors in MNE_Brain."""

    def __init__(self, device_name: str, timeout: int = 120, collector_id: Optional[str] = None):
        self.device_name = device_name
        self.timeout = timeout
        self.collector_id = collector_id or DEVICE_TO_CANONICAL.get(device_name, device_name.lower().replace(" ", "_"))

    def _fetch_logs_internal(self, hours_back: int) -> List[NormalizedSecurityEvent]:
        """Legacy fetch hook. Subclasses may override this or _fetch_logs_with_request."""
        return []

    def _fetch_logs_with_request(self, request: CollectorRequest) -> CollectorResult:
        """Subclasses can implement this method to execute collection with rich diagnostics.
        Default implementation delegates to _fetch_logs_internal for backwards compatibility.
        """
        h = int(request.hours_back or 24)
        events = self._fetch_logs_internal(hours_back=h)
        return CollectorResult(
            device_name=self.device_name,
            status=CollectorStatus.SUCCESS,
            events=events,
            records_fetched=len(events),
            records_parsed=len(events),
        )

    def collect_logs(
        self,
        hours_back: Union[int, float, CollectorRequest, None] = 24,
        request: Optional[CollectorRequest] = None,
    ) -> CollectorResult:
        """Executes log collection within an isolated fault boundary with rich diagnostics."""
        start_time = time.time()

        if isinstance(hours_back, CollectorRequest):
            actual_request = hours_back
        elif request is not None:
            actual_request = request
        else:
            h = float(hours_back) if hours_back is not None else 24.0
            actual_request = CollectorRequest(hours_back=h)

        start_dt, end_dt = actual_request.get_time_window()
        requested_time_range = {
            "start": start_dt.isoformat(),
            "end": end_dt.isoformat(),
            "hours_back": actual_request.hours_back,
        }

        if actual_request.is_cancelled():
            diag = CollectorDiagnostic(
                collector_id=self.collector_id,
                device_name=self.device_name,
                canonical_entity=self.collector_id,
                stage=DiagnosticStage.QUERY,
                status=DiagnosticStatus.CANCELLED,
                diagnostic_code="CANCELLED",
                message="Collection was cancelled before execution.",
                requested_time_range=requested_time_range,
                duration_seconds=0.0,
            )
            return CollectorResult(
                device_name=self.device_name,
                status=CollectorStatus.SKIPPED,
                events=[],
                error_message="Collection cancelled.",
                collection_duration_seconds=0.0,
                diagnostic=diag,
            )

        try:
            res = self._fetch_logs_with_request(actual_request)
            duration = round(time.time() - start_time, 2)
            res.collection_duration_seconds = duration

            if res.diagnostic is None:
                observed_time_range = None
                if res.events:
                    timestamps = [e.timestamp for e in res.events if e.timestamp]
                    if timestamps:
                        oldest = min(timestamps).isoformat()
                        newest = max(timestamps).isoformat()
                        observed_time_range = {"oldest": oldest, "newest": newest}

                if res.status == CollectorStatus.SUCCESS:
                    if len(res.events) == 0:
                        if res.records_fetched == 0:
                            diag_code = "QUERY_EMPTY_ZERO_SOURCE"
                            msg = f"Source returned zero records for time window ({requested_time_range['start']} to {requested_time_range['end']})."
                        elif res.records_ignored > 0 and res.records_parsed == 0:
                            diag_code = "QUERY_EMPTY_FILTERED"
                            msg = f"{res.records_fetched} records retrieved but all filtered by time/category."
                        elif res.records_malformed > 0 and res.records_parsed == 0:
                            diag_code = "PARSE_ERROR"
                            res.status = CollectorStatus.FAILED
                            msg = f"{res.records_fetched} records retrieved but all failed parsing."
                        else:
                            diag_code = "QUERY_EMPTY_ZERO_SOURCE"
                            msg = "Zero records found."
                    else:
                        diag_code = "OK"
                        msg = f"Successfully collected {len(res.events)} events."

                    status_val = DiagnosticStatus.SUCCESS if res.status == CollectorStatus.SUCCESS else DiagnosticStatus.FAILED
                elif res.status == CollectorStatus.WARNING:
                    diag_code = "PARTIAL_RESULTS"
                    msg = res.error_message or "Partial collection completed."
                    status_val = DiagnosticStatus.PARTIAL
                else:
                    diag_code = "COLLECTION_ERROR"
                    msg = res.error_message or "Collection failed."
                    status_val = DiagnosticStatus.FAILED

                res.diagnostic = CollectorDiagnostic(
                    collector_id=self.collector_id,
                    device_name=self.device_name,
                    canonical_entity=self.collector_id,
                    stage=DiagnosticStage.COMPLETE,
                    status=status_val,
                    diagnostic_code=diag_code,
                    message=msg,
                    requested_time_range=requested_time_range,
                    observed_time_range=observed_time_range,
                    records_fetched=res.records_fetched or len(res.events),
                    records_parsed=res.records_parsed or len(res.events),
                    records_ignored=res.records_ignored,
                    records_malformed=res.records_malformed,
                    duration_seconds=duration,
                )

            return res

        except Exception as exc:
            duration = round(time.time() - start_time, 2)
            logger.error("Error collecting logs from %s: %s", self.device_name, exc, exc_info=True)
            err_msg = str(exc)

            stage = DiagnosticStage.QUERY
            diag_code = "COLLECTION_ERROR"
            suggested_action = "Check device configuration and connectivity."

            if isinstance(exc, TimeoutError):
                stage = DiagnosticStage.CONNECTION
                diag_code = "TIMEOUT"
                suggested_action = "Verify network reachability and device response time."
            elif isinstance(exc, (ConnectionError, ConnectionRefusedError)):
                stage = DiagnosticStage.CONNECTION
                diag_code = "CONNECTION_FAILED"
                suggested_action = f"Verify network route and firewall port accessibility to {self.device_name}."
            elif (
                isinstance(exc, PermissionError)
                or "credential" in err_msg.lower()
                or "password" in err_msg.lower()
                or "api_key" in err_msg.lower()
                or "unauthorized" in err_msg.lower()
                or "401" in err_msg.lower()
                or "authentication" in err_msg.lower()
            ):
                stage = DiagnosticStage.AUTHENTICATION
                diag_code = "MISSING_CREDENTIALS" if ("neither" in err_msg.lower() or "not configured" in err_msg.lower()) else "AUTH_FAILED"
                suggested_action = "Verify credentials in environment or local secrets configuration."
            elif "parse" in err_msg.lower() or "json" in err_msg.lower():
                stage = DiagnosticStage.PARSE
                diag_code = "PARSE_ERROR"
                suggested_action = "Inspect raw device log format for schema drift or unexpected characters."

            diag = CollectorDiagnostic(
                collector_id=self.collector_id,
                device_name=self.device_name,
                canonical_entity=self.collector_id,
                stage=stage,
                status=DiagnosticStatus.FAILED,
                diagnostic_code=diag_code,
                message=err_msg,
                requested_time_range=requested_time_range,
                duration_seconds=duration,
                suggested_next_action=suggested_action,
            )
            return CollectorResult(
                device_name=self.device_name,
                status=CollectorStatus.FAILED,
                error_message=err_msg,
                events=[],
                collection_duration_seconds=duration,
                diagnostic=diag,
            )
