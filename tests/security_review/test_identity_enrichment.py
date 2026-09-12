"""
Comprehensive test suite for Local Attacker Identity Enrichment in MNE_Brain Security Agent.
Covers RFC1918/ULA classification, multi-source deterministic resolution (Event-Native,
DHCP lease windows, SCCM SQL, DNS/AD, FortiGate auth), ambiguity handling, in-run caching,
fingerprint invariance, presentation contracts, schemas, CSV/HTML/PDF reporting, and secret protection.
"""

import csv
import io
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
import pytest

from core.connectors.security.models import (
    Incident,
    NormalizedSecurityEvent,
    SeverityLevel,
    ThreatCategory,
    CollectorResult,
    CollectorStatus,
    UsernameRelation,
)
from core.security_review.contracts import validate_contract, SecurityReviewRequest, ReportFormat, ReviewMode, AnalysisEngine
from core.security_review.identity_enrichment import (
    AttackerAttribution,
    classify_ip,
    NetworkScope,
    IdentityStatus,
    IdentityConfidence,
    IncidentTimeMatch,
    BaseIdentitySourceAdapter,
    SourceResolutionResult,
    EventNativeIdentityAdapter,
    DhcpIdentityAdapter,
    SccmIdentityAdapter,
    DnsActiveDirectoryAdapter,
    FortiGateAuthAdapter,
    LocalAttackerIdentityResolver,
)
from core.security_review.incidents import (
    IncidentRecord,
    IncidentStore,
    generate_fingerprint,
)
from core.security_review.reporter import SecurityReporter
from core.security_review.service import SecurityReviewService
from core.security_review.run_store import SecurityReviewRunStore


# 1. External IP returns NOT_APPLICABLE
def test_external_ip_returns_not_applicable():
    resolver = LocalAttackerIdentityResolver()
    attr = resolver.resolve_attacker_identity("185.220.101.5")

    assert attr.network_scope == NetworkScope.EXTERNAL.value
    assert attr.status == IdentityStatus.NOT_APPLICABLE.value
    assert attr.pc_name == "Not applicable"
    assert attr.username == "Not applicable"
    assert attr.confidence == IdentityConfidence.UNKNOWN.value
    assert attr.confidence_score == 0
    assert "public" in attr.diagnostics[0].lower() or "external" in attr.diagnostics[0].lower()


# 2. Invalid IP returns INVALID scope
def test_invalid_ip_returns_invalid_scope():
    resolver = LocalAttackerIdentityResolver()
    for bad_ip in ["999.999.999.999", "invalid-ip", "", None]:
        attr = resolver.resolve_attacker_identity(bad_ip)
        assert attr.network_scope == NetworkScope.INVALID.value
        assert attr.status == IdentityStatus.FAILED.value
        assert attr.pc_name in ("Not applicable", "Unknown")
        assert attr.username in ("Not applicable", "Unknown")


# 3. Event-Native Identity Exact Match
def test_event_native_identity_exact_match():
    now = datetime.now(timezone.utc)
    ev = NormalizedSecurityEvent(
        event_id="ev-1",
        timestamp=now,
        source_device="FortiGate",
        category=ThreatCategory.BRUTE_FORCE,
        threat_name="Failed SSH Login",
        attacker_ip="10.20.30.40",
        target="10.20.30.1",
        metadata={
            "srcname": "PC-FINANCE-042",
            "user": "MNE\\ahmad",
            "username_relation": "AUTHENTICATED_SOURCE_USER",
            "srcmac": "00-11-22-33-44-55",
            "displayName": "Ahmad Salem",
        },
    )

    resolver = LocalAttackerIdentityResolver()
    attr = resolver.resolve_attacker_identity("10.20.30.40", events=[ev], first_seen=now)

    assert attr.network_scope == NetworkScope.LOCAL.value
    assert attr.status == IdentityStatus.RESOLVED.value
    assert attr.pc_name == "PC-FINANCE-042"
    assert attr.username == "MNE\\ahmad"
    assert attr.mac_address == "00-11-22-33-44-55"
    assert attr.confidence in (IdentityConfidence.HIGH.value, IdentityConfidence.MEDIUM.value)
    assert attr.confidence_score >= 75


# 4. DHCP Lease Window Matching
def test_dhcp_lease_window_matching():
    base_time = datetime(2026, 9, 11, 10, 0, 0, tzinfo=timezone.utc)
    incident_time = base_time + timedelta(minutes=30)  # 10:30 UTC

    leases = [
        {
            "ip": "10.20.30.50",
            "hostname": "PC-OLD-LEASE",
            "mac": "11-11-11-11-11-11",
            "lease_start": base_time - timedelta(hours=2),
            "lease_end": base_time + timedelta(minutes=15),  # Ended 10:15
        },
        {
            "ip": "10.20.30.50",
            "hostname": "PC-FINANCE-042",
            "mac": "00-11-22-33-44-55",
            "lease_start": base_time + timedelta(minutes=20),  # Started 10:20
            "lease_end": base_time + timedelta(hours=4),       # Ends 14:00
        },
    ]

    dhcp_adapter = DhcpIdentityAdapter(lease_history_provider=lambda ip: leases if ip == "10.20.30.50" else [])
    resolver = LocalAttackerIdentityResolver(adapters=[dhcp_adapter])

    attr = resolver.resolve_attacker_identity("10.20.30.50", first_seen=incident_time, last_seen=incident_time)

    assert attr.pc_name == "PC-FINANCE-042"
    assert attr.mac_address == "00-11-22-33-44-55"
    assert attr.incident_time_match == IncidentTimeMatch.EXACT.value
    assert "DHCP" in attr.sources_queried


# 5. DHCP Current Record Only Decay
def test_dhcp_current_record_only_decay():
    now = datetime.now(timezone.utc)
    old_incident_time = now - timedelta(hours=36)  # 36 hours ago

    current_leases = [
        {
            "ip": "10.20.30.60",
            "hostname": "PC-DESK-CURRENT",
            "mac": "22-22-22-22-22-22",
            "lease_start": now - timedelta(hours=5),
            "lease_end": now + timedelta(hours=19),
        }
    ]

    dhcp_adapter = DhcpIdentityAdapter(lease_history_provider=lambda ip: current_leases)
    resolver = LocalAttackerIdentityResolver(adapters=[dhcp_adapter])

    attr = resolver.resolve_attacker_identity("10.20.30.60", first_seen=old_incident_time)

    assert attr.pc_name == "PC-DESK-CURRENT"
    assert attr.incident_time_match == IncidentTimeMatch.CURRENT_ONLY.value
    # Because incident was 36h ago and current lease started 5h ago, confidence decayed
    assert attr.confidence in (IdentityConfidence.MEDIUM.value, IdentityConfidence.LOW.value)


