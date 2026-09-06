import hashlib
import logging
import os
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


class FmcSecurityCollector(BaseSecurityCollector):
    """Collector for Cisco FMC / FTD (172.23.70.77 / .78).

    Collects Snort intrusion alerts, Security Intelligence blocks,
    and audit records.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: int = 120,
    ):
        super().__init__(device_name="Cisco FMC", timeout=timeout)
        self.host = host or os.getenv("MNE_FMC_HOST", "172.23.70.77")
        self.username = username or os.getenv("MNE_FMC_USERNAME", "admin")
        self.password = password or os.getenv("MNE_FMC_PASSWORD", "")

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

        ts = item.get("timestamp") or item.get("time")
        event_time = datetime.now(timezone.utc)
        if ts:
            try:
                if isinstance(ts, (int, float)):
                    event_time = datetime.fromtimestamp(ts, tz=timezone.utc)
                elif isinstance(ts, str):
                    event_time = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except Exception:
                pass

        category = ThreatCategory.INTRUSION
        if "login" in rule_msg.lower() or "session" in rule_msg.lower():
            category = ThreatCategory.PRIVILEGE_CHANGE
        elif "malware" in rule_msg.lower():
            category = ThreatCategory.MALWARE

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
            metadata=item,
        )

    def _fetch_logs_internal(self, hours_back: int) -> List[NormalizedSecurityEvent]:
        """Queries FMC REST API for audit & intrusion events."""
        events: List[NormalizedSecurityEvent] = []
        if not self.password:
            raise ValueError("MNE_FMC_PASSWORD is not configured in .env.")

        import requests
        import urllib3
        urllib3.disable_warnings()

        auth_url = f"https://{self.host}/api/fmc_platform/v1/auth/generatetoken"
        resp = requests.post(
            auth_url,
            auth=(self.username, self.password),
            verify=False,
            timeout=30,
        )
        if resp.status_code not in (200, 204):
            raise ConnectionError(f"FMC authentication failed with status {resp.status_code}")

        token = resp.headers.get("X-auth-access-token")
        domain = resp.headers.get("DOMAIN_UUID") or "e276abec-e0f2-11e3-8169-6d9ed49b625f"
        if not token:
            raise ConnectionError("FMC authentication succeeded but no X-auth-access-token was returned.")

        headers = {"X-auth-access-token": token}

        # 1. Fetch Audit Records from FMC platform
        audit_url = f"https://{self.host}/api/fmc_platform/v1/domain/{domain}/audit/auditrecords?limit=50"
        audit_resp = requests.get(audit_url, headers=headers, verify=False, timeout=self.timeout)
        if audit_resp.status_code == 200:
            for it in audit_resp.json().get("items", []):
                events.append(self.parse_fmc_event(it))

        return events
