"""Exercise unrelated libraries using the recorded core freeze and data-only packs."""

from __future__ import annotations

import hashlib
import json
import logging
import sys
from collections import Counter
from pathlib import Path

from attrs import asdict, evolve

from library_deep_enrichment.corpus.admission import Coordinator, WriterIdentity
from library_deep_enrichment.corpus.contracts import Operation, Release
from library_deep_enrichment.corpus.encoding import canonical
from library_deep_enrichment.corpus.native_contracts import NativeArtifact
from library_deep_enrichment.corpus.schemas import revision_of
from library_deep_enrichment.corpus.store import Corpus
from library_deep_enrichment.paths import implementation_root
from library_deep_enrichment.publication.export import export_view, import_view
from library_deep_enrichment.publication.releases import publish, read_guide
from library_deep_enrichment.semantic_packs import install
from library_deep_enrichment.semantics.comparison import counterfactuals
from library_deep_enrichment.semantics.contracts import (
    Comparison,
    Interpretation,
    Requirement,
    Task,
)
from library_deep_enrichment.semantics.task_matching import compare
from library_deep_enrichment.semantics.vocabulary import approve_rules, foundation, text_value
from library_deep_enrichment.workflows import enrichment, semantics, shapes
from library_deep_enrichment.workflows.python_documents import build as documents
from library_deep_enrichment.workflows.python_interfaces import build as interfaces

ROOT = Path(__file__).resolve().parents[2]
RUN = implementation_root() / "completion-20260912T220757Z"
REPORTS = Path(__file__).with_name("reports")
LOG = logging.getLogger(__name__)


def verify_freeze() -> str:
    """Check the frozen code inventory.

    Returns:
        The unchanged recorded core digest.

    """
    freeze = json.loads((REPORTS / "completion-core-freeze.json").read_bytes())
    changed = [
        name
        for name, expected in freeze["files"].items()
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected
    ]
    assert not changed, changed
    return freeze["digest"]


def run(name: str) -> None:
    """Build, compare, reverse, publish and restore one full acquired library scope."""
    freeze = verify_freeze()
    work = RUN / f"reuse-{name}"
    corpus = Corpus(work / "corpus", max_rows=2_500_000)
    writer = Coordinator(corpus, WriterIdentity(principal="implementation-agent", role="policy"))
    records = foundation()
    writer.commit(
        (
            *records,
            *approve_rules(
                records,
                authority="implementation-agent",
                rationale="Same-agent reusable foundation model review; no independent review.",
            ),
        ),
        expected=corpus.reader().manifest_id,
    )
    pack = install(
        corpus,
        ROOT / "library_deep_enrichment/assets/packs/input_contracts.json",
        authority="implementation-agent",
        approve=True,
    )
    stages = []
    if name == "pydantic":
        artifact = next(corpus.reader().records("native_artifacts"))
        assert isinstance(artifact, NativeArtifact)
        interfaces(corpus, revision_of(artifact))
        assert interfaces(corpus, revision_of(artifact)).reused
        first, warm = (
            documents(corpus, revision_of(artifact)),
            documents(corpus, revision_of(artifact)),
        )
        assert warm.reused
        stages.append({"stage": "documents", "first": asdict(first), "warm": asdict(warm)})
    for label, build in (
        ("structure", enrichment.build),
        ("shapes", shapes.build),
        ("semantics", semantics.build),
    ):
        LOG.info("START %s %s", name, label)
        first, warm = build(corpus), build(corpus)
        assert warm.reused
        stages.append({"stage": label, "first": asdict(first), "warm": asdict(warm)})
    comparisons = _tasks(corpus, writer, name)
    assert any(item.disposition == "eligible" for item in comparisons[0].candidates)
    work /= f"qualified-{freeze[:16]}-{pack.source_digest[:12]}"
    work.mkdir(exist_ok=True)
    releases = [
        _release(corpus, work, comparison, index) for index, comparison in enumerate(comparisons)
    ]
    assert verify_freeze() == freeze
    report = {
        "freeze": freeze,
        "core_changes": [],
        "prior_core_exceptions": "completion-reuse-findings.json",
        "adapter_changes": [],
        "operation_overrides": 0,
        "author": "implementation-agent",
        "reviewer": "same implementation-agent",
        "independent_review": False,
        "pack": asdict(pack),
        "stages": stages,
        "releases": releases,
        "remaining_interpretation": "Input representation is a narrow contract. Pydantic strictness and serde persistent framing require separate mechanism/fixture evidence. No universal optimum or exhaustive upstream semantic coverage is asserted.",
    }
    (REPORTS / f"completion-{name}-decision-reuse.json").write_bytes(canonical(report) + b"\n")


