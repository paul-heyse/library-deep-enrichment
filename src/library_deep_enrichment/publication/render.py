"""Render task decisions directly from qualified computational records."""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

from library_deep_enrichment.corpus.contracts import Operation
from library_deep_enrichment.corpus.schemas import revision_of
from library_deep_enrichment.publication.objectives import deltas, evidence, policies
from library_deep_enrichment.semantics.contracts import Comparison, Predicate, Task

if TYPE_CHECKING:
    from library_deep_enrichment.corpus.store import CorpusReader

RENDERER = "library-guides.structured-decision-markdown.v3"
MAX_GUIDE_ALTERNATIVES = 20


def _names(reader: CorpusReader, operations: tuple[str, ...]) -> str:
    return (
        ", ".join(
            f"`{item.symbol}`"
            for item in reader.get_many("operations", operations)
            if isinstance(item, Operation)
        )
        or "none"
    )


def _preferences(reader: CorpusReader, comparison: Comparison) -> list[str]:
    selected = policies(reader, comparison)
    if not selected:
        return []
    lines = ["## Consumer preferences", ""]
    for policy in selected:
        lines.extend(
            [
                f"Strategy: **{policy.strategy}**. Policy: `{revision_of(policy)}`.",
                "",
                policy.rationale,
                "",
            ]
        )
        for objective in policy.objectives:
            predicate = reader.get("predicates", objective.predicate)
            assert isinstance(predicate, Predicate)
            order = " → ".join(value.text for value in objective.order)
            lines.append(
                f"- `{predicate.name}`: {objective.direction}"
                + (f" ({order})" if order else "")
                + "."
            )
        lines.append("")
    lines.extend(
        [
            f"Retained preference frontier: {_names(reader, comparison.preferred)}.",
            "",
            "Candidates with unresolved objective values remain on the frontier. Preference does not establish invocation compatibility or a universal optimum.",
            "",
        ]
    )
    observations = evidence(reader, comparison)
    for assertion in observations[:MAX_GUIDE_ALTERNATIVES]:
        predicate = reader.get("predicates", assertion.predicate)
        assert isinstance(predicate, Predicate)
        lines.append(
            f"- {_names(reader, (assertion.subject,))}: `{predicate.name} = {assertion.value.text}`, **{assertion.state}**, {assertion.interpretation}; assertion `{revision_of(assertion)}`."
        )
    if len(observations) > MAX_GUIDE_ALTERNATIVES:
        lines.append(
            f"- All {len(observations)} objective evidence assertions remain in the portable closure; this display shows the first {MAX_GUIDE_ALTERNATIVES}."
        )
    lines.append("")
    return lines


def _changes(reader: CorpusReader, comparison: Comparison) -> list[str]:
    changes = deltas(reader, comparison)
    if not changes:
        return []
    lines = [
        "## Computed requirement changes",
        "",
        "Each case changes one requirement and retains the other task context. These are checked comparisons over the same admitted candidate population.",
        "",
    ]
    for change in changes:
        lines.extend(
            [
                f"- Requirement {change.requirement + 1}: `{change.before.text}` → `{change.after.text}`. Newly eligible: {_names(reader, change.became_eligible)}. No longer eligible: {_names(reader, change.ceased_eligible)}. Delta `{revision_of(change)}`.",
            ]
        )
    lines.append("")
    return lines


def render_comparison(reader: CorpusReader, comparison: Comparison) -> str:
    """Render exact outcomes and evidence identifiers without inventing a narrative.

    Returns:
        A portable Markdown decision view, including unknown alternatives and limits.

    """
    task = reader.get("tasks", comparison.task)
    assert isinstance(task, Task)
    lines = [
        f"# {task.description}",
        "",
        f"Profile: `{task.profile}`.",
        "",
        f"Comparison: `{revision_of(comparison)}`. Universe: `{comparison.universe}`.",
        "",
        "Candidates are drawn from the admitted interface universe. Retrieval rank does not exclude alternatives.",
        "",
    ]
    predicates = {
        revision_of(item): item
        for item in reader.records("predicates")
        if isinstance(item, Predicate)
    }
    counts = Counter(candidate.disposition for candidate in comparison.candidates)
    lines.extend(
        [
            f"Compared {len(comparison.candidates)} admitted operations: "
            + ", ".join(f"{count} {state}" for state, count in sorted(counts.items()))
            + ".",
            "",
            "Eligibility addresses the stated semantic requirements. Native invocation and unmodeled properties remain separate checks.",
            "",
        ]
    )
    order = {"eligible": 0, "conditional": 1, "rejected": 2}
    candidates = sorted(
        comparison.candidates,
        key=lambda candidate: (
            order.get(candidate.disposition, 3),
            -sum(bool(result.assertions) for result in candidate.requirements),
            candidate.operation,
        ),
    )
    for candidate in candidates[:MAX_GUIDE_ALTERNATIVES]:
        operation = reader.get("operations", candidate.operation)
        assert isinstance(operation, Operation)
        lines.extend(
            [
                f"## {operation.symbol}",
                "",
                f"Disposition: **{candidate.disposition}**.",
                "",
                f"Interface: `{operation.signature}`.",
                "",
            ]
        )
        for result in candidate.requirements:
            name = predicates[result.predicate].name
            lines.append(
                f"- `{name} = {result.required.text}`: **{result.state}**. {result.reason}."
            )
            if result.assertions:
                lines.append(
                    "  Evidence assertions: "
                    + ", ".join(f"`{item}`" for item in result.assertions)
                    + "."
                )
        if candidate.reversing_conditions:
            lines.extend(["", "Re-evaluation triggers:", ""])
            lines.extend(f"- {condition}." for condition in candidate.reversing_conditions)
        lines.append("")
    if len(candidates) > MAX_GUIDE_ALTERNATIVES:
        lines.extend(
            [
                f"The remaining {len(candidates) - MAX_GUIDE_ALTERNATIVES} alternatives and all individual assessments are retained in the comparison record `{revision_of(comparison)}`. This display limit does not narrow the candidate universe.",
                "",
            ]
        )
    lines.extend(_preferences(reader, comparison))
    lines.extend(_changes(reader, comparison))
    lines.extend(["## Unresolved scope", "", *[f"- {item}." for item in comparison.unresolved], ""])
    return "\n".join(lines)
