import hashlib
import logging
import os
import re
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()

from core.connectors.security.base import BaseSecurityCollector
from core.connectors.security.models import (
    NormalizedSecurityEvent,
    ThreatCategory,
)

logger = logging.getLogger(__name__)


class FortiGateSecurityCollector(BaseSecurityCollector):
    """Collector for FortiGate Edge Firewall (172.23.70.4).

    Collects IPS attacks, Antivirus/malware detections, SSL-VPN failed logins,
    and system administrator events.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = 120,
    ):
        super().__init__(device_name="FortiGate", timeout=timeout)
        self.host = host or os.getenv("MNE_FORTIGATE_HOST", "172.23.70.4")
        self.username = username or os.getenv("MNE_FORTIGATE_USERNAME", "admin")
        self.password = password or os.getenv("MNE_FORTIGATE_PASSWORD", "")
        self.api_key = api_key or os.getenv("MNE_FORTIGATE_API_KEY", "")

    def parse_key_value_pairs(self, line: str) -> Dict[str, str]:
        """Parses standard FortiGate syslog key=value or key="value" pairs."""
        pattern = re.compile(r'([a-zA-Z0-9_]+)=(?:"([^"]*)"|(\S+))')
        data = {}
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

        # Determine category & threat name
        category = ThreatCategory.ANOMALY
        threat_name = msg or attack or "FortiGate Security Event"
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
        elif log_type == "virus" or subtype == "virus":
            category = ThreatCategory.MALWARE
            threat_name = f"Malware Detected: {fields.get('virus', msg)}"
        elif subtype == "system" or subtype == "admin":
            if "login" in msg.lower():
                category = ThreatCategory.PRIVILEGE_CHANGE
                threat_name = f"Admin Login Event: {msg}"
            else:
                category = ThreatCategory.SYSTEM_HEALTH
                threat_name = f"System Event: {msg}"

        # Action normalization
        if action in ("dropped", "block", "deny", "tunnel-down", "clear"):
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
            metadata=fields,
        )

    def _fetch_logs_internal(self, hours_back: int) -> List[NormalizedSecurityEvent]:
        """Fetch logs from FortiGate using REST API or SSH."""
        events: List[NormalizedSecurityEvent] = []

        if not self.password and not self.api_key:
            raise ValueError("Neither MNE_FORTIGATE_PASSWORD nor MNE_FORTIGATE_API_KEY is configured in .env.")

        # If API key configured, use REST API
        if self.api_key:
            import requests
            url = f"https://{self.host}/api/v2/log/disk/event"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            resp = requests.get(url, headers=headers, verify=False, timeout=self.timeout)
            if resp.status_code == 200:
                for entry in resp.json().get("results", []):
                    parsed = self.parse_log_line(str(entry))
                    if parsed:
                        events.append(parsed)
            return events

        # If SSH credentials configured
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

            # Pull IPS / UTM attack logs from disk
            cmd_ips = "execute log filter device disk\nexecute log filter view-lines 50\nexecute log filter category 4\nexecute log display\n"
            shell.send(cmd_ips)
            time.sleep(2.5)
            output_ips = shell.recv(65536).decode("utf-8", errors="ignore")
            for line in output_ips.splitlines():
                parsed = self.parse_log_line(line)
                if parsed:
                    events.append(parsed)

            # Pull System / VPN events from disk
            cmd_sys = "execute log filter category 1\nexecute log display\n"
            shell.send(cmd_sys)
            time.sleep(2.5)
            output_sys = shell.recv(65536).decode("utf-8", errors="ignore")
            for line in output_sys.splitlines():
                parsed = self.parse_log_line(line)
                if parsed:
                    events.append(parsed)

        finally:
            client.close()

        return events
