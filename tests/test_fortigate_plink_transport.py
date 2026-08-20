#!/usr/bin/env python3
"""Offline tests for the pinned Plink FortiGate transport boundary."""

import subprocess
import sys
from pathlib import Path


base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(base_dir))

from integrations.fortigate.plink_transport import PinnedPlinkFortiGateTransport


def _workspace(tmp_path: Path) -> tuple[Path, Path]:
    source = tmp_path / "source.env"
    source.write_text(
        "MNE_FORTIGATE_HOST=172.23.70.4\n"
        "MNE_FORTIGATE_USERNAME=adminread\n"
        "MNE_FORTIGATE_PASSWORD=fixture-password\n",
        encoding="utf-8",
    )
    plink = tmp_path / "plink.exe"
    plink.write_text("fixture", encoding="utf-8")
    (tmp_path / ".env").write_text(
        "FORTIGATE_CREDENTIAL_REF=secretref://local/fortigate-edge-readonly\n"
        f"MNE_FORTIGATE_CREDENTIAL_ENV_FILE={source.as_posix()}\n"
        "MNE_FORTIGATE_HOST_KEY=MNE_FORTIGATE_HOST\n"
        "MNE_FORTIGATE_USERNAME_KEY=MNE_FORTIGATE_USERNAME\n"
        "MNE_FORTIGATE_PASSWORD_KEY=MNE_FORTIGATE_PASSWORD\n"
        "MNE_FORTIGATE_SSH_HOSTKEY=ssh-ed25519 255 SHA256:fixturekey=\n",
        encoding="utf-8",
    )
    return source, plink


def _request() -> dict:
    return {
        "adapter_id": "fortigate_ssh_readonly",
        "profile_name": "fortigate_edge",
        "entity_id": "fw-fortigate-edge-01",
        "target": "172.23.70.4",
        "check_id": "system_status",
        "command": "get system status",
        "credential_reference": "secretref://local/fortigate-edge-readonly",
        "timeout_seconds": 10,
        "max_output_bytes": 65536,
        "simulation_mode": False,
    }


def test_plink_transport_uses_pinned_key_and_temporary_password_file(tmp_path: Path) -> None:
    _, plink = _workspace(tmp_path)
    observed: dict = {}

    def runner(arguments: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
        observed["arguments"] = list(arguments)
        password_path = Path(arguments[arguments.index("-pwfile") + 1])
        observed["password_path"] = password_path
        observed["password"] = password_path.read_text(encoding="utf-8").strip()
        observed["kwargs"] = kwargs
        return subprocess.CompletedProcess(arguments, 0, "Hostname: FG-MNE\n", "")

    result = PinnedPlinkFortiGateTransport(
        base_dir=tmp_path,
        runner=runner,
        plink_path=plink,
    )(_request())

    assert result["status"] == "SUCCESS"
    assert result["connection_attempted"] is True
    assert result["credential_returned"] is False
    assert "-hostkey" in observed["arguments"]
    assert "-pwfile" in observed["arguments"]
    assert "fixture-password" not in observed["arguments"]
    assert observed["password"] == "fixture-password"
    assert observed["kwargs"]["timeout"] == 10
    assert observed["kwargs"]["creationflags"] == 0 or sys.platform == "win32"
    assert not observed["password_path"].exists()


def test_plink_transport_rejects_scope_before_process_start(tmp_path: Path) -> None:
    _, plink = _workspace(tmp_path)
    calls: list = []
    request = _request()
    request["command"] = "show firewall policy"
    result = PinnedPlinkFortiGateTransport(
        base_dir=tmp_path,
        runner=lambda *args, **kwargs: calls.append((args, kwargs)),
        plink_path=plink,
    )(request)

    assert result["status"] == "SCOPE_BLOCKED"
    assert result["connection_attempted"] is False
    assert calls == []


def test_plink_transport_accepts_exact_interface_status_check(tmp_path: Path) -> None:
    _, plink = _workspace(tmp_path)
    observed: list[list[str]] = []

    def runner(arguments: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
        observed.append(arguments)
        return subprocess.CompletedProcess(
            arguments,
            0,
            "==[port1]\nstatus: up\n==[port2]\nstatus: down\n",
            "",
        )

    request = _request()
    request["check_id"] = "interface_stats"
    request["command"] = "get system interface physical"
    result = PinnedPlinkFortiGateTransport(
        base_dir=tmp_path,
        runner=runner,
        plink_path=plink,
    )(request)

    assert result["status"] == "SUCCESS"
    assert observed[0][-1] == "get system interface physical"
    assert result["credential_returned"] is False


def test_plink_transport_bounds_timeout_and_authentication_failure(tmp_path: Path) -> None:
    _, plink = _workspace(tmp_path)

    def timeout_runner(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=kwargs["timeout"])

    timed_out = PinnedPlinkFortiGateTransport(
        base_dir=tmp_path,
        runner=timeout_runner,
        plink_path=plink,
    )(_request())
    denied = PinnedPlinkFortiGateTransport(
        base_dir=tmp_path,
        runner=lambda arguments, **kwargs: subprocess.CompletedProcess(
            arguments, 1, "", "Access denied"
        ),
        plink_path=plink,
    )(_request())

    assert timed_out["status"] == "TIMEOUT"
    assert timed_out["connection_attempted"] is True
    assert denied["status"] == "AUTHENTICATION_FAILED"
    assert denied["raw_error_returned"] is False
