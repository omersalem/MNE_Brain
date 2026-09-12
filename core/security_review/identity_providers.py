"""
Governed Identity Provider Adapters for MNE_Brain Release 2 Security Agent.

Provides production-ready, schema-governed provider adapters for:
- Event-Native telemetry (FortiGate / FortiAnalyzer / F5 / FMC)
- FortiAnalyzer UTM and VPN session log queries
- DHCP server lease history and current leases
- SCCM / MECM database hardware inventory and user affinity
- Reverse DNS and Active Directory domain computer accounts
- FortiGate authenticated session tables
"""

from __future__ import annotations

import abc
import logging
import os
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from core.connectors.security.models import NormalizedSecurityEvent
from core.security_review.identity_enrichment import (
    BaseIdentitySourceAdapter,
    SourceResolutionResult,
    IncidentTimeMatch,
    EventNativeIdentityAdapter,
    DhcpIdentityAdapter,
    SccmIdentityAdapter,
    DnsActiveDirectoryAdapter,
    FortiGateAuthAdapter,
    coerce_datetime_utc,
)

logger = logging.getLogger(__name__)


def _cancelled(kwargs: Dict[str, Any]) -> bool:
    signal = kwargs.get("cancel_event")
    return bool(signal is not None and signal.is_set())


def _binding_allows_read(binding: Optional[Dict[str, Any]]) -> bool:
    return bool(
        binding
        and binding.get("scope_status") == "ACTIVE"
        and binding.get("read_only") is True
    )


def _fortianalyzer_result(
    *,
    binding_id: str,
    ip: str,
    record: Dict[str, Any],
    ref_time: datetime,
    tolerance_seconds: int,
    diagnostic: str,
) -> SourceResolutionResult:
    pc_name = record.get("srcname") or record.get("src_host") or record.get("workstation_name")
    username = record.get("authuser")
    generic_user = record.get("user") or record.get("srcuser")
    relation = str(record.get("username_relation") or "").upper()
    if not username and relation in {"AUTHENTICATED_SOURCE_USER", "LOGGED_ON_ENDPOINT_USER"}:
        username = generic_user
    claimed_username = None if username else (record.get("unauthuser") or generic_user)
    mac = record.get("srcmac") or record.get("mac")

    observation_time = None
    for key in ("timestamp", "event_time", "source_timestamp", "datetime"):
        observation_time = coerce_datetime_utc(record.get(key))
        if observation_time:
            break
    if observation_time:
        distance = abs((observation_time - ref_time).total_seconds())
        time_match = IncidentTimeMatch.EXACT if distance <= tolerance_seconds else IncidentTimeMatch.CURRENT_ONLY
        weight = 0.90 if time_match == IncidentTimeMatch.EXACT else 0.45
    else:
        time_match = IncidentTimeMatch.UNKNOWN
        weight = 0.55

    matched_fields = [
        field
        for field, value in (
            ("srcname", pc_name),
            ("authuser", username),
            ("claimed_user", claimed_username),
            ("srcmac", mac),
        )
        if value
    ]
    return SourceResolutionResult(
        source_name="FortiAnalyzer",
        binding_id=binding_id,
        status=ResultStatus.SUCCESS.value,
        pc_name=pc_name.upper() if pc_name else None,
        username=username,
        claimed_username=claimed_username,
        mac_address=mac.upper().replace(":", "-") if mac else None,
        observation_time=observation_time,
        time_match=time_match,
        confidence_weight=weight,
        diagnostic=diagnostic,
        evidence_ref=f"faz-log-{ip}",
        matched_fields=matched_fields,
    )


class ResultStatus(str, Enum):
    SUCCESS = "SUCCESS"
    NO_MATCH = "NO_MATCH"
    NOT_CONFIGURED = "NOT_CONFIGURED"
    NOT_AUTHORIZED = "NOT_AUTHORIZED"
    UNREACHABLE = "UNREACHABLE"
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    QUERY_TIMEOUT = "QUERY_TIMEOUT"
    SKIPPED_DEADLINE = "SKIPPED_DEADLINE"
    STALE_RESULT = "STALE_RESULT"
    AMBIGUOUS = "AMBIGUOUS"
    MALFORMED_RESPONSE = "MALFORMED_RESPONSE"
    FAILED = "FAILED"


