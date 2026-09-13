"""Retain all main pilot tasks, including their unmodeled consumer obligations."""

from __future__ import annotations

import hashlib
import io
import logging
import re
from collections import Counter
from typing import TYPE_CHECKING

import yaml
from attrs import frozen
from library_deep_enrichment.corpus.admission import Coordinator, WriterIdentity
from library_deep_enrichment.corpus.contracts import Disposition, Operation, Qualification, Release
from library_deep_enrichment.corpus.encoding import CONVERTER, canonical
from library_deep_enrichment.corpus.evidence import stage_blob
from library_deep_enrichment.corpus.schemas import revision_of
from library_deep_enrichment.corpus.store import Corpus
from library_deep_enrichment.publication.closure import evidence_closure
from library_deep_enrichment.publication.export import export_view, import_view
from library_deep_enrichment.publication.releases import read_guide
from library_deep_enrichment.publication.render import RENDERER, render_comparison
from library_deep_enrichment.semantics.contracts import (
    Comparison,
    Interpretation,
    Predicate,
    Requirement,
    Task,
    ValueKind,
)
from library_deep_enrichment.semantics.task_matching import compare, replay
from library_deep_enrichment.semantics.vocabulary import text_value
from library_deep_enrichment.workflows.semantics import build as build_semantics

from pilot.intelligence.qualify_reuse import REPORTS, ROOT, RUN, verify_freeze

if TYPE_CHECKING:
    from library_deep_enrichment.corpus.store import CorpusReader

LOG = logging.getLogger(__name__)
PYTHON = "python-installed-54-25"
RUST = "rust-docsrs-54.1-58.4"

# These are consumer criteria, never mappings from operation IDs to semantic claims.
# Unlisted requirements become explicit unsupported predicates and stay mandatory.
CRITERIA = {
    "rust-results": (
        "consume-results",
        {
            "Stream versus collect": ("documented-result-delivery", "incremental"),
            "Drop behavior": ("documented-drop-cancellation", "drop-stream-aborts-query"),
        },
    ),
    "python-results": (
        "consume-results",
        {"Result type": ("declares-result-carrier", "stream")},
    ),
    "python-placement": (
        "elementwise-add",
        {
            "Representation": ("registered-input-domain", "native-datum-inputs"),
            "Query versus kernel": ("registered-execution-phase", "execution"),
            "Checked versus wrapping overflow": ("documented-integer-overflow-policy", "wrap"),
        },
    ),
    "reverse-python-overflow": (
        "elementwise-add",
        {
            "Checked operation": ("documented-integer-overflow-policy", "error"),
            "No accidental wrapping": ("documented-integer-overflow-policy", "error"),
        },
    ),
    "rust-schema": (
        "reconcile-schema",
        {
            "Nested compatibility": (
                "documented-schema-merge-policy",
                "compatible-recursive-structs",
            )
        },
    ),
}
ASSURANCE_LIMITS = {
    "No blanket operator-memory guarantee",
    "No borrowed Rust cancellation guarantee",
}


@frozen(kw_only=True)
class TaskSpec:
    """Retained task-catalog schema; authoring data is not operation evidence."""

    id: str
    prompt: str
    profile: str
    requirements: tuple[str, ...]


def _unknown(label: str) -> Predicate:
    """Name an unmet consumer obligation without manufacturing evidence.

    Returns:
        A shared criterion reusable by every operation and task with that obligation.

    """
    name = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
    return Predicate(
        logical_id=f"predicate:consumer-{name}",
        name=f"consumer_{name.replace('-', '_')}",
        description=f"Consumer requires: {label}. No extraction or transfer model is supplied by this task definition.",
        value_kind=ValueKind.TEXT,
        allowed_values=("established",),
        exclusive=False,
        interpretations=(Interpretation.UPSTREAM_CONTRACT, Interpretation.WITNESSED),
        template=f"Consumer obligation {label}: {{value}}.",
    )


