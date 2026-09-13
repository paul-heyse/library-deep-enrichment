"""Resolve optional runtime registry integrations outside the library-neutral facade."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from library_deep_enrichment.registry_adapters import arrow_fabric, datafusion_fabric

if TYPE_CHECKING:
    from library_deep_enrichment.corpus.store import Corpus


class RegistryImporter(Protocol):
    """The generic application-to-adapter boundary."""

    def __call__(self, corpus: Corpus, *, profile: str) -> object:
        """Capture one explicit installed registry environment."""
        ...


def adapters() -> dict[str, RegistryImporter]:
    """Return the installed owned registry adapters.

    Returns:
        Explicit identifiers mapped to typed capture entry points.

    """
    return {
        "pyarrow": arrow_fabric.import_registry,
        "datafusion": datafusion_fabric.import_registry,
    }
