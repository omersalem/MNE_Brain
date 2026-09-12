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


class SophosEmailCollector(BaseSecurityCollector):
    """Collector for Sophos Email Protection Appliance (172.23.71.39:4444).

    Collects SMTP rejected logs, RBL blocks, quarantine alerts,
    DKIM/SPF/DMARC failures, and malware/phishing detections.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: int = 4444,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: int = 120,
    ):
        super().__init__(device_name="Sophos Email", timeout=timeout, collector_id="sophos_email")
        self.host = host or os.getenv("MNE_SOPHOS_HOST", "172.23.71.39")
        self.port = int(os.getenv("MNE_SOPHOS_WEB_PORT", str(port)))
        self.username = username or os.getenv("MNE_SOPHOS_USERNAME", "admin")
        self.password = password or os.getenv("MNE_SOPHOS_PASSWORD", "")

    def _extract_timestamp(self, line: str) -> datetime:
        """Extracts timestamp from Sophos log lines."""
        # E.g. "2026-09-06 08:29:08.746Z" or "2026-09-06T08:29:08Z"
        iso_match = re.search(r'^(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}(?:\.\d+)?)Z?', line.strip())
        if iso_match:
            try:
                dt_str = iso_match.group(1).replace(" ", "T")
                return datetime.fromisoformat(dt_str).replace(tzinfo=timezone.utc)
            except Exception:
                pass

        # Syslog format
        syslog_match = re.search(r'^([A-Za-z]{3}\s+\d+\s+\d{2}:\d{2}:\d{2})', line.strip())
        if syslog_match:
            try:
                raw_ts = re.sub(r'\s+', ' ', syslog_match.group(1))
                year = datetime.now(timezone.utc).year
                return datetime.strptime(f"{year} {raw_ts}", "%Y %b %d %H:%M:%S").replace(tzinfo=timezone.utc)
            except Exception:
                pass

        return datetime.now(timezone.utc)

    def parse_quarantine_entry(self, entry: Dict[str, Any]) -> NormalizedSecurityEvent:
        """Parses a structured quarantine dictionary entry."""
        mail_id = entry.get("mail_id") or hashlib.md5(str(entry).encode()).hexdigest()[:10]
        sender = entry.get("sender", "unknown@sender")
        recipient = entry.get("recipient", "unknown@recipient")
        reason = entry.get("reason", "Suspicious Email Event")
        action_raw = entry.get("action", "QUARANTINED").upper()
        sandbox = entry.get("sandbox_verdict", "")

        category = ThreatCategory.PHISHING
        reason_lower = reason.lower()
        if "malware" in reason_lower or "trojan" in reason_lower or "virus" in reason_lower or sandbox.lower() == "malicious":
            category = ThreatCategory.MALWARE
        elif "spf" in reason_lower or "dkim" in reason_lower or "dmarc" in reason_lower:
            category = ThreatCategory.PHISHING
        elif "rbl" in reason_lower or "relay" in reason_lower:
            category = ThreatCategory.INTRUSION

        if "QUARANTINE" in action_raw:
            action = "QUARANTINED"
        elif "DROP" in action_raw or "REJECT" in action_raw or "BLOCK" in action_raw:
            action = "DROPPED"
        else:
            action = "ALLOWED"

        event_time = datetime.now(timezone.utc)
        ts_str = entry.get("timestamp")
        if ts_str:
            try:
                event_time = datetime.fromisoformat(ts_str.replace("Z", "+00:00")).replace(tzinfo=timezone.utc)
            except Exception:
                pass

        # Subject identifier hash if available
        subject = entry.get("subject", "")
        subject_hash = hashlib.md5(subject.encode()).hexdigest()[:8] if subject else None

        metadata = dict(entry)
        metadata["sender"] = sender
        metadata["recipient"] = recipient
        metadata["sandbox_verdict"] = sandbox
        if subject_hash:
            metadata["subject_hash"] = subject_hash

        return NormalizedSecurityEvent(
            event_id=f"sophos-{mail_id}",
            timestamp=event_time,
            source_device="Sophos Email",
            category=category,
            threat_name=f"{reason} (From: {sender})",
            attacker_ip=entry.get("client_ip"),
            target=recipient,
            action_taken=action,
            count=1,
            raw_snippet=f"Sender={sender}, Recipient={recipient}, Reason={reason}, Action={action}",
            metadata=metadata,
        )

    def parse_reject_log_line(self, line: str) -> Optional[NormalizedSecurityEvent]:
        """Parses a line from Sophos /log/smtpd_reject.log."""
        if not line or ("rejected RCPT" not in line and "rejected" not in line.lower()):
            return None

        event_time = self._extract_timestamp(line)

        # IP extraction: client IP has port e.g. [185.190.140.22]:59371 or standard IPv4/IPv6 notation
        ip_match = re.search(r'\[([0-9a-fA-F\.\:]+)\]:\d+', line)
        if not ip_match:
            ip_match = re.search(r'\[(\d{1,3}(?:\.\d{1,3}){3})\]', line)
        src_ip = ip_match.group(1) if ip_match else None

        sender_match = re.search(r'F=<([^>]+)>', line)
        sender = sender_match.group(1) if sender_match else "unknown_sender"

        rcpt_match = re.search(r'rejected RCPT <([^>]+)>:\s*(.*)', line)
        if rcpt_match:
            recipient = rcpt_match.group(1)
            reason = rcpt_match.group(2).strip()
        else:
            recipient = "unknown_recipient"
            reason = "Rejected by policy"

        reason_lower = reason.lower()
        category = ThreatCategory.PHISHING
        if "rbl" in reason_lower:
            category = ThreatCategory.INTRUSION
        elif "malware" in reason_lower or "virus" in reason_lower:
            category = ThreatCategory.MALWARE
        elif "spf" in reason_lower or "dkim" in reason_lower or "dmarc" in reason_lower:
            category = ThreatCategory.PHISHING

        raw_hash = hashlib.md5(f"{src_ip}_{sender}_{recipient}_{reason}_{event_time.isoformat()}".encode()).hexdigest()[:10]

        return NormalizedSecurityEvent(
            event_id=f"sophos-rej-{raw_hash}",
            timestamp=event_time,
            source_device="Sophos Email",
            category=category,
            threat_name=f"Email Blocked: {reason} (From: {sender})",
            attacker_ip=src_ip,
            target=recipient,
            action_taken="DROPPED",
            count=1,
            raw_snippet=line.strip()[:300],
            metadata={"sender": sender, "recipient": recipient, "reason": reason},
        )

    def parse_quarantine_log_line(self, line: str) -> Optional[NormalizedSecurityEvent]:
        """Parses a quarantine or spam log line (from /log/quarantine.log or /log/spam.log)."""
        if not line or not line.strip():
            return None
        line_lower = line.lower()
        if "quarantine" not in line_lower and "spam" not in line_lower:
            return None

        event_time = self._extract_timestamp(line)

        mail_id_m = re.search(r'mail_id=["\']?([a-zA-Z0-9_\-]+)["\']?', line)
        mail_id = mail_id_m.group(1) if mail_id_m else hashlib.md5(line.encode()).hexdigest()[:8]

        sender_m = re.search(r'(?:sender|from)=["\']?([^"\'\s>]+)["\']?', line, re.IGNORECASE)
        sender = sender_m.group(1) if sender_m else "unknown_sender"

        rcpt_m = re.search(r'(?:recipient|to)=["\']?([^"\'\s>]+)["\']?', line, re.IGNORECASE)
        rcpt = rcpt_m.group(1) if rcpt_m else "unknown_recipient"

        reason_m = re.search(r'reason=["\']?([^"\'\n]+?)["\']?(?:\s+[a-z_]+=|[\],]|$)', line, re.IGNORECASE)
        reason = reason_m.group(1).strip() if reason_m else ("Spam detected" if "spam" in line_lower else "Email Quarantined")

        ip_m = re.search(r'(?:client_ip|src_ip|ip|src)=["\']?([0-9a-fA-F\.\:]+)["\']?', line, re.IGNORECASE)
        src_ip = ip_m.group(1) if ip_m else None

        category = ThreatCategory.MALWARE if any(k in reason.lower() for k in ("malware", "trojan", "virus")) else ThreatCategory.PHISHING
        action = "QUARANTINED" if "quarantin" in line_lower else "DROPPED"

        return NormalizedSecurityEvent(
            event_id=f"sophos-quar-{mail_id}",
            timestamp=event_time,
            source_device="Sophos Email",
            category=category,
            threat_name=f"{reason} (From: {sender})",
            attacker_ip=src_ip,
            target=rcpt,
            action_taken=action,
            count=1,
            raw_snippet=line.strip()[:300],
            metadata={"sender": sender, "recipient": rcpt, "reason": reason, "mail_id": mail_id},
        )

    def parse_malware_log_line(self, line: str) -> Optional[NormalizedSecurityEvent]:
        """Parses an antivirus / sandbox malware log line (from /log/av.log or /log/sandbox.log)."""
        if not line or not line.strip():
            return None
        line_lower = line.lower()
        if not any(k in line_lower for k in ("malware", "virus", "trojan", "infected", "sandbox", "threat")):
            return None

        event_time = self._extract_timestamp(line)

        virus_m = re.search(r'(?:malware|virus|trojan|threat)=["\']?([^"\'\n]+?)["\']?(?:\s+[a-z_]+=|[\],]|$)', line, re.IGNORECASE)
        if not virus_m:
            virus_m = re.search(r'(?:infected with|detected:?)\s+([A-Za-z0-9_\-\.\/]+)', line, re.IGNORECASE)
        virus_name = virus_m.group(1).strip() if virus_m else "Unknown Malware"

        file_m = re.search(r'file=["\']?([^"\'\s]+)["\']?', line, re.IGNORECASE)
        filename = file_m.group(1) if file_m else None

        sender_m = re.search(r'(?:sender|from)=["\']?([^"\'\s>]+)["\']?', line, re.IGNORECASE)
        sender = sender_m.group(1) if sender_m else None

        rcpt_m = re.search(r'(?:recipient|to)=["\']?([^"\'\s>]+)["\']?', line, re.IGNORECASE)
        rcpt = rcpt_m.group(1) if rcpt_m else "mail-filter"

        ip_m = re.search(r'(?:client_ip|src_ip|ip|src)=["\']?([0-9a-fA-F\.\:]+)["\']?', line, re.IGNORECASE)
        src_ip = ip_m.group(1) if ip_m else None

        raw_hash = hashlib.md5(line.encode()).hexdigest()[:8]
        threat_name = f"Malware Detected: {virus_name}" + (f" (File: {filename})" if filename else "")

        return NormalizedSecurityEvent(
            event_id=f"sophos-av-{raw_hash}",
            timestamp=event_time,
            source_device="Sophos Email",
            category=ThreatCategory.MALWARE,
            threat_name=threat_name,
            attacker_ip=src_ip,
            target=rcpt,
            action_taken="DROPPED",
            count=1,
            raw_snippet=line.strip()[:300],
            metadata={"virus_name": virus_name, "filename": filename, "sender": sender, "recipient": rcpt},
        )

    def parse_auth_log_line(self, line: str) -> Optional[NormalizedSecurityEvent]:
        """Parses an authentication log line (from /log/access_server.log or /log/auth.log)."""
        if not line or not line.strip():
            return None
        line_lower = line.lower()
        if not any(k in line_lower for k in ("fail", "invalid", "denied", "reject", "auth")):
            return None

        event_time = self._extract_timestamp(line)

        user_m = re.search(r'(?:user(?:name)?|account)=["\']?([^"\'\s]+)["\']?', line, re.IGNORECASE)
        if not user_m:
            user_m = re.search(r'user\s+["\']?([^"\'\s]+)["\']?', line, re.IGNORECASE)
        user = user_m.group(1) if user_m else "unknown_user"

        ip_m = re.search(r'(?:from|src(?:_ip)?|client(?:_ip)?)=["\']?([0-9a-fA-F\.\:]+)["\']?', line, re.IGNORECASE)
        if not ip_m:
            ip_m = re.search(r'from\s+["\']?([0-9a-fA-F\.\:]+)["\']?', line, re.IGNORECASE)
        src_ip = ip_m.group(1) if ip_m else None

        raw_hash = hashlib.md5(line.encode()).hexdigest()[:8]
        return NormalizedSecurityEvent(
            event_id=f"sophos-auth-{raw_hash}",
            timestamp=event_time,
            source_device="Sophos Email",
            category=ThreatCategory.BRUTE_FORCE if "fail" in line_lower else ThreatCategory.PRIVILEGE_CHANGE,
            threat_name=f"Authentication Failure: user '{user}'",
            attacker_ip=src_ip,
            target=user,
            action_taken="DROPPED",
            count=1,
            raw_snippet=line.strip()[:300],
            metadata={"user": user, "src_ip": src_ip},
        )

    def parse_delivery_log_line(self, line: str) -> Optional[NormalizedSecurityEvent]:
        """Parses a delivery / transport log line (from /log/smtpd_activity.log or /log/delivery.log)."""
        if not line or not line.strip():
            return None
        line_lower = line.lower()
        if not any(k in line_lower for k in ("fail", "error", "defer", "timeout", "reject", "tls")):
            return None

        event_time = self._extract_timestamp(line)

        rcpt_m = re.search(r'(?:recipient|to)=["\']?([^"\'\s>]+)["\']?', line, re.IGNORECASE)
        rcpt = rcpt_m.group(1) if rcpt_m else "unknown_destination"

        reason_m = re.search(r'reason=["\']?([^"\'\n]+?)["\']?(?:\s+[a-z_]+=|[\],]|$)', line, re.IGNORECASE)
        if not reason_m:
            reason_m = re.search(r'\[delivery\]\s*(.*?)(?:\s+[a-z_]+=["\']|$)', line, re.IGNORECASE)
        if not reason_m:
            reason_m = re.search(r'(?:failed|deferred|error).*?:\s*(.*)', line, re.IGNORECASE)
        reason = reason_m.group(1).strip() if reason_m else "Email delivery or transport failure"

        ip_m = re.search(r'(?:host|ip|server|with)\s*[:=]?\s*\[?([0-9a-fA-F\.\:]+)\]?', line, re.IGNORECASE)
        remote_ip = ip_m.group(1) if ip_m else None

        raw_hash = hashlib.md5(line.encode()).hexdigest()[:8]
        return NormalizedSecurityEvent(
            event_id=f"sophos-del-{raw_hash}",
            timestamp=event_time,
            source_device="Sophos Email",
            category=ThreatCategory.SYSTEM_HEALTH if "tls" in line_lower or "timeout" in line_lower else ThreatCategory.ANOMALY,
            threat_name=f"Delivery Failure: {reason[:80]}",
            attacker_ip=remote_ip,
            target=rcpt,
            action_taken="ALERT",
            count=1,
            raw_snippet=line.strip()[:300],
            metadata={"reason": reason, "recipient": rcpt, "remote_ip": remote_ip},
        )

    def _fetch_logs_internal(self, hours_back: int) -> List[NormalizedSecurityEvent]:
        """Legacy entrypoint: validates credentials and calls _fetch_logs_with_request."""
        if not self.password:
            raise ValueError("MNE_SOPHOS_PASSWORD is not configured in .env.")
        req = CollectorRequest(hours_back=hours_back)
        result = self._fetch_logs_with_request(req)
        return result.events

    def _fetch_logs_with_request(self, request: CollectorRequest) -> CollectorResult:
        """Fetches reject, quarantine, malware, auth, and delivery logs via Sophos SSH shell."""
        if not self.password:
            raise ValueError("MNE_SOPHOS_PASSWORD is not configured in .env.")

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
            shell = client.invoke_shell()
            time.sleep(1)
            if shell.recv_ready():
                shell.recv(4096)

            # Navigate Sophos menu: 5 (Device Management) -> 3 (Advanced Shell)
            shell.send("5\n3\n")
            time.sleep(1.5)
            if shell.recv_ready():
                shell.recv(8192)

            line_limit = min(max(request.max_records * 5, int((request.hours_back or 24) * 200)), 10000)
            sources = [
                ("/log/smtpd_reject.log", self.parse_reject_log_line),
                ("/log/quarantine.log", self.parse_quarantine_log_line),
                ("/log/av.log", self.parse_malware_log_line),
                ("/log/access_server.log", self.parse_auth_log_line),
                ("/log/smtpd_activity.log", self.parse_delivery_log_line),
            ]

            for log_path, parse_fn in sources:
                if len(events) >= request.max_records or request.is_cancelled():
                    has_more = True
                    break

                pages_retrieved += 1
                cmd = (
                    f"if ls {log_path}* >/dev/null 2>&1; then "
                    f"for f in $(ls -tr {log_path}* 2>/dev/null); do "
                    f"if [[ \"$f\" == *.gz ]]; then gzip -dc \"$f\" 2>/dev/null | tail -n {line_limit}; "
                    f"else tail -n {line_limit} \"$f\" 2>/dev/null; fi; "
                    f"done | tail -n {line_limit}; "
                    f"else tail -n {line_limit} {log_path} 2>/dev/null || true; fi\n"
                )
                shell.send(cmd)
                time.sleep(1.0)

                log_output = ""
                start_wait = time.time()
                while time.time() - start_wait < 2.0:
                    if shell.recv_ready():
                        log_output += shell.recv(65536).decode("utf-8", errors="ignore")
                    time.sleep(0.2)

                lines = log_output.splitlines()
                records_fetched += len(lines)
                for line in lines:
                    if len(events) >= request.max_records or request.is_cancelled():
                        has_more = True
                        break
                    parsed = parse_fn(line)
                    if parsed:
                        if request.categories and parsed.category.value not in request.categories and parsed.category not in request.categories:
                            records_ignored += 1
                            continue
                        if start_dt <= parsed.timestamp <= end_dt:
                            events.append(parsed)
                            records_parsed += 1
                        else:
                            records_ignored += 1

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
            msg = f"Retrieved {len(events)} security events from Sophos Email."
        elif records_fetched == 0:
            status = CollectorStatus.SUCCESS
            diag_code = "QUERY_EMPTY_ZERO_SOURCE"
            msg = f"Sophos Email returned zero logs for requested time window ({start_dt.isoformat()} to {end_dt.isoformat()})."
        elif records_ignored > 0 and records_parsed == 0:
            status = CollectorStatus.SUCCESS
            diag_code = "QUERY_EMPTY_FILTERED"
            msg = f"Sophos Email returned {records_fetched} lines but all were outside requested time range."
        elif records_malformed > 0 and records_parsed == 0:
            status = CollectorStatus.FAILED
            diag_code = "PARSE_ERROR"
            msg = f"Sophos Email returned {records_fetched} lines but none could be parsed."
        else:
            status = CollectorStatus.SUCCESS
            diag_code = "QUERY_EMPTY_ZERO_SOURCE"
            msg = "Zero events found."

        diagnostic = CollectorDiagnostic(
            collector_id="sophos_email",
            device_name=self.device_name,
            canonical_entity="sophos_email",
            stage=DiagnosticStage.COMPLETE,
            status=DiagnosticStatus.SUCCESS if status == CollectorStatus.SUCCESS else DiagnosticStatus.FAILED,
            diagnostic_code=diag_code,
            message=msg,
            requested_time_range=requested_time_range,
            observed_time_range=observed_time_range,
            transport="SSH_CLI",
            source_queried="/log/smtpd_reject.log, /log/quarantine.log, /log/av.log, /log/access_server.log, /log/smtpd_activity.log",
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
