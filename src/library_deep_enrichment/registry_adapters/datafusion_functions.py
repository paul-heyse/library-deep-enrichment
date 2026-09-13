"""Ask a DataFusion session for its registered function catalog.

This reads ``information_schema.routines`` and ``information_schema.parameters``
from a default session. It is a runtime-registry observation for the engine
version the *Python* binding wraps. A Rust workspace pinning a different patch
release is a different profile, so these entries are evidence for their own
profile and only candidates for any other.
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

__all__ = ["PROBE_ID", "DataFusionFunctionProbeResult", "probe_datafusion_functions"]

PROBE_ID: Final = "datafusion_sql_functions"

_ROUTINES_QUERY: Final = """
SELECT routine_name, function_type, is_deterministic, data_type, description, syntax_example
FROM information_schema.routines
"""
_PARAMETERS_QUERY: Final = """
SELECT specific_name, ordinal_position, parameter_name, data_type, is_variadic
FROM information_schema.parameters
"""


@frozen(kw_only=True)
class DataFusionFunctionProbeResult:
    """Registered SQL functions reported by a live DataFusion session."""

    entries: tuple[SurfaceEntry, ...] = field()
    detail: str = field()
    signature_rows: int = field(default=0)


class _SqlSession(Protocol):
    """The narrow slice of a DataFusion session this probe uses."""

    def sql(self, query: str) -> _Queryable:
        """Plan ``query``.

        Returns:
            Something whose batches can be collected.

        """
        ...


class _Queryable(Protocol):
    """A planned query whose result batches can be collected."""

    def collect(self) -> Sequence[object]:
        """Execute and gather every output batch.

        Returns:
            The collected batches.

        """
        ...


def _query(context: _SqlSession, sql: str) -> list[dict[str, object]]:
    import pyarrow as pa

    batches = context.sql(sql).collect()
    if not batches:
        return []
    table = pa.Table.from_batches(batches)
    rows = table.to_pylist()
    return [row for row in rows if isinstance(row, dict)]


def probe_datafusion_functions(
    *,
    library_id: str,
    profile_id: str,
) -> DataFusionFunctionProbeResult:
    """Return the SQL functions a default DataFusion session registers.

    Args:
        library_id: Owning library identifier.
        profile_id: Profile this observation is evidence for.

    Returns:
        The probe result.

    """
    import datafusion
    from datafusion import SessionContext

    context = SessionContext()
    routines = _query(context, _ROUTINES_QUERY)
    parameters = _query(context, _PARAMETERS_QUERY)

    arity: dict[str, int] = {}
    variadic: set[str] = set()
    for row in parameters:
        name = row.get("specific_name")
        if not isinstance(name, str):
            continue
        ordinal = row.get("ordinal_position")
        position = ordinal if isinstance(ordinal, int) else 0
        arity[name] = max(arity.get(name, 0), position)
        if row.get("is_variadic") is True:
            variadic.add(name)

    grouped: dict[str, dict[str, object]] = {}
    for row in routines:
        name = row.get("routine_name")
        if not isinstance(name, str):
            continue
        grouped.setdefault(name, row)

    entries: list[SurfaceEntry] = []
    for name, row in sorted(grouped.items()):
        attributes: list[tuple[str, str]] = [
            ("function_type", str(row.get("function_type") or "unknown")),
            ("deterministic", str(row.get("is_deterministic"))),
            ("max_arity", str(arity.get(name, 0))),
            ("variadic", str(name in variadic)),
        ]
        example = row.get("syntax_example")
        if isinstance(example, str) and example:
            attributes.append(("syntax_example", example))
        description = row.get("description")
        entries.append(
            SurfaceEntry(
                library_id=library_id,
                profile_id=profile_id,
                identity=SurfaceId(
                    ecosystem=Ecosystem.PYTHON,
                    package="datafusion",
                    surface_kind=str(SurfaceKind.SQL_FUNCTION),
                    name=name,
                ),
                surface_kind=SurfaceKind.SQL_FUNCTION,
                description=description if isinstance(description, str) else None,
                attributes=tuple(attributes),
                availability_conditions=("registered in a default SessionContext",),
                evidence_origin=EvidenceOrigin.RUNTIME_REGISTRY,
                resolution_state=ResolutionState.RESOLVED,
            )
        )

    return DataFusionFunctionProbeResult(
        entries=tuple(entries),
        detail=(
            f"information_schema.routines in a default SessionContext, "
            f"datafusion-python {datafusion.__version__}"
        ),
        signature_rows=len(routines),
    )


register_probe(PROBE_ID, probe_datafusion_functions)
