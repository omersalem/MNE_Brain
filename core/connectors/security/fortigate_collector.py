import hashlib
import logging
import os
import re
import time
from datetime import datetime, timezone
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


class FortiGateSecurityCollector(BaseSecurityCollector):
    """Collector for FortiGate Edge Firewall (172.23.70.4).

    Collects IPS attacks, Antivirus/malware detections, Web filter blocks,
    SSL-VPN failed logins, and system administrator events.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = 120,
    ):
        super().__init__(device_name="FortiGate", timeout=timeout, collector_id="fortigate_core")
        self.host = host or os.getenv("MNE_FORTIGATE_HOST", "172.23.70.4")
        self.username = username or os.getenv("MNE_FORTIGATE_USERNAME", "admin")
        self.password = password or os.getenv("MNE_FORTIGATE_PASSWORD", "")
        self.api_key = api_key or os.getenv("MNE_FORTIGATE_API_KEY", "")

    def parse_key_value_pairs(self, line: str) -> Dict[str, str]:
        """Parses standard FortiGate syslog key=value or key="value" pairs."""
        pattern = re.compile(r'([a-zA-Z0-9_]+)=(?:"([^"]*)"|(\S+))')
        data: Dict[str, str] = {}
        for match in pattern.finditer(line):
            key = match.group(1)
            value = match.group(2) if match.group(2) is not None else match.group(3)
            data[key] = value
        return data

    def parse_log_line(self, line: str) -> Optional[NormalizedSecurityEvent]:
        """Converts a raw FortiGate syslog string into a NormalizedSecurityEvent."""
        if not line or not line.strip() or ("date=" not in line and "logid=" not in line):
            return None

        fields = self.parse_key_value_pairs(line)
        if not fields:
            return None

        log_type = fields.get("type", "").lower()
        subtype = fields.get("subtype", "").lower()
        msg = fields.get("msg", "")
        action = fields.get("action", "").lower()
        attack = fields.get("attack", "")
        hostname = fields.get("hostname", "")
        virus = fields.get("virus", "")
        url = fields.get("url", "")

        category = ThreatCategory.ANOMALY
        threat_name = msg or attack or virus or "FortiGate Security Event"
        attacker_ip = fields.get("srcip") or fields.get("remip")
        target = fields.get("dstip") or fields.get("user") or fields.get("hostname")

        if subtype == "vpn" or "vpn login fail" in msg.lower() or "negotiation failure" in fields.get("reason", "").lower():
            category = ThreatCategory.BRUTE_FORCE
            threat_name = f"SSL-VPN Authentication Failure: {fields.get('user', 'unknown user')}"
            target = fields.get("user") or target
        elif log_type in ("ips", "utm") or subtype in ("ips", "signature") or attack:
            category = ThreatCategory.INTRUSION
            threat_name = f"IPS / Security Attack: {attack or msg}"
            if hostname:
                threat_name += f" ({hostname})"
        elif log_type == "virus" or subtype == "virus" or virus:
            category = ThreatCategory.MALWARE
            threat_name = f"Malware Detected: {virus or msg}"
        elif log_type == "webfilter" or subtype == "webfilter" or url:
            category = ThreatCategory.INTRUSION if ("malicious" in msg.lower() or "botnet" in msg.lower()) else ThreatCategory.ANOMALY
            threat_name = f"Web Filter Block: {url or msg}"
        elif subtype in ("system", "admin"):
            if "login" in msg.lower():
                category = ThreatCategory.PRIVILEGE_CHANGE
                threat_name = f"Admin Login Event: {msg}"
            else:
                category = ThreatCategory.SYSTEM_HEALTH
                threat_name = f"System Event: {msg}"

        # Action normalization
        if action in ("dropped", "block", "deny", "tunnel-down", "clear", "quarantine"):
            normalized_action = "DROPPED"
        elif action in ("passthrough", "allowed", "accept", "permit"):
            normalized_action = "ALLOWED"
        else:
            normalized_action = "ALERT"

        # Unique event ID hash
        raw_hash = hashlib.md5(f"{line}_{fields.get('date')}_{fields.get('time')}_{fields.get('eventtime')}".encode("utf-8")).hexdigest()[:12]
        event_id = f"fgt-{raw_hash}"

        event_time = datetime.now(timezone.utc)
        if "date" in fields and "time" in fields:
            try:
                dt_str = f"{fields['date']} {fields['time']}"
                event_time = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            except Exception:
                pass

        # Capture enriched metadata
        metadata = dict(fields)
        if "policyid" in fields:
            metadata["policy_id"] = fields["policyid"]
        if "vdom" in fields:
            metadata["vdom"] = fields["vdom"]
        if "srcintf" in fields:
            metadata["src_interface"] = fields["srcintf"]
        if "dstintf" in fields:
            metadata["dst_interface"] = fields["dstintf"]
        if "service" in fields:
            metadata["service"] = fields["service"]
        if "app" in fields:
            metadata["application"] = fields["app"]
        if "srcport" in fields:
            metadata["src_port"] = fields["srcport"]
        if "dstport" in fields:
            metadata["dst_port"] = fields["dstport"]
        if "devname" in fields:
            metadata["device_name"] = fields["devname"]

        source_pc = None
        for k in ("srcname", "src_host", "workstation_name"):
            v = fields.get(k)
            if v and isinstance(v, str) and v.strip() and v.strip().lower() not in ("unknown", "none", "n/a", "fortigate", "fortianalyzer"):
                if v.strip() not in (fields.get("devname", ""), "FortiGate", "FortiAnalyzer"):
                    source_pc = v.strip()
                    break

        hostname_role = fields.get("hostname_role")
        if subtype == "webfilter" or "webfilter" in line:
            if not hostname_role:
                hostname_role = "DESTINATION_TARGET"

        if not source_pc and fields.get("hostname") and hostname_role == "SOURCE_ENDPOINT":
            source_pc = fields["hostname"].strip()

        source_mac = fields.get("srcmac") or fields.get("mac") or fields.get("client_mac")
        if source_mac and source_mac.strip().lower() in ("unknown", "none", "00:00:00:00:00:00"):
            source_mac = None

        auth_user = None
        claimed_user = None
        target_account = None
        user_relation = None

        is_failed_vpn = (
            subtype == "vpn"
            or "login fail" in msg.lower()
            or "failed" in msg.lower()
            or "negotiation failure" in fields.get("reason", "").lower()
        )
        raw_user = fields.get("user") or fields.get("srcuser")

        if is_failed_vpn:
            claimed_user = raw_user
            target_account = raw_user
            user_relation = "CLAIMED_LOGIN_USERNAME"
        elif fields.get("authuser"):
            auth_user = fields.get("authuser")
            user_relation = "AUTHENTICATED_SOURCE_USER"
        elif fields.get("srcuser") and "auth" in raw_action.lower():
            auth_user = fields.get("srcuser")
            user_relation = "AUTHENTICATED_SOURCE_USER"
        elif raw_user:
            claimed_user = raw_user
            user_relation = "UNKNOWN_RELATION"

        return NormalizedSecurityEvent(
            event_id=event_id,
            timestamp=event_time,
            source_device="FortiGate",
            category=category,
            threat_name=threat_name,
            attacker_ip=attacker_ip,
            target=target,
            action_taken=normalized_action,
            count=1,
            raw_snippet=line.strip()[:300],
            metadata=metadata,
            attacker_hostname=source_pc,
            source_hostname=source_pc,
            attacker_mac=source_mac,
            authenticated_source_user=auth_user,
            claimed_login_username=claimed_user,
            target_account=target_account,
            username_relation=user_relation,
            hostname_role=hostname_role,
        )

    def _fetch_logs_with_request(self, request: CollectorRequest) -> CollectorResult:
        """Fetch logs from FortiGate using REST API with fallback to SSH, applying real time windows."""
        if not self.password and not self.api_key:
            raise ValueError("Neither MNE_FORTIGATE_PASSWORD nor MNE_FORTIGATE_API_KEY is configured in .env.")

        start_dt, end_dt = request.get_time_window()
        requested_time_range = {
            "start": start_dt.isoformat(),
            "end": end_dt.isoformat(),
            "hours_back": request.hours_back,
        }

        transport_used = "REST_API" if self.api_key else "SSH_CLI"
        fallback_occurred = False
        events: List[NormalizedSecurityEvent] = []
        records_fetched = 0
        records_parsed = 0
        records_ignored = 0
        records_malformed = 0
        pages_retrieved = 0
        has_more = False

        # Try REST API if api_key is available
        if self.api_key:
            try:
                import requests
                import urllib3
                urllib3.disable_warnings()

                endpoints = [
                    "/api/v2/log/disk/utm/ips",
                    "/api/v2/log/disk/utm/virus",
                    "/api/v2/log/disk/utm/webfilter",
                    "/api/v2/log/disk/event",
                ]
                headers = {"Authorization": f"Bearer {self.api_key}"}

                for ep in endpoints:
                    if len(events) >= request.max_records or request.is_cancelled():
                        break
                    pages_retrieved += 1
                    url = f"https://{self.host}{ep}"
                    params = {
                        "start": start_dt.strftime("%Y-%m-%d %H:%M:%S"),
                        "end": end_dt.strftime("%Y-%m-%d %H:%M:%S"),
                        "count": min(request.max_records - len(events), 100),
                    }
                    resp = requests.get(url, headers=headers, params=params, verify=False, timeout=self.timeout)
                    if resp.status_code == 200:
                        results = resp.json().get("results", [])
                        records_fetched += len(results)
                        for entry in results:
                            line_str = str(entry) if not isinstance(entry, dict) else " ".join(f'{k}="{v}"' for k, v in entry.items())
                            parsed = self.parse_log_line(line_str)
                            if parsed:
                                # Apply time range check
                                if start_dt <= parsed.timestamp <= end_dt:
                                    parsed.metadata["transport"] = "REST_API"
                                    events.append(parsed)
                                    records_parsed += 1
                                    if len(events) >= request.max_records:
                                        has_more = True
                                        break
                                else:
                                    records_ignored += 1
                            else:
                                records_malformed += 1
                    elif resp.status_code in (401, 403):
                        raise PermissionError(f"FortiGate REST authentication failed: HTTP {resp.status_code}")
                    else:
                        logger.warning("FortiGate REST endpoint %s returned HTTP %d", ep, resp.status_code)

            except Exception as rest_exc:
                if self.password:
                    logger.warning("FortiGate REST failed (%s); falling back to SSH.", rest_exc)
                    fallback_occurred = True
                    transport_used = "SSH_CLI"
                else:
                    raise rest_exc

        # If SSH is primary or used as fallback
        if transport_used == "SSH_CLI":
            import paramiko
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                client.connect(
                    hostname=self.host,
                    username=self.username,
                    password=self.password,
                    timeout=30,
                    look_for_keys=False,
                    allow_agent=False,
                )
                shell = client.invoke_shell()
                time.sleep(1)
                if shell.recv_ready():
                    shell.recv(4096)

                categories = [
                    ("IPS", "execute log filter category 4\n"),
                    ("System_VPN", "execute log filter category 1\n"),
                    ("Virus", "execute log filter category 2\n"),
                    ("WebFilter", "execute log filter category 3\n"),
                ]

                # Filter lines per view
                view_lines = min(max(request.max_records // 2, 50), 200)
                init_cmds = f"execute log filter device disk\nexecute log filter view-lines {view_lines}\n"
                shell.send(init_cmds)
                time.sleep(1)
                if shell.recv_ready():
                    shell.recv(4096)

                for cat_name, cmd in categories:
                    if len(events) >= request.max_records or request.is_cancelled():
                        break
                    pages_retrieved += 1
                    shell.send(cmd)
                    shell.send("execute log display\n")
                    time.sleep(2.0)

                    output = ""
                    start_wait = time.time()
                    while time.time() - start_wait < 3.0:
                        if shell.recv_ready():
                            chunk = shell.recv(65536).decode("utf-8", errors="ignore")
                            output += chunk
                        time.sleep(0.3)

                    lines = [ln.strip() for ln in output.splitlines() if ln.strip() and "date=" in ln]
                    records_fetched += len(lines)
                    for line in lines:
                        parsed = self.parse_log_line(line)
                        if parsed:
                            if start_dt <= parsed.timestamp <= end_dt:
                                parsed.metadata["transport"] = "SSH_CLI"
                                if fallback_occurred:
                                    parsed.metadata["transport_fallback"] = True
                                events.append(parsed)
                                records_parsed += 1
                                if len(events) >= request.max_records:
                                    has_more = True
                                    break
                            else:
                                records_ignored += 1
                        else:
                            records_malformed += 1

            finally:
                client.close()

        # Observed time range
        observed_time_range = None
        if events:
            timestamps = [e.timestamp for e in events if e.timestamp]
            if timestamps:
                observed_time_range = {
                    "oldest": min(timestamps).isoformat(),
                    "newest": max(timestamps).isoformat(),
                }

        # Status and diagnostic code
        if len(events) > 0:
            status = CollectorStatus.SUCCESS
            diag_code = "OK"
            msg = f"Retrieved {len(events)} security events from FortiGate via {transport_used}."
        elif records_fetched == 0:
            status = CollectorStatus.SUCCESS
            diag_code = "QUERY_EMPTY_ZERO_SOURCE"
            msg = f"FortiGate returned zero records for requested time window ({start_dt.isoformat()} to {end_dt.isoformat()})."
        elif records_ignored > 0 and records_parsed == 0:
            status = CollectorStatus.SUCCESS
            diag_code = "QUERY_EMPTY_FILTERED"
            msg = f"FortiGate returned {records_fetched} records but all were outside requested time range or filters."
        elif records_malformed > 0 and records_parsed == 0:
            status = CollectorStatus.FAILED
            diag_code = "PARSE_ERROR"
            msg = f"FortiGate returned {records_fetched} records but none could be parsed."
        else:
            status = CollectorStatus.SUCCESS
            diag_code = "QUERY_EMPTY_ZERO_SOURCE"
            msg = "Zero events found."

        diagnostic = CollectorDiagnostic(
            collector_id="fortigate_core",
            device_name=self.device_name,
            canonical_entity="fortigate_core",
            stage=DiagnosticStage.COMPLETE,
            status=DiagnosticStatus.SUCCESS if status == CollectorStatus.SUCCESS else DiagnosticStatus.FAILED,
            diagnostic_code=diag_code,
            message=msg,
            requested_time_range=requested_time_range,
            observed_time_range=observed_time_range,
            transport=transport_used,
            source_queried="disk log (event, ips, virus, webfilter)",
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
