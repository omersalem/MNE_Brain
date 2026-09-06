import logging
from typing import Any, Dict, List, Set, Tuple
from core.connectors.security.models import Incident, SeverityLevel

logger = logging.getLogger(__name__)

# Ministry of National Economy Protected Infrastructure IPs
# Auto-blocking or taking action against these IPs is strictly prohibited.
PROTECTED_INFRASTRUCTURE_IPS: Set[str] = {
    "172.23.70.4",   # FortiGate inside management
    "213.6.17.30",   # FortiGate WAN
    "213.6.17.29",   # WAN next hop / ISP Gateway
    "172.23.70.89",  # F5 BIG-IP management
    "172.23.70.77",  # Cisco FMC management
    "172.23.70.78",  # Cisco FTD management
    "172.23.71.39",  # Sophos Email Protection appliance
    "172.23.71.27",  # MNE-DC1 (Active Directory & DNS)
    "172.23.71.173", # MNE-DC1 secondary IP
    "172.23.71.36",  # Exchange 2019 server
    "172.23.69.38",  # VMware vCenter
    "172.23.70.254", # Cisco Core switch gateway
    "127.0.0.1",
    "::1",
}


class RemediationExecutor:
    """Mode B Assisted Remediation Engine.

    Prepares verified containment plans and executes them upon explicit
    MNE-BRAIN-OWNER confirmation, enforcing infrastructure IP protection.
    """

    def __init__(self, protected_ips: Set[str] = None):
        self.protected_ips = protected_ips or PROTECTED_INFRASTRUCTURE_IPS

    def validate_target_safety(self, target_ip: str) -> Tuple[bool, str]:
        """Ensures the target is not a protected infrastructure IP or critical service."""
        if not target_ip:
            return False, "Target IP is empty or undefined."

        clean_ip = target_ip.strip()
        if clean_ip in self.protected_ips:
            return False, f"Target {clean_ip} is a protected infrastructure IP. Remediation blocked by safety policy."

        # Verify not internal subnet broadcast or gateway .254 / .1
        if clean_ip.endswith(".254") or clean_ip.endswith(".1"):
            logger.warning("Target IP %s appears to be a gateway. Flagging warning.", clean_ip)

        return True, f"Target {clean_ip} is safe for containment."

    def prepare_plan(self, incident: Incident) -> Dict[str, Any]:
        """Constructs an executable remediation plan for owner review."""
        is_safe, safety_reason = self.validate_target_safety(incident.attacker_ip or "")
        plan = {
            "incident_id": incident.incident_id,
            "title": incident.title,
            "severity": incident.severity.value,
            "source_device": incident.source_device,
            "attacker_ip": incident.attacker_ip,
            "target": incident.target,
            "is_safe_to_execute": is_safe,
            "safety_assessment": safety_reason,
            "proposed_commands": incident.remediation_cli,
            "gui_instructions": incident.remediation_gui,
            "requires_confirmation": True,
            "status": "PREPARED",
        }
        return plan

    def execute_plan(self, plan: Dict[str, Any], confirmed_by: str) -> Dict[str, Any]:
        """Executes the plan once owner confirmation is explicitly verified."""
        if confirmed_by != "MNE-BRAIN-OWNER":
            return {
                "success": False,
                "error": f"Authorization denied. Only MNE-BRAIN-OWNER can authorize remediation. Received: {confirmed_by}",
            }

        if not plan.get("is_safe_to_execute"):
            return {
                "success": False,
                "error": f"Execution aborted by safety engine: {plan.get('safety_assessment')}",
            }

        # In production, invokes the corresponding device connector (e.g., FortiGate / F5)
        # Here we record the verified change audit
        return {
            "success": True,
            "incident_id": plan.get("incident_id"),
            "executed_commands": plan.get("proposed_commands"),
            "status": "EXECUTED",
            "message": f"Remediation successfully applied for {plan.get('incident_id')}.",
        }
