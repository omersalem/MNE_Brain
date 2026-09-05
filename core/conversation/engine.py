"""Codex-like P11 thread/turn/item lifecycle with SSE-safe events."""

from __future__ import annotations

import json
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.conversation.cancellation import CancellationToken, TurnCancelled, TurnTimedOut
from core.conversation.context_builder import ContextBuilder
from core.conversation.event_stream import EventStream
from core.conversation.thread_store import ThreadStore, ThreadStoreError
from core.entity.build_entity_index import EntityIndexBuilder
from core.llm.external_authorization import ExternalAuthorizationError, ExternalAuthorizationManager, ExternalDataPolicy
from core.llm.gateway import ProviderGateway
from core.llm.registry import ProviderRegistry
from core.llm.providers.base import SAFE_PROVIDER_ERRORS
from core.investigation.planner import InvestigationPlanner
from core.observability.diagnostics import DiagnosticStore
from core.tools.broker import ToolBroker
from core.codex.app_server import CODEX_PROVIDER_ID, CodexAppServerError, CodexAppServerHarness
from core.opencode import OPENCODE_PROVIDER_ID, OpenCodeError, OpenCodeRuntime
from core.antigravity import ANTIGRAVITY_PROVIDER_ID, AntigravityCliError, AntigravityHarness


