import hashlib
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv

load_dotenv()

from core.connectors.security.base import BaseSecurityCollector
from core.connectors.security.models import (
    CollectorRequest,
    CollectorResult,
    CollectorStatus,
    NormalizedSecurityEvent,
    ThreatCategory,
)
from core.security_review.contracts import (
    CollectorDiagnostic,
    DiagnosticStage,
    DiagnosticStatus,
)

logger = logging.getLogger(__name__)


class FmcSecurityCollector(BaseSecurityCollector):
    """Collector for Cisco FMC / FTD (172.23.70.77 / .78).

    Collects Snort intrusion alerts, Security Intelligence blocks,
    malware/file events, and audit records.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        domain_uuid: Optional[str] = None,
        timeout: int = 120,
    ):
        super().__init__(device_name="Cisco FMC", timeout=timeout, collector_id="cisco_fmc")
        self.host = host or os.getenv("MNE_FMC_HOST", "172.23.70.77")
        self.username = username or os.getenv("MNE_FMC_USERNAME", "admin")
        self.password = password or os.getenv("MNE_FMC_PASSWORD", "")
        self.domain_uuid = domain_uuid or os.getenv("MNE_FMC_DOMAIN_UUID", "")

    def parse_fmc_event(self, item: Dict[str, Any]) -> NormalizedSecurityEvent:
        """Parses a Cisco FMC intrusion or security intelligence JSON record."""
        event_id = str(item.get("id") or item.get("eventId") or hashlib.md5(str(item).encode()).hexdigest()[:10])
        src_ip = item.get("sourceIp") or item.get("attackerIp")
        dst_ip = item.get("destinationIp") or item.get("targetIp")
        rule_msg = item.get("ruleMessage") or item.get("message") or "Snort Intrusion Event"
        action_raw = str(item.get("action", "")).lower()

        if action_raw in ("block", "drop", "dropped", "blocked"):
            action = "BLOCKED"
        elif action_raw in ("allow", "permit", "passed"):
            action = "ALLOWED"
        else:
            action = "ALERT"

        ts = item.get("timestamp") or item.get("time") or item.get("eventTime")
        event_time = datetime.now(timezone.utc)
        if ts:
            try:
                if isinstance(ts, (int, float)):
                    # Check if epoch is in milliseconds
                    if ts > 1e11:
                        ts = ts / 1000.0
                    event_time = datetime.fromtimestamp(ts, tz=timezone.utc)
                elif isinstance(ts, str):
                    clean_ts = ts.replace("Z", "+00:00")
                    event_time = datetime.fromisoformat(clean_ts).replace(tzinfo=timezone.utc)
            except Exception:
                pass

        category = ThreatCategory.INTRUSION
        rule_lower = rule_msg.lower()
        if "login" in rule_lower or "session" in rule_lower or "authentication" in rule_lower:
            category = ThreatCategory.PRIVILEGE_CHANGE
        elif "malware" in rule_lower or "virus" in rule_lower or "trojan" in rule_lower:
            category = ThreatCategory.MALWARE
        elif "c2" in rule_lower or "botnet" in rule_lower or "scan" in rule_lower:
            category = ThreatCategory.INTRUSION

        # Enriched metadata preserving managed device identity and policies
        metadata = dict(item)
        if "classification" in item:
            metadata["classification"] = item["classification"]
        if "impact" in item:
            metadata["impact"] = item["impact"]
        if "sensor" in item or "deviceName" in item:
            metadata["managed_device"] = item.get("deviceName") or item.get("sensor")

        return NormalizedSecurityEvent(
            event_id=f"fmc-{event_id}",
            timestamp=event_time,
            source_device="Cisco FMC",
            category=category,
            threat_name=rule_msg,
            attacker_ip=src_ip,
            target=dst_ip,
            action_taken=action,
            count=1,
            raw_snippet=str(item)[:300],
            metadata=metadata,
        )

    def _fetch_logs_internal(self, hours_back: int) -> List[NormalizedSecurityEvent]:
        """Legacy entrypoint: validates credentials and calls _fetch_logs_with_request."""
        if not self.password:
            raise ValueError("MNE_FMC_PASSWORD is not configured in .env.")
        req = CollectorRequest(hours_back=hours_back)
        result = self._fetch_logs_with_request(req)
        return result.events

    def _fetch_logs_with_request(self, request: CollectorRequest) -> CollectorResult:
        """Queries FMC REST API for intrusion, security intelligence, and audit events."""
        if not self.password:
            raise ValueError("MNE_FMC_PASSWORD is not configured in .env.")

        start_dt, end_dt = request.get_time_window()
        requested_time_range = {
            "start": start_dt.isoformat(),
            "end": end_dt.isoformat(),
            "hours_back": request.hours_back,
        }

        import requests
        import urllib3
        urllib3.disable_warnings()

        events: List[NormalizedSecurityEvent] = []
        records_fetched = 0
        records_parsed = 0
        records_ignored = 0
        records_malformed = 0
        pages_retrieved = 0
        has_more = False

        # Authenticate
        auth_url = f"https://{self.host}/api/fmc_platform/v1/auth/generatetoken"
        try:
            resp = requests.post(
                auth_url,
                auth=(self.username, self.password),
                verify=False,
                timeout=30,
            )
        except Exception as conn_err:
            raise ConnectionError(f"Could not connect to FMC at {self.host}: {conn_err}")

        if resp.status_code in (401, 403):
            raise PermissionError(f"FMC authentication failed: HTTP {resp.status_code}")
        elif resp.status_code not in (200, 204):
            raise ConnectionError(f"FMC authentication returned status {resp.status_code}")

        token = resp.headers.get("X-auth-access-token")
        if not token:
            raise ConnectionError("FMC authentication succeeded but no X-auth-access-token was returned.")

        headers = {"X-auth-access-token": token}

        # Domain discovery
        domain = self.domain_uuid or resp.headers.get("DOMAIN_UUID")
        if not domain:
            try:
                dom_url = f"https://{self.host}/api/fmc_platform/v1/info/domain"
                dom_resp = requests.get(dom_url, headers=headers, verify=False, timeout=20)
                if dom_resp.status_code == 200:
                    items = dom_resp.json().get("items", [])
                    if items:
                        domain = items[0].get("uuid")
            except Exception:
                pass
        if not domain:
            domain = "e276abec-e0f2-11e3-8169-6d9ed49b625f"

        batch_limit = min(request.max_records, 100)

        # Endpoints to query
        endpoints = [
            f"/api/fmc_config/v1/domain/{domain}/operational/intrusionevents",
            f"/api/fmc_config/v1/domain/{domain}/operational/securityintelligenceevents",
            f"/api/fmc_platform/v1/domain/{domain}/audit/auditrecords",
        ]

        endpoint_diagnostics: Dict[str, Dict[str, Any]] = {}
        for ep in endpoints:
            ep_name = ep.split("/")[-1]
            endpoint_diagnostics[ep_name] = {
                "endpoint": ep,
                "status": "NOT_ATTEMPTED",
                "status_code": None,
                "records_fetched": 0,
                "error": None,
            }

        for ep in endpoints:
            if len(events) >= request.max_records or request.is_cancelled():
                break

            ep_name = ep.split("/")[-1]
            offset = 0
            while len(events) < request.max_records and not request.is_cancelled():
                pages_retrieved += 1
                query_url = f"https://{self.host}{ep}?limit={batch_limit}&offset={offset}"
                try:
                    q_resp = requests.get(query_url, headers=headers, verify=False, timeout=self.timeout)
                    endpoint_diagnostics[ep_name]["status_code"] = q_resp.status_code
                    if q_resp.status_code == 200:
                        endpoint_diagnostics[ep_name]["status"] = "SUCCESS"
                        data = q_resp.json()
                        items = data.get("items", [])
                        records_fetched += len(items)
                        endpoint_diagnostics[ep_name]["records_fetched"] += len(items)
                        if not items:
                            break

                        for it in items:
                            try:
                                parsed = self.parse_fmc_event(it)
                                if request.categories and parsed.category.value not in request.categories and parsed.category not in request.categories:
                                    records_ignored += 1
                                    continue
                                if (start_dt - timedelta(minutes=5)) <= parsed.timestamp <= (end_dt + timedelta(minutes=15)):
                                    events.append(parsed)
                                    records_parsed += 1
                                    if len(events) >= request.max_records:
                                        has_more = True
                                        break
                                else:
                                    records_ignored += 1
                            except Exception:
                                records_malformed += 1

                        offset += len(items)
                        if len(items) < batch_limit:
                            break
                    elif q_resp.status_code in (401, 403):
                        endpoint_diagnostics[ep_name]["status"] = "REJECTED"
                        endpoint_diagnostics[ep_name]["error"] = f"HTTP {q_resp.status_code} Access Denied"
                        logger.warning("FMC query to %s returned HTTP %d (rejected)", ep, q_resp.status_code)
                        break
                    elif q_resp.status_code == 404:
                        endpoint_diagnostics[ep_name]["status"] = "NOT_FOUND"
                        endpoint_diagnostics[ep_name]["error"] = "HTTP 404 Not Found"
                        logger.warning("FMC query to %s returned HTTP 404 (endpoint not supported)", ep)
                        break
                    else:
                        endpoint_diagnostics[ep_name]["status"] = "ERROR"
                        endpoint_diagnostics[ep_name]["error"] = f"HTTP {q_resp.status_code}"
                        logger.warning("FMC query to %s returned HTTP %d", ep, q_resp.status_code)
                        break
                except Exception as ep_err:
                    endpoint_diagnostics[ep_name]["status"] = "FAILED"
                    endpoint_diagnostics[ep_name]["error"] = str(ep_err)
                    logger.warning("FMC query to %s failed: %s", ep, ep_err)
                    break

        # Observed time range
        observed_time_range = None
        if events:
            timestamps = [e.timestamp for e in events if e.timestamp]
            if timestamps:
                observed_time_range = {
                    "oldest": min(timestamps).isoformat(),
                    "newest": max(timestamps).isoformat(),
                }

        # Status and message evaluation
        successful_eps = [name for name, d in endpoint_diagnostics.items() if d["status"] == "SUCCESS"]
        rejected_eps = [name for name, d in endpoint_diagnostics.items() if d["status"] == "REJECTED"]
        unsupported_eps = [name for name, d in endpoint_diagnostics.items() if d["status"] == "NOT_FOUND"]
        failed_eps = [name for name, d in endpoint_diagnostics.items() if d["status"] in ("ERROR", "FAILED")]

        if len(events) > 0:
            if rejected_eps or failed_eps:
                status = CollectorStatus.WARNING
                diag_code = "PARTIAL_SUCCESS"
                msg = (
                    f"Retrieved {len(events)} security events from Cisco FMC (domain: {domain}). "
                    f"Endpoints rejected/failed: {', '.join(rejected_eps + failed_eps)}."
                )
            else:
                status = CollectorStatus.SUCCESS
                diag_code = "OK"
                stream_note = f" (streams requiring eStreamer omitted: {', '.join(unsupported_eps)})" if unsupported_eps else ""
                msg = f"Retrieved {len(events)} security events from Cisco FMC (domain: {domain}){stream_note}."
        elif len(successful_eps) == 0 and (rejected_eps or failed_eps or unsupported_eps):
            status = CollectorStatus.FAILED
            diag_code = "ENDPOINTS_UNAVAILABLE"
            all_bad = rejected_eps + failed_eps + unsupported_eps
            msg = f"All queried FMC endpoints failed, were rejected, or unsupported: {', '.join(all_bad)}."
        elif records_fetched == 0:
            status = CollectorStatus.SUCCESS
            diag_code = "QUERY_EMPTY_ZERO_SOURCE"
            msg = f"Cisco FMC returned zero events for requested time window ({start_dt.isoformat()} to {end_dt.isoformat()})."
        elif records_ignored > 0 and records_parsed == 0:
            status = CollectorStatus.SUCCESS
            diag_code = "QUERY_EMPTY_FILTERED"
            msg = f"Cisco FMC returned {records_fetched} records but all were outside requested time range."
        elif records_malformed > 0 and records_parsed == 0:
            status = CollectorStatus.FAILED
            diag_code = "PARSE_ERROR"
            msg = f"Cisco FMC returned {records_fetched} records but none could be parsed."
        else:
            status = CollectorStatus.SUCCESS
            diag_code = "QUERY_EMPTY_ZERO_SOURCE"
            msg = "Zero events found."

        if status == CollectorStatus.WARNING:
            diagnostic_status = DiagnosticStatus.PARTIAL
        elif status == CollectorStatus.SUCCESS:
            diagnostic_status = DiagnosticStatus.SUCCESS
        else:
            diagnostic_status = DiagnosticStatus.FAILED

        diagnostic = CollectorDiagnostic(
            collector_id="cisco_fmc",
            device_name=self.device_name,
            canonical_entity="cisco_fmc",
            stage=DiagnosticStage.COMPLETE,
            status=diagnostic_status,
            diagnostic_code=diag_code,
            message=msg,
            requested_time_range=requested_time_range,
            observed_time_range=observed_time_range,
            transport="REST_API",
            source_queried=f"FMC domain {domain} (intrusion, sec_intel, audit)",
            records_fetched=records_fetched,
            records_parsed=records_parsed,
            records_ignored=records_ignored,
            records_malformed=records_malformed,
            pagination={"pages_retrieved": pages_retrieved, "has_more": has_more},
        )

        return CollectorResult(
            device_name=self.device_name,
            status=status,
            events=events,
            diagnostic=diagnostic,
            records_fetched=records_fetched,
            records_parsed=records_parsed,
            records_ignored=records_ignored,
            records_malformed=records_malformed,
        )
