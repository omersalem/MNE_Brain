"""
Local Attacker Identity Enrichment for MNE_Brain Release 2 Security Agent.

Deterministically correlates and enriches internal/local attacker IP addresses across:
- Event-native normalized log attributes (FortiGate, FortiAnalyzer UTM/VPN)
- DHCP historical and current lease records
- SCCM / MECM database and inventory records
- Reverse DNS and Active Directory computer/user objects
- FortiGate authenticated-user and VPN session mappings
"""

from __future__ import annotations

import abc
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
import hashlib
import ipaddress
import json
import logging
import re
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from core.connectors.security.models import NormalizedSecurityEvent, Incident

logger = logging.getLogger(__name__)

def coerce_datetime_utc(value: Any) -> Optional[datetime]:
    """Deterministically coerces any timestamp representation into a UTC datetime object.

    Handles:
    - None -> None
    - datetime: tz-naive is assumed UTC; tz-aware is converted to UTC
    - int/float: POSIX timestamp converted to UTC
    - str: ISO 8601 (with 'Z' or offset or naive) or common date strings
    - invalid/corrupt formats -> None (never raises exception)
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value, tz=timezone.utc)
        except (ValueError, OverflowError, OSError):
            return None
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return None
        # Replace terminal Z with +00:00 for ISO parsing
        if cleaned.endswith("Z") or cleaned.endswith("z"):
            cleaned = cleaned[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(cleaned)
            if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            pass
        # Fallback formats
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(cleaned, fmt)
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
    return None

def sanitize_secret_text(text: str) -> str:
    if not isinstance(text, str):
        return text
    sanitized = text
    # 1. Bearer tokens (with optional Bearer prefix)
    sanitized = re.sub(r"(Bearer\s+)[A-Za-z0-9_\-\.]{6,}", r"\1***REDACTED***", sanitized, flags=re.IGNORECASE)
    # 2. Key-value credentials (e.g. password=..., token=..., secret=...)
    sanitized = re.sub(
        r"(password|passwd|pwd|token|secret|api_key|apikey|authorization|credential)[=:\s]+(['\"]?)(?:Bearer\s+)?([^'\"\s&,;]+)\2",
        r"\1=***REDACTED***",
        sanitized,
        flags=re.IGNORECASE,
    )
    sanitized = re.sub(
        r"\bauth\s*=\s*(['\"]?)([^'\"\s&,;]+)\1",
        "auth=***REDACTED***",
        sanitized,
        flags=re.IGNORECASE,
    )
    return sanitized

# Default RFC1918 + IPv6 ULA for local private subnets
RFC1918_AND_LOCAL_CIDRS = [
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16",
    "fc00::/7",
]

# Documentation and benchmark networks (RFC 5737 / RFC 3849) must be classified as EXTERNAL
DOCUMENTATION_AND_TEST_CIDRS = [
    "192.0.2.0/24",     # TEST-NET-1
    "198.51.100.0/24",  # TEST-NET-2
    "203.0.113.0/24",   # TEST-NET-3
    "2001:db8::/32",    # IPv6 Documentation
]

# Loopback, link-local, multicast, and unspecified are NOT valid infrastructure targets
SPECIAL_AND_INVALID_CIDRS = [
    "127.0.0.0/8",
    "::1/128",
    "169.254.0.0/16",
    "fe80::/10",
    "224.0.0.0/4",
    "0.0.0.0/8",
]


class NetworkScope(str, Enum):
    LOCAL = "LOCAL"
    EXTERNAL = "EXTERNAL"
    INVALID = "INVALID"
    UNKNOWN = "UNKNOWN"


class IdentityStatus(str, Enum):
    RESOLVED = "RESOLVED"
    PARTIAL = "PARTIAL"
    AMBIGUOUS = "AMBIGUOUS"
    NOT_FOUND = "NOT_FOUND"
    NOT_CONFIGURED = "NOT_CONFIGURED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    FAILED = "FAILED"


class IdentityConfidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


class IncidentTimeMatch(str, Enum):
    EXACT = "EXACT"
    WITHIN_WINDOW = "WITHIN_WINDOW"
    CURRENT_ONLY = "CURRENT_ONLY"
    UNKNOWN = "UNKNOWN"


class UsernameRelation(str, Enum):
    AUTHENTICATED_SOURCE_USER = "AUTHENTICATED_SOURCE_USER"
    LOGGED_ON_ENDPOINT_USER = "LOGGED_ON_ENDPOINT_USER"
    CLAIMED_LOGIN_USERNAME = "CLAIMED_LOGIN_USERNAME"
    TARGET_ACCOUNT = "TARGET_ACCOUNT"
    PRIMARY_DEVICE_USER = "PRIMARY_DEVICE_USER"
    DEVICE_OWNER = "DEVICE_OWNER"
    UNKNOWN_RELATION = "UNKNOWN_RELATION"


@dataclass
class AttributionEvidenceSource:
    source_type: str
    source_entity_or_binding_id: str
    matched_fields: List[str] = field(default_factory=list)
    observation_time: Optional[str] = None
    event_time_distance_seconds: Optional[float] = None
    freshness: str = "CURRENT"
    evidence_reference: str = ""
    result_status: str = "SUCCESS"

    def __post_init__(self) -> None:
        if self.freshness not in ("CURRENT", "HISTORICAL", "STALE", "UNKNOWN"):
            self.freshness = "HISTORICAL" if "HISTORICAL" in str(self.freshness).upper() else "CURRENT"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AttributionCandidate:
    candidate_id: str
    pc_name: Optional[str] = None
    fqdn: Optional[str] = None
    username: Optional[str] = None
    mac_address: Optional[str] = None
    sources: List[str] = field(default_factory=list)
    confidence: str = "MEDIUM"
    confidence_score: int = 50
    rationale: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class AttackerAttribution:
    ip_address: str
    network_scope: str = "UNKNOWN"
    pc_name: str = "Unknown"
    fqdn: str = "Unknown"
    domain: str = ""
    username: str = "Unknown"
    user_display_name: str = "Unknown"
    device_owner: str = "Unknown"
    primary_device_user: str = "Unknown"
    claimed_username: str = "Unknown"
    target_account: str = "Unknown"
    mac_address: str = "Unknown"
    branch: str = ""
    status: str = "NOT_CONFIGURED"
    confidence: str = "UNKNOWN"
    confidence_score: int = 0
    confidence_rationale: str = ""
    observed_at: Optional[str] = None
    incident_time_match: str = "UNKNOWN"
    sources_queried: List[str] = field(default_factory=list)
    successful_sources: List[str] = field(default_factory=list)
    evidence_sources: List[Dict[str, Any]] = field(default_factory=list)
    candidates: List[Dict[str, Any]] = field(default_factory=list)
    attribution_history: List[Dict[str, Any]] = field(default_factory=list)
    diagnostics: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.confidence not in ("HIGH", "MEDIUM", "LOW", "UNKNOWN"):
            self.confidence = "UNKNOWN"
        try:
            self.confidence_score = int(round(float(self.confidence_score or 0)))
        except (ValueError, TypeError):
            self.confidence_score = 0
        if self.diagnostics:
            self.diagnostics = [sanitize_secret_text(d) for d in self.diagnostics]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ip_address": self.ip_address,
            "network_scope": self.network_scope,
            "pc_name": self.pc_name,
            "fqdn": self.fqdn,
            "domain": self.domain,
            "username": self.username,
            "user_display_name": self.user_display_name,
            "device_owner": self.device_owner,
            "primary_device_user": self.primary_device_user,
            "claimed_username": self.claimed_username,
            "target_account": self.target_account,
            "mac_address": self.mac_address,
            "branch": self.branch,
            "status": self.status,
            "confidence": self.confidence,
            "confidence_score": self.confidence_score,
            "confidence_rationale": self.confidence_rationale,
            "observed_at": self.observed_at,
            "incident_time_match": self.incident_time_match,
            "sources_queried": list(self.sources_queried),
            "successful_sources": list(self.successful_sources),
            "evidence_sources": list(self.evidence_sources),
            "candidates": list(self.candidates),
            "attribution_history": list(self.attribution_history),
            "diagnostics": list(self.diagnostics),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AttackerAttribution:
        return cls(
            ip_address=data.get("ip_address", ""),
            network_scope=data.get("network_scope", "UNKNOWN"),
            pc_name=data.get("pc_name", "Unknown"),
            fqdn=data.get("fqdn", "Unknown"),
            domain=data.get("domain", ""),
            username=data.get("username", "Unknown"),
            user_display_name=data.get("user_display_name", "Unknown"),
            device_owner=data.get("device_owner", "Unknown"),
            primary_device_user=data.get("primary_device_user", "Unknown"),
            claimed_username=data.get("claimed_username", "Unknown"),
            target_account=data.get("target_account", "Unknown"),
            mac_address=data.get("mac_address", "Unknown"),
            branch=data.get("branch", ""),
            status=data.get("status", "NOT_CONFIGURED"),
            confidence=data.get("confidence", "UNKNOWN"),
            confidence_score=data.get("confidence_score", 0),
            confidence_rationale=data.get("confidence_rationale", ""),
            observed_at=data.get("observed_at"),
            incident_time_match=data.get("incident_time_match", "UNKNOWN"),
            sources_queried=list(data.get("sources_queried", [])),
            successful_sources=list(data.get("successful_sources", [])),
            evidence_sources=list(data.get("evidence_sources", [])),
            candidates=list(data.get("candidates", [])),
            attribution_history=list(data.get("attribution_history", [])),
            diagnostics=list(data.get("diagnostics", [])),
        )

    def formatted_summary(self) -> str:
        if self.network_scope == NetworkScope.EXTERNAL.value:
            return (
                f"Attacker IP: {self.ip_address}\n"
                f"Network Scope: EXTERNAL\n"
                f"PC Name: Not applicable\n"
                f"Username: Not applicable\n"
                f"Identity Status: NOT_APPLICABLE"
            )
        if self.network_scope == NetworkScope.INVALID.value:
            return (
                f"Attacker IP: {self.ip_address}\n"
                f"Network Scope: INVALID\n"
                f"PC Name: Not applicable\n"
                f"Username: Not applicable\n"
                f"Identity Status: {self.status}"
            )

        sources_str = ", ".join(self.successful_sources or self.sources_queried) if (self.successful_sources or self.sources_queried) else "None"
        lines = [
            f"Attacker IP: {self.ip_address}",
            f"PC Name: {self.pc_name}",
            f"Username: {self.username}",
        ]
        if self.device_owner and self.device_owner != "Unknown" and self.device_owner != self.username:
            lines.append(f"Device Owner: {self.device_owner}")
        lines.extend([
            f"MAC Address: {self.mac_address}",
            f"Identity Sources: {sources_str}",
            f"Identity Confidence: {self.confidence}",
            f"Identity Status: {self.status}",
        ])
        if self.observed_at:
            lines.append(f"Identity Observed At: {self.observed_at}")
        if self.diagnostics:
            lines.append(f"Diagnostics: {'; '.join(self.diagnostics[:2])}")
        return "\n".join(lines)


def classify_ip(
    ip_str: str,
    local_cidrs: Optional[List[str]] = None,
    excluded_cidrs: Optional[List[str]] = None,
) -> NetworkScope:
    if not ip_str or not isinstance(ip_str, str):
        return NetworkScope.INVALID

    cleaned = ip_str.strip()
    try:
        addr = ipaddress.ip_address(cleaned)
    except ValueError:
        return NetworkScope.INVALID

    # 1. Loopback, link-local, multicast, and unspecified are INVALID
    if addr.is_loopback or addr.is_link_local or addr.is_multicast or addr.is_unspecified:
        return NetworkScope.INVALID
    for cidr in SPECIAL_AND_INVALID_CIDRS:
        try:
            if addr in ipaddress.ip_network(cidr, strict=False):
                return NetworkScope.INVALID
        except ValueError:
            continue

    # 2. RFC documentation and test ranges are EXTERNAL
    for cidr in DOCUMENTATION_AND_TEST_CIDRS:
        try:
            if addr in ipaddress.ip_network(cidr, strict=False):
                return NetworkScope.EXTERNAL
        except ValueError:
            continue

    # 3. Excluded CIDRs override to EXTERNAL
    if excluded_cidrs:
        for cidr in excluded_cidrs:
            try:
                net = ipaddress.ip_network(cidr.strip(), strict=False)
                if addr in net:
                    return NetworkScope.EXTERNAL
            except ValueError:
                continue

    # 4. Local CIDRs checking
    if local_cidrs is not None:
        # Strictly check against provided local CIDRs only; do NOT fall back to addr.is_private
        for cidr in local_cidrs:
            try:
                net = ipaddress.ip_network(cidr.strip(), strict=False)
                if addr in net:
                    return NetworkScope.LOCAL
            except ValueError:
                continue
        return NetworkScope.EXTERNAL

    # 5. Default: RFC1918 + IPv6 ULA
    for cidr in RFC1918_AND_LOCAL_CIDRS:
        try:
            net = ipaddress.ip_network(cidr.strip(), strict=False)
            if addr in net:
                return NetworkScope.LOCAL
        except ValueError:
            continue

    return NetworkScope.EXTERNAL


def compute_identity_confidence(
    status: str,
    time_match: IncidentTimeMatch,
    sources_count: int,
    is_ambiguous: bool,
    has_pc: bool,
    has_user: bool,
    has_owner: bool,
    time_decay: bool = False,
) -> Tuple[str, int]:
    """Deterministic formula calculating confidence score (0-100) and rating."""
    if status in (
        IdentityStatus.NOT_FOUND.value,
        IdentityStatus.NOT_CONFIGURED.value,
        IdentityStatus.NOT_APPLICABLE.value,
        IdentityStatus.FAILED.value,
    ):
        return (IdentityConfidence.UNKNOWN.value, 0)

    if is_ambiguous or status == IdentityStatus.AMBIGUOUS.value:
        score = 40
        if time_decay:
            score -= 10
        return (IdentityConfidence.LOW.value, max(0, min(score, 45)))

    score = 0
    if has_pc and has_user:
        score += 70
    elif has_pc and has_owner:
        score += 55
    elif has_pc:
        score += 45
    elif has_user:
        score += 40
    elif has_owner:
        score += 30

    if time_match == IncidentTimeMatch.EXACT:
        score += 20
    elif time_match == IncidentTimeMatch.WITHIN_WINDOW:
        score += 15
    elif time_match == IncidentTimeMatch.CURRENT_ONLY:
        score += 5

    if sources_count >= 3:
        score += 15
    elif sources_count >= 2:
        score += 10

    if time_decay:
        score -= 20

    score = max(5, min(score, 100))

    if score >= 80:
        rating = IdentityConfidence.HIGH.value
    elif score >= 50:
        rating = IdentityConfidence.MEDIUM.value
    elif score >= 20:
        rating = IdentityConfidence.LOW.value
    else:
        rating = IdentityConfidence.UNKNOWN.value

    return (rating, score)


def should_replace_attribution(
    current: Optional[AttackerAttribution],
    candidate: AttackerAttribution,
) -> bool:
    """Non-downgrade persistence logic.

    Ensures that a previously verified, high-quality attribution is never overwritten
    by an unconfigured, failed, missing, or stale candidate.
    """
    if current is None:
        return True

    # Do not replace with invalid/failed candidates if we had any valid state
    if candidate.status in (IdentityStatus.FAILED.value, IdentityStatus.NOT_CONFIGURED.value) and current.status not in (
        IdentityStatus.FAILED.value,
        IdentityStatus.NOT_CONFIGURED.value,
    ):
        return False

    # Fully resolved attributions must not be downgraded
    if current.status == IdentityStatus.RESOLVED.value:
        if candidate.status in (
            IdentityStatus.NOT_FOUND.value,
            IdentityStatus.NOT_CONFIGURED.value,
            IdentityStatus.FAILED.value,
            IdentityStatus.AMBIGUOUS.value,
        ):
            return False
        # Do not overwrite exact/window historical match with CURRENT_ONLY
        if candidate.incident_time_match == IncidentTimeMatch.CURRENT_ONLY.value and current.incident_time_match in (
            IncidentTimeMatch.EXACT.value,
            IncidentTimeMatch.WITHIN_WINDOW.value,
        ):
            return False
        if candidate.confidence_score < current.confidence_score - 15:
            return False
        return True

    # Partial attributions should not be overwritten by NOT_FOUND
    if current.status == IdentityStatus.PARTIAL.value:
        if candidate.status in (
            IdentityStatus.NOT_FOUND.value,
            IdentityStatus.NOT_CONFIGURED.value,
            IdentityStatus.FAILED.value,
        ):
            return False
        current_has_facts = (current.pc_name not in ("Unknown", "Not applicable")) or (
            current.username not in ("Unknown", "Not applicable")
        )
        cand_has_facts = (candidate.pc_name not in ("Unknown", "Not applicable")) or (
            candidate.username not in ("Unknown", "Not applicable")
        )
        if current_has_facts and not cand_has_facts:
            return False
        return True

    return True


@dataclass
class SourceResolutionResult:
    source_name: str
    binding_id: str = ""
    status: str = "NO_MATCH"
    pc_name: Optional[str] = None
    fqdn: Optional[str] = None
    domain: Optional[str] = None
    username: Optional[str] = None
    user_display_name: Optional[str] = None
    device_owner: Optional[str] = None
    primary_device_user: Optional[str] = None
    claimed_username: Optional[str] = None
    target_account: Optional[str] = None
    mac_address: Optional[str] = None
    observation_time: Optional[datetime] = None
    time_match: IncidentTimeMatch = IncidentTimeMatch.UNKNOWN
    confidence_weight: float = 0.0
    diagnostic: str = ""
    evidence_ref: str = ""
    matched_fields: List[str] = field(default_factory=list)


class BaseIdentitySourceAdapter(abc.ABC):
    def __init__(self, name: str, binding_id: str = ""):
        self.name = name
        self.binding_id = binding_id

    @abc.abstractmethod
    def resolve(
        self,
        ip: str,
        first_seen: Optional[datetime] = None,
        last_seen: Optional[datetime] = None,
        events: Optional[List[NormalizedSecurityEvent]] = None,
        branch: Optional[str] = None,
        timeout: float = 5.0,
        supporting_event_ids: Optional[Set[str]] = None,
        event_time_tolerance_seconds: int = 3600,
        **kwargs: Any,
    ) -> SourceResolutionResult:
        raise NotImplementedError


class EventNativeIdentityAdapter(BaseIdentitySourceAdapter):
    def __init__(self):
        super().__init__(name="Event-Native", binding_id="event-native-extractor")

    def resolve(
        self,
        ip: str,
        first_seen: Optional[datetime] = None,
        last_seen: Optional[datetime] = None,
        events: Optional[List[NormalizedSecurityEvent]] = None,
        branch: Optional[str] = None,
        timeout: float = 5.0,
        supporting_event_ids: Optional[Set[str]] = None,
        event_time_tolerance_seconds: int = 3600,
        **kwargs: Any,
    ) -> SourceResolutionResult:
        if not events:
            return SourceResolutionResult(
                source_name=self.name,
                binding_id=self.binding_id,
                status="NO_MATCH",
                diagnostic="No supporting security events available for native identity extraction.",
            )

        extracted_pcs: Set[str] = set()
        extracted_users: Set[str] = set()
        claimed_users: Set[str] = set()
        extracted_macs: Set[str] = set()
        matched_fields: Set[str] = set()
        newest_ts: Optional[datetime] = None
        has_exact_match = False
        has_window_match = False

        start_utc = coerce_datetime_utc(first_seen)
        end_utc = coerce_datetime_utc(last_seen) or start_utc

        for ev in events:
            if ev.attacker_ip != ip:
                continue

            if supporting_event_ids and ev.event_id not in supporting_event_ids:
                continue

            ev_ts = coerce_datetime_utc(ev.timestamp)
            if start_utc and end_utc and ev_ts:
                window_start = start_utc - timedelta(seconds=event_time_tolerance_seconds)
                window_end = end_utc + timedelta(seconds=event_time_tolerance_seconds)
                if ev_ts < window_start or ev_ts > window_end:
                    continue
                if start_utc <= ev_ts <= end_utc:
                    has_exact_match = True
                else:
                    has_window_match = True
            elif ev_ts:
                has_exact_match = True

            meta = ev.metadata if isinstance(ev.metadata, dict) else {}

            # Strict endpoint extraction: NEVER use devname, devid, reporting_firewall, device_name, source_device!
            candidate_pc = None
            if ev.attacker_hostname and ev.attacker_hostname.strip().lower() not in ("unknown", "none", "n/a"):
                candidate_pc = ev.attacker_hostname.strip().upper()
                matched_fields.add("attacker_hostname")
            elif ev.source_hostname and ev.source_hostname.strip().lower() not in ("unknown", "none", "n/a"):
                candidate_pc = ev.source_hostname.strip().upper()
                matched_fields.add("source_hostname")
            else:
                for k in ("srcname", "src_host", "workstation_name"):
                    v = meta.get(k)
                    if v and isinstance(v, str) and v.strip() and v.strip().lower() not in ("unknown", "none", "n/a", "perimeter"):
                        if v.strip() not in ("FortiGate", "FortiAnalyzer", "F5 BIG-IP", "Cisco FMC", "Sophos Email"):
                            candidate_pc = v.strip().upper()
                            matched_fields.add(k)
                            break
                # Generic FortiGate/FortiAnalyzer ``hostname`` commonly names a
                # web destination.  It is an endpoint only when the collector
                # explicitly labels its role.
                if not candidate_pc and "hostname" in meta:
                    h_val = str(meta["hostname"]).strip()
                    role = meta.get("hostname_role")
                    if role == "SOURCE_ENDPOINT":
                        if h_val.lower() not in ("unknown", "none", "n/a") and h_val not in ("FortiGate", "FortiAnalyzer", "F5 BIG-IP", "Cisco FMC"):
                            candidate_pc = h_val.upper()
                            matched_fields.add("hostname")

            if candidate_pc:
                extracted_pcs.add(candidate_pc)

            # User extraction: distinguish authenticated/active vs claimed/unauth
            if ev.authenticated_source_user and ev.authenticated_source_user.strip().lower() not in ("unknown", "none", "n/a"):
                extracted_users.add(ev.authenticated_source_user.strip())
                matched_fields.add("authenticated_source_user")
            elif meta.get("authuser") and str(meta["authuser"]).strip().lower() not in ("unknown", "none", "n/a"):
                extracted_users.add(str(meta["authuser"]).strip())
                matched_fields.add("authuser")
            elif meta.get("username_relation") == "AUTHENTICATED_SOURCE_USER" and (meta.get("user") or meta.get("srcuser")):
                u = str(meta.get("user") or meta.get("srcuser")).strip()
                if u.lower() not in ("unknown", "none", "n/a"):
                    extracted_users.add(u)
                    matched_fields.add("user")
            elif getattr(ev, "claimed_login_username", None) and ev.claimed_login_username.strip().lower() not in ("unknown", "none", "n/a"):
                claimed_users.add(ev.claimed_login_username.strip())
                matched_fields.add("claimed_login_username")
            elif meta.get("unauthuser") and str(meta["unauthuser"]).strip().lower() not in ("unknown", "none", "n/a"):
                claimed_users.add(str(meta["unauthuser"]).strip())
                matched_fields.add("unauthuser")
            elif (meta.get("username_relation") == "CLAIMED_LOGIN_USERNAME" or meta.get("subtype") == "vpn") and (meta.get("user") or meta.get("srcuser")):
                u = str(meta.get("user") or meta.get("srcuser")).strip()
                if u.lower() not in ("unknown", "none", "n/a"):
                    claimed_users.add(u)
                    matched_fields.add("claimed_user")
            elif meta.get("user") or meta.get("srcuser"):
                # A generic user field is not sufficient to prove that the
                # account belongs to the source endpoint.  Collectors must set
                # username_relation or one of the explicit normalized fields.
                matched_fields.add("unclassified_user_ignored")

            # MAC address extraction
            if ev.attacker_mac and ev.attacker_mac.strip().lower() not in ("unknown", "none", "00:00:00:00:00:00"):
                extracted_macs.add(ev.attacker_mac.strip().upper().replace(":", "-"))
                matched_fields.add("attacker_mac")
            else:
                for k in ("srcmac", "mac", "client_mac"):
                    v = meta.get(k)
                    if v and isinstance(v, str) and v.strip() and v.strip().lower() not in ("unknown", "none", "00:00:00:00:00:00"):
                        extracted_macs.add(v.strip().upper().replace(":", "-"))
                        matched_fields.add(k)

            if ev_ts:
                if newest_ts is None or ev_ts > newest_ts:
                    newest_ts = ev_ts

        if not extracted_pcs and not extracted_users and not claimed_users and not extracted_macs:
            return SourceResolutionResult(
                source_name=self.name,
                binding_id=self.binding_id,
                status="NO_MATCH",
                diagnostic="No native computer name, username, or MAC address found in event telemetry.",
            )

        pc_name = list(extracted_pcs)[0] if len(extracted_pcs) == 1 else (None if len(extracted_pcs) > 1 else None)
        username = list(extracted_users)[0] if len(extracted_users) == 1 else (None if len(extracted_users) > 1 else None)
        claimed_user = list(claimed_users)[0] if len(claimed_users) == 1 else (None if len(claimed_users) > 1 else None)
        mac_addr = list(extracted_macs)[0] if len(extracted_macs) == 1 else (None if len(extracted_macs) > 1 else None)

        status_val = "SUCCESS"
        diag = "Extracted identity from security event payload."
        if len(extracted_pcs) > 1 or len(extracted_users) > 1:
            status_val = "AMBIGUOUS"
            diag = f"Multiple conflicting native values found (PCs: {sorted(list(extracted_pcs))}, Users: {sorted(list(extracted_users))})."

        if has_exact_match:
            time_match = IncidentTimeMatch.EXACT
        elif has_window_match:
            time_match = IncidentTimeMatch.WITHIN_WINDOW
        else:
            time_match = IncidentTimeMatch.CURRENT_ONLY

        return SourceResolutionResult(
            source_name=self.name,
            binding_id=self.binding_id,
            status=status_val,
            pc_name=pc_name,
            username=username,
            claimed_username=claimed_user,
            mac_address=mac_addr,
            observation_time=newest_ts or datetime.now(timezone.utc),
            time_match=time_match,
            confidence_weight=0.90 if status_val == "SUCCESS" else 0.50,
            diagnostic=diag,
            evidence_ref="event-metadata",
            matched_fields=sorted(list(matched_fields)),
        )


class DhcpIdentityAdapter(BaseIdentitySourceAdapter):
    def __init__(
        self,
        dhcp_provider: Optional[Callable[..., Any]] = None,
        lease_history_provider: Optional[Callable[..., Any]] = None,
        binding_id: str = "p7-dhcp-primary",
    ):
        super().__init__(name="DHCP", binding_id=binding_id)
        self.dhcp_provider = dhcp_provider or lease_history_provider

    def resolve(
        self,
        ip: str,
        first_seen: Optional[datetime] = None,
        last_seen: Optional[datetime] = None,
        events: Optional[List[NormalizedSecurityEvent]] = None,
        branch: Optional[str] = None,
        timeout: float = 5.0,
        **kwargs: Any,
    ) -> SourceResolutionResult:
        if self.dhcp_provider is None:
            return SourceResolutionResult(
                source_name=self.name,
                binding_id=self.binding_id,
                status="NOT_CONFIGURED",
                diagnostic="DHCP source not configured; event-time IP ownership could not be checked.",
            )

        ref_time = coerce_datetime_utc(last_seen) or coerce_datetime_utc(first_seen) or datetime.now(timezone.utc)
        try:
            try:
                record = self.dhcp_provider(ip, ref_time)
            except TypeError:
                record = self.dhcp_provider(ip)
        except Exception as exc:
            return SourceResolutionResult(
                source_name=self.name,
                binding_id=self.binding_id,
                status="FAILED",
                diagnostic=f"DHCP query failed: {exc}",
            )

        if not record:
            return SourceResolutionResult(
                source_name=self.name,
                binding_id=self.binding_id,
                status="NO_MATCH",
                diagnostic=f"No DHCP lease record found for {ip}.",
            )

        tolerance_sec = int(kwargs.get("event_time_tolerance_seconds", 3600))

        def _evaluate_lease_match(lease_entry: Dict[str, Any]) -> Tuple[IncidentTimeMatch, float, str]:
            start = coerce_datetime_utc(lease_entry.get("lease_start") or lease_entry.get("start_time"))
            end = coerce_datetime_utc(lease_entry.get("lease_end") or lease_entry.get("end_time"))
            if start and end and start <= ref_time <= end:
                return (IncidentTimeMatch.EXACT, 0.90, "Historical DHCP lease matched incident timeframe exactly.")
            if start and start <= ref_time and (not end or ref_time <= end):
                return (IncidentTimeMatch.EXACT, 0.90, "Historical DHCP lease covered incident time without expiration.")
            if start or end:
                ref_ts = ref_time.timestamp()
                s_dist = abs(ref_ts - start.timestamp()) if start else float("inf")
                e_dist = abs(ref_ts - end.timestamp()) if end else float("inf")
                if min(s_dist, e_dist) <= tolerance_sec:
                    return (IncidentTimeMatch.WITHIN_WINDOW, 0.80, f"DHCP lease within {tolerance_sec}s tolerance window of incident.")
                else:
                    return (IncidentTimeMatch.CURRENT_ONLY, 0.35, "DHCP lease outside incident timeframe; historical lease decayed.")
            if lease_entry.get("current_only"):
                return (IncidentTimeMatch.CURRENT_ONLY, 0.35, "Current DHCP lease returned without historical timestamps.")
            return (IncidentTimeMatch.UNKNOWN, 0.40, "DHCP lease record without timestamp bounds; reduced confidence.")

        time_match = IncidentTimeMatch.UNKNOWN
        weight = 0.40
        diag = "DHCP lease record matched IP."

        if isinstance(record, list):
            matched_lease = None
            best_match = (IncidentTimeMatch.UNKNOWN, 0.0, "")
            for l in record:
                tm, wt, dg = _evaluate_lease_match(l)
                if tm == IncidentTimeMatch.EXACT:
                    matched_lease = l
                    best_match = (tm, wt, dg)
                    break
                elif tm == IncidentTimeMatch.WITHIN_WINDOW and best_match[0] != IncidentTimeMatch.EXACT:
                    matched_lease = l
                    best_match = (tm, wt, dg)
                elif matched_lease is None:
                    matched_lease = l
                    best_match = (tm, wt, dg)
            if not matched_lease and record:
                matched_lease = record[-1]
                best_match = _evaluate_lease_match(matched_lease)
            record = matched_lease
            time_match, weight, diag = best_match
        elif isinstance(record, dict):
            time_match, weight, diag = _evaluate_lease_match(record)

        if not record:
            return SourceResolutionResult(
                source_name=self.name,
                binding_id=self.binding_id,
                status="NO_MATCH",
                diagnostic=f"No DHCP lease record found for {ip}.",
            )

        pc_name = record.get("hostname") or record.get("client_name")
        mac = record.get("mac_address") or record.get("mac") or record.get("client_id")

        return SourceResolutionResult(
            source_name=self.name,
            binding_id=self.binding_id,
            status="SUCCESS",
            pc_name=pc_name.upper() if pc_name else None,
            mac_address=mac.upper().replace(":", "-") if mac else None,
            observation_time=ref_time,
            time_match=time_match,
            confidence_weight=weight,
            diagnostic=diag,
            evidence_ref=f"dhcp-lease-{ip}",
            matched_fields=["leased_ip", "hostname", "mac_address"],
        )


class SccmIdentityAdapter(BaseIdentitySourceAdapter):
    def __init__(
        self,
        sccm_provider: Optional[Callable[[str], Optional[Dict[str, Any]]]] = None,
        query_executor: Optional[Callable[[str], Optional[Dict[str, Any]]]] = None,
        binding_id: str = "p7-sccm-sql",
    ):
        super().__init__(name="SCCM", binding_id=binding_id)
        self.sccm_provider = sccm_provider or query_executor

    def resolve(
        self,
        ip: str,
        first_seen: Optional[datetime] = None,
        last_seen: Optional[datetime] = None,
        events: Optional[List[NormalizedSecurityEvent]] = None,
        branch: Optional[str] = None,
        timeout: float = 5.0,
        **kwargs: Any,
    ) -> SourceResolutionResult:
        if self.sccm_provider is None:
            return SourceResolutionResult(
                source_name=self.name,
                binding_id=self.binding_id,
                status="NOT_CONFIGURED",
                diagnostic="SCCM database source not configured; host and primary-user inventory could not be checked.",
            )

        try:
            record = self.sccm_provider(ip)
        except Exception as exc:
            return SourceResolutionResult(
                source_name=self.name,
                binding_id=self.binding_id,
                status="FAILED",
                diagnostic=f"SCCM query failed: {exc}",
            )

        if not record:
            return SourceResolutionResult(
                source_name=self.name,
                binding_id=self.binding_id,
                status="NO_MATCH",
                diagnostic=f"No SCCM hardware/client inventory record found matching IP {ip}.",
            )

        pc_name = record.get("netbios_name") or record.get("computer_name") or record.get("Netbios_Name0") or record.get("ResourceNames")
        fqdn = record.get("fqdn") or record.get("Full_Domain_Name0")
        domain = record.get("domain") or record.get("Resource_Domain_OR_Workgr0")
        mac = record.get("mac_address") or record.get("MAC_Addresses0")
        primary_user = record.get("primary_user") or record.get("last_console_user") or record.get("User_Name0") or record.get("LastConsoleUser")
        ref_time = coerce_datetime_utc(last_seen) or coerce_datetime_utc(first_seen) or datetime.now(timezone.utc)
        max_age_hours = float(kwargs.get("current_record_max_age_hours", 24))

        is_stale = bool(record.get("is_stale", False))
        inv_time: Optional[datetime] = None
        for ts_key in ("last_active", "last_inventory", "LastHWScan", "client_activity_timestamp", "LastActiveTime", "LastPolicyRequest"):
            v = record.get(ts_key)
            if v:
                ts_dt = coerce_datetime_utc(v)
                if ts_dt:
                    inv_time = ts_dt
                    age_h = (ref_time - ts_dt).total_seconds() / 3600.0
                    if age_h > max_age_hours:
                        is_stale = True
                    break

        weight = 0.80 if not is_stale else 0.40
        diag = "SCCM hardware inventory record matched IP."
        if is_stale:
            diag = f"SCCM returned record, but its inventory timestamp is older than the configured freshness limit ({max_age_hours}h)."

        return SourceResolutionResult(
            source_name=self.name,
            binding_id=self.binding_id,
            status="SUCCESS" if not is_stale else "STALE_RESULT",
            pc_name=pc_name.upper() if pc_name else None,
            fqdn=fqdn,
            domain=domain,
            device_owner=primary_user,  # Kept strictly separate from attacker_username!
            primary_device_user=primary_user,
            mac_address=mac.upper().replace(":", "-") if mac else None,
            observation_time=inv_time or ref_time,
            time_match=IncidentTimeMatch.WITHIN_WINDOW if not is_stale else IncidentTimeMatch.CURRENT_ONLY,
            confidence_weight=weight,
            diagnostic=diag,
            evidence_ref=f"sccm-res-{record.get('resource_id', 'unknown')}",
            matched_fields=["IP_Addresses0", "Netbios_Name0", "MAC_Addresses0"],
        )


class DnsActiveDirectoryAdapter(BaseIdentitySourceAdapter):
    def __init__(
        self,
        ad_provider: Optional[Callable[[str], Optional[Dict[str, Any]]]] = None,
        dns_provider: Optional[Callable[[str], Optional[str]]] = None,
        binding_id: str = "p7-ad-primary",
    ):
        super().__init__(name="DNS/AD", binding_id=binding_id)
        self.ad_provider = ad_provider
        self.dns_provider = dns_provider

    def resolve(
        self,
        ip: str,
        first_seen: Optional[datetime] = None,
        last_seen: Optional[datetime] = None,
        events: Optional[List[NormalizedSecurityEvent]] = None,
        branch: Optional[str] = None,
        timeout: float = 5.0,
        **kwargs: Any,
    ) -> SourceResolutionResult:
        if self.dns_provider is None and self.ad_provider is None:
            return SourceResolutionResult(
                source_name=self.name,
                binding_id=self.binding_id,
                status="NOT_CONFIGURED",
                diagnostic="DNS/Active Directory source not configured; reverse DNS computer lookup could not be executed.",
            )

        resolved_host = None
        fqdn = None

        if self.dns_provider is not None:
            try:
                host = self.dns_provider(ip)
                if host:
                    resolved_host = host.split(".")[0].upper()
                    fqdn = host.lower()
            except Exception as exc:
                logger.debug("DNS lookup failed for %s: %s", ip, exc)
                resolved_host = None

        if self.ad_provider is not None and resolved_host:
            try:
                ad_record = self.ad_provider(resolved_host)
                if ad_record:
                    fqdn = ad_record.get("fqdn") or fqdn
                    domain = ad_record.get("domain", "mne.local")
                    return SourceResolutionResult(
                        source_name=self.name,
                        binding_id=self.binding_id,
                        status="SUCCESS",
                        pc_name=resolved_host,
                        fqdn=fqdn,
                        domain=domain,
                        username=None,  # AD computer record proves device, NOT user!
                        observation_time=datetime.now(timezone.utc),
                        time_match=IncidentTimeMatch.CURRENT_ONLY,
                        confidence_weight=0.60,
                        diagnostic="Reverse DNS and Active Directory confirmed computer object; username remains Unknown.",
                        evidence_ref=f"ad-computer-{resolved_host}",
                        matched_fields=["dNSHostName", "sAMAccountName"],
                    )
            except Exception as exc:
                logger.debug("AD computer lookup failed for %s: %s", resolved_host, exc)

        if resolved_host:
            return SourceResolutionResult(
                source_name=self.name,
                binding_id=self.binding_id,
                status="PARTIAL",
                pc_name=resolved_host,
                fqdn=fqdn,
                username=None,
                observation_time=datetime.now(timezone.utc),
                time_match=IncidentTimeMatch.CURRENT_ONLY,
                confidence_weight=0.45,
                diagnostic="DNS reverse lookup returned hostname; AD directory verification was not available.",
                evidence_ref=f"dns-ptr-{ip}",
                matched_fields=["PTR"],
            )

        return SourceResolutionResult(
            source_name=self.name,
            binding_id=self.binding_id,
            status="NO_MATCH",
            diagnostic="DNS PTR lookup and Active Directory returned no computer record for this IP.",
        )


class FortiGateAuthAdapter(BaseIdentitySourceAdapter):
    def __init__(self, auth_provider: Optional[Callable[[str, Optional[datetime]], Optional[Dict[str, Any]]]] = None, binding_id: str = "p7-fortigate-edge"):
        super().__init__(name="FortiGate-Auth", binding_id=binding_id)
        self.auth_provider = auth_provider

    def resolve(
        self,
        ip: str,
        first_seen: Optional[datetime] = None,
        last_seen: Optional[datetime] = None,
        events: Optional[List[NormalizedSecurityEvent]] = None,
        branch: Optional[str] = None,
        timeout: float = 5.0,
        **kwargs: Any,
    ) -> SourceResolutionResult:
        if self.auth_provider is None:
            return SourceResolutionResult(
                source_name=self.name,
                binding_id=self.binding_id,
                status="NOT_CONFIGURED",
                diagnostic="FortiGate authenticated-user mapping provider is not configured.",
            )


        ref_time = last_seen or first_seen or datetime.now(timezone.utc)
        try:
            record = self.auth_provider(ip, ref_time)
        except Exception as exc:
            return SourceResolutionResult(
                source_name=self.name,
                binding_id=self.binding_id,
                status="FAILED",
                diagnostic=f"FortiGate auth session lookup failed: {exc}",
            )

        if not record:
            return SourceResolutionResult(
                source_name=self.name,
                binding_id=self.binding_id,
                status="NO_MATCH",
                diagnostic=f"No authenticated user or VPN session found for IP {ip} at incident time.",
            )

        user = record.get("username")
        pc = record.get("hostname")

        return SourceResolutionResult(
            source_name=self.name,
            binding_id=self.binding_id,
            status="SUCCESS",
            pc_name=pc.upper() if pc else None,
            username=user,
            observation_time=ref_time,
            time_match=IncidentTimeMatch.EXACT,
            confidence_weight=0.85,
            diagnostic="Matched active FortiGate authenticated session or VPN lease.",
            evidence_ref=f"fgt-auth-{ip}",
            matched_fields=["authuser", "srcip"],
        )

class LocalAttackerIdentityResolver:
    """Deterministic orchestrator for local attacker identity enrichment."""

    def __init__(
        self,
        adapters: Optional[List[BaseIdentitySourceAdapter]] = None,
        local_cidrs: Optional[List[str]] = None,
        excluded_cidrs: Optional[List[str]] = None,
        per_source_timeout: float = 5.0,
        overall_timeout: float = 15.0,
        cache_enabled: bool = True,
        source_priority: Optional[List[str]] = None,
        enabled_sources: Optional[List[str]] = None,
        per_source_timeout_seconds: Optional[float] = None,
        overall_timeout_seconds: Optional[float] = None,
        event_time_tolerance_seconds: int = 3600,
        current_record_max_age_hours: int = 24,
        max_candidates: int = 5,
        enable_cache: Optional[bool] = None,
    ):
        base_adapters = adapters or [
            EventNativeIdentityAdapter(),
            DhcpIdentityAdapter(),
            SccmIdentityAdapter(),
            DnsActiveDirectoryAdapter(),
            FortiGateAuthAdapter(),
        ]

        adapter_type_map = {
            "event_native": "Event-Native",
            "fortianalyzer": "FortiAnalyzer",
            "dhcp": "DHCP",
            "sccm": "SCCM",
            "dns_ad": "DNS/AD",
            "fortigate_auth": "FortiGate-Auth",
        }
        name_to_key = {v.lower(): k for k, v in adapter_type_map.items()}

        if enabled_sources is not None:
            enabled_set = {s.lower().replace("-", "_") for s in enabled_sources}
            base_adapters = [a for a in base_adapters if a.name.lower().replace("-", "_") in enabled_set or name_to_key.get(a.name.lower()) in enabled_set]

        if source_priority is not None:
            priority_order = [s.lower().replace("-", "_") for s in source_priority]
            def _prio(a):
                k = name_to_key.get(a.name.lower(), a.name.lower().replace("-", "_"))
                return priority_order.index(k) if k in priority_order else 999
            base_adapters = sorted(base_adapters, key=_prio)

        self.adapters = base_adapters
        self.local_cidrs = local_cidrs
        self.excluded_cidrs = excluded_cidrs
        self.per_source_timeout = per_source_timeout_seconds if per_source_timeout_seconds is not None else per_source_timeout
        self.overall_timeout = overall_timeout_seconds if overall_timeout_seconds is not None else overall_timeout
        self.cache_enabled = enable_cache if enable_cache is not None else cache_enabled
        self.event_time_tolerance_seconds = event_time_tolerance_seconds
        self.current_record_max_age_hours = current_record_max_age_hours
        self.max_candidates = max_candidates
        self._cache: Dict[Tuple[str, str, str, str], AttackerAttribution] = {}

    def _make_cache_key(
        self,
        ip: str,
        incident_time: Optional[datetime],
        branch: Optional[str],
        events: Optional[List[NormalizedSecurityEvent]] = None,
        supporting_event_ids: Optional[Set[str]] = None,
    ) -> Tuple[str, str, str, str]:
        ts = incident_time or datetime.now(timezone.utc)
        hour_bucket = ts.strftime("%Y%m%d%H")
        support = set(supporting_event_ids or [])
        evidence = []
        for event in events or []:
            if event.attacker_ip != ip or (support and event.event_id not in support):
                continue
            evidence.append({
                "event_id": event.event_id,
                "timestamp": coerce_datetime_utc(event.timestamp).isoformat() if coerce_datetime_utc(event.timestamp) else str(event.timestamp),
                "attacker_hostname": event.attacker_hostname,
                "source_hostname": event.source_hostname,
                "attacker_mac": event.attacker_mac,
                "authenticated_source_user": event.authenticated_source_user,
                "logged_on_endpoint_user": event.logged_on_endpoint_user,
                "claimed_login_username": event.claimed_login_username,
                "target_account": event.target_account,
                "username_relation": event.username_relation,
            })
        evidence.sort(key=lambda item: (str(item["event_id"]), str(item["timestamp"])))
        evidence_digest = hashlib.sha256(
            json.dumps(evidence, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        ).hexdigest()
        return (ip.strip(), hour_bucket, (branch or "core").strip().lower(), evidence_digest)

    def resolve_attacker_identity(
        self,
        ip_address: Optional[str],
        first_seen: Optional[datetime] = None,
        last_seen: Optional[datetime] = None,
        events: Optional[List[NormalizedSecurityEvent]] = None,
        branch: Optional[str] = None,
        device_name: Optional[str] = None,
        supporting_event_ids: Optional[Set[str]] = None,
    ) -> AttackerAttribution:
        if not ip_address or not isinstance(ip_address, str) or not ip_address.strip():
            return AttackerAttribution(
                ip_address="",
                network_scope=NetworkScope.INVALID.value,
                pc_name="Not applicable",
                username="Not applicable",
                status=IdentityStatus.FAILED.value,
                confidence=IdentityConfidence.UNKNOWN.value,
                confidence_score=0,
                diagnostics=["No valid IP address provided for identity resolution."],
            )

        clean_ip = ip_address.strip()
        scope = classify_ip(clean_ip, self.local_cidrs, self.excluded_cidrs)

        # 1. Invalid IP
        if scope == NetworkScope.INVALID:
            return AttackerAttribution(
                ip_address=clean_ip,
                network_scope=NetworkScope.INVALID.value,
                pc_name="Not applicable",
                username="Not applicable",
                status=IdentityStatus.FAILED.value,
                confidence=IdentityConfidence.UNKNOWN.value,
                confidence_score=0,
                diagnostics=["Malformed or invalid IP address; identity lookup skipped."],
            )

        # 2. External IP
        if scope == NetworkScope.EXTERNAL:
            return AttackerAttribution(
                ip_address=clean_ip,
                network_scope=NetworkScope.EXTERNAL.value,
                pc_name="Not applicable",
                username="Not applicable",
                status=IdentityStatus.NOT_APPLICABLE.value,
                confidence=IdentityConfidence.UNKNOWN.value,
                confidence_score=0,
                diagnostics=["External public IP address; internal computer and username discovery skipped."],
            )

        # 3. Check Cache
        ref_time = coerce_datetime_utc(last_seen) or coerce_datetime_utc(first_seen) or datetime.now(timezone.utc)
        cache_key = self._make_cache_key(clean_ip, ref_time, branch, events, supporting_event_ids)
        if self.cache_enabled and cache_key in self._cache:
            return self._cache[cache_key]

        # 4. Dispatch Adapters sequentially with monotonic timeout enforcement
        sources_queried: List[str] = []
        evidence_sources: List[Dict[str, Any]] = []
        candidates_map: Dict[str, Dict[str, Any]] = {}
        diagnostics: List[str] = []

        discovered_pcs: Dict[str, List[str]] = {}
        discovered_users: Dict[str, List[str]] = {}
        claimed_users: Dict[str, List[str]] = {}
        discovered_macs: Dict[str, List[str]] = {}
        device_owners: Dict[str, List[str]] = {}
        primary_users: Dict[str, List[str]] = {}
        fqdn_val = "Unknown"
        domain_val = ""
        observed_at_str = ref_time.isoformat()
        primary_time_match = IncidentTimeMatch.UNKNOWN
        has_time_decay = False

        deadline = time.monotonic() + self.overall_timeout

        source_results: List[SourceResolutionResult] = []

        for adapter in self.adapters:
            sources_queried.append(adapter.name)
            now_mono = time.monotonic()
            remaining_time = deadline - now_mono

            if remaining_time <= 0:
                res = SourceResolutionResult(
                    source_name=adapter.name,
                    binding_id=adapter.binding_id,
                    status="SKIPPED_DEADLINE",
                    diagnostic="Skipped because overall resolution timeout reached.",
                )
            else:
                call_timeout = min(self.per_source_timeout, remaining_time)
                res_box: List[SourceResolutionResult] = []
                err_box: List[Exception] = []
                cancel_event = threading.Event()

                def _run_adapter():
                    try:
                        r = adapter.resolve(
                            ip=clean_ip,
                            first_seen=first_seen,
                            last_seen=last_seen,
                            events=events,
                            branch=branch,
                            timeout=call_timeout,
                            cancel_event=cancel_event,
                            supporting_event_ids=supporting_event_ids,
                            event_time_tolerance_seconds=self.event_time_tolerance_seconds,
                            current_record_max_age_hours=self.current_record_max_age_hours,
                        )
                        if not cancel_event.is_set():
                            res_box.append(r)
                    except Exception as exc:
                        if not cancel_event.is_set():
                            err_box.append(exc)

                th = threading.Thread(target=_run_adapter, daemon=True)
                th.start()
                th.join(timeout=max(0.001, call_timeout))
                if th.is_alive():
                    cancel_event.set()
                    res = SourceResolutionResult(
                        source_name=adapter.name,
                        binding_id=adapter.binding_id,
                        status="QUERY_TIMEOUT",
                        diagnostic=f"Adapter timed out after {call_timeout:.2f}s.",
                    )
                elif err_box:
                    exc = err_box[0]
                    logger.error("Adapter %s threw exception: %s", adapter.name, exc, exc_info=True)
                    res = SourceResolutionResult(
                        source_name=adapter.name,
                        binding_id=adapter.binding_id,
                        status="FAILED",
                        diagnostic=f"Adapter encountered unexpected error: {exc}",
                    )
                elif res_box:
                    res = res_box[0]
                else:
                    res = SourceResolutionResult(
                        source_name=adapter.name,
                        binding_id=adapter.binding_id,
                        status="NO_MATCH",
                        diagnostic="Adapter returned no result.",
                    )

            source_results.append(res)
            ev_source = AttributionEvidenceSource(
                source_type=res.source_name,
                source_entity_or_binding_id=res.binding_id,
                matched_fields=res.matched_fields,
                observation_time=res.observation_time.isoformat() if res.observation_time else None,
                freshness="CURRENT" if res.time_match != IncidentTimeMatch.CURRENT_ONLY else "HISTORICAL",
                evidence_reference=res.evidence_ref,
                result_status=res.status,
            )
            evidence_sources.append(ev_source.to_dict())

            if res.diagnostic:
                diagnostics.append(f"{res.source_name}: {res.diagnostic}")

            if res.status in ("SUCCESS", "PARTIAL", "STALE_RESULT"):
                if res.claimed_username:
                    claimed_users.setdefault(res.claimed_username, []).append(res.source_name)
                if res.mac_address:
                    discovered_macs.setdefault(res.mac_address.upper(), []).append(res.source_name)
                if res.device_owner:
                    device_owners.setdefault(res.device_owner, []).append(res.source_name)
                if res.primary_device_user:
                    primary_users.setdefault(res.primary_device_user, []).append(res.source_name)
                if res.fqdn and fqdn_val == "Unknown":
                    fqdn_val = res.fqdn
                if res.domain and not domain_val:
                    domain_val = res.domain
                if res.time_match in (IncidentTimeMatch.EXACT, IncidentTimeMatch.WITHIN_WINDOW):
                    primary_time_match = res.time_match
                elif res.time_match == IncidentTimeMatch.CURRENT_ONLY:
                    if primary_time_match == IncidentTimeMatch.UNKNOWN:
                        primary_time_match = res.time_match
                    has_time_decay = True

        # 5. Candidate Conflict & Ambiguity Resolution
        pc_cand_info: Dict[str, Dict[str, Any]] = {}
        user_cand_info: Dict[str, Dict[str, Any]] = {}

        for res in source_results:
            if res.status in ("SUCCESS", "PARTIAL", "STALE_RESULT"):
                if res.pc_name:
                    pc = res.pc_name.upper().strip()
                    if pc not in pc_cand_info:
                        pc_cand_info[pc] = {"scores": [], "sources": [], "time_matches": []}
                    pc_cand_info[pc]["sources"].append(res.source_name)
                    base = res.confidence_weight * 100.0
                    if res.time_match == IncidentTimeMatch.EXACT:
                        base += 20.0
                    elif res.time_match == IncidentTimeMatch.WITHIN_WINDOW:
                        base += 10.0
                    elif res.time_match == IncidentTimeMatch.CURRENT_ONLY:
                        base -= 15.0
                    pc_cand_info[pc]["scores"].append(base)
                    pc_cand_info[pc]["time_matches"].append(res.time_match)

                if res.username:
                    u = res.username.strip()
                    if u not in user_cand_info:
                        user_cand_info[u] = {"scores": [], "sources": [], "time_matches": []}
                    user_cand_info[u]["sources"].append(res.source_name)
                    base = res.confidence_weight * 100.0
                    if res.time_match == IncidentTimeMatch.EXACT:
                        base += 20.0
                    elif res.time_match == IncidentTimeMatch.WITHIN_WINDOW:
                        base += 10.0
                    elif res.time_match == IncidentTimeMatch.CURRENT_ONLY:
                        base -= 15.0
                    user_cand_info[u]["scores"].append(base)
                    user_cand_info[u]["time_matches"].append(res.time_match)

        pc_scores: Dict[str, float] = {}
        for pc, info in pc_cand_info.items():
            base_max = max(info["scores"])
            corrob = 15.0 * (len(set(info["sources"])) - 1)
            pc_scores[pc] = max(0.0, min(100.0, base_max + corrob))

        user_scores: Dict[str, float] = {}
        for u, info in user_cand_info.items():
            base_max = max(info["scores"])
            corrob = 15.0 * (len(set(info["sources"])) - 1)
            user_scores[u] = max(0.0, min(100.0, base_max + corrob))

        is_ambiguous_pc = False
        resolved_pc = "Unknown"
        if len(pc_scores) == 1:
            resolved_pc = list(pc_scores.keys())[0]
        elif len(pc_scores) > 1:
            sorted_pcs = sorted(pc_scores.items(), key=lambda x: x[1], reverse=True)
            top_pc, top_score = sorted_pcs[0]
            sec_pc, sec_score = sorted_pcs[1]
            if (top_score - sec_score) >= 25.0:
                resolved_pc = top_pc
                diagnostics.append(
                    f"Computer identity {top_pc} selected (score {top_score:.0f}) over {sec_pc} (score {sec_score:.0f}) by clear score delta >= 25."
                )
            else:
                is_ambiguous_pc = True
                diagnostics.append(
                    f"Conflicting computer identities {top_pc} (score {top_score:.0f}) vs {sec_pc} (score {sec_score:.0f}) within ambiguity margin (< 25); marked AMBIGUOUS."
                )

        is_ambiguous_user = False
        resolved_user = "Unknown"
        if len(user_scores) == 1:
            resolved_user = list(user_scores.keys())[0]
        elif len(user_scores) > 1:
            sorted_users = sorted(user_scores.items(), key=lambda x: x[1], reverse=True)
            top_user, top_score = sorted_users[0]
            sec_user, sec_score = sorted_users[1]
            if (top_score - sec_score) >= 25.0:
                resolved_user = top_user
                diagnostics.append(
                    f"Username {top_user} selected (score {top_score:.0f}) over {sec_user} (score {sec_score:.0f}) by clear score delta >= 25."
                )
            else:
                is_ambiguous_user = True
                diagnostics.append(
                    f"Conflicting active usernames {top_user} (score {top_score:.0f}) vs {sec_user} (score {sec_score:.0f}) within ambiguity margin (< 25); marked AMBIGUOUS."
                )

        is_ambiguous = is_ambiguous_pc or is_ambiguous_user

        resolved_claimed = list(claimed_users.keys())[0] if claimed_users else "Unknown"
        resolved_mac = list(discovered_macs.keys())[0] if discovered_macs else "Unknown"
        resolved_owner = "Unknown"
        if device_owners:
            resolved_owner = list(device_owners.keys())[0]
            if resolved_user == "Unknown":
                diagnostics.append(f"Device owner identified as {resolved_owner} via SCCM/management association; no event-time active username established.")

        resolved_primary = list(primary_users.keys())[0] if primary_users else "Unknown"

        # 6. Status & Confidence Computation
        successful_sources_list = [s.get("source_type") for s in evidence_sources if s.get("result_status") in ("SUCCESS", "PARTIAL", "STALE_RESULT")]
        success_sources = [s for s in evidence_sources if s.get("result_status") == "SUCCESS"]
        not_configured_sources = [s for s in evidence_sources if s.get("result_status") == "NOT_CONFIGURED"]

        if is_ambiguous:
            status = IdentityStatus.AMBIGUOUS.value
        elif resolved_pc != "Unknown" and resolved_user != "Unknown":
            status = IdentityStatus.RESOLVED.value
        elif resolved_pc != "Unknown" or resolved_user != "Unknown" or resolved_owner != "Unknown":
            status = IdentityStatus.PARTIAL.value
        elif not success_sources and len(not_configured_sources) == len(evidence_sources):
            status = IdentityStatus.NOT_CONFIGURED.value
        elif not success_sources:
            status = IdentityStatus.NOT_FOUND.value
        else:
            status = IdentityStatus.PARTIAL.value

        confidence, confidence_score = compute_identity_confidence(
            status=status,
            time_match=primary_time_match,
            sources_count=len(successful_sources_list),
            is_ambiguous=is_ambiguous,
            has_pc=(resolved_pc != "Unknown"),
            has_user=(resolved_user != "Unknown"),
            has_owner=(resolved_owner != "Unknown"),
            time_decay=has_time_decay,
        )

        all_candidates: List[Dict[str, Any]] = []
        for pc, sc in sorted(pc_scores.items(), key=lambda x: x[1], reverse=True):
            srcs = pc_cand_info[pc]["sources"]
            all_candidates.append({
                "candidate_id": f"pc-{pc}",
                "pc_name": pc,
                "username": None,
                "sources": list(dict.fromkeys(srcs)),
                "confidence": "HIGH" if sc >= 80 else ("MEDIUM" if sc >= 50 else "LOW"),
                "confidence_score": int(sc),
                "rationale": f"Reported as computer identity by {', '.join(dict.fromkeys(srcs))} (score {sc:.0f}).",
            })
        for u, sc in sorted(user_scores.items(), key=lambda x: x[1], reverse=True):
            srcs = user_cand_info[u]["sources"]
            all_candidates.append({
                "candidate_id": f"user-{u}",
                "pc_name": None,
                "username": u,
                "sources": list(dict.fromkeys(srcs)),
                "confidence": "HIGH" if sc >= 80 else ("MEDIUM" if sc >= 50 else "LOW"),
                "confidence_score": int(sc),
                "rationale": f"Reported as active attacker username by {', '.join(dict.fromkeys(srcs))} (score {sc:.0f}).",
            })

        clamped_candidates = all_candidates[:self.max_candidates]

        confidence_rationale = (
            f"Status: {status}. Evaluated {len(sources_queried)} sources ({len(success_sources)} successful). "
            f"Time match: {primary_time_match.value}. Final score: {confidence_score}/100 ({confidence})."
        )

        attribution = AttackerAttribution(
            ip_address=clean_ip,
            network_scope=NetworkScope.LOCAL.value,
            pc_name=resolved_pc,
            fqdn=fqdn_val,
            domain=domain_val,
            username=resolved_user,
            user_display_name="Unknown",
            device_owner=resolved_owner,
            primary_device_user=resolved_primary,
            claimed_username=resolved_claimed,
            target_account="Unknown",
            mac_address=resolved_mac,
            branch=branch or "",
            status=status,
            confidence=confidence,
            confidence_score=confidence_score,
            confidence_rationale=confidence_rationale,
            observed_at=observed_at_str,
            incident_time_match=primary_time_match.value,
            sources_queried=list(sources_queried),
            successful_sources=successful_sources_list,
            evidence_sources=evidence_sources,
            candidates=clamped_candidates,
            diagnostics=diagnostics,
        )

        if self.cache_enabled:
            self._cache[cache_key] = attribution

        return attribution

    def resolve_incident_identity(
        self,
        incident: Incident,
        events: Optional[List[NormalizedSecurityEvent]] = None,
    ) -> AttackerAttribution:
        branch = incident.branches_involved[0] if incident.branches_involved else None
        supporting_ids = set(incident.supporting_event_ids) if incident.supporting_event_ids else None

        attribution = self.resolve_attacker_identity(
            ip_address=incident.attacker_ip,
            first_seen=incident.first_seen,
            last_seen=incident.last_seen,
            events=events,
            branch=branch,
            device_name=incident.source_device,
            supporting_event_ids=supporting_ids,
        )

        current_attr = None
        if incident.attacker_attribution:
            try:
                current_attr = AttackerAttribution.from_dict(incident.attacker_attribution)
            except Exception:
                current_attr = None

        if should_replace_attribution(current_attr, attribution):
            if current_attr:
                history_entry = {
                    "observed_at": current_attr.observed_at or None,
                    "status": current_attr.status,
                    "confidence": current_attr.confidence,
                    "confidence_score": current_attr.confidence_score,
                    "pc_name": current_attr.pc_name if current_attr.pc_name not in ("Unknown", "Not applicable") else None,
                    "username": current_attr.username if current_attr.username not in ("Unknown", "Not applicable") else None,
                    "sources": list(current_attr.successful_sources),
                    "diagnostic": "Superseded by a stronger identity resolution.",
                }
                attribution.attribution_history = ([history_entry] + list(current_attr.attribution_history))[:10]

            incident.attacker_pc_name = attribution.pc_name
            incident.attacker_fqdn = attribution.fqdn
            incident.attacker_username = attribution.username
            incident.attacker_user_display_name = attribution.user_display_name
            incident.attacker_device_owner = attribution.device_owner
            incident.attacker_primary_device_user = attribution.primary_device_user
            incident.attacker_claimed_username = attribution.claimed_username
            incident.attacker_target_account = attribution.target_account
            incident.attacker_mac_address = attribution.mac_address
            incident.attacker_network_scope = attribution.network_scope
            incident.attacker_identity_status = attribution.status
            incident.attacker_identity_confidence = attribution.confidence
            incident.attacker_identity_confidence_score = attribution.confidence_score
            incident.attacker_identity_observed_at = attribution.observed_at
            incident.attacker_identity_sources = attribution.successful_sources or attribution.sources_queried
            incident.attacker_identity_candidates = attribution.candidates
            incident.attacker_identity_diagnostics = attribution.diagnostics
            incident.attacker_attribution = attribution.to_dict()

        return attribution

