"""Receive threat-only FMC/FTD security syslog over UDP and append JSONL.

This is deliberately a narrow local boundary: it accepts CEF datagrams only
from the configured FTD/FMC source addresses, drops connection/allow telemetry,
and writes one normalized JSON object per accepted threat event. File rotation
is handled by rotate_fmc_estreamer_spool.ps1; the file is opened per event so a
rotation pass can acquire the file after each write.

FMC/FTD security-event logging normally uses Cisco RFC5424/EMBLEM syslog, not
CEF. The receiver therefore accepts both formats. Security Intelligence is
represented by the 430002/430003 connection-event IDs, so those IDs are
accepted only when SI-specific fields/reasons are present; ordinary connection
and Allow events are discarded.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_CEF_MARKER = "CEF:"
_KEY_RE = re.compile(r"(?:^|\s)([A-Za-z][A-Za-z0-9_.-]*)=")
_THREAT_MARKERS = (
    "intrusion",
    "exploit",
    "malware",
    "virus",
    "trojan",
    "ransom",
    "file event",
    "security intelligence",
    "blacklist",
    "botnet",
    "sinkhole",
    "phishing",
)
_CONNECTION_MARKERS = ("connection", "flow", "access control", "allowed traffic")
_SECURITY_EVENT_RE = re.compile(
    r"%(?:NGIPS|FTD|FIREPOWER)-(?P<severity>\d+)-(?P<event_id>43000[1-5])\s*:\s*(?P<body>.*)$",
    re.IGNORECASE,
)
_FIELD_RE = re.compile(r"(?:^|,\s*)(?P<key>[A-Za-z][A-Za-z0-9_]*)\s*:\s*")
_SI_REASON_MARKERS = ("ip block", "dns block", "url block", "security intelligence", "botnet")


def _cef_unescape(value: str) -> str:
    return (
        value.replace(r"\=", "=")
        .replace(r"\|", "|")
        .replace(r"\n", "\n")
        .replace(r"\r", "\r")
        .replace(r"\\", "\\")
    )


def parse_cef(line: str) -> dict[str, Any] | None:
    """Parse a syslog-wrapped CEF line into the collector's input shape."""
    marker = line.find(_CEF_MARKER)
    if marker < 0:
        return None
    cef = line[marker:]
    parts = cef.split("|", 7)
    if len(parts) != 8 or not parts[0].startswith("CEF:"):
        return None
    _version, vendor, product, device_version, signature_id, name, severity, extension = parts
    matches = list(_KEY_RE.finditer(extension))
    fields: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(extension)
        fields[match.group(1)] = _cef_unescape(extension[match.end() : end].strip())

    label = " ".join(
        value for value in (name, fields.get("cat"), fields.get("cs1"), fields.get("msg")) if value
    ).lower()
    if any(marker in label for marker in _CONNECTION_MARKERS) and not any(
        marker in label for marker in _THREAT_MARKERS
    ):
        return None
    if not any(marker in label for marker in _THREAT_MARKERS):
        return None

    raw_time = fields.get("rt") or fields.get("eventTime") or fields.get("timestamp")
    timestamp: Any = datetime.now(timezone.utc).isoformat()
    if raw_time:
        try:
            numeric = float(raw_time)
            timestamp = int(numeric / 1000) if numeric > 1e11 else int(numeric)
        except ValueError:
            timestamp = raw_time

    event_id = fields.get("externalId") or fields.get("eventId") or fields.get("id") or signature_id
    if not event_id:
        event_id = hashlib.sha256(line.encode("utf-8", "replace")).hexdigest()[:20]

    message = fields.get("msg") or name or f"{vendor} {product} event"
    event: dict[str, Any] = {
        "id": event_id,
        "timestamp": timestamp,
        "sourceIp": fields.get("src") or fields.get("sourceIp"),
        "destinationIp": fields.get("dst") or fields.get("destinationIp"),
        "ruleMessage": message,
        "action": fields.get("act") or fields.get("action") or "alert",
        "ThreatName": name,
        "cef": {
            "device_vendor": vendor,
            "device_product": product,
            "device_version": device_version,
            "signature_id": signature_id,
            "severity": severity,
            "category": fields.get("cat"),
        },
        "metadata": {"transport": "SYSLOG_CEF", "source": "FMC/FTD"},
    }
    return {key: value for key, value in event.items() if value is not None}


def _parse_syslog_fields(body: str) -> dict[str, str]:
    matches = list(_FIELD_RE.finditer(body))
    fields: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        value = body[match.end() : end].strip().rstrip(",")
        fields[match.group("key")] = value
    return fields


def _parse_event_timestamp(value: str | None) -> Any:
    if not value:
        return datetime.now(timezone.utc).isoformat()
    candidate = value.strip()
    try:
        parsed = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc).isoformat()
    except ValueError:
        return candidate