class GovernedIdentityQueryExecutor(abc.ABC):
    """Abstract contract for P7/P9 schema-governed infrastructure query execution."""

    @abc.abstractmethod
    def execute_query(
        self,
        binding_id: str,
        query_type: str,
        parameters: Dict[str, Any],
        timeout: float = 5.0,
    ) -> Dict[str, Any]:
        """Executes a strictly read-only, schema-governed query through registered transport."""
        raise NotImplementedError


EXPECTED_BINDING_CONTRACTS: Dict[str, Dict[str, Any]] = {
    "p7-fortianalyzer-log": {
        "platform": "fortianalyzer",
        "protocol": "json-rpc",
        "read_only": True,
        "credential_ref": "FORTIANALYZER_API_KEY",
    },
    "p7-dhcp-primary": {
        "platform": "windows-dhcp",
        "protocol": "powershell-winrm",
        "read_only": True,
        "credential_ref": "MNE_DHCP_PASSWORD",
    },
    "p7-sccm-sql": {
        "platform": "microsoft-sccm",
        "protocol": "sql-tds",
        "read_only": True,
        "credential_ref": "MNE_SCCM_PASSWORD",
    },
    "p7-ad-primary": {
        "platform": "active-directory",
        "protocol": "ldap-dns",
        "read_only": True,
        "credential_ref": "MNE_AD_PASSWORD",
    },
    "p7-fortigate-auth": {
        "platform": "fortios",
        "protocol": "rest-api",
        "read_only": True,
        "credential_ref": "FORTIGATE_CORE_API_KEY",
    },
}


class EventNativeIdentityProvider(EventNativeIdentityAdapter):
    """Event-native identity extractor utilizing normalized security telemetry."""

    def __init__(self, binding_id: str = "p7-event-native"):
        super().__init__()
        self.binding_id = binding_id


class FortiAnalyzerIdentityProvider(BaseIdentitySourceAdapter):
    """Queries FortiAnalyzer log database for historical and active session attributions."""

    def __init__(
        self,
        host: Optional[str] = None,
        adom: str = "root",
        binding_id: str = "p7-fortianalyzer-log",
        binding: Optional[Dict[str, Any]] = None,
        executor: Optional[GovernedIdentityQueryExecutor] = None,
        credential_reference: Optional[str] = "FORTIANALYZER_API_KEY",
        log_fetcher: Optional[Callable[..., Any]] = None,
        **kwargs: Any,
    ):
        super().__init__(name="FortiAnalyzer", binding_id=binding_id)
        self.host = host or os.environ.get("FORTIANALYZER_HOST")
        self.adom = adom or os.environ.get("FORTIANALYZER_ADOM", "root")
        self.binding = binding
        self.executor = executor
        self.credential_reference = credential_reference
        self.log_fetcher = log_fetcher

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
        ref_time = coerce_datetime_utc(last_seen) or coerce_datetime_utc(first_seen) or datetime.now(timezone.utc)

        if self.log_fetcher:
            try:
                record = self.log_fetcher(ip, ref_time)
            except Exception as exc:
                return SourceResolutionResult(
                    source_name=self.name,
                    binding_id=self.binding_id,
                    status=ResultStatus.FAILED.value,
                    diagnostic=f"FortiAnalyzer query failed: {exc}",
                )
            if not record:
                return SourceResolutionResult(
                    source_name=self.name,
                    binding_id=self.binding_id,
                    status=ResultStatus.NO_MATCH.value,
                    diagnostic=f"No FortiAnalyzer session logs found for IP {ip}.",
                )
            return _fortianalyzer_result(
                binding_id=self.binding_id,
                ip=ip,
                record=record,
                ref_time=ref_time,
                tolerance_seconds=int(kwargs.get("event_time_tolerance_seconds", 3600)),
                diagnostic="FortiAnalyzer log session matched the requested IP.",
            )

        if self.binding is None or self.executor is None:
            return SourceResolutionResult(
                source_name=self.name,
                binding_id=self.binding_id,
                status=ResultStatus.NOT_CONFIGURED.value,
                diagnostic="FortiAnalyzer binding or query executor not configured; live queries disabled at rest.",
            )

        if not _binding_allows_read(self.binding):
            return SourceResolutionResult(
                source_name=self.name,
                binding_id=self.binding_id,
                status=ResultStatus.NOT_AUTHORIZED.value,
                diagnostic="FortiAnalyzer query not authorized: binding scope is excluded or non-read-only.",
            )

        try:
            if _cancelled(kwargs):
                return SourceResolutionResult(source_name=self.name, binding_id=self.binding_id, status=ResultStatus.QUERY_TIMEOUT.value, diagnostic="Query cancelled before execution.")
            res = self.executor.execute_query(
                binding_id=self.binding_id,
                query_type="session_log_search",
                parameters={"ip": ip, "timestamp": ref_time.isoformat(), "adom": self.adom},
                timeout=timeout,
            )
            record = res.get("record")
            if not record:
                return SourceResolutionResult(
                    source_name=self.name,
                    binding_id=self.binding_id,
                    status=ResultStatus.NO_MATCH.value,
                    diagnostic=f"No FortiAnalyzer session logs returned for IP {ip}.",
                )
            if _cancelled(kwargs):
                return SourceResolutionResult(source_name=self.name, binding_id=self.binding_id, status=ResultStatus.QUERY_TIMEOUT.value, diagnostic="Query result discarded after timeout.")
            return _fortianalyzer_result(
                binding_id=self.binding_id,
                ip=ip,
                record=record,
                ref_time=ref_time,
                tolerance_seconds=int(kwargs.get("event_time_tolerance_seconds", 3600)),
                diagnostic="Governed FortiAnalyzer query matched the requested IP.",
            )
        except Exception as exc:
            return SourceResolutionResult(
                source_name=self.name,
                binding_id=self.binding_id,
                status=ResultStatus.FAILED.value,
                diagnostic=f"Governed FortiAnalyzer query failed: {exc}",
            )


