"""Rule-driven discovery candidates; nominations never imply accepted functionality."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TypedDict

import yaml
from attrs import evolve

from library_guides.evidence_graph import EvidenceGraph
from library_guides.knowledge import Knowledge


class Nomination(TypedDict):
    """A rule match with explicit evidence and unaccepted disposition."""

    binding: str
    families: tuple[str, ...]
    evidence: list[str]
    state: str
    reason: str


def nominate(root: Path, knowledge: Knowledge, rules: Path) -> tuple[Knowledge, list[Nomination]]:
    """Attach declared candidate families using typed signatures and exact documentation.

    Returns:
        Updated candidate-family annotations and unreviewed nomination records.

    """
    configuration = yaml.safe_load(rules.read_text(encoding="utf-8"))
    families = configuration["families"]
    graph = EvidenceGraph(root, knowledge)
    docs: dict[tuple[str, str], list[str]] = {}
    for evidence in knowledge.evidence:
        if evidence.kind in {"statement", "registry"}:
            profile = graph.sources[evidence.source].profile
            docs.setdefault((profile, evidence.subject), []).append(evidence.id)
    output: list[Nomination] = []
    bindings = []
    for binding in knowledge.bindings:
        supporting = docs.get((binding.profile, binding.symbol), [])
        text = "\n".join(
            [
                binding.signature,
                *(graph.selected(graph.evidence[key]).decode() for key in supporting),
            ]
        )
        matched = tuple(
            sorted(
                family
                for family, rule in families.items()
                if re.search(rule["pattern"], text, flags=re.IGNORECASE)
            )
        )
        bindings.append(evolve(binding, families=matched))
        if matched:
            output.append(
                {
                    "binding": binding.id,
                    "families": matched,
                    "evidence": supporting,
                    "state": "candidate",
                    "reason": "pattern matched signature or upstream documentation",
                }
            )
    return evolve(knowledge, bindings=tuple(bindings)), output