def _tasks(corpus: Corpus, writer: Coordinator, name: str) -> list[Comparison]:
    """Retain all representation reversals and the persistent-IO counterexample.

    Returns:
        Replayed comparisons over every admitted operation in the library profile.

    """
    reader = corpus.reader()
    profile = "pydantic-2.13.4" if name == "pydantic" else "serde-json-1.0.151"
    predicate = reader.lookup("predicates", "predicate:documented-input-form")
    assert predicate is not None
    task = Task(
        logical_id=f"task:{name}-input",
        profile=profile,
        goal="decode-input",
        profiles=(profile,),
        requirements=(
            Requirement(
                predicate=revision_of(predicate),
                value=text_value("python-object" if name == "pydantic" else "json-text"),
                operator="equal",
                interpretations=(Interpretation.UPSTREAM_CONTRACT,),
                mandatory=True,
            ),
        ),
        context=(),
        inputs=(),
        preferences=(),
        description="Choose the input representation entry; target/model validity, strictness, errors, ownership and performance remain separate requirements.",
    )
    changes = tuple(counterfactuals(reader, task))
    writer.commit(changes, expected=reader.manifest_id)
    comparisons = [item for item in changes if isinstance(item, Comparison)]
    if name == "serde":
        reader = corpus.reader()
        eof = reader.lookup("predicates", "predicate:documented-eof-policy")
        assert eof is not None
        persistent = evolve(
            task,
            logical_id="task:serde-persistent-input",
            requirements=(
                evolve(task.requirements[0], value=text_value("json-io")),
                Requirement(
                    predicate=revision_of(eof),
                    value=text_value("prefix-decoder"),
                    operator="equal",
                    interpretations=(Interpretation.UPSTREAM_CONTRACT,),
                    mandatory=True,
                ),
            ),
            description="Consume one value from a persistent IO connection; a complete-document helper requiring EOF is unsuitable. Decoder construction still needs a Deserialize step and a framing policy.",
        )
        universe, comparison = compare(reader, persistent)
        writer.commit((persistent, universe, comparison), expected=reader.manifest_id)
        comparisons.append(comparison)
    return comparisons


def _release(corpus: Corpus, work: Path, comparison: Comparison, index: int) -> dict[str, object]:
    """Publish and independently restore a complete comparison closure.

    Returns:
        Exact artifact identities and disposition counts.

    """
    head = f"reuse-{index}"
    manifest = publish(corpus, comparison, expected=corpus.reader(head).manifest_id, head=head)
    selected = corpus.reader(head)
    release = next(item for item in selected.records("releases") if isinstance(item, Release))
    guide = read_guide(selected, release)
    destination = work / f"export-{index}"
    export_view(selected, destination)
    restored = Corpus(work / f"restored-{index}", max_rows=2_500_000)
    assert import_view(restored, destination) == manifest
    restored_release = next(
        item for item in restored.reader("release").records("releases") if isinstance(item, Release)
    )
    assert read_guide(restored.reader("release"), restored_release) == guide
    task_record = selected.get("tasks", comparison.task)
    assert isinstance(task_record, Task)
    operations = {
        revision_of(item): item.symbol
        for item in selected.records("operations")
        if isinstance(item, Operation)
    }
    return {
        "head": head,
        "manifest": manifest,
        "export": str(destination),
        "comparison": revision_of(comparison),
        "task": asdict(task_record),
        "counts": dict(Counter(item.disposition for item in comparison.candidates)),
        "eligible": [
            operations[item.operation]
            for item in comparison.candidates
            if item.disposition == "eligible"
        ],
        "guide_sha256": hashlib.sha256(guide.encode()).hexdigest(),
        "restored_identically": True,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run(sys.argv[1])
