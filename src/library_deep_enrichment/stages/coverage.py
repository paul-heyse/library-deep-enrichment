"""Coverage accounting across the four axes.

Every fraction is reported with its numerator, denominator, exclusions and
unresolved items. A bare percentage hides whether the denominator was complete,
and a catalog-only route earns discovery coverage but never decision coverage.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from attrs import field, frozen

from library_deep_enrichment.models.enums import ResolutionState

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from library_deep_enrichment.models.records import ApiBinding, ExtractionReceipt, SurfaceEntry

__all__ = [
    "COVERAGE_AXES",
    "AxisCoverage",
    "CoverageReport",
    "FacetTally",
    "surface_axis",
]

COVERAGE_AXES: Final = ("surface", "use_case", "decision", "composition")

FACETS: Final = (
    "mentioned",
    "signature_available",
    "behavior_explained",
    "conditions_explained",
    "alternative_compared",
    "example_present",
    "example_executed",
)


@frozen(kw_only=True)
class FacetTally:
    """How many items satisfy each independent facet."""

    counts: Mapping[str, int] = field()

    def as_rows(self) -> tuple[tuple[str, int], ...]:
        """Return the facets in declaration order.

        Returns:
            Facet name and count pairs.

        """
        return tuple((facet, self.counts.get(facet, 0)) for facet in FACETS)


@frozen(kw_only=True)
class AxisCoverage:
    """One coverage axis, reported with everything needed to judge it."""

    axis: str = field()
    numerator: int = field()
    denominator: int = field()
    unresolved: int = field(default=0)
    excluded: tuple[tuple[str, int], ...] = field(default=())
    denominator_is_complete: bool = field(default=True)
    facets: FacetTally | None = field(default=None)
    note: str = field(default="")

    @property
    def fraction(self) -> float:
        """The covered share of the declared denominator.

        Returns:
            A value in ``[0, 1]``; zero when the denominator is empty.

        """
        return self.numerator / self.denominator if self.denominator else 0.0

    def describe(self) -> str:
        """Return the axis as a line that cannot be misread as a bare percentage.

        Returns:
            A one-line description.

        """
        scope = "declared inventory" if self.denominator_is_complete else "observed inventory"
        excluded = sum(count for _, count in self.excluded)
        return (
            f"{self.axis}: {self.numerator:,}/{self.denominator:,} of the {scope} "
            f"({self.fraction:.1%}); {self.unresolved:,} unresolved, {excluded:,} excluded"
        )


@frozen(kw_only=True)
class CoverageReport:
    """Coverage for one library profile across every axis."""

    library_id: str = field()
    profile_id: str = field()
    axes: tuple[AxisCoverage, ...] = field()

    def axis(self, name: str) -> AxisCoverage | None:
        """Return one axis by name.

        Returns:
            The axis, or ``None`` when it was not computed.

        """
        for entry in self.axes:
            if entry.axis == name:
                return entry
        return None

    def describe(self) -> str:
        """Return every axis as readable lines.

        Returns:
            One line per axis.

        """
        head = f"{self.library_id}/{self.profile_id}"
        return "\n".join([head, *(f"  {axis.describe()}" for axis in self.axes)])


def surface_axis(
    bindings: Sequence[ApiBinding],
    surfaces: Sequence[SurfaceEntry],
    *,
    routed_paths: frozenset[str],
    excluded: Sequence[tuple[str, int]],
    receipt: ExtractionReceipt,
) -> AxisCoverage:
    """Return surface coverage: how much of the declared inventory has a route.

    Args:
        bindings: In-surface API bindings for the profile.
        surfaces: Non-symbol surfaces for the profile.
        routed_paths: Public paths and surface names a guide currently routes to.
        excluded: Packages excluded from the surface, with counts.
        receipt: The extraction receipt, which decides whether the denominator
            may be described as complete.

    Returns:
        The surface axis.

    """
    identifiers = {binding.identity.public_path for binding in bindings}
    identifiers.update(entry.identity.name for entry in surfaces)
    unresolved = sum(
        1 for binding in bindings if binding.resolution_state is not ResolutionState.RESOLVED
    )
    covered = len(identifiers & routed_paths)
    return AxisCoverage(
        axis="surface",
        numerator=covered,
        denominator=len(identifiers),
        unresolved=unresolved,
        excluded=tuple(excluded),
        denominator_is_complete=receipt.authorizes_absence_claim(),
        facets=FacetTally(counts={"mentioned": covered, "signature_available": len(identifiers)}),
        note=(
            "A route proves the item is discoverable. It does not establish that "
            "its semantics or alternatives are explained."
        ),
    )