class DhcpIdentityProvider(DhcpIdentityAdapter):
    """Production DHCP provider adapter checking environment configuration and bindings."""

    def __init__(
        self,
        host: Optional[str] = None,
        username: Optional[str] = None,
        binding_id: str = "p7-dhcp-primary",
        binding: Optional[Dict[str, Any]] = None,
        executor: Optional[GovernedIdentityQueryExecutor] = None,
        credential_reference: Optional[str] = "MNE_DHCP_PASSWORD",
        lease_history_provider: Optional[Callable[..., Any]] = None,
        **kwargs: Any,
    ):
        self.host = host or os.environ.get("MNE_DHCP_HOST")
        self.username = username or os.environ.get("MNE_DHCP_USERNAME")
        self.binding = binding
        self.executor = executor
        self.credential_reference = credential_reference
        super().__init__(dhcp_provider=lease_history_provider, binding_id=binding_id)

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
        if self.dhcp_provider is not None:
            return super().resolve(
                ip=ip,
                first_seen=first_seen,
                last_seen=last_seen,
                events=events,
                branch=branch,
                timeout=timeout,
                **kwargs,
            )

        if self.binding is None or self.executor is None:
            return SourceResolutionResult(
                source_name=self.name,
                binding_id=self.binding_id,
                status=ResultStatus.NOT_CONFIGURED.value,
                diagnostic="DHCP server binding or query executor not configured; live queries disabled at rest.",
            )

        if not _binding_allows_read(self.binding):
            return SourceResolutionResult(
                source_name=self.name,
                binding_id=self.binding_id,
                status=ResultStatus.NOT_AUTHORIZED.value,
                diagnostic="DHCP query not authorized: binding scope is excluded or non-read-only.",
            )

        try:
            if _cancelled(kwargs):
                return SourceResolutionResult(source_name=self.name, binding_id=self.binding_id, status=ResultStatus.QUERY_TIMEOUT.value, diagnostic="Query cancelled before execution.")
            ref_time = coerce_datetime_utc(last_seen) or coerce_datetime_utc(first_seen) or datetime.now(timezone.utc)
            res = self.executor.execute_query(
                binding_id=self.binding_id,
                query_type="dhcp_lease_lookup",
                parameters={"ip": ip, "timestamp": ref_time.isoformat()},
                timeout=timeout,
            )
            record = res.get("record")
            if not record:
                return SourceResolutionResult(
                    source_name=self.name,
                    binding_id=self.binding_id,
                    status=ResultStatus.NO_MATCH.value,
                    diagnostic=f"No DHCP lease record found for {ip}.",
                )
            if _cancelled(kwargs):
                return SourceResolutionResult(source_name=self.name, binding_id=self.binding_id, status=ResultStatus.QUERY_TIMEOUT.value, diagnostic="Query result discarded after timeout.")
            parser = DhcpIdentityAdapter(dhcp_provider=lambda _ip, _t=None: record, binding_id=self.binding_id)
            return parser.resolve(
                ip=ip,
                first_seen=first_seen,
                last_seen=last_seen,
                events=events,
                branch=branch,
                timeout=timeout,
                **kwargs,
            )
        except Exception as exc:
            return SourceResolutionResult(
                source_name=self.name,
                binding_id=self.binding_id,
                status=ResultStatus.FAILED.value,
                diagnostic=f"Governed DHCP query failed: {exc}",
            )


