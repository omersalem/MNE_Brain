"""
MNE_Brain Release 2 — FortiEDR Cloud Central Manager Security Collector.
Connects via HTTPS/TLS to the FortiEDR Cloud Central Manager console
(https://fortiedrconnectil.console.ensilo.com) using authenticated session & DWR protocols,
collects unhandled endpoint threats, collector health, infrastructure status,
and communicating application vulnerabilities, and normalizes them into NormalizedSecurityEvent records.
"""

import hashlib
import json
import logging
import os
import random
import re
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
import requests
import urllib3

load_dotenv()
urllib3.disable_warnings()

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


def _tokenify(num: float) -> str:
    chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    res = ""
    n = int(num)
    while n > 0:
        res = chars[n % len(chars)] + res
        n //= len(chars)
    return res or "0"


def _parse_dwr_reply(text: str) -> Any:
    """Extracts and deserializes payload from a Direct Web Remoting (DWR) JavaScript response."""
    m_quoted = re.search(
        r'handleCallback\s*\(\s*["\'][^"\']*["\']\s*,\s*["\'][^"\']*["\']\s*,\s*"(.*?)"\s*\);',
        text,
        re.DOTALL | re.IGNORECASE,
    )
    if m_quoted:
        raw_json_str = m_quoted.group(1).encode().decode("unicode_escape")
        try:
            return json.loads(raw_json_str)
        except Exception:
            return raw_json_str
    m_raw = re.search(
        r'handleCallback\s*\(\s*["\'][^"\']*["\']\s*,\s*["\'][^"\']*["\']\s*,\s*(\[.*?\]|\{.*?\})\s*\);',
        text,
        re.DOTALL | re.IGNORECASE,
    )
    if m_raw:
        try:
            return json.loads(m_raw.group(1))
        except Exception:
            return m_raw.group(1)
    m_exc = re.search(r'handle(?:Batch)?Exception\s*\(\s*(\{[^}]+\})\s*\)', text, re.IGNORECASE)
    if m_exc:
        try:
            return json.loads(m_exc.group(1))
        except Exception:
            return {"error": m_exc.group(1)}
    return text


