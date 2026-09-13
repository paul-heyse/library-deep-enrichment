"""Report absent external prerequisites as *blocked*, never as failures or fake passes.

Two prerequisites are environmental rather than part of the code under test: the qualified
Souffle 2.5 rule runtime (``just souffle-provision``) and a ``bwrap`` that can create user and
network namespaces (denied on some CI runners). When one is missing the affected test is
skipped with the prerequisite named. ``LDE_REQUIRE_WORKERS=1`` (``just test-native``) turns
the same condition into a failure so a full run cannot silently narrow.
"""

from __future__ import annotations

import os
from collections.abc import Generator

import pluggy
import pytest

_BLOCKERS: tuple[tuple[str, str], ...] = (
    (
        "Souffle 2.5 runtime is unavailable",
        "blocked: qualified Souffle 2.5 runtime absent (run `just souffle-provision`)",
    ),
    (
        "bwrap: loopback: Failed RTM_NEWADDR",
        "blocked: bwrap cannot create a network namespace on this host",
    ),
    (
        "bwrap: setting up uid map",
        "blocked: bwrap cannot create a user namespace on this host",
    ),
)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item: pytest.Item) -> Generator[None, pluggy.Result[None]]:
    """Convert a named-prerequisite failure into a skip unless workers are required."""
    outcome = yield
    if os.environ.get("LDE_REQUIRE_WORKERS") == "1":
        return
    excinfo = outcome.excinfo
    if excinfo is None:
        return
    text = str(excinfo[1])
    for needle, reason in _BLOCKERS:
        if needle in text:
            outcome.force_exception(pytest.skip.Exception(f"{reason} [{item.nodeid}]"))
            return
