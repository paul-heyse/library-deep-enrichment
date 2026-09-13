"""The pluggable registry-probe table.

A probe asks a library for its own catalog. Adding one for a new library is a
module plus a manifest entry; nothing in the stage layer names a library.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Mapping

    from library_guides.models.records import SurfaceEntry

__all__ = ["ProbeResult", "RegistryProbe", "available_probes", "probe_by_id", "register_probe"]


class ProbeResult(Protocol):
    """What a registry probe returns."""

    @property
    def entries(self) -> tuple[SurfaceEntry, ...]:
        """Non-symbol surfaces the library reported.

        Returns:
            The discovered entries.

        """
        ...

    @property
    def detail(self) -> str:
        """How the probe was performed and what it is evidence for.

        Returns:
            A short description.

        """
        ...


class RegistryProbe(Protocol):
    """A callable that interrogates one library's own catalog."""

    def __call__(self, *, library_id: str, profile_id: str) -> ProbeResult:
        """Run the probe.

        Returns:
            The probe result.

        """
        ...


_PROBES: dict[str, RegistryProbe] = {}


def register_probe(probe_id: str, probe: RegistryProbe) -> None:
    """Register ``probe`` under ``probe_id``.

    Raises:
        ValueError: When a probe identifier is registered twice.

    """
    if probe_id in _PROBES:
        message = f"registry probe {probe_id!r} is already registered"
        raise ValueError(message)
    _PROBES[probe_id] = probe


def probe_by_id(probe_id: str) -> RegistryProbe:
    """Return the probe registered under ``probe_id``.

    Returns:
        The probe.

    Raises:
        LookupError: When no probe carries that identifier.

    """
    probe = _PROBES.get(probe_id)
    if probe is None:
        known = ", ".join(sorted(_PROBES)) or "none"
        message = f"unknown registry probe {probe_id!r}; registered: {known}"
        raise LookupError(message)
    return probe


def available_probes() -> Mapping[str, RegistryProbe]:
    """Return every registered probe.

    Returns:
        Mapping of probe identifier to probe.

    """
    return dict(_PROBES)
