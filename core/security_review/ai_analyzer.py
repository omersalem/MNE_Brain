"""
Security AI Analyzer for MNE_Brain Release 2.
Coordinates Codex App Server and Antigravity CLI analysis runs, concurrent multi-model investigations,
result normalization conforming to security-analysis-result.schema.json, and interactive chat handoffs.
"""

from __future__ import annotations

import concurrent.futures
import json
import logging
import re
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from core.antigravity import ANTIGRAVITY_PROVIDER_ID, DEFAULT_ANTIGRAVITY_MODEL
from core.codex.app_server import CODEX_PROVIDER_ID
from core.security_review.analysis_compare import SecurityAnalysisComparator
from core.security_review.analysis_pack import SecurityAnalysisPackBuilder
from core.security_review.contracts import validate_contract
from core.security_review.run_store import SecurityReviewRunStore

logger = logging.getLogger(__name__)


def _extract_json_block(text: str) -> Optional[Dict[str, Any]]:
    """Extracts a valid JSON object from model output, handling markdown blocks."""
    if not text or not text.strip():
        return None

    # 1. Try markdown code block
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass

    # 2. Try first outer curly braces
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start : end + 1]
        try:
            return json.loads(candidate)
        except Exception:
            pass

    # 3. Direct parse attempt
    try:
        parsed = json.loads(text.strip())
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    return None