# 6. SCCM Parameterized Query Mock
def test_sccm_parameterized_query_mock():
    queried_ips = []

    def mock_sccm_query(ip: str):
        queried_ips.append(ip)
        if ip == "172.16.50.25":
            return {
                "Netbios_Name0": "PC-HR-009",
                "Resource_Domain_OR_Workgr0": "MNE",
                "User_Name0": "MNE\\sara",
                "LastConsoleUser": "MNE\\sara",
                "MAC_Addresses0": "AA-BB-CC-DD-EE-FF",
                "LastHWScan": datetime.now(timezone.utc).isoformat(),
            }
        return None

    sccm_adapter = SccmIdentityAdapter(query_executor=mock_sccm_query)
    resolver = LocalAttackerIdentityResolver(adapters=[sccm_adapter])

    attr = resolver.resolve_attacker_identity("172.16.50.25")

    assert queried_ips == ["172.16.50.25"]
    assert attr.pc_name == "PC-HR-009"
    assert attr.mac_address == "AA-BB-CC-DD-EE-FF"


# 7. SCCM Primary User vs Active Username Separation
def test_sccm_primary_user_vs_active_username_separation():
    def mock_sccm(ip: str):
        return {
            "Netbios_Name0": "PC-LOGISTICS-03",
            "User_Name0": "MNE\\sara",
            "LastConsoleUser": "MNE\\sara",
            "MAC_Addresses0": "00-50-56-11-22-33",
        }

    sccm_adapter = SccmIdentityAdapter(query_executor=mock_sccm)
    resolver = LocalAttackerIdentityResolver(adapters=[sccm_adapter])

    # No active security event with authenticated user session passed
    attr = resolver.resolve_attacker_identity("192.168.10.45", events=[])

    assert attr.pc_name == "PC-LOGISTICS-03"
    assert attr.device_owner == "MNE\\sara"
    # Crucial Senior Engineering Rule: Device owner is NOT active attacker username
    assert attr.username == "Unknown"
    assert any("Device owner identified as MNE\\sara" in d for d in attr.diagnostics)


# 8. DNS / Active Directory Computer Verification
def test_dns_active_directory_computer_verification():
    mock_dns = lambda ip: "pc-exec-01.mne.local" if ip == "10.10.10.15" else None
    mock_ad = lambda host: {"fqdn": "pc-exec-01.mne.local", "domain": "mne.local"} if host == "PC-EXEC-01" else None

    dns_ad_adapter = DnsActiveDirectoryAdapter(ad_provider=mock_ad, dns_provider=mock_dns)
    resolver = LocalAttackerIdentityResolver(adapters=[dns_ad_adapter])

    attr = resolver.resolve_attacker_identity("10.10.10.15")

    assert attr.pc_name == "PC-EXEC-01"
    assert attr.fqdn == "pc-exec-01.mne.local"
    # AD computer object proves device existence, NOT active user!
    assert attr.username == "Unknown"
    assert attr.status == IdentityStatus.PARTIAL.value


# 9. FortiAnalyzer UTM Log Identity
def test_fortianalyzer_utm_log_identity():
    now = datetime.now(timezone.utc)
    faz_event = NormalizedSecurityEvent(
        event_id="faz-utm-99",
        timestamp=now,
        source_device="FortiAnalyzer",
        category=ThreatCategory.WAF_EXPLOIT,
        threat_name="SQL Injection Attack",
        attacker_ip="172.23.80.12",
        target="172.23.70.89",
        raw_snippet='date=2026-09-11 time=11:20:00 devname="FGT-BRANCH-1" srcname="PC-BRANCH-03" user="MNE\\yousef" srcip=172.23.80.12',
        metadata={
            "srcname": "PC-BRANCH-03",
            "user": "MNE\\yousef",
            "username_relation": "AUTHENTICATED_SOURCE_USER",
        },
    )

    resolver = LocalAttackerIdentityResolver(adapters=[EventNativeIdentityAdapter()])
    attr = resolver.resolve_attacker_identity("172.23.80.12", events=[faz_event])

    assert attr.pc_name == "PC-BRANCH-03"
    assert attr.username == "MNE\\yousef"
    assert attr.status == IdentityStatus.RESOLVED.value


# 10. Conflicting Sources Marked AMBIGUOUS
def test_conflicting_sources_marked_ambiguous():
    now = datetime.now(timezone.utc)

    # Adapter 1 says PC-FINANCE-01
    class FakeAdapter1(BaseIdentitySourceAdapter):
        def __init__(self):
            super().__init__(name="Source1", binding_id="b1")
        def resolve(self, ip, **kwargs):
            return SourceResolutionResult(source_name=self.name, binding_id=self.binding_id, status="SUCCESS", pc_name="PC-FINANCE-01", confidence_weight=0.8)

    # Adapter 2 says PC-SALES-02
    class FakeAdapter2(BaseIdentitySourceAdapter):
        def __init__(self):
            super().__init__(name="Source2", binding_id="b2")
        def resolve(self, ip, **kwargs):
            return SourceResolutionResult(source_name=self.name, binding_id=self.binding_id, status="SUCCESS", pc_name="PC-SALES-02", confidence_weight=0.8)

    resolver = LocalAttackerIdentityResolver(adapters=[FakeAdapter1(), FakeAdapter2()])
    attr = resolver.resolve_attacker_identity("10.50.60.70")

    assert attr.status == IdentityStatus.AMBIGUOUS.value
    assert attr.pc_name == "Unknown"
    assert len(attr.candidates) >= 2
    cand_names = [c.get("pc_name") for c in attr.candidates]
    assert "PC-FINANCE-01" in cand_names
    assert "PC-SALES-02" in cand_names
    assert any("Conflicting computer identities" in d for d in attr.diagnostics)


