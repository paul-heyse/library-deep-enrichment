"""Evidence packets: the unit of work for deriving behavior.

The knowledge base is not a summary of an existing document. Behaviors are
*derived* here from primary evidence - the library's own API surface, its doc
comments, its registries, its configuration - and a locally authored reference,
where one exists, is supplied only as an unverified prior to compare against.

That ordering is deliberate. Grounding a derivation in a hand-written document
inherits that document's errors and, worse, its blind spots: anything the author
never noticed stays invisible. Deriving from evidence and *then* diffing against
the prior turns both directions into findings - a claim the evidence contradicts,
and a behavior the evidence supports that nobody wrote down.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from attrs import field, frozen

from library_deep_enrichment.store.digests import digest_mapping

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from library_deep_enrichment.adapters.docs.behaviors import Behavior as GroundingClaim
    from library_deep_enrichment.models.records import ApiBinding, SurfaceEntry

__all__ = [
    "EvidenceItem",
    "EvidencePacket",
    "PacketBudget",
    "PacketRequest",
    "build_packets",
]

_DEFAULT_MAX_ITEMS: Final = 40
_DEFAULT_MAX_DOC_CHARS: Final = 24_000


@frozen(kw_only=True)
class PacketBudget:
    """Bounds on one packet, so model cost stays predictable per unit of work."""

    max_items: int = field(default=_DEFAULT_MAX_ITEMS)
    max_documentation_chars: int = field(default=_DEFAULT_MAX_DOC_CHARS)


@frozen(kw_only=True)
class EvidenceItem:
    """One piece of primary evidence a behavior may be derived from."""

    evidence_id: str = field()
    kind: str = field()
    identity: str = field()
    detail: str = field(default="")
    documentation: str = field(default="")
    attributes: tuple[tuple[str, str], ...] = field(default=())

    def documentation_chars(self) -> int:
        """Return how much upstream prose this item contributes.

        Returns:
            Character count of the attached documentation.

        """
        return len(self.documentation)


@frozen(kw_only=True)
class EvidencePacket:
    """Everything needed to derive the behaviors of one coherent group.

    ``grounding`` is explicitly separated from ``evidence`` and is never
    presented as authoritative. A derivation must stand on the evidence; the
    grounding exists to be agreed with, contradicted, or found incomplete.
    """

    packet_id: str = field()
    library_id: str = field()
    profile_id: str = field()
    group_key: str = field()
    evidence: tuple[EvidenceItem, ...] = field()
    grounding: tuple[str, ...] = field(default=())
    open_questions: tuple[str, ...] = field(default=())

    def digest(self) -> str:
        """Return the cache key for this packet's content.

        Returns:
            Digest over every fact the packet presents.

        """
        return digest_mapping(
            {
                "group_key": self.group_key,
                "library_id": self.library_id,
                "profile_id": self.profile_id,
                "evidence": [
                    [
                        item.evidence_id,
                        item.kind,
                        item.identity,
                        item.detail,
                        item.documentation,
                        list(item.attributes),
                    ]
                    for item in self.evidence
                ],
                "grounding": list(self.grounding),
                "open_questions": list(self.open_questions),
            }
        )

    def documentation_chars(self) -> int:
        """Return total upstream prose in the packet.

        Returns:
            Summed character count.

        """
        return sum(item.documentation_chars() for item in self.evidence)

    def summary(self) -> str:
        """Describe the packet in one line.

        Returns:
            A short human-readable summary.

        """
        return (
            f"{self.packet_id}: {len(self.evidence)} evidence items, "
            f"{self.documentation_chars():,} doc chars, "
            f"{len(self.grounding)} grounding claim(s)"
        )


def _group_key_for(public_path: str) -> str:
    """Return the module-level group a public path belongs to.

    Returns:
        The path with its final segment removed, or the path itself.

    """
    for separator in ("::", "."):
        if separator in public_path:
            return public_path.rsplit(separator, 1)[0]
    return public_path


@frozen(kw_only=True)
class PacketRequest:
    """One profile's evidence, ready to be grouped into packets."""

    library_id: str = field()
    profile_id: str = field()
    bindings: Sequence[ApiBinding] = field()
    documentation: Mapping[str, str] = field(factory=dict)
    surfaces: Sequence[SurfaceEntry] = field(default=())
    grounding: Mapping[str, Sequence[GroundingClaim]] = field(factory=dict)
    budget: PacketBudget = field(factory=PacketBudget)


def build_packets(request: PacketRequest) -> tuple[EvidencePacket, ...]:
    """Group evidence into bounded packets, one per module-level group.

    Returns:
        Packets in deterministic order.

    """
    bindings = request.bindings
    library_id = request.library_id
    profile_id = request.profile_id
    documentation = request.documentation
    surfaces = request.surfaces
    limits = request.budget
    priors = request.grounding
    grouped: dict[str, list[EvidenceItem]] = {}

    for binding in bindings:
        path = binding.identity.public_path
        grouped.setdefault(_group_key_for(path), []).append(
            EvidenceItem(
                evidence_id=f"api:{path}",
                kind="api_item",
                identity=path,
                detail=binding.signature or binding.identity.item_kind,
                documentation=documentation.get(path, ""),
                attributes=(
                    ("item_kind", binding.identity.item_kind),
                    ("package", binding.identity.package),
                    ("resolution", str(binding.resolution_state)),
                ),
            )
        )

    for surface in surfaces:
        name = surface.identity.name
        grouped.setdefault(f"{surface.surface_kind}", []).append(
            EvidenceItem(
                evidence_id=f"surface:{name}",
                kind=str(surface.surface_kind),
                identity=name,
                detail=surface.description or "",
                documentation=documentation.get(name, ""),
                attributes=surface.attributes,
            )
        )

    packets: list[EvidencePacket] = []
    for group_key in sorted(grouped):
        items = sorted(grouped[group_key], key=_by_identity)
        for chunk_index, chunk in enumerate(_chunk(items, limits)):
            suffix = f"#{chunk_index + 1}" if chunk_index else ""
            claims = priors.get(group_key, ())
            packets.append(
                EvidencePacket(
                    packet_id=f"{library_id}:{group_key}{suffix}",
                    library_id=library_id,
                    profile_id=profile_id,
                    group_key=group_key,
                    evidence=tuple(chunk),
                    grounding=tuple(f"{claim.behavior_id} {claim.title}" for claim in claims),
                    open_questions=(
                        "Which behaviors does this evidence establish that no prior states?",
                        "Does any prior claim contradict this evidence?",
                        "Which behaviors need executable evidence rather than a doc comment?",
                    ),
                )
            )
    return tuple(packets)


def _by_identity(item: EvidenceItem) -> str:
    return item.identity


def _chunk(
    items: Sequence[EvidenceItem],
    limits: PacketBudget,
) -> list[list[EvidenceItem]]:
    chunks: list[list[EvidenceItem]] = []
    current: list[EvidenceItem] = []
    characters = 0
    for item in items:
        too_many = len(current) >= limits.max_items
        too_long = characters + item.documentation_chars() > limits.max_documentation_chars
        if current and (too_many or too_long):
            chunks.append(current)
            current = []
            characters = 0
        current.append(item)
        characters += item.documentation_chars()
    if current:
        chunks.append(current)
    return chunks
