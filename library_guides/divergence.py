"""Compare derived behaviors against the prior documents, in both directions.

A single "coverage" number hides the two results that matter. Deriving from
evidence and then diffing against a hand-written prior produces four buckets, and
three of them are findings:

* **novel** - the evidence supports a behavior no prior document contains. This
  is the reason to derive rather than summarize.
* **contradicts_prior** - the evidence disagrees with what a prior asserts.
* **refined** - the prior is broadly right but states a sufficient condition as
  though it were necessary, or omits a condition the evidence shows.
* **prior_only** - a prior claim nothing derived has corroborated. Not yet an
  error: it may be true and simply outside what the acquired evidence covers, so
  it is reported as an open obligation rather than a defect.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from attrs import field, frozen

from library_guides.derivation import Agreement

if TYPE_CHECKING:
    from collections.abc import Sequence

    from library_guides.adapters.docs.behaviors import Behavior as GroundingClaim
    from library_guides.derivation import DerivedBehavior

__all__ = ["DivergenceReport", "compare"]


@frozen(kw_only=True)
class DivergenceReport:
    """What deriving from evidence found, relative to the prior documents."""

    library_id: str = field()
    profile_id: str = field()
    derived_total: int = field()
    packets_derived: int = field()
    packets_available: int = field()
    buckets: dict[str, int] = field()
    prior_total: int = field()
    prior_corroborated: int = field()

    @property
    def novel_rate(self) -> float:
        """Share of derived behaviors that no prior document contains.

        Returns:
            A value in ``[0, 1]``.

        """
        if not self.derived_total:
            return 0.0
        return self.buckets.get(str(Agreement.NOVEL), 0) / self.derived_total

    @property
    def behaviors_per_packet(self) -> float:
        """Average derived behaviors per packet processed.

        Returns:
            Behaviors per packet, or zero when nothing was derived.

        """
        return self.derived_total / self.packets_derived if self.packets_derived else 0.0

    def describe(self) -> str:
        """Return the report as readable lines.

        Returns:
            A multi-line summary with the denominators intact.

        """
        findings = self.buckets.get(str(Agreement.NOVEL), 0) + self.buckets.get(
            str(Agreement.CONTRADICTS_PRIOR), 0
        )
        coverage = self.packets_derived / self.packets_available if self.packets_available else 0.0
        return "\n".join(
            [
                f"{self.library_id}/{self.profile_id}",
                (
                    f"  derived      {self.derived_total:,} behaviors from "
                    f"{self.packets_derived}/{self.packets_available:,} packets "
                    f"({coverage:.1%} of packets, {self.behaviors_per_packet:.1f} per packet)"
                ),
                f"  buckets      {self.buckets}",
                f"  novel rate   {self.novel_rate:.0%}  ({findings} findings)",
                (
                    f"  prior claims {self.prior_corroborated:,}/{self.prior_total:,} "
                    f"corroborated by a derived behavior"
                ),
            ]
        )


def compare(
    derived: Sequence[DerivedBehavior],
    priors: Sequence[GroundingClaim],
    *,
    library_id: str,
    profile_id: str,
    packets_available: int,
) -> DivergenceReport:
    """Return the two-directional comparison for one profile.

    Args:
        derived: Behaviors this process asserted.
        priors: Prior claims from the locally authored documents.
        library_id: Owning library identifier.
        profile_id: Profile identifier.
        packets_available: How many packets exist, so partial runs stay visible.

    Returns:
        The divergence report.

    """
    buckets: dict[str, int] = dict.fromkeys((item.value for item in Agreement), 0)
    referenced: set[str] = set()
    for behavior in derived:
        buckets[str(behavior.agreement)] += 1
        referenced.update(behavior.prior_refs)
    corroborated = sum(1 for claim in priors if claim.behavior_id in referenced)
    return DivergenceReport(
        library_id=library_id,
        profile_id=profile_id,
        derived_total=len(derived),
        packets_derived=len({behavior.packet_id for behavior in derived}),
        packets_available=packets_available,
        buckets=buckets,
        prior_total=len(priors),
        prior_corroborated=corroborated,
    )