class ConversationEngine:
    _SIMPLE_GREETING = re.compile(
        r"\s*(?:hello|hi|hey|good\s+(?:morning|afternoon|evening))(?:\s+there)?[.!?\s]*\Z",
        re.IGNORECASE,
    )
    _LIVE_VERIFICATION_INTENT = re.compile(
        r"\b(?:live|current|currently|latest|verify|verified|actual|realtime|real-time|right\s+now|check\s+now)\b",
        re.IGNORECASE,
    )
    _IP_FACT_LOOKUP = re.compile(
        r"(?:\bip(?:\s+address)?\s+(?:of|for)\s+\S+|"
        r"\b(?:switch|firewall|fortigate|fmc|ftd|router|gateway|server|host|device|waf|vcenter|vmware|exchange|storage|printer)\b.{0,80}\bip(?:\s+address)?\b)",
        re.IGNORECASE,
    )

    def __init__(self, base_dir: Path, *, gateway: ProviderGateway | None = None, tool_broker: ToolBroker | None = None, codex_harness: CodexAppServerHarness | None = None, opencode_runtime: OpenCodeRuntime | None = None, antigravity_harness: AntigravityHarness | None = None, external_calls_enabled: bool = False, auto_authorize_external_redacted_context: bool = False, storage_dir: Path | None = None):
        self.base_dir = base_dir.resolve()
        self.store = ThreadStore(self.base_dir, storage_dir=storage_dir)
        self.events = EventStream(self.base_dir)
        self.context_builder = ContextBuilder()
        self.entity_index = EntityIndexBuilder(self.base_dir)
        self.registry = gateway.registry if gateway else ProviderRegistry(self.base_dir)
        self.gateway = gateway or ProviderGateway(self.base_dir, registry=self.registry, external_calls_enabled=external_calls_enabled)
        self.tool_broker = tool_broker or ToolBroker(self.base_dir)
        self.external_authorizations = ExternalAuthorizationManager(self.base_dir)
        self.auto_authorize_external_redacted_context = bool(auto_authorize_external_redacted_context)
        self.diagnostics = DiagnosticStore()
        self._tokens: dict[str, CancellationToken] = {}
        self._owner_session_digests: dict[str, str] = {}
        self._active_threads: set[str] = set()
        self._lock = threading.RLock()
        self.codex = codex_harness or CodexAppServerHarness(
            self.base_dir,
            tool_broker=self.tool_broker,
            event_sink=self._codex_event,
            completion_sink=self._codex_completed,
            failure_sink=self._codex_failed,
        )
        self.opencode = opencode_runtime or OpenCodeRuntime(
            self.base_dir,
            tool_broker=self.tool_broker,
            event_sink=self._opencode_event,
            completion_sink=self._opencode_completed,
            failure_sink=self._opencode_failed,
        )
        self.antigravity = antigravity_harness or AntigravityHarness(
            self.base_dir,
            tool_broker=self.tool_broker,
            event_sink=self._antigravity_event,
            completion_sink=self._antigravity_completed,
            failure_sink=self._antigravity_failed,
        )

    def create_thread(self, **kwargs: Any) -> dict[str, Any]:
        profile = self.registry.get(kwargs.get("provider_id", "prv_local_deterministic"))
        kwargs.setdefault("model_id", profile["model_id"])
        return self.store.create_thread(**kwargs)

    def delete_thread(self, thread_id: str) -> bool:
        return self.store.delete_thread(thread_id)

    def import_thread(self, payload: dict[str, Any]) -> dict[str, Any]:
        metadata = payload.get("thread", {}) if isinstance(payload, dict) else {}
        provider_id = str(metadata.get("provider_id", ""))
        self.registry.get(OPENCODE_PROVIDER_ID if provider_id == ThreadStore.LEGACY_GEMINI_PROVIDER_ID or metadata.get("engine_id") == "gemini" else provider_id)
        return self.store.import_thread(payload)

    @staticmethod
    def _validated_evidence(evidence: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
        accepted: list[dict[str, Any]] = []
        unknowns: list[str] = []
        now = datetime.now(timezone.utc)
        for item in evidence:
            if not isinstance(item, dict):
                unknowns.append("A malformed evidence item was excluded.")
                continue
            status = item.get("evidence_status", item.get("status"))
            target = item.get("verification_target", item.get("target"))
            check_id = item.get("verification_check_id", item.get("check_id"))
            outcome = item.get("verification_outcome", item.get("outcome"))
            try:
                observed = datetime.fromisoformat(str(item.get("observed_at", "")).replace("Z", "+00:00"))
            except ValueError:
                observed = datetime.min.replace(tzinfo=timezone.utc)
            attributable = (
                status == "live_verified" and item.get("trust_level") == 5 and item.get("evidence_id")
                and item.get("source") and target and check_id and outcome == "success"
                and observed.tzinfo is not None and 0 <= (now - observed.astimezone(timezone.utc)).total_seconds() <= 900
            )
            if attributable:
                accepted.append(item)
            else:
                unknowns.append(f"Evidence {item.get('evidence_id', 'unknown')} lacked fresh attributable live verification and was excluded.")
        if not accepted and not unknowns:
            unknowns.append("No attributable evidence was supplied for this turn.")
        return accepted, unknowns

    def _documented_baseline(self, prompt: str) -> tuple[list[dict[str, str]], list[str]]:
        """Return a tiny, explicitly non-live context block for one exact entity."""
        matches = self.entity_index.resolve_entity(prompt)
        if len(matches) != 1:
            return [], []
        entity = matches[0]
        source = str(entity.get("canonical_file", ""))
        record = {
            "entity_id": entity.get("entity_id"),
            "name": entity.get("name"),
            "hostname": entity.get("hostname"),
            "fqdn": entity.get("fqdn"),
            "ip": entity.get("ip"),
            "vlan": entity.get("vlan"),
            "knowledge_status": entity.get("knowledge_status", "unverified"),
            "source_file": source,
            "last_verified": entity.get("last_verified"),
        }
        instruction = (
            "Documented workspace baseline for this exact target follows. Answer simple fact lookups "
            "directly and concisely. Treat this as documented context, not current live state, and state "
            "that distinction when it matters: " + json.dumps(record, sort_keys=True, ensure_ascii=False)
        )
        return [{"role": "system", "content": instruction}], [source] if source.startswith("knowledge/") else []

    def _documented_ip_answer(self, prompt: str) -> tuple[str, list[str]] | None:
        """Answer targeted IP lookups deterministically or fail closed without guessing."""
        if not self._IP_FACT_LOOKUP.search(prompt):
            return None
        matches = self.entity_index.resolve_entity(prompt)
        if len(matches) != 1:
            qualifier = "no exact" if not matches else "more than one"
            return (
                f"I cannot provide an IP address because {qualifier} documented entity matches this target. "
                "No IP address was guessed. Please provide the exact site and device type.",
                [],
            )
        entity = matches[0]
        ip = str(entity.get("ip", "")).strip()
        source = str(entity.get("canonical_file", ""))
        sources = [source] if source.startswith("knowledge/") else []
        if not ip:
            return (
                f"The exact documented entity `{entity['entity_id']}` has no recorded IP address. "
                "No IP address was guessed.",
                sources,
            )
        hostname = str(entity.get("hostname", "")).strip() or entity["entity_id"]
        answer = (
            f"Documented baseline: **{entity['name']}** (`{hostname}`) has management IP **`{ip}`**.\n\n"
            f"Source: `{source}`. This was not live-verified in this turn."
        )
        return answer, sources

    def _local_fast_answer(self, prompt: str) -> tuple[str, list[str], str] | None:
        """Return only bounded answers that need neither an AI agent nor a live read."""
        if self._SIMPLE_GREETING.fullmatch(prompt):
            return "Hello! How can I help?", [], "DETERMINISTIC_GREETING"
        if self._LIVE_VERIFICATION_INTENT.search(prompt):
            return None
        # A negative or ambiguous resolver result is not an answer. Let the
        # selected agent investigate instead of turning a fast-path miss into
        # a user-visible rejection.
        if len(self.entity_index.resolve_entity(prompt)) != 1:
            return None
        documented_ip = self._documented_ip_answer(prompt)
        if documented_ip is None:
            return None
        answer, sources = documented_ip
        return answer, sources, "DETERMINISTIC_DOCUMENTED_IP"

    def _build_context(self, messages: list[dict[str, Any]], evidence: list[dict[str, Any]], prompt: str) -> tuple[list[dict[str, str]], dict[str, Any], list[str]]:
        context, meta = self.context_builder.build(messages, evidence)
        documented, sources = self._documented_baseline(prompt)
        if documented:
            context = documented + context
        meta["documented_source_count"] = len(sources)
        return context, meta, sources

    def prepare_external_authorization(self, thread_id: str, *, prompt: str, evidence_context: Any, evidence_sources: list[str], data_classification: str = "INTERNAL_REDACTED", includes_live_evidence: bool = False) -> dict[str, Any]:
        thread = self.store.get_thread(thread_id, include_items=False)
        profile = self.registry.get(thread["provider_id"])
        if profile["classification"] != "EXTERNAL":
            raise ExternalAuthorizationError("The selected provider is local and needs no external authorization.")
        pending_messages = self.store.messages_for_thread(thread_id) + [{"role": "user", "content": prompt, "evidence_refs": []}]
        normalized_evidence = evidence_context if isinstance(evidence_context, list) else []
        context, _, documented_sources = self._build_context(pending_messages, normalized_evidence, prompt)
        sources = sorted(set([*evidence_sources, *documented_sources]))
        item, _ = self.external_authorizations.prepare(thread_id=thread_id, provider_id=profile["provider_id"], model_id=profile["model_id"], prompt=prompt, context={"conversation": context, "evidence": normalized_evidence}, evidence_sources=sources, data_classification=data_classification, includes_live_evidence=includes_live_evidence)
        return item

    def start_turn(self, thread_id: str, *, content: str, external_authorization_id: str | None = None, evidence: list[dict[str, Any]] | None = None, owner_session_digest: str | None = None, run_async: bool = True) -> dict[str, Any]:
        thread = self.store.get_thread(thread_id, include_items=False)
        profile = self.registry.get(thread["provider_id"])
        normalized_evidence = evidence or []
        if profile["provider_id"] in {CODEX_PROVIDER_ID, OPENCODE_PROVIDER_ID, ANTIGRAVITY_PROVIDER_ID}:
            fast_answer = self._local_fast_answer(content)
            if fast_answer is not None:
                if not re.fullmatch(r"[0-9a-f]{64}", owner_session_digest or ""):
                    if profile["provider_id"] == CODEX_PROVIDER_ID:
                        raise CodexAppServerError("Authenticated owner session is required for Codex turns.")
                    if profile["provider_id"] == OPENCODE_PROVIDER_ID:
                        raise OpenCodeError("OPENCODE_AUTH_REQUIRED", "Authenticated owner session is required for OpenCode turns.")
                    raise AntigravityCliError("Authenticated owner session is required for Antigravity turns.")
                return self._start_local_fast_turn(thread, content=content, fast_answer=fast_answer)
        if profile["provider_id"] == CODEX_PROVIDER_ID:
            return self._start_codex_turn(
                thread,
                content=content,
                owner_session_digest=owner_session_digest,
                run_async=run_async,
            )
        if profile["provider_id"] == OPENCODE_PROVIDER_ID:
            return self._start_opencode_turn(
                thread,
                content=content,
                owner_session_digest=owner_session_digest,
                run_async=run_async,
            )
        if profile["provider_id"] == ANTIGRAVITY_PROVIDER_ID:
            return self._start_antigravity_turn(
                thread,
                content=content,
                owner_session_digest=owner_session_digest,
                run_async=run_async,
            )
        if profile["classification"] == "EXTERNAL" and not external_authorization_id:
            if not self.auto_authorize_external_redacted_context or normalized_evidence:
                raise ExternalAuthorizationError("Explicit external-data authorization is required for supplied evidence.")
            authorization = self.prepare_external_authorization(
                thread_id,
                prompt=content,
                evidence_context=[],
                evidence_sources=[f"conversation:{thread_id}"],
                data_classification="INTERNAL_REDACTED",
                includes_live_evidence=False,
            )
            external_authorization_id = authorization["authorization_id"]
        with self._lock:
            if thread_id in self._active_threads:
                raise RuntimeError("TURN_ALREADY_ACTIVE")
            self._active_threads.add(thread_id)
        try:
            turn = self.store.create_turn(thread_id, external_authorization_id=external_authorization_id)
            self.store.add_message(turn["turn_id"], role="user", content=content)
            token = CancellationToken(profile["limits"]["timeout_seconds"])
            with self._lock:
                self._tokens[turn["turn_id"]] = token
                if owner_session_digest:
                    self._owner_session_digests[turn["turn_id"]] = owner_session_digest
            if run_async:
                worker = threading.Thread(target=self._run_turn, args=(turn["turn_id"], content, normalized_evidence), name=f"p11-{turn['turn_id']}", daemon=True)
                worker.start()
            else:
                self._run_turn(turn["turn_id"], content, normalized_evidence)
        except Exception:
            with self._lock:
                self._active_threads.discard(thread_id)
            raise
        return self.store.get_turn(turn["turn_id"])

    def _start_local_fast_turn(self, thread: dict[str, Any], *, content: str, fast_answer: tuple[str, list[str], str]) -> dict[str, Any]:
        """Complete a safe local answer without starting the selected agent process."""
        thread_id = thread["thread_id"]
        with self._lock:
            if thread_id in self._active_threads:
                raise RuntimeError("TURN_ALREADY_ACTIVE")
            self._active_threads.add(thread_id)
        try:
            turn = self.store.create_turn(thread_id)
            self.store.add_message(turn["turn_id"], role="user", content=content)
            turn = self.store.update_turn(turn["turn_id"], "RUNNING")
            answer, sources, answer_mode = fast_answer
            self.events.append(
                thread_id=thread_id, turn_id=turn["turn_id"], provider_id=turn["provider_id"],
                event_type="turn.started", status="RUNNING",
                redacted_payload={
                    "permission_mode": turn["permission_mode"],
                    "execution_path": "LOCAL_DETERMINISTIC_FAST_PATH",
                    "selected_engine": turn["engine_id"],
                },
            )
            self.events.append(
                thread_id=thread_id, turn_id=turn["turn_id"], provider_id=turn["provider_id"],
                event_type="evidence.accepted", status="RUNNING",
                redacted_payload={
                    "accepted": bool(sources),
                    "count": len(sources),
                    "sources": sources,
                    "documented_source_count": len(sources),
                    "unknowns": (["Current live state was not requested or verified."] if sources else []),
                    "answer_mode": answer_mode,
                },
            )
            self.store.add_message(turn["turn_id"], role="assistant", content=answer, evidence_refs=sources)
            self.events.append(
                thread_id=thread_id, turn_id=turn["turn_id"], provider_id=turn["provider_id"],
                event_type="answer.final", status="RUNNING",
                redacted_payload={"text": answer, "answer_mode": answer_mode, "provider_invoked": False},
            )
            completed = self.store.update_turn(turn["turn_id"], "COMPLETED")
            self.events.append(
                thread_id=thread_id, turn_id=turn["turn_id"], provider_id=turn["provider_id"],
                event_type="turn.completed", status="COMPLETED",
                redacted_payload={
                    "answer_chars": len(answer),
                    "answer_mode": answer_mode,
                    "execution_path": "LOCAL_DETERMINISTIC_FAST_PATH",
                    "provider_invoked": False,
                },
            )
            return completed
        finally:
            with self._lock:
                self._active_threads.discard(thread_id)

    def _start_codex_turn(self, thread: dict[str, Any], *, content: str, owner_session_digest: str | None, run_async: bool) -> dict[str, Any]:
        if not re.fullmatch(r"[0-9a-f]{64}", owner_session_digest or ""):
            raise CodexAppServerError("Authenticated owner session is required for Codex turns.")
        thread_id = thread["thread_id"]
        with self._lock:
            if thread_id in self._active_threads:
                raise RuntimeError("TURN_ALREADY_ACTIVE")
            self._active_threads.add(thread_id)
        try:
            turn = self.store.create_turn(thread_id)
            self.store.add_message(turn["turn_id"], role="user", content=content)
            with self._lock:
                self._owner_session_digests[turn["turn_id"]] = owner_session_digest
            worker = threading.Thread(
                target=self._run_codex_turn,
                args=(turn["turn_id"], content, owner_session_digest),
                name=f"codex-{turn['turn_id']}",
                daemon=True,
            )
            if run_async:
                worker.start()
            else:
                worker.run()
            return self.store.get_turn(turn["turn_id"])
        except Exception:
            with self._lock:
                self._active_threads.discard(thread_id)
            raise

    def _run_codex_turn(self, turn_id: str, content: str, owner_session_digest: str) -> None:
        turn = self.store.update_turn(turn_id, "RUNNING")
        self.events.append(
            thread_id=turn["thread_id"], turn_id=turn_id, provider_id=CODEX_PROVIDER_ID,
            event_type="turn.started", status="RUNNING",
            redacted_payload={"permission_mode": turn["permission_mode"], "agent_harness": "CODEX_APP_SERVER"},
        )
        try:
            self.codex.start_turn(
                gui_thread_id=turn["thread_id"], gui_turn_id=turn_id,
                content=content, owner_session_digest=owner_session_digest, permission_mode=turn["permission_mode"],
            )
        except CodexAppServerError:
            self._codex_failed(turn_id, "CODEX_APP_SERVER_UNAVAILABLE")

    def _start_opencode_turn(self, thread: dict[str, Any], *, content: str, owner_session_digest: str | None, run_async: bool) -> dict[str, Any]:
        if not re.fullmatch(r"[0-9a-f]{64}", owner_session_digest or ""):
            raise OpenCodeError("OPENCODE_AUTH_REQUIRED", "Authenticated owner session is required for OpenCode turns.")
        thread_id = thread["thread_id"]
        with self._lock:
            if thread_id in self._active_threads:
                raise RuntimeError("TURN_ALREADY_ACTIVE")
            self._active_threads.add(thread_id)
        try:
            turn = self.store.create_turn(thread_id)
            self.store.add_message(turn["turn_id"], role="user", content=content)
            with self._lock:
                self._owner_session_digests[turn["turn_id"]] = owner_session_digest
            worker = threading.Thread(
                target=self._run_opencode_turn,
                args=(turn["turn_id"], content, owner_session_digest),
                name=f"opencode-{turn['turn_id']}", daemon=True,
            )
            if run_async:
                worker.start()
            else:
                worker.run()
            return self.store.get_turn(turn["turn_id"])
        except Exception:
            with self._lock:
                self._active_threads.discard(thread_id)
            raise

    def _run_opencode_turn(self, turn_id: str, content: str, owner_session_digest: str) -> None:
        turn = self.store.update_turn(turn_id, "RUNNING")
        self.events.append(
            thread_id=turn["thread_id"], turn_id=turn_id, provider_id=OPENCODE_PROVIDER_ID,
            event_type="turn.started", status="RUNNING",
            redacted_payload={"permission_mode": turn["permission_mode"], "agent_harness": "OPENCODE_HTTP_SSE", "model_id": turn["model_id"]},
        )
        try:
            self.opencode.start_turn(
                gui_thread_id=turn["thread_id"], gui_turn_id=turn_id,
                content=content, owner_session_digest=owner_session_digest,
                model_id=turn["model_id"],
                permission_mode=turn["permission_mode"],
            )
        except OpenCodeError as exc:
            self._opencode_failed(turn_id, exc.code)

    def _opencode_event(self, thread_id: str, turn_id: str, event_type: str, payload: dict[str, Any]) -> None:
        if event_type == "tool.approval_required":
            status = "APPROVAL_REQUIRED"
        elif event_type == "tool.proposed":
            status = "AUTOMATIC_READ" if payload.get("status") == "AUTOMATIC_READ" else "RUNNING"
        elif event_type in {"tool.completed", "command.completed"}:
            status = "COMPLETED"
        else:
            status = "RUNNING"
        self.events.append(
            thread_id=thread_id, turn_id=turn_id, provider_id=OPENCODE_PROVIDER_ID,
            event_type=event_type, status=status, redacted_payload=payload,
        )

    def _opencode_completed(self, thread_id: str, turn_id: str, answer: str | None) -> None:
        try:
            if answer:
                self.store.add_message(turn_id, role="assistant", content=answer)
            self.store.update_turn(turn_id, "COMPLETED")
            self.events.append(
                thread_id=thread_id, turn_id=turn_id, provider_id=OPENCODE_PROVIDER_ID,
                event_type="turn.completed", status="COMPLETED",
                redacted_payload={"agent_harness": "OPENCODE_HTTP_SSE", "answer_chars": len(answer or "")},
            )
        finally:
            with self._lock:
                self._owner_session_digests.pop(turn_id, None)
                self._active_threads.discard(thread_id)

    def _opencode_failed(self, turn_id: str, code: str) -> None:
        try:
            turn = self.store.get_turn(turn_id)
        except ThreadStoreError:
            return
        if turn["status"] in {"COMPLETED", "FAILED", "CANCELLED"}:
            return
        cancelled = code == "OPENCODE_TURN_CANCELLED"
        if cancelled:
            self.store.update_turn(turn_id, "CANCELLED")
            self.events.append(thread_id=turn["thread_id"], turn_id=turn_id, provider_id=OPENCODE_PROVIDER_ID, event_type="turn.cancelled", status="CANCELLED", redacted_payload={"reason": "OWNER_CANCELLED"})
        else:
            diagnostic = self.diagnostics.record(code=code, phase="stream", provider_id=OPENCODE_PROVIDER_ID)
            self.store.update_turn(turn_id, "FAILED", failure_code=diagnostic["code"])
            self.events.append(thread_id=turn["thread_id"], turn_id=turn_id, provider_id=OPENCODE_PROVIDER_ID, event_type="turn.failed", status="FAILED", redacted_payload=diagnostic)
        with self._lock:
            self._owner_session_digests.pop(turn_id, None)
            self._active_threads.discard(turn["thread_id"])

    def _codex_event(self, thread_id: str, turn_id: str, event_type: str, payload: dict[str, Any]) -> None:
        if event_type == "tool.approval_required":
            status = "APPROVAL_REQUIRED"
        elif event_type == "tool.proposed":
            candidate = str(payload.get("status", ""))
            status = candidate if candidate in {"AUTOMATIC_READ", "AUTOMATIC_PREPARATION"} else "RUNNING"
        elif event_type in {"tool.completed", "command.completed"}:
            status = "COMPLETED"
        else:
            status = "RUNNING"
        self.events.append(
            thread_id=thread_id, turn_id=turn_id, provider_id=CODEX_PROVIDER_ID,
            event_type=event_type, status=status, redacted_payload=payload,
        )

    def _codex_completed(self, thread_id: str, turn_id: str, answer: str | None) -> None:
        try:
            if answer:
                self.store.add_message(turn_id, role="assistant", content=answer)
            self.store.update_turn(turn_id, "COMPLETED")
            self.events.append(
                thread_id=thread_id, turn_id=turn_id, provider_id=CODEX_PROVIDER_ID,
                event_type="turn.completed", status="COMPLETED",
                redacted_payload={"agent_harness": "CODEX_APP_SERVER", "answer_chars": len(answer or "")},
            )
        finally:
            with self._lock:
                self._owner_session_digests.pop(turn_id, None)
                self._active_threads.discard(thread_id)

    def _codex_failed(self, turn_id: str, code: str) -> None:
        try:
            turn = self.store.get_turn(turn_id)
        except ThreadStoreError:
            return
        if turn["status"] in {"COMPLETED", "FAILED", "CANCELLED"}:
            return
        cancelled = code == "CODEX_TURN_CANCELLED"
        if cancelled:
            self.store.update_turn(turn_id, "CANCELLED")
            self.events.append(
                thread_id=turn["thread_id"], turn_id=turn_id, provider_id=CODEX_PROVIDER_ID,
                event_type="turn.cancelled", status="CANCELLED", redacted_payload={"reason": "OWNER_CANCELLED"},
            )
        else:
            diagnostic = self.diagnostics.record(code=code, phase="stream", provider_id=CODEX_PROVIDER_ID)
            self.store.update_turn(turn_id, "FAILED", failure_code=diagnostic["code"])
            self.events.append(
                thread_id=turn["thread_id"], turn_id=turn_id, provider_id=CODEX_PROVIDER_ID,
                event_type="turn.failed", status="FAILED", redacted_payload=diagnostic,
            )
        with self._lock:
            self._owner_session_digests.pop(turn_id, None)
            self._active_threads.discard(turn["thread_id"])

    def _start_antigravity_turn(self, thread: dict[str, Any], *, content: str, owner_session_digest: str | None, run_async: bool) -> dict[str, Any]:
        if not re.fullmatch(r"[0-9a-f]{64}", owner_session_digest or ""):
            raise AntigravityCliError("Authenticated owner session is required for Antigravity turns.")
        thread_id = thread["thread_id"]
        with self._lock:
            if thread_id in self._active_threads:
                raise RuntimeError("TURN_ALREADY_ACTIVE")
            self._active_threads.add(thread_id)
        try:
            turn = self.store.create_turn(thread_id)
            self.store.add_message(turn["turn_id"], role="user", content=content)
            with self._lock:
                self._owner_session_digests[turn["turn_id"]] = owner_session_digest
            worker = threading.Thread(
                target=self._run_antigravity_turn,
                args=(turn["turn_id"], content, owner_session_digest),
                name=f"antigravity-{turn['turn_id']}",
                daemon=True,
            )
            if run_async:
                worker.start()
            else:
                worker.run()
            return self.store.get_turn(turn["turn_id"])
        except Exception:
            with self._lock:
                self._active_threads.discard(thread_id)
            raise

    def _run_antigravity_turn(self, turn_id: str, content: str, owner_session_digest: str) -> None:
        turn = self.store.update_turn(turn_id, "RUNNING")
        self.events.append(
            thread_id=turn["thread_id"],
            turn_id=turn_id,
            provider_id=ANTIGRAVITY_PROVIDER_ID,
            event_type="turn.started",
            status="RUNNING",
            redacted_payload={"permission_mode": turn["permission_mode"], "agent_harness": "ANTIGRAVITY_CLI", "model_id": turn["model_id"]},
        )
        try:
            self.antigravity.start_turn(
                gui_thread_id=turn["thread_id"],
                gui_turn_id=turn_id,
                content=content,
                owner_session_digest=owner_session_digest,
                model_id=turn["model_id"],
                permission_mode=turn["permission_mode"],
            )
        except Exception as exc:
            self._antigravity_failed(turn_id, f"ANTIGRAVITY_TURN_FAILED")

    def _antigravity_event(self, thread_id: str, turn_id: str, event_type: str, payload: dict[str, Any]) -> None:
        status = "RUNNING"
        if event_type == "tool.approval_required":
            status = "APPROVAL_REQUIRED"
        elif event_type == "tool.proposed":
            status = "AUTOMATIC_READ" if payload.get("status") == "AUTOMATIC_READ" else "RUNNING"
        elif event_type in {"tool.completed", "command.completed", "answer.completed"}:
            status = "COMPLETED"
        self.events.append(
            thread_id=thread_id,
            turn_id=turn_id,
            provider_id=ANTIGRAVITY_PROVIDER_ID,
            event_type=event_type,
            status=status,
            redacted_payload=payload,
        )

    def _antigravity_completed(self, turn_id: str, answer: str | None) -> None:
        try:
            turn = self.store.get_turn(turn_id)
            thread_id = turn["thread_id"]
            if answer:
                self.store.add_message(turn_id, role="assistant", content=answer)
            self.store.update_turn(turn_id, "COMPLETED")
            self.events.append(
                thread_id=thread_id,
                turn_id=turn_id,
                provider_id=ANTIGRAVITY_PROVIDER_ID,
                event_type="turn.completed",
                status="COMPLETED",
                redacted_payload={"agent_harness": "ANTIGRAVITY_CLI", "answer_chars": len(answer or "")},
            )
        finally:
            with self._lock:
                self._owner_session_digests.pop(turn_id, None)
                self._active_threads.discard(turn["thread_id"])

    def _antigravity_failed(self, turn_id: str, code: str) -> None:
        try:
            turn = self.store.get_turn(turn_id)
        except ThreadStoreError:
            return
        if turn["status"] in {"COMPLETED", "FAILED", "CANCELLED"}:
            return
        cancelled = code == "ANTIGRAVITY_TURN_CANCELLED"
        if cancelled:
            self.store.update_turn(turn_id, "CANCELLED")
            self.events.append(
                thread_id=turn["thread_id"],
                turn_id=turn_id,
                provider_id=ANTIGRAVITY_PROVIDER_ID,
                event_type="turn.cancelled",
                status="CANCELLED",
                redacted_payload={"reason": "OWNER_CANCELLED"},
            )
        else:
            diagnostic = self.diagnostics.record(code=code, phase="stream", provider_id=ANTIGRAVITY_PROVIDER_ID)
            self.store.update_turn(turn_id, "FAILED", failure_code=diagnostic["code"])
            self.events.append(
                thread_id=turn["thread_id"],
                turn_id=turn_id,
                provider_id=ANTIGRAVITY_PROVIDER_ID,
                event_type="turn.failed",
                status="FAILED",
                redacted_payload=diagnostic,
            )
        with self._lock:
            self._owner_session_digests.pop(turn_id, None)
            self._active_threads.discard(turn["thread_id"])

    def _run_turn(self, turn_id: str, content: str, evidence: list[dict[str, Any]]) -> None:
        turn = self.store.update_turn(turn_id, "RUNNING")
        token = self._tokens[turn_id]
        self.events.append(thread_id=turn["thread_id"], turn_id=turn_id, provider_id=turn["provider_id"], event_type="turn.started", status="RUNNING", redacted_payload={"permission_mode": turn["permission_mode"]})
        try:
            messages = self.store.messages_for_thread(turn["thread_id"])
            accepted_evidence, unknowns = self._validated_evidence(evidence)
            context, meta, documented_sources = self._build_context(messages, accepted_evidence, content)
            profile = self.registry.get(turn["provider_id"])
            if profile["classification"] == "EXTERNAL":
                manager = self.external_authorizations
                item = manager.inspect(turn["external_authorization_id"])
                sanitized_context = ExternalDataPolicy.sanitize({"conversation": context, "evidence": accepted_evidence})
                expected = {
                    "thread_id": turn["thread_id"],
                    "provider_id": profile["provider_id"],
                    "model_id": profile["model_id"],
                    "context_digest": manager.digest({"context": sanitized_context, "sources": item["evidence_sources"]}),
                    "prompt_digest": manager.digest(ExternalDataPolicy.redact_text(content)),
                    "redaction_digest": manager.digest(sanitized_context),
                }
                manager.authorize(turn["external_authorization_id"], expected=expected)
            self.events.append(
                thread_id=turn["thread_id"], turn_id=turn_id, provider_id=turn["provider_id"],
                event_type="evidence.accepted", status="RUNNING",
                redacted_payload={
                    "accepted": bool(accepted_evidence),
                    "count": len(accepted_evidence),
                    "sources": [item.get("source") for item in accepted_evidence] + documented_sources,
                    "documented_source_count": len(documented_sources),
                    "unknowns": (["Documented baseline is available, but current live state remains unverified."] if documented_sources and unknowns == ["No attributable evidence was supplied for this turn."] else unknowns),
                },
            )
            documented_ip = self._documented_ip_answer(content)
            if documented_ip is not None and turn["permission_mode"] in {"LIVE_READ", "OWNER_AUTONOMOUS", "OWNER_FULL_CONTROL"}:
                matches = self.entity_index.resolve_entity(content)
                live_arguments = (
                    self.tool_broker.live_read_arguments_for_entity(matches[0]["entity_id"])
                    if len(matches) == 1
                    else None
                )
                if live_arguments is not None:
                    call = self.tool_broker.propose(
                        thread_id=turn["thread_id"],
                        turn_id=turn_id,
                        tool_name="mne.prepare_live_read",
                        arguments=live_arguments,
                        permission_mode=turn["permission_mode"],
                    )
                    entity = matches[0]
                    if turn["permission_mode"] in {"OWNER_AUTONOMOUS", "OWNER_FULL_CONTROL"} and self._owner_session_digests.get(turn_id):
                        self.events.append(
                            thread_id=turn["thread_id"], turn_id=turn_id, provider_id=turn["provider_id"],
                            event_type="tool.proposed", status="AUTOMATIC_READ",
                            redacted_payload={"tool_call_id": call["tool_call_id"], "tool_name": call["tool_name"], "argument_digest": call["argument_digest"], "status": "AUTOMATIC_READ"},
                        )
                        self.events.append(
                            thread_id=turn["thread_id"], turn_id=turn_id, provider_id=turn["provider_id"],
                            event_type="tool.started", status="RUNNING",
                            redacted_payload={"tool_call_id": call["tool_call_id"], "tool_name": call["tool_name"], "mode": "AUTOMATIC_READ"},
                        )
                        result = self.tool_broker.run_owner_autonomous_live_read(
                            live_arguments,
                            owner_session_digest=self._owner_session_digests[turn_id],
                            tool_call_id=call["tool_call_id"],
                        )
                        self.events.append(
                            thread_id=turn["thread_id"], turn_id=turn_id, provider_id=turn["provider_id"],
                            event_type="tool.completed", status="COMPLETED",
                            redacted_payload={"tool_call_id": call["tool_call_id"], "tool_name": call["tool_name"], "result": result},
                        )
                        answer, answer_sources = documented_ip
                        if result.get("live_verified"):
                            answer += "\n\nLive check: **verified now** through the exact pinned read-only binding."
                            answer_sources = [*answer_sources, result["evidence"]["evidence_id"]]
                        else:
                            answer += f"\n\nLive check attempted but did not verify the current state (`{result.get('status', 'FAILED')}`)."
                        self.events.append(thread_id=turn["thread_id"], turn_id=turn_id, provider_id=turn["provider_id"], event_type="answer.delta", status="RUNNING", redacted_payload={"text": answer})
                        self.store.add_message(turn_id, role="assistant", content=answer, evidence_refs=answer_sources)
                        self.store.update_turn(turn_id, "COMPLETED")
                        meta["answer_mode"] = "OWNER_FULL_CONTROL_LIVE_READ"
                        self.events.append(thread_id=turn["thread_id"], turn_id=turn_id, provider_id=turn["provider_id"], event_type="turn.completed", status="COMPLETED", redacted_payload={"context": meta, "answer_chars": len(answer)})
                        return
                    answer = (
                        f"A governed P7 live read is ready for **{entity['name']}** "
                        f"(`{entity['entity_id']}`) at exact documented target **`{live_arguments['target']}`**.\n\n"
                        "Review the proposal below, copy the exact server phrase, approve it, and then run the single read-only check. "
                        "No device connection has been made yet."
                    )
                    self.events.append(
                        thread_id=turn["thread_id"], turn_id=turn_id, provider_id=turn["provider_id"],
                        event_type="tool.proposed", status="APPROVAL_REQUIRED",
                        redacted_payload={
                            "tool_call_id": call["tool_call_id"],
                            "tool_name": call["tool_name"],
                            "argument_digest": call["argument_digest"],
                            "status": call["status"],
                        },
                    )
                    self.events.append(
                        thread_id=turn["thread_id"], turn_id=turn_id, provider_id=turn["provider_id"],
                        event_type="answer.delta", status="RUNNING", redacted_payload={"text": answer},
                    )
                    self.store.add_message(turn_id, role="assistant", content=answer, evidence_refs=documented_ip[1])
                    self.store.update_turn(turn_id, "COMPLETED")
                    meta["answer_mode"] = "P7_EXACT_LIVE_READ_PROPOSAL"
                    self.events.append(
                        thread_id=turn["thread_id"], turn_id=turn_id, provider_id=turn["provider_id"],
                        event_type="turn.completed", status="COMPLETED",
                        redacted_payload={"context": meta, "answer_chars": len(answer)},
                    )
                    return
            if documented_ip is not None:
                answer, answer_sources = documented_ip
                meta["answer_mode"] = "DETERMINISTIC_DOCUMENTED_IP"
                self.events.append(
                    thread_id=turn["thread_id"], turn_id=turn_id, provider_id=turn["provider_id"],
                    event_type="answer.delta", status="RUNNING", redacted_payload={"text": answer},
                )
                self.store.add_message(turn_id, role="assistant", content=answer, evidence_refs=answer_sources)
                self.store.update_turn(turn_id, "COMPLETED")
                self.events.append(
                    thread_id=turn["thread_id"], turn_id=turn_id, provider_id=turn["provider_id"],
                    event_type="turn.completed", status="COMPLETED",
                    redacted_payload={"context": meta, "answer_chars": len(answer)},
                )
                return
            chunks: list[str] = []
            provider_tools = self.tool_broker.registry.provider_tools(self.tool_broker.permissions.modes[turn["permission_mode"]])
            auto_read_tools = {"workspace.list", "workspace.search", "workspace.read", "workspace.status", "workspace.diff", "mne.build_evidence", "mne.plan_investigation", "owner_direct.discover", "owner_direct.identity_audit"}
            auto_prepare_tools = {"workspace.prepare_patch", "workspace.run_validator", "workspace.prepare_rollback", "p10.prepare", "p10.prepare_critical", "owner_direct.prepare_write"}
            round_context = list(context)
            investigation_plan = InvestigationPlanner(self.base_dir).plan(content)
            if investigation_plan["candidates"] and turn["permission_mode"] in {"LIVE_READ", "OWNER_AUTONOMOUS", "OWNER_FULL_CONTROL", "INFRASTRUCTURE_WRITE"}:
                plan_instruction = (
                    "Server-generated governed investigation plan follows. These are the only valid live-read candidates for this question. "
                    "For a current fact or policy lookup, use mne.prepare_live_read for each essential candidate before answering; do not substitute workspace search for an available live check. "
                    "Use no more than three live checks. Explain failures and distinguish live facts from inference. Plan: "
                    + json.dumps(investigation_plan, ensure_ascii=False, sort_keys=True)
                )
                round_context = [{"role": "system", "content": plan_instruction}, *round_context]
                self.events.append(
                    thread_id=turn["thread_id"], turn_id=turn_id, provider_id=turn["provider_id"],
                    event_type="investigation.planned", status="RUNNING",
                    redacted_payload={
                        "intent": investigation_plan["intent"],
                        "candidate_count": len(investigation_plan["candidates"]),
                        "subject_ips": investigation_plan["subject_ips"],
                        "writes_allowed": False,
                    },
                )
            automatic_steps = 0
            previous_automatic_tool = ""
            same_tool_streak = 0
            force_text_only = False
            live_evidence_refs: list[str] = []
            for tool_step in range(8):
                completed = False
                automatic_results: list[dict[str, Any]] = []
                automatic_tool_names: list[str] = []
                offered_tools = [] if force_text_only else provider_tools
                for provider_event in self.gateway.stream(turn["provider_id"], round_context, tools=offered_tools, cancellation_check=token.checkpoint):
                    token.checkpoint()
                    if provider_event.event_type == "text_delta":
                        text = str(provider_event.payload.get("text", ""))
                        chunks.append(text)
                        self.events.append(thread_id=turn["thread_id"], turn_id=turn_id, provider_id=turn["provider_id"], event_type="answer.delta", status="RUNNING", redacted_payload={"text": text})
                    elif provider_event.event_type == "tool_proposal":
                        arguments = provider_event.payload.get("arguments", {})
                        if isinstance(arguments, str):
                            arguments = json.loads(arguments)
                        try:
                            call = self.tool_broker.propose(
                                thread_id=turn["thread_id"], turn_id=turn_id,
                                tool_name=str(provider_event.payload.get("name", "")), arguments=arguments,
                                permission_mode=turn["permission_mode"],
                            )
                        except Exception as exc:
                            raise RuntimeError("TOOL_PROPOSAL_REJECTED") from exc
                        automatic = turn["permission_mode"] in {"OWNER_DIRECT", "OWNER_AUTONOMOUS", "OWNER_FULL_CONTROL"} and (
                            call["tool_name"] in auto_read_tools or (
                                call["tool_name"] == "mne.prepare_live_read" and self._owner_session_digests.get(turn_id)
                            ) or call["tool_name"] in auto_prepare_tools
                        )
                        automatic_status = "AUTOMATIC_PREPARATION" if call["tool_name"] in auto_prepare_tools else "AUTOMATIC_READ"
                        self.events.append(
                            thread_id=turn["thread_id"], turn_id=turn_id, provider_id=turn["provider_id"],
                            event_type="tool.proposed", status=automatic_status if automatic else "APPROVAL_REQUIRED",
                            redacted_payload={"tool_call_id": call["tool_call_id"], "tool_name": call["tool_name"], "argument_digest": call["argument_digest"], "status": automatic_status if automatic else call["status"]},
                        )
                        if automatic:
                            automatic_tool_names.append(call["tool_name"])
                            self.events.append(thread_id=turn["thread_id"], turn_id=turn_id, provider_id=turn["provider_id"], event_type="tool.started", status="RUNNING", redacted_payload={"tool_call_id": call["tool_call_id"], "tool_name": call["tool_name"], "mode": automatic_status})
                            try:
                                if call["tool_name"] == "mne.prepare_live_read":
                                    result = self.tool_broker.run_owner_autonomous_live_read(arguments, owner_session_digest=self._owner_session_digests[turn_id], tool_call_id=call["tool_call_id"])
                                    automatic_result = {"tool_call_id": call["tool_call_id"], "status": result["status"], "result": result}
                                    evidence_item = result.get("evidence") if isinstance(result, dict) else None
                                    if isinstance(evidence_item, dict) and evidence_item.get("evidence_id"):
                                        live_evidence_refs.append(str(evidence_item["evidence_id"]))
                                        self.events.append(
                                            thread_id=turn["thread_id"], turn_id=turn_id, provider_id=turn["provider_id"],
                                            event_type="evidence.accepted", status="RUNNING",
                                            redacted_payload={
                                                "accepted": True,
                                                "count": 1,
                                                "sources": [evidence_item.get("source_file")],
                                                "documented_source_count": len(documented_sources),
                                                "unknowns": [],
                                                "append": True,
                                            },
                                        )
                                else:
                                    automatic_result = self.tool_broker.invoke(
                                        call["tool_call_id"],
                                        owner_session_digest=self._owner_session_digests.get(turn_id),
                                    )
                                automatic_results.append(automatic_result)
                            except Exception as exc:
                                raise RuntimeError("TOOL_EXECUTION_FAILED") from exc
                            self.events.append(thread_id=turn["thread_id"], turn_id=turn_id, provider_id=turn["provider_id"], event_type="tool.completed", status="COMPLETED", redacted_payload={"tool_call_id": call["tool_call_id"], "tool_name": call["tool_name"], "result": automatic_result.get("result")})
                    elif provider_event.event_type == "failed":
                        code = str(provider_event.payload.get("code", "PROVIDER_UNAVAILABLE"))
                        raise RuntimeError(code if code in SAFE_PROVIDER_ERRORS else "PROVIDER_UNAVAILABLE")
                    elif provider_event.event_type == "completed":
                        completed = True
                if not completed:
                    raise RuntimeError("PROVIDER_STREAM_INCOMPLETE")
                if not automatic_results:
                    break
                for automatic_tool_name in automatic_tool_names:
                    automatic_steps += 1
                    same_tool_streak = same_tool_streak + 1 if automatic_tool_name == previous_automatic_tool else 1
                    previous_automatic_tool = automatic_tool_name
                force_text_only = (
                    any(name in auto_prepare_tools for name in automatic_tool_names)
                    or same_tool_streak >= 2
                    or automatic_steps >= 4
                )
                safe_result = ExternalDataPolicy.sanitize(automatic_results[0] if len(automatic_results) == 1 else automatic_results)
                continuation = (
                    " Final response required now: do not request another tool. Answer from the collected results, or state clearly that the requested fact is unknown."
                    if force_text_only else
                    " Use a different tool only if it is essential; otherwise answer now."
                )
                round_context = [*round_context, {"role": "system", "content": "Automatic read-only tool result. Cite its source/path when present, distinguish documented from live state, and never invent missing values: " + json.dumps(safe_result, ensure_ascii=False, sort_keys=True)[:200000] + continuation}]
            else:
                raise RuntimeError("TOOL_STEP_LIMIT_REACHED")
            answer = "".join(chunks).strip()
            if answer:
                self.store.add_message(turn_id, role="assistant", content=answer, evidence_refs=[str(item.get("evidence_id")) for item in accepted_evidence if item.get("evidence_id")] + live_evidence_refs)
            self.store.update_turn(turn_id, "COMPLETED")
            self.events.append(thread_id=turn["thread_id"], turn_id=turn_id, provider_id=turn["provider_id"], event_type="turn.completed", status="COMPLETED", redacted_payload={"context": meta, "answer_chars": len(answer)})
        except TurnCancelled:
            self.store.update_turn(turn_id, "CANCELLED")
            self.events.append(thread_id=turn["thread_id"], turn_id=turn_id, provider_id=turn["provider_id"], event_type="turn.cancelled", status="CANCELLED", redacted_payload={"reason": "OWNER_CANCELLED"})
        except TurnTimedOut:
            diagnostic = self.diagnostics.record(code="PROVIDER_TIMEOUT", phase="stream", provider_id=turn["provider_id"])
            self.store.update_turn(turn_id, "FAILED", failure_code=diagnostic["code"])
            self.events.append(thread_id=turn["thread_id"], turn_id=turn_id, provider_id=turn["provider_id"], event_type="turn.failed", status="FAILED", redacted_payload=diagnostic)
        except Exception as exc:
            candidate = str(exc)
            if candidate not in SAFE_PROVIDER_ERRORS:
                candidate = "PROVIDER_RESPONSE_INVALID" if isinstance(exc, (json.JSONDecodeError, TypeError, ValueError)) else "PROVIDER_UNAVAILABLE"
            phase = "tool" if candidate == "TOOL_PROPOSAL_REJECTED" else "stream"
            diagnostic = self.diagnostics.record(code=candidate, phase=phase, provider_id=turn["provider_id"])
            self.store.update_turn(turn_id, "FAILED", failure_code=diagnostic["code"])
            self.events.append(thread_id=turn["thread_id"], turn_id=turn_id, provider_id=turn["provider_id"], event_type="turn.failed", status="FAILED", redacted_payload=diagnostic)
        finally:
            with self._lock:
                self._tokens.pop(turn_id, None)
                self._owner_session_digests.pop(turn_id, None)
                self._active_threads.discard(turn["thread_id"])

    def cancel(self, turn_id: str) -> dict[str, Any]:
        turn = self.store.get_turn(turn_id)
        if turn["provider_id"] == CODEX_PROVIDER_ID:
            self.codex.cancel(turn_id)
            return self.store.get_turn(turn_id)
        if turn["provider_id"] == OPENCODE_PROVIDER_ID:
            self.opencode.cancel(turn_id)
            self._opencode_failed(turn_id, "OPENCODE_TURN_CANCELLED")
            return self.store.get_turn(turn_id)
        if turn["provider_id"] == ANTIGRAVITY_PROVIDER_ID:
            self.antigravity.cancel_turn(turn_id)
            self._antigravity_failed(turn_id, "ANTIGRAVITY_TURN_CANCELLED")
            return self.store.get_turn(turn_id)
        with self._lock:
            token = self._tokens.get(turn_id)
        if token is None:
            return self.store.get_turn(turn_id)
        token.cancel()
        return self.store.get_turn(turn_id)
