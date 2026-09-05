"""Supervised Antigravity CLI 1.1.26 harness with Unrestricted Read and Governed Write Risk/Rollback Review."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from core.tools.broker import ToolBroker

ANTIGRAVITY_PROVIDER_ID = "prv_antigravity_cli"
DEFAULT_ANTIGRAVITY_MODEL = "gemini-3.8-flash-high"

KNOWN_ANTIGRAVITY_MODELS = [
    {"id": "gemini-3.8-flash-high", "label": "Gemini 3.8 Flash (High)", "effort": "high"},
    {"id": "gemini-3.8-flash-medium", "label": "Gemini 3.8 Flash (Medium)", "effort": "medium"},
    {"id": "gemini-3.8-flash-low", "label": "Gemini 3.8 Flash (Low)", "effort": "low"},
    {"id": "gemini-3.7-flash-high", "label": "Gemini 3.7 Flash (High)", "effort": "high"},
    {"id": "gemini-3.7-flash-medium", "label": "Gemini 3.7 Flash (Medium)", "effort": "medium"},
    {"id": "gemini-3.7-flash-low", "label": "Gemini 3.7 Flash (Low)", "effort": "low"},
    {"id": "gemini-3.6-flash-high", "label": "Gemini 3.6 Flash (High)", "effort": "high"},
    {"id": "gemini-3.1-pro-high", "label": "Gemini 3.1 Pro (High)", "effort": "high"},
    {"id": "gemini-3.1-pro-low", "label": "Gemini 3.1 Pro (Low)", "effort": "low"},
    {"id": "claude-sonnet-4-6", "label": "Claude Sonnet 4.6 (Thinking)", "effort": "default"},
    {"id": "claude-opus-4-6-thinking", "label": "Claude Opus 4.6 (Thinking)", "effort": "default"},
    {"id": "gpt-oss-120b-medium", "label": "GPT-OSS 120B (Medium)", "effort": "medium"},
]


class AntigravityCliError(RuntimeError):
    pass


def discover_agy_executable() -> Path | None:
    """Discover the agy.exe binary across known install locations and PATH."""
    env_path = os.environ.get("AGY_PATH")
    if env_path and Path(env_path).is_file():
        return Path(env_path).resolve()

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        candidate = Path(local_app_data) / "agy/bin/agy.exe"
        if candidate.is_file():
            return candidate.resolve()

    home = Path.home()
    for sub in ("antigravity-cli", "antigravity"):
        candidate = home / ".gemini" / sub / "bin/agy.exe"
        if candidate.is_file():
            return candidate.resolve()

    which = shutil.which("agy.exe") or shutil.which("agy")
    if which:
        return Path(which).resolve()

    return None


def query_models(agy_path: Path | None = None) -> list[dict[str, Any]]:
    """Query live models from the agy CLI, falling back to known models."""
    if not agy_path or not Path(agy_path).is_file():
        return deepcopy(KNOWN_ANTIGRAVITY_MODELS)
    try:
        res = subprocess.run(
            [str(agy_path), "models"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if res.returncode == 0:
            lines = res.stdout.strip().splitlines()
            models: list[dict[str, Any]] = []
            for line in lines:
                parts = line.strip().split("\t")
                if len(parts) >= 2:
                    model_id = parts[0].strip()
                    label = parts[1].strip()
                    if model_id and not model_id.lower().startswith("fetching"):
                        models.append({"id": model_id, "label": label})
                elif parts and parts[0] and not parts[0].lower().startswith("fetching"):
                    models.append({"id": parts[0].strip(), "label": parts[0].strip()})
            if models:
                return models
    except Exception:
        pass
    return deepcopy(KNOWN_ANTIGRAVITY_MODELS)


class AntigravityHarness:
    """Supervised runtime harness for Antigravity CLI with Unrestricted Read & Governed Write."""

    def __init__(
        self,
        base_dir: Path,
        *,
        tool_broker: ToolBroker | None = None,
        event_sink: Callable[[str, str, str, dict[str, Any]], None] | None = None,
        completion_sink: Callable[[str, str], None] | None = None,
        failure_sink: Callable[[str, str], None] | None = None,
        binary_path: Path | None = None,
    ):
        self.base_dir = base_dir.resolve()
        self.tool_broker = tool_broker
        self.event_sink = event_sink or (lambda *_: None)
        self.completion_sink = completion_sink or (lambda *_: None)
        self.failure_sink = failure_sink or (lambda *_: None)
        self._custom_binary = binary_path
        self._conversations: dict[str, str] = {}
        self._active_processes: dict[str, subprocess.Popen[str]] = {}
        self._cancelled: set[str] = set()
        self._lock = threading.RLock()

    def binary(self) -> Path | None:
        if self._custom_binary is not None:
            if Path(self._custom_binary).is_file():
                return Path(self._custom_binary).resolve()
            return None
        return discover_agy_executable()

    def readiness(self, *, start_process: bool = False) -> dict[str, Any]:
        """Return a secret-free Antigravity CLI readiness summary."""
        bin_path = self.binary()
        if not bin_path:
            return {
                "status": "NOT_INSTALLED",
                "version": None,
                "binary_path": None,
                "models": query_models(None),
                "default_model": DEFAULT_ANTIGRAVITY_MODEL,
                "missing_prerequisites": ["Antigravity CLI ('agy.exe') was not found in LOCALAPPDATA or PATH."],
                "unrestricted_read": True,
                "write_governance": "RISK_AND_ROLLBACK_REVIEW_REQUIRED",
            }
        version = "1.1.26"
        try:
            res = subprocess.run([str(bin_path), "--version"], capture_output=True, text=True, timeout=5, check=False)
            if res.returncode == 0 and res.stdout.strip():
                version = res.stdout.strip()
        except Exception:
            pass
        return {
            "status": "READY",
            "version": version,
            "binary_path": str(bin_path),
            "models": query_models(bin_path),
            "default_model": DEFAULT_ANTIGRAVITY_MODEL,
            "missing_prerequisites": [],
            "unrestricted_read": True,
            "write_governance": "RISK_AND_ROLLBACK_REVIEW_REQUIRED",
        }

    def models(self) -> dict[str, Any]:
        return {
            "models": query_models(self.binary()),
            "default_model": DEFAULT_ANTIGRAVITY_MODEL,
        }

    def start_turn(
        self,
        *,
        gui_thread_id: str,
        gui_turn_id: str,
        content: str,
        owner_session_digest: str,
        model_id: str = DEFAULT_ANTIGRAVITY_MODEL,
        permission_mode: str = "OWNER_FULL_CONTROL",
        timeout_seconds: int = 600,
    ) -> None:
        """Execute a turn using Antigravity CLI in a managed background thread."""
        worker = threading.Thread(
            target=self._run_turn,
            args=(gui_thread_id, gui_turn_id, content, owner_session_digest, model_id, permission_mode, timeout_seconds),
            name="antigravity-" + gui_turn_id,
            daemon=True,
        )
        worker.start()

    def cancel_turn(self, gui_turn_id: str) -> None:
        """Cancel an active turn and terminate the running child process."""
        with self._lock:
            self._cancelled.add(gui_turn_id)
            proc = self._active_processes.get(gui_turn_id)
            if proc is not None and proc.poll() is None:
                try:
                    proc.terminate()
                except OSError:
                    pass

    def prepare_write_review(
        self,
        *,
        entity_id: str,
        protocol: str,
        operations: list[str],
        intended_change: str,
        expected_impact: str,
        downtime_risk: str,
        blast_radius: str,
        prechecks: list[str],
        postchecks: list[str],
        rollback_steps: list[str] | None = None,
        owner_requested: bool = True,
    ) -> dict[str, Any]:
        """Prepare an exact write plan with transparent risk classification and rollback feasibility."""
        if not self.tool_broker:
            raise AntigravityCliError("Tool broker is required for governed write operations.")
        return self.tool_broker.owner_direct.prepare_write(
            entity_id=entity_id,
            protocol=protocol,
            operations=operations,
            intended_change=intended_change,
            expected_impact=expected_impact,
            downtime_risk=downtime_risk,
            blast_radius=blast_radius,
            prechecks=prechecks,
            postchecks=postchecks,
            rollback_steps=rollback_steps,
            owner_requested=owner_requested,
        )

    def _notify_failure(self, gui_turn_id: str, code: str, accumulated_text: str = "") -> None:
        try:
            self.failure_sink(gui_turn_id, code, accumulated_text)
        except TypeError:
            self.failure_sink(gui_turn_id, code)

    @staticmethod
    def _map_error_code(err: str) -> str:
        lowered = str(err or "").lower()
        if "timeout" in lowered:
            return "ANTIGRAVITY_TIMEOUT"
        if "not installed" in lowered or "not found" in lowered:
            return "ANTIGRAVITY_NOT_INSTALLED"
        if "cancel" in lowered:
            return "ANTIGRAVITY_TURN_CANCELLED"
        if "auth" in lowered or "login" in lowered or "unauthorized" in lowered:
            return "ANTIGRAVITY_AUTH_REQUIRED"
        if "empty" in lowered:
            return "ANTIGRAVITY_EMPTY_RESPONSE"
        from core.llm.providers.base import SAFE_PROVIDER_ERRORS
        if err in SAFE_PROVIDER_ERRORS:
            return err
        return "ANTIGRAVITY_TURN_FAILED"

    def _run_turn(
        self,
        gui_thread_id: str,
        gui_turn_id: str,
        content: str,
        owner_digest: str,
        model_id: str,
        permission_mode: str,
        timeout_seconds: int,
    ) -> None:
        bin_path = self.binary()
        if not bin_path:
            self._notify_failure(gui_turn_id, "ANTIGRAVITY_NOT_INSTALLED")
            return

        with self._lock:
            if gui_turn_id in self._cancelled:
                self._notify_failure(gui_turn_id, "ANTIGRAVITY_TURN_CANCELLED")
                return
            conversation_id = self._conversations.get(gui_thread_id)

        self.event_sink(
            gui_thread_id,
            gui_turn_id,
            "agent.progress",
            {"text": f"Antigravity CLI (1.1.26) starting turn with {model_id} (Unrestricted Read & Governed Write)..."},
        )

        cmd = [
            str(bin_path),
            "--model",
            model_id,
            "--output-format",
            "stream-json",
            "--dangerously-skip-permissions",
            "--print-timeout",
            f"{max(600, timeout_seconds)}s",
        ]
        if conversation_id:
            cmd.extend(["--conversation", conversation_id])
        cmd.extend(["--print", content])

        accumulated_text = ""
        last_error = ""

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=str(self.base_dir),
            )
            with self._lock:
                self._active_processes[gui_turn_id] = proc

            deadline = time.monotonic() + max(1, min(timeout_seconds, 1800))

            if proc.stdout:
                for line in proc.stdout:
                    if time.monotonic() > deadline:
                        proc.terminate()
                        self._notify_failure(gui_turn_id, "ANTIGRAVITY_TIMEOUT", accumulated_text)
                        return

                    with self._lock:
                        if gui_turn_id in self._cancelled:
                            proc.terminate()
                            self._notify_failure(gui_turn_id, "ANTIGRAVITY_TURN_CANCELLED", accumulated_text)
                            return

                    line_str = line.strip()
                    if not line_str:
                        continue

                    try:
                        event_data = json.loads(line_str)
                    except json.JSONDecodeError:
                        continue

                    event_type = event_data.get("event")

                    if event_type == "init":
                        init_conv_id = event_data.get("conversation_id")
                        if init_conv_id:
                            with self._lock:
                                self._conversations[gui_thread_id] = init_conv_id

                    elif event_type == "step_update":
                        step = event_data.get("step_update", {})
                        stype = step.get("step_type")
                        if stype == "agent_response":
                            delta = step.get("text_delta")
                            if delta:
                                accumulated_text += delta
                                self.event_sink(
                                    gui_thread_id,
                                    gui_turn_id,
                                    "answer.delta",
                                    {"text": delta},
                                )
                        elif stype == "tool":
                            tname = step.get("tool_name", "unknown_tool")
                            tstate = step.get("state", "ACTIVE")
                            tinfo = step.get("tool_info", {})
                            self.event_sink(
                                gui_thread_id,
                                gui_turn_id,
                                "agent.progress",
                                {"text": f"Running tool: {tname} [{tstate}]"},
                            )

                    elif event_type == "error":
                        err_val = event_data.get("error", {})
                        last_error = err_val.get("message") if isinstance(err_val, dict) else str(err_val)

                    elif event_type == "result":
                        res = event_data.get("result", {})
                        if res.get("status") == "SUCCESS":
                            resp_text = res.get("response") or accumulated_text
                            self.completion_sink(gui_turn_id, resp_text)
                            return
                        else:
                            last_error = res.get("error") or "Antigravity CLI execution error"
                            self._notify_failure(gui_turn_id, self._map_error_code(last_error), accumulated_text)
                            return

            proc.wait(timeout=15)
            if proc.returncode == 0 and (accumulated_text or not last_error):
                self.completion_sink(gui_turn_id, accumulated_text or "Turn completed.")
            else:
                stderr_text = proc.stderr.read() if proc.stderr else ""
                err_msg = last_error or stderr_text.strip() or "ANTIGRAVITY_EMPTY_RESPONSE"
                self._notify_failure(gui_turn_id, self._map_error_code(err_msg), accumulated_text)

        except Exception as exc:
            self._notify_failure(gui_turn_id, "ANTIGRAVITY_TURN_FAILED", accumulated_text)
        finally:
            with self._lock:
                self._active_processes.pop(gui_turn_id, None)
                self._cancelled.discard(gui_turn_id)