class SecurityAIAnalyzer:
    """Orchestrates single and dual AI analysis of security runs and incidents."""

    def __init__(
        self,
        run_store: Optional[SecurityReviewRunStore] = None,
        pack_builder: Optional[SecurityAnalysisPackBuilder] = None,
        comparator: Optional[SecurityAnalysisComparator] = None,
        conversation_engine: Optional[Any] = None,
        codex_invoker: Optional[Callable[[str, Dict[str, Any]], str]] = None,
        antigravity_invoker: Optional[Callable[[str, Dict[str, Any]], str]] = None,
        clock: Optional[Callable[[], datetime]] = None,
    ):
        self.run_store = run_store or SecurityReviewRunStore()
        self.pack_builder = pack_builder or SecurityAnalysisPackBuilder(run_store=self.run_store)
        self.comparator = comparator or SecurityAnalysisComparator()
        self.conversation_engine = conversation_engine
        self.codex_invoker = codex_invoker
        self.antigravity_invoker = antigravity_invoker
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self._lock = threading.Lock()
        self._results: Dict[str, Dict[str, Any]] = {}
        self._events: Dict[str, List[Dict[str, Any]]] = {}

    def _generate_analysis_id(self, engine: str) -> str:
        timestamp = int(time.time())
        unique = uuid.uuid4().hex[:6]
        eng_tag = engine.lower()[:3]
        return f"an-{eng_tag}-{timestamp}-{unique}"

    def emit_event(
        self,
        analysis_id: str,
        event_type: str,
        data: Dict[str, Any],
        progress_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None,
    ) -> None:
        """Records an SSE-friendly progress event and dispatches to optional progress callback."""
        if analysis_id not in self._events:
            self._events[analysis_id] = []
        evt = {
            "analysis_id": analysis_id,
            "event_type": event_type,
            "timestamp": self.clock().isoformat(),
            "data": data,
        }
        self._events[analysis_id].append(evt)
        logger.debug("Analysis event [%s] %s: %s", analysis_id, event_type, data)
        if progress_callback:
            try:
                progress_callback(event_type, data)
            except Exception:
                pass

    def get_events(self, analysis_id: str) -> List[Dict[str, Any]]:
        return list(self._events.get(analysis_id, []))

    def _build_instruction_prompt(self, pack: Dict[str, Any]) -> str:
        """Builds a focused instruction prompt embedding the analysis pack."""
        pack_json = json.dumps(pack, ensure_ascii=False, separators=(",", ":"))
        return (
            "You are a Senior Infrastructure Security Engineer analyzing cybersecurity incident telemetry for MNE_Brain.\n\n"
            "Here is the standardized Security Analysis Pack containing verified telemetry and documented infrastructure baseline:\n\n"
            f"<SECURITY_ANALYSIS_PACK>\n{pack_json}\n</SECURITY_ANALYSIS_PACK>\n\n"
            "Task Instructions:\n"
            "1. Use the supplied pack as your primary run evidence.\n"
            "2. Analyze the supplied telemetry, matching runbooks, and canonical entities contained in the pack.\n"
            "3. Separate observed facts, root-cause hypotheses, and missing operational evidence.\n"
            "4. Return strictly a single valid JSON object conforming to this schema:\n"
            "{\n"
            '  "plain_summary": "Concise executive overview of the security situation",\n'
            '  "confidence": 0.85,\n'
            '  "affected_systems": ["list of hostnames or IP addresses"],\n'
            '  "affected_users": ["list of usernames or accounts"],\n'
            '  "affected_branches": ["list of sites or branch names"],\n'
            '  "affected_services": ["list of protocols or services"],\n'
            '  "ranked_hypotheses": [\n'
            '    {\n'
            '      "hypothesis": "Description of threat or operational cause",\n'
            '      "likelihood": "HIGH",\n'  # HIGH, MEDIUM, LOW, UNKNOWN
            '      "explanation": "Technical reasoning citing observed logs"\n'
            '    }\n'
            '  ],\n'
            '  "observations": {\n'
            '    "supporting": ["Observed facts supporting the hypothesis"],\n'
            '    "contradicting": ["Observed facts arguing against alternate explanations"]\n'
            '  },\n'
            '  "missing_evidence": ["Crucial logs or checks not yet available"],\n'
            '  "recommended_diagnostics": ["Specific CLI or GUI verification checks to run next"],\n'
            '  "immediate_actions": ["Immediate containment or mitigation steps"],\n'
            '  "long_term_actions": ["Post-incident hardening measures"],\n'
            '  "relevant_steps": {\n'
            '    "cli": ["CLI command lines"],\n'
            '    "gui": ["GUI navigation paths"]\n'
            '  },\n'
            '  "source_references": ["List of source files or incident fingerprints cited"],\n'
            '  "warnings": []\n'
            "}\n\n"
            "Output only the JSON structure inside ```json ... ``` code fence."
        )

    def _execute_single_engine(
        self,
        analysis_id: str,
        engine: str,
        model: Optional[str],
        pack: Dict[str, Any],
        owner_session_digest: Optional[str] = None,
        progress_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        """Executes analysis against a single engine (Codex or Antigravity) and normalizes output."""
        engine_lower = engine.lower()
        provider_id = CODEX_PROVIDER_ID if engine_lower == "codex" else ANTIGRAVITY_PROVIDER_ID
        actual_model = model or ("chatgpt" if engine_lower == "codex" else DEFAULT_ANTIGRAVITY_MODEL)
        created_at = self.clock().isoformat()

        self.emit_event(analysis_id, "analysis.started", {
            "engine": engine_lower,
            "provider": provider_id,
            "model": actual_model,
            "target_type": pack.get("target_type"),
        }, progress_callback=progress_callback)

        prompt = self._build_instruction_prompt(pack)
        raw_output = ""
        status = "COMPLETED"
        error_msg: Optional[str] = None

        try:

            if engine_lower == "codex":
                if self.codex_invoker:
                    raw_output = self.codex_invoker(prompt, pack)
                elif self.conversation_engine and hasattr(self.conversation_engine, "codex"):
                    raw_output = self._invoke_via_conversation_engine("codex", prompt, pack, actual_model, owner_session_digest)
                else:
                    raise RuntimeError("AI analysis provider 'codex' is not available: conversation engine or provider adapter is not configured.")
            else:  # Antigravity
                if self.antigravity_invoker:
                    raw_output = self.antigravity_invoker(prompt, pack)
                elif self.conversation_engine and hasattr(self.conversation_engine, "antigravity"):
                    raw_output = self._invoke_via_conversation_engine("antigravity", prompt, pack, actual_model, owner_session_digest)
                else:
                    raise RuntimeError("AI analysis provider 'antigravity' is not available: conversation engine or provider adapter is not configured.")
        except Exception as exc:
            logger.error("AI analysis engine %s invocation failed: %s", engine, exc, exc_info=True)
            status = "FAILED"
            error_msg = str(exc)
            raw_output = ""

        completed_at = self.clock().isoformat()
        normalized = self._normalize_result(
            analysis_id=analysis_id,
            engine=engine_lower,
            provider_id=provider_id,
            model=actual_model,
            pack=pack,
            raw_output=raw_output,
            status=status,
            error_msg=error_msg,
            created_at=created_at,
            completed_at=completed_at,
        )

        self.run_store.save_analysis(normalized)
        self.emit_event(
            analysis_id,
            "analysis.completed" if normalized["status"] != "FAILED" else "analysis.failed",
            {
                "analysis_id": analysis_id,
                "status": normalized["status"],
                "confidence": normalized.get("confidence", 0.0),
                "summary": normalized.get("plain_summary", "")[:200],
            },
            progress_callback=progress_callback,
        )
        return normalized

    def _invoke_via_conversation_engine(
        self,
        engine: str,
        prompt: str,
        pack: Dict[str, Any],
        model: str,
        owner_session_digest: Optional[str],
        timeout: float = 300.0,
    ) -> str:
        """Calls the conversation engine thread/turn pipeline synchronously, waiting for completion."""
        provider_id = CODEX_PROVIDER_ID if engine == "codex" else ANTIGRAVITY_PROVIDER_ID
        digest = owner_session_digest or ("0" * 64)
        thread = self.conversation_engine.create_thread(
            title=f"Security Review Analysis ({engine.upper()})",
            provider_id=provider_id,
            engine_id=engine,
            model_id=model,
            permission_mode="OWNER_DIRECT",
        )
        thread_id = thread["thread_id"]
        turn = self.conversation_engine.start_preloaded_turn(
            thread_id=thread_id,
            content=prompt,
            preloaded_context=pack,
            owner_session_digest=digest,
            run_async=False,
        )
        turn_id = turn.get("turn_id") if isinstance(turn, dict) else getattr(turn, "turn_id", None)

        # Wait for the actual conversation turn to reach COMPLETED, FAILED, CANCELLED, or timeout
        if turn_id and hasattr(self.conversation_engine, "store") and hasattr(self.conversation_engine.store, "get_turn"):
            start_time = time.time()
            poll_interval = 0.05
            terminal_states = {"COMPLETED", "FAILED", "CANCELLED"}
            current_status = None
            while time.time() - start_time < timeout:
                try:
                    current_turn = self.conversation_engine.store.get_turn(turn_id)
                    current_status = current_turn.get("status")
                    if current_status in terminal_states:
                        break
                except Exception:
                    pass
                time.sleep(poll_interval)
                if poll_interval < 0.5:
                    poll_interval *= 1.5

            if current_status in ("FAILED", "CANCELLED"):
                current_turn = self.conversation_engine.store.get_turn(turn_id) if hasattr(self.conversation_engine, "store") else None
                failure_code = (current_turn.get("failure_code") if current_turn else None) or current_status
                raise RuntimeError(f"Turn {turn_id} failed with status {current_status} ({failure_code})")
            if current_status not in terminal_states:
                raise TimeoutError(f"Turn {turn_id} timed out after {timeout} seconds (last status: {current_status})")

        # Fetch the assistant message from turn
        messages = self.conversation_engine.store.messages_for_thread(thread_id)
        for msg in reversed(messages):
            if msg.get("role") == "assistant":
                content = str(msg.get("content", ""))
                if content.strip():
                    return content
        raise RuntimeError(f"Turn {turn_id} completed but no assistant message was returned for thread {thread_id}")

    def _normalize_result(
        self,
        analysis_id: str,
        engine: str,
        provider_id: str,
        model: str,
        pack: Dict[str, Any],
        raw_output: str,
        status: str,
        error_msg: Optional[str],
        created_at: str,
        completed_at: str,
    ) -> Dict[str, Any]:
        """Validates and maps output strictly to security-analysis-result.schema.json."""
        parsed = _extract_json_block(raw_output) if raw_output else None

        if status == "FAILED" or error_msg:
            return {
                "analysis_id": analysis_id,
                "pack_id": pack.get("pack_id"),
                "run_id": pack.get("run_id") if pack.get("run_id") != "NONE" else None,
                "incident_fingerprint": (pack.get("incident_fingerprints") or [None])[0],
                "provider": provider_id,
                "engine": engine,
                "model": model,
                "created_at": created_at,
                "completed_at": completed_at,
                "status": "FAILED",
                "plain_summary": f"Analysis execution failed: {error_msg or 'No response from model.'}",
                "confidence": 0.0,
                "affected_systems": [],
                "affected_users": [],
                "affected_branches": [],
                "affected_services": [],
                "ranked_hypotheses": [],
                "observations": {"supporting": [], "contradicting": []},
                "missing_evidence": [],
                "recommended_diagnostics": [],
                "immediate_actions": [],
                "long_term_actions": [],
                "relevant_steps": {"cli": [], "gui": []},
                "source_references": pack.get("sources", []),
                "warnings": [error_msg] if error_msg else [],
            }

        # Handle partial or unstructured text
        actual_status = "COMPLETED"
        warnings: List[str] = []
        if parsed is None:
            actual_status = "PARTIAL"
            warnings.append("Model response was unstructured text; partial summary populated.")
            plain_summary = raw_output.strip()[:1500] if raw_output else "Partial response received."
            parsed = {
                "plain_summary": plain_summary,
                "confidence": 0.5,
            }

        plain_summary = str(parsed.get("plain_summary") or "Analysis completed.").strip()
        try:
            confidence = float(parsed.get("confidence", 0.75))
            confidence = max(0.0, min(1.0, confidence))
        except (TypeError, ValueError):
            confidence = 0.75

        ranked_hypotheses: List[Dict[str, Any]] = []
        for h in parsed.get("ranked_hypotheses", []):
            if isinstance(h, dict) and "hypothesis" in h:
                like = str(h.get("likelihood", "UNKNOWN")).upper()
                if like not in ("HIGH", "MEDIUM", "LOW", "UNKNOWN"):
                    like = "UNKNOWN"
                item = {
                    "hypothesis": str(h["hypothesis"]),
                    "likelihood": like,
                }
                if h.get("explanation"):
                    item["explanation"] = str(h["explanation"])
                ranked_hypotheses.append(item)

        observations_dict = parsed.get("observations")
        observations: Dict[str, List[str]] = {"supporting": [], "contradicting": []}
        if isinstance(observations_dict, dict):
            if isinstance(observations_dict.get("supporting"), list):
                observations["supporting"] = [str(s) for s in observations_dict["supporting"]]
            if isinstance(observations_dict.get("contradicting"), list):
                observations["contradicting"] = [str(c) for c in observations_dict["contradicting"]]

        relevant_steps_dict = parsed.get("relevant_steps")
        relevant_steps: Dict[str, List[str]] = {"cli": [], "gui": []}
        if isinstance(relevant_steps_dict, dict):
            if isinstance(relevant_steps_dict.get("cli"), list):
                relevant_steps["cli"] = [str(s) for s in relevant_steps_dict["cli"]]
            if isinstance(relevant_steps_dict.get("gui"), list):
                relevant_steps["gui"] = [str(s) for s in relevant_steps_dict["gui"]]

        fp = (pack.get("incident_fingerprints") or [None])[0]
        run_id = pack.get("run_id")
        if run_id in ("NONE", "SELECTION"):
            run_id = None

        result: Dict[str, Any] = {
            "analysis_id": analysis_id,
            "pack_id": pack.get("pack_id"),
            "run_id": run_id,
            "incident_fingerprint": fp,
            "provider": provider_id,
            "engine": engine,
            "model": model,
            "created_at": created_at,
            "completed_at": completed_at,
            "status": actual_status,
            "plain_summary": plain_summary,
            "confidence": confidence,
            "affected_systems": [str(x) for x in parsed.get("affected_systems", [])],
            "affected_users": [str(x) for x in parsed.get("affected_users", [])],
            "affected_branches": [str(x) for x in parsed.get("affected_branches", [])],
            "affected_services": [str(x) for x in parsed.get("affected_services", [])],
            "ranked_hypotheses": ranked_hypotheses,
            "observations": observations,
            "missing_evidence": [str(x) for x in parsed.get("missing_evidence", [])],
            "recommended_diagnostics": [str(x) for x in parsed.get("recommended_diagnostics", [])],
            "immediate_actions": [str(x) for x in parsed.get("immediate_actions", [])],
            "long_term_actions": [str(x) for x in parsed.get("long_term_actions", [])],
            "relevant_steps": relevant_steps,
            "source_references": [str(x) for x in parsed.get("source_references", pack.get("sources", []))],
            "warnings": warnings + [str(w) for w in parsed.get("warnings", [])],
        }

        try:
            validate_contract(result, "security-analysis-result.schema.json")
        except Exception as exc:
            logger.warning("Analysis result contract validation error: %s", exc)

        return result

    def analyze_pack(
        self,
        pack: Dict[str, Any],
        engine: str = "BOTH",
        model: Optional[str] = None,
        owner_session_digest: Optional[str] = None,
        analysis_id: Optional[str] = None,
        progress_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        """Analyzes a prepared context pack using Codex, Antigravity, or Both concurrently."""
        engine_clean = engine.upper()
        if engine_clean not in ("CODEX", "ANTIGRAVITY", "BOTH"):
            raise ValueError(f"Invalid engine '{engine}'. Must be CODEX, ANTIGRAVITY, or BOTH.")

        if engine_clean in ("CODEX", "ANTIGRAVITY"):
            aid = analysis_id or self._generate_analysis_id(engine_clean)
            res = self._execute_single_engine(aid, engine_clean, model, pack, owner_session_digest, progress_callback=progress_callback)
            out = {
                "engine": engine_clean,
                "result": res,
                "analysis_id": aid,
                "status": res.get("status", "COMPLETED"),
            }
            with self._lock:
                self._results[aid] = out
            return out

        # BOTH: execute concurrently
        aid = analysis_id or self._generate_analysis_id("dual")
        self.emit_event(aid, "analysis.started", {
            "engine": "BOTH",
            "analysis_id": aid,
            "target_type": pack.get("target_type"),
        }, progress_callback=progress_callback)

        aid_codex = self._generate_analysis_id("codex")
        aid_agy = self._generate_analysis_id("antigravity")

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            fut_codex = executor.submit(self._execute_single_engine, aid_codex, "CODEX", model, pack, owner_session_digest, progress_callback)
            fut_agy = executor.submit(self._execute_single_engine, aid_agy, "ANTIGRAVITY", model, pack, owner_session_digest, progress_callback)
            res_codex = fut_codex.result()
            res_agy = fut_agy.result()

        comparison: Optional[Dict[str, Any]] = None
        if res_codex.get("status") in ("COMPLETED", "PARTIAL") and res_agy.get("status") in ("COMPLETED", "PARTIAL"):
            try:
                comparison = self.comparator.compare(res_codex, res_agy)
                self.run_store.save_comparison(comparison)
            except Exception as exc:
                logger.error("Failed comparing analyses: %s", exc, exc_info=True)

        overall_status = "COMPLETED" if (
            res_codex.get("status") in ("COMPLETED", "PARTIAL") or res_agy.get("status") in ("COMPLETED", "PARTIAL")
        ) else "FAILED"

        out = {
            "engine": "BOTH",
            "analysis_id": aid,
            "status": overall_status,
            "codex": res_codex,
            "antigravity": res_agy,
            "comparison": comparison,
            "completed_at": self.clock().isoformat(),
        }
        with self._lock:
            self._results[aid] = out

        self.emit_event(
            aid,
            "analysis.completed" if overall_status != "FAILED" else "analysis.failed",
            {
                "analysis_id": aid,
                "status": overall_status,
                "confidence": comparison.get("synthesis", {}).get("overall_confidence", 0.85) if comparison else 0.85,
                "summary": comparison.get("synthesis", {}).get("consensus_summary", "") if comparison else "Dual analysis completed.",
            },
            progress_callback=progress_callback,
        )
        return out

    def submit_run_analysis(
        self,
        run_id: str,
        engine: str = "BOTH",
        model: Optional[str] = None,
        owner_session_digest: Optional[str] = None,
    ) -> str:
        """Schedules a run analysis in the background and returns the analysis_id."""
        run = self.run_store.get_run(run_id)
        if not run:
            raise ValueError(f"Run '{run_id}' not found.")
        engine_clean = engine.upper()
        aid = self._generate_analysis_id("dual" if engine_clean == "BOTH" else engine_clean)
        self.emit_event(aid, "analysis.queued", {"analysis_id": aid, "run_id": run_id, "engine": engine_clean})

        def _worker():
            try:
                pack = self.pack_builder.build_run_pack(run_id)
                self.analyze_pack(pack, engine=engine_clean, model=model, owner_session_digest=owner_session_digest, analysis_id=aid)
            except Exception as exc:
                logger.error("Background run analysis %s failed: %s", aid, exc, exc_info=True)
                self.emit_event(aid, "analysis.failed", {"analysis_id": aid, "error": str(exc)})
                with self._lock:
                    self._results[aid] = {"analysis_id": aid, "engine": engine_clean, "status": "FAILED", "error": str(exc)}

        threading.Thread(target=_worker, name=f"sec-run-analysis-{aid}", daemon=True).start()
        return aid

    def submit_incident_analysis(
        self,
        fingerprint: str,
        engine: str = "BOTH",
        model: Optional[str] = None,
        owner_session_digest: Optional[str] = None,
    ) -> str:
        """Schedules an incident analysis in the background and returns the analysis_id."""
        rec = self.run_store.get_incident_record(fingerprint)
        if not rec:
            raise ValueError(f"Incident '{fingerprint}' not found.")
        engine_clean = engine.upper()
        aid = self._generate_analysis_id("dual" if engine_clean == "BOTH" else engine_clean)
        self.emit_event(aid, "analysis.queued", {"analysis_id": aid, "incident_fingerprint": fingerprint, "engine": engine_clean})

        def _worker():
            try:
                pack = self.pack_builder.build_incident_pack(fingerprint)
                self.analyze_pack(pack, engine=engine_clean, model=model, owner_session_digest=owner_session_digest, analysis_id=aid)
            except Exception as exc:
                logger.error("Background incident analysis %s failed: %s", aid, exc, exc_info=True)
                self.emit_event(aid, "analysis.failed", {"analysis_id": aid, "error": str(exc)})
                with self._lock:
                    self._results[aid] = {"analysis_id": aid, "engine": engine_clean, "status": "FAILED", "error": str(exc)}

        threading.Thread(target=_worker, name=f"sec-incident-analysis-{aid}", daemon=True).start()
        return aid

    def analyze_run(
        self,
        run_id: str,
        engine: str = "BOTH",
        model: Optional[str] = None,
        owner_session_digest: Optional[str] = None,
        progress_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        pack = self.pack_builder.build_run_pack(run_id)
        return self.analyze_pack(pack, engine=engine, model=model, owner_session_digest=owner_session_digest, progress_callback=progress_callback)

    def analyze_incident(
        self,
        fingerprint: str,
        engine: str = "BOTH",
        model: Optional[str] = None,
        owner_session_digest: Optional[str] = None,
        progress_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        pack = self.pack_builder.build_incident_pack(fingerprint)
        return self.analyze_pack(pack, engine=engine, model=model, owner_session_digest=owner_session_digest, progress_callback=progress_callback)

    def analyze_incidents(
        self,
        fingerprints: List[str],
        run_id: Optional[str] = None,
        engine: str = "BOTH",
        model: Optional[str] = None,
        owner_session_digest: Optional[str] = None,
        progress_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        pack = self.pack_builder.build_incidents_pack(fingerprints, run_id=run_id)
        return self.analyze_pack(pack, engine=engine, model=model, owner_session_digest=owner_session_digest, progress_callback=progress_callback)

    def get_analysis(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            if analysis_id in self._results:
                return self._results[analysis_id]
        return self.run_store.get_analysis(analysis_id)

    def compare_analyses(self, codex_analysis_id: str, antigravity_analysis_id: str) -> Dict[str, Any]:
        c_res = self.get_analysis(codex_analysis_id) or self.run_store.get_analysis(codex_analysis_id)
        if not c_res:
            raise ValueError(f"Codex analysis '{codex_analysis_id}' not found.")
        a_res = self.get_analysis(antigravity_analysis_id) or self.run_store.get_analysis(antigravity_analysis_id)
        if not a_res:
            raise ValueError(f"Antigravity analysis '{antigravity_analysis_id}' not found.")

        # Extract underlying result if wrapped
        c_payload = c_res.get("result", c_res)
        a_payload = a_res.get("result", a_res)
        comparison = self.comparator.compare(c_payload, a_payload)
        return self.run_store.save_comparison(comparison)

    def open_incident_chat(
        self,
        fingerprint: str,
        engine: str = "codex",
        model: Optional[str] = None,
        owner_session_digest: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Creates a dedicated conversation thread in ConversationEngine for interactive troubleshooting."""
        rec = self.run_store.get_incident_record(fingerprint)
        if not rec:
            raise ValueError(f"Incident '{fingerprint}' not found.")

        engine_clean = engine.lower()
        if engine_clean not in ("codex", "antigravity"):
            engine_clean = "codex"

        provider_id = CODEX_PROVIDER_ID if engine_clean == "codex" else ANTIGRAVITY_PROVIDER_ID
        actual_model = model or ("chatgpt" if engine_clean == "codex" else DEFAULT_ANTIGRAVITY_MODEL)

        title = f"Incident: {rec.display_id} - {rec.title[:45]}"

        if self.conversation_engine:
            thread = self.conversation_engine.create_thread(
                title=title,
                provider_id=provider_id,
                engine_id=engine_clean,
                model_id=actual_model,
                permission_mode="OWNER_DIRECT",
            )
            thread_id = thread["thread_id"]

            # Seed context with incident details and source references
            pack = self.pack_builder.build_incident_pack(fingerprint)
            rec_display = getattr(rec, "display_id", getattr(rec, "fingerprint", fingerprint))
            rec_title = getattr(rec, "title", "Incident Investigation")
            rec_sev = getattr(rec, "current_severity", getattr(rec, "peak_severity", getattr(rec, "severity", "UNKNOWN")))
            if hasattr(rec_sev, "value"):
                rec_sev = rec_sev.value
            rec_dev = getattr(rec, "source_device", getattr(rec, "source_entity", "UNKNOWN"))
            rec_attacker = getattr(rec, "attacker_identity", getattr(rec, "attacker_ip", "UNKNOWN"))
            rec_target = getattr(rec, "target_identity", getattr(rec, "target", "UNKNOWN"))
            rec_cat = getattr(rec, "category", "UNKNOWN")
            if hasattr(rec_cat, "value"):
                rec_cat = rec_cat.value

            seed_content = (
                f"Incident Investigation Context for {rec_display}:\n"
                f"- Title: {rec_title}\n"
                f"- Severity: {rec_sev}\n"
                f"- Device: {rec_dev}\n"
                f"- Attacker IP: {rec_attacker}\n"
                f"- Target: {rec_target}\n"
                f"- Category: {rec_cat}\n"
                f"- Sources: {', '.join(pack.get('sources', []))}\n\n"
                "Please analyze this incident and recommend immediate verification checks."
            )
            turn_id = None
            try:
                turn = self.conversation_engine.store.create_turn(thread_id)
                turn_id = turn.get("turn_id") if isinstance(turn, dict) else getattr(turn, "turn_id", None)
                if turn_id:
                    self.conversation_engine.store.add_message(turn_id, role="user", content=seed_content)
            except Exception as exc:
                logger.warning("Failed creating initial turn for incident chat: %s", exc)

            return {
                "thread_id": thread_id,
                "turn_id": turn_id,
                "title": title,
                "fingerprint": fingerprint,
                "engine": engine_clean,
                "model": actual_model,
            }

        # Fallback if conversation_engine not wired
        fake_thread_id = f"thr_sec_{uuid.uuid4().hex[:12]}"
        fake_turn_id = f"trn_sec_{uuid.uuid4().hex[:12]}"
        return {
            "thread_id": fake_thread_id,
            "turn_id": fake_turn_id,
            "title": title,
            "fingerprint": fingerprint,
            "engine": engine_clean,
            "model": actual_model,
        }
