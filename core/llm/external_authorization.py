"""Short-lived authorization for exact redacted context sent to external AI."""

from __future__ import annotations

import hashlib
import json
import re
import secrets
import threading
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Any

import jsonschema


class ExternalAuthorizationError(PermissionError):
    pass


class ExternalDataPolicy:
    _SECRET = re.compile(r"(?i)(password|passwd|token|secret|authorization|api[_-]?key|private[_-]?key|community)\s*[:=]\s*\S+")
    _PROHIBITED_KEYS = {"credential", "credentials", "raw_output", "command", "rollback_secret", "hidden_log", "private_key"}
    _ALLOWED_SOURCE_PREFIXES = ("knowledge/", "intelligence/reports/", "public-doc:", "conversation:")

    @classmethod
    def redact_text(cls, value: str) -> str:
        return cls._SECRET.sub(r"\1=[REDACTED]", value)

    @classmethod
    def sanitize(cls, value: Any, *, key: str = "") -> Any:
        if key.lower() in cls._PROHIBITED_KEYS:
            raise ExternalAuthorizationError(f"Prohibited external context field: {key}")
        if isinstance(value, dict):
            return {str(k): cls.sanitize(v, key=str(k)) for k, v in value.items()}
        if isinstance(value, list):
            return [cls.sanitize(item, key=key) for item in value]
        if isinstance(value, str):
            return cls.redact_text(value)
        return value

    @classmethod
    def validate_sources(cls, sources: list[str]) -> None:
        for source in sources:
            if not isinstance(source, str) or not source.startswith(cls._ALLOWED_SOURCE_PREFIXES) or "\\" in source or "\x00" in source or "\n" in source or "\r" in source:
                raise ExternalAuthorizationError("External evidence source is outside the allowlist.")
            if source.startswith(("knowledge/", "intelligence/reports/")):
                path = PurePosixPath(source)
                if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
                    raise ExternalAuthorizationError("External evidence source traversal rejected.")


class ExternalAuthorizationManager:
    def __init__(self, base_dir: Path, *, ttl_seconds: int = 300, now: Any = None):
        self.base_dir = base_dir.resolve()
        self.ttl_seconds = ttl_seconds
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._items: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._schema = json.loads((self.base_dir / "00_meta/schemas/external-ai-authorization.schema.json").read_text(encoding="utf-8"))

    @staticmethod
    def canonical(value: Any) -> str:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    @classmethod
    def digest(cls, value: Any) -> str:
        return hashlib.sha256(cls.canonical(value).encode("utf-8")).hexdigest()

    def prepare(self, *, thread_id: str, provider_id: str, model_id: str, prompt: str, context: Any, evidence_sources: list[str], data_classification: str, includes_live_evidence: bool) -> tuple[dict[str, Any], Any]:
        if data_classification not in {"PUBLIC", "INTERNAL_REDACTED"}:
            raise ExternalAuthorizationError("External data classification is not allowed.")
        ExternalDataPolicy.validate_sources(evidence_sources)
        sanitized = ExternalDataPolicy.sanitize(context)
        redaction_digest = self.digest(sanitized)
        prompt_digest = self.digest(ExternalDataPolicy.redact_text(prompt))
        context_digest = self.digest({"context": sanitized, "sources": evidence_sources})
        created = self._now()
        core = {
            "thread_id": thread_id,
            "provider_id": provider_id,
            "model_id": model_id,
            "evidence_sources": sorted(evidence_sources),
            "data_classification": data_classification,
            "redaction_digest": redaction_digest,
            "context_digest": context_digest,
            "prompt_digest": prompt_digest,
            "estimated_context_tokens": len(self.canonical(sanitized)) // 4,
            "includes_live_evidence": bool(includes_live_evidence),
        }
        item = {
            "authorization_id": "xauth_" + secrets.token_urlsafe(18),
            **core,
            "created_at": created.isoformat(),
            "expires_at": (created + timedelta(seconds=self.ttl_seconds)).isoformat(),
            "authorization_digest": self.digest(core),
            "used": False,
        }
        jsonschema.Draft7Validator(self._schema, format_checker=jsonschema.FormatChecker()).validate(item)
        with self._lock:
            self._items[item["authorization_id"]] = deepcopy(item)
        return deepcopy(item), sanitized

    def authorize(self, authorization_id: str, *, expected: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            item = self._items.get(authorization_id)
            if item is None:
                raise ExternalAuthorizationError("External authorization is missing.")
            if self._now() > datetime.fromisoformat(item["expires_at"]):
                raise ExternalAuthorizationError("External authorization expired.")
            if item["used"]:
                raise ExternalAuthorizationError("External authorization replay rejected.")
            fields = ("thread_id", "provider_id", "model_id", "context_digest", "prompt_digest", "redaction_digest")
            if any(item[field] != expected.get(field) for field in fields):
                raise ExternalAuthorizationError("External authorization context changed.")
            item["used"] = True
            return deepcopy(item)

    def inspect(self, authorization_id: str) -> dict[str, Any]:
        with self._lock:
            item = deepcopy(self._items.get(authorization_id))
        if item is None:
            raise ExternalAuthorizationError("External authorization is missing.")
        return item
