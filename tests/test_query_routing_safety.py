#!/usr/bin/env python3
"""Offline checks for bounded query routing and target disambiguation."""

import sys
from pathlib import Path

base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(base_dir))

from core.router.route_query import QueryRouter


def test_router_bounds_unknown_target_options() -> None:
    router = QueryRouter(base_dir=base_dir)

    unknown = router.classify_query("Why is the internet down?")
    assert unknown["route_type"] == "troubleshoot"
    assert unknown["resolution_status"] == "unknown"
    assert unknown["clarification_request"]["requires_clarification"] is True
    assert unknown["clarification_request"]["options"] == []

    exact = router.classify_query("Why is 172.23.19.1 unreachable?")
    assert exact["route_type"] == "troubleshoot"
    assert exact["resolution_status"] == "exact"
    assert exact["clarification_request"] is None
    assert exact["resolved_entity_ids"] == ["fw-fortigate-hq-01"]

    concept = router.classify_query("Explain network topology")
    assert concept["route_type"] == "concept"
    assert concept["requires_entity_resolution"] is False
    assert concept["clarification_request"] is None


def test_concept_queries_bypass_entity_resolution() -> None:
    router = QueryRouter(base_dir=base_dir)

    def unexpected_resolution(_: str):
        raise AssertionError("Generic concept queries must not resolve entities")

    router.entity_builder.resolve_entity = unexpected_resolution
    result = router.classify_query("Explain network topology")
    assert result["route_type"] == "concept"


if __name__ == "__main__":
    test_router_bounds_unknown_target_options()
    test_concept_queries_bypass_entity_resolution()
    print("Query routing safety test passed.")
