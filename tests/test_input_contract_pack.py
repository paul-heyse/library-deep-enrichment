"""Real input-contract templates preserve competing representations and caveats."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from library_deep_enrichment.corpus.admission import Coordinator, WriterIdentity
from library_deep_enrichment.corpus.contracts import ByteRange, Passage
from library_deep_enrichment.corpus.store import Corpus
from library_deep_enrichment.semantic_packs import install
from library_deep_enrichment.semantics.contracts import Rule
from library_deep_enrichment.semantics.rules import matching_text
from library_deep_enrichment.semantics.vocabulary import foundation


@pytest.mark.parametrize("kind", ["input", "result"])
def test_input_forms_and_eof_do_not_inherit_negated_or_appended_contracts(
    tmp_path: Path, kind: str
) -> None:
    """Exact upstream clauses activate; polarity, EOF and new exceptions matter."""
    corpus = Corpus(tmp_path)
    Coordinator(corpus, WriterIdentity(principal="fixture")).commit(foundation(), expected="")
    pack = Path(__file__).parents[1] / f"src/library_deep_enrichment/assets/packs/{kind}_contracts.json"
    install(
        corpus,
        pack,
        authority="fixture-reviewer",
    )
    names = {
        row["record"]["logical_id"]
        for row in json.loads(pack.read_bytes())["records"]
        if row["family"] == "rules"
    }
    rules = [
        item
        for item in corpus.reader().records("rules")
        if isinstance(item, Rule) and item.logical_id in names
    ]
    fixtures = json.loads(
        (Path(__file__).with_name("fixtures") / f"{kind}-contract-docs.json").read_bytes()
    )
    for item in fixtures:
        source = Passage(
            logical_id="fixture",
            owner="fixture-operation",
            role="upstream-description",
            text=item["text"],
            language="en",
            source=ByteRange(blob="fixture", start=0, end=0, digest="fixture"),
        )
        matched = {
            rule.logical_id.removeprefix("rule:")
            for rule in rules
            if matching_text(rule, source) is not None
        }
        assert matched == set(item["expected_rules"]), item["symbol"]
        from attrs import evolve

        for text in ("Never " + source.text, source.text + "\nExcept for the current target."):
            assert not any(matching_text(rule, evolve(source, text=text)) for rule in rules)
        if item["symbol"] == "serde_json::de::from_reader":
            changed = source.text.replace(
                "It is expected that the input stream ends after the deserialized object.",
                "The input stream does not need to end after the deserialized object.",
            )
            assert not any(matching_text(rule, evolve(source, text=changed)) for rule in rules)
