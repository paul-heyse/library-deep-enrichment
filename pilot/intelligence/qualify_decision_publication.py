"""Publish actual checked-add counterfactuals and explicit consumer preference evidence."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from attrs import evolve

from library_deep_enrichment.corpus.admission import Coordinator, WriterIdentity
from library_deep_enrichment.corpus.contracts import Release
from library_deep_enrichment.corpus.encoding import CONVERTER, canonical
from library_deep_enrichment.corpus.schemas import revision_of
from library_deep_enrichment.corpus.store import Corpus
from library_deep_enrichment.paths import default_corpus, intelligence_root
from library_deep_enrichment.publication.export import export_view, import_view
from library_deep_enrichment.publication.objectives import deltas, evidence
from library_deep_enrichment.publication.releases import publish, read_guide
from library_deep_enrichment.semantics.comparison import counterfactuals
from library_deep_enrichment.semantics.contracts import Comparison, Interpretation, Task
from library_deep_enrichment.semantics.decision_contracts import Objective, PreferencePolicy
from library_deep_enrichment.semantics.task_matching import compare
from library_deep_enrichment.semantics.vocabulary import text_value


def _publish(corpus: Corpus, comparison: Comparison, name: str) -> dict[str, object]:
    head = "release-" + name
    manifest = publish(corpus, comparison, expected=corpus.reader(head).manifest_id, head=head)
    reader = corpus.reader(head)
    release = next(item for item in reader.records("releases") if isinstance(item, Release))
    guide = read_guide(reader, release)
    Path(f"tooling/library_deep_enrichment/pilot/intelligence/guides/{name}.md").write_text(
        guide, encoding="utf-8"
    )
    destination = intelligence_root() / "decision-publication" / uuid4().hex
    export_view(reader, destination)
    restored = Corpus(destination.with_name(destination.name + "-restored"))
    assert import_view(restored, destination) == manifest
    return {
        "head": head,
        "manifest": manifest,
        "export": str(destination),
        "restored_manifest": restored.reader("release").manifest_id,
        "comparison": revision_of(comparison),
        "preferred": comparison.preferred,
        "objective_assertions": len(evidence(reader, comparison)),
        "counterfactuals": len(deltas(reader, comparison)),
    }


def main() -> None:
    """Retain both hard overflow constraints and a separately declared soft preference."""
    corpus = Corpus(default_corpus(), max_rows=2_500_000)
    reader = corpus.reader()
    original = reader.lookup("tasks", "task:integer-add-error", "python-installed-54-25")
    assert isinstance(original, Task)
    policy = PreferencePolicy(
        logical_id="consumer:prefer-overflow-error",
        strategy="lexicographic",
        objectives=(
            Objective(
                predicate=original.requirements[1].predicate,
                direction="ordered",
                order=(text_value("error"), text_value("wrap")),
                interpretations=(Interpretation.UPSTREAM_CONTRACT,),
            ),
        ),
        rationale="For this demonstration both overflow policies are permitted; the consumer explicitly prefers a reported error. This is a consumer choice, not a measured speed or memory claim.",
    )
    preference_task = evolve(
        original,
        logical_id="task:integer-add-prefer-error",
        requirements=original.requirements[:1],
        preferences=(revision_of(policy),),
        description="Choose element-wise addition with an explicit preference for overflow errors",
    )
    writer = Coordinator(corpus, WriterIdentity(principal="attributed-pilot-consumer"))
    writer.commit((policy, preference_task), expected=reader.manifest_id)
    source = corpus.reader()
    changes = tuple(counterfactuals(source, original))
    universe, preferred = compare(source, preference_task)
    writer.commit((*changes, preference_task, universe, preferred), expected=source.manifest_id)
    baseline = next(
        item
        for item in changes
        if isinstance(item, Comparison) and item.task == revision_of(original)
    )
    reports = [
        _publish(corpus, baseline, "integer-add-with-counterfactuals"),
        _publish(corpus, preferred, "integer-add-with-preferences"),
    ]
    assert reports[0]["counterfactuals"]
    assert reports[1]["objective_assertions"]
    report = {
        "source_manifest": reader.manifest_id,
        "analysis_manifest": corpus.reader().manifest_id,
        "policy": CONVERTER.unstructure(policy),
        "author": "implementation-agent",
        "reviewer": "same implementation-agent",
        "independent_review": False,
        "releases": reports,
    }
    Path(
        "tooling/library_deep_enrichment/pilot/intelligence/reports/resume-decision-publication.json"
    ).write_bytes(canonical(report) + b"\n")


if __name__ == "__main__":
    main()
