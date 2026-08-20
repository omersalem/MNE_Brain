"""Pytest compatibility for validation scripts that return a boolean result."""

import inspect

import pytest


SAFE_INTEGRATION_FILES = {
    "test_milestone_13.py",
    "test_performance_scalability.py",
    "test_security_validation.py",
}


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Classify every collected test; no unmarked test silently enters CI."""
    known_markers = {"offline", "integration", "live", "mutating"}
    for item in items:
        if any(item.get_closest_marker(marker) for marker in known_markers):
            continue
        marker = pytest.mark.integration if item.path.name in SAFE_INTEGRATION_FILES else pytest.mark.offline
        item.add_marker(marker)


@pytest.hookimpl(tryfirst=True)
def pytest_pyfunc_call(pyfuncitem: pytest.Function) -> bool | None:
    """Turn legacy boolean validation results into enforceable pytest outcomes."""
    test_function = pyfuncitem.obj
    if inspect.iscoroutinefunction(test_function):
        return None

    test_arguments = {
        argument_name: pyfuncitem.funcargs[argument_name]
        for argument_name in pyfuncitem._fixtureinfo.argnames
    }
    result = test_function(**test_arguments)
    if isinstance(result, bool):
        if not result:
            pytest.fail(
                f"{pyfuncitem.nodeid} returned False",
                pytrace=False,
            )
    elif result is not None:
        pytest.fail(
            f"{pyfuncitem.nodeid} returned unsupported value {result!r}",
            pytrace=False,
        )
    return True