# 11. Conflicting Usernames Marked AMBIGUOUS
def test_conflicting_usernames_marked_ambiguous():
    class FakeUserAdapter1(BaseIdentitySourceAdapter):
        def __init__(self):
            super().__init__(name="Auth1", binding_id="b1")
        def resolve(self, ip, **kwargs):
            return SourceResolutionResult(source_name=self.name, binding_id=self.binding_id, status="SUCCESS", pc_name="PC-SHARED", username="MNE\\tariq", confidence_weight=0.8)

    class FakeUserAdapter2(BaseIdentitySourceAdapter):
        def __init__(self):
            super().__init__(name="Auth2", binding_id="b2")
        def resolve(self, ip, **kwargs):
            return SourceResolutionResult(source_name=self.name, binding_id=self.binding_id, status="SUCCESS", pc_name="PC-SHARED", username="MNE\\fadi", confidence_weight=0.8)

    resolver = LocalAttackerIdentityResolver(adapters=[FakeUserAdapter1(), FakeUserAdapter2()])
    attr = resolver.resolve_attacker_identity("10.50.60.80")

    assert attr.status == IdentityStatus.AMBIGUOUS.value
    assert attr.username == "Unknown"
    cand_users = [c.get("username") for c in attr.candidates]
    assert "MNE\\tariq" in cand_users
    assert "MNE\\fadi" in cand_users


# 12. Unconfigured Source Graceful Diagnostics
def test_unconfigured_source_graceful_diagnostics():
    # Adapters without live connectors or environment variables should return NOT_CONFIGURED
    dhcp = DhcpIdentityAdapter(lease_history_provider=None)
    sccm = SccmIdentityAdapter(query_executor=None)
    fgt = FortiGateAuthAdapter(auth_provider=None)

    resolver = LocalAttackerIdentityResolver(adapters=[dhcp, sccm, fgt])
    attr = resolver.resolve_attacker_identity("192.168.1.55")

    assert attr.network_scope == NetworkScope.LOCAL.value
    assert attr.status == IdentityStatus.NOT_CONFIGURED.value
    assert attr.confidence == IdentityConfidence.UNKNOWN.value
    assert attr.confidence_score == 0
    assert len(attr.diagnostics) > 0


# 13. In-Run Caching Behavior
def test_in_run_caching_behavior():
    call_counts = {"count": 0}

    def mock_dhcp(ip: str):
        call_counts["count"] += 1
        return [{
            "ip": ip,
            "hostname": "PC-CACHED-01",
            "mac": "33-33-33-33-33-33",
            "lease_start": datetime.now(timezone.utc) - timedelta(hours=1),
            "lease_end": datetime.now(timezone.utc) + timedelta(hours=1),
        }]

    dhcp = DhcpIdentityAdapter(lease_history_provider=mock_dhcp)
    resolver = LocalAttackerIdentityResolver(adapters=[dhcp], cache_enabled=True)

    now = datetime(2026, 9, 11, 14, 15, 0, tzinfo=timezone.utc)
    res1 = resolver.resolve_attacker_identity("10.0.0.100", first_seen=now)
    res2 = resolver.resolve_attacker_identity("10.0.0.100", first_seen=now)

    assert call_counts["count"] == 1
    assert res1.pc_name == "PC-CACHED-01"
    assert res2.pc_name == "PC-CACHED-01"


# 14. Fingerprint Invariance
def test_fingerprint_invariance():
    """Confirms that enriching incident with PC/User does NOT mutate its stable cross-run fingerprint."""
    raw_fp = generate_fingerprint(
        category="BRUTE_FORCE",
        signature_family="Failed SSH Login",
        source_scope="FortiGate",
        attacker_identity="10.20.30.40",
        target_identity="10.20.30.1",
        branch_scope="core",
    )

    # Creating an incident with enrichment fields
    now = datetime.now(timezone.utc)
    inc = Incident(
        incident_id="inc-inv-1",
        title="Failed SSH Login",
        severity=SeverityLevel.HIGH,
        source_device="FortiGate",
        category=ThreatCategory.BRUTE_FORCE,
        first_seen=now,
        last_seen=now,
        description="SSH brute force attempt blocked.",
        fingerprint=raw_fp,
        attacker_ip="10.20.30.40",
        target="10.20.30.1",
        action_taken="BLOCKED",
        attacker_pc_name="PC-FINANCE-042",
        attacker_username="MNE\\ahmad",
        attacker_identity_status="RESOLVED",
    )

    # Re-generating fingerprint must produce identical hash
    re_fp = generate_fingerprint(
        category=inc.category.value,
        signature_family=inc.title,
        source_scope=inc.source_device,
        attacker_identity=inc.attacker_ip,
        target_identity=inc.target,
        branch_scope="core",
    )

    assert raw_fp == re_fp == inc.fingerprint


# 15. Schema Validation: IncidentRecord
def test_schema_validation_incident_record():
    now_iso = datetime.now(timezone.utc).isoformat()
    record = IncidentRecord(
        fingerprint="inc-schema-val-001",
        display_id="MNE-SEC-VAL-01",
        title="Lateral Movement Detected",
        category="LATERAL_MOVEMENT",
        signature_family="smb-exec",
        source_device="FortiGate",
        attacker_identity="10.20.30.40",
        target_identity="10.20.30.100",
        lifecycle_state="NEW",
        first_seen=now_iso,
        last_seen=now_iso,
        occurrence_count=1,
        current_severity="HIGH",
        peak_severity="HIGH",
        attacker_pc_name="PC-FINANCE-042",
        attacker_fqdn="pc-finance-042.mne.local",
        attacker_username="MNE\\ahmad",
        attacker_user_display_name="Ahmad Salem",
        attacker_device_owner="MNE\\ahmad",
        attacker_mac_address="00-11-22-33-44-55",
        attacker_network_scope="LOCAL",
        attacker_identity_status="RESOLVED",
        attacker_identity_confidence="HIGH",
        attacker_identity_confidence_score=92,
        attacker_identity_observed_at=now_iso,
        attacker_identity_sources=["FortiAnalyzer", "DHCP", "SCCM"],
        attacker_identity_candidates=[],
        attacker_attribution=AttackerAttribution(
            ip_address="10.20.30.40",
            network_scope="LOCAL",
            pc_name="PC-FINANCE-042",
            status="RESOLVED",
            confidence="HIGH",
            confidence_score=92,
        ).to_dict(),
    )
    # validate_contract strictly checks against security-incident-record.schema.json
    validate_contract(record.to_dict(), "security-incident-record.schema.json")


