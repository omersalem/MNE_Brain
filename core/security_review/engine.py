import collections
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from core.connectors.security.models import (
    Incident,
    NormalizedSecurityEvent,
    SeverityLevel,
    ThreatCategory,
)


class SecurityRiskEngine:
    """Normalizes, deduplicates, correlates, and scores cybersecurity risks across MNE."""

    def __init__(self):
        pass

    def evaluate_severity(
        self,
        category: ThreatCategory,
        threat_name: str,
        action_taken: str,
        count: int,
        is_multi_device: bool = False,
    ) -> SeverityLevel:
        """Applies Standard Enterprise SOC classification rules."""
        threat_lower = threat_name.lower()

        # 1. Critical Rules
        if action_taken == "ALLOWED" and category in (
            ThreatCategory.MALWARE,
            ThreatCategory.INTRUSION,
            ThreatCategory.WAF_EXPLOIT,
        ):
            return SeverityLevel.CRITICAL

        if category == ThreatCategory.PRIVILEGE_CHANGE and any(
            g in threat_lower for g in ("domain admins", "enterprise admins", "schema admins")
        ):
            return SeverityLevel.CRITICAL

        if "zero-day" in threat_lower or "sandstorm" in threat_lower:
            return SeverityLevel.CRITICAL

        # 2. High Rules
        if is_multi_device:
            return SeverityLevel.HIGH

        if category == ThreatCategory.BRUTE_FORCE and count >= 20:
            return SeverityLevel.HIGH

        if category == ThreatCategory.MALWARE:
            return SeverityLevel.HIGH

        if category in (ThreatCategory.INTRUSION, ThreatCategory.WAF_EXPLOIT):
            if any(k in threat_lower for k in ("sqli", "sql-injection", "log4j", "rce", "remote code", "c2", "command and control")):
                return SeverityLevel.HIGH
            return SeverityLevel.HIGH

        if "certificate" in threat_lower and any(d in threat_lower for d in ("1 day", "2 days", "3 days", "4 days", "5 days", "6 days", "7 days")):
            return SeverityLevel.HIGH

        # 3. Medium Rules
        if category in (ThreatCategory.BRUTE_FORCE, ThreatCategory.PHISHING, ThreatCategory.SYSTEM_HEALTH, ThreatCategory.ANOMALY):
            return SeverityLevel.MEDIUM

        return SeverityLevel.MEDIUM

    def process_events(self, events: List[NormalizedSecurityEvent]) -> List[Incident]:
        """Groups raw normalized events into consolidated, correlated Incidents."""
        if not events:
            return []

        # Check for multi-device attacker IPs
        ip_device_map = collections.defaultdict(set)
        for ev in events:
            if ev.attacker_ip:
                ip_device_map[ev.attacker_ip].add(ev.source_device)

        multi_device_ips = {ip for ip, devices in ip_device_map.items() if len(devices) > 1}

        # Deduplication grouping:
        # Group key: (attacker_ip or target, category, primary device or 'Multi-Device')
        groups: Dict[Tuple[str, ThreatCategory, str], List[NormalizedSecurityEvent]] = collections.defaultdict(list)

        for ev in events:
            if ev.attacker_ip and ev.attacker_ip in multi_device_ips:
                key = (ev.attacker_ip, ev.category, "Multi-Device")
            elif ev.attacker_ip:
                key = (ev.attacker_ip, ev.category, ev.source_device)
            else:
                key = (ev.target or ev.threat_name, ev.category, ev.source_device)
            groups[key].append(ev)

        incidents: List[Incident] = []
        today_str = datetime.now(timezone.utc).strftime("%Y%m%d")

        for key, group_events in groups.items():
            primary_id_val, category, dev_label = key
            first_event = group_events[0]
            attacker_ip = first_event.attacker_ip
            target = first_event.target
            total_count = sum(e.count for e in group_events)
            first_seen = min(e.timestamp for e in group_events)
            last_seen = max(e.timestamp for e in group_events)

            # Did any event succeed/get allowed?
            has_allowed = any(e.action_taken == "ALLOWED" for e in group_events)
            action_taken = "ALLOWED" if has_allowed else first_event.action_taken

            is_multi = dev_label == "Multi-Device" or (attacker_ip and attacker_ip in multi_device_ips)
            devices_involved = list({e.source_device for e in group_events})
            source_device = " / ".join(devices_involved) if len(devices_involved) > 1 else devices_involved[0]

            severity = self.evaluate_severity(
                category=category,
                threat_name=first_event.threat_name,
                action_taken=action_taken,
                count=total_count,
                is_multi_device=is_multi,
            )

            title_prefix = "[Multi-Device Coordinated Attack] " if is_multi else ""
            title = f"{title_prefix}{first_event.threat_name}"
            if total_count > 1 and "Failure" in title:
                title = f"{title_prefix}Repeated {first_event.threat_name} ({total_count} attempts)"

            desc = (
                f"Observed {total_count} security event(s) across {source_device}. "
                f"Target: {target or 'Perimeter'}. Action: {action_taken}."
            )

            incident = Incident(
                incident_id="", # Assigned during sort
                title=title,
                severity=severity,
                source_device=source_device,
                category=category,
                first_seen=first_seen,
                last_seen=last_seen,
                description=desc,
                action_taken=action_taken,
                event_count=total_count,
                attacker_ip=attacker_ip,
                target=target,
            )
            incidents.append(incident)

        # Sort incidents: CRITICAL first, then HIGH, then MEDIUM, then event_count desc
        severity_order = {
            SeverityLevel.CRITICAL: 0,
            SeverityLevel.HIGH: 1,
            SeverityLevel.MEDIUM: 2,
            SeverityLevel.LOW: 3,
            SeverityLevel.INFO: 4,
        }
        incidents.sort(key=lambda x: (severity_order.get(x.severity, 99), -x.event_count))

        # Assign clean incremental incident IDs
        for idx, inc in enumerate(incidents, start=1):
            inc.incident_id = f"MNE-SEC-{today_str}-{idx:02d}"

        return incidents
