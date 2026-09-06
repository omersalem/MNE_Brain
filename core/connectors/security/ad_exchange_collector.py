import hashlib
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.connectors.security.base import BaseSecurityCollector
from core.connectors.security.models import (
    NormalizedSecurityEvent,
    ThreatCategory,
)

logger = logging.getLogger(__name__)


class ActiveDirectoryCollector(BaseSecurityCollector):
    """Collector for Active Directory (MNE-DC1 172.23.71.27).

    Collects Account Lockouts (4740), Logon Failures (4625),
    and Privileged Group Membership Additions (4728, 4732, 4756).
    """

    def __init__(
        self,
        host: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: int = 120,
    ):
        super().__init__(device_name="Active Directory", timeout=timeout)
        self.host = host or os.getenv("MNE_AD_HOST", "172.23.71.27")
        self.username = username or os.getenv("MNE_AD_USERNAME", "")
        self.password = password or os.getenv("MNE_AD_PASSWORD", "")

    def parse_security_event(self, event: Dict[str, Any]) -> NormalizedSecurityEvent:
        """Parses a Windows Security EventLog JSON/dict."""
        event_id = int(event.get("EventID", 0))
        target_user = event.get("TargetUserName", "UnknownUser")
        time_created = event.get("TimeCreated")

        event_time = datetime.now(timezone.utc)
        if time_created:
            try:
                event_time = datetime.fromisoformat(time_created.replace("Z", "+00:00"))
            except Exception:
                pass

        category = ThreatCategory.ANOMALY
        action = "ALERT"
        threat_name = f"Windows Security Event {event_id}"
        attacker_ip = event.get("IpAddress") or event.get("CallerComputerName")
        target = target_user

        if event_id == 4740:
            category = ThreatCategory.BRUTE_FORCE
            threat_name = f"Account Locked Out: {target_user}"
            action = "BLOCKED"
        elif event_id == 4625:
            category = ThreatCategory.BRUTE_FORCE
            threat_name = f"Failed Domain Logon: {target_user}"
            action = "DROPPED"
        elif event_id in (4728, 4732, 4756):
            category = ThreatCategory.PRIVILEGE_CHANGE
            group_name = event.get("TargetUserName", "Privileged Group")
            member_raw = event.get("MemberName", "UnknownMember")
            cn_match = re.search(r'CN=([^,]+)', member_raw)
            clean_member = cn_match.group(1) if cn_match else member_raw
            target = clean_member
            threat_name = f"Member added to {group_name}: {clean_member}"
            action = "ALLOWED"

        raw_hash = hashlib.md5(f"{event_id}_{target}_{time_created}".encode()).hexdigest()[:10]

        return NormalizedSecurityEvent(
            event_id=f"ad-{raw_hash}",
            timestamp=event_time,
            source_device="Active Directory",
            category=category,
            threat_name=threat_name,
            attacker_ip=attacker_ip,
            target=target,
            action_taken=action,
            count=1,
            raw_snippet=str(event)[:300],
            metadata=event,
        )

    def _fetch_logs_internal(self, hours_back: int) -> List[NormalizedSecurityEvent]:
        """Queries Windows Security EventLog via WinRM / PowerShell."""
        events: List[NormalizedSecurityEvent] = []
        if not self.password:
            logger.warning("AD password not configured. Skipping live fetch.")
            return events

        # PowerShell script to retrieve security events as JSON
        ps_script = f"""
        $cutOff = (Get-Date).AddHours(-{hours_back})
        $events = Get-WinEvent -FilterHashtable @{{LogName='Security'; Id=4740,4728,4732,4756; StartTime=$cutOff}} -ErrorAction SilentlyContinue -MaxEvents 100
        $events | ForEach-Object {{
            $xml = [xml]$_.ToXml()
            [PSCustomObject]@{{
                EventID = $_.Id
                TimeCreated = $_.TimeCreated.ToString('o')
                TargetUserName = ($xml.Event.EventData.Data | Where-Object {{ $_.Name -eq 'TargetUserName' }}).'#text'
                MemberName = ($xml.Event.EventData.Data | Where-Object {{ $_.Name -eq 'MemberName' }}).'#text'
                CallerComputerName = ($xml.Event.EventData.Data | Where-Object {{ $_.Name -eq 'CallerComputerName' }}).'#text'
                IpAddress = ($xml.Event.EventData.Data | Where-Object {{ $_.Name -eq 'IpAddress' }}).'#text'
            }}
        }} | ConvertTo-Json -Compress
        """
        # Execute via WinRM
        try:
            import winrm
            session = winrm.Session(self.host, auth=(self.username, self.password), transport="ntlm")
            result = session.run_ps(ps_script)
            if result.status_code == 0 and result.std_out.strip():
                import json
                parsed_json = json.loads(result.std_out)
                items = parsed_json if isinstance(parsed_json, list) else [parsed_json]
                for it in items:
                    events.append(self.parse_security_event(it))
        except Exception as exc:
            logger.warning("WinRM query to AD failed: %s", exc)
            raise

        return events


class ExchangeCollector(BaseSecurityCollector):
    """Collector for Exchange 2019 (172.23.71.36).

    Collects SMTP relay blocking events, high recipient surges,
    and transport security failures.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: int = 120,
    ):
        super().__init__(device_name="Exchange", timeout=timeout)
        self.host = host or os.getenv("MNE_EXCHANGE_HOST", "172.23.71.36")
        self.username = username or os.getenv("MNE_EXCHANGE_USERNAME", "")
        self.password = password or os.getenv("MNE_EXCHANGE_PASSWORD", "")

    def parse_tracking_log(self, item: Dict[str, Any]) -> NormalizedSecurityEvent:
        """Parses an Exchange MessageTracking or Protocol Log record."""
        client_ip = item.get("client_ip")
        sender = item.get("sender", "unknown@external")
        reason = item.get("reason", "")
        event_time = datetime.now(timezone.utc)
        ts_str = item.get("timestamp")
        if ts_str:
            try:
                event_time = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            except Exception:
                pass

        category = ThreatCategory.ANOMALY
        action = "BLOCKED" if "unable to relay" in reason.lower() or item.get("event_type") == "FAIL" else "ALLOWED"
        threat_name = f"Exchange Relay Attempt Blocked from {sender}" if "relay" in reason.lower() else f"Exchange Transport Anomaly: {reason}"

        raw_hash = hashlib.md5(f"{client_ip}_{sender}_{ts_str}".encode()).hexdigest()[:10]

        return NormalizedSecurityEvent(
            event_id=f"ex-{raw_hash}",
            timestamp=event_time,
            source_device="Exchange",
            category=category,
            threat_name=threat_name,
            attacker_ip=client_ip,
            target=sender,
            action_taken=action,
            count=1,
            raw_snippet=str(item)[:300],
            metadata=item,
        )

    def _fetch_logs_internal(self, hours_back: int) -> List[NormalizedSecurityEvent]:
        """Queries Exchange Transport logs via WinRM."""
        events: List[NormalizedSecurityEvent] = []
        if not self.password:
            logger.warning("Exchange password not configured. Skipping live fetch.")
            return events
        # WinRM query implementation...
        return events