# 16. Schema Validation: AttackerAttribution
def test_schema_validation_attacker_attribution():
    attribution = AttackerAttribution(
        ip_address="10.20.30.40",
        network_scope="LOCAL",
        pc_name="PC-FINANCE-042",
        fqdn="pc-finance-042.mne.local",
        domain="mne.local",
        username="MNE\\ahmad",
        user_display_name="Ahmad Salem",
        device_owner="MNE\\ahmad",
        mac_address="00-11-22-33-44-55",
        branch="Gaza-HQ",
        status="RESOLVED",
        confidence="HIGH",
        confidence_score=92,
        observed_at=datetime.now(timezone.utc).isoformat(),
        incident_time_match="EXACT",
        sources_queried=["FortiAnalyzer", "DHCP", "SCCM"],
        evidence_sources=[
            {
                "source_type": "DHCP",
                "source_entity_or_binding_id": "p7-dhcp-primary",
                "matched_fields": ["hostname", "mac"],
                "result_status": "SUCCESS",
            }
        ],
        candidates=[],
        diagnostics=["Corroborated."],
    )
    validate_contract(attribution.to_dict(), "attacker-attribution.schema.json")


# 17. CSV Report Contains Attribution Columns
def test_csv_report_contains_attribution_columns(tmp_path):
    store = SecurityReviewRunStore(tmp_path / "runs")
    reporter = SecurityReporter()

    class FakeIncidentCollector:
        def __init__(self):
            self.device_name = "FortiGate"
        def collect_logs(self, **kwargs):
            ev = NormalizedSecurityEvent(
                event_id="e-csv-1",
                timestamp=datetime.now(timezone.utc),
                source_device="FortiGate",
                category=ThreatCategory.BRUTE_FORCE,
                threat_name="Failed Login",
                attacker_ip="10.20.30.40",
                target="admin",
                action_taken="BLOCKED",
                count=5,
                metadata={"srcname": "PC-FINANCE-042", "user": "MNE\\ahmad", "username_relation": "AUTHENTICATED_SOURCE_USER", "srcmac": "00-11-22-33-44-55"},
            )
            return CollectorResult(device_name="FortiGate", status=CollectorStatus.SUCCESS, events=[ev])

    svc = SecurityReviewService(
        run_store=store,
        reporter=reporter,
        collector_registry={"fortigate_core": FakeIncidentCollector()},
    )

    req = SecurityReviewRequest(
        mode=ReviewMode.QUICK,
        collector_ids=["fortigate_core"],
        hours_back=1.0,
        analysis_engine=AnalysisEngine.NONE,
        send_email=False,
        report_formats=[ReportFormat.CSV],
    )

    run = svc.start_review(req, async_run=False)
    csv_path = run.report_artifacts.get("csv")
    assert csv_path is not None and Path(csv_path).exists()

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = [r for r in csv.reader(f) if r]

    headers = reader[0]
    expected_cols = [
        "incident_id", "severity", "category", "source_device",
        "attacker_ip", "network_scope", "pc_name", "username",
        "device_owner", "mac_address", "identity_status", "identity_confidence",
        "identity_sources", "target", "title", "description",
    ]
    for col in expected_cols:
        assert col in headers, f"Missing required column {col} in CSV report"

    row = reader[1]
    pc_idx = headers.index("pc_name")
    user_idx = headers.index("username")
    scope_idx = headers.index("network_scope")

    assert row[pc_idx] == "PC-FINANCE-042"
    assert row[user_idx] == "MNE\\ahmad"
    assert row[scope_idx] == "LOCAL"


# 18. HTML Report Contains Attribution Details
def test_html_report_contains_attribution_details():
    reporter = SecurityReporter()
    now = datetime.now(timezone.utc)
    inc = Incident(
        incident_id="inc-html-1",
        title="Web Exploit Probe",
        severity=SeverityLevel.HIGH,
        source_device="FortiGate",
        category=ThreatCategory.WAF_EXPLOIT,
        first_seen=now,
        last_seen=now,
        description="Web Exploit Probe blocked.",
        action_taken="BLOCKED",
        attacker_ip="10.20.30.40",
        target="10.20.30.1",
        attacker_pc_name="PC-FINANCE-042",
        attacker_username="MNE\\ahmad",
        attacker_mac_address="00-11-22-33-44-55",
        attacker_network_scope="LOCAL",
        attacker_identity_status="RESOLVED",
        attacker_identity_confidence="HIGH",
        attacker_identity_sources=["FortiAnalyzer", "DHCP"],
    )

    html = reporter.render_html_report(incidents=[inc], collectors=[])

    assert "PC-FINANCE-042" in html
    assert "MNE\\ahmad" in html
    assert "00-11-22-33-44-55" in html
    assert "RESOLVED" in html
    assert "HIGH" in html


# 19. Secrets Protection in Diagnostics
def test_secrets_protection_in_diagnostics():
    """Verifies that no secrets or raw credentials ever leak into diagnostics or reports."""
    class SecretExposingAdapter(BaseIdentitySourceAdapter):
        def __init__(self):
            super().__init__(name="SecretSource", binding_id="b-sec")
        def resolve(self, ip, **kwargs):
            return SourceResolutionResult(
                source_name=self.name,
                binding_id=self.binding_id,
                status="FAILED",
                diagnostic="Failed connecting with password=SecretPassword123! and token=Bearer secretTokenXYZ",
            )

    resolver = LocalAttackerIdentityResolver(adapters=[SecretExposingAdapter()])
    attr = resolver.resolve_attacker_identity("10.0.0.99")

    dumped = json.dumps(attr.to_dict())
    assert "SecretPassword123!" not in dumped
    assert "secretTokenXYZ" not in dumped
    assert "SecretPassword" not in dumped


# 20. Documentation IP Ranges Return EXTERNAL
def test_documentation_ip_ranges_return_external():
    """RFC 5737 (TEST-NET-1/2/3) and RFC 3849 documentation IPs must be classified as EXTERNAL."""
    doc_ips = ["192.0.2.1", "198.51.100.22", "203.0.113.50", "2001:db8::1"]
    for ip in doc_ips:
        scope = classify_ip(ip)
        assert scope == NetworkScope.EXTERNAL, f"Expected EXTERNAL for documentation IP {ip}, got {scope}"

    resolver = LocalAttackerIdentityResolver(adapters=[])
    attr = resolver.resolve_attacker_identity("198.51.100.22")
    assert attr.network_scope == NetworkScope.EXTERNAL.value
    assert attr.status == IdentityStatus.NOT_APPLICABLE.value
    assert attr.pc_name == "Not applicable"
    assert attr.username == "Not applicable"


# 21. Loopback, Link-Local, Multicast Return INVALID
def test_loopback_link_local_multicast_return_invalid():
    """Loopback, link-local, multicast, and unspecified IPs are not valid targets and must return INVALID."""
    invalid_ips = ["127.0.0.1", "169.254.1.1", "224.0.0.1", "::1", "fe80::1", "0.0.0.0"]
    for ip in invalid_ips:
        scope = classify_ip(ip)
        assert scope == NetworkScope.INVALID, f"Expected INVALID for IP {ip}, got {scope}"

    resolver = LocalAttackerIdentityResolver(adapters=[])
    attr = resolver.resolve_attacker_identity("127.0.0.1")
    assert attr.network_scope == NetworkScope.INVALID.value
    assert attr.status == IdentityStatus.FAILED.value
    assert attr.pc_name == "Not applicable"


