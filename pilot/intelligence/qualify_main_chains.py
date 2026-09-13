"""Inspect four real source-to-release chains and exercise their change boundaries."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from attrs import asdict, evolve

from library_deep_enrichment.corpus.admission import Coordinator, WriterIdentity
from library_deep_enrichment.corpus.contracts import AdmissionBatch, Operation, Qualification
from library_deep_enrichment.corpus.encoding import canonical
from library_deep_enrichment.corpus.identities import identify, join
from library_deep_enrichment.corpus.schemas import revision_of
from library_deep_enrichment.corpus.store import Corpus
from library_deep_enrichment.publication.export import import_view
from library_deep_enrichment.semantics.contracts import (
    Assertion,
    Capability,
    Comparison,
    Proof,
    Task,
)
from library_deep_enrichment.semantics.task_matching import compare
from library_deep_enrichment.semantics.vocabulary import text_value
from pilot.intelligence.qualify_reuse import REPORTS, RUN, verify_freeze

if TYPE_CHECKING:
    from library_deep_enrichment.corpus.store import CorpusReader

LOG = logging.getLogger(__name__)
CASES = (
    (
        "datafusion-rust",
        "rust-results",
        "execute_stream",
        "documented-result-delivery",
        "collected",
    ),
    (
        "datafusion-python",
        "python-results",
        "execute_stream",
        "declares-result-carrier",
        "collection",
    ),
    (
        "pyarrow",
        "reverse-python-overflow",
        "add_checked",
        "documented-integer-overflow-policy",
        "wrap",
    ),
    ("arrow-rust", "rust-schema", "try_merge", "documented-schema-merge-policy", ""),
)


def _chain(
    reader: CorpusReader, task_name: str, symbol: str, predicate_name: str
) -> dict[str, object]:
    """Resolve a qualified consequence and its complete admitted source ancestry.

    Returns:
        Exact operation, context, proof, capability, task and comparison identities.

    """
    task = reader.lookup(
        "tasks",
        f"task:completion:{task_name}",
        "python-installed-54-25"
        if task_name in {"python-results", "reverse-python-overflow"}
        else "rust-docsrs-54.1-58.4",
    )
    assert isinstance(task, Task)
    comparison = next(
        item
        for item in reader.records("comparisons")
        if isinstance(item, Comparison) and item.task == revision_of(task)
    )
    predicate = reader.lookup("predicates", f"predicate:{predicate_name}")
    assert predicate is not None
    operations = {
        revision_of(item): item
        for item in reader.records("operations")
        if isinstance(item, Operation) and symbol in item.symbol
    }
    assertions = [
        item
        for item in reader.records("assertions")
        if isinstance(item, Assertion)
        and item.subject in operations
        and item.predicate == revision_of(predicate)
        and any(
            requirement.predicate == item.predicate and requirement.value == item.value
            for requirement in task.requirements
        )
    ]
    eligible = {
        item.operation
        for item in comparison.candidates
        if any(
            result.assertions
            for result in item.requirements
            if result.predicate == revision_of(predicate)
        )
    }
    assertion = next(
        item
        for item in sorted(
            assertions,
            key=lambda item: (
                not any(
                    source.family == "native_facts" for source in operations[item.subject].evidence
                ),
                revision_of(item),
            ),
        )
        if item.subject in eligible
    )
    operation = operations[assertion.subject]
    proof = next(
        item
        for item in reader.records("proofs")
        if isinstance(item, Proof) and item.conclusion == revision_of(assertion)
    )
    qualification = next(
        item
        for item in reader.records("qualifications")
        if isinstance(item, Qualification) and item.subject == revision_of(assertion)
    )
    capabilities = [
        revision_of(item)
        for item in reader.records("capabilities")
        if isinstance(item, Capability)
        and item.operation == assertion.subject
        and revision_of(assertion) in item.assertions
    ]
    assert capabilities
    identity = identify(reader, "operations", revision_of(operation))
    return {
        "operation": revision_of(operation),
        "symbol": operation.symbol,
        "profile": operation.profile,
        "contextual_identity": asdict(identity),
        "declaration_support": [asdict(item) for item in operation.evidence],
        "assertion": revision_of(assertion),
        "predicate": revision_of(predicate),
        "value": assertion.value.text,
        "rule": assertion.rule,
        "proof": revision_of(proof),
        "premises": [asdict(item) for item in proof.premises],
        "qualification": revision_of(qualification),
        "capabilities": capabilities,
        "task": revision_of(task),
        "comparison": revision_of(comparison),
        "universe": comparison.universe,
        "universe_count": len(comparison.candidates),
    }


def _change(corpus: Corpus, chain: dict[str, object], value: str) -> dict[str, object]:
    """Change one consumer criterion, or withdraw the exact schema source premise.

    Returns:
        Admitted before/after identities and the changed operation's actual disposition.

    """
    before = corpus.reader()
    task = before.get("tasks", str(chain["task"]))
    assert isinstance(task, Task)
    writer = Coordinator(corpus, WriterIdentity(principal="finite-change-control"))
    if value:
        changed = evolve(
            task,
            requirements=tuple(
                evolve(item, value=text_value(value))
                if item.predicate == chain["predicate"]
                else item
                for item in task.requirements
            ),
        )
        scope, comparison = compare(before, changed)
        manifest = writer.commit((changed, scope, comparison), expected=before.manifest_id)
        kind = "consumer-requirement-change"
    else:
        assertion = before.get("assertions", str(chain["assertion"]))
        assert isinstance(assertion, Assertion)
        premise = next(item for item in assertion.support if item.family == "passages")
        member = next(
            item for item in before.members("passages") if item.revision == premise.revision
        )
        manifest = writer.commit(
            AdmissionBatch(records=(), retire=(member,)), expected=before.manifest_id
        )
        assert not any(
            item.revision == chain["qualification"]
            for item in corpus.reader().members("qualifications")
        )
        scope, comparison = compare(corpus.reader(), task)
        manifest = writer.commit((scope, comparison), expected=manifest)
        kind = "exact-source-premise-withdrawal"
    candidate = next(item for item in comparison.candidates if item.operation == chain["operation"])
    assert candidate.disposition != "eligible"
    assert any(
        item.state.value != "supported"
        for item in candidate.requirements
        if item.predicate == chain["predicate"]
    )
    assert before.get("comparisons", str(chain["comparison"]))
    return {
        "kind": kind,
        "before_manifest": before.manifest_id,
        "after_manifest": manifest,
        "comparison": revision_of(comparison),
        "changed_candidate": asdict(candidate),
        "historical_comparison_readable": True,
        "source_version_change_claimed": False,
    }


def run() -> None:
    """Qualify four main-library chains in one portable mutable successor."""
    freeze = verify_freeze()
    cohort = json.loads((REPORTS / "completion-main-task-cohort.json").read_bytes())
    corpus = Corpus(RUN / f"main-chain-controls-{freeze[:16]}", max_rows=2_500_000)
    from pathlib import Path

    import_view(corpus, Path(cohort["export"]), head="analysis")
    original = corpus.reader()
    chains = []
    for library, task, symbol, predicate, value in CASES:
        LOG.info("CHAIN %s", library)
        chain = _chain(original, task, symbol, predicate)
        chain.update(
            {
                "library": library,
                "release_manifest": cohort["release_manifest"],
                "release": cohort["release"],
                "guide_sha256": cohort["guide_sha256"],
                "change": _change(corpus, chain, value),
            }
        )
        chains.append(chain)
    identities = [identify(original, "operations", str(item["operation"])) for item in chains]
    joins = [join(identity, identity) for identity in identities]
    joins.append(join(identities[0], identities[1]))
    Coordinator(corpus, WriterIdentity(principal="identity-replay-control")).commit(
        (*identities, *joins), expected=corpus.reader().manifest_id
    )
    assert joins[-1].resolution == "unresolved"
    assert verify_freeze() == freeze
    (REPORTS / "completion-four-library-chains.json").write_bytes(
        canonical(
            {
                "freeze": freeze,
                "author": "implementation-agent",
                "reviewer": "same implementation-agent",
                "independent_review": False,
                "chains": chains,
                "identity_joins": [asdict(item) for item in joins],
                "bridge_limit": "Exact native origin does not establish rustdoc-to-MIR, Python-to-Rust runtime dispatch, ordinary-consumer availability, or cross-language equivalence. Unbridged pairs remain unresolved.",
            }
        )
        + b"\n"
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
