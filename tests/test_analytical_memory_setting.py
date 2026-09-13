"""Explicit worker calibration is captured rather than silently falling back."""

import pytest
from library_guides.corpus.backend import CorpusError
from library_guides.workflows.remote import memory_budget

DEFAULT_MEMORY = 4_000_000_000


def test_default_and_explicit_memory_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ordinary workers keep their default; a scoped invocation can calibrate its limit."""
    monkeypatch.delenv("LIBRARY_GUIDES_ANALYTICAL_MEMORY_BYTES", raising=False)
    assert memory_budget(DEFAULT_MEMORY) == DEFAULT_MEMORY
    monkeypatch.setenv("LIBRARY_GUIDES_ANALYTICAL_MEMORY_BYTES", str(8 * 1024**3))
    assert memory_budget(4_000_000_000) == 8 * 1024**3


@pytest.mark.parametrize("value", ["", "invalid", "0", "-1", str(65 * 1024**3)])
def test_invalid_memory_settings_are_errors(value: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """A mistyped or unsupported explicit bound must never acquire a permissive fallback."""
    monkeypatch.setenv("LIBRARY_GUIDES_ANALYTICAL_MEMORY_BYTES", value)
    with pytest.raises(CorpusError):
        memory_budget(4_000_000_000)