class SccmIdentityProvider(SccmIdentityAdapter):
    """Production SCCM provider adapter checking environment configuration and bindings."""

    def __init__(
        self,
        host: Optional[str] = None,
        username: Optional[str] = None,
        binding_id: str = "p7-sccm-sql",
        binding: Optional[Dict[str, Any]] = None,
        executor: Optional[GovernedIdentityQueryExecutor] = None,
        credential_reference: Optional[str] = "MNE_SCCM_PASSWORD",
        query_executor: Optional[Callable[..., Any]] = None,
        **kwargs: Any,
    ):
        self.host = host or os.environ.get("MNE_SCCM_HOST")
        self.username = username or os.environ.get("MNE_SCCM_USERNAME")
        self.binding = binding
        self.executor = executor
        self.credential_reference = credential_reference
        super().__init__(query_executor=query_executor, binding_id=binding_id)

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
        if self.sccm_provider is not None:
            return super().resolve(
                ip=ip,
                first_seen=first_seen,
                last_seen=last_seen,
                events=events,
                branch=branch,
                timeout=timeout,
                **kwargs,
            )

        if self.binding is None or self.executor is None:
            return SourceResolutionResult(
                source_name=self.name,
                binding_id=self.binding_id,
                status=ResultStatus.NOT_CONFIGURED.value,
                diagnostic="SCCM database binding or query executor not configured; live queries disabled at rest.",
            )

        if not _binding_allows_read(self.binding):
            return SourceResolutionResult(
                source_name=self.name,
                binding_id=self.binding_id,
                status=ResultStatus.NOT_AUTHORIZED.value,
                diagnostic="SCCM query not authorized: binding scope is excluded or non-read-only.",
            )

        try:
            if _cancelled(kwargs):
                return SourceResolutionResult(source_name=self.name, binding_id=self.binding_id, status=ResultStatus.QUERY_TIMEOUT.value, diagnostic="Query cancelled before execution.")
            res = self.executor.execute_query(
                binding_id=self.binding_id,
                query_type="sccm_inventory_lookup",
                parameters={"ip": ip},
                timeout=timeout,
            )
            record = res.get("record")
            if not record:
                return SourceResolutionResult(
                    source_name=self.name,
                    binding_id=self.binding_id,
                    status=ResultStatus.NO_MATCH.value,
                    diagnostic=f"No SCCM hardware inventory record found matching IP {ip}.",
                )
            if _cancelled(kwargs):
                return SourceResolutionResult(source_name=self.name, binding_id=self.binding_id, status=ResultStatus.QUERY_TIMEOUT.value, diagnostic="Query result discarded after timeout.")
            parser = SccmIdentityAdapter(query_executor=lambda _ip: record, binding_id=self.binding_id)
            return parser.resolve(
                ip=ip,
                first_seen=first_seen,
                last_seen=last_seen,
                events=events,
                branch=branch,
                timeout=timeout,
                **kwargs,
            )
        except Exception as exc:
            return SourceResolutionResult(
                source_name=self.name,
                binding_id=self.binding_id,
                status=ResultStatus.FAILED.value,
                diagnostic=f"Governed SCCM query failed: {exc}",
            )


