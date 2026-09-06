import hashlib
import logging
import os
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()

from core.connectors.security.base import BaseSecurityCollector
from core.connectors.security.models import (
    NormalizedSecurityEvent,
    ThreatCategory,
)

logger = logging.getLogger(__name__)


class SophosEmailCollector(BaseSecurityCollector):
    """Collector for Sophos Email Protection Appliance (172.23.71.39:4444).

    Collects SMTP rejected logs, RBL blocks, quarantine alerts,
    and malware/phishing detections.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: int = 4444,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: int = 120,
    ):
        super().__init__(device_name="Sophos Email", timeout=timeout)
        self.host = host or os.getenv("MNE_SOPHOS_HOST", "172.23.71.39")
        self.port = int(os.getenv("MNE_SOPHOS_WEB_PORT", str(port)))
        self.username = username or os.getenv("MNE_SOPHOS_USERNAME", "admin")
        self.password = password or os.getenv("MNE_SOPHOS_PASSWORD", "")

    def parse_quarantine_entry(self, entry: Dict[str, Any]) -> NormalizedSecurityEvent:
        """Parses a structured quarantine dictionary entry."""
        mail_id = entry.get("mail_id") or hashlib.md5(str(entry).encode()).hexdigest()[:10]
        sender = entry.get("sender", "unknown@sender")
        recipient = entry.get("recipient", "unknown@recipient")
        reason = entry.get("reason", "Suspicious Email Event")
        action_raw = entry.get("action", "QUARANTINED").upper()
        sandbox = entry.get("sandbox_verdict", "")

        category = ThreatCategory.PHISHING
        if "malware" in reason.lower() or "trojan" in reason.lower() or "virus" in reason.lower() or sandbox.lower() == "malicious":
            category = ThreatCategory.MALWARE

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
                event_time = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            except Exception:
                pass

        return NormalizedSecurityEvent(
            event_id=f"sophos-{mail_id}",
            timestamp=event_time,
            source_device="Sophos Email",
            category=category,
            threat_name=f"{reason} (From: {sender})",
            attacker_ip=None,
            target=recipient,
            action_taken=action,
            count=1,
            raw_snippet=f"Sender={sender}, Recipient={recipient}, Reason={reason}, Action={action}",
            metadata={"sender": sender, "recipient": recipient, "sandbox_verdict": sandbox},
        )

    def parse_reject_log_line(self, line: str) -> Optional[NormalizedSecurityEvent]:
        """Parses a line from Sophos /log/smtpd_reject.log."""
        if not line or "rejected RCPT" not in line:
            return None

        # Format: 2026-09-06 08:29:08.746Z [13449] H=omta34.uswest2.a.cloudfilter.net [35.89.44.33]:59371 ... F=<hr@jscpd.ps> rejected RCPT <nablus@mne.gov.ps>: An RBL has blocked...
        ip_match = re.search(r'\[([0-9a-fA-F\.\:]+)\]:\d+', line)
        src_ip = ip_match.group(1) if ip_match else None

        sender_match = re.search(r'F=<([^>]+)>', line)
        sender = sender_match.group(1) if sender_match else "unknown_sender"

        rcpt_match = re.search(r'rejected RCPT <([^>]+)>:\s*(.*)', line)
        recipient = rcpt_match.group(1) if rcpt_match else "unknown_recipient"
        reason = rcpt_match.group(2).strip() if rcpt_match else "Rejected by policy"

        category = ThreatCategory.PHISHING
        if "rbl" in reason.lower():
            category = ThreatCategory.INTRUSION
        elif "malware" in reason.lower() or "virus" in reason.lower():
            category = ThreatCategory.MALWARE

        raw_hash = hashlib.md5(f"{src_ip}_{sender}_{recipient}_{reason}".encode()).hexdigest()[:10]

        return NormalizedSecurityEvent(
            event_id=f"sophos-rej-{raw_hash}",
            timestamp=datetime.now(timezone.utc),
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

    def _fetch_logs_internal(self, hours_back: int) -> List[NormalizedSecurityEvent]:
        """Fetches reject and mail logs via Sophos SSH shell."""
        events: List[NormalizedSecurityEvent] = []
        if not self.password:
            raise ValueError("MNE_SOPHOS_PASSWORD is not configured in .env.")

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
            shell.recv(4096)
            # Enter menu 5 (Device Management) -> 3 (Advanced Shell)
            shell.send("5\n3\n")
            time.sleep(1.5)
            shell.recv(8192)

            # Query the last 50 rejected emails
            shell.send("tail -n 50 /log/smtpd_reject.log\n")
            time.sleep(2)
            reject_output = shell.recv(65536).decode("utf-8", errors="ignore")
            for line in reject_output.splitlines():
                parsed = self.parse_reject_log_line(line)
                if parsed:
                    events.append(parsed)

        finally:
            client.close()

        return events