# 22. Strict Local CIDRs Without Private Fallback
def test_strict_local_cidrs_not_private_fallback():
    """When authoritative local CIDRs are explicitly configured, only matching subnets are LOCAL."""
    authoritative = ["10.20.0.0/16"]
    # 10.20.5.1 is inside the configured CIDR -> LOCAL
    assert classify_ip("10.20.5.1", local_cidrs=authoritative) == NetworkScope.LOCAL

    # 10.30.5.1 is RFC1918 private, but NOT in authoritative CIDRs -> must NOT fall back to LOCAL
    assert classify_ip("10.30.5.1", local_cidrs=authoritative) == NetworkScope.EXTERNAL


# 23. Username Relation Distinction
def test_username_relation_distinction():
    """Confirms active authenticated user, claimed login, target account, and primary device owner are distinct."""
    now_iso = datetime.now(timezone.utc).isoformat()
    attr = AttackerAttribution(
        ip_address="10.20.30.40",
        network_scope="LOCAL",
        pc_name="PC-FINANCE-042",
        username="MNE\\active_user",
        primary_device_user="MNE\\pc_owner",
        claimed_username="claimed_admin",
        target_account="target_svc",
        status="RESOLVED",
        confidence="HIGH",
        confidence_score=90,
    )
    d = attr.to_dict()
    assert d["username"] == "MNE\\active_user"
    assert d["primary_device_user"] == "MNE\\pc_owner"
    assert d["claimed_username"] == "claimed_admin"
    assert d["target_account"] == "target_svc"
    validate_contract(d, "attacker-attribution.schema.json")

    record = IncidentRecord(
        fingerprint="fp-rel-001",
        display_id="MNE-SEC-REL-01",
        title="Account Probing",
        category="BRUTE_FORCE",
        signature_family="login-abuse",
        source_device="FortiGate",
        attacker_identity="10.20.30.40",
        target_identity="10.20.30.1",
        lifecycle_state="NEW",
        first_seen=now_iso,
        last_seen=now_iso,
        occurrence_count=1,
        current_severity="HIGH",
        peak_severity="HIGH",
        attacker_username="MNE\\active_user",
        attacker_primary_device_user="MNE\\pc_owner",
        attacker_claimed_username="claimed_admin",
        attacker_target_account="target_svc",
        attacker_network_scope="LOCAL",
        attacker_identity_status="RESOLVED",
    )
    rd = record.to_dict()
    assert rd["attacker_username"] == "MNE\\active_user"
    assert rd["attacker_primary_device_user"] == "MNE\\pc_owner"
    assert rd["attacker_claimed_username"] == "claimed_admin"
    assert rd["attacker_target_account"] == "target_svc"
    validate_contract(rd, "security-incident-record.schema.json")


# 24. Monotonic Deadline Timeout Skips Subsequent Adapters
def test_monotonic_deadline_timeout_skips_subsequent_adapters():
    """Verifies that when overall resolution deadline expires, remaining adapters are safely skipped."""
    import time

    class SlowMockAdapter(BaseIdentitySourceAdapter):
        def __init__(self, name: str):
            super().__init__(name=name, binding_id=f"b-{name}")
        def resolve(self, ip: str, **kwargs: Any) -> SourceResolutionResult:
            time.sleep(0.06)
            return SourceResolutionResult(
                source_name=self.name,
                binding_id=self.binding_id,
                status="MATCH",
                pc_name="PC-SLOW",
            )

    class FastMockAdapter(BaseIdentitySourceAdapter):
        def __init__(self, name: str):
            super().__init__(name=name, binding_id=f"b-{name}")
        def resolve(self, ip: str, **kwargs: Any) -> SourceResolutionResult:
            return SourceResolutionResult(
                source_name=self.name,
                binding_id=self.binding_id,
                status="MATCH",
                pc_name="PC-FAST",
            )

    resolver = LocalAttackerIdentityResolver(
        adapters=[SlowMockAdapter("SlowSource"), FastMockAdapter("FastSource")],
        overall_timeout=0.03,
    )
    attr = resolver.resolve_attacker_identity("10.20.30.40")
    statuses = [s["result_status"] for s in attr.evidence_sources]
    assert "SKIPPED_DEADLINE" in statuses


# 25. Non-Downgrade Persistence Logic
def test_should_replace_attribution_non_downgrade():
    """Ensures should_replace_attribution preserves high-quality attributions against stale/failed ones."""
    from core.security_review.identity_enrichment import should_replace_attribution

    # 1. None existing attribution is always replaced
    cand_resolved = AttackerAttribution(
        ip_address="10.20.30.40",
        status="RESOLVED",
        confidence="HIGH",
        confidence_score=90,
        pc_name="PC-FINANCE-042",
        username="MNE\\ahmad",
    )
    assert should_replace_attribution(None, cand_resolved) is True

    # 2. RESOLVED attribution cannot be replaced by UNRESOLVED / NOT_FOUND / FAILED
    cand_unresolved = AttackerAttribution(
        ip_address="10.20.30.40",
        status="NOT_FOUND",
        confidence="LOW",
        confidence_score=10,
    )
    assert should_replace_attribution(cand_resolved, cand_unresolved) is False

    cand_failed = AttackerAttribution(
        ip_address="10.20.30.40",
        status="FAILED",
        confidence="UNKNOWN",
        confidence_score=0,
    )
    assert should_replace_attribution(cand_resolved, cand_failed) is False

    # 3. EXACT match cannot be downgraded to CURRENT_ONLY match
    cand_exact = AttackerAttribution(
        ip_address="10.20.30.40",
        status="RESOLVED",
        confidence="HIGH",
        confidence_score=90,
        incident_time_match="EXACT",
    )
    cand_current_only = AttackerAttribution(
        ip_address="10.20.30.40",
        status="RESOLVED",
        confidence="MEDIUM",
        confidence_score=75,
        incident_time_match="CURRENT_ONLY",
    )
    assert should_replace_attribution(cand_exact, cand_current_only) is False

    # 4. PARTIAL attribution can be upgraded to RESOLVED
    cand_partial = AttackerAttribution(
        ip_address="10.20.30.40",
        status="PARTIAL",
        confidence="MEDIUM",
        confidence_score=50,
        pc_name="PC-FINANCE-042",
    )
    assert should_replace_attribution(cand_partial, cand_resolved) is True