class DnsActiveDirectoryIdentityProvider(DnsActiveDirectoryAdapter):
    """Production DNS/AD provider adapter checking environment configuration and bindings."""

    def __init__(
        self,
        ad_host: Optional[str] = None,
        binding_id: str = "p7-ad-primary",
        binding: Optional[Dict[str, Any]] = None,
        executor: Optional[GovernedIdentityQueryExecutor] = None,
        credential_reference: Optional[str] = "MNE_AD_PASSWORD",
        ad_provider: Optional[Callable[..., Any]] = None,
        dns_provider: Optional[Callable[..., Any]] = None,
        **kwargs: Any,
    ):
        self.ad_host = ad_host or os.environ.get("MNE_AD_HOST")
        self.binding = binding
        self.executor = executor
        self.credential_reference = credential_reference
        super().__init__(ad_provider=ad_provider, dns_provider=dns_provider, binding_id=binding_id)

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
        if self.dns_provider is not None or self.ad_provider is not None:
            return super().resolve(
                ip=ip,
                first_seen=first_seen,
                last_seen=last_seen,
                events=events,
                branch=branch,
                timeout=timeout,
                **kwargs,
            )

        if self.binding is None or self.executor is None:
            return SourceResolutionResult(
                source_name=self.name,
                binding_id=self.binding_id,
                status=ResultStatus.NOT_CONFIGURED.value,
                diagnostic="DNS/AD server binding or query executor not configured; live queries disabled at rest.",
            )

        if not _binding_allows_read(self.binding):
            return SourceResolutionResult(
                source_name=self.name,
                binding_id=self.binding_id,
                status=ResultStatus.NOT_AUTHORIZED.value,
                diagnostic="DNS/AD query not authorized: binding scope is excluded or non-read-only.",
            )

        try:
            if _cancelled(kwargs):
                return SourceResolutionResult(source_name=self.name, binding_id=self.binding_id, status=ResultStatus.QUERY_TIMEOUT.value, diagnostic="Query cancelled before execution.")
            res = self.executor.execute_query(
                binding_id=self.binding_id,
                query_type="dns_ad_lookup",
                parameters={"ip": ip},
                timeout=timeout,
            )
            if _cancelled(kwargs):
                return SourceResolutionResult(source_name=self.name, binding_id=self.binding_id, status=ResultStatus.QUERY_TIMEOUT.value, diagnostic="Query result discarded after timeout.")
            host = res.get("resolved_host")
            ad_obj = res.get("ad_record")
            parser = DnsActiveDirectoryAdapter(
                dns_provider=(lambda _ip: host) if host else None,
                ad_provider=(lambda _host: ad_obj) if ad_obj else None,
                binding_id=self.binding_id,
            )
            return parser.resolve(
                ip=ip,
                first_seen=first_seen,
                last_seen=last_seen,
                events=events,
                branch=branch,
                timeout=timeout,
                **kwargs,
            )
        except Exception as exc:
            return SourceResolutionResult(
                source_name=self.name,
                binding_id=self.binding_id,
                status=ResultStatus.FAILED.value,
                diagnostic=f"Governed DNS/AD query failed: {exc}",
            )


