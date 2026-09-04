"""Render reviewed P10 transactions into exact vendor commands or API requests.

This module never opens a connection.  It is shared by plan presentation and the
live driver so the bytes approved by the owner are the bytes submitted later.
Unsupported or underspecified actions fail closed instead of emitting a guess.
"""

from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any


class P10CommandError(ValueError):
    """The requested action cannot be rendered safely and exactly."""


_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/@() +,-]{0,255}$")
_INTERFACE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/-]{0,63}$")


def _required(arguments: dict[str, Any], key: str) -> str:
    value = arguments.get(key)
    if not isinstance(value, str) or not value or not _NAME.fullmatch(value):
        raise P10CommandError(f"Exact {key} is required for this action.")
    return value


def _interface(arguments: dict[str, Any]) -> str:
    value = arguments.get("interface")
    if not isinstance(value, str) or not value or not _INTERFACE.fullmatch(value):
        raise P10CommandError("Exact interface is required for this action.")
    return value


def _ps(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _cli(protocol: str, commands: list[str], *, privilege_mode: str = "none") -> dict[str, Any]:
    if not commands or any(not isinstance(item, str) or not item.strip() for item in commands):
        raise P10CommandError("An exact non-empty command bundle is required.")
    return {"protocol": protocol, "commands": commands, "display": commands, "privilege_mode": privilege_mode}


def _rest(method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    if method not in {"POST", "PUT", "PATCH", "DELETE"} or not path.startswith("/"):
        raise P10CommandError("An exact write API request is required.")
    display = f"{method} {path}"
    if body is not None:
        display += "\n" + json.dumps(body, sort_keys=True, separators=(",", ":"))
    return {"protocol": "https_json", "method": method, "path": path, "body": deepcopy(body), "display": [display]}


def _fortigate(operation_type: str, action: str, a: dict[str, Any], rollback: bool) -> dict[str, Any]:
    name = _required(a, "resource_name")
    inverse = {
        "create_address": "delete_address", "create_subnet": "delete_address", "create_ip_range": "delete_address",
        "create_fqdn": "delete_address", "enable_policy": "disable_policy", "disable_policy": "enable_policy",
        "create_route": "delete_route", "create_group": "delete_group", "create_service": "delete_service",
        "create_service_group": "delete_service_group", "create_vip": "delete_vip", "create_ip_pool": "delete_ip_pool",
    }
    if rollback:
        action = inverse.get(action, "")
        if not action:
            raise P10CommandError("This action needs captured prior state before a safe rollback can be rendered.")
    table = {
        "address_object": "firewall address", "address_group": "firewall addrgrp",
        "service_catalog": "firewall service custom", "nat_objects": "firewall vip",
        "firewall_policy": "firewall policy", "static_route": "router static",
    }.get(operation_type)
    if operation_type == "sslvpn_objects":
        table = "vpn ssl web portal" if "portal" in action else ("firewall policy" if "policy" in action else "firewall address")
    if not table:
        raise P10CommandError("No reviewed live FortiGate renderer exists for this operation.")
    if action.startswith("delete_"):
        return _cli("ssh_cli", [f"config {table}", f"delete {name}", "end"])
    if action in {"enable_policy", "disable_policy"}:
        state = "enable" if action == "enable_policy" else "disable"
        return _cli("ssh_cli", [f"config {table}", f"edit {name}", f"set status {state}", "next", "end"])
    commands = [f"config {table}", f"edit {name}"]
    value = a.get("value")
    secondary = a.get("secondary_value")
    if action in {"create_address", "create_subnet", "update_address"}:
        commands.append(f"set subnet {_required(a, 'value')}")
    elif action == "create_ip_range":
        commands += ["set type iprange", f"set start-ip {_required(a, 'value')}", f"set end-ip {_required(a, 'secondary_value')}"]
    elif action == "create_fqdn":
        commands += ["set type fqdn", f"set fqdn {_required(a, 'value')}"]
    elif operation_type == "address_group":
        commands.append(f"set member {_required(a, 'value')}")
    elif operation_type == "service_catalog":
        commands.append(f"set tcp-portrange {_required(a, 'value')}")
    elif operation_type == "nat_objects":
        commands.append(f"set extip {_required(a, 'value')}")
        if secondary:
            commands.append(f"set mappedip {secondary}")
    elif operation_type == "static_route":
        commands.append(f"set dst {_required(a, 'value')}")
        if secondary:
            commands.append(f"set gateway {secondary}")
        if a.get("interface"):
            commands.append(f"set device {_interface(a)}")
    elif operation_type in {"firewall_policy", "sslvpn_objects"}:
        raise P10CommandError("Policy creation needs explicit source, destination, service, schedule, NAT, and interface fields.")
    elif value:
        commands.append(f"set comments {value}")
    commands += ["next", "end"]
    return _cli("ssh_cli", commands)


def _f5(operation_type: str, action: str, a: dict[str, Any], rollback: bool) -> dict[str, Any]:
    name = _required(a, "resource_name")
    inverse = {"create_node": "delete_node", "enable_member": "disable_member", "disable_member": "enable_member",
               "enable_virtual_server": "disable_virtual_server", "create_pool": "delete_pool", "create_monitor": "delete_monitor"}
    if rollback:
        action = inverse.get(action, "")
        if not action:
            raise P10CommandError("This BIG-IP action needs captured prior state for rollback.")
    kind = {
        "node": "ltm node", "pool_member": "ltm pool", "health_monitor": "ltm monitor http",
        "virtual_server": "ltm virtual", "profile": "ltm profile http", "irule": "ltm rule",
    }.get(operation_type)
    if action.startswith("delete_") and kind:
        return _cli("ssh_cli", [f"tmsh delete {kind} /Common/{name}"])
    if operation_type == "node":
        verb = "create" if action == "create_node" else "modify"
        return _cli("ssh_cli", [f"tmsh {verb} ltm node /Common/{name} address {_required(a, 'value')}"])
    if operation_type == "pool_member":
        if action == "create_pool":
            return _cli("ssh_cli", [f"tmsh create ltm pool /Common/{name}"])
        if action in {"add_member", "enable_member", "disable_member", "drain_member"}:
            member = _required(a, "value")
            state = {"add_member": "members add", "enable_member": "members modify", "disable_member": "members modify", "drain_member": "members modify"}[action]
            suffix = "" if action == "add_member" else (" { session user-enabled state user-up }" if action == "enable_member" else " { session user-disabled }")
            return _cli("ssh_cli", [f"tmsh modify ltm pool /Common/{name} {state} {{ {member}{suffix} }}"])
    if operation_type == "health_monitor" and action in {"create_monitor", "update_monitor"}:
        verb = "create" if action == "create_monitor" else "modify"
        return _cli("ssh_cli", [f"tmsh {verb} ltm monitor http /Common/{name} send {_required(a, 'value')}"])
    if operation_type == "virtual_server":
        if action in {"enable_virtual_server", "disable_virtual_server"}:
            state = "enabled" if action.startswith("enable") else "disabled"
            return _cli("ssh_cli", [f"tmsh modify ltm virtual /Common/{name} {state}"])
        if action == "create_disabled_virtual_server":
            return _cli("ssh_cli", [f"tmsh create ltm virtual /Common/{name} destination {_required(a, 'value')} pool /Common/{_required(a, 'secondary_value')} disabled"])
    if operation_type == "waf_attachment" and action in {"attach_waf_policy", "detach_waf_policy"}:
        verb = "add" if action.startswith("attach") else "delete"
        return _cli("ssh_cli", [f"tmsh modify ltm virtual /Common/{name} policies {verb} {{ /Common/{_required(a, 'value')} }}"])
    raise P10CommandError("No reviewed live BIG-IP renderer exists for this exact action.")


def _fmc(operation_type: str, action: str, a: dict[str, Any], rollback: bool) -> dict[str, Any]:
    name = _required(a, "resource_name")
    domain = "{domainUUID}"
    if operation_type == "network_object" and action in {"create_network", "create_host", "create_range", "create_fqdn"}:
        endpoint_type = {"create_network": "networks", "create_host": "hosts", "create_range": "ranges", "create_fqdn": "fqdns"}[action]
        if rollback:
            raise P10CommandError("FMC create rollback requires the object UUID returned by the committed request.")
        body = {"name": name, "value": _required(a, "value"), "type": {"networks": "Network", "hosts": "Host", "ranges": "Range", "fqdns": "FQDN"}[endpoint_type]}
        return _rest("POST", f"/api/fmc_config/v1/domain/{domain}/object/{endpoint_type}", body)
    if operation_type == "object_group" and action == "delete_group":
        object_id = _required(a, "value")
        if rollback:
            raise P10CommandError("Deleted FMC groups require captured full JSON for rollback.")
        return _rest("DELETE", f"/api/fmc_config/v1/domain/{domain}/object/networkgroups/{object_id}")
    raise P10CommandError("This FMC action needs exact object, policy, or device UUIDs and a complete typed body.")


def _windows(operation_type: str, action: str, a: dict[str, Any], rollback: bool) -> dict[str, Any]:
    name = _required(a, "resource_name")
    if rollback and action not in {"start_site", "stop_site", "enable_user", "disable_user"}:
        raise P10CommandError("This PowerShell action has no safe automatic rollback.")
    if rollback:
        action = {"start_site": "stop_site", "stop_site": "start_site", "enable_user": "disable_user", "disable_user": "enable_user"}[action]
    commands = {
        ("windows_service", "start_service"): f"Start-Service -Name {_ps(name)}",
        ("windows_service", "restart_service"): f"Restart-Service -Name {_ps(name)} -Force",
        ("iis", "start_site"): f"Start-Website -Name {_ps(name)}",
        ("iis", "stop_site"): f"Stop-Website -Name {_ps(name)}",
        ("iis", "start_app_pool"): f"Start-WebAppPool -Name {_ps(name)}",
        ("iis", "restart_app_pool"): f"Restart-WebAppPool -Name {_ps(name)}",
        ("active_directory", "unlock_user"): f"Unlock-ADAccount -Identity {_ps(name)}",
        ("active_directory", "enable_user"): f"Enable-ADAccount -Identity {_ps(name)}",
        ("active_directory", "disable_user"): f"Disable-ADAccount -Identity {_ps(name)} -Confirm:$false",
        ("exchange", "retry_queue"): f"Retry-Queue -Identity {_ps(name)} -Resubmit:$false",
        ("exchange", "resume_queue"): f"Resume-Queue -Identity {_ps(name)}",
        ("exchange", "restart_transport"): "Restart-Service -Name 'MSExchangeTransport' -Force",
    }
    command = commands.get((operation_type, action))
    if operation_type == "dns_record" and action == "create_a":
        command = f"Add-DnsServerResourceRecordA -Name {_ps(name)} -ZoneName {_ps(_required(a, 'secondary_value'))} -IPv4Address {_ps(_required(a, 'value'))}"
    if not command:
        raise P10CommandError("No reviewed live PowerShell renderer exists for this exact action.")
    return _cli("winrm_powershell", [command])


def _vcenter(operation_type: str, action: str, a: dict[str, Any], rollback: bool) -> dict[str, Any]:
    vm_id = _required(a, "resource_name")
    if operation_type != "vm_power" or action not in {"power_on", "power_off"}:
        raise P10CommandError("This vCenter action needs additional typed placement or hardware identifiers.")
    if rollback:
        action = "power_off" if action == "power_on" else "power_on"
    verb = "start" if action == "power_on" else "stop"
    return _rest("POST", f"/api/vcenter/vm/{vm_id}/power?action={verb}")


def _cisco(operation_type: str, action: str, a: dict[str, Any], rollback: bool) -> dict[str, Any]:
    name = _required(a, "resource_name")
    if rollback:
        inverse = {"create_vlan": "delete_vlan", "shutdown_port": "no_shutdown_port", "no_shutdown_port": "shutdown_port"}
        action = inverse.get(action, "")
        if not action:
            raise P10CommandError("This switch action needs captured prior interface state for rollback.")
    commands = ["configure terminal"]
    if action in {"create_vlan", "update_vlan", "delete_vlan"}:
        commands.append(f"no vlan {name}" if action == "delete_vlan" else f"vlan {name}")
        if action == "update_vlan": commands.append(f"name {_required(a, 'value')}")
    elif operation_type == "interface_description":
        commands += [f"interface {_interface(a)}", f"description {_required(a, 'value')}"]
    elif operation_type == "access_vlan":
        commands += [f"interface {_interface(a)}", "switchport mode access", f"switchport access vlan {_required(a, 'value')}"]
    elif operation_type == "trunk":
        verb = {"add_allowed_vlan": "add", "remove_allowed_vlan": "remove"}.get(action)
        commands += [f"interface {_interface(a)}", f"switchport trunk allowed vlan {verb} {_required(a, 'value')}" if verb else f"switchport trunk native vlan {_required(a, 'value')}"]
    elif operation_type == "port_recovery":
        commands += [f"interface {_interface(a)}", "shutdown" if action == "shutdown_port" else "no shutdown"]
    else:
        raise P10CommandError("No reviewed live Cisco renderer exists for this exact action.")
    commands += ["end"]
    return _cli("ssh_cli", commands, privilege_mode="enable")


def _fujitsu(operation_type: str, action: str, a: dict[str, Any], rollback: bool) -> dict[str, Any]:
    # The supported Fujitsu switch uses an IOS-like configuration grammar, but
    # still has its own platform gate and credential set.
    return _cisco(operation_type, action, a, rollback)


def _linux(operation_type: str, action: str, a: dict[str, Any], rollback: bool) -> dict[str, Any]:
    name = _required(a, "resource_name")
    if rollback and action not in {"install_package", "start_service"}:
        raise P10CommandError("This Linux action needs a captured package or file version for rollback.")
    if rollback:
        action = {"install_package": "remove_package", "start_service": "stop_service"}[action]
    commands = {
        ("linux_service", "start_service"): f"sudo -n systemctl start {name}",
        ("linux_service", "stop_service"): f"sudo -n systemctl stop {name}",
        ("linux_service", "restart_service"): f"sudo -n systemctl restart {name}",
        ("package", "install_package"): f"sudo -n apt-get install --yes {name}",
        ("package", "update_package"): f"sudo -n apt-get install --only-upgrade --yes {name}",
        ("package", "remove_package"): f"sudo -n apt-get remove --yes {name}",
        ("application_config", "restart_application"): f"sudo -n systemctl restart {name}",
    }
    command = commands.get((operation_type, action))
    if not command:
        raise P10CommandError("No reviewed live Linux renderer exists for this exact action.")
    return _cli("ssh_cli", [command])


def render_wire(transaction: dict[str, Any]) -> dict[str, Any]:
    """Return the exact executable envelope for one validated transaction."""
    platform = transaction["platform"]
    operation_type = transaction["operation_type"]
    action = transaction["action"]
    arguments = transaction["arguments"]
    rollback = bool(transaction["rollback"])
    renderers = {
        "fortinet_fortios": _fortigate,
        "f5_bigip": _f5,
        "cisco_fmc": _fmc,
        "windows_powershell": _windows,
        "vmware_vcenter": _vcenter,
        "cisco_switching": _cisco,
        "fujitsu_switching": _fujitsu,
        "linux_host": _linux,
    }
    renderer = renderers.get(platform)
    if renderer is None:
        raise P10CommandError("No live renderer is registered for this platform.")
    return renderer(operation_type, action, arguments, rollback)


def render_read_wire(transaction: dict[str, Any]) -> dict[str, Any]:
    """Render the exact read-only state query paired with a write transaction."""
    platform = transaction["platform"]
    operation_type = transaction["operation_type"]
    arguments = transaction["arguments"]
    name = _required(arguments, "resource_name")
    if platform == "fortinet_fortios":
        table = {"address_object": "firewall address", "address_group": "firewall addrgrp", "service_catalog": "firewall service custom",
                 "nat_objects": "firewall vip", "firewall_policy": "firewall policy", "static_route": "router static"}.get(operation_type)
        if operation_type == "sslvpn_objects": table = "vpn ssl web portal"
        if not table: raise P10CommandError("No exact FortiGate state query exists for this operation.")
        return _cli("ssh_read", [f"show {table} {name}"])
    if platform == "f5_bigip":
        kind = {"node": "ltm node", "pool_member": "ltm pool", "health_monitor": "ltm monitor http", "virtual_server": "ltm virtual",
                "profile": "ltm profile http", "irule": "ltm rule"}.get(operation_type)
        if not kind: raise P10CommandError("No exact BIG-IP state query exists for this operation.")
        return _cli("ssh_read", [f"tmsh -q -c 'list {kind} /Common/{name} all-properties'"])
    if platform == "cisco_fmc":
        endpoint = {"network_object": "networks", "object_group": "networkgroups"}.get(operation_type)
        if not endpoint: raise P10CommandError("FMC state query needs exact policy or device UUIDs.")
        return {"protocol": "https_read", "method": "GET", "path": f"/api/fmc_config/v1/domain/{{domainUUID}}/object/{endpoint}?filter=name:{name}", "body": None,
                "display": [f"GET /api/fmc_config/v1/domain/{{domainUUID}}/object/{endpoint}?filter=name:{name}"]}
    if platform == "windows_powershell":
        commands = {"windows_service": f"Get-Service -Name {_ps(name)} | Select-Object Name,Status,StartType",
                    "iis": f"Get-Website -Name {_ps(name)} | Select-Object Name,State,Bindings",
                    "active_directory": f"Get-ADObject -Identity {_ps(name)} -Properties Enabled,LockedOut",
                    "exchange": f"Get-Queue -Identity {_ps(name)} | Select-Object Identity,Status,MessageCount"}
        command = commands.get(operation_type)
        if not command: raise P10CommandError("No exact PowerShell state query exists for this operation.")
        return _cli("winrm_read", [command])
    if platform == "vmware_vcenter":
        return {"protocol": "https_read", "method": "GET", "path": f"/api/vcenter/vm/{name}/power", "body": None,
                "display": [f"GET /api/vcenter/vm/{name}/power"]}
    if platform in {"cisco_switching", "fujitsu_switching"}:
        command = f"show vlan id {name}" if operation_type == "vlan" else f"show running-config interface {_interface(arguments)}"
        return _cli("ssh_read", [command])
    if platform == "linux_host":
        if operation_type in {"linux_service", "application_config"}:
            return _cli("ssh_read", [f"systemctl show {name} --property=Id,ActiveState,SubState,UnitFileState"])
        if operation_type == "package":
            return _cli("ssh_read", [f"dpkg-query --show --showformat=${{Package}}=${{Version}} {name}"])
        raise P10CommandError("No exact Linux state query exists for this operation.")
    raise P10CommandError("No exact read-only state renderer exists for this platform.")
