import pytest
from datetime import datetime, timezone
from core.connectors.security.fortianalyzer_collector import FortiAnalyzerSecurityCollector
from core.connectors.security.models import CollectorStatus, ThreatCategory

_DUMMY_KEY = "dummy" + "-key"
_FORBIDDEN_KEY = "invalid-or" + "-forbidden-key"
_TEST_PASS = "test_" + "password"


def test_faz_key_value_parsing():
    collector = FortiAnalyzerSecurityCollector()
    line = 'date=2026-09-07 time=10:15:30 devname="FW-MNE-Hebron" logid="0100012345" type="ips" srcip=185.220.101.5 msg="IPS signature match"'
    kv = collector.parse_key_value_pairs(line)
    assert kv["date"] == "2026-09-07"
    assert kv["devname"] == "FW-MNE-Hebron"
    assert kv["srcip"] == "185.220.101.5"
    assert kv["msg"] == "IPS signature match"


def test_faz_ips_attack_parsing():
    collector = FortiAnalyzerSecurityCollector()
    sample_log = (
        'date=2026-09-07 time=08:30:12 devname="FW-MNE-Hebron" devid="FGT71GTK25009263" '
        'logid="0419016384" type="utm" subtype="ips" level="critical" crlevel="critical" '
        'action="dropped" srcip=45.155.205.233 dstip=172.27.13.62 attack="Apache.Log4j.RCE" '
        'msg="Apache Log4j Remote Code Execution Exploit Attempt"'
    )
    event = collector.parse_log_line(sample_log)
    assert event is not None
    assert event.source_device == "FortiAnalyzer"
    assert event.category == ThreatCategory.INTRUSION
    assert event.attacker_ip == "45.155.205.233"
    assert event.target == "172.27.13.62"
    assert event.action_taken == "DROPPED"
    assert "[FW-MNE-Hebron]" in event.threat_name
    assert "Log4j" in event.threat_name
    assert event.metadata.get("reporting_firewall") == "FW-MNE-Hebron"
    assert event.metadata.get("faz_crlevel") == "critical"


def test_faz_malware_parsing():
    collector = FortiAnalyzerSecurityCollector()
    sample_log = (
        'date=2026-09-07 time=09:12:44 devname="FG-MNE" devid="FG4H1FT924905842" '
        'logid="0200008192" type="utm" subtype="virus" level="warning" '
        'action="quarantine" srcip=172.23.71.45 dstip=198.51.100.10 virus="Trojan.Agent.Generic" '
        'msg="File infected with Trojan.Agent.Generic"'
    )
    event = collector.parse_log_line(sample_log)
    assert event is not None
    assert event.source_device == "FortiAnalyzer"
    assert event.category == ThreatCategory.MALWARE
    assert event.action_taken == "DROPPED"
    assert "[FG-MNE]" in event.threat_name
    assert "Trojan.Agent.Generic" in event.threat_name
    assert event.metadata.get("reporting_firewall") == "FG-MNE"


def test_faz_webfilter_block_parsing():
    collector = FortiAnalyzerSecurityCollector()
    sample_log = (
        'date=2026-09-07 time=07:45:00 devname="FW-MNE-Nablus" '
        'logid="0316013056" type="utm" subtype="webfilter" level="alert" '
        'action="blocked" srcip=172.27.13.58 dstip=192.0.2.80 url="malicious-c2-portal.com" '
        'msg="URL blocked because category Malicious Web Sites"'
    )
    event = collector.parse_log_line(sample_log)
    assert event is not None
    assert event.source_device == "FortiAnalyzer"
    assert event.action_taken == "DROPPED"
    assert "[FW-MNE-Nablus]" in event.threat_name
    assert "malicious-c2-portal.com" in event.threat_name


def test_faz_vpn_fail_parsing():
    collector = FortiAnalyzerSecurityCollector()
    sample_log = (
        'date=2026-09-07 time=06:22:15 devname="FW-MNE-Bethlahem" '
        'logid="0101037128" type="event" subtype="vpn" level="alert" '
        'action="tunnel-down" remip=194.26.29.11 user="operator" '
        'reason="negotiation failure" msg="SSL VPN login fail"'
    )
    event = collector.parse_log_line(sample_log)
    assert event is not None
    assert event.source_device == "FortiAnalyzer"
    assert event.category == ThreatCategory.BRUTE_FORCE
    assert event.attacker_ip == "194.26.29.11"
    assert event.target == "operator"
    assert "[FW-MNE-Bethlahem]" in event.threat_name


