#!/usr/bin/env python3
"""Non-connecting SQL driver foundation."""

from typing import Any

from .base_driver import ProtocolDriver


class SQLDriver(ProtocolDriver):
    def __init__(self):
        super().__init__("sql")

    def execute(
        self,
        db_host: str,
        query: str,
        port: int = 1433,
        timeout: int = 3,
        *,
        authorized: bool = False,
    ) -> dict[str, Any]:
        del port, timeout
        return self.execute_request(db_host, query, authorized=authorized)