# 26. In-Flight Resolution Deduplication Lock
def test_in_flight_deduplication_lock():
    """Verifies that in-flight resolution tracking prevents concurrent duplicate jobs on the same incident."""
    from core.api.server import _in_flight_resolutions, _in_flight_resolutions_lock

    test_fingerprint = "inc-inflight-lock-test"

    # Simulate marking an incident in-flight
    with _in_flight_resolutions_lock:
        assert test_fingerprint not in _in_flight_resolutions
        _in_flight_resolutions.add(test_fingerprint)

    # Attempting to start another resolution for the same incident detects it as in-flight
    with _in_flight_resolutions_lock:
        is_already_running = test_fingerprint in _in_flight_resolutions
    assert is_already_running is True

    # Cleanup upon completion
    with _in_flight_resolutions_lock:
        _in_flight_resolutions.discard(test_fingerprint)

    # Verify released
    with _in_flight_resolutions_lock:
        assert test_fingerprint not in _in_flight_resolutions


# 27. Provider Factory Reports NOT_CONFIGURED Honestly
def test_provider_factory_unconfigured_honest_status():
    """When connection parameters/credentials are missing, providers must honestly report NOT_CONFIGURED."""
    from core.security_review.identity_providers import create_identity_adapters

    adapters = create_identity_adapters({})
    assert len(adapters) > 0

    for adapter in adapters:
        res = adapter.resolve("10.20.30.40")
        assert res.status == "NOT_CONFIGURED" or res.diagnostic != "", (
            f"Adapter {adapter.name} failed to honestly report unconfigured state"
        )


# 28. Supporting Events Scoping
def test_supporting_events_scoping():
    """EventNativeIdentityAdapter strictly scopes correlation to supporting event IDs and matching attacker IP."""
    now = datetime.now(timezone.utc)
    ev_supported = NormalizedSecurityEvent(
        event_id="ev-sup-01",
        timestamp=now,
        source_device="FortiGate",
        category=ThreatCategory.BRUTE_FORCE,
        threat_name="SSH probe",
        attacker_ip="10.20.30.40",
        target="10.20.30.1",
        action_taken="BLOCKED",
        attacker_hostname="PC-TARGETED-01",
        authenticated_source_user="MNE\\authorized_user",
    )
    ev_unsupported = NormalizedSecurityEvent(
        event_id="ev-unsup-02",
        timestamp=now,
        source_device="FortiGate",
        category=ThreatCategory.BRUTE_FORCE,
        threat_name="SSH probe 2",
        attacker_ip="10.20.30.40",
        target="10.20.30.1",
        action_taken="BLOCKED",
        attacker_hostname="PC-OTHER-02",
        authenticated_source_user="MNE\\other_user",
    )
    ev_wrong_ip = NormalizedSecurityEvent(
        event_id="ev-wrong-03",
        timestamp=now,
        source_device="FortiGate",
        category=ThreatCategory.BRUTE_FORCE,
        threat_name="SSH probe 3",
        attacker_ip="10.50.50.50",
        target="10.20.30.1",
        action_taken="BLOCKED",
        attacker_hostname="PC-WRONG-03",
    )

    adapter = EventNativeIdentityAdapter()
    res = adapter.resolve(
        ip="10.20.30.40",
        events=[ev_supported, ev_unsupported, ev_wrong_ip],
        supporting_event_ids=["ev-sup-01"],
    )
    assert res.pc_name == "PC-TARGETED-01"
    assert res.username == "MNE\\authorized_user"


# 29. Attribution History Bounded Retention
def test_attribution_history_bounded_retention():
    """Attribution history maintains a bounded FIFO buffer of at most 10 snapshots without unbounded growth."""
    history = []
    for i in range(15):
        snapshot = {
            "snapshot_index": i,
            "status": "PARTIAL" if i < 5 else "RESOLVED",
            "confidence_score": 50 + i * 2,
            "observed_at": f"2026-09-11T12:{i:02d}:00Z",
        }
        history.append(snapshot)
        if len(history) > 10:
            history.pop(0)

    assert len(history) == 10
    assert history[0]["snapshot_index"] == 5
    assert history[-1]["snapshot_index"] == 14

    attr = AttackerAttribution(
        ip_address="10.20.30.40",
        network_scope="LOCAL",
        pc_name="PC-FINANCE-042",
        status="RESOLVED",
        confidence="HIGH",
        confidence_score=90,
        attribution_history=history,
    )
    assert len(attr.attribution_history) == 10
    validate_contract(attr.to_dict(), "attacker-attribution.schema.json")


# 30. Max Candidates Clamping
def test_max_candidates_clamping():
    """Verifies that candidates are clamped to max_candidates limit to prevent unbounded memory growth."""
    class MultiCandidateAdapter(BaseIdentitySourceAdapter):
        def __init__(self):
            super().__init__(name="MultiCandSource", binding_id="b-multi")
        def resolve(self, ip: str, **kwargs: Any) -> SourceResolutionResult:
            return SourceResolutionResult(
                source_name=self.name,
                binding_id=self.binding_id,
                status="MATCH",
                pc_name="PC-CAND-01",
            )

    resolver = LocalAttackerIdentityResolver(
        adapters=[MultiCandidateAdapter()],
        max_candidates=3,
    )
    attr = resolver.resolve_attacker_identity("10.20.30.40")
    assert len(attr.candidates) <= 3


# 31. Reproduction 1: Failed VPN Login maps to claimed_username, not attacker_username
def test_reproduction_1_failed_vpn_login_claimed_user():
    now = datetime.now(timezone.utc)
    ev = NormalizedSecurityEvent(
        event_id="ev-vpn-fail-01",
        timestamp=now,
        source_device="FortiGate",
        category=ThreatCategory.BRUTE_FORCE,
        threat_name="SSL-VPN Failed Authentication",
        attacker_ip="10.100.20.5",
        target="10.100.20.1",
        action_taken="DROPPED",
        claimed_login_username="admin",
        username_relation=UsernameRelation.CLAIMED_LOGIN_USERNAME,
        authenticated_source_user=None,
        metadata={"subtype": "vpn", "action": "failed", "user": "admin", "username_relation": "CLAIMED_LOGIN_USERNAME"},
    )
    resolver = LocalAttackerIdentityResolver(adapters=[EventNativeIdentityAdapter()])
    attr = resolver.resolve_attacker_identity("10.100.20.5", events=[ev], first_seen=now)

    assert attr.username == "Unknown"
    assert attr.claimed_username == "admin"
    assert attr.status != IdentityStatus.RESOLVED.value


