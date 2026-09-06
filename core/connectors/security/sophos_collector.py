import hashlib
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.connectors.security.base import BaseSecurityCollector
from core.connectors.security.models import (
    NormalizedSecurityEvent,
    ThreatCategory,
)

logger = logging.getLogger(__name__)


class SophosEmailCollector(BaseSecurityCollector):
    """Collector for Sophos Email Protection Appliance (172.23.71.39:4444).

    Collects SMTP Quarantine alerts, Zero-day Sandstorm detonations,
    malware attachments, and spam surge anomalies.
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
        self.port = int(os.getenv("MNE_SOPHOS_PORT", str(port)))
        self.username = username or os.getenv("MNE_SOPHOS_USERNAME", "admin")
        self.password = password or os.getenv("MNE_SOPHOS_PASSWORD", "")

    def parse_quarantine_entry(self, entry: Dict[str, Any]) -> NormalizedSecurityEvent:
        """Parses a Sophos quarantine or mail log entry dictionary."""
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

    def _fetch_logs_internal(self, hours_back: int) -> List[NormalizedSecurityEvent]:
        """Fetches quarantine and mail logs via Sophos XML API or SSH."""
        events: List[NormalizedSecurityEvent] = []
        if not self.password:
            logger.warning("Sophos password not configured. Skipping live fetch.")
            return events

        # Query Sophos WebConsole XML API
        import requests
        api_url = f"https://{self.host}:{self.port}/webconsole/APIController"
        login_xml = (
            f"<Request><Login><Username>{self.username}</Username>"
            f"<Password>{self.password}</Password></Login></Request>"
        )
        try:
            resp = requests.post(api_url, data={"reqxml": login_xml}, verify=False, timeout=self.timeout)
            if resp.status_code == 200 and "Authentication Failure" not in resp.text:
                # Query quarantine records
                query_xml = (
                    f"<Request><Login><Username>{self.username}</Username>"
                    f"<Password>{self.password}</Password></Login>"
                    f"<Get><MailQuarantine></MailQuarantine></Get></Request>"
                )
                q_resp = requests.post(api_url, data={"reqxml": query_xml}, verify=False, timeout=self.timeout)
                # Parse XML responses or log records
                pass
        except Exception as exc:
            logger.warning("Sophos API request failed: %s", exc)
            raise

        return events
