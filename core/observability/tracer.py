#!/usr/bin/env python3
"""
MNE_Brain Release 2 — Enterprise Observability Engine (`core/observability/tracer.py`)
Provides Correlation ID tracking, structured logging, component execution timelines,
performance metrics, and audit trail collection.
"""

import json
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

class ObservabilityTracer:
    """In-memory tracing by default; persistence is an explicit opt-in action."""

    _SENSITIVE_KEY = re.compile(r"password|token|secret|credential|community|private.?key", re.I)

    def __init__(self, base_dir: Path = None, correlation_id: Optional[str] = None, *, persist: bool = False):
        self.base_dir = base_dir or Path(__file__).resolve().parent.parent.parent
        self.correlation_id = correlation_id or f"corr-{uuid.uuid4().hex[:8]}"
        self.investigation_id = f"inv-{uuid.uuid4().hex[:8]}"
        self.start_time = time.time()
        self.timeline: List[Dict[str, Any]] = []
        self.metrics: Dict[str, Any] = {}
        self.log_file = self.base_dir / "operations" / "logs" / "observability.jsonl"
        self.persist = bool(persist)

    @classmethod
    def _redact(cls, value: Any) -> Any:
        if isinstance(value, dict):
            return {
                str(key): "[REDACTED]" if cls._SENSITIVE_KEY.search(str(key)) else cls._redact(item)
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [cls._redact(item) for item in value]
        return value

    def trace_step(self, component: str, action: str, status: str = "SUCCESS", details: Optional[Dict[str, Any]] = None, duration: float = 0.0):
        timestamp = datetime.now(timezone.utc).isoformat()
        entry = {
            "correlation_id": self.correlation_id,
            "investigation_id": self.investigation_id,
            "timestamp": timestamp,
            "component": component,
            "action": action,
            "status": status,
            "duration_ms": round(duration * 1000, 2),
            "details": self._redact(details or {})
        }
        self.timeline.append(entry)
        if self.persist:
            self._append_log(entry)

    def _append_log(self, entry: Dict[str, Any]):
        try:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            pass

    def get_summary(self) -> Dict[str, Any]:
        total_duration = round((time.time() - self.start_time) * 1000, 2)
        return {
            "correlation_id": self.correlation_id,
            "investigation_id": self.investigation_id,
            "total_duration_ms": total_duration,
            "steps_executed": len(self.timeline),
            "timeline": self.timeline
        }

if __name__ == "__main__":
    tracer = ObservabilityTracer(persist=False)
    tracer.trace_step("query_router", "classify_query", details={"route_type": "troubleshoot"}, duration=0.002)
    print(json.dumps(tracer.get_summary(), indent=2))
