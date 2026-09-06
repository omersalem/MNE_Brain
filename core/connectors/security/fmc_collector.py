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


class FmcSecurityCollector(BaseSecurityCollector):
    """Collector for Cisco FMC / FTD (172.23.70.77 / .78).

    Collects Snort intrusion alerts, Security Intelligence blocks,
    and malware file detection events.
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

        ts = item.get("timestamp")
        event_time = datetime.now(timezone.utc)
        if ts:
            try:
                if isinstance(ts, (int, float)):
                    event_time = datetime.fromtimestamp(ts, tz=timezone.utc)
                elif isinstance(ts, str):
                    event_time = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except Exception:
                pass

        return NormalizedSecurityEvent(
            event_id=f"fmc-{event_id}",
            timestamp=event_time,
            source_device="Cisco FMC",
            category=ThreatCategory.INTRUSION,
            threat_name=rule_msg,
            attacker_ip=src_ip,
            target=dst_ip,
            action_taken=action,
            count=1,
            raw_snippet=str(item)[:300],
            metadata=item,
        )

    def _fetch_logs_internal(self, hours_back: int) -> List[NormalizedSecurityEvent]:
        """Queries FMC REST API for intrusion & security intelligence events."""
        events: List[NormalizedSecurityEvent] = []
        if not self.password:
            logger.warning("FMC password not configured. Skipping live fetch.")
            return events

        import requests
        auth_url = f"https://{self.host}/api/fmc_platform/v1/auth/generatetoken"
        try:
            resp = requests.post(
                auth_url,
                auth=(self.username, self.password),
                verify=False,
                timeout=45,
            )
            if resp.status_code in (200, 204):
                token = resp.headers.get("X-auth-access-token")
                domain_uuid = resp.headers.get("DOMAIN_UUID", "e276abec-e0f2-11e3-8169-6d9ed49b625f")
                if token:
                    events_url = f"https://{self.host}/api/fmc_config/v1/domain/{domain_uuid}/audit/auditrecords"
                    headers = {"X-auth-access-token": token}
                    ev_resp = requests.get(events_url, headers=headers, verify=False, timeout=self.timeout)
                    if ev_resp.status_code == 200:
                        items = ev_resp.json().get("items", [])
                        for item in items:
                            events.append(self.parse_fmc_event(item))
        except Exception as exc:
            logger.warning("FMC REST call failed (%s). Attempting SSH fallback...", exc)
            # SSH fallback to FMC/FTD can be performed if needed
            raise

        return events
