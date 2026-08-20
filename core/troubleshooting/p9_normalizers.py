"""Small deterministic normalizers that discard P9 raw output after extraction."""

import json
import re
from typing import Any


def _counts(text: str, words: tuple[str, ...]) -> dict[str, int]:
    lowered = text.casefold()
    return {word.replace(" ", "_"): len(re.findall(rf"\b{re.escape(word)}\b", lowered)) for word in words}


def _json_observations(text: str) -> dict[str, Any]:
    candidate = text.strip().splitlines()[-1] if text.strip() else "{}"
    try:
        parsed = json.loads(candidate)
    except (json.JSONDecodeError, TypeError):
        return {"json_valid": False}
    if not isinstance(parsed, dict):
        return {"json_valid": False}
    safe: dict[str, Any] = {"json_valid": True}
    for key, value in parsed.items():
        clean_key = re.sub(r"[^a-z0-9_]", "_", str(key).casefold())[:48]
        if isinstance(value, bool) or value is None:
            safe[clean_key] = value
        elif isinstance(value, (int, float)):
            safe[clean_key] = value
        elif isinstance(value, str) and len(value) <= 80:
            safe[clean_key] = value
        elif isinstance(value, list) and len(value) <= 20 and all(isinstance(item, str) and len(item) <= 80 for item in value):
            safe[clean_key] = value
    return safe


def _inventory_observations(text: str, *, fmc: bool = False) -> dict[str, Any]:
    """Return aggregate object/state counts without names, IDs, addresses, or topology."""
    try:
        parsed = json.loads(text.strip())
    except (json.JSONDecodeError, TypeError):
        return {"json_valid": False, "signal_quality": "LOW"}
    if isinstance(parsed, dict):
        items = parsed.get("value", parsed.get("items", []))
    else:
        items = parsed
    if isinstance(items, dict):
        items = [items]
    if not isinstance(items, list):
        return {"json_valid": True, "object_count": 0, "signal_quality": "LOW"}
    safe_states = ("connected", "disconnected", "not_responding", "powered_on", "powered_off", "up", "down", "online", "offline", "pending", "deployed")
    state_counts = {state: 0 for state in safe_states}
    accessible_true = accessible_false = 0
    for item in items[:10000]:
        if not isinstance(item, dict):
            continue
        flattened = " ".join(str(value).casefold() for key, value in item.items() if key.casefold() in {"state", "status", "power_state", "connection_state", "healthstatus", "deploymentsstatus"})
        for state in safe_states:
            state_counts[state] += len(re.findall(rf"\b{re.escape(state)}\b", flattened))
        accessible = item.get("accessible")
        accessible_true += accessible is True
        accessible_false += accessible is False
    observations: dict[str, Any] = {"json_valid": True, "object_count": len(items), **{key: value for key, value in state_counts.items() if value}}
    if accessible_true or accessible_false:
        observations.update({"accessible_true": accessible_true, "accessible_false": accessible_false})
    if fmc:
        observations["managed_objects_present"] = len(items) > 0
    observations["signal_quality"] = "HIGH" if items else "LOW"
    return observations


def normalize_output(normalizer: str, output: str) -> tuple[dict[str, Any], str]:
    text = output[:131072]
    lines = [line for line in text.splitlines() if line.strip()]
    if normalizer == "fortigate_interfaces":
        observations = {"sections": len(re.findall(r"^==\s*\[", text, re.MULTILINE)), **_counts(text, ("up", "down", "error"))}
    elif normalizer == "fortigate_routes":
        observations = {"route_lines": sum(bool(re.match(r"^[A-Z][A-Z*]?\s+", line.strip())) for line in lines), "default_route_present": "0.0.0.0/0" in text, **_counts(text, ("connected", "static", "blackhole"))}
    elif normalizer == "fortigate_vpn":
        observations = {"nonempty_lines": len(lines), "configuration_present": len(lines) > 2, **_counts(text, ("up", "down", "tunnel", "ssl", "ipsec"))}
    elif normalizer in ("f5_virtuals", "f5_pools"):
        observations = {"objects": len(re.findall(r"^Ltm::", text, re.MULTILINE)), **_counts(text, ("available", "offline", "unknown", "enabled", "disabled"))}
    elif normalizer in ("windows_json", "replication_json"):
        observations = _json_observations(text)
    elif normalizer == "rest_inventory":
        observations = _inventory_observations(text)
    elif normalizer == "fmc_json":
        observations = _inventory_observations(text, fmc=True)
    elif normalizer == "linux_services":
        states = [line.strip().casefold() for line in lines if len(line.strip()) < 40]
        observations = {"services_reported": len(states), "active": states.count("active"), "inactive": states.count("inactive"), "failed": states.count("failed")}
    elif normalizer == "linux_ports":
        ports = sorted({int(item) for item in re.findall(r":(\d{1,5})(?:\s|$)", text) if 0 < int(item) <= 65535})
        observations = {"listening_port_count": len(ports), "expected_22": 22 in ports, "expected_80": 80 in ports, "expected_443": 443 in ports}
    elif normalizer == "linux_resources":
        percentages = [int(item) for item in re.findall(r"\b(\d{1,3})%", text) if int(item) <= 100]
        observations = {"maximum_percent_seen": max(percentages, default=0), "sample_count": len(percentages)}
    elif normalizer == "vcenter_health":
        observations = {"health_signal": next((word for word in ("red", "orange", "yellow", "gray", "green") if re.search(rf"\b{word}\b", text.casefold())), "unknown"), "nonempty_lines": len(lines)}
    elif normalizer == "network_errors":
        error_lines = [line for line in lines if re.search(r"error|crc|drop|discard", line, re.IGNORECASE)]
        nonzero = sum(bool(re.search(r"\b[1-9]\d*\b", line)) for line in error_lines)
        observations = {"table_lines": len(lines), "error_label_lines": len(error_lines), "nonzero_error_lines": nonzero}
    elif normalizer == "network_interfaces":
        observations = {"nonempty_lines": len(lines), **_counts(text, ("up", "down", "administratively down", "port-channel", "bundled"))}
        observations["signal_quality"] = "HIGH" if (
            observations["up"] + observations["down"] + observations["port-channel"] + observations["bundled"] > 0
        ) else "LOW"
    elif normalizer == "identity_status":
        observations = {"nonempty_lines": len(lines), **_counts(text, ("connected", "pending", "success", "failed", "up", "down", "version", "model", "firmware"))}
        identity_terms = observations["version"] + observations["model"] + observations["firmware"]
        observations["version_number_present"] = bool(re.search(r"\b\d+\.\d+(?:\.\d+){0,3}\b", text))
        observations["signal_quality"] = "HIGH" if len(lines) >= 3 or identity_terms > 0 or observations["version_number_present"] else "LOW"
    else:
        raise ValueError("Unknown P9 normalizer.")
    summary_parts = [f"{key}={value}" for key, value in observations.items() if isinstance(value, (bool, int, float, str))]
    return observations, "; ".join(summary_parts)[:240]