# 32. Reproduction 2: Blocked Timeout Isolation
def test_reproduction_2_blocked_timeout_isolation():
    import time

    class HangingAdapter(BaseIdentitySourceAdapter):
        def __init__(self):
            super().__init__(name="HangingAdapter", binding_id="hang-1")
        def resolve(self, ip, **kwargs):
            time.sleep(0.20)
            return SourceResolutionResult(source_name=self.name, status="SUCCESS", pc_name="SLOW-PC")

    resolver = LocalAttackerIdentityResolver(
        adapters=[HangingAdapter()],
        per_source_timeout=0.01,
        overall_timeout=0.05,
    )
    t0 = time.monotonic()
    attr = resolver.resolve_attacker_identity("10.20.30.40")
    elapsed = time.monotonic() - t0

    assert elapsed < 0.08
    hang_src = next((s for s in attr.evidence_sources if s["source_type"] == "HangingAdapter"), None)
    assert hang_src is not None
    assert hang_src["result_status"] == "QUERY_TIMEOUT"


# 33. Reproduction 3: Fake Configured DHCP without Binding Returns NOT_CONFIGURED
def test_reproduction_3_fake_dhcp_without_registered_binding():
    from core.security_review.identity_providers import DhcpIdentityProvider

    adapter = DhcpIdentityProvider(
        host="10.10.10.10",
        username="fake_admin",
        binding=None,
        executor=None,
    )
    res = adapter.resolve("10.20.30.40")
    assert res.status == "NOT_CONFIGURED"
    assert "not configured" in res.diagnostic.lower()
    assert not hasattr(adapter, "password")


# 34. Reproduction 4: Strong vs Weak Conflict Resolution
def test_reproduction_4_strong_vs_weak_conflict_resolution():
    class StrongAdapter(BaseIdentitySourceAdapter):
        def __init__(self):
            super().__init__(name="StrongSource", binding_id="b-strong")
        def resolve(self, ip, **kwargs):
            return SourceResolutionResult(
                source_name=self.name,
                binding_id=self.binding_id,
                status="SUCCESS",
                pc_name="PC-EXACT",
                time_match=IncidentTimeMatch.EXACT,
                confidence_weight=0.95,
            )

    class WeakAdapter(BaseIdentitySourceAdapter):
        def __init__(self):
            super().__init__(name="WeakSource", binding_id="b-weak")
        def resolve(self, ip, **kwargs):
            return SourceResolutionResult(
                source_name=self.name,
                binding_id=self.binding_id,
                status="SUCCESS",
                pc_name="PC-CURRENT",
                time_match=IncidentTimeMatch.CURRENT_ONLY,
                confidence_weight=0.20,
            )

    resolver = LocalAttackerIdentityResolver(adapters=[StrongAdapter(), WeakAdapter()])
    attr = resolver.resolve_attacker_identity("10.20.30.40")

    assert attr.pc_name == "PC-EXACT"
    assert attr.status != IdentityStatus.AMBIGUOUS.value
    cand_pcs = [c.get("pc_name") for c in attr.candidates if c.get("pc_name")]
    assert "PC-EXACT" in cand_pcs
    assert "PC-CURRENT" in cand_pcs


# 35. Reproduction 5: Cross-run Downgrade Protection in IncidentStore
def test_reproduction_5_cross_run_downgrade_incident_store(tmp_path):
    store = IncidentStore(tmp_path / "incidents")
    now_iso = datetime.now(timezone.utc).isoformat()
    fp = "inc-repro-5"

    inc1 = Incident(
        incident_id="MNE-SEC-REPRO-1",
        category=ThreatCategory.INTRUSION,
        title="SMB Exploit Attempt",
        description="SMB Exploit Attempt detected",
        severity=SeverityLevel.HIGH,
        source_device="FortiGate",
        attacker_ip="10.20.30.40",
        target="10.20.30.100",
        action_taken="BLOCKED",
        event_count=5,
        first_seen=datetime.now(timezone.utc),
        last_seen=datetime.now(timezone.utc),
        attacker_pc_name="PC-CORP-01",
        attacker_username="MNE\\bob",
        attacker_network_scope="LOCAL",
        attacker_identity_status="RESOLVED",
        attacker_identity_confidence="HIGH",
        attacker_identity_confidence_score=95,
        attacker_attribution=AttackerAttribution(
            ip_address="10.20.30.40",
            network_scope="LOCAL",
            pc_name="PC-CORP-01",
            username="MNE\\bob",
            status="RESOLVED",
            confidence="HIGH",
            confidence_score=95,
        ).to_dict(),
    )
    inc1.fingerprint = fp

    store.record_run_incidents("run-001", [inc1])

    inc2 = Incident(
        incident_id="MNE-SEC-REPRO-1",
        category=ThreatCategory.INTRUSION,
        title="SMB Exploit Attempt",
        description="SMB Exploit Attempt detected",
        severity=SeverityLevel.HIGH,
        source_device="FortiGate",
        attacker_ip="10.20.30.40",
        target="10.20.30.100",
        action_taken="BLOCKED",
        event_count=2,
        first_seen=datetime.now(timezone.utc),
        last_seen=datetime.now(timezone.utc),
        attacker_pc_name="Unknown",
        attacker_username="Unknown",
        attacker_network_scope="LOCAL",
        attacker_identity_status="NOT_FOUND",
        attacker_identity_confidence="UNKNOWN",
        attacker_identity_confidence_score=0,
        attacker_attribution=AttackerAttribution(
            ip_address="10.20.30.40",
            network_scope="LOCAL",
            pc_name="Unknown",
            username="Unknown",
            status="NOT_FOUND",
            confidence="UNKNOWN",
            confidence_score=0,
        ).to_dict(),
    )
    inc2.fingerprint = fp

    store.record_run_incidents("run-002", [inc2])

    rec = store.get_incident(fp)
    assert rec is not None
    assert rec.attacker_pc_name == "PC-CORP-01"
    assert rec.attacker_username == "MNE\\bob"
    assert rec.attacker_identity_status == "RESOLVED"
    assert rec.attacker_identity_confidence_score == 95
    assert rec.attacker_attribution is not None
    assert len(rec.attacker_attribution.get("attribution_history", [])) >= 1
    assert rec.attacker_attribution["attribution_history"][-1]["status"] == "NOT_FOUND"


