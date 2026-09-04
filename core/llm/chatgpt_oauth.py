"""Quarantined legacy shim.

ChatGPT consumer-account OAuth is not a supported provider authentication path.
P11 uses server-side OpenAI Platform API-key references only.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


class ChatGPTOAuthDisabled(RuntimeError):
    pass


class ChatGPTOAuthEngine:
    """Compatibility import that fails closed and never stores or synthesizes tokens."""

    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir

    @staticmethod
    def _disabled() -> None:
        raise ChatGPTOAuthDisabled("Synthetic ChatGPT OAuth is quarantined; configure an OpenAI Platform API-key reference.")

    def get_authorization_url(self) -> dict[str, Any]:
        self._disabled()

    def exchange_code_for_token(self, code: str, verifier: str) -> dict[str, Any]:
        self._disabled()

    def save_tokens(self, token_data: dict[str, Any]) -> None:
        self._disabled()

    def get_access_token(self) -> None:
        return None