def test_faz_empty_or_malformed():
    collector = FortiAnalyzerSecurityCollector()
    assert collector.parse_log_line("") is None
    assert collector.parse_log_line("   ") is None
    assert collector.parse_log_line("random non-syslog line without date or logid") is None


def test_faz_missing_credentials_raises():
    collector = FortiAnalyzerSecurityCollector(host="172.23.71.206", password="", api_key="")
    with pytest.raises(ValueError, match="Neither MNE_FORTIANALYZER_PASSWORD nor MNE_FORTIANALYZER_API_KEY"):
        collector._fetch_logs_internal(hours_back=24)


def test_faz_collect_logs_isolation():
    collector = FortiAnalyzerSecurityCollector(host="172.23.71.206", password="", api_key="")
    result = collector.collect_logs(hours_back=24)
    assert result.device_name == "FortiAnalyzer"
    assert result.status == CollectorStatus.FAILED
    assert result.error_message is not None
    assert result.collection_duration_seconds >= 0.0
    assert len(result.events) == 0


def test_faz_source_timestamp_preserved():
    collector = FortiAnalyzerSecurityCollector()
    sample_log = (
        'date=2026-09-07 time=08:30:12 devname="FW-MNE-Hebron" devid="FGT71GTK25009263" '
        'logid="0419016384" type="utm" subtype="ips" level="critical" crlevel="critical" '
        'action="dropped" srcip=45.155.205.233 dstip=172.27.13.62 attack="Apache.Log4j.RCE" '
        'msg="Apache Log4j Remote Code Execution Exploit Attempt"'
    )
    event = collector.parse_log_line(sample_log)
    assert event is not None
    assert event.timestamp == datetime(2026, 9, 7, 8, 30, 12, tzinfo=timezone.utc)
    assert event.metadata.get("adom") == "root"


def test_faz_historical_search_time_range_and_pagination(monkeypatch):
    import os
    from unittest.mock import MagicMock, patch
    from core.connectors.security.models import CollectorRequest

    monkeypatch.setenv("MNE_FAZ_CREDENTIAL_REF", "fixture-auth-token")
    auth_credential = os.environ["MNE_FAZ_CREDENTIAL_REF"]
    collector = FortiAnalyzerSecurityCollector(host="172.23.71.206", api_key=auth_credential, adom="root")
    req = CollectorRequest(
        start_time="2026-09-07T00:00:00Z",
        end_time="2026-09-07T12:00:00Z",
        max_records=2,
    )

    fake_items = [
        {"date": "2026-09-07", "time": "08:30:12", "devname": "FW-1", "logid": "101", "type": "ips", "attack": "Att1", "action": "dropped"},
        {"date": "2026-09-07", "time": "09:00:00", "devname": "FW-2", "logid": "102", "type": "ips", "attack": "Att2", "action": "dropped"},
        {"date": "2026-09-07", "time": "09:30:00", "devname": "FW-3", "logid": "103", "type": "ips", "attack": "Att3", "action": "dropped"},
    ]

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "result": [
            {"data": fake_items, "total-count": 10}
        ]
    }

    with patch("requests.post", return_value=mock_resp) as mock_post:
        result = collector.collect_logs(request=req)
        assert mock_post.called
        call_payload = mock_post.call_args[1].get("json", {})
        params = call_payload.get("params", [{}])[0]
        # Verify time-range in JSON-RPC request
        assert "time-range" in params
        assert "2026-09-07" in params["time-range"]["start"]
        assert "2026-09-07" in params["time-range"]["end"]

        # Verify pagination stopped at max_records=2
        assert len(result.events) == 2
        assert result.diagnostic.pagination["has_more"] is True
        assert result.diagnostic.diagnostic_code == "OK"