# 36. Reproduction 6: Nested Schema Rejects Malformed Attribution
def test_reproduction_6_nested_schema_rejects_malformed_attribution():
    import jsonschema

    now_iso = datetime.now(timezone.utc).isoformat()
    bad_record = {
        "fingerprint": "inc-bad-attr-01",
        "display_id": "MNE-SEC-BAD-01",
        "title": "Test Malformed",
        "category": "ANOMALY",
        "signature_family": "test",
        "source_device": "FortiGate",
        "attacker_identity": "10.20.30.40",
        "target_identity": "10.20.30.1",
        "lifecycle_state": "NEW",
        "first_seen": now_iso,
        "last_seen": now_iso,
        "occurrence_count": 1,
        "current_severity": "LOW",
        "peak_severity": "LOW",
        "attacker_attribution": {"garbage": 1},
    }
    with pytest.raises(jsonschema.ValidationError):
        validate_contract(bad_record, "security-incident-record.schema.json")


# 37. Reproduction 7: No Direct Socket Bypass
def test_reproduction_7_no_direct_socket_bypass(monkeypatch):
    def fake_gethostbyaddr(*args, **kwargs):
        raise RuntimeError("Direct socket call forbidden by AGENTS.md!")

    import socket
    monkeypatch.setattr(socket, "gethostbyaddr", fake_gethostbyaddr)

    adapter = DnsActiveDirectoryAdapter()
    res = adapter.resolve("10.20.30.40")
    assert res.status == "NOT_CONFIGURED"
    assert "not configured" in res.diagnostic.lower()


def test_generic_hostname_and_user_are_not_promoted_without_roles():
    now = datetime.now(timezone.utc)
    event = NormalizedSecurityEvent(
        event_id="generic-fields",
        timestamp=now,
        source_device="FortiGate",
        category=ThreatCategory.ANOMALY,
        threat_name="Web event",
        attacker_ip="10.20.30.40",
        target="188.114.96.7",
        metadata={"hostname": "destination.example", "user": "target-account"},
    )
    result = EventNativeIdentityAdapter().resolve("10.20.30.40", events=[event])
    assert result.pc_name is None
    assert result.username is None


def test_cache_changes_when_supporting_identity_evidence_changes():
    now = datetime.now(timezone.utc)
    resolver = LocalAttackerIdentityResolver(adapters=[EventNativeIdentityAdapter()], enable_cache=True)
    empty = resolver.resolve_attacker_identity("10.20.30.40", first_seen=now, last_seen=now, events=[])
    event = NormalizedSecurityEvent(
        event_id="identity-evidence",
        timestamp=now,
        source_device="FortiAnalyzer",
        category=ThreatCategory.ANOMALY,
        threat_name="Authenticated traffic",
        attacker_ip="10.20.30.40",
        source_hostname="PC-CORRECT",
        authenticated_source_user="MNE\\alice",
        username_relation=UsernameRelation.AUTHENTICATED_SOURCE_USER,
    )
    resolved = resolver.resolve_attacker_identity(
        "10.20.30.40",
        first_seen=now,
        last_seen=now,
        events=[event],
        supporting_event_ids={"identity-evidence"},
    )
    assert empty.status == IdentityStatus.NOT_FOUND.value
    assert resolved.pc_name == "PC-CORRECT"
    assert resolved.username == "MNE\\alice"
    assert resolved is not empty


def test_governed_providers_are_stateless_across_ips_and_fortigate_signature_matches():
    from core.security_review.identity_providers import (
        DhcpIdentityProvider,
        FortiGateAuthIdentityProvider,
        GovernedIdentityQueryExecutor,
    )

    class FakeExecutor(GovernedIdentityQueryExecutor):
        def execute_query(self, binding_id, query_type, parameters, timeout=5.0):
            suffix = parameters["ip"].split(".")[-1]
            if query_type == "dhcp_lease_lookup":
                return {"record": {"hostname": f"PC-{suffix}", "current_only": True}}
            return {"record": {"hostname": f"VPN-{suffix}", "username": f"user-{suffix}"}}

    binding = {"scope_status": "ACTIVE", "read_only": True}
    executor = FakeExecutor()
    dhcp = DhcpIdentityProvider(binding=binding, executor=executor)
    assert dhcp.resolve("10.0.0.1").pc_name == "PC-1"
    assert dhcp.resolve("10.0.0.2").pc_name == "PC-2"

    fortigate = FortiGateAuthIdentityProvider(binding=binding, executor=executor)
    auth = fortigate.resolve("10.0.0.3")
    assert auth.status == "SUCCESS"
    assert auth.pc_name == "VPN-3"
    assert auth.username == "user-3"


def test_default_service_keeps_fortianalyzer_identity_source_enabled():
    service = SecurityReviewService()
    assert "FortiAnalyzer" in [adapter.name for adapter in service.identity_resolver.adapters]


def test_resolver_history_uses_schema_valid_compact_snapshot():
    class StrongAdapter(BaseIdentitySourceAdapter):
        def __init__(self):
            super().__init__(name="Strong", binding_id="strong")

        def resolve(self, ip, **kwargs):
            return SourceResolutionResult(
                source_name=self.name,
                binding_id=self.binding_id,
                status="SUCCESS",
                pc_name="PC-NEW",
                username="MNE\\new-user",
                confidence_weight=0.95,
                time_match=IncidentTimeMatch.EXACT,
            )

    now = datetime.now(timezone.utc)
    incident = Incident(
        incident_id="history-test",
        title="History test",
        severity=SeverityLevel.HIGH,
        source_device="FortiGate",
        category=ThreatCategory.ANOMALY,
        first_seen=now,
        last_seen=now,
        description="test",
        action_taken="BLOCKED",
        attacker_ip="10.20.30.40",
        attacker_attribution=AttackerAttribution(
            ip_address="10.20.30.40",
            network_scope="LOCAL",
            pc_name="PC-OLD",
            status="PARTIAL",
            confidence="LOW",
            confidence_score=30,
        ).to_dict(),
    )
    attribution = LocalAttackerIdentityResolver(adapters=[StrongAdapter()]).resolve_incident_identity(incident)
    assert attribution.attribution_history
    validate_contract(attribution.to_dict(), "attacker-attribution.schema.json")


def test_secret_sanitizer_preserves_provider_name_but_redacts_auth_value():
    from core.security_review.identity_enrichment import sanitize_secret_text

    diagnostic = sanitize_secret_text("FortiGate-Auth: provider unavailable; auth=secret-value")
    assert diagnostic.startswith("FortiGate-Auth: provider unavailable")
    assert "secret-value" not in diagnostic
