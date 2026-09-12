import collections
from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from core.connectors.security.models import (
    Incident,
    NormalizedSecurityEvent,
    SeverityLevel,
    ThreatCategory,
    normalize_action,
)
from core.security_review.incidents import generate_fingerprint


def extract_signature_family(category: ThreatCategory, threat_name: str, metadata: Optional[Dict[str, Any]] = None) -> str:
    """Extracts a normalized signature/threat family to prevent collapsing unrelated threats."""
    meta = metadata or {}
    # Check explicit metadata fields first
    explicit_sig = meta.get("signature_id") or meta.get("signature") or meta.get("attack_name") or meta.get("rule_id")
    if explicit_sig and isinstance(explicit_sig, str) and explicit_sig.strip():
        norm_sig = re.sub(r"[^a-zA-Z0-9_.-]", "_", explicit_sig.strip().lower())
        if len(norm_sig) >= 3:
            return norm_sig

    raw = (threat_name or "").lower()
    # Strip common appliance prefixes
    cleaned = re.sub(r"^\[[^\]]+\]\s*", "", raw)
    cleaned = re.sub(r"^(ips attack|waf violation|av|email threat|firewall event):\s*", "", cleaned).strip()

    # Pattern recognition for well-known signature families
    if "log4j" in cleaned or "cve-2021-44228" in cleaned:
        return "log4j"
    if any(k in cleaned for k in ("sqli", "sql-injection", "sql injection", "union select")):
        return "sqli"
    if any(k in cleaned for k in ("xss", "cross-site scripting", "cross site scripting")):
        return "xss"
    if any(k in cleaned for k in ("rce", "remote code execution", "command injection", "remote code")):
        return "rce"
    if any(k in cleaned for k in ("path-traversal", "directory traversal", "etc/passwd", "lfi")):
        return "path-traversal"
    if any(k in cleaned for k in ("ssl-vpn failed logon", "ssl-vpn login fail", "failed logon", "login fail", "bad password", "brute force", "account lockout")):
        return "brute-force"
    if any(k in cleaned for k in ("lockbit", "ransomware", "trojan", "backdoor", "virus", "malware", "sandstorm")):
        return "malware"
    if any(k in cleaned for k in ("phishing", "spoof", "spf-fail", "dkim-fail", "dmarc-fail", "spam")):
        return "phishing"
    if any(k in cleaned for k in ("domain admins", "enterprise admins", "schema admins", "privilege change", "admin group")):
        return "privilege-escalation"
    if any(k in cleaned for k in ("certificate", "ssl cert", "tls cert", "cert expiry")):
        return "cert-expiry"
    if any(k in cleaned for k in ("c2", "command and control", "beacon", "botnet")):
        return "c2"

    # Fallback to normalized alphanumeric root
    tokens = re.findall(r"[a-z0-9]+", cleaned)
    if tokens:
        return "-".join(tokens[:3])
    cat_val = category.value if hasattr(category, "value") else str(category)
    return cat_val.lower()


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
        is_multi_branch: bool = False,
        crlevel: str = "",
        sig_family: str = "",
        with_rationale: bool = False,
    ) -> SeverityLevel | Tuple[SeverityLevel, str]:
        """Applies Standard Enterprise SOC classification rules.
        Supports Low and Informational results without filling the incident list with noise.
        """
        threat_lower = threat_name.lower()
        crlevel_lower = (crlevel or "").lower()
        family_lower = (sig_family or extract_signature_family(category, threat_name)).lower()
        norm_action = normalize_action(action_taken)

        sev: SeverityLevel = SeverityLevel.MEDIUM
        rationale: str = "Standard security event observed."

        # 1. Critical Rules
        if norm_action == "ALLOWED" and category in (
            ThreatCategory.MALWARE,
            ThreatCategory.INTRUSION,
            ThreatCategory.WAF_EXPLOIT,
        ):
            sev = SeverityLevel.CRITICAL
            rationale = f"Unblocked active {category.value} threat was allowed through perimeter policy."
        elif category == ThreatCategory.PRIVILEGE_CHANGE and any(
            g in threat_lower for g in ("domain admins", "enterprise admins", "schema admins")
        ):
            sev = SeverityLevel.CRITICAL
            rationale = "Privilege escalation detected on Tier-0 administrative security group."
        elif "zero-day" in threat_lower or "sandstorm" in threat_lower or crlevel_lower == "critical":
            sev = SeverityLevel.CRITICAL
            rationale = "High-confidence critical severity rating or zero-day sandbox detonation."
        elif (is_multi_device or is_multi_branch) and category in (
            ThreatCategory.INTRUSION,
            ThreatCategory.MALWARE,
            ThreatCategory.WAF_EXPLOIT,
        ):
            sev = SeverityLevel.CRITICAL
            rationale = f"Coordinated {category.value} campaign observed spreading across multiple perimeters or branch firewalls."

        # 2. High Rules
        elif is_multi_device or is_multi_branch:
            sev = SeverityLevel.HIGH
            rationale = "Attack activity correlated across multiple perimeters or ministry branch firewalls."
        elif category == ThreatCategory.BRUTE_FORCE and count >= 20:
            sev = SeverityLevel.HIGH
            rationale = f"High-volume brute force credential stuffing detected ({count} attempts)."
        elif category == ThreatCategory.MALWARE:
            sev = SeverityLevel.HIGH
            rationale = "Malicious malware or virus payload blocked by perimeter security controls."
        elif category in (ThreatCategory.INTRUSION, ThreatCategory.WAF_EXPLOIT):
            if any(k in family_lower or k in threat_lower for k in ("sqli", "sql-injection", "log4j", "rce", "remote code", "c2", "command and control", "path-traversal")):
                sev = SeverityLevel.HIGH
                rationale = f"High-impact exploit signature family '{family_lower}' targeted at infrastructure."
            else:
                sev = SeverityLevel.HIGH
                rationale = "Intrusion or WAF attack signature observed and contained."
        elif "certificate" in threat_lower and any(d in threat_lower for d in ("1 day", "2 days", "3 days", "4 days", "5 days", "6 days", "7 days")):
            sev = SeverityLevel.HIGH
            rationale = "SSL/TLS production certificate expiring in under 7 days."

        # 3. Medium Rules
        elif category == ThreatCategory.BRUTE_FORCE and count >= 5:
            sev = SeverityLevel.MEDIUM
            rationale = f"Repeated authentication failures detected ({count} attempts)."
        elif any(w in threat_lower for w in ("audit", "routine", "backup", "cleared")) or crlevel_lower in ("info", "informational"):
            sev = SeverityLevel.INFO
            rationale = "Informational operational telemetry or routine administrative action."
        elif category == ThreatCategory.PHISHING:
            sev = SeverityLevel.MEDIUM
            rationale = "Suspicious email or phishing indicator quarantined by mail protection."
        elif category in (ThreatCategory.SYSTEM_HEALTH, ThreatCategory.ANOMALY):
            if any(w in threat_lower for w in ("fail", "error", "down", "degraded", "exhaust", "high", "alert")):
                sev = SeverityLevel.MEDIUM
                rationale = f"Operational alert or anomaly categorized under {category.value}."
            else:
                sev = SeverityLevel.LOW
                rationale = "Low-impact operational telemetry or minor health notification."
        elif "certificate" in threat_lower and ("expir" in threat_lower or "cert" in threat_lower):
            sev = SeverityLevel.MEDIUM
            rationale = "SSL/TLS certificate maintenance notification."

        # 4. Low Rules
        elif category == ThreatCategory.BRUTE_FORCE and count < 5:
            sev = SeverityLevel.LOW
            rationale = f"Low-volume isolated authentication failure ({count} attempt(s))."
        elif category == ThreatCategory.PRIVILEGE_CHANGE:
            sev = SeverityLevel.LOW
            rationale = "Standard user account or non-privileged group modification."
        elif category in (ThreatCategory.SYSTEM_HEALTH, ThreatCategory.ANOMALY) and norm_action in ("ALLOWED", "UNKNOWN"):
            sev = SeverityLevel.LOW
            rationale = "Low-impact operational telemetry or minor health notification."

        if with_rationale:
            return sev, rationale
        return sev

    def process_events(self, events: List[NormalizedSecurityEvent]) -> List[Incident]:
        """Groups raw normalized events into consolidated, correlated Incidents.
        Guarantees that different exploit signatures or targets are not merged
        merely because an IP matches.
        """
        if not events:
            return []

        # Check for multi-device attacker IPs
        ip_device_map: Dict[str, Set[str]] = collections.defaultdict(set)
        # Check for multi-branch attacker IPs (across firewalls reported via FortiAnalyzer)
        ip_branch_map: Dict[str, Set[str]] = collections.defaultdict(set)
        # Check for signature-family scope across branches/devices
        ip_sig_branch_map: Dict[Tuple[str, str], Set[str]] = collections.defaultdict(set)
        ip_sig_device_map: Dict[Tuple[str, str], Set[str]] = collections.defaultdict(set)

        for ev in events:
            if ev.attacker_ip:
                ip_device_map[ev.attacker_ip].add(ev.source_device)
                branch = ev.metadata.get("reporting_firewall") or ev.metadata.get("devname")
                if branch and branch != "FortiGate":
                    ip_branch_map[ev.attacker_ip].add(branch)

                sig_fam = extract_signature_family(ev.category, ev.threat_name, ev.metadata)
                ip_sig_device_map[(ev.attacker_ip, sig_fam)].add(ev.source_device)
                if branch and branch != "FortiGate":
                    ip_sig_branch_map[(ev.attacker_ip, sig_fam)].add(branch)

        multi_device_ips = {ip for ip, devices in ip_device_map.items() if len(devices) > 1}
        multi_branch_ips = {ip for ip, branches in ip_branch_map.items() if len(branches) > 1}

        # Deduplication grouping:
        # Group key MUST NOT collapse unrelated threats merely because they share an attacker IP and category.
        # It includes category, signature_family, and target scope.
        groups: Dict[Tuple[Any, ...], List[NormalizedSecurityEvent]] = collections.defaultdict(list)

        for ev in events:
            sig_fam = extract_signature_family(ev.category, ev.threat_name, ev.metadata)
            attacker = ev.attacker_ip
            target = ev.target or "perimeter"

            # Check if this specific signature family is participating in a multi-branch or multi-device campaign
            is_campaign_branch = attacker and len(ip_sig_branch_map.get((attacker, sig_fam), set())) > 1
            is_campaign_dev = attacker and len(ip_sig_device_map.get((attacker, sig_fam), set())) > 1

            if is_campaign_branch:
                # Coordinated campaign targeting multiple branches with same signature family
                key = ("MULTI_BRANCH", attacker, ev.category, sig_fam)
            elif is_campaign_dev:
                # Coordinated attack hitting multiple devices with same signature family
                key = ("MULTI_DEVICE", attacker, ev.category, sig_fam)
            elif attacker:
                # Attacker targeting specific target/device with specific signature family
                key = ("ATTACKER", attacker, ev.category, sig_fam, target, ev.source_device)
            else:
                # Internal / system / target event with specific signature family
                key = ("INTERNAL", target, ev.category, sig_fam, ev.source_device)

            groups[key].append(ev)

        incidents: List[Incident] = []
        today_str = datetime.now(timezone.utc).strftime("%Y%m%d")

        for key, group_events in groups.items():
            first_event = group_events[0]
            attacker_ip = first_event.attacker_ip
            category = first_event.category
            sig_fam = extract_signature_family(category, first_event.threat_name, first_event.metadata)

            total_count = sum(e.count for e in group_events)
            first_seen = min(e.timestamp for e in group_events)
            last_seen = max(e.timestamp for e in group_events)

            # Preserved detailed collections
            devices_involved = sorted(list({e.source_device for e in group_events if e.source_device}))
            branches_involved = sorted(list({
                e.metadata.get("reporting_firewall") or e.metadata.get("devname")
                for e in group_events
                if (e.metadata.get("reporting_firewall") or e.metadata.get("devname"))
                and (e.metadata.get("reporting_firewall") or e.metadata.get("devname")) != "FortiGate"
            }))
            affected_targets = sorted(list({e.target for e in group_events if e.target}))
            observed_dispositions = sorted(list({normalize_action(e.action_taken) for e in group_events}))
            supporting_event_ids = [e.event_id for e in group_events if e.event_id]
            distinct_signatures = sorted(list({e.threat_name for e in group_events if e.threat_name}))

            blocked_count = sum(e.count for e in group_events if normalize_action(e.action_taken) in ("BLOCKED", "DROPPED"))
            allowed_count = sum(e.count for e in group_events if normalize_action(e.action_taken) == "ALLOWED")

            has_allowed = allowed_count > 0
            primary_action = "ALLOWED" if has_allowed else (observed_dispositions[0] if observed_dispositions else "UNKNOWN")

            # Check multi-device / multi-branch context
            group_type = key[0]
            is_multi_branch = (group_type == "MULTI_BRANCH") or (attacker_ip and attacker_ip in multi_branch_ips)
            is_multi_dev = (group_type == "MULTI_DEVICE") or (attacker_ip and attacker_ip in multi_device_ips)

            source_device = " / ".join(devices_involved) if len(devices_involved) > 1 else (devices_involved[0] if devices_involved else "Perimeter")
            primary_target = affected_targets[0] if affected_targets else (first_event.target or "Perimeter")

            crlevels = [e.metadata.get("faz_crlevel", "") for e in group_events if e.metadata.get("faz_crlevel")]
            highest_crlevel = "critical" if any(c.lower() == "critical" for c in crlevels) else (crlevels[0] if crlevels else "")

            eval_res = self.evaluate_severity(
                category=category,
                threat_name=first_event.threat_name,
                action_taken=primary_action,
                count=total_count,
                is_multi_device=is_multi_dev,
                is_multi_branch=is_multi_branch,
                crlevel=highest_crlevel,
                sig_family=sig_fam,
                with_rationale=True,
            )
            severity, severity_rationale = eval_res

            # Title construction
            if is_multi_branch:
                title_prefix = "[Multi-Branch Coordinated Campaign] "
            elif is_multi_dev:
                title_prefix = "[Multi-Device Coordinated Attack] "
            else:
                title_prefix = ""

            title = f"{title_prefix}{first_event.threat_name}"
            if total_count > 1 and "Failure" in title:
                title = f"{title_prefix}Repeated {first_event.threat_name} ({total_count} attempts)"

            branch_info = f" Targeted branch firewalls: {', '.join(branches_involved)}." if len(branches_involved) > 1 else (f" Branch: {branches_involved[0]}." if branches_involved else "")

            desc = (
                f"Observed {total_count} security event(s) across {source_device}.{branch_info} "
                f"Target: {primary_target}. Action: {primary_action} ({blocked_count} blocked, {allowed_count} allowed)."
            )

            # Generate stable cross-run fingerprint
            source_scope = "Multi-Branch" if is_multi_branch else ("Multi-Device" if is_multi_dev else source_device)
            target_scope = "campaign" if (is_multi_branch or is_multi_dev) else primary_target
            branch_scope = ",".join(branches_involved) if branches_involved else "core"

            fp = generate_fingerprint(
                category=category.value if hasattr(category, "value") else str(category),
                signature_family=sig_fam,
                source_scope=source_scope,
                attacker_identity=attacker_ip or "none",
                target_identity=target_scope,
                branch_scope=branch_scope,
            )

            incident = Incident(
                incident_id="",  # Assigned sequentially after sorting
                title=title,
                severity=severity,
                source_device=source_device,
                category=category,
                first_seen=first_seen,
                last_seen=last_seen,
                description=desc,
                action_taken=primary_action,
                event_count=total_count,
                attacker_ip=attacker_ip,
                target=primary_target,
                fingerprint=fp,
                signature_family=sig_fam,
                devices_involved=devices_involved,
                branches_involved=branches_involved,
                affected_targets=affected_targets,
                observed_dispositions=observed_dispositions,
                supporting_event_ids=supporting_event_ids,
                distinct_signatures=distinct_signatures,
                blocked_count=blocked_count,
                allowed_count=allowed_count,
                severity_rationale=severity_rationale,
                lifecycle_state="NEW",
                occurrence_count=1,
            )
            incidents.append(incident)

        # Sort incidents: CRITICAL first, then HIGH, then MEDIUM, then LOW, then INFO, then event_count desc
        severity_order = {
            SeverityLevel.CRITICAL: 0,
            SeverityLevel.HIGH: 1,
            SeverityLevel.MEDIUM: 2,
            SeverityLevel.LOW: 3,
            SeverityLevel.INFO: 4,
        }
        incidents.sort(key=lambda x: (severity_order.get(x.severity, 99), -x.event_count))

        # Assign clean incremental daily display IDs
        for idx, inc in enumerate(incidents, start=1):
            disp_id = f"MNE-SEC-{today_str}-{idx:02d}"
            inc.incident_id = disp_id
            inc.display_id = disp_id

        return incidents