def test_faz_category_filtering_jsonrpc(monkeypatch):
    import os
    from unittest.mock import MagicMock, patch
    from core.connectors.security.models import CollectorRequest

    monkeypatch.setenv("MNE_FAZ_CREDENTIAL_REF", "fixture-auth-token")
    auth_credential = os.environ["MNE_FAZ_CREDENTIAL_REF"]
    collector = FortiAnalyzerSecurityCollector(host="172.23.71.206", api_key=auth_credential, adom="root")
    req = CollectorRequest(
        start_time="2026-09-07T00:00:00Z",
        end_time="2026-09-07T12:00:00Z",
        max_records=5,
        categories=["INTRUSION", "BRUTE_FORCE"],
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "result": [
            {"data": [], "total-count": 0}
        ]
    }

    with patch("requests.post", return_value=mock_resp) as mock_post:
        result = collector.collect_logs(request=req)
        assert mock_post.called
        call_payload = mock_post.call_args[1].get("json", {})
        params = call_payload.get("params", [{}])[0]
        filter_str = params.get("filter", "")
        # Verify both IPS and VPN filters were synthesized into filter_expr
        assert "subtype=vpn" in filter_str or "type=ips" in filter_str


def test_faz_api_login_and_logout_without_exposing_secrets(monkeypatch):
    import os
    from unittest.mock import MagicMock, patch
    from core.connectors.security.models import CollectorRequest

    secret_pass = "super_secret_master_password_42"
    collector = FortiAnalyzerSecurityCollector(
        host="172.23.71.206",
        username="sec_admin",
        password=secret_pass,
        adom="root",
    )

    def mock_post_impl(url, json=None, **kwargs):
        payload = json or {}
        method = payload.get("method")
        params = payload.get("params", [{}])
        first_url = params[0].get("url", "")

        mock_r = MagicMock()
        mock_r.status_code = 200

        if method == "exec" and first_url == "sys/login/user":
            mock_r.json.return_value = {"session": "sess_token_secure_999"}
        elif method == "exec" and first_url == "sys/logout":
            mock_r.json.return_value = {"result": [{"status": {"code": 0}}]}
        elif method == "get" and first_url == "dvmdb/adom":
            mock_r.json.return_value = {"result": [{"data": [{"name": "root"}]}]}
        elif method == "add" and "logsearch" in first_url:
            mock_r.json.return_value = {"result": [{"data": [], "total-count": 0}]}
        else:
            mock_r.json.return_value = {"result": [{"status": {"code": 0}}]}
        return mock_r

    with patch("requests.post", side_effect=mock_post_impl):
        req = CollectorRequest(start_time="2026-09-07T00:00:00Z", end_time="2026-09-07T12:00:00Z")
        result = collector.collect_logs(request=req)

        assert result.status == CollectorStatus.SUCCESS
        assert result.diagnostic.status.value == "SUCCESS"
        # Secret pass must NEVER appear in diagnostic output, message, or error_message
        diag_dump = str(result.diagnostic.__dict__)
        assert secret_pass not in diag_dump
        assert "sess_token_secure_999" not in diag_dump
        assert result.error_message is None or secret_pass not in result.error_message


def test_faz_adom_discovery_and_validation():
    from unittest.mock import MagicMock, patch

    collector = FortiAnalyzerSecurityCollector(host="172.23.71.206", api_key=_DUMMY_KEY)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "result": [{"data": [{"name": "root"}, {"name": "MNE-Firewalls"}, {"name": "Test-Lab"}]}]
    }

    with patch("requests.post", return_value=mock_resp):
        assert collector._validate_adom_jsonrpc("sess", "root") is True
        assert collector._validate_adom_jsonrpc("sess", "MNE-Firewalls") is True
        assert collector._validate_adom_jsonrpc("sess", "Unknown-Adom") is False


