from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

from core.security_review.contracts import (
    CollectorDiagnostic,
    DiagnosticStage,
    DiagnosticStatus,
)


class SeverityLevel(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class ThreatCategory(str, Enum):
    INTRUSION = "INTRUSION"
    MALWARE = "MALWARE"
    BRUTE_FORCE = "BRUTE_FORCE"
    WAF_EXPLOIT = "WAF_EXPLOIT"
    PHISHING = "PHISHING"
    PRIVILEGE_CHANGE = "PRIVILEGE_CHANGE"
    SYSTEM_HEALTH = "SYSTEM_HEALTH"
    ANOMALY = "ANOMALY"


class CollectorStatus(str, Enum):
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


@dataclass
class CollectorRequest:
    start_time: Optional[Union[datetime, str]] = None
    end_time: Optional[Union[datetime, str]] = None
    hours_back: Optional[float] = 24.0
    max_records: int = 500
    mode: str = "FULL"
    categories: Optional[List[str]] = None
    branches: Optional[List[str]] = None
    source_addresses: Optional[List[str]] = None
    destination_addresses: Optional[List[str]] = None
    usernames: Optional[List[str]] = None
    filters: Dict[str, Any] = field(default_factory=dict)
    cancel_callback: Optional[Callable[[], bool]] = None

    def __post_init__(self) -> None:
        if isinstance(self.start_time, str):
            try:
                self.start_time = datetime.fromisoformat(self.start_time.replace("Z", "+00:00"))
            except Exception:
                pass
        if isinstance(self.end_time, str):
            try:
                self.end_time = datetime.fromisoformat(self.end_time.replace("Z", "+00:00"))
            except Exception:
                pass

    def get_time_window(self, now: Optional[datetime] = None) -> tuple[datetime, datetime]:
        """Returns (start_dt, end_dt) in UTC guaranteed to be timezone-aware datetimes."""
        ref_now = now or datetime.now(timezone.utc)
        if self.end_time and isinstance(self.end_time, datetime):
            end_dt = self.end_time if self.end_time.tzinfo else self.end_time.replace(tzinfo=timezone.utc)
        else:
            end_dt = ref_now

        if self.start_time and isinstance(self.start_time, datetime):
            start_dt = self.start_time if self.start_time.tzinfo else self.start_time.replace(tzinfo=timezone.utc)
        else:
            h = float(self.hours_back) if self.hours_back is not None else 24.0
            start_dt = end_dt - timedelta(hours=h)

        return start_dt, end_dt

    def is_cancelled(self) -> bool:
        if self.cancel_callback is not None:
            try:
                return bool(self.cancel_callback())
            except Exception:
                return False
        return False


class UsernameRelation(str, Enum):
    AUTHENTICATED_SOURCE_USER = "AUTHENTICATED_SOURCE_USER"
    LOGGED_ON_ENDPOINT_USER = "LOGGED_ON_ENDPOINT_USER"
    CLAIMED_LOGIN_USERNAME = "CLAIMED_LOGIN_USERNAME"
    TARGET_ACCOUNT = "TARGET_ACCOUNT"
    PRIMARY_DEVICE_USER = "PRIMARY_DEVICE_USER"
    DEVICE_OWNER = "DEVICE_OWNER"
    UNKNOWN_RELATION = "UNKNOWN_RELATION"


@dataclass
class NormalizedSecurityEvent:
    event_id: str
    timestamp: datetime
    source_device: str
    category: ThreatCategory
    threat_name: str
    attacker_ip: Optional[str] = None
    target: Optional[str] = None
    action_taken: str = "UNKNOWN"
    count: int = 1
    raw_snippet: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    attacker_hostname: Optional[str] = None
    source_hostname: Optional[str] = None
    attacker_mac: Optional[str] = None
    authenticated_source_user: Optional[str] = None
    logged_on_endpoint_user: Optional[str] = None
    claimed_login_username: Optional[str] = None
    target_account: Optional[str] = None
    username_relation: Optional[str] = None
    hostname_role: Optional[str] = None


def normalize_action(action: str) -> str:
    """Explicitly and case-insensitively normalizes event disposition/action."""
    act = (action or "").strip().upper()
    if act in ("ALLOWED", "ALLOW", "PASS", "PERMIT", "ACCEPT", "SUCCESS", "AUDIT"):
        return "ALLOWED"
    if act in ("BLOCKED", "BLOCK", "DROPPED", "DROP", "DENIED", "DENY", "REJECTED", "REJECT", "QUARANTINED", "QUARANTINE", "DISCARD"):
        return "BLOCKED"
    if act in ("ALERT", "DETECTED", "DETECT", "MONITOR", "MONITORED", "WARNING"):
        return "ALERT"
    return "UNKNOWN"


@dataclass
class Incident:
    incident_id: str
    title: str
    severity: SeverityLevel
    source_device: str
    category: ThreatCategory
    first_seen: datetime
    last_seen: datetime
    description: str
    action_taken: str
    event_count: int = 1
    attacker_ip: Optional[str] = None
    target: Optional[str] = None
    remediation_cli: List[str] = field(default_factory=list)
    remediation_gui: List[str] = field(default_factory=list)
    remediation_mode_b_command: Optional[str] = None
    fingerprint: str = ""
    display_id: str = ""
    signature_family: str = ""
    devices_involved: List[str] = field(default_factory=list)
    branches_involved: List[str] = field(default_factory=list)
    affected_targets: List[str] = field(default_factory=list)
    observed_dispositions: List[str] = field(default_factory=list)
    supporting_event_ids: List[str] = field(default_factory=list)
    distinct_signatures: List[str] = field(default_factory=list)
    blocked_count: int = 0
    allowed_count: int = 0
    severity_rationale: str = ""
    lifecycle_state: str = "NEW"
    occurrence_count: int = 1
    analyst_notes: List[Dict[str, str]] = field(default_factory=list)
    attacker_pc_name: str = "Unknown"
    attacker_fqdn: str = "Unknown"
    attacker_username: str = "Unknown"
    attacker_user_display_name: str = "Unknown"
    attacker_device_owner: str = "Unknown"
    attacker_primary_device_user: str = "Unknown"
    attacker_claimed_username: str = "Unknown"
    attacker_target_account: str = "Unknown"
    attacker_mac_address: str = "Unknown"
    attacker_network_scope: str = "UNKNOWN"
    attacker_identity_status: str = "NOT_CONFIGURED"
    attacker_identity_confidence: str = "UNKNOWN"
    attacker_identity_confidence_score: int = 0
    attacker_identity_observed_at: Optional[str] = None
    attacker_identity_sources: List[str] = field(default_factory=list)
    attacker_identity_candidates: List[Dict[str, Any]] = field(default_factory=list)
    attacker_identity_diagnostics: List[str] = field(default_factory=list)
    attacker_attribution: Optional[Dict[str, Any]] = None



@dataclass
class CollectorResult:
    device_name: str
    status: CollectorStatus
    events: List[NormalizedSecurityEvent] = field(default_factory=list)
    error_message: Optional[str] = None
    collection_duration_seconds: float = 0.0
    diagnostic: Optional[CollectorDiagnostic] = None
    records_fetched: int = 0
    records_parsed: int = 0
    records_ignored: int = 0
    records_malformed: int = 0
    records_duplicate: int = 0
