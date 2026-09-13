from scripts.fmc_cef_receiver import parse_cef, parse_security_syslog


def test_parse_cef_keeps_intrusion_and_maps_threat_fields():
    event = parse_cef(
        "<134>CEF:0|Cisco|Firepower|7.6|400001|SQL Injection|8|"
        "src=10.0.0.1 dst=10.0.0.2 rt=1788680000000 act=Block "
        "cat=Intrusion msg=SQL\\=Injection"
    )

    assert event is not None
    assert event["id"] == "400001"
    assert event["timestamp"] == 1788680000
    assert event["sourceIp"] == "10.0.0.1"
    assert event["destinationIp"] == "10.0.0.2"
    assert event["action"] == "Block"
    assert event["ruleMessage"] == "SQL=Injection"


def test_parse_cef_drops_connection_allow_events():
    event = parse_cef(
        "CEF:0|Cisco|Firepower|7.6|1|Connection Allowed|3|"
        "src=10.0.0.1 dst=10.0.0.2 act=Allow cat=Connection"
    )

    assert event is None


def test_parse_cef_drops_unclassified_events():
    event = parse_cef("CEF:0|Cisco|Firepower|7.6|1|Policy Notice|3|msg=notice")

    assert event is None


def test_parse_security_syslog_keeps_intrusion_event():
    event = parse_security_syslog(
        "2026-09-13T10:00:00Z ftd %NGIPS-1-430001: "
        "EventPriority: High, DeviceUUID: dev-1, FirstPacketSecond: 2026-09-13T09:59:59Z, "
        "ConnectionID: 42, AccessControlRuleAction: Block, SrcIP: 10.0.0.1, "
        "DstIP: 10.0.0.2, Signature: SQL Injection"
    )

    assert event is not None
    assert event["cef"]["signature_id"] == "430001"
    assert event["sourceIp"] == "10.0.0.1"
    assert event["action"] == "Block"
    assert event["metadata"]["transport"] == "SYSLOG_SECURITY_EVENT"


def test_parse_security_syslog_keeps_malware_event():
    event = parse_security_syslog(
        "2026-09-13T10:00:00Z ftd %FTD-4-430005: "
        "EventPriority: High, DeviceUUID: dev-1, FileName: evil.exe, "
        "AccessControlRuleAction: Block, SrcIP: 10.0.0.1, DstIP: 10.0.0.2"
    )

    assert event is not None
    assert event["cef"]["signature_id"] == "430005"
    assert event["ThreatName"] == "evil.exe"


def test_parse_security_syslog_keeps_security_intelligence_but_drops_allow():
    si_event = parse_security_syslog(
        "%NGIPS-4-430002: AccessControlRuleAction: Block, "
        "AccessControlRuleReason: IP Block, IPReputationSICategory: Known bad, "
        "SrcIP: 10.0.0.1, DstIP: 10.0.0.2"
    )
    allow_event = parse_security_syslog(
        "%NGIPS-4-430002: AccessControlRuleAction: Allow, "
        "SrcIP: 10.0.0.1, DstIP: 10.0.0.2"
    )

    assert si_event is not None
    assert si_event["metadata"]["security_intelligence"] is True
    assert allow_event is None