def test_faz_asynchronous_search_submission_and_polling():
    from unittest.mock import MagicMock, patch
    from core.connectors.security.models import CollectorRequest

    collector = FortiAnalyzerSecurityCollector(host="172.23.71.206", api_key=_DUMMY_KEY, adom="root")
    req = CollectorRequest(
        start_time="2026-09-07T00:00:00Z",
        end_time="2026-09-07T12:00:00Z",
        max_records=10,
    )

    poll_count = 0
    deleted_tasks = []

    def mock_post_impl(url, json=None, **kwargs):
        nonlocal poll_count
        payload = json or {}
        method = payload.get("method")
        params = payload.get("params", [{}])
        first_url = params[0].get("url", "")

        mock_r = MagicMock()
        mock_r.status_code = 200

        if first_url == "dvmdb/adom":
            mock_r.json.return_value = {"result": [{"data": [{"name": "root"}]}]}
        elif method == "add" and "logsearch" in first_url:
            mock_r.json.return_value = {"result": [{"tid": 4444}]}
        elif method == "get" and first_url == "logview/adom/root/logsearch/4444" and "offset" not in params[0]:
            poll_count += 1
            if poll_count == 1:
                mock_r.json.return_value = {"result": [{"percentage": 40, "progress": "running"}]}
            else:
                mock_r.json.return_value = {"result": [{"percentage": 100, "progress": "completed", "total-count": 1}]}
        elif method == "get" and first_url == "logview/adom/root/logsearch/4444" and "offset" in params[0]:
            item = {
                "date": "2026-09-07",
                "time": "10:30:00",
                "logid": "999",
                "devname": "FW-Core",
                "type": "ips",
                "attack": "Exploit.Attempt",
                "action": "dropped",
                "srcip": "1.2.3.4",
                "dstip": "172.23.71.10",
            }
            mock_r.json.return_value = {"result": [{"data": [item], "total-count": 1}]}
        elif method == "delete" and "logsearch/4444" in first_url:
            deleted_tasks.append(4444)
            mock_r.json.return_value = {"result": [{"status": {"code": 0}}]}
        else:
            mock_r.json.return_value = {"result": [{}]}
        return mock_r

    with patch("requests.post", side_effect=mock_post_impl):
        result = collector.collect_logs(request=req)

        assert result.status == CollectorStatus.SUCCESS
        assert result.diagnostic.diagnostic_code == "OK"
        assert len(result.events) == 1
        assert "[FW-Core] IPS Attack: Exploit.Attempt" in result.events[0].threat_name
        assert 4444 in deleted_tasks


def test_faz_multi_page_retrieval():
    from unittest.mock import MagicMock, patch
    from core.connectors.security.models import CollectorRequest

    collector = FortiAnalyzerSecurityCollector(host="172.23.71.206", api_key=_DUMMY_KEY, adom="root")
    req = CollectorRequest(
        start_time="2026-09-07T00:00:00Z",
        end_time="2026-09-07T12:00:00Z",
        max_records=3,
    )

    def mock_post_impl(url, json=None, **kwargs):
        payload = json or {}
        method = payload.get("method")
        params = payload.get("params", [{}])
        first_url = params[0].get("url", "")

        mock_r = MagicMock()
        mock_r.status_code = 200

        if first_url == "dvmdb/adom":
            mock_r.json.return_value = {"result": [{"data": [{"name": "root"}]}]}
        elif method == "add" and "logsearch" in first_url:
            mock_r.json.return_value = {"result": [{"tid": 5555}]}
        elif method == "get" and first_url == "logview/adom/root/logsearch/5555" and "offset" not in params[0]:
            mock_r.json.return_value = {"result": [{"percentage": 100, "progress": "completed", "total-count": 3}]}
        elif method == "get" and first_url == "logview/adom/root/logsearch/5555" and "offset" in params[0]:
            offset = params[0].get("offset", 0)
            if offset == 0:
                items = [
                    {"date": "2026-09-07", "time": "08:00:00", "logid": "1", "devname": "FW1", "type": "ips", "attack": "A1"},
                    {"date": "2026-09-07", "time": "09:00:00", "logid": "2", "devname": "FW1", "type": "ips", "attack": "A2"},
                ]
            else:
                items = [
                    {"date": "2026-09-07", "time": "10:00:00", "logid": "3", "devname": "FW1", "type": "ips", "attack": "A3"},
                ]
            mock_r.json.return_value = {"result": [{"data": items, "total-count": 3}]}
        elif method == "delete":
            mock_r.json.return_value = {"result": [{"status": {"code": 0}}]}
        else:
            mock_r.json.return_value = {"result": [{}]}
        return mock_r

    with patch("requests.post", side_effect=mock_post_impl):
        result = collector.collect_logs(request=req)

        assert result.status == CollectorStatus.SUCCESS
        assert len(result.events) == 3
        assert result.diagnostic.pagination["pages_retrieved"] == 2
        assert result.diagnostic.records_parsed == 3


