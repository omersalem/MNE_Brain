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


class FortiAnalyzerSecurityCollector(BaseSecurityCollector):
    """Collector for FortiAnalyzer Central Log & Analytics Appliance (172.23.71.206).

    Collects aggregated UTM, IPS, Antivirus, Web Filter, Application Control,
    and IOC security logs across all 14 ministry firewalls.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        api_key: Optional[str] = None,
        ssh_port: Optional[int] = None,
        timeout: int = 120,
    ):
        super().__init__(device_name="FortiAnalyzer", timeout=timeout)
        self.host = host if host is not None else os.getenv("MNE_FORTIANALYZER_HOST", "172.23.71.206")
        self.username = username if username is not None else os.getenv("MNE_FORTIANALYZER_USERNAME", "admin")
        self.password = password if password is not None else os.getenv("MNE_FORTIANALYZER_PASSWORD", "")
        self.api_key = api_key if api_key is not None else os.getenv("MNE_FORTIANALYZER_API_KEY", "")
        port_env = os.getenv("MNE_FORTIANALYZER_SSH_PORT", "22")
        self.ssh_port = ssh_port or (int(port_env) if port_env.isdigit() else 22)

    def parse_key_value_pairs(self, line: str) -> Dict[str, str]:
        """Parses standard Fortinet syslog key=value or key=\"value\" pairs."""
        pattern = re.compile(r'([a-zA-Z0-9_]+)=(?:"([^"]*)"|(\S+))')
        data: Dict[str, str] = {}
        for match in pattern.finditer(line):
            key = match.group(1)
            value = match.group(2) if match.group(2) is not None else match.group(3)
            data[key] = value
        return data

    def parse_log_line(self, line: str) -> Optional[NormalizedSecurityEvent]:
        """Converts a raw FortiAnalyzer log line into a NormalizedSecurityEvent."""
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
        virus = fields.get("virus", "")
        app = fields.get("app", "")
        url = fields.get("url", "")
        devname = fields.get("devname") or fields.get("devid") or "FortiGate"
        crlevel = fields.get("crlevel") or fields.get("level", "")

        # Target & Attacker attribution
        attacker_ip = fields.get("srcip") or fields.get("remip")
        target = fields.get("dstip") or fields.get("user") or fields.get("hostname")

        # Determine Category & Threat Name
        category = ThreatCategory.ANOMALY
        base_threat = msg or attack or virus or app or "FortiAnalyzer Security Event"

        if subtype == "vpn" or "vpn login fail" in msg.lower() or "negotiation failure" in fields.get("reason", "").lower():
            category = ThreatCategory.BRUTE_FORCE
            base_threat = f"SSL-VPN Authentication Failure: {fields.get('user', 'unknown user')}"
            target = fields.get("user") or target
        elif subtype == "virus" or log_type == "virus" or virus:
            category = ThreatCategory.MALWARE
            base_threat = f"Malware / Virus Detected: {virus or msg}"
        elif subtype == "webfilter" or log_type == "webfilter" or url:
            category = ThreatCategory.INTRUSION if "malicious" in msg.lower() or "botnet" in msg.lower() else ThreatCategory.ANOMALY
            target_url = url or fields.get("hostname") or msg
            base_threat = f"Web Filter Security Block: {target_url}"
        elif subtype in ("ips", "signature") or log_type in ("ips", "utm") or attack:
            category = ThreatCategory.INTRUSION
            base_threat = f"IPS Attack: {attack or msg}"
        elif subtype == "app-ctrl" or log_type == "app-ctrl" or app:
            category = ThreatCategory.ANOMALY
            base_threat = f"High-Risk Application Activity: {app or msg}"
        elif subtype in ("system", "admin"):
            if "login" in msg.lower():
                category = ThreatCategory.PRIVILEGE_CHANGE
                base_threat = f"Admin Login Event: {msg}"
            else:
                category = ThreatCategory.SYSTEM_HEALTH
                base_threat = f"System Event: {msg}"

        # Prefix threat name with originating firewall identity
        threat_name = f"[{devname}] {base_threat}"

        # Action normalization
        if action in ("dropped", "block", "blocked", "deny", "tunnel-down", "clear", "quarantine"):
            normalized_action = "DROPPED"
        elif action in ("passthrough", "allowed", "accept", "permit"):
            normalized_action = "ALLOWED"
        else:
            normalized_action = "ALERT"

        # Unique event ID hash
        raw_hash = hashlib.md5(
            f"faz_{line}_{fields.get('date')}_{fields.get('time')}_{fields.get('eventtime')}".encode("utf-8")
        ).hexdigest()[:12]
        event_id = f"faz-{raw_hash}"

        event_time = datetime.now(timezone.utc)
        if "date" in fields and "time" in fields:
            try:
                dt_str = f"{fields['date']} {fields['time']}"
                event_time = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            except Exception:
                pass

        # Preserve originating firewall in metadata for multi-branch correlation
        metadata = dict(fields)
        metadata["reporting_firewall"] = devname
        metadata["devname"] = devname
        metadata["faz_crlevel"] = crlevel

        return NormalizedSecurityEvent(
            event_id=event_id,
            timestamp=event_time,
            source_device="FortiAnalyzer",
            category=category,
            threat_name=threat_name,
            attacker_ip=attacker_ip,
            target=target,
            action_taken=normalized_action,
            count=1,
            raw_snippet=line.strip()[:300],
            metadata=metadata,
        )

    def _fetch_logs_internal(self, hours_back: int) -> List[NormalizedSecurityEvent]:
        """Queries FortiAnalyzer via SSH or API to collect central security logs."""
        events: List[NormalizedSecurityEvent] = []

        if not self.password and not self.api_key:
            raise ValueError("Neither MNE_FORTIANALYZER_PASSWORD nor MNE_FORTIANALYZER_API_KEY is configured in .env.")

        # API token / JSON-RPC pathway if configured
        if self.api_key:
            import requests
            url = f"https://{self.host}/jsonrpc"
            payload = {
                "method": "get",
                "params": [
                    {
                        "url": "logview/adom/root/logsearch",
                        "apiver": 3,
                        "filter": "type=utm or type=ips or type=virus",
                        "limit": 50,
                    }
                ],
                "session": self.api_key,
                "id": 1,
            }
            resp = requests.post(url, json=payload, verify=False, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("result", [{}])[0].get("data", [])
                for item in results:
                    line_str = " ".join(f'{k}="{v}"' for k, v in item.items())
                    parsed = self.parse_log_line(line_str)
                    if parsed:
                        events.append(parsed)
            return events

        # SSH CLI query pathway via fortilogd
        import paramiko

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(
                hostname=self.host,
                port=self.ssh_port,
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

            # Query real-time aggregated security log stream across all 14 firewalls
            shell.send("diagnose test application fortilogd 5 75\n")
            time.sleep(1)

            full_output = ""
            start = time.time()
            while time.time() - start < 4:
                if shell.recv_ready():
                    chunk = shell.recv(65536).decode("utf-8", errors="ignore")
                    full_output += chunk
                time.sleep(0.5)

            # Parse all incoming normalized Fortinet log lines
            for line in full_output.splitlines():
                line_clean = line.strip()
                if "devname=" in line_clean:
                    parsed = self.parse_log_line(line_clean)
                    if parsed:
                        events.append(parsed)

        finally:
            client.close()

        return events
