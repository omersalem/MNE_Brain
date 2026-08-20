#!/usr/bin/env python3
"""Non-connecting REST driver foundation."""

from typing import Any

from .base_driver import ProtocolDriver


class RESTDriver(ProtocolDriver):
    def __init__(self):
        super().__init__("rest")

    def execute(
        self,
        endpoint: str,
        method: str = "GET",
        payload: dict[str, Any] | None = None,
        timeout: int = 3,
        *,
        authorized: bool = False,
    ) -> dict[str, Any]:
        del payload, timeout
        return self.execute_request(endpoint, method, authorized=authorized)