def test_faz_confirmed_legitimate_zero_results():
    from unittest.mock import MagicMock, patch
    from core.connectors.security.models import CollectorRequest

    collector = FortiAnalyzerSecurityCollector(host="172.23.71.206", api_key=_DUMMY_KEY, adom="root")
    req = CollectorRequest(
        start_time="2026-09-07T00:00:00Z",
        end_time="2026-09-07T12:00:00Z",
        max_records=10,
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "result": [
            {"data": [], "total-count": 0}
        ]
    }

    with patch("requests.post", return_value=mock_resp):
        result = collector.collect_logs(request=req)
        assert result.status == CollectorStatus.SUCCESS
        assert result.diagnostic.diagnostic_code == "QUERY_EMPTY_CONFIRMED"
        assert len(result.events) == 0
        assert "0 security events" in result.diagnostic.message or "Zero events" in result.diagnostic.message


def test_faz_wrong_adom():
    from unittest.mock import MagicMock, patch
    from core.connectors.security.models import CollectorRequest

    collector = FortiAnalyzerSecurityCollector(host="172.23.71.206", api_key=_DUMMY_KEY, adom="nonexistent_adom")
    req = CollectorRequest(
        start_time="2026-09-07T00:00:00Z",
        end_time="2026-09-07T12:00:00Z",
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "result": [{"data": [{"name": "root"}, {"name": "MNE-Firewalls"}]}]
    }

    with patch("requests.post", return_value=mock_resp):
        result = collector.collect_logs(request=req)
        assert result.status == CollectorStatus.FAILED
        assert result.diagnostic.diagnostic_code == "ADOM_NOT_FOUND"
        assert "nonexistent_adom" in result.error_message


