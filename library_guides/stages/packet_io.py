"""Assemble and render evidence packets for derivation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from library_guides.adapters.docs.behaviors import index_behaviors_file
from library_guides.manifest import load_library_manifest, load_stack_manifest
from library_guides.models.records import ApiBinding, Observation, SurfaceEntry
from library_guides.packets import PacketBudget, PacketRequest, build_packets
from library_guides.stages.extract_documentation import DOC_PREDICATE
from library_guides.stages.paths import api_path, documentation_path, surfaces_path
from library_guides.store.jsonl import read_records

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path

    from library_guides.adapters.docs.behaviors import Behavior as GroundingClaim
    from library_guides.packets import EvidencePacket

__all__ = ["evidence_reference_ids", "packets_for_library", "render_packet"]


def _grounding_for_stack(stack_id: str, *, repository_root: Path) -> tuple[GroundingClaim, ...]:
    claims: list[GroundingClaim] = []
    for entry in load_stack_manifest(stack_id).documents:
        path = repository_root / entry.path
        if not path.is_file():
            continue
        index = index_behaviors_file(path, doc_id=entry.doc_id, document_path=entry.path)
        claims.extend(index.behaviors)
    return tuple(claims)


def _grounding_by_group(
    claims: Sequence[GroundingClaim],
) -> dict[str, list[GroundingClaim]]:
    """Group prior claims by the identifiers they cite.

    A prior claim is offered to the packet whose evidence it talks about. Any
    claim citing nothing the evidence names is simply not offered, which keeps a
    packet from being padded with unrelated prose.

    Returns:
        Mapping of cited identifier to the claims citing it.

    """
    grouped: dict[str, list[GroundingClaim]] = {}
    for claim in claims:
        for identifier in claim.api_shaped_identifiers:
            grouped.setdefault(identifier, []).append(claim)
    return grouped


def packets_for_library(
    library_id: str,
    *,
    repository_root: Path,
    stack_id: str | None = None,
    budget: PacketBudget | None = None,
) -> tuple[EvidencePacket, ...]:
    """Return every evidence packet for one library's first profile.

    Returns:
        Packets in deterministic order.

    """
    manifest = load_library_manifest(library_id)
    profile = manifest.profiles[0]
    bindings = list(
        read_records(
            api_path(library_id, profile.profile_id, repository_root=repository_root), ApiBinding
        )
    )
    doc_file = documentation_path(library_id, profile.profile_id, repository_root=repository_root)
    documentation: Mapping[str, str] = (
        {
            record.subject: record.object_value
            for record in read_records(doc_file, Observation)
            if record.predicate == DOC_PREDICATE
        }
        if doc_file.is_file()
        else {}
    )
    surface_file = surfaces_path(library_id, profile.profile_id, repository_root=repository_root)
    surfaces = list(read_records(surface_file, SurfaceEntry)) if surface_file.is_file() else []

    grounding: dict[str, list[GroundingClaim]] = {}
    if stack_id is not None:
        by_identifier = _grounding_by_group(
            _grounding_for_stack(stack_id, repository_root=repository_root)
        )
        for binding in bindings:
            path = binding.identity.public_path
            leaf = path.rsplit("::", 1)[-1].rsplit(".", 1)[-1]
            claims = by_identifier.get(path, []) + by_identifier.get(leaf, [])
            if claims:
                group = path.rsplit("::", 1)[0] if "::" in path else path
                grouped = grounding.setdefault(group, [])
                grouped.extend(claim for claim in claims if claim not in grouped)

    return build_packets(
        PacketRequest(
            library_id=library_id,
            profile_id=profile.profile_id,
            bindings=bindings,
            documentation=documentation,
            surfaces=surfaces,
            grounding=grounding,
            budget=budget or PacketBudget(),
        )
    )


def evidence_reference_ids(packets: Sequence[EvidencePacket]) -> frozenset[str]:
    """Return every evidence reference the packets actually offered.

    Returns:
        The set of valid evidence identifiers.

    """
    return frozenset(item.evidence_id for packet in packets for item in packet.evidence)


def render_packet(packet: EvidencePacket) -> str:
    """Return one packet as a readable derivation brief.

    Evidence and grounding are rendered under separate headings, and the
    grounding heading says plainly that it is unverified. A derivation that
    cannot tell the two apart will quietly inherit the prior's mistakes.

    Returns:
        The rendered brief.

    """
    lines = [
        f"# Derivation packet: {packet.packet_id}",
        "",
        f"library: {packet.library_id}   profile: {packet.profile_id}",
        f"group: {packet.group_key}   digest: {packet.digest()[:16]}",
        "",
        "## Evidence (authoritative)",
        "",
    ]
    for item in packet.evidence:
        attributes = " ".join(f"{key}={value}" for key, value in item.attributes)
        lines.append(f"### {item.evidence_id}")
        lines.append(f"- kind: {item.kind}   {attributes}")
        if item.detail:
            lines.append(f"- detail: {item.detail}")
        if item.documentation:
            lines.append("- upstream documentation:")
            lines.extend(f"    {row}" for row in item.documentation.splitlines())
        lines.append("")
    if packet.grounding:
        lines.extend(
            [
                "## Prior claims (UNVERIFIED - compare against, do not adopt)",
                "",
                *(f"- {claim}" for claim in packet.grounding),
                "",
            ]
        )
    lines.extend(["## Questions", "", *(f"- {question}" for question in packet.open_questions)])
    return "\n".join(lines)
