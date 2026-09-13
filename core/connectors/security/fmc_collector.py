import hashlib
import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
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
        estreamer_jsonl_path: Optional[str] = None,
        timeout: int = 120,
    ):
        super().__init__(device_name="Cisco FMC", timeout=timeout, collector_id="cisco_fmc")
        self.host = host or os.getenv("MNE_FMC_HOST", "172.23.70.77")
        self.username = username or os.getenv("MNE_FMC_USERNAME", "admin")
        self.password = password or os.getenv("MNE_FMC_PASSWORD", "")
        self.domain_uuid = domain_uuid or os.getenv("MNE_FMC_DOMAIN_UUID", "")
        self.estreamer_jsonl_path = estreamer_jsonl_path or os.getenv("MNE_FMC_ESTREAMER_JSONL_PATH", "")
        self.estreamer_health_path = os.getenv("MNE_FMC_ESTREAMER_HEALTH_PATH", "")

    def _estreamer_health_file(self) -> Optional[Path]:
        """Return the receiver health file beside the configured JSONL spool."""
        if not self.estreamer_jsonl_path:
            return None
        configured = Path(self.estreamer_jsonl_path)
        if configured.is_dir():
            return configured / "receiver-health.json"
        if self.estreamer_health_path:
            return Path(self.estreamer_health_path)
        return configured.with_name("receiver-health.json")

    def _estreamer_health_ready(self) -> Optional[Dict[str, Any]]:
        """Accept an empty threat window only when the local receiver is fresh.

        An empty spool is not evidence of a healthy feed by itself.  The
        receiver writes a short-lived heartbeat independently of event volume,
        allowing a real zero-event window to be distinguished from a stopped
        listener or broken forwarding path.
        """
        health_file = self._estreamer_health_file()
        if health_file is None or not health_file.is_file():
            return None
        try:
            payload = json.loads(health_file.read_text(encoding="utf-8"))
            if not isinstance(payload, dict) or payload.get("status") != "LISTENING":
                return None
            stamp = payload.get("last_seen_utc") or payload.get("started_at_utc")
            if not isinstance(stamp, str):
                return None
            observed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
            if observed.tzinfo is None:
                observed = observed.replace(tzinfo=timezone.utc)
            age = datetime.now(timezone.utc) - observed.astimezone(timezone.utc)
            if age < timedelta(minutes=-1) or age > timedelta(minutes=3):
                return None
            return payload
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return None

    def _estreamer_spool_paths(self) -> List[Path]:
        """Resolve an active spool plus bounded JSONL rotations.

        The configured value may be the active JSONL file or its containing
        directory. Rotation keeps the writer's active filename stable while
        the collector reads archived files as well, so a 24-hour report does
        not silently lose events at a rotation boundary.
        """
        configured = Path(self.estreamer_jsonl_path)
        if configured.is_dir():
            paths = sorted(configured.glob("events*.jsonl"), key=lambda item: item.name)
            if not paths:
                raise FileNotFoundError("Configured FMC eStreamer JSONL directory contains no JSONL spool files.")
            return paths

        parent = configured.parent
        if configured.is_file():
            paths = [configured]
        else:
            paths = []
        if parent.is_dir():
            suffix = configured.suffix or ".jsonl"
            stem = configured.stem
            paths.extend(parent.glob(f"{stem}-*{suffix}"))
        unique = {path.resolve(): path for path in paths}
        if not unique:
            raise FileNotFoundError("Configured FMC eStreamer JSONL spool does not exist.")
        return sorted(unique.values(), key=lambda item: item.name)

    def _load_estreamer_spool(self) -> List[Dict[str, Any]]:
        """Load normalized eStreamer JSON/JSONL produced by a governed client.

        The collector deliberately does not implement FMC certificate enrollment
        or the binary eStreamer transport.  Those are appliance-side operations.
        This local spool boundary lets an approved eStreamer client provide the
        actual intrusion stream without pretending unsupported REST resources are
        complete threat telemetry.
        """
        if not self.estreamer_jsonl_path:
            return []
        items: List[Dict[str, Any]] = []
        for path in self._estreamer_spool_paths():
            raw = path.read_text(encoding="utf-8-sig")
            if not raw.strip():
                continue
            if raw.lstrip().startswith("["):
                payload = json.loads(raw)
                if not isinstance(payload, list):
                    raise ValueError("FMC eStreamer spool JSON must be an array or JSON Lines.")
                items.extend(item for item in payload if isinstance(item, dict))
                continue
            for line_number, line in enumerate(raw.splitlines(), start=1):
                if not line.strip():
                    continue
                item = json.loads(line)
                if not isinstance(item, dict):
                    raise ValueError(f"FMC eStreamer spool line {line_number} is not a JSON object.")
                items.append(item)
        return items

    @staticmethod
    def _unwrap_estreamer_event(item: Dict[str, Any]) -> Tuple[Dict[str, Any], Optional[str]]:
        """Return the FQE payload when a client wraps it by event type."""
        for event_type in ("IntrusionEvent", "ConnectionEvent", "FileEvent", "MalwareEvent"):
            payload = item.get(event_type)
            if isinstance(payload, dict):
                return payload, event_type
        return item, None

    @staticmethod
    def _first_value(item: Dict[str, Any], *names: str) -> Any:
        """Look up Cisco REST/FQE aliases without making field case significant."""
        folded = {str(key).casefold(): value for key, value in item.items()}
        for name in names:
            value = folded.get(name.casefold())
            if value is not None and value != "":
                return value
        return None

    def parse_fmc_event(self, item: Dict[str, Any]) -> NormalizedSecurityEvent:
        """Parses a Cisco FMC intrusion or security intelligence JSON record."""
        original_item = item
        item, wrapped_event_type = self._unwrap_estreamer_event(item)
        event_id = str(
            self._first_value(item, "id", "eventId", "EventID", "ConnectionID")
            or hashlib.md5(str(original_item).encode()).hexdigest()[:10]
        )
        src_ip = self._first_value(item, "sourceIp", "attackerIp", "InitiatorIP", "SrcIP", "SendingIP")
        dst_ip = self._first_value(item, "destinationIp", "targetIp", "ResponderIP", "DstIP", "ReceivingIP")
        rule_msg = str(
            self._first_value(
                item,
                "ruleMessage",
                "message",
                "IntrusionRuleMessage",
                "ThreatName",
                "AC_RuleReason",
                "FileName",
                "EventType",
            )
            or "Cisco Secure Firewall Event"
        )
        action_raw = str(
            self._first_value(item, "action", "AC_RuleAction", "InlineResult", "SHA_Disposition") or ""
        ).lower()

        if any(marker in action_raw for marker in ("block", "drop", "deny", "reject")):
            action = "BLOCKED"
        elif any(marker in action_raw for marker in ("allow", "permit", "passed", "trust", "fastpath")):
            action = "ALLOWED"
        else:
            action = "ALERT"

        ts = self._first_value(
            item,
            "timestamp",
            "time",
            "eventTime",
            "EventSecond",
            "FirstPacketSecond",
        )
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
                    parsed_time = datetime.fromisoformat(clean_ts)
                    event_time = (
                        parsed_time.replace(tzinfo=timezone.utc)
                        if parsed_time.tzinfo is None
                        else parsed_time.astimezone(timezone.utc)
                    )
            except Exception:
                pass

        category = ThreatCategory.INTRUSION
        rule_lower = rule_msg.lower()
        is_audit_record = bool(item.get("auditId") or item.get("subSystem") or item.get("subsystem"))
        is_successful_audit = is_audit_record and (
            " ok (200)" in rule_lower
            or "request has succeeded" in rule_lower
            or "login success" in rule_lower
            or "new session source ip" in rule_lower
        )
        is_failed_auth = is_audit_record and any(
            marker in rule_lower
            for marker in ("login fail", "authentication fail", "invalid credential", "unauthorized")
        )
        is_change_audit = is_audit_record and (
            rule_lower.startswith(("post ", "put ", "delete ", "patch "))
            or any(marker in rule_lower for marker in ("configuration created", "configuration modified", "configuration deleted"))
        )

        if is_failed_auth:
            category = ThreatCategory.BRUTE_FORCE
            action = "ALERT"
        elif is_change_audit:
            category = ThreatCategory.PRIVILEGE_CHANGE
            action = "ALLOWED"
        elif is_successful_audit or is_audit_record:
            category = ThreatCategory.SYSTEM_HEALTH
            action = "ALLOWED" if is_successful_audit else "ALERT"
            rule_msg = f"FMC Audit: {rule_msg}"
        elif "login" in rule_lower or "session" in rule_lower or "authentication" in rule_lower:
            category = ThreatCategory.PRIVILEGE_CHANGE
        elif (
            wrapped_event_type in ("FileEvent", "MalwareEvent")
            or self._first_value(item, "SHA_Disposition", "ThreatName", "FileName") is not None
            or "malware" in rule_lower
            or "virus" in rule_lower
            or "trojan" in rule_lower
        ):
            category = ThreatCategory.MALWARE
        elif "c2" in rule_lower or "botnet" in rule_lower or "scan" in rule_lower:
            category = ThreatCategory.INTRUSION

        # Enriched metadata preserving managed device identity and policies
        metadata = dict(original_item)
        classification = self._first_value(item, "classification", "Classification")
        impact = self._first_value(item, "impact", "Impact", "ImpactFlag")
        managed_device = self._first_value(item, "deviceName", "sensor", "Device", "DeviceIP")
        if classification is not None:
            metadata["classification"] = classification
        if impact is not None:
            metadata["impact"] = impact
        if managed_device is not None:
            metadata["managed_device"] = managed_device
        if wrapped_event_type:
            metadata["estreamer_event_type"] = wrapped_event_type

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
        threat_events_observed = False
        seen_event_ids: set[str] = set()

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

        endpoint_diagnostics["estreamer"] = {
            "endpoint": "LOCAL_JSONL_SPOOL",
            "status": "NOT_CONFIGURED" if not self.estreamer_jsonl_path else "NOT_ATTEMPTED",
            "status_code": None,
            "records_fetched": 0,
            "error": None,
        }

        # eStreamer is FMC's supported threat-event stream.  Consume a local,
        # normalized spool when an approved client has been configured.
        if self.estreamer_jsonl_path and not request.is_cancelled():
            try:
                stream_items = self._load_estreamer_spool()
                health = self._estreamer_health_ready()
                endpoint_diagnostics["estreamer"]["status"] = (
                    "SUCCESS" if stream_items else "READY_EMPTY" if health else "EMPTY"
                )
                if health:
                    endpoint_diagnostics["estreamer"]["health"] = {
                        "status": health.get("status"),
                        "last_seen_utc": health.get("last_seen_utc"),
                        "accepted_events": health.get("accepted_events", 0),
                    }
                endpoint_diagnostics["estreamer"]["records_fetched"] = len(stream_items)
                records_fetched += len(stream_items)
                pages_retrieved += 1
                for item in stream_items:
                    if len(events) >= request.max_records:
                        has_more = True
                        break
                    try:
                        parsed = self.parse_fmc_event(item)
                        if parsed.event_id in seen_event_ids:
                            continue
                        seen_event_ids.add(parsed.event_id)
                        parsed.metadata["transport"] = "ESTREAMER_JSONL_SPOOL"
                        if request.categories and parsed.category.value not in request.categories and parsed.category not in request.categories:
                            records_ignored += 1
                        elif start_dt <= parsed.timestamp <= end_dt:
                            events.append(parsed)
                            records_parsed += 1
                            threat_events_observed = True
                        else:
                            records_ignored += 1
                    except Exception:
                        records_malformed += 1
            except Exception as stream_err:
                endpoint_diagnostics["estreamer"]["status"] = "FAILED"
                endpoint_diagnostics["estreamer"]["error"] = str(stream_err)

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
                                if parsed.event_id in seen_event_ids:
                                    continue
                                seen_event_ids.add(parsed.event_id)
                                if request.categories and parsed.category.value not in request.categories and parsed.category not in request.categories:
                                    records_ignored += 1
                                    continue
                                if start_dt <= parsed.timestamp <= end_dt:
                                    events.append(parsed)
                                    records_parsed += 1
                                    if ep_name in {"intrusionevents", "securityintelligenceevents"}:
                                        threat_events_observed = True
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
        threat_stream_available = endpoint_diagnostics["estreamer"]["status"] in {"SUCCESS", "READY_EMPTY"} or any(
            endpoint_diagnostics[name]["status"] == "SUCCESS"
            for name in ("intrusionevents", "securityintelligenceevents")
        )

        if has_more:
            status = CollectorStatus.WARNING
            diag_code = "TRUNCATED_AT_LIMIT"
            msg = f"Cisco FMC collection reached the configured limit; {len(events)} events were retained and coverage is partial."
        elif len(events) > 0:
            if not threat_stream_available:
                status = CollectorStatus.WARNING
                diag_code = "THREAT_STREAMS_UNAVAILABLE"
                msg = (
                    f"Retrieved {len(events)} FMC audit/operational events, but no usable intrusion threat stream was available. "
                    "Configure an approved eStreamer client and MNE_FMC_ESTREAMER_JSONL_PATH."
                )
            elif rejected_eps or failed_eps:
                status = CollectorStatus.WARNING
                diag_code = "PARTIAL_SUCCESS"
                msg = (
                    f"Retrieved {len(events)} security events from Cisco FMC (domain: {domain}). "
                    f"Endpoints rejected/failed: {', '.join(rejected_eps + failed_eps)}."
                )
            elif not threat_events_observed and endpoint_diagnostics["estreamer"]["status"] == "READY_EMPTY":
                status = CollectorStatus.SUCCESS
                diag_code = "OK"
                msg = (
                    f"Retrieved {len(events)} FMC audit/operational events from domain {domain}; "
                    "the local threat receiver heartbeat is healthy and no in-window intrusion, "
                    "malware, or Security Intelligence events were observed."
                )
            else:
                status = CollectorStatus.SUCCESS
                diag_code = "OK"
                msg = f"Retrieved {len(events)} security events from Cisco FMC (domain: {domain}) with usable threat-stream coverage."
        elif len(successful_eps) == 0 and (rejected_eps or failed_eps or unsupported_eps):
            status = CollectorStatus.FAILED
            diag_code = "ENDPOINTS_UNAVAILABLE"
            all_bad = rejected_eps + failed_eps + unsupported_eps
            msg = f"All queried FMC endpoints failed, were rejected, or unsupported: {', '.join(all_bad)}."
        elif not threat_stream_available:
            status = CollectorStatus.WARNING
            diag_code = "THREAT_STREAMS_UNAVAILABLE"
            msg = (
                "FMC audit/operational records were queried, but no usable intrusion threat stream was available. "
                "Configure an approved eStreamer client and MNE_FMC_ESTREAMER_JSONL_PATH."
            )
        elif records_fetched == 0:
            status = CollectorStatus.SUCCESS
            diag_code = "QUERY_EMPTY_ZERO_SOURCE"
            msg = f"Cisco FMC returned zero events for requested time window ({start_dt.isoformat()} to {end_dt.isoformat()})."
        elif records_ignored > 0 and records_parsed == 0:
            status = CollectorStatus.WARNING
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
            transport="REST_API+ESTREAMER_SPOOL" if self.estreamer_jsonl_path else "REST_API",
            source_queried=f"FMC domain {domain} (REST audit; intrusion/sec_intel REST capability probe; optional eStreamer spool)",
            records_fetched=records_fetched,
            records_parsed=records_parsed,
            records_ignored=records_ignored,
            records_malformed=records_malformed,
            pagination={
                "pages_retrieved": pages_retrieved,
                "has_more": has_more,
                "endpoint_diagnostics": endpoint_diagnostics,
                "threat_stream_available": threat_stream_available,
            },
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
