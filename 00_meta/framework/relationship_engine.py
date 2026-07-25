from typing import Dict, Any, List

class RelationshipEngine:
    """Auto-detects Wiki graph edges [[Entity]] between entities."""

    @staticmethod
    def infer_relationships(normalized: Dict[str, Any]) -> Dict[str, List[str]]:
        upstream = []
        downstream = []

        # Firewall -> Core Switch / WAF
        if normalized.get("vendor") in ["Fortinet", "Cisco"]:
            upstream.append("[[sw-cisco-core-01]]")
            downstream.append("[[f5-vip-public-98]]")

        # Virtual Machine -> ESXi Host
        if "vmware" in normalized.get("vendor", "").lower() or "esxi" in normalized.get("hostname", "").lower():
            upstream.append("[[vcenter-main]]")
            upstream.append("[[san-fujitsu-eternus-01]]")

        # Application / Exchange -> AD
        if "exch" in normalized.get("hostname", "").lower() or "ad" in normalized.get("hostname", "").lower():
            upstream.append("[[ad-dc-01]]")
            upstream.append("[[dns-zone-mne-gov-ps]]")

        return {
            "upstream_dependencies": list(set(upstream)),
            "downstream_consumers": list(set(downstream))
        }
