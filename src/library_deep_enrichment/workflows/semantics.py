"""An atomic semantic build from admitted inputs to qualified capabilities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from attrs import evolve, frozen

from library_deep_enrichment.semantics.proofs import check_consequence
from library_deep_enrichment.semantics.realization import realize
from library_deep_enrichment.semantics.rules import derive
from library_deep_enrichment.workflows.discovery import definition
from library_deep_enrichment.workflows.engine import overlay, run_stage
from library_deep_enrichment.workflows.remote import RemoteProducer

if TYPE_CHECKING:
    from collections.abc import Iterator

    from library_deep_enrichment.corpus.contracts import Record
    from library_deep_enrichment.corpus.store import Corpus, CorpusReader

STAGE = "semantic-consequences.v1"
INPUT_FIELDS: dict[str, tuple[str, ...]] = {
    "operation_shapes": ("/operation", "/inputs", "/outputs", "/support"),
    "capability_schemas": ("/name", "/description", "/requirements", "/any_qualified_support"),
    "type_uses": ("/owner", "/nominal", "/role", "/direct", "/resolution", "/nominal_scope"),
    "operations": ("/signature", "/returns", "/parameters", "/profile"),
    "passages": ("/text", "/owner", "/profile"),
    "registry_entries": ("/operation", "/kind", "/input_domain", "/phase"),
    "witness_observations": ("/operation", "/field", "/value", "/scope", "/run"),
    "rules": ("/algorithm", "/pattern", "/predicate", "/value", "/condition", "/version"),
    "predicates": ("/name", "/allowed_values", "/interpretations"),
    "policies": ("/subject", "/allowed_predicates", "/required_scopes"),
}


@frozen(kw_only=True)
class BuildReceipt:
    """A concrete semantic stage outcome, including exact warm-reuse disposition."""

    manifest: str
    request: str
    reused: bool
    assertions: int
    qualifications: int
    capabilities: int


def _produce(reader: CorpusReader) -> Iterator[Record]:
    pairs = list(derive(reader))
    records: list[Record] = [record for pair in pairs for record in pair]
    staged = overlay(reader, records)
    records.extend(check_consequence(staged, proof) for _, proof in pairs)
    records.extend(realize(overlay(reader, records)))
    yield from records


def build(corpus: Corpus) -> BuildReceipt:
    """Run qualified semantic derivation with producer fingerprints and failure currentness.

    Returns:
        Actual product counts or zero-work reuse for the unchanged requested generation.

    """
    stage = definition(
        STAGE,
        INPUT_FIELDS,
        ("assertions", "proofs", "qualifications", "modes", "capabilities"),
        (
            "semantics/rules.py",
            "semantics/relational.py",
            "semantics/proofs.py",
            "semantics/realization.py",
            "semantics/type_shapes.py",
            "assets/semantic/owner_rules.dl",
        ),
    )
    stage = evolve(stage, max_records=500_000, max_bytes=512 * 1024 * 1024, max_seconds=1800.0)
    result = run_stage(
        corpus, stage, RemoteProducer(root=corpus.root, definition=stage, route="semantics")
    )
    counts = dict(result.outputs)
    return BuildReceipt(
        manifest=result.manifest,
        request=result.request,
        reused=result.reused,
        assertions=counts.get("assertions", 0),
        qualifications=counts.get("qualifications", 0),
        capabilities=counts.get("capabilities", 0),
    )
