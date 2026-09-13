"""Ask PyArrow for its registered compute-function catalog.

``pyarrow.compute.list_functions`` reports what the loaded native library
actually registered, which is a stronger inventory than any scan of Python
source can produce for a C++-backed package.
"""

from __future__ import annotations

from typing import Final

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

__all__ = ["PROBE_ID", "PyArrowComputeProbeResult", "probe_pyarrow_compute"]

PROBE_ID: Final = "pyarrow_compute_functions"


@frozen(kw_only=True)
class PyArrowComputeProbeResult:
    """Compute functions reported by the loaded PyArrow native library."""

    entries: tuple[SurfaceEntry, ...] = field()
    detail: str = field()
    unreadable: tuple[str, ...] = field(default=())


def probe_pyarrow_compute(*, library_id: str, profile_id: str) -> PyArrowComputeProbeResult:
    """Return the compute functions PyArrow registers at import time.

    Args:
        library_id: Owning library identifier.
        profile_id: Profile this observation is evidence for.

    Returns:
        The probe result.

    """
    import pyarrow as pa
    from pyarrow import compute

    entries: list[SurfaceEntry] = []
    unreadable: list[str] = []
    for name in sorted(compute.list_functions()):
        try:
            function = compute.get_function(name)
        except KeyError, pa.ArrowInvalid, pa.ArrowKeyError:
            unreadable.append(name)
            continue
        attributes = (
            ("function_kind", str(getattr(function, "kind", "unknown"))),
            ("arity", str(getattr(function, "arity", "unknown"))),
            ("kernel_count", str(getattr(function, "num_kernels", 0))),
        )
        doc = getattr(function, "_doc", None)
        summary = getattr(doc, "summary", None)
        entries.append(
            SurfaceEntry(
                library_id=library_id,
                profile_id=profile_id,
                identity=SurfaceId(
                    ecosystem=Ecosystem.PYTHON,
                    package="pyarrow",
                    surface_kind=str(SurfaceKind.COMPUTE_FUNCTION),
                    name=name,
                ),
                surface_kind=SurfaceKind.COMPUTE_FUNCTION,
                description=summary if isinstance(summary, str) else None,
                attributes=attributes,
                availability_conditions=("registered by the loaded native library",),
                evidence_origin=EvidenceOrigin.RUNTIME_REGISTRY,
                resolution_state=ResolutionState.RESOLVED,
            )
        )
    return PyArrowComputeProbeResult(
        entries=tuple(entries),
        detail=f"pyarrow.compute.list_functions in pyarrow {pa.__version__}",
        unreadable=tuple(unreadable),
    )


register_probe(PROBE_ID, probe_pyarrow_compute)