def parse_security_syslog(line: str) -> dict[str, Any] | None:
    """Parse Cisco FTD security-event RFC5424/EMBLEM syslog."""
    match = _SECURITY_EVENT_RE.search(line)
    if match is None:
        return None

    event_id = match.group("event_id")
    body = match.group("body")
    fields = _parse_syslog_fields(body)
    lowered = {key.lower(): value for key, value in fields.items()}
    reason = lowered.get("accesscontrolrulereason", "").lower()
    si_field = any(
        key.lower().endswith("sicategory") and value not in {"", "unknown", "none"}
        for key, value in fields.items()
    )
    is_si = si_field or any(marker in reason for marker in _SI_REASON_MARKERS)

    # Cisco's security-event IDs 430002/430003 cover all connection events;
    # retain only Security-Intelligence-specific blocked/marked events.
    if event_id in {"430002", "430003"} and not is_si:
        return None
    if event_id not in {"430001", "430005"} and not is_si:
        return None

    label = {
        "430001": "Intrusion event",
        "430005": "File malware event",
        "430002": "Security Intelligence event",
        "430003": "Security Intelligence event",
    }[event_id]
    threat_name = (
        lowered.get("signature")
        or lowered.get("malwarename")
        or lowered.get("filename")
        or lowered.get("urlsicategory")
        or lowered.get("dnssicategory")
        or lowered.get("ipreputationsicategory")
        or label
    )
    identity = ":".join(
        value
        for value in (
            event_id,
            lowered.get("deviceuuid"),
            lowered.get("firstpacketsecond"),
            lowered.get("connectionid"),
            lowered.get("signatureid"),
        )
        if value
    )
    stable_id = identity or hashlib.sha256(line.encode("utf-8", "replace")).hexdigest()[:20]
    event: dict[str, Any] = {
        "id": stable_id,
        "timestamp": _parse_event_timestamp(
            lowered.get("firstpacketsecond") or lowered.get("eventtime")
        ),
        "sourceIp": lowered.get("srcip"),
        "destinationIp": lowered.get("dstip"),
        "ruleMessage": f"{label}: {threat_name}",
        "action": lowered.get("accesscontrolruleaction") or "alert",
        "ThreatName": threat_name,
        "cef": {
            "signature_id": event_id,
            "severity": match.group("severity"),
            "category": label,
        },
        "metadata": {
            "transport": "SYSLOG_SECURITY_EVENT",
            "source": "FMC/FTD",
            "syslog_event_id": event_id,
            "security_intelligence": is_si,
        },
    }
    return {key: value for key, value in event.items() if value is not None}


def parse_line(line: str) -> dict[str, Any] | None:
    """Parse either CEF or Cisco security-event syslog."""
    return parse_cef(line) or parse_security_syslog(line)


def append_event(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")


def write_health(path: Path, *, bind: str, port: int, started_at: str, accepted_events: int, status: str) -> None:
    """Publish a short-lived receiver heartbeat without writing security events."""
    payload = {
        "status": status,
        "bind": bind,
        "port": port,
        "pid": os.getpid(),
        "started_at_utc": started_at,
        "last_seen_utc": datetime.now(timezone.utc).isoformat(),
        "accepted_events": accepted_events,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.tmp")
    temporary.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    temporary.replace(path)


def receive(
    bind: str,
    port: int,
    spool: Path,
    allowed_sources: set[str],
    health_file: Path | None = None,
    once: bool = False,
) -> int:
    health_path = health_file or spool.with_name("receiver-health.json")
    started_at = datetime.now(timezone.utc).isoformat()
    accepted_events = 0
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((bind, port))
        sock.settimeout(30.0)
        write_health(
            health_path,
            bind=bind,
            port=port,
            started_at=started_at,
            accepted_events=accepted_events,
            status="LISTENING",
        )
        while True:
            try:
                payload, address = sock.recvfrom(65535)
            except socket.timeout:
                write_health(
                    health_path,
                    bind=bind,
                    port=port,
                    started_at=started_at,
                    accepted_events=accepted_events,
                    status="LISTENING",
                )
                continue
            if address[0] not in allowed_sources:
                continue
            event = parse_line(payload.decode("utf-8", "replace").strip())
            if event is not None:
                append_event(spool, event)
                accepted_events += 1
            write_health(
                health_path,
                bind=bind,
                port=port,
                started_at=started_at,
                accepted_events=accepted_events,
                status="LISTENING",
            )
            if once:
                break
    write_health(
        health_path,
        bind=bind,
        port=port,
        started_at=started_at,
        accepted_events=accepted_events,
        status="STOPPED",
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bind", default="172.23.50.62")
    parser.add_argument("--port", type=int, default=1514)
    parser.add_argument(
        "--spool",
        type=Path,
        default=Path(r"F:\MNE_Brain\runtime\fmc-estreamer\events.jsonl"),
    )
    parser.add_argument(
        "--allowed-source",
        action="append",
        default=["172.23.70.78"],
        help="Allowed FTD/FMC source address; repeat for additional sources.",
    )
    parser.add_argument(
        "--health-file",
        type=Path,
        default=None,
        help="Optional receiver heartbeat JSON path (default: beside the spool).",
    )
    parser.add_argument("--once", action="store_true", help="Receive exactly one datagram, then exit.")
    args = parser.parse_args()
    if not (0 < args.port < 65536):
        parser.error("--port must be between 1 and 65535")
    return receive(args.bind, args.port, args.spool, set(args.allowed_source), args.health_file, args.once)


if __name__ == "__main__":
    sys.exit(main())
