"""Publish modeled alternatives and their exact generated-program witnesses through the corpus."""

from __future__ import annotations

import io
from typing import TYPE_CHECKING

from library_deep_enrichment.corpus.admission import Coordinator, WriterIdentity
from library_deep_enrichment.corpus.backend import CorpusError
from library_deep_enrichment.corpus.contracts import Operation, Release
from library_deep_enrichment.corpus.evidence import stage_blob
from library_deep_enrichment.corpus.schemas import revision_of
from library_deep_enrichment.corpus.validation import validate_records
from library_deep_enrichment.publication.closure import evidence_closure
from library_deep_enrichment.semantics.contracts import Capability, Composition, Task
from library_deep_enrichment.semantics.enrichment_contracts import (
    CompositionEvaluation,
    CompositionWitness,
)

if TYPE_CHECKING:
    from library_deep_enrichment.corpus.store import Corpus, CorpusReader


def render(reader: CorpusReader, evaluations: tuple[CompositionEvaluation, ...]) -> str:
    """Render exact plan outcomes without promoting a finite witness to a universal guarantee.

    Returns:
        A Markdown view with source operations, modeled properties, and explicit witness scope.

    """
    lines = [
        "# Generated composition comparison",
        "",
        "Models describe explicit intermediate state changes. Compiler and execution results apply only to the retained finite inputs.",
        "",
    ]
    witnesses = tuple(
        item
        for item in reader.records("composition_witnesses")
        if isinstance(item, CompositionWitness)
    )
    for evaluation in evaluations:
        plan = reader.get("compositions", evaluation.composition)
        assert isinstance(plan, Composition)
        task = reader.get("tasks", plan.task)
        assert isinstance(task, Task)
        names = []
        for step in plan.steps:
            capability = reader.get("capabilities", step.capability)
            assert isinstance(capability, Capability)
            operation = reader.get("operations", capability.operation)
            assert isinstance(operation, Operation)
            names.append(operation.symbol)
        lines.extend(
            [
                f"## {' → '.join(names)}",
                "",
                f"Task: {task.description}",
                "",
                f"Profile: `{plan.profile}`. Modeled disposition: **{evaluation.disposition}**.",
                "",
                "Final modeled properties:",
                "",
            ]
        )
        lines.extend(f"- `{item.variable}` = `{item.value.text}`" for item in evaluation.outputs)
        matched = tuple(item for item in witnesses if item.evaluation == revision_of(evaluation))
        lines.extend(
            [
                "",
                "Finite witness: "
                + (", ".join(item.disposition for item in matched) if matched else "not executed")
                + ".",
                "",
                f"Evaluation: `{revision_of(evaluation)}`. Plan: `{evaluation.composition}`.",
                "",
                "Invocation and scope qualifications:",
                "",
            ]
        )
        lines.extend(f"- {item}" for item in (*plan.frontier, *evaluation.frontier))
        lines.append("")
    return "\n".join(lines)


def publish(
    corpus: Corpus,
    evaluations: tuple[CompositionEvaluation, ...],
    *,
    expected: str,
    head: str = "release",
) -> str:
    """Publish a closed modeled comparison and actual compiler evidence under a named head.

    Returns:
        The coherent release manifest with the same portable evidence resolver as decisions.

    Raises:
        CorpusError: No evaluation was selected.

    """
    if not evaluations:
        message = "composition publication requires at least one exact evaluation"
        raise CorpusError(message)
    reader = corpus.reader()
    selected = {revision_of(item) for item in evaluations}
    roots = tuple(("composition_evaluations", revision) for revision in sorted(selected)) + tuple(
        ("composition_witnesses", revision_of(item))
        for item in reader.records("composition_witnesses")
        if isinstance(item, CompositionWitness) and item.evaluation in selected
    )
    records = evidence_closure(reader, roots)
    validate_records(reader, records)
    blob, chunks = stage_blob(
        io.BytesIO(render(reader, evaluations).encode()), media_type="text/markdown"
    )
    plans = tuple(reader.get("compositions", item.composition) for item in evaluations)
    release = Release(
        logical_id="release:composition-comparison",
        profile=evaluations[0].profile,
        source_manifest=reader.manifest_id,
        subjects=tuple(sorted(selected)),
        qualifications=(),
        universes=tuple(sorted({plan.universe for plan in plans if isinstance(plan, Composition)})),
        renderer="library-guides.composition-markdown.v1",
        guide_blob=revision_of(blob),
    )
    return Coordinator(
        corpus, WriterIdentity(principal="composition-publication", role="migration")
    ).commit(
        (*records, *chunks, blob, release),
        expected=expected,
        head=head,
        replace=True,
    )
