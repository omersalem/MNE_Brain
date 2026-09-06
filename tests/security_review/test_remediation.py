from datetime import datetime, timezone
from core.connectors.security.models import Incident, SeverityLevel, ThreatCategory
from core.security_review.playbooks import attach_remediation_playbooks
from core.security_review.remediator import RemediationExecutor

def test_fortigate_vpn_brute_force_playbook():
    now = datetime.now(timezone.utc)
    incident = Incident(
        incident_id="MNE-SEC-20260906-01",
        title="SSL-VPN Brute Force",
        severity=SeverityLevel.HIGH,
        source_device="FortiGate",
        category=ThreatCategory.BRUTE_FORCE,
        first_seen=now,
        last_seen=now,
        description="Persistent brute-force from 185.220.101.5",
        action_taken="DROPPED",
        attacker_ip="185.220.101.5",
        target="admin"
    )
    attach_remediation_playbooks(incident)
    assert len(incident.remediation_cli) > 0
    assert any("diagnose user ban add src-ip 185.220.101.5" in cmd for cmd in incident.remediation_cli)
    assert incident.remediation_mode_b_command is not None
    assert "remediate incident MNE-SEC-20260906-01" in incident.remediation_mode_b_command
    assert len(incident.remediation_gui) > 0

def test_f5_asm_remediation_playbook():
    now = datetime.now(timezone.utc)
    incident = Incident(
        incident_id="MNE-SEC-20260906-02",
        title="WAF Violation: SQL-Injection",
        severity=SeverityLevel.HIGH,
        source_device="F5 BIG-IP",
        category=ThreatCategory.WAF_EXPLOIT,
        first_seen=now,
        last_seen=now,
        description="SQL injection attempts from 194.26.29.112",
        action_taken="BLOCKED",
        attacker_ip="194.26.29.112",
        target="/portal/login.aspx"
    )
    attach_remediation_playbooks(incident)
    assert any("tmsh modify /sys datagroup" in cmd for cmd in incident.remediation_cli)
    assert any("Traffic Learning" in step for step in incident.remediation_gui)

def test_ad_privilege_change_playbook():
    now = datetime.now(timezone.utc)
    incident = Incident(
        incident_id="MNE-SEC-20260906-03",
        title="Member added to Domain Admins",
        severity=SeverityLevel.CRITICAL,
        source_device="Active Directory",
        category=ThreatCategory.PRIVILEGE_CHANGE,
        first_seen=now,
        last_seen=now,
        description="Unauthorized addition of TempAdmin to Domain Admins",
        action_taken="ALLOWED",
        target="TempAdmin"
    )
    attach_remediation_playbooks(incident)
    assert any("Remove-ADGroupMember" in cmd for cmd in incident.remediation_cli)
    assert any("Disable-ADAccount" in cmd for cmd in incident.remediation_cli)

def test_remediation_whitelist_protection():
    # Attempting to remediate an internal core IP or DNS must be rejected by safety check
    executor = RemediationExecutor()
    is_safe, reason = executor.validate_target_safety("172.23.71.27") # MNE-DC1 IP
    assert not is_safe
    assert "protected infrastructure IP" in reason

    is_safe2, _ = executor.validate_target_safety("185.220.101.5")
    assert is_safe2
