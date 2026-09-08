import logging
from typing import List
from core.connectors.security.models import Incident, SeverityLevel, ThreatCategory

logger = logging.getLogger(__name__)


def attach_remediation_playbooks(incident: Incident) -> None:
    """Attaches concrete, copy-pasteable CLI commands and GUI procedures to the incident."""
    cli_commands: List[str] = []
    gui_steps: List[str] = []
    mode_b_cmd = f"remediate incident {incident.incident_id}"

    ip = incident.attacker_ip or "0.0.0.0"
    target = incident.target or "TargetObject"
    device = incident.source_device

    # 1. FortiGate Playbooks
    if "FortiGate" in device:
        if incident.category in (ThreatCategory.BRUTE_FORCE, ThreatCategory.INTRUSION, ThreatCategory.MALWARE):
            cli_commands.extend([
                f"# Immediate temporary ban (24 hours):",
                f"diagnose user ban add src-ip {ip} 86400",
                f"# Permanent Address Object & Group Block:",
                f"config firewall address",
                f"    edit \"BLOCK_{ip}\"",
                f"    set subnet {ip} 255.255.255.255",
                f"    set comment \"MNE Security Review Auto-Block\"",
                f"end",
                f"config firewall addrgrp",
                f"    edit \"G_BLACK_LIST\"",
                f"    append member \"BLOCK_{ip}\"",
                f"end"
            ])
            gui_steps.extend([
                "1. Log in to FortiGate GUI at https://172.23.70.4",
                "2. Navigate to Policy & Objects ➔ Addresses",
                f"3. Select group 'G_BLACK_LIST' and add address object for {ip}",
                "4. Check VPN ➔ SSL-VPN Monitor to terminate any active sessions for this IP"
            ])

    # 1b. FortiAnalyzer Central Analytics Playbooks
    if "FortiAnalyzer" in device:
        cli_commands.extend([
            f"# Query aggregated security logs for attacker IP across all 14 firewalls:",
            f"execute log filter srcip {ip}",
            f"execute log display",
            f"# Filter by threat category:",
            f"execute log filter category {incident.category.value.lower()}",
            f"execute log display",
        ])
        gui_steps.extend([
            "1. Log in to FortiAnalyzer Web Console at https://172.23.71.206",
            "2. Navigate to FortiView ➔ Threats ➔ Threats Map / Top Threats",
            f"3. Filter search by Attacker IP '{ip}' to inspect all impacted ministry firewalls",
            "4. Navigate to Log View ➔ Traffic / Security to export correlated event timeline",
            "5. If confirmed malicious, push address ban to affected branch firewalls via FortiGate G_BLACK_LIST"
        ])

    # 2. F5 BIG-IP Playbooks
    if "F5" in device or "BIG-IP" in device:
        if incident.category == ThreatCategory.WAF_EXPLOIT:
            cli_commands.extend([
                f"# Immediate DataGroup Network Block:",
                f"tmsh modify /sys datagroup type ip external-datagroup-blocked records add {{ {ip} {{}} }}",
                f"# Verify ASM violation details:",
                f"grep \"{ip}\" /var/log/asm | tail -n 10"
            ])
            gui_steps.extend([
                "1. Log in to F5 BIG-IP GUI at https://172.23.70.89",
                "2. Navigate to Security ➔ Application Security ➔ Policy Building ➔ Traffic Learning",
                "3. Locate the violation event for URL / target",
                "4. Click 'Enforce' to move the signature from Staging to Alarm & Block"
            ])
        elif incident.category == ThreatCategory.SYSTEM_HEALTH and "Certificate" in incident.title:
            cli_commands.extend([
                f"# List expiring certificate details:",
                f"tmsh list sys crypto cert {target}",
                f"# Renew and reload certificate:",
                f"tmsh install /sys crypto cert {target} from-local-file /var/tmp/{target}.crt"
            ])
            gui_steps.extend([
                "1. Log in to F5 GUI ➔ System ➔ Certificate Management ➔ Traffic Certificate Management",
                f"2. Select certificate '{target}' and click Renew/Import",
                "3. Update SSL Profile under Local Traffic ➔ Profiles ➔ SSL ➔ Client"
            ])

    # 3. Cisco FMC / FTD Playbooks
    if "Cisco" in device or "FMC" in device:
        cli_commands.extend([
            f"# FMC Security Intelligence Blacklist CLI verification:",
            f"show access-rule | include {ip}",
        ])
        gui_steps.extend([
            "1. Log in to Cisco FMC at https://172.23.70.77",
            "2. Navigate to Objects ➔ Object Management ➔ Security Intelligence ➔ Network Lists",
            f"3. Add {ip} to the 'Global-Block-List'",
            "4. Deploy changes to Cisco FTD (172.23.70.78)"
        ])

    # 4. Sophos Email Protection Playbooks
    if "Sophos" in device:
        gui_steps.extend([
            "1. Log in to Sophos WebConsole at https://172.23.71.39:4444",
            "2. Navigate to Email ➔ Policies & Exceptions ➔ Inbound Exceptions",
            f"3. Add sender pattern or target '{target}' to Quarantine/Blacklist",
            "4. Navigate to Email ➔ SMTP Quarantine and purge malicious message"
        ])

    # 5. Active Directory Playbooks
    if "Active Directory" in device or "AD" in device:
        if incident.category == ThreatCategory.PRIVILEGE_CHANGE:
            cli_commands.extend([
                f"# Remove user from privileged group:",
                f"Remove-ADGroupMember -Identity \"Domain Admins\" -Members \"{target}\" -Confirm:$false",
                f"# Disable compromised account pending investigation:",
                f"Disable-ADAccount -Identity \"{target}\"",
                f"# Audit recent logon events for user:",
                f"Get-WinEvent -FilterHashtable @{{LogName='Security';Id=4624;Data='{target}'}} -MaxEvents 10"
            ])
            gui_steps.extend([
                "1. Open Active Directory Users and Computers on MNE-DC1 (172.23.71.27)",
                f"2. Locate user '{target}' in Users OU and inspect 'Member Of' tab",
                "3. Remove unauthorized administrative group memberships",
                "4. Reset password and require change at next logon"
            ])
        elif incident.category == ThreatCategory.BRUTE_FORCE:
            cli_commands.extend([
                f"# Unlock account after verifying user identity:",
                f"Unlock-ADAccount -Identity \"{target}\"",
                f"# Check lockout event source:",
                f"Get-WinEvent -FilterHashtable @{{LogName='Security';Id=4740}} -MaxEvents 5"
            ])
            gui_steps.extend([
                "1. Open Active Directory Users and Computers",
                f"2. Search for user '{target}', open Properties ➔ Account",
                "3. Check 'Unlock account' box and click Apply"
            ])

    # Default fallback if no specific playbook triggered
    if not cli_commands and not gui_steps:
        cli_commands.append(f"# Investigate source {ip} on core firewall:")
        cli_commands.append(f"diagnose firewall iprope lookup {ip} 0 0 0")
        gui_steps.append(f"Review security logs for target '{target}' and source '{ip}'.")

    incident.remediation_cli = cli_commands
    incident.remediation_gui = gui_steps
    incident.remediation_mode_b_command = mode_b_cmd