def _prepare(corpus: Corpus, catalog: list[TaskSpec]) -> dict[str, Predicate]:
    """Admit explicitly unmodeled consumer predicates.

    Returns:
        Current vocabulary including the unmet consumer requirements.

    """
    writer = Coordinator(corpus, WriterIdentity(principal="implementation-agent", role="policy"))
    predicates = {
        item.logical_id: item
        for item in corpus.reader().records("predicates")
        if isinstance(item, Predicate)
    }
    unknowns = {}
    for item in catalog:
        _, modeled = CRITERIA.get(item.id, ("unmodeled-consumer-goal", {}))
        for label in item.requirements:
            if label not in modeled and label not in ASSURANCE_LIMITS:
                predicate = _unknown(label)
                unknowns[predicate.logical_id] = predicate
    writer.commit(tuple(unknowns.values()), expected=corpus.reader().manifest_id)
    predicates.update(unknowns)
    return predicates


def _task(item: TaskSpec, predicates: dict[str, Predicate]) -> Task:
    """Translate retained consumer requirements without inventing operation mappings.

    Returns:
        A task with every substantive requirement still mandatory.

    """
    goal, modeled = CRITERIA.get(item.id, ("unmodeled-consumer-goal", {}))
    requirements = []
    for label in item.requirements:
        if label in ASSURANCE_LIMITS:
            continue
        if label in modeled:
            name, value = modeled[label]
            predicate = predicates[f"predicate:{name}"]
        else:
            predicate, value = _unknown(label), "established"
        requirements.append(
            Requirement(
                predicate=revision_of(predicate),
                value=text_value(value),
                operator="equal",
                interpretations=predicate.interpretations,
                mandatory=True,
            )
        )
    profile = PYTHON if item.profile.startswith("python-installed") else item.profile
    selected = (RUST, PYTHON) if profile == "interop-pilot" else (profile,)
    return Task(
        logical_id=f"task:completion:{item.id}",
        profile=profile,
        profiles=selected,
        goal=goal,
        requirements=tuple(requirements),
        context=(),
        inputs=(),
        preferences=(),
        description=item.prompt
        + ". Consumer criteria are semantic screening only; invocation, full guarantee coverage and assurance limits remain explicit in the attributed assessment.",
    )


def _compare(
    corpus: Corpus, catalog: list[TaskSpec], predicates: dict[str, Predicate]
) -> tuple[list[Task], list[Comparison]]:
    """Compare the full declared profile universe for every retained task.

    Returns:
        Admitted tasks and independently replayed comparisons.

    """
    writer = Coordinator(corpus, WriterIdentity(principal="implementation-agent", role="policy"))
    reader = corpus.reader()
    tasks, comparisons, scopes = [], [], []
    for item in catalog:
        LOG.info("COMPARE %s", item.id)
        task = _task(item, predicates)
        scope, comparison = compare(reader, task)
        tasks.append(task)
        scopes.append(scope)
        comparisons.append(comparison)
    writer.commit((*tasks, *scopes, *comparisons), expected=reader.manifest_id)
    reader = corpus.reader()
    LOG.info("REPLAY %s comparisons", len(comparisons))
    for task, comparison in zip(tasks, comparisons, strict=True):
        assert replay(reader, task, comparison) == comparison
    return tasks, comparisons


