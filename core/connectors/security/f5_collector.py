import hashlib
import logging
import os
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional

from core.connectors.security.base import BaseSecurityCollector
from core.connectors.security.models import (
    NormalizedSecurityEvent,
    ThreatCategory,
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
        super().__init__(device_name="F5 BIG-IP", timeout=timeout)
        self.host = host or os.getenv("MNE_F5_HOST", "172.23.70.89")
        self.username = username or os.getenv("MNE_F5_USERNAME", "admin")
        self.password = password or os.getenv("MNE_F5_PASSWORD", "")

    def parse_asm_log_line(self, line: str) -> Optional[NormalizedSecurityEvent]:
        """Parses an F5 ASM attack log line (from /var/log/asm or remote syslog)."""
        if not line or "ASM:" not in line:
            return None

        # Extract Client IP
        client_ip_match = re.search(r'Client IP:\s*([0-9a-fA-F\.\:]+)', line)
        client_ip = client_ip_match.group(1) if client_ip_match else None

        # Extract Violations / Attack
        violations_match = re.search(r'Violations:\s*([^,]+)', line)
        violations = violations_match.group(1).strip() if violations_match else "ASM Security Violation"

        # Extract Action
        action_match = re.search(r'Action:\s*([A-Za-z]+)', line)
        action_raw = action_match.group(1).upper() if action_match else "ALERT"
        action = "BLOCKED" if "BLOCK" in action_raw else "ALLOWED"

        # Extract URL / Target
        url_match = re.search(r'URL:\s*(\S+)', line)
        target = url_match.group(1) if url_match else "Web Application"

        # Support ID
        support_id_match = re.search(r'Support ID:\s*([0-9]+)', line)
        support_id = support_id_match.group(1) if support_id_match else "0"

        event_id = f"f5-asm-{support_id}"
        event_time = datetime.now(timezone.utc)

        return NormalizedSecurityEvent(
            event_id=event_id,
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

    def parse_syslog_line(self, line: str) -> Optional[NormalizedSecurityEvent]:
        """Parses F5 LTM / system warnings (certificate expiry, pool member failure)."""
        if not line or not line.strip():
            return None

        line_lower = line.lower()
        if "certificate" in line_lower and "expire" in line_lower:
            cert_match = re.search(r'Certificate\s+(\S+).*?expire in\s+(\d+\s+\w+)', line, re.IGNORECASE)
            cert_name = cert_match.group(1) if cert_match else "SSL Certificate"
            expiry_time = cert_match.group(2) if cert_match else "soon"
            raw_hash = hashlib.md5(line.encode("utf-8")).hexdigest()[:10]

            return NormalizedSecurityEvent(
                event_id=f"f5-cert-{raw_hash}",
                timestamp=datetime.now(timezone.utc),
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
                timestamp=datetime.now(timezone.utc),
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
        """Collects logs over SSH from F5 BIG-IP."""
        events: List[NormalizedSecurityEvent] = []
        if not self.password:
            logger.warning("F5 password not configured. Skipping live fetch.")
            return events

        import paramiko
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(
                hostname=self.host,
                username=self.username,
                password=self.password,
                timeout=45,
                look_for_keys=False,
                allow_agent=False,
            )
            # Read ASM logs
            cmd_asm = "tail -n 200 /var/log/asm 2>/dev/null || true"
            stdin, stdout, stderr = client.exec_command(cmd_asm, timeout=self.timeout)
            for line in stdout.read().decode("utf-8", errors="ignore").splitlines():
                parsed = self.parse_asm_log_line(line)
                if parsed:
                    events.append(parsed)

            # Read LTM logs for cert warnings & pool drops
            cmd_ltm = "tail -n 200 /var/log/ltm 2>/dev/null || true"
            stdin, stdout, stderr = client.exec_command(cmd_ltm, timeout=self.timeout)
            for line in stdout.read().decode("utf-8", errors="ignore").splitlines():
                parsed = self.parse_syslog_line(line)
                if parsed:
                    events.append(parsed)

        finally:
            client.close()

        return events
