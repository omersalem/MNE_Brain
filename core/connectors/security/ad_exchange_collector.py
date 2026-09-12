import hashlib
import json
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


class ActiveDirectoryCollector(BaseSecurityCollector):
    """Collector for Active Directory (MNE-DC1 172.23.71.27).

    Collects Account Lockouts (4740), Logon Failures (4625),
    Privileged Group Membership Additions (4728, 4732, 4756), Privilege Grants (4672),
    Account Provisioning (4720, 4722, 4725), Password Resets (4723, 4724),
    and Kerberos Pre-Auth Failures (4768, 4771).
    """

    def __init__(
        self,
        host: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: int = 120,
    ):
        super().__init__(device_name="Active Directory", timeout=timeout, collector_id="active_directory")
        self.host = host or os.getenv("MNE_AD_HOST", "172.23.71.27")
        self.username = username or os.getenv("MNE_AD_USERNAME", "")
        self.password = password or os.getenv("MNE_AD_PASSWORD", "")

    def parse_security_event(self, event: Dict[str, Any]) -> NormalizedSecurityEvent:
        """Parses a Windows Security EventLog JSON/dict."""
        event_id = int(event.get("EventID", 0))
        target_user = event.get("TargetUserName") or event.get("target_user") or "SystemUser"
        time_created = event.get("TimeCreated") or event.get("time_created")

        event_time = datetime.now(timezone.utc)
        if time_created:
            try:
                event_time = datetime.fromisoformat(time_created.replace("Z", "+00:00")).replace(tzinfo=timezone.utc)
            except Exception:
                pass

        category = ThreatCategory.ANOMALY
        action = "ALERT"
        threat_name = f"Windows Security Event {event_id}"
        attacker_ip = event.get("IpAddress") or event.get("CallerComputerName") or event.get("WorkstationName")
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
        elif event_id == 4672:
            category = ThreatCategory.PRIVILEGE_CHANGE
            threat_name = "Special privileges assigned to new logon"
            action = "ALLOWED"
        elif event_id == 4720:
            category = ThreatCategory.PRIVILEGE_CHANGE
            threat_name = f"User Account Created: {target_user}"
            action = "ALLOWED"
        elif event_id == 4722:
            category = ThreatCategory.PRIVILEGE_CHANGE
            threat_name = f"User Account Enabled: {target_user}"
            action = "ALLOWED"
        elif event_id == 4725:
            category = ThreatCategory.PRIVILEGE_CHANGE
            threat_name = f"User Account Disabled: {target_user}"
            action = "ALERT"
        elif event_id in (4723, 4724):
            category = ThreatCategory.PRIVILEGE_CHANGE
            threat_name = f"User Password Reset: {target_user}"
            action = "ALERT"
        elif event_id in (4768, 4771):
            category = ThreatCategory.BRUTE_FORCE
            threat_name = f"Kerberos Pre-Auth Failure: {target_user}"
            action = "DROPPED"

        raw_hash = hashlib.md5(f"{event_id}_{target}_{time_created}".encode()).hexdigest()[:10]

        # Enriched metadata preserving named XML event fields
        metadata = dict(event)
        for k in ("TargetSid", "WorkstationName", "Status", "SubStatus", "TicketOptions", "FailureCode"):
            if k in event:
                metadata[k] = event[k]

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
            metadata=metadata,
        )

    def _fetch_logs_internal(self, hours_back: int) -> List[NormalizedSecurityEvent]:
        """Legacy entrypoint: validates credentials and calls _fetch_logs_with_request."""
        if not self.password:
            raise ValueError("MNE_AD_PASSWORD is not configured in .env.")
        req = CollectorRequest(hours_back=hours_back)
        result = self._fetch_logs_with_request(req)
        return result.events

    def _fetch_logs_with_request(self, request: CollectorRequest) -> CollectorResult:
        """Queries Windows Security EventLog via WinRM using exact StartTime/EndTime filters."""
        if not self.password:
            raise ValueError("MNE_AD_PASSWORD is not configured in .env.")

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
        pages_retrieved = 1
        has_more = False

        import winrm
        session = winrm.Session(self.host, auth=(self.username, self.password), transport="ntlm")

        start_ps = start_dt.strftime("%Y-%m-%dT%H:%M:%S")
        end_ps = end_dt.strftime("%Y-%m-%dT%H:%M:%S")
        max_events = min(request.max_records, 500)

        ps_script = f"""
        $res = @()
        $ErrorActionPreference = 'Stop'
        try {{
            $startTime = [DateTime]::Parse('{start_ps}')
            $endTime = [DateTime]::Parse('{end_ps}')
            $ids = @(4625, 4740, 4728, 4732, 4756, 4672, 4720, 4722, 4725, 4723, 4724, 4768, 4771)
            $filter = @{{
                LogName = 'Security'
                Id = $ids
                StartTime = $startTime
                EndTime = $endTime
            }}
            $events = Get-WinEvent -FilterHashtable $filter -MaxEvents {max_events}
            foreach ($e in $events) {{
                $xml = [xml]$e.ToXml()
                $targetUser = ($xml.Event.EventData.Data | Where-Object {{ $_.Name -eq 'TargetUserName' }}).'#text'
                $ip = ($xml.Event.EventData.Data | Where-Object {{ $_.Name -eq 'IpAddress' }}).'#text'
                $workstation = ($xml.Event.EventData.Data | Where-Object {{ $_.Name -eq 'WorkstationName' }}).'#text'
                $status = ($xml.Event.EventData.Data | Where-Object {{ $_.Name -eq 'Status' }}).'#text'
                $subStatus = ($xml.Event.EventData.Data | Where-Object {{ $_.Name -eq 'SubStatus' }}).'#text'
                $failureCode = ($xml.Event.EventData.Data | Where-Object {{ $_.Name -eq 'FailureCode' }}).'#text'

                $res += [PSCustomObject]@{{
                    EventID = $e.Id
                    TimeCreated = $e.TimeCreated.ToString('o')
                    TargetUserName = $targetUser
                    IpAddress = $ip
                    WorkstationName = $workstation
                    Status = $status
                    SubStatus = $subStatus
                    FailureCode = $failureCode
                    Message = ($e.Message -split "`r?`n")[0]
                }}
            }}
        }} catch {{
            if ($_.Exception.Message -notlike "*No events were found that match the specified selection criteria*") {{
                Write-Error $_.Exception.Message
                exit 1
            }}
        }}
        $res | ConvertTo-Json -Compress
        """

        result = session.run_ps(ps_script)

        # Do not swallow PowerShell errors!
        if result.status_code != 0:
            err_msg = result.std_err.decode("utf-8", errors="ignore").strip()
            raise RuntimeError(f"Active Directory WinRM execution failed (exit code {result.status_code}): {err_msg}")

        raw_out = result.std_out.decode("utf-8", errors="ignore").strip()
        if raw_out:
            try:
                parsed_json = json.loads(raw_out)
                items = parsed_json if isinstance(parsed_json, list) else [parsed_json]
                records_fetched = len(items)
                for it in items:
                    if len(events) >= request.max_records or request.is_cancelled():
                        has_more = True
                        break
                    try:
                        parsed = self.parse_security_event(it)
                        if start_dt <= parsed.timestamp <= end_dt:
                            events.append(parsed)
                            records_parsed += 1
                        else:
                            records_ignored += 1
                    except Exception:
                        records_malformed += 1
            except Exception as parse_err:
                logger.warning("Error parsing AD JSON output: %s", parse_err)
                records_malformed += 1

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
            msg = f"Retrieved {len(events)} security events from Active Directory."
        elif records_fetched == 0:
            status = CollectorStatus.SUCCESS
            diag_code = "QUERY_EMPTY_ZERO_SOURCE"
            msg = f"Active Directory returned zero events for requested time window ({start_dt.isoformat()} to {end_dt.isoformat()})."
        elif records_ignored > 0 and records_parsed == 0:
            status = CollectorStatus.SUCCESS
            diag_code = "QUERY_EMPTY_FILTERED"
            msg = f"Active Directory returned {records_fetched} events but all were outside requested time range."
        elif records_malformed > 0 and records_parsed == 0:
            status = CollectorStatus.FAILED
            diag_code = "PARSE_ERROR"
            msg = f"Active Directory returned {records_fetched} events but none could be parsed."
        else:
            status = CollectorStatus.SUCCESS
            diag_code = "QUERY_EMPTY_ZERO_SOURCE"
            msg = "Zero events found."

        diagnostic = CollectorDiagnostic(
            collector_id="active_directory",
            device_name=self.device_name,
            canonical_entity="active_directory",
            stage=DiagnosticStage.COMPLETE,
            status=DiagnosticStatus.SUCCESS if status == CollectorStatus.SUCCESS else DiagnosticStatus.FAILED,
            diagnostic_code=diag_code,
            message=msg,
            requested_time_range=requested_time_range,
            observed_time_range=observed_time_range,
            transport="WINRM_PS",
            source_queried="Security EventLog (4625, 4740, 4728, 4732, 4756, 4672, 4720, 4768, 4771)",
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


class ExchangeCollector(BaseSecurityCollector):
    """Collector for Exchange 2019 (172.23.71.36).

    Collects message tracking logs, transport anomalies,
    OWA/ECP authentication events, and certificate status.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: int = 120,
    ):
        super().__init__(device_name="Exchange", timeout=timeout, collector_id="exchange_2019")
        self.host = host or os.getenv("MNE_EXCHANGE_HOST", "172.23.71.36")
        self.username = username or os.getenv("MNE_EXCHANGE_USERNAME", "")
        self.password = password or os.getenv("MNE_EXCHANGE_PASSWORD", "")

    def parse_tracking_log(self, item: Dict[str, Any]) -> NormalizedSecurityEvent:
        """Parses an Exchange tracking log item."""
        client_ip = item.get("client_ip") or item.get("ClientIp") or item.get("IpAddress")
        sender = item.get("sender") or item.get("Sender") or "unknown@external"
        reason = item.get("reason") or item.get("Message") or item.get("EventId", "")
        event_time = datetime.now(timezone.utc)
        ts_str = item.get("timestamp") or item.get("Timestamp") or item.get("TimeCreated")
        if ts_str:
            try:
                event_time = datetime.fromisoformat(str(ts_str).replace("Z", "+00:00")).replace(tzinfo=timezone.utc)
            except Exception:
                pass

        category = ThreatCategory.ANOMALY
        reason_lower = str(reason).lower()
        if "unable to relay" in reason_lower or item.get("event_type") == "FAIL" or "relay" in reason_lower:
            action = "BLOCKED"
            threat_name = f"Exchange Relay Attempt Blocked from {sender}"
        elif "spam" in reason_lower or "phish" in reason_lower:
            action = "DROPPED"
            category = ThreatCategory.PHISHING
            threat_name = f"Exchange Transport Block: {reason}"
        else:
            action = "ALERT"
            threat_name = f"Exchange Transport Anomaly: {reason}"

        raw_hash = hashlib.md5(f"{client_ip}_{sender}_{ts_str}_{reason}".encode()).hexdigest()[:10]

        return NormalizedSecurityEvent(
            event_id=f"ex-trk-{raw_hash}",
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

    def parse_security_event(self, item: Dict[str, Any]) -> NormalizedSecurityEvent:
        """Parses an Exchange Windows Security / OWA auth event."""
        event_id = int(item.get("EventID", 0))
        target_user = item.get("TargetUserName") or item.get("user") or "ExchangeUser"
        time_created = item.get("TimeCreated")

        event_time = datetime.now(timezone.utc)
        if time_created:
            try:
                event_time = datetime.fromisoformat(time_created.replace("Z", "+00:00")).replace(tzinfo=timezone.utc)
            except Exception:
                pass

        category = ThreatCategory.BRUTE_FORCE if event_id in (4625, 4740) else ThreatCategory.PRIVILEGE_CHANGE
        action = "DROPPED" if event_id == 4625 else ("BLOCKED" if event_id == 4740 else "ALLOWED")
        threat_name = f"Exchange OWA/Logon Failure: {target_user}" if event_id == 4625 else f"Exchange Security Event {event_id}: {target_user}"

        raw_hash = hashlib.md5(f"ex_sec_{event_id}_{target_user}_{time_created}".encode()).hexdigest()[:10]

        return NormalizedSecurityEvent(
            event_id=f"ex-sec-{raw_hash}",
            timestamp=event_time,
            source_device="Exchange",
            category=category,
            threat_name=threat_name,
            attacker_ip=item.get("IpAddress"),
            target=target_user,
            action_taken=action,
            count=1,
            raw_snippet=str(item)[:300],
            metadata=item,
        )

    def _fetch_logs_internal(self, hours_back: int) -> List[NormalizedSecurityEvent]:
        """Legacy entrypoint: validates credentials and calls _fetch_logs_with_request."""
        if not self.password:
            raise ValueError("MNE_EXCHANGE_PASSWORD is not configured in .env.")
        req = CollectorRequest(hours_back=hours_back)
        result = self._fetch_logs_with_request(req)
        return result.events

    def _fetch_logs_with_request(self, request: CollectorRequest) -> CollectorResult:
        """Queries Exchange message tracking and security logs via WinRM with time window filtering."""
        if not self.password:
            raise ValueError("MNE_EXCHANGE_PASSWORD is not configured in .env.")

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
        pages_retrieved = 1
        has_more = False

        import winrm
        session = winrm.Session(self.host, auth=(self.username, self.password), transport="ntlm")

        start_ps = start_dt.strftime("%Y-%m-%dT%H:%M:%S")
        end_ps = end_dt.strftime("%Y-%m-%dT%H:%M:%S")
        max_events = min(request.max_records, 300)

        # PowerShell script retrieving both tracking logs and security events separately
        ps_script = f"""
        $res = @{{
            tracking = @()
            security = @()
        }}
        $ErrorActionPreference = 'Stop'
        try {{
            $startTime = [DateTime]::Parse('{start_ps}')
            $endTime = [DateTime]::Parse('{end_ps}')

            # 1. Message Tracking Log (relay fails, drop events)
            try {{
                Add-PSSnapin Microsoft.Exchange.Management.PowerShell.SnapIn -ErrorAction SilentlyContinue
                $logs = Get-MessageTrackingLog -EventId FAIL -Start $startTime -End $endTime -ResultSize {max_events} -ErrorAction SilentlyContinue
                foreach ($l in $logs) {{
                    $res.tracking += [PSCustomObject]@{{
                        timestamp = $l.Timestamp.ToString('o')
                        client_ip = $l.ClientIp
                        sender = $l.Sender
                        recipients = $l.Recipients -join ';'
                        event_type = $l.EventId
                        reason = $l.MessageInfo
                    }}
                }}
            }} catch {{}}

            # 2. Windows Security Events (Exchange OWA / logon)
            try {{
                $secEvents = Get-WinEvent -FilterHashtable @{{
                    LogName = 'Security'
                    Id = @(4625, 4740, 4672)
                    StartTime = $startTime
                    EndTime = $endTime
                }} -MaxEvents {max_events} -ErrorAction SilentlyContinue
                foreach ($e in $secEvents) {{
                    $xml = [xml]$e.ToXml()
                    $user = ($xml.Event.EventData.Data | Where-Object {{ $_.Name -eq 'TargetUserName' }}).'#text'
                    $ip = ($xml.Event.EventData.Data | Where-Object {{ $_.Name -eq 'IpAddress' }}).'#text'
                    $res.security += [PSCustomObject]@{{
                        EventID = $e.Id
                        TimeCreated = $e.TimeCreated.ToString('o')
                        TargetUserName = $user
                        IpAddress = $ip
                        Message = ($e.Message -split "`r?`n")[0]
                    }}
                }}
            }} catch {{}}

        }} catch {{
            Write-Error $_.Exception.Message
            exit 1
        }}
        $res | ConvertTo-Json -Compress -Depth 3
        """

        result = session.run_ps(ps_script)

        # Do not swallow terminating errors
        if result.status_code != 0:
            err_msg = result.std_err.decode("utf-8", errors="ignore").strip()
            raise RuntimeError(f"Exchange WinRM execution failed (exit code {result.status_code}): {err_msg}")

        raw_out = result.std_out.decode("utf-8", errors="ignore").strip()
        if raw_out:
            try:
                data = json.loads(raw_out)
                tracking_items = data.get("tracking", [])
                if isinstance(tracking_items, dict):
                    tracking_items = [tracking_items]
                security_items = data.get("security", [])
                if isinstance(security_items, dict):
                    security_items = [security_items]

                records_fetched = len(tracking_items) + len(security_items)

                for item in tracking_items:
                    if len(events) >= request.max_records or request.is_cancelled():
                        has_more = True
                        break
                    try:
                        parsed = self.parse_tracking_log(item)
                        if start_dt <= parsed.timestamp <= end_dt:
                            events.append(parsed)
                            records_parsed += 1
                        else:
                            records_ignored += 1
                    except Exception:
                        records_malformed += 1

                for item in security_items:
                    if len(events) >= request.max_records or request.is_cancelled():
                        has_more = True
                        break
                    try:
                        parsed = self.parse_security_event(item)
                        if start_dt <= parsed.timestamp <= end_dt:
                            events.append(parsed)
                            records_parsed += 1
                        else:
                            records_ignored += 1
                    except Exception:
                        records_malformed += 1

            except Exception as parse_err:
                logger.warning("Error parsing Exchange JSON output: %s", parse_err)
                records_malformed += 1

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
            msg = f"Retrieved {len(events)} security and transport events from Exchange."
        elif records_fetched == 0:
            status = CollectorStatus.SUCCESS
            diag_code = "QUERY_EMPTY_ZERO_SOURCE"
            msg = f"Exchange returned zero events for requested time window ({start_dt.isoformat()} to {end_dt.isoformat()})."
        elif records_ignored > 0 and records_parsed == 0:
            status = CollectorStatus.SUCCESS
            diag_code = "QUERY_EMPTY_FILTERED"
            msg = f"Exchange returned {records_fetched} items but all were outside requested time range."
        elif records_malformed > 0 and records_parsed == 0:
            status = CollectorStatus.FAILED
            diag_code = "PARSE_ERROR"
            msg = f"Exchange returned {records_fetched} items but none could be parsed."
        else:
            status = CollectorStatus.SUCCESS
            diag_code = "QUERY_EMPTY_ZERO_SOURCE"
            msg = "Zero events found."

        diagnostic = CollectorDiagnostic(
            collector_id="exchange_2019",
            device_name=self.device_name,
            canonical_entity="exchange_2019",
            stage=DiagnosticStage.COMPLETE,
            status=DiagnosticStatus.SUCCESS if status == CollectorStatus.SUCCESS else DiagnosticStatus.FAILED,
            diagnostic_code=diag_code,
            message=msg,
            requested_time_range=requested_time_range,
            observed_time_range=observed_time_range,
            transport="WINRM_PS",
            source_queried="Get-MessageTrackingLog, Security EventLog (4625, 4740)",
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