def _publish(corpus: Corpus, comparisons: list[Comparison]) -> dict[str, object]:
    """Publish one complete union evidence closure.

    Returns:
        Exact release identities after an independent clean-store restoration.

    """
    reader = corpus.reader()
    LOG.info("CLOSURE")
    records = evidence_closure(
        reader, tuple(("comparisons", revision_of(item)) for item in comparisons)
    )
    guide = (
        "# Main-library task cohort\n\nAuthor and reviewer: the same implementation agent. This is an attributed assessment, not independent review.\n\n"
        + "\n\n---\n\n".join(render_comparison(reader, item) for item in comparisons)
    )
    blob, chunks = stage_blob(io.BytesIO(guide.encode()), media_type="text/markdown")
    release = Release(
        logical_id="release:completion-main-task-cohort",
        profile="pilot-main-cohort",
        source_manifest=reader.manifest_id,
        subjects=tuple(revision_of(item) for item in comparisons),
        qualifications=tuple(
            revision_of(item)
            for item in records
            if isinstance(item, Qualification) and item.disposition == Disposition.COMPLETE
        ),
        universes=tuple(item.universe for item in comparisons),
        renderer=f"cohort-concatenation.v1/{RENDERER}",
        guide_blob=revision_of(blob),
    )
    LOG.info("PUBLISH %s closure records", len(records))
    head = "completion-task-cohort"
    manifest = Coordinator(
        corpus, WriterIdentity(principal="release-coordinator", role="migration")
    ).commit(
        (*records, *chunks, blob, release),
        expected=corpus.reader(head).manifest_id,
        head=head,
        replace=True,
    )
    work = RUN / f"main-task-cohort-{manifest[:16]}"
    work.mkdir(exist_ok=True)
    destination = work / "export"
    LOG.info("EXPORT %s", manifest)
    export_view(corpus.reader(head), destination)
    restored = Corpus(work / "restored", max_rows=2_500_000)
    assert import_view(restored, destination) == manifest
    assert read_guide(restored.reader("release"), release) == guide
    (ROOT / "pilot/intelligence/guides/completion-main-tasks.md").write_text(guide)
    return {
        "source_manifest": reader.manifest_id,
        "release_manifest": manifest,
        "release": revision_of(release),
        "export": str(destination),
        "guide_sha256": hashlib.sha256(guide.encode()).hexdigest(),
        "restored_identically": True,
    }


def _summarize(
    reader: CorpusReader,
    catalog: list[TaskSpec],
    tasks: list[Task],
    comparisons: list[Comparison],
) -> list[dict[str, object]]:
    """Describe exact eligibility and unmodeled requirements.

    Returns:
        One evidence summary per retained task.

    """
    operations = {
        revision_of(item): item
        for item in reader.records("operations")
        if isinstance(item, Operation)
    }
    results: list[dict[str, object]] = []
    for item, task, comparison in zip(catalog, tasks, comparisons, strict=True):
        results.append(
            {
                "task": item.id,
                "task_revision": revision_of(task),
                "comparison": revision_of(comparison),
                "universe": comparison.universe,
                "universe_count": len(comparison.candidates),
                "counts": dict(
                    Counter(candidate.disposition for candidate in comparison.candidates)
                ),
                "eligible": [
                    {
                        "revision": candidate.operation,
                        "symbol": operations[candidate.operation].symbol,
                    }
                    for candidate in comparison.candidates
                    if candidate.disposition == "eligible"
                ],
                "modeled_requirements": list(CRITERIA.get(item.id, ("", {}))[1]),
                "unmodeled_requirements": [
                    label
                    for label in item.requirements
                    if label not in CRITERIA.get(item.id, ("", {}))[1]
                    and label not in ASSURANCE_LIMITS
                ],
                "assurance_limits": [
                    label for label in item.requirements if label in ASSURANCE_LIMITS
                ],
            }
        )
    return results


def run() -> None:
    """Compare all 22 retained main-library tasks and release their union closure."""
    freeze = verify_freeze()
    corpus = Corpus(
        ROOT.parents[1] / ".cache/library-guides-intelligence/pilot-v4/corpus", max_rows=2_500_000
    )
    catalog = CONVERTER.structure(
        yaml.safe_load((ROOT / "pilot/tasks.yaml").read_bytes())["tasks"], list[TaskSpec]
    )
    catalog = [item for item in catalog if item.id not in {"pydantic-input", "serde-input"}]
    predicates = _prepare(corpus, catalog)
    build_semantics(corpus)
    assert build_semantics(corpus).reused
    tasks, comparisons = _compare(corpus, catalog, predicates)
    report = _publish(corpus, comparisons)
    report.update(
        {
            "freeze": freeze,
            "author": "implementation-agent",
            "reviewer": "same implementation-agent",
            "independent_review": False,
            "tasks": _summarize(corpus.reader(), catalog, tasks, comparisons),
        }
    )
    assert verify_freeze() == freeze
    (REPORTS / "completion-main-task-cohort.json").write_bytes(canonical(report) + b"\n")
    LOG.info("DONE %s", report["release_manifest"])


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
