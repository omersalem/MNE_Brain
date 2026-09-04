"""Schema-valid in-memory thread, turn, and message store."""

from __future__ import annotations

import json
import secrets
import threading
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jsonschema

from core.llm.capability_policy import CapabilityPolicy, PERMISSION_MODES


class ThreadStoreError(ValueError):
    pass


class ThreadStore:
    LEGACY_GEMINI_PROVIDER_ID = "prv_gemini_cli"
    OPENCODE_PROVIDER_ID = "prv_opencode"
    ANTIGRAVITY_PROVIDER_ID = "prv_antigravity_cli"

    def __init__(self, base_dir: Path):
        schema_dir = base_dir / "00_meta/schemas"
        self._schemas = {name: json.loads((schema_dir / name).read_text(encoding="utf-8")) for name in ("conversation-thread.schema.json", "conversation-turn.schema.json", "conversation-message.schema.json")}
        self._threads: dict[str, dict[str, Any]] = {}
        self._turns: dict[str, dict[str, Any]] = {}
        self._messages: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _id(prefix: str) -> str:
        return prefix + secrets.token_urlsafe(18)

    def _validate(self, name: str, value: dict[str, Any]) -> None:
        jsonschema.Draft7Validator(self._schemas[name], format_checker=jsonschema.FormatChecker()).validate(value)

    @staticmethod
    def _engine_for_provider(provider_id: str) -> str:
        if provider_id == "prv_codex_app_server":
            return "codex"
        if provider_id == "prv_opencode":
            return "opencode"
        if provider_id == "prv_antigravity_cli":
            return "antigravity"
        if provider_id == "prv_local_deterministic":
            return "deterministic"
        return "provider"

    def create_thread(self, *, title: str, provider_id: str = "prv_local_deterministic", permission_mode: str = "OWNER_FULL_CONTROL", engine_id: str | None = None, model_id: str | None = None) -> dict[str, Any]:
        if permission_mode not in PERMISSION_MODES:
            raise ThreadStoreError("Invalid permission mode.")
        now = self._now()
        resolved_engine = engine_id or self._engine_for_provider(provider_id)
        default_models = {
            "codex": "codex-account-default",
            "opencode": "select-model",
            "antigravity": "gemini-3.8-flash-high",
            "deterministic": "mne-deterministic-v1",
        }
        item = {"thread_id": self._id("thr_"), "title": (title or "New conversation")[:160], "created_at": now, "updated_at": now, "status": "ACTIVE", "permission_mode": permission_mode, "provider_id": provider_id, "engine_id": resolved_engine, "model_id": model_id or default_models.get(resolved_engine, "provider-default"), "turn_ids": []}
        self._validate("conversation-thread.schema.json", item)
        with self._lock:
            self._threads[item["thread_id"]] = item
        return deepcopy(item)

    def list_threads(self, search: str = "") -> list[dict[str, Any]]:
        query = search.casefold().strip()
        with self._lock:
            values = [deepcopy(item) for item in self._threads.values() if not query or query in item["title"].casefold() or self._thread_contains(item["thread_id"], query)]
        return sorted(values, key=lambda item: item["updated_at"], reverse=True)

    def _thread_contains(self, thread_id: str, query: str) -> bool:
        return any(query in item["content"].casefold() for item in self._messages.values() if item["thread_id"] == thread_id)

    def get_thread(self, thread_id: str, *, include_items: bool = True) -> dict[str, Any]:
        with self._lock:
            thread = deepcopy(self._threads.get(thread_id))
            if thread is None:
                raise ThreadStoreError("Thread not found.")
            if include_items:
                thread["turns"] = [deepcopy(self._turns[turn_id]) for turn_id in thread["turn_ids"]]
                thread["messages"] = [deepcopy(item) for item in self._messages.values() if item["thread_id"] == thread_id]
        return thread

    def switch_provider(self, thread_id: str, provider_id: str) -> dict[str, Any]:
        with self._lock:
            if thread_id not in self._threads:
                raise ThreadStoreError("Thread not found.")
            updated = CapabilityPolicy.switch_provider(self._threads[thread_id], provider_id)
            updated["engine_id"] = self._engine_for_provider(provider_id)
            updated["updated_at"] = self._now()
            self._validate("conversation-thread.schema.json", updated)
            self._threads[thread_id] = updated
            return deepcopy(updated)

    def pin_engine(self, thread_id: str, *, provider_id: str, engine_id: str, model_id: str) -> dict[str, Any]:
        with self._lock:
            item = self._threads.get(thread_id)
            if item is None:
                raise ThreadStoreError("Thread not found.")
            if item["turn_ids"]:
                raise ThreadStoreError("Engine and model are pinned after the first turn. Create a new conversation to switch engines.")
            if self._engine_for_provider(provider_id) != engine_id:
                raise ThreadStoreError("Engine and provider do not match.")
            item["provider_id"] = provider_id
            item["engine_id"] = engine_id
            item["model_id"] = model_id[:512]
            item["updated_at"] = self._now()
            self._validate("conversation-thread.schema.json", item)
            return deepcopy(item)

    def recover_unavailable_opencode_model(self, thread_id: str, model_id: str) -> dict[str, Any]:
        """Explicitly replace only an unavailable OpenCode pin; history is unchanged."""
        with self._lock:
            item = self._threads.get(thread_id)
            if item is None:
                raise ThreadStoreError("Thread not found.")
            if item["engine_id"] != "opencode" or item["provider_id"] != self.OPENCODE_PROVIDER_ID:
                raise ThreadStoreError("Model recovery applies only to an OpenCode conversation.")
            item["model_id"] = model_id[:512]
            item["updated_at"] = self._now()
            self._validate("conversation-thread.schema.json", item)
            return deepcopy(item)

    def set_permission_mode(self, thread_id: str, permission_mode: str) -> dict[str, Any]:
        if permission_mode not in PERMISSION_MODES:
            raise ThreadStoreError("Invalid permission mode.")
        with self._lock:
            if thread_id not in self._threads:
                raise ThreadStoreError("Thread not found.")
            self._threads[thread_id]["permission_mode"] = permission_mode
            self._threads[thread_id]["updated_at"] = self._now()
            self._validate("conversation-thread.schema.json", self._threads[thread_id])
            return deepcopy(self._threads[thread_id])

    def create_turn(self, thread_id: str, *, external_authorization_id: str | None = None) -> dict[str, Any]:
        with self._lock:
            thread = self._threads.get(thread_id)
            if thread is None:
                raise ThreadStoreError("Thread not found.")
            now = self._now()
            turn = {"turn_id": self._id("trn_"), "thread_id": thread_id, "provider_id": thread["provider_id"], "engine_id": thread["engine_id"], "model_id": thread["model_id"], "permission_mode": thread["permission_mode"], "status": "QUEUED", "created_at": now, "updated_at": now, "message_ids": [], "external_authorization_id": external_authorization_id}
            self._validate("conversation-turn.schema.json", turn)
            self._turns[turn["turn_id"]] = turn
            thread["turn_ids"].append(turn["turn_id"])
            thread["updated_at"] = now
            return deepcopy(turn)

    def _set_turn_attribution(self, turn_id: str, *, provider_id: str, engine_id: str, model_id: str) -> None:
        """Restore immutable historical attribution during a trusted import."""
        with self._lock:
            turn = self._turns[turn_id]
            turn["provider_id"] = provider_id
            turn["engine_id"] = engine_id
            turn["model_id"] = model_id[:512]
            self._validate("conversation-turn.schema.json", turn)

    def migrate_legacy_gemini_threads(self, *, model_id: str = "select-model") -> int:
        """Pin future turns to OpenCode without rewriting historical turns."""
        migrated = 0
        with self._lock:
            for thread in self._threads.values():
                if thread["provider_id"] == self.LEGACY_GEMINI_PROVIDER_ID or thread["engine_id"] == "gemini":
                    thread["provider_id"] = self.OPENCODE_PROVIDER_ID
                    thread["engine_id"] = "opencode"
                    thread["model_id"] = model_id[:160]
                    thread["updated_at"] = self._now()
                    self._validate("conversation-thread.schema.json", thread)
                    migrated += 1
        return migrated

    def update_turn(self, turn_id: str, status: str, *, failure_code: str | None = None) -> dict[str, Any]:
        with self._lock:
            turn = self._turns.get(turn_id)
            if turn is None:
                raise ThreadStoreError("Turn not found.")
            turn["status"] = status
            turn["updated_at"] = self._now()
            if failure_code:
                turn["failure_code"] = failure_code[:80]
            self._validate("conversation-turn.schema.json", turn)
            return deepcopy(turn)

    def get_turn(self, turn_id: str) -> dict[str, Any]:
        with self._lock:
            turn = deepcopy(self._turns.get(turn_id))
        if turn is None:
            raise ThreadStoreError("Turn not found.")
        return turn

    def add_message(self, turn_id: str, *, role: str, content: str, evidence_refs: list[str] | None = None, summary_of: list[str] | None = None) -> dict[str, Any]:
        with self._lock:
            turn = self._turns.get(turn_id)
            if turn is None:
                raise ThreadStoreError("Turn not found.")
            item = {"message_id": self._id("msg_"), "thread_id": turn["thread_id"], "turn_id": turn_id, "role": role, "created_at": self._now(), "content": content[:200000], "evidence_refs": evidence_refs or [], "visibility": "USER_VISIBLE"}
            if summary_of:
                item["summary_of"] = list(summary_of)
            self._validate("conversation-message.schema.json", item)
            self._messages[item["message_id"]] = item
            turn["message_ids"].append(item["message_id"])
            turn["updated_at"] = item["created_at"]
            return deepcopy(item)

    def messages_for_thread(self, thread_id: str) -> list[dict[str, Any]]:
        with self._lock:
            if thread_id not in self._threads:
                raise ThreadStoreError("Thread not found.")
            return [deepcopy(item) for item in self._messages.values() if item["thread_id"] == thread_id]

    def export_thread(self, thread_id: str) -> dict[str, Any]:
        """Return a portable user-visible transcript without sessions or authorizations."""
        thread = self.get_thread(thread_id)
        turns = []
        messages = {item["message_id"]: item for item in thread["messages"]}
        for turn in thread["turns"]:
            visible = []
            for message_id in turn["message_ids"]:
                item = messages.get(message_id)
                if item and item["visibility"] == "USER_VISIBLE":
                    visible.append({"role": item["role"], "content": item["content"], "evidence_refs": item["evidence_refs"]})
            turns.append({
                "status": turn["status"],
                "provider_id": turn["provider_id"],
                "engine_id": turn["engine_id"],
                "model_id": turn["model_id"],
                "messages": visible,
            })
        return {
            "format": "MNE_BRAIN_CONVERSATION_V2",
            "exported_at": self._now(),
            "thread": {"title": thread["title"], "provider_id": thread["provider_id"], "engine_id": thread["engine_id"], "model_id": thread["model_id"], "permission_mode": thread["permission_mode"]},
            "turns": turns,
            "contains_credentials": False,
            "contains_server_diagnostics": False,
        }

    def import_thread(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict) or payload.get("format") not in {"MNE_BRAIN_CONVERSATION_V1", "MNE_BRAIN_CONVERSATION_V2"}:
            raise ThreadStoreError("Unsupported conversation export format.")
        if set(payload) != {"format", "exported_at", "thread", "turns", "contains_credentials", "contains_server_diagnostics"}:
            raise ThreadStoreError("Conversation export envelope is invalid.")
        if payload.get("contains_credentials") or payload.get("contains_server_diagnostics"):
            raise ThreadStoreError("Sensitive conversation exports are rejected.")
        metadata = payload.get("thread")
        turns = payload.get("turns")
        if not isinstance(metadata, dict) or set(metadata) not in ({"title", "provider_id", "permission_mode"}, {"title", "provider_id", "engine_id", "model_id", "permission_mode"}) or not isinstance(turns, list) or len(turns) > 1000:
            raise ThreadStoreError("Conversation export structure is invalid.")
        legacy_gemini = str(metadata.get("provider_id")) == self.LEGACY_GEMINI_PROVIDER_ID or metadata.get("engine_id") == "gemini"
        active_provider = self.OPENCODE_PROVIDER_ID if legacy_gemini else str(metadata["provider_id"])
        active_engine = "opencode" if legacy_gemini else metadata.get("engine_id")
        active_model = "select-model" if legacy_gemini else metadata.get("model_id")
        thread = self.create_thread(title=str(metadata["title"]), provider_id=active_provider, engine_id=active_engine, model_id=active_model, permission_mode=str(metadata["permission_mode"]))
        for exported_turn in turns:
            v1_keys = {"status", "messages"}
            v2_keys = {"status", "provider_id", "engine_id", "model_id", "messages"}
            keys = set(exported_turn) if isinstance(exported_turn, dict) else set()
            if not isinstance(exported_turn, dict) or (keys != v1_keys and keys != v2_keys) or not isinstance(exported_turn["messages"], list):
                raise ThreadStoreError("Conversation turn is invalid.")
            turn = self.create_turn(thread["thread_id"])
            if set(exported_turn) == v2_keys:
                attribution = {
                    "provider_id": str(exported_turn["provider_id"]),
                    "engine_id": str(exported_turn["engine_id"]),
                    "model_id": str(exported_turn["model_id"]),
                }
            elif legacy_gemini:
                attribution = {
                    "provider_id": self.LEGACY_GEMINI_PROVIDER_ID,
                    "engine_id": "gemini",
                    "model_id": str(metadata.get("model_id") or "auto"),
                }
            else:
                attribution = {
                    "provider_id": str(metadata["provider_id"]),
                    "engine_id": str(metadata.get("engine_id") or self._engine_for_provider(str(metadata["provider_id"]))),
                    "model_id": str(metadata.get("model_id") or "provider-default"),
                }
            self._set_turn_attribution(turn["turn_id"], **attribution)
            for message in exported_turn["messages"]:
                if not isinstance(message, dict) or set(message) != {"role", "content", "evidence_refs"}:
                    raise ThreadStoreError("Conversation message is invalid.")
                if message["role"] not in {"user", "assistant", "system"} or not isinstance(message["content"], str) or len(message["content"]) > 200000:
                    raise ThreadStoreError("Conversation message content is invalid.")
                refs = message["evidence_refs"]
                if not isinstance(refs, list) or len(refs) > 200 or any(not isinstance(item, str) or len(item) > 200 for item in refs):
                    raise ThreadStoreError("Conversation evidence references are invalid.")
                self.add_message(turn["turn_id"], role=message["role"], content=message["content"], evidence_refs=refs)
            status = exported_turn["status"] if exported_turn["status"] in {"COMPLETED", "CANCELLED", "FAILED"} else "COMPLETED"
            self.update_turn(turn["turn_id"], status, failure_code="PROVIDER_UNAVAILABLE" if status == "FAILED" else None)
        return self.get_thread(thread["thread_id"])