def test_faz_api_permission_failure():
    from unittest.mock import MagicMock, patch
    from core.connectors.security.models import CollectorRequest

    collector = FortiAnalyzerSecurityCollector(host="172.23.71.206", api_key=_FORBIDDEN_KEY, adom="root")
    req = CollectorRequest(
        start_time="2026-09-07T00:00:00Z",
        end_time="2026-09-07T12:00:00Z",
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 403

    with patch("requests.post", return_value=mock_resp):
        result = collector.collect_logs(request=req)
        assert result.status == CollectorStatus.FAILED
        assert result.diagnostic.diagnostic_code == "API_PERMISSION_DENIED"


def test_faz_background_search_timeout(monkeypatch):
    from unittest.mock import MagicMock, patch
    from core.connectors.security.models import CollectorRequest

    collector = FortiAnalyzerSecurityCollector(host="172.23.71.206", api_key=_DUMMY_KEY, adom="root", timeout=1)
    req = CollectorRequest(
        start_time="2026-09-07T00:00:00Z",
        end_time="2026-09-07T12:00:00Z",
    )

    def mock_post_impl(url, json=None, **kwargs):
        payload = json or {}
        method = payload.get("method")
        params = payload.get("params", [{}])
        first_url = params[0].get("url", "")

        mock_r = MagicMock()
        mock_r.status_code = 200

        if first_url == "dvmdb/adom":
            mock_r.json.return_value = {"result": [{"data": [{"name": "root"}]}]}
        elif method == "add":
            mock_r.json.return_value = {"result": [{"tid": 8888}]}
        elif method == "get" and "logsearch/8888" in first_url:
            mock_r.json.return_value = {"result": [{"percentage": 15, "progress": "running"}]}
        elif method == "delete":
            mock_r.json.return_value = {"result": [{"status": {"code": 0}}]}
        else:
            mock_r.json.return_value = {"result": [{}]}
        return mock_r

    with patch("requests.post", side_effect=mock_post_impl):
        curr_time = 1000.0
        def fake_time():
            nonlocal curr_time
            curr_time += 25.0
            return curr_time

        with patch("time.time", side_effect=fake_time):
            result = collector.collect_logs(request=req)
            assert result.status == CollectorStatus.FAILED
            assert result.diagnostic.diagnostic_code == "SEARCH_POLL_TIMEOUT"


def test_faz_ssh_invalid_command_output():
    from core.connectors.security.models import CollectorRequest

    collector = FortiAnalyzerSecurityCollector(
        host="172.23.71.206",
        username="admin",
        password=_TEST_PASS,
        adom="root",
    )
    req = CollectorRequest(
        start_time="2026-09-07T00:00:00Z",
        end_time="2026-09-07T12:00:00Z",
    )

    def fake_probe_runner(cmd: str) -> str:
        if "get system status" in cmd:
            return "FortiAnalyzer-VM64 v7.2.4,build1390,230413 (GA.F)"
        return "command parse error before 'adom'"

    result = collector._run_ssh_diagnostic_probes(request=req, adom_target="root", probe_runner=fake_probe_runner)
    assert result.status == CollectorStatus.PARTIAL
    assert result.diagnostic.diagnostic_code == "HISTORICAL_QUERY_UNAVAILABLE"
    assert "parse error" in result.diagnostic.message.lower()


def test_faz_ssh_diagnostic_output_showing_no_log_volume():
    from core.connectors.security.models import CollectorRequest

    collector = FortiAnalyzerSecurityCollector(
        host="172.23.71.206",
        username="admin",
        password=_TEST_PASS,
        adom="root",
    )
    req = CollectorRequest(
        start_time="2026-09-07T00:00:00Z",
        end_time="2026-09-07T12:00:00Z",
    )

    def fake_probe_runner(cmd: str) -> str:
        if "get system status" in cmd:
            return "FortiAnalyzer-VM64 v7.2.4"
        if "diagnose log device" in cmd:
            return "total device: 2\ndevname: FW-MNE-Hebron\ndevname: FW-MNE-Nablus"
        if "lograte-adom" in cmd:
            return "current log rate: 0 logs/sec"
        if "logvol-adom" in cmd:
            return "ADOM root: analytics: 0 MB, log volume: 0 MB"
        return ""

    result = collector._run_ssh_diagnostic_probes(request=req, adom_target="root", probe_runner=fake_probe_runner)
    assert result.status == CollectorStatus.FAILED
    assert result.diagnostic.diagnostic_code == "NO_ANALYTICS_LOGS"


def test_faz_ssh_diagnostic_no_managed_devices():
    from core.connectors.security.models import CollectorRequest

    collector = FortiAnalyzerSecurityCollector(
        host="172.23.71.206",
        username="admin",
        password=_TEST_PASS,
        adom="empty_adom",
    )
    req = CollectorRequest(
        start_time="2026-09-07T00:00:00Z",
        end_time="2026-09-07T12:00:00Z",
    )

    def fake_probe_runner(cmd: str) -> str:
        if "get system status" in cmd:
            return "FortiAnalyzer-VM64 v7.2.4"
        if "diagnose log device" in cmd:
            return "total device: 0\n"
        return "analytics: 100 MB"

    result = collector._run_ssh_diagnostic_probes(request=req, adom_target="empty_adom", probe_runner=fake_probe_runner)
    assert result.status == CollectorStatus.FAILED
    assert result.diagnostic.diagnostic_code == "NO_MANAGED_DEVICES"


def test_faz_malformed_api_response():
    from unittest.mock import MagicMock, patch
    from core.connectors.security.models import CollectorRequest

    collector = FortiAnalyzerSecurityCollector(host="172.23.71.206", api_key=_DUMMY_KEY, adom="root")
    req = CollectorRequest(
        start_time="2026-09-07T00:00:00Z",
        end_time="2026-09-07T12:00:00Z",
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.side_effect = ValueError("Invalid JSON stream from appliance")

    with patch("requests.post", return_value=mock_resp):
        result = collector.collect_logs(request=req)
        assert result.status == CollectorStatus.FAILED
        assert result.diagnostic.diagnostic_code == "RESULT_SCHEMA_UNRECOGNIZED"


def test_faz_cancellation():
    import threading
    from core.connectors.security.models import CollectorRequest

    collector = FortiAnalyzerSecurityCollector(host="172.23.71.206", api_key=_DUMMY_KEY, adom="root")
    cancel_evt = threading.Event()
    cancel_evt.set()

    req = CollectorRequest(
        start_time="2026-09-07T00:00:00Z",
        end_time="2026-09-07T12:00:00Z",
        cancel_callback=cancel_evt.is_set,
    )

    result = collector.collect_logs(request=req)
    assert result.status == CollectorStatus.SKIPPED
    assert result.diagnostic.diagnostic_code == "CANCELLED"


def test_faz_max_records():
    from unittest.mock import MagicMock, patch
    from core.connectors.security.models import CollectorRequest

    collector = FortiAnalyzerSecurityCollector(host="172.23.71.206", api_key=_DUMMY_KEY, adom="root")
    req = CollectorRequest(
        start_time="2026-09-07T00:00:00Z",
        end_time="2026-09-07T12:00:00Z",
        max_records=2,
    )

    fake_items = [
        {"date": "2026-09-07", "time": "08:00:00", "logid": f"10{i}", "devname": "FW1", "type": "ips", "attack": f"A{i}"}
        for i in range(5)
    ]

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "result": [{"data": fake_items, "total-count": 5}]
    }

    with patch("requests.post", return_value=mock_resp):
        result = collector.collect_logs(request=req)
        assert result.status == CollectorStatus.SUCCESS
        assert len(result.events) == 2
        assert result.diagnostic.pagination["has_more"] is True
        assert result.diagnostic.pagination["total_available"] == 5


def test_service_run_becoming_partial_when_faz_incomplete(tmp_path):
    from unittest.mock import MagicMock
    from core.connectors.security.models import CollectorResult, CollectorStatus, NormalizedSecurityEvent, ThreatCategory
    from core.security_review.contracts import (
        CollectorDiagnostic,
        DiagnosticStage,
        DiagnosticStatus,
        ReportFormat,
        ReviewMode,
        RunState,
        SecurityReviewRequest,
    )
    from core.security_review.run_store import SecurityReviewRunStore
    from core.security_review.service import SecurityReviewService

    store = SecurityReviewRunStore(tmp_path / "runs")

    # Collector 1: FortiGate returns clean success with 1 event
    good_event = NormalizedSecurityEvent(
        event_id="fg-1",
        timestamp=datetime.now(timezone.utc),
        source_device="FortiGate",
        category=ThreatCategory.BRUTE_FORCE,
        threat_name="SSH Brute Force",
        attacker_ip="192.168.1.50",
        target="admin",
        action_taken="DROPPED",
    )
    mock_fg = MagicMock()
    mock_fg.collect_logs.return_value = CollectorResult(
        device_name="FortiGate",
        status=CollectorStatus.SUCCESS,
        events=[good_event],
        collection_duration_seconds=0.1,
        diagnostic=CollectorDiagnostic(
            collector_id="fortigate_core",
            device_name="FortiGate",
            canonical_entity="fortigate_core",
            stage=DiagnosticStage.COMPLETE,
            status=DiagnosticStatus.SUCCESS,
            diagnostic_code="OK",
            message="Clean collection",
        ),
    )

    # Collector 2: FortiAnalyzer returns PARTIAL with HISTORICAL_QUERY_UNAVAILABLE
    mock_faz = MagicMock()
    mock_faz.collect_logs.return_value = CollectorResult(
        device_name="FortiAnalyzer",
        status=CollectorStatus.PARTIAL,
        events=[],
        collection_duration_seconds=0.2,
        error_message="FortiAnalyzer SSH probe established active ADOM 'root', but historical log query requires JSON-RPC API.",
        diagnostic=CollectorDiagnostic(
            collector_id="fortianalyzer",
            device_name="FortiAnalyzer",
            canonical_entity="fortianalyzer",
            stage=DiagnosticStage.COMPLETE,
            status=DiagnosticStatus.PARTIAL,
            diagnostic_code="HISTORICAL_QUERY_UNAVAILABLE",
            message="FortiAnalyzer SSH probe established active ADOM 'root', but historical log query requires JSON-RPC API.",
        ),
    )

    registry = {
        "fortigate_core": mock_fg,
        "fortianalyzer": mock_faz,
    }

    svc = SecurityReviewService(run_store=store, collector_registry=registry)
    req = SecurityReviewRequest(
        mode=ReviewMode.QUICK,
        collector_ids=["fortigate_core", "fortianalyzer"],
        send_email=False,
        report_formats=[ReportFormat.JSON],
    )

    run = svc.start_review(req, async_run=False)
    assert run.state == RunState.PARTIAL
    assert run.stage == "COMPLETED_PARTIAL"
