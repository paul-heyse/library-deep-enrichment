"""Reusable data models retain polarity, exceptions, authority, and execution bounds."""

from __future__ import annotations

from pathlib import Path

import pytest
from attrs import evolve
from library_deep_enrichment.corpus.backend import BudgetExceededError
from library_deep_enrichment.corpus.contracts import ByteRange, Passage, Policy
from library_deep_enrichment.corpus.store import Corpus
from library_deep_enrichment.semantic_packs import install
from library_deep_enrichment.semantics.contracts import Rule
from library_deep_enrichment.semantics.rules import matching_text

PACK = Path(__file__).parents[1] / "library_deep_enrichment/assets/packs/arithmetic_contracts.json"


def _source(text: str) -> Passage:
    return Passage(
        logical_id="fixture:description",
        owner="fixture:operation",
        role="upstream-description",
        text=text,
        language="en",
        source=ByteRange(blob="fixture", start=0, end=0, digest="fixture"),
    )


def test_pack_approval_is_separate_and_full_field_templates_keep_alternative_polarity(
    tmp_path: Path,
) -> None:
    """The second clause describes an alternative, while extra exceptions defeat the template."""
    corpus = Corpus(tmp_path)
    candidate = install(corpus, PACK, authority="fixture-author")
    assert not candidate.approved
    assert not tuple(corpus.reader().records("policies"))
    approved = install(corpus, PACK, authority="fixture-rule-reviewer", approve=True)
    assert approved.approved
    assert approved.operation_mappings == 0
    assert all(
        isinstance(policy, Policy) and policy.authority == "fixture-rule-reviewer"
        for policy in corpus.reader().records("policies")
    )
    rule = corpus.reader().lookup("rules", "rule:integer-overflow-error")
    assert isinstance(rule, Rule)
    text = 'This function returns an error on overflow.  For a variant that\ndoesn\'t fail on overflow, use function "add".'
    assert matching_text(rule, _source(text)) == text
    assert matching_text(rule, _source(text + "\nExcept on the GPU.")) is None
    assert (
        matching_text(rule, _source(text.replace("returns an error", "never returns an error")))
        is None
    )
    assert matching_text(rule, _source(text.replace("This function", "Another function"))) is None


def test_a_pathological_model_cannot_hang_the_consequence_checker(tmp_path: Path) -> None:
    """Even an admitted pattern has a hard finite matching budget."""
    corpus = Corpus(tmp_path)
    install(corpus, PACK, authority="fixture-author")
    source = corpus.reader().lookup("rules", "rule:integer-overflow-error")
    assert isinstance(source, Rule)
    pathological = evolve(source, pattern="(a|aa)+$")
    with pytest.raises(BudgetExceededError, match="execution budget"):
        matching_text(pathological, _source("a" * 6000 + "!"))


def test_registry_facets_require_their_own_observed_fields(tmp_path: Path) -> None:
    """A runtime phase cannot inherit a kind citation or a contradictory raw field."""
    from library_deep_enrichment.corpus.contracts import RegistryEntry
    from library_deep_enrichment.corpus.staging import ObservationBuilder

    corpus = Corpus(tmp_path)
    install(corpus, PACK.with_name("registry_applicability.json"), authority="fixture-author")
    rule = corpus.reader().lookup("rules", "rule:registered-execution-phase")
    assert isinstance(rule, Rule)
    builder = ObservationBuilder("fixture")
    raw = builder.observe(
        "source", {"kind": "scalar", "phase": "execution"}, profile="p", kind="fixture"
    )
    entry = RegistryEntry(
        logical_id="entry",
        profile="p",
        operation="op",
        namespace="registry",
        kind="scalar",
        arity="1",
        argument_names=("value",),
        options_class="",
        options_required=False,
        summary="",
        description="",
        input_domain="native-datum-inputs",
        phase="execution",
        evidence=(builder.select(raw, "/phase", "registry"),),
    )
    assert matching_text(rule, entry) == "execution"
    assert matching_text(rule, evolve(entry, phase="registered")) is None
    assert (
        matching_text(rule, evolve(entry, evidence=(builder.select(raw, "/kind", "registry"),)))
        is None
    )
