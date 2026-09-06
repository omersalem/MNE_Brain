from datetime import datetime, timezone
from core.connectors.security.ad_exchange_collector import ActiveDirectoryCollector, ExchangeCollector
from core.connectors.security.models import ThreatCategory

def test_ad_privileged_group_change_parsing():
    sample_event = {
        "EventID": 4728,
        "TargetUserName": "Domain Admins",
        "MemberName": "CN=TemporaryUser,OU=Users,DC=mne,DC=gov,DC=ps",
        "SubjectUserName": "svc_installer",
        "TimeCreated": "2026-09-06T05:22:00Z"
    }
    collector = ActiveDirectoryCollector()
    event = collector.parse_security_event(sample_event)
    assert event.source_device == "Active Directory"
    assert event.category == ThreatCategory.PRIVILEGE_CHANGE
    assert "Member added to Domain Admins" in event.threat_name
    assert event.target == "TemporaryUser"

def test_ad_account_lockout_parsing():
    sample_event = {
        "EventID": 4740,
        "TargetUserName": "finance_mgr",
        "CallerComputerName": "WORKSTATION-102",
        "TimeCreated": "2026-09-06T04:15:00Z"
    }
    collector = ActiveDirectoryCollector()
    event = collector.parse_security_event(sample_event)
    assert event.source_device == "Active Directory"
    assert event.category == ThreatCategory.BRUTE_FORCE
    assert "Account Locked Out" in event.threat_name
    assert event.target == "finance_mgr"

def test_exchange_relay_anomaly_parsing():
    sample_log = {
        "event_type": "FAIL",
        "client_ip": "185.190.140.22",
        "sender": "spammer@external-junk.com",
        "recipient_count": 140,
        "reason": "550 5.7.1 Unable to relay",
        "timestamp": "2026-09-06T03:30:00Z"
    }
    collector = ExchangeCollector()
    event = collector.parse_tracking_log(sample_log)
    assert event.source_device == "Exchange"
    assert event.category == ThreatCategory.ANOMALY
    assert event.attacker_ip == "185.190.140.22"
    assert "Relay Attempt Blocked" in event.threat_name
    assert event.action_taken == "BLOCKED"
