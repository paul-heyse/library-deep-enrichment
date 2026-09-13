"""V3 migrations preserve V2 and cannot grant source-evidence acceptance."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from attrs import asdict
from jsonschema.exceptions import ValidationError
from library_deep_enrichment.collection import load
from library_deep_enrichment.facts.contracts import FactSelection
from library_deep_enrichment.knowledge_v3 import KnowledgeV3
from library_deep_enrichment.migrations.knowledge_v2_to_v3 import migrate
from library_deep_enrichment.schemas import schema_for, validate_document
from library_deep_enrichment.store.digests import canonical_bytes, digest_file

from .test_knowledge_v2 import _sample


def test_explicit_migration_preserves_original_bytes(tmp_path: Path) -> None:
    """Planning writes nothing; apply writes a new authority with an audit trail."""
    source, target = tmp_path / "v2", tmp_path / "v3"
    source.mkdir()
    old = _sample(source)
    before = digest_file(source / "knowledge.yaml")
    report = migrate(source, target)
    assert report["state"] == "planned"
    assert not target.exists()
    migrate(source, target, apply=True)
    current = load(target)
    assert isinstance(current, KnowledgeV3)
    assert current.claims == old.claims
    assert current.fact_artifacts == ()
    assert current.revalidations
    assert digest_file(source / "knowledge.yaml") == before
    assert (target / "migration/v2-knowledge.json").is_file()


def test_v3_unknown_fields_and_mixed_schema_are_rejected() -> None:
    """A proposal cannot smuggle new authority through untyped fields."""
    value = json.loads(
        canonical_bytes(
            asdict(KnowledgeV3(schema_version="library-guides.knowledge.v3", collection_id="test"))
        )
    )
    validate_document(value)
    value["made_up_acceptance"] = True
    with pytest.raises(ValidationError):
        validate_document(value)
    value.pop("made_up_acceptance")
    value["schema_version"] = "library-guides.knowledge.v2"
    with pytest.raises(ValidationError):
        validate_document(value)


def test_fact_support_requires_explicit_typed_roles() -> None:
    """Selectors cannot carry arbitrary unchecked certainty or review dispositions."""
    from jsonschema import Draft202012Validator

    schema = schema_for(FactSelection)
    validator = Draft202012Validator(schema)
    value = {
        "artifact": "a",
        "record": "r",
        "selector": "json:/item/inner",
        "digest": "d",
        "role": "compiler_proven",
    }
    with pytest.raises(ValidationError):
        validator.validate(value)