class FortiGateAuthIdentityProvider(FortiGateAuthAdapter):
    """Production FortiGate Auth provider adapter checking environment configuration and bindings."""

    def __init__(
        self,
        host: Optional[str] = None,
        binding_id: str = "p7-fortigate-auth",
        binding: Optional[Dict[str, Any]] = None,
        executor: Optional[GovernedIdentityQueryExecutor] = None,
        credential_reference: Optional[str] = "FORTIGATE_CORE_API_KEY",
        auth_provider: Optional[Callable[..., Any]] = None,
        **kwargs: Any,
    ):
        self.host = host or os.environ.get("FORTIGATE_CORE_HOST")
        self.binding = binding
        self.executor = executor
        self.credential_reference = credential_reference
        super().__init__(auth_provider=auth_provider, binding_id=binding_id)

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
        if self.auth_provider is not None:
            return super().resolve(
                ip=ip,
                first_seen=first_seen,
                last_seen=last_seen,
                events=events,
                branch=branch,
                timeout=timeout,
                **kwargs,
            )

        if self.binding is None or self.executor is None:
            return SourceResolutionResult(
                source_name=self.name,
                binding_id=self.binding_id,
                status=ResultStatus.NOT_CONFIGURED.value,
                diagnostic="FortiGate Auth binding or query executor not configured; live queries disabled at rest.",
            )

        if not _binding_allows_read(self.binding):
            return SourceResolutionResult(
                source_name=self.name,
                binding_id=self.binding_id,
                status=ResultStatus.NOT_AUTHORIZED.value,
                diagnostic="FortiGate Auth query not authorized: binding scope is excluded or non-read-only.",
            )

        try:
            if _cancelled(kwargs):
                return SourceResolutionResult(source_name=self.name, binding_id=self.binding_id, status=ResultStatus.QUERY_TIMEOUT.value, diagnostic="Query cancelled before execution.")
            res = self.executor.execute_query(
                binding_id=self.binding_id,
                query_type="auth_session_lookup",
                parameters={"ip": ip},
                timeout=timeout,
            )
            record = res.get("record")
            if not record:
                return SourceResolutionResult(
                    source_name=self.name,
                    binding_id=self.binding_id,
                    status=ResultStatus.NO_MATCH.value,
                    diagnostic=f"No FortiGate authenticated session found for IP {ip}.",
                )
            if _cancelled(kwargs):
                return SourceResolutionResult(source_name=self.name, binding_id=self.binding_id, status=ResultStatus.QUERY_TIMEOUT.value, diagnostic="Query result discarded after timeout.")
            parser = FortiGateAuthAdapter(auth_provider=lambda _ip, _time=None: record, binding_id=self.binding_id)
            return parser.resolve(
                ip=ip,
                first_seen=first_seen,
                last_seen=last_seen,
                events=events,
                branch=branch,
                timeout=timeout,
                **kwargs,
            )
        except Exception as exc:
            return SourceResolutionResult(
                source_name=self.name,
                binding_id=self.binding_id,
                status=ResultStatus.FAILED.value,
                diagnostic=f"Governed FortiGate Auth query failed: {exc}",
            )


def create_identity_adapters(
    config: Optional[Dict[str, Any]] = None,
    bindings: Optional[Dict[str, Any]] = None,
    executor: Optional[GovernedIdentityQueryExecutor] = None,
) -> List[BaseIdentitySourceAdapter]:
    """Factory creating schema-governed identity source adapters from environment or config.

    Instantiates production adapters without mock data defaults; unconfigured systems
    honestly report NOT_CONFIGURED upon execution.
    """
    cfg = config or {}
    b = bindings or {}
    adapters: List[BaseIdentitySourceAdapter] = [
        EventNativeIdentityProvider(),
        FortiAnalyzerIdentityProvider(
            host=cfg.get("fortianalyzer_host"),
            binding_id="p7-fortianalyzer-log",
            binding=b.get("p7-fortianalyzer-log"),
            executor=executor,
            credential_reference="FORTIANALYZER_API_KEY",
        ),
        DhcpIdentityProvider(
            host=cfg.get("dhcp_host"),
            username=cfg.get("dhcp_username"),
            binding_id="p7-dhcp-primary",
            binding=b.get("p7-dhcp-primary"),
            executor=executor,
            credential_reference="MNE_DHCP_PASSWORD",
        ),
        SccmIdentityProvider(
            host=cfg.get("sccm_host"),
            username=cfg.get("sccm_username"),
            binding_id="p7-sccm-sql",
            binding=b.get("p7-sccm-sql"),
            executor=executor,
            credential_reference="MNE_SCCM_PASSWORD",
        ),
        DnsActiveDirectoryIdentityProvider(
            ad_host=cfg.get("ad_host"),
            binding_id="p7-ad-primary",
            binding=b.get("p7-ad-primary"),
            executor=executor,
            credential_reference="MNE_AD_PASSWORD",
        ),
        FortiGateAuthIdentityProvider(
            host=cfg.get("fortigate_host"),
            binding_id="p7-fortigate-auth",
            binding=b.get("p7-fortigate-auth"),
            executor=executor,
            credential_reference="FORTIGATE_CORE_API_KEY",
        ),
    ]
    return adapters
