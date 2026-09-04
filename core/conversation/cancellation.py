"""Bounded cancellation tokens for conversation turns."""

from __future__ import annotations

import threading
import time


class TurnCancelled(RuntimeError):
    pass


class TurnTimedOut(RuntimeError):
    pass


class CancellationToken:
    def __init__(self, timeout_seconds: int):
        self._cancelled = threading.Event()
        self._deadline = time.monotonic() + max(1, timeout_seconds)

    def cancel(self) -> None:
        self._cancelled.set()

    def checkpoint(self) -> None:
        if self._cancelled.is_set():
            raise TurnCancelled("Turn was cancelled by the owner.")
        if time.monotonic() >= self._deadline:
            raise TurnTimedOut("Turn exceeded its bounded execution time.")

    @property
    def cancelled(self) -> bool:
        return self._cancelled.is_set()