class FortiEDRSecurityCollector(BaseSecurityCollector):
    """Security log & telemetry collector for FortiEDR Cloud Central Manager."""

    def __init__(
        self,
        host: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        organization: Optional[str] = None,
        timeout: int = 30,
        collector_id: str = "fortiedr",
    ):
        super().__init__(device_name="FortiEDR", timeout=timeout, collector_id=collector_id)
        self.host = host or os.getenv("MNE_FORTIEDR_HOST", "fortiedrconnectil.console.ensilo.com")
        self.username = username or os.getenv("MNE_FORTIEDR_USERNAME", "omersalem")
        self.password = password or os.getenv("MNE_FORTIEDR_PASSWORD", "")
        self.organization = organization or os.getenv("MNE_FORTIEDR_ORGANIZATION", "MNE")
        self.account_id: int = 11394210

    def _login(self, session: requests.Session) -> Tuple[bool, Optional[str], Optional[int]]:
        """Authenticates with Central Manager console using multi-tenant credentials."""
        login_url = f"https://{self.host}/login"
        data = {
            "username": self.username,
            "password": self.password,
            "account": self.organization,
        }
        try:
            resp = session.post(
                login_url,
                data=data,
                allow_redirects=False,
                verify=False,
                timeout=self.timeout,
            )
        except Exception as exc:
            raise ConnectionError(f"Failed to connect to FortiEDR console at {self.host}: {exc}") from exc

        if resp.status_code not in (200, 302, 303):
            raise PermissionError(f"FortiEDR authentication failed: HTTP {resp.status_code}")

        jsessionid = session.cookies.get("JSESSIONID")
        if not jsessionid and "Set-Cookie" in resp.headers:
            m = re.search(r"JSESSIONID=([^;]+)", resp.headers["Set-Cookie"])
            if m:
                jsessionid = m.group(1)
                session.cookies.set("JSESSIONID", jsessionid)

        if not jsessionid:
            raise PermissionError("FortiEDR authentication succeeded but no JSESSIONID cookie was returned.")

        return True, jsessionid, resp.status_code

    def _call_dwr(
        self,
        session: requests.Session,
        service: str,
        method: str,
        params: Optional[List[Tuple[str, Any]]] = None,
        script_session_id: str = "",
    ) -> Any:
        """Executes a plaincall DWR RPC invocation against Central Manager backend."""
        url = f"https://{self.host}/dwr/call/plaincall/{service}.{method}.dwr"
        jsessionid = session.cookies.get("JSESSIONID", "")
        body_lines = [
            "callCount=1",
            "page=%2F",
            f"httpSessionId={jsessionid}",
            f"scriptSessionId={script_session_id}",
            f"c0-scriptName={service}",
            f"c0-methodName={method}",
            "c0-id=0",
        ]
        if params:
            for idx, (p_type, p_val) in enumerate(params):
                if p_type == "string":
                    body_lines.append(f"c0-param{idx}=string:{p_val}")
                elif p_type == "number":
                    body_lines.append(f"c0-param{idx}=number:{p_val}")
                elif p_type == "boolean":
                    body_lines.append(f"c0-param{idx}=boolean:{str(p_val).lower()}")
                elif p_type == "null":
                    body_lines.append(f"c0-param{idx}=null:null")
        body_lines.extend([
            "batchId=0",
            "instanceId=0",
        ])
        data = "\n".join(body_lines) + "\n"
        headers = {
            "Content-Type": "text/plain",
            "Referer": f"https://{self.host}/",
            "Origin": f"https://{self.host}",
        }
        resp = session.post(url, data=data, headers=headers, verify=False, timeout=self.timeout)
        if resp.status_code != 200:
            raise ConnectionError(f"DWR call {service}.{method} returned HTTP {resp.status_code}")
        return _parse_dwr_reply(resp.text)

    def parse_security_event(self, item: Dict[str, Any]) -> NormalizedSecurityEvent:
        """Normalizes a FortiEDR unhandled or handled threat event."""
        ev_id = str(item.get("id") or hashlib.md5(str(item).encode()).hexdigest()[:10])
        classification = str(item.get("classification") or "Malicious")
        org = str(item.get("organization") or self.organization)

        category = ThreatCategory.MALWARE
        action = "BLOCKED"
        if classification.lower() in ("malicious", "classificationmalicious"):
            category = ThreatCategory.MALWARE
            action = "BLOCKED"
        elif classification.lower() in ("suspicious", "classificationsuspicious"):
            category = ThreatCategory.INTRUSION
            action = "ALERT"
        elif classification.lower() in ("inconclusive", "classificationinconclusive"):
            category = ThreatCategory.ANOMALY
            action = "ALERT"
        elif classification.lower() in (
            "safe",
            "classificationsafe",
            "likely safe",
            "classificationprobablygood",
            "good",
            "classificationgood",
        ):
            category = ThreatCategory.ANOMALY
            action = "ALLOWED"

        last_seen = item.get("lastSeen")
        event_time = datetime.now(timezone.utc)
        if last_seen and isinstance(last_seen, str):
            timezone_name = os.getenv("MNE_FORTIEDR_SOURCE_TIMEZONE", "Africa/Cairo")
            try:
                source_timezone = ZoneInfo(timezone_name)
            except ZoneInfoNotFoundError:
                logger.warning(
                    "Unknown MNE_FORTIEDR_SOURCE_TIMEZONE=%s; using UTC and marking timestamp fallback.",
                    timezone_name,
                )
                source_timezone = timezone.utc
            for fmt in ("%d-%b-%Y, %H:%M:%S", "%d-%b-%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
                try:
                    event_time = (
                        datetime.strptime(last_seen.strip(), fmt)
                        .replace(tzinfo=source_timezone)
                        .astimezone(timezone.utc)
                    )
                    break
                except ValueError:
                    pass

        threat_title = f"FortiEDR {classification} Endpoint Threat #{ev_id}"
        return NormalizedSecurityEvent(
            event_id=f"edr-{ev_id}",
            timestamp=event_time,
            source_device="FortiEDR",
            category=category,
            threat_name=threat_title,
            attacker_ip=item.get("ip") or None,
            target=item.get("device") or f"MNE-Endpoint ({org})",
            action_taken=action,
            count=1,
            raw_snippet=json.dumps(item, ensure_ascii=False)[:300],
            metadata={
                "canonical_entity": "edr-fortiedr-cloud-01",
                "collector_id": self.collector_id,
                "fortiedr_id": ev_id,
                "classification": classification,
                "organization": org,
                "last_seen": last_seen,
                "source_timezone": timezone_name if last_seen else None,
            },
        )

    def _fetch_logs_internal(self, hours_back: int) -> List[NormalizedSecurityEvent]:
        req = CollectorRequest(hours_back=hours_back)
        return self._fetch_logs_with_request(req).events

    def _fetch_logs_with_request(self, request: CollectorRequest) -> CollectorResult:
        """Executes multi-endpoint collection across FortiEDR Central Manager with rich diagnostics."""
        if not self.password:
            raise ValueError("MNE_FORTIEDR_PASSWORD is not configured in .env.")

        start_dt, end_dt = request.get_time_window()
        # Health and dashboard responses are point-in-time observations.  Use
        # the review window end as their observation timestamp so a long live
        # run cannot create events after its own fixed window and be reported
        # as a false coverage gap.
        observation_time = end_dt
        requested_time_range = {
            "start": start_dt.isoformat(),
            "end": end_dt.isoformat(),
            "hours_back": request.hours_back,
        }

        session = requests.Session()
        events: List[NormalizedSecurityEvent] = []
        endpoint_diagnostics: Dict[str, Dict[str, Any]] = {}
        records_fetched = 0
        records_parsed = 0
        records_ignored = 0
        records_malformed = 0

        # STAGE 1 & 2: Connection & Authentication
        diag = CollectorDiagnostic(
            collector_id=self.collector_id,
            canonical_entity="edr-fortiedr-cloud-01",
            device_name=self.device_name,
            stage=DiagnosticStage.CONNECTION,
            status=DiagnosticStatus.RUNNING,
            source_queried=f"https://{self.host}/login",
            requested_time_range=requested_time_range,
        )

        try:
            self._login(session)
            diag.stage = DiagnosticStage.AUTHENTICATION
            diag.status = DiagnosticStatus.SUCCESS
        except PermissionError as p_err:
            diag.stage = DiagnosticStage.AUTHENTICATION
            diag.status = DiagnosticStatus.FAILED
            diag.message = str(p_err)
            diag.diagnostic_code = "AUTH_FAILED"
            return CollectorResult(
                device_name=self.device_name,
                status=CollectorStatus.FAILED,
                error_message=str(p_err),
                diagnostic=diag,
            )
        except Exception as c_err:
            diag.stage = DiagnosticStage.CONNECTION
            diag.status = DiagnosticStatus.FAILED
            diag.message = str(c_err)
            diag.diagnostic_code = "CONNECTION_ERROR"
            return CollectorResult(
                device_name=self.device_name,
                status=CollectorStatus.FAILED,
                error_message=str(c_err),
                diagnostic=diag,
            )

        # STAGE 3: Query Telemetry
        diag.stage = DiagnosticStage.QUERY
        diag.status = DiagnosticStatus.RUNNING

        page_id = f"{_tokenify(time.time() * 1000)}-{_tokenify(random.randint(100000, 999999999))}"
        jsess = session.cookies.get("JSESSIONID", "")
        script_sess_id = f"{jsess}/{page_id}"

        # Discover Account ID if needed
        try:
            acct_data = self._call_dwr(session, "AdminService", "getCurrentAccount", script_session_id=script_sess_id)
            if isinstance(acct_data, dict) and acct_data.get("id"):
                self.account_id = int(acct_data["id"])
        except Exception:
            pass

        # 1. Active Threat Events Query
        try:
            ev_data = self._call_dwr(session, "EventsPageBackingService", "getEventsTabIndicatorInfo", script_session_id=script_sess_id)
            new_events = (ev_data.get("newEvents", []) if isinstance(ev_data, dict) else [])
            endpoint_diagnostics["EventsPageBackingService.getEventsTabIndicatorInfo"] = {
                "status": "SUCCESS",
                "records_fetched": len(new_events),
                "total_unhandled_count": ev_data.get("newEventsCount", len(new_events)) if isinstance(ev_data, dict) else 0,
            }
            records_fetched += len(new_events)
            for item in new_events:
                if len(events) >= request.max_records:
                    break
                try:
                    norm_ev = self.parse_security_event(item)
                    if not item.get("lastSeen"):
                        norm_ev.timestamp = observation_time
                    # Central Manager's indicator endpoint returns active
                    # records, not a bounded 24-hour query.  Filter its
                    # historical records here so the review service does not
                    # mislabel expected out-of-window data as incomplete
                    # coverage.
                    if start_dt <= norm_ev.timestamp <= end_dt:
                        events.append(norm_ev)
                        records_parsed += 1
                    else:
                        records_ignored += 1
                except Exception as parse_err:
                    logger.debug("Failed parsing FortiEDR event: %s", parse_err)
                    records_malformed += 1
        except Exception as exc:
            endpoint_diagnostics["EventsPageBackingService.getEventsTabIndicatorInfo"] = {
                "status": "FAILED",
                "error": str(exc),
                "records_fetched": 0,
            }

        # 2. Endpoint Collector Health & Fleet Status
        try:
            health_data = self._call_dwr(
                session,
                "ExecutiveSummaryReportPageBackingService",
                "getAgentHealthData",
                params=[("number", self.account_id)],
                script_session_id=script_sess_id,
            )
            endpoint_diagnostics["ExecutiveSummaryReportPageBackingService.getAgentHealthData"] = {
                "status": "SUCCESS",
                "records_fetched": len(health_data) if isinstance(health_data, list) else 0,
            }
            if isinstance(health_data, list):
                records_fetched += len(health_data)
                for h_item in health_data:
                    name = h_item.get("name", "")
                    count_val = int(h_item.get(name, 0))
                    if count_val > 0 and name in ("Degraded", "Down", "Unmanaged"):
                        cat = ThreatCategory.ANOMALY if name == "Unmanaged" else ThreatCategory.SYSTEM_HEALTH
                        act = "ALERT" if name != "Unmanaged" else "ALLOWED"
                        sev_note = f"FortiEDR Endpoint Fleet Health: {count_val} {name} Collectors"
                        events.append(
                            NormalizedSecurityEvent(
                                event_id=f"edr-fleet-{name.lower()}",
                                timestamp=observation_time,
                                source_device="FortiEDR",
                                category=cat,
                                threat_name=sev_note,
                                attacker_ip=None,
                                target="MNE Endpoint Fleet",
                                action_taken=act,
                                count=count_val,
                                raw_snippet=json.dumps(h_item)[:300],
                                metadata={
                                    "canonical_entity": "edr-fortiedr-cloud-01",
                                    "collector_id": self.collector_id,
                                    "state": name,
                                    "affected_count": count_val,
                                },
                            )
                        )
                        records_parsed += 1
        except Exception as exc:
            endpoint_diagnostics["ExecutiveSummaryReportPageBackingService.getAgentHealthData"] = {
                "status": "FAILED",
                "error": str(exc),
                "records_fetched": 0,
            }

        # 3. Backend Cloud Components Health (Cores, Repositories, Aggregators)
        try:
            comp_data = self._call_dwr(
                session,
                "DashboardPageBackingService",
                "getDevicesHealthChartData",
                script_session_id=script_sess_id,
            )
            endpoint_diagnostics["DashboardPageBackingService.getDevicesHealthChartData"] = {
                "status": "SUCCESS",
                "records_fetched": len(comp_data) if isinstance(comp_data, list) else 0,
            }
            if isinstance(comp_data, list):
                records_fetched += len(comp_data)
                for comp in comp_data:
                    c_name = comp.get("name", "Component")
                    down_count = int(comp.get("Down", 0))
                    degraded_count = int(comp.get("Degraded", 0))
                    enabled_count = int(comp.get("Enabled", 0))
                    if down_count > 0 or degraded_count > 0:
                        events.append(
                            NormalizedSecurityEvent(
                                event_id=f"edr-comp-{c_name.lower()}",
                                timestamp=observation_time,
                                source_device="FortiEDR",
                                category=ThreatCategory.SYSTEM_HEALTH,
                                threat_name=f"FortiEDR Cloud {c_name} Degraded / Offline ({down_count} Down, {degraded_count} Degraded)",
                                attacker_ip=None,
                                target=f"FortiEDR Cloud {c_name}",
                                action_taken="ALERT",
                                count=down_count + degraded_count,
                                raw_snippet=json.dumps(comp)[:300],
                                metadata={
                                    "canonical_entity": "edr-fortiedr-cloud-01",
                                    "collector_id": self.collector_id,
                                    "component": c_name,
                                    "enabled": enabled_count,
                                    "down": down_count,
                                },
                            )
                        )
                        records_parsed += 1
        except Exception as exc:
            endpoint_diagnostics["DashboardPageBackingService.getDevicesHealthChartData"] = {
                "status": "FAILED",
                "error": str(exc),
                "records_fetched": 0,
            }

        # 4. Unhandled Communicating Applications (Vulnerabilities & Risk)
        try:
            vuln_data = self._call_dwr(
                session,
                "DashboardPageBackingService",
                "getUnhandledApplicationsChartData",
                script_session_id=script_sess_id,
            )
            if isinstance(vuln_data, dict):
                endpoint_diagnostics["DashboardPageBackingService.getUnhandledApplicationsChartData"] = {
                    "status": "SUCCESS",
                    "records_fetched": 1,
                    "data": vuln_data,
                }
                records_fetched += 1
                crit_vuln = int(vuln_data.get("Critical-vulnerability", 0))
                low_rep = int(vuln_data.get("Low-reputation", 0))
                if crit_vuln > 0:
                    events.append(
                        NormalizedSecurityEvent(
                            event_id="edr-apps-critical-cve",
                            timestamp=observation_time,
                            source_device="FortiEDR",
                            category=ThreatCategory.ANOMALY,
                            threat_name=f"Communicating Applications with Critical CVE Vulnerabilities ({crit_vuln} apps)",
                            attacker_ip=None,
                            target="MNE Network Applications",
                            action_taken="ALERT",
                            count=crit_vuln,
                            raw_snippet=json.dumps(vuln_data)[:300],
                            metadata={
                                "canonical_entity": "edr-fortiedr-cloud-01",
                                "collector_id": self.collector_id,
                                "category": "Critical Vulnerabilities",
                                "app_count": crit_vuln,
                            },
                        )
                    )
                    records_parsed += 1
                if low_rep > 0:
                    events.append(
                        NormalizedSecurityEvent(
                            event_id="edr-apps-low-reputation",
                            timestamp=observation_time,
                            source_device="FortiEDR",
                            category=ThreatCategory.ANOMALY,
                            threat_name=f"Low Reputation Communicating Software Detected ({low_rep} apps)",
                            attacker_ip=None,
                            target="MNE Network Applications",
                            action_taken="ALERT",
                            count=low_rep,
                            raw_snippet=json.dumps(vuln_data)[:300],
                            metadata={
                                "canonical_entity": "edr-fortiedr-cloud-01",
                                "collector_id": self.collector_id,
                                "category": "Low Reputation",
                                "app_count": low_rep,
                            },
                        )
                    )
                    records_parsed += 1
        except Exception as exc:
            endpoint_diagnostics["DashboardPageBackingService.getUnhandledApplicationsChartData"] = {
                "status": "FAILED",
                "error": str(exc),
                "records_fetched": 0,
            }

        failed_endpoints = [
            name for name, details in endpoint_diagnostics.items()
            if details.get("status") == "FAILED"
        ]
        diag.stage = DiagnosticStage.COMPLETE
        diag.status = DiagnosticStatus.PARTIAL if failed_endpoints else DiagnosticStatus.SUCCESS
        if failed_endpoints:
            diag.message = (
                f"Retrieved {len(events)} security telemetry events from FortiEDR Cloud Central Manager, "
                f"but endpoint checks failed: {', '.join(failed_endpoints)}."
            )
            diag.diagnostic_code = "PARTIAL_SUCCESS"
        elif events:
            diag.message = f"Retrieved {len(events)} security telemetry events from FortiEDR Cloud Central Manager."
            diag.diagnostic_code = "OK"
        else:
            diag.message = (
                "FortiEDR endpoints responded successfully and no in-window threat or health events were observed."
            )
            diag.diagnostic_code = "QUERY_EMPTY_ZERO_SOURCE"
        diag.records_fetched = records_fetched
        diag.records_parsed = records_parsed
        diag.records_ignored = records_ignored
        diag.records_malformed = records_malformed
        diag.endpoint_diagnostics = endpoint_diagnostics

        return CollectorResult(
            device_name=self.device_name,
            status=CollectorStatus.PARTIAL if failed_endpoints else CollectorStatus.SUCCESS,
            events=events,
            records_fetched=records_fetched,
            records_parsed=records_parsed,
            diagnostic=diag,
        )
