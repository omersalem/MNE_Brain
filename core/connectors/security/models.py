from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any


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
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


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


@dataclass
class CollectorResult:
    device_name: str
    status: CollectorStatus
    events: List[NormalizedSecurityEvent] = field(default_factory=list)
    error_message: Optional[str] = None
    collection_duration_seconds: float = 0.0
