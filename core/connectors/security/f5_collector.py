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


class F5SecurityCollector(BaseSecurityCollector):
    """Collector for F5 BIG-IP / WAF (172.23.70.89).

    Collects ASM/WAF attack events, virtual server/pool health failures,
    and SSL certificate expiration warnings.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: int = 120,
    ):
        super().__init__(device_name="F5 BIG-IP", timeout=timeout, collector_id="f5_bigip")
        self.host = host or os.getenv("MNE_F5_HOST", "172.23.70.89")
        self.username = username or os.getenv("MNE_F5_USERNAME", "admin")
        self.password = password or os.getenv("MNE_F5_PASSWORD", "")

    def _extract_timestamp(self, line: str) -> datetime:
        """Extracts source timestamp from syslog line, preserving it accurately."""
        # Syslog format: "Sep  6 03:15:22" or "Sep 06 03:15:22"
        ts_match = re.search(r'^([A-Za-z]{3}\s+\d+\s+\d{2}:\d{2}:\d{2})', line.strip())
        if ts_match:
            try:
                raw_ts = re.sub(r'\s+', ' ', ts_match.group(1))
                year = datetime.now(timezone.utc).year
                return datetime.strptime(f"{year} {raw_ts}", "%Y %b %d %H:%M:%S").replace(tzinfo=timezone.utc)
            except Exception:
                pass

        # ISO format: "2026-09-06T03:15:22"
        iso_match = re.search(r'(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2})', line)
        if iso_match:
            try:
                dt_str = iso_match.group(1).replace(" ", "T")
                return datetime.fromisoformat(dt_str).replace(tzinfo=timezone.utc)
            except Exception:
                pass

        return datetime.now(timezone.utc)

    def parse_asm_log_line(self, line: str) -> Optional[NormalizedSecurityEvent]:
        """Parses an F5 ASM attack log line (from /var/log/asm or remote syslog)."""
        if not line or not line.strip():
            return None

        event_time = self._extract_timestamp(line)

        # Pattern 1: Attack detected format
        if "Attack detected:" in line:
            client_ip_match = re.search(r'Client IP:\s*([0-9a-fA-F\.\:]+)', line)
            client_ip = client_ip_match.group(1) if client_ip_match else None

            violations_match = re.search(r'Violations:\s*([^,]+)', line)
            violations = violations_match.group(1).strip() if violations_match else "ASM Security Violation"

            action_match = re.search(r'Action:\s*([A-Za-z]+)', line)
            action_raw = action_match.group(1).upper() if action_match else "ALERT"
            action = "BLOCKED" if "BLOCK" in action_raw else "ALLOWED"

            url_match = re.search(r'URL:\s*(\S+)', line)
            target = url_match.group(1) if url_match else "Web Application"

            support_id_match = re.search(r'Support ID:\s*([0-9]+)', line)
            support_id = support_id_match.group(1) if support_id_match else "0"

            return NormalizedSecurityEvent(
                event_id=f"f5-asm-{support_id}",
                timestamp=event_time,
                source_device="F5 BIG-IP",
                category=ThreatCategory.WAF_EXPLOIT,
                threat_name=f"WAF Violation: {violations}",
                attacker_ip=client_ip,
                target=target,
                action_taken=action,
                count=1,
                raw_snippet=line.strip()[:300],
                metadata={"support_id": support_id, "violations": violations},
            )

        # Pattern 2: Policy Builder incident change (e.g. IncidentType was set to Malicious Scan / Malicious Session)
        if "ASMConfig change: Incident" in line and "IncidentType was set to" in line:
            inc_type_match = re.search(r'IncidentType was set to\s+([^.]+)', line)
            inc_type = inc_type_match.group(1).strip() if inc_type_match else "Security Incident"
            inc_id_match = re.search(r'Incident\s+(\d+)', line)
            inc_id = inc_id_match.group(1) if inc_id_match else "0"

            return NormalizedSecurityEvent(
                event_id=f"f5-inc-{inc_id}",
                timestamp=event_time,
                source_device="F5 BIG-IP",
                category=ThreatCategory.WAF_EXPLOIT,
                threat_name=f"F5 ASM Incident: {inc_type}",
                attacker_ip=None,
                target="Web Application VIP",
                action_taken="BLOCKED",
                count=1,
                raw_snippet=line.strip()[:300],
            )

        # Pattern 3: Subsystem error / Partition issue
        if "ASM subsystem error" in line:
            raw_hash = hashlib.md5(line.encode()).hexdigest()[:8]
            return NormalizedSecurityEvent(
                event_id=f"f5-err-{raw_hash}",
                timestamp=event_time,
                source_device="F5 BIG-IP",
                category=ThreatCategory.SYSTEM_HEALTH,
                threat_name="ASM Subsystem Database Error",
                target="asmlogd",
                action_taken="ALERT",
                count=1,
                raw_snippet=line.strip()[:300],
            )

        return None

    def parse_syslog_line(self, line: str) -> Optional[NormalizedSecurityEvent]:
        """Parses F5 LTM / system warnings (certificate expiry, pool member failure, SSL handshake fail)."""
        if not line or not line.strip():
            return None

        event_time = self._extract_timestamp(line)
        line_lower = line.lower()

        # SSL Handshake failure pattern
        if "ssl handshake failed for tcp" in line_lower:
            ip_match = re.search(r'TCP\s+([0-9\.]+):\d+\s+->\s+([0-9\.]+):', line)
            src_ip = ip_match.group(1) if ip_match else None
            dst_ip = ip_match.group(2) if ip_match else None
            raw_hash = hashlib.md5(line.encode()).hexdigest()[:8]

            return NormalizedSecurityEvent(
                event_id=f"f5-ssl-{raw_hash}",
                timestamp=event_time,
                source_device="F5 BIG-IP",
                category=ThreatCategory.INTRUSION,
                threat_name=f"SSL Handshake Failure from {src_ip}",
                attacker_ip=src_ip,
                target=dst_ip or "HTTPS VIP",
                action_taken="DROPPED",
                count=1,
                raw_snippet=line.strip()[:300],
            )

        if "certificate" in line_lower and "expire" in line_lower:
            cert_match = re.search(r'Certificate\s+(\S+).*?expire in\s+(\d+\s+\w+)', line, re.IGNORECASE)
            cert_name = cert_match.group(1) if cert_match else "SSL Certificate"
            expiry_time = cert_match.group(2) if cert_match else "soon"
            raw_hash = hashlib.md5(line.encode("utf-8")).hexdigest()[:10]

            return NormalizedSecurityEvent(
                event_id=f"f5-cert-{raw_hash}",
                timestamp=event_time,
                source_device="F5 BIG-IP",
                category=ThreatCategory.SYSTEM_HEALTH,
                threat_name=f"Certificate Expiration: {cert_name} expires in {expiry_time}",
                target=cert_name,
                action_taken="ALERT",
                count=1,
                raw_snippet=line.strip()[:300],
            )

        if "monitor status down" in line_lower:
            node_match = re.search(r'Node\s+(\S+)\s+monitor status down', line, re.IGNORECASE)
            node_name = node_match.group(1) if node_match else "Pool Member"
            raw_hash = hashlib.md5(line.encode("utf-8")).hexdigest()[:10]

            return NormalizedSecurityEvent(
                event_id=f"f5-node-{raw_hash}",
                timestamp=event_time,
                source_device="F5 BIG-IP",
                category=ThreatCategory.SYSTEM_HEALTH,
                threat_name=f"Pool Member Health Degradation: {node_name} down",
                target=node_name,
                action_taken="ALERT",
                count=1,
                raw_snippet=line.strip()[:300],
            )

        return None

    def _fetch_logs_internal(self, hours_back: int) -> List[NormalizedSecurityEvent]:
        """Legacy entrypoint: validates credentials and calls _fetch_logs_with_request."""
        if not self.password:
            raise ValueError("MNE_F5_PASSWORD is not configured in .env.")
        req = CollectorRequest(hours_back=hours_back)
        result = self._fetch_logs_with_request(req)
        return result.events

    def _fetch_logs_with_request(self, request: CollectorRequest) -> CollectorResult:
        """Collects logs over SSH from F5 BIG-IP with interval filtering and diagnostics."""
        if not self.password:
            raise ValueError("MNE_F5_PASSWORD is not configured in .env.")

        start_dt, end_dt = request.get_time_window()
        requested_time_range = {
            "start": start_dt.isoformat(),
            "end": end_dt.isoformat(),
            "hours_back": request.hours_back,
        }

        events: List[NormalizedSecurityEvent] = []
        records_fetched = 0
        records_parsed = 0
        records_ignored = 0
        records_malformed = 0
        pages_retrieved = 0
        has_more = False

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

            # Query ASM logs with requested interval / bound and rotated log handling (/var/log/asm*)
            line_limit = min(max(request.max_records * 5, int((request.hours_back or 24) * 500)), 20000)
            pages_retrieved += 1
            cmd_asm = (
                f"if ls /var/log/asm* >/dev/null 2>&1; then "
                f"for f in $(ls -tr /var/log/asm* 2>/dev/null); do "
                f"if [[ \"$f\" == *.gz ]]; then gzip -dc \"$f\" 2>/dev/null | tail -n {line_limit}; "
                f"else tail -n {line_limit} \"$f\" 2>/dev/null; fi; "
                f"done | tail -n {line_limit}; "
                f"else tail -n {line_limit} /var/log/asm 2>/dev/null || true; fi"
            )
            stdin, stdout, stderr = client.exec_command(cmd_asm, timeout=self.timeout)
            asm_lines = stdout.read().decode("utf-8", errors="ignore").splitlines()
            records_fetched += len(asm_lines)

            for line in asm_lines:
                if len(events) >= request.max_records or request.is_cancelled():
                    has_more = True
                    break
                parsed = self.parse_asm_log_line(line)
                if parsed:
                    if request.categories and parsed.category.value not in request.categories and parsed.category not in request.categories:
                        records_ignored += 1
                        continue
                    if start_dt <= parsed.timestamp <= end_dt:
                        events.append(parsed)
                        records_parsed += 1
                    else:
                        records_ignored += 1
                elif line.strip():
                    records_malformed += 1

            # Query LTM logs (certs, pool member health, SSL handshake) with rotated log handling
            if len(events) < request.max_records and not request.is_cancelled():
                pages_retrieved += 1
                cmd_ltm = (
                    f"if ls /var/log/ltm* >/dev/null 2>&1; then "
                    f"for f in $(ls -tr /var/log/ltm* 2>/dev/null); do "
                    f"if [[ \"$f\" == *.gz ]]; then gzip -dc \"$f\" 2>/dev/null | tail -n {line_limit}; "
                    f"else tail -n {line_limit} \"$f\" 2>/dev/null; fi; "
                    f"done | tail -n {line_limit}; "
                    f"else tail -n {line_limit} /var/log/ltm 2>/dev/null || true; fi"
                )
                stdin, stdout, stderr = client.exec_command(cmd_ltm, timeout=self.timeout)
                ltm_lines = stdout.read().decode("utf-8", errors="ignore").splitlines()
                records_fetched += len(ltm_lines)

                for line in ltm_lines:
                    if len(events) >= request.max_records or request.is_cancelled():
                        has_more = True
                        break
                    parsed = self.parse_syslog_line(line)
                    if parsed:
                        if request.categories and parsed.category.value not in request.categories and parsed.category not in request.categories:
                            records_ignored += 1
                            continue
                        if start_dt <= parsed.timestamp <= end_dt:
                            events.append(parsed)
                            records_parsed += 1
                        else:
                            records_ignored += 1

            # Check certificate inventory via tmsh if deep check requested
            if request.mode in ("FULL", "DEEP") and len(events) < request.max_records and not request.is_cancelled():
                pages_retrieved += 1
                cmd_cert = "tmsh -q list sys crypto cert expiration 2>/dev/null || true"
                stdin, stdout, stderr = client.exec_command(cmd_cert, timeout=30)
                cert_out = stdout.read().decode("utf-8", errors="ignore")
                # Parse expiration entries
                for block in cert_out.split("sys crypto cert"):
                    if "expiration" in block:
                        name_match = re.search(r'^\s*(\S+)', block)
                        exp_match = re.search(r'expiration\s+(.+)', block)
                        if name_match and exp_match:
                            cert_name = name_match.group(1)
                            exp_str = exp_match.group(1).strip()
                            try:
                                exp_dt = datetime.strptime(exp_str, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
                                days_left = (exp_dt - datetime.now(timezone.utc)).days
                                if days_left < 30:
                                    cert_event = NormalizedSecurityEvent(
                                        event_id=f"f5-inv-cert-{hashlib.md5(cert_name.encode()).hexdigest()[:8]}",
                                        timestamp=datetime.now(timezone.utc),
                                        source_device="F5 BIG-IP",
                                        category=ThreatCategory.SYSTEM_HEALTH,
                                        threat_name=f"Certificate Near Expiration: {cert_name} (in {days_left} days)",
                                        target=cert_name,
                                        action_taken="ALERT",
                                        count=1,
                                        raw_snippet=f"Certificate {cert_name} expires {exp_str} ({days_left} days remaining)",
                                        metadata={"cert_name": cert_name, "days_left": days_left},
                                    )
                                    events.append(cert_event)
                                    records_parsed += 1
                            except Exception:
                                pass

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

        # Status and message evaluation
        if len(events) > 0:
            status = CollectorStatus.SUCCESS
            diag_code = "OK"
            msg = f"Retrieved {len(events)} security events from F5 BIG-IP."
        elif records_fetched == 0:
            status = CollectorStatus.SUCCESS
            diag_code = "QUERY_EMPTY_ZERO_SOURCE"
            msg = f"F5 BIG-IP returned zero logs for requested time window ({start_dt.isoformat()} to {end_dt.isoformat()})."
        elif records_ignored > 0 and records_parsed == 0:
            status = CollectorStatus.SUCCESS
            diag_code = "QUERY_EMPTY_FILTERED"
            msg = f"F5 BIG-IP returned {records_fetched} lines but all were outside requested time range."
        elif records_malformed > 0 and records_parsed == 0:
            status = CollectorStatus.FAILED
            diag_code = "PARSE_ERROR"
            msg = f"F5 BIG-IP returned {records_fetched} lines but none could be parsed."
        else:
            status = CollectorStatus.SUCCESS
            diag_code = "QUERY_EMPTY_ZERO_SOURCE"
            msg = "Zero events found."

        diagnostic = CollectorDiagnostic(
            collector_id="f5_bigip",
            device_name=self.device_name,
            canonical_entity="f5_bigip",
            stage=DiagnosticStage.COMPLETE,
            status=DiagnosticStatus.SUCCESS if status == CollectorStatus.SUCCESS else DiagnosticStatus.FAILED,
            diagnostic_code=diag_code,
            message=msg,
            requested_time_range=requested_time_range,
            observed_time_range=observed_time_range,
            transport="SSH_CLI",
            source_queried="/var/log/asm*, /var/log/ltm*, sys crypto cert",
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
