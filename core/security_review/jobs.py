"""
Background Job and Progress Manager for MNE_Brain Release 2 Security Review Subsystem.
Handles asynchronous background execution, thread pools, bounded SSE event streaming,
duplicate rejection, cancellation checkpoints, and targeted retries.
"""

from __future__ import annotations

import logging
import queue
import threading
from collections import deque
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Callable, Deque, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class SecurityReviewJobManager:
    """Manages background review jobs, progress event distribution, and cancellation flags."""

    def __init__(self, max_event_buffer: int = 500, max_workers: int = 3):
        self.max_event_buffer = max_event_buffer
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="sec_job")
        self._lock = threading.Lock()
        self._active_futures: Dict[str, Future] = {}
        self._cancelled_runs: Set[str] = set()
        self._event_buffers: Dict[str, Deque[Dict[str, Any]]] = {}
        self._event_seq: Dict[str, int] = {}
        self._subscribers: Dict[str, List[queue.Queue]] = {}

    def is_running(self, run_id: str) -> bool:
        """Returns True if the run is currently executing in a background thread."""
        with self._lock:
            future = self._active_futures.get(run_id)
            if future is None:
                return False
            return not future.done()

    def is_cancelled(self, run_id: str) -> bool:
        """Checks if a cancellation request has been recorded for the run."""
        with self._lock:
            return run_id in self._cancelled_runs

    def request_cancel(self, run_id: str) -> bool:
        """Requests cancellation of a running review job."""
        with self._lock:
            self._cancelled_runs.add(run_id)

        self.emit_event(
            run_id=run_id,
            event_type="run.cancelling",
            data={"run_id": run_id, "message": "Cancellation requested by operator."},
        )
        logger.info("Cancellation requested for security review run %s", run_id)
        return True

    def submit_job(
        self,
        run_id: str,
        target_fn: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> bool:
        """Submits a job for execution outside the HTTP request thread.
        Rejects duplicate starts for the same run ID.
        """
        with self._lock:
            future = self._active_futures.get(run_id)
            if future is not None and not future.done():
                logger.warning("Rejecting duplicate run execution for %s", run_id)
                return False

            # Reset state for this run ID
            self._cancelled_runs.discard(run_id)
            if run_id not in self._event_buffers:
                self._event_buffers[run_id] = deque(maxlen=self.max_event_buffer)
                self._event_seq[run_id] = 0

            # Schedule future
            fut = self._executor.submit(self._run_wrapper, run_id, target_fn, *args, **kwargs)
            self._active_futures[run_id] = fut
            return True

    def _run_wrapper(
        self,
        run_id: str,
        target_fn: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        try:
            return target_fn(*args, **kwargs)
        except Exception as exc:
            logger.error("Error executing background run %s: %s", run_id, exc, exc_info=True)
            self.emit_event(
                run_id=run_id,
                event_type="run.failed",
                data={"run_id": run_id, "error": str(exc)},
            )
            raise
        finally:
            with self._lock:
                self._active_futures.pop(run_id, None)

    def emit_event(
        self,
        run_id: str,
        event_type: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Emits a structured progress event, stores it in the ring buffer, and notifies SSE subscribers."""
        with self._lock:
            if run_id not in self._event_buffers:
                self._event_buffers[run_id] = deque(maxlen=self.max_event_buffer)
                self._event_seq[run_id] = 0

            seq = self._event_seq[run_id] + 1
            self._event_seq[run_id] = seq

            event_obj = {
                "id": str(seq),
                "event": event_type,
                "run_id": run_id,
                "data": data,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            self._event_buffers[run_id].append(event_obj)
            subscribers = list(self._subscribers.get(run_id, []))

        # Deliver to subscribers outside lock
        for q in subscribers:
            try:
                q.put_nowait(event_obj)
            except Exception:
                pass

        return event_obj

    def get_events(self, run_id: str, since_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Returns buffered events for a run, optionally filtered to events after since_id."""
        with self._lock:
            buffer = self._event_buffers.get(run_id)
            if not buffer:
                return []
            events = list(buffer)

        if since_id is not None:
            return [e for e in events if int(e["id"]) > since_id]
        return events

    def subscribe(
        self, run_id: str, last_event_id: Optional[int] = None
    ) -> Tuple[queue.Queue, List[Dict[str, Any]]]:
        """Subscribes an SSE connection to events for run_id.
        Returns a queue for new events and a list of missed buffered events.
        """
        q: queue.Queue = queue.Queue(maxsize=100)
        with self._lock:
            if run_id not in self._subscribers:
                self._subscribers[run_id] = []
            self._subscribers[run_id].append(q)

            # Get historical missed events from buffer
            buffer = self._event_buffers.get(run_id)
            if buffer:
                if last_event_id is not None:
                    missed = [e for e in buffer if int(e["id"]) > last_event_id]
                else:
                    missed = list(buffer)
            else:
                missed = []

        return q, missed

    def unsubscribe(self, run_id: str, q: queue.Queue) -> None:
        """Removes an SSE subscriber queue."""
        with self._lock:
            subs = self._subscribers.get(run_id)
            if subs and q in subs:
                subs.remove(q)
            if subs is not None and not subs:
                self._subscribers.pop(run_id, None)

    def shutdown(self, wait: bool = False) -> None:
        """Gracefully shuts down the thread pool."""
        self._executor.shutdown(wait=wait)
