"""Ask a DataFusion session for its configuration catalog.

Configuration is functionality: a setting can remove the need for custom code as
completely as a built-in function can. An inventory that counts only callable
symbols misses it, which is why non-symbol surfaces carry their own denominator.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final, Protocol

from attrs import field, frozen

from library_deep_enrichment.models.enums import (
    Ecosystem,
    EvidenceOrigin,
    ResolutionState,
    SurfaceKind,
)
from library_deep_enrichment.models.ids import SurfaceId
from library_deep_enrichment.models.records import SurfaceEntry
from library_deep_enrichment.registry_adapters.registry import register_probe

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = ["PROBE_ID", "DataFusionSettingsProbeResult", "probe_datafusion_settings"]

PROBE_ID: Final = "datafusion_settings"

_SETTINGS_QUERY: Final = "SELECT name, value, description FROM information_schema.df_settings"


class _Queryable(Protocol):
    """A planned query whose result batches can be collected."""

    def collect(self) -> Sequence[object]:
        """Execute and gather every output batch.

        Returns:
            The collected batches.

        """
        ...


class _SqlSession(Protocol):
    """The narrow slice of a DataFusion session this probe uses."""

    def sql(self, query: str) -> _Queryable:
        """Plan ``query``.

        Returns:
            Something whose batches can be collected.

        """
        ...


@frozen(kw_only=True)
class DataFusionSettingsProbeResult:
    """Configuration keys reported by a live DataFusion session."""

    entries: tuple[SurfaceEntry, ...] = field()
    detail: str = field()


def probe_datafusion_settings(
    *,
    library_id: str,
    profile_id: str,
) -> DataFusionSettingsProbeResult:
    """Return the configuration keys a default DataFusion session exposes.

    Args:
        library_id: Owning library identifier.
        profile_id: Profile this observation is evidence for.

    Returns:
        The probe result.

    """
    import datafusion
    import pyarrow as pa
    from datafusion import SessionContext

    context: _SqlSession = SessionContext()
    batches = context.sql(_SETTINGS_QUERY).collect()
    rows = pa.Table.from_batches(batches).to_pylist() if batches else []

    entries: list[SurfaceEntry] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = row.get("name")
        if not isinstance(name, str):
            continue
        value = row.get("value")
        description = row.get("description")
        entries.append(
            SurfaceEntry(
                library_id=library_id,
                profile_id=profile_id,
                identity=SurfaceId(
                    ecosystem=Ecosystem.PYTHON,
                    package="datafusion",
                    surface_kind=str(SurfaceKind.CONFIGURATION_KEY),
                    name=name,
                ),
                surface_kind=SurfaceKind.CONFIGURATION_KEY,
                description=description if isinstance(description, str) else None,
                attributes=(("default", str(value)),),
                availability_conditions=("readable from a default SessionContext",),
                evidence_origin=EvidenceOrigin.RUNTIME_REGISTRY,
                resolution_state=ResolutionState.RESOLVED,
            )
        )

    return DataFusionSettingsProbeResult(
        entries=tuple(entries),
        detail=(
            f"information_schema.df_settings in a default SessionContext, "
            f"datafusion-python {datafusion.__version__}"
        ),
    )


register_probe(PROBE_ID, probe_datafusion_settings)
