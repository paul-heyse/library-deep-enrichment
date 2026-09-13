"""Four typed decoders retain every advertised declaration and type wire variant."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
import yaml
from library_deep_enrichment.corpus.evidence import read_field
from library_deep_enrichment.corpus.native_contracts import NativeFact
from library_deep_enrichment.corpus.schemas import revision_of
from library_deep_enrichment.corpus.store import Corpus
from library_deep_enrichment.publication.export import export_view, import_view
from library_deep_enrichment.workflows.native import build

from tests.support.workers import worker_binary

TOOLING = Path(__file__).parents[1]
FAMILIES = {
    "module",
    "extern_crate",
    "use",
    "union",
    "struct",
    "struct_field",
    "enum",
    "variant",
    "function",
    "trait",
    "trait_alias",
    "impl",
    "type_alias",
    "constant",
    "static",
    "extern_type",
    "macro",
    "proc_macro",
    "primitive",
    "assoc_const",
    "assoc_type",
}
OLDER_DEFAULT_FORMATS = {57, 59}
PRE_STABILITY_FORMAT = 57
FLAT_STABILITY_FORMATS = {59, 60}
TYPE_VARIANTS = {
    "resolved_path",
    "dyn_trait",
    "generic",
    "primitive",
    "function_pointer",
    "tuple",
    "slice",
    "array",
    "pat",
    "impl_trait",
    "infer",
    "raw_pointer",
    "borrowed_ref",
    "qualified_path",
}


def _document(version: int) -> tuple[dict, dict]:
    """Create an explicitly synthetic versioned fixture and its independent expected items.

    Returns:
        Input and expected output with unavailable old-schema fields explicitly null.

    """
    document = json.loads((TOOLING / "tests/fixtures/declaration-format-matrix.json").read_bytes())
    document["format_version"] = version
    expected = copy.deepcopy(document["index"])
    for key, item in document["index"].items():
        if version == PRE_STABILITY_FORMAT:
            for field in ("stability", "const_stability"):
                item.pop(field, None)
                expected[key][field] = None
        if version in FLAT_STABILITY_FORMATS:
            for field in ("stability", "const_stability"):
                stability = item.get(field)
                if stability and isinstance(stability["level"], dict):
                    stable = stability["level"]["stable"]
                    stability["level"] = "stable"
                    stability["since"] = stable["since"]
        if version in OLDER_DEFAULT_FORMATS and isinstance(item["inner"], dict):
            for kind in ("function", "assoc_type", "assoc_const"):
                if kind in item["inner"]:
                    item["inner"][kind].pop("default_unstable", None)
                    expected[key]["inner"][kind]["default_unstable"] = None
    return document, expected


@pytest.mark.native_lanes
@pytest.mark.parametrize("version", [57, 59, 60, 61])
def test_all_declaration_and_type_variants_survive_portable_native_admission(
    tmp_path: Path, version: int
) -> None:
    """Ordering, restricted visibility, negative impls and format frontiers survive exactly."""
    document, expected = _document(version)
    source = tmp_path / "input.json"
    source.write_text(json.dumps(document))
    manifest = tmp_path / "source.yaml"
    manifest.write_text(
        yaml.safe_dump(
            {
                "schema_version": "library-guides.source-manifest.v1",
                "jobs": [
                    {
                        "id": f"all-families-{version}",
                        "kind": "declarations",
                        "profile": f"synthetic-format-{version}",
                        "input": str(source),
                        "helper": str(
                            worker_binary("rustdoc-facts")
                        ),
                        "schema": str(
                            TOOLING / "src/library_deep_enrichment/assets/schemas/declaration.v1.schema.json"
                        ),
                    }
                ],
            }
        )
    )
    corpus = Corpus(tmp_path / "corpus")
    first = build(corpus, manifest, tmp_path / "transport")
    assert not first.reused
    assert build(corpus, manifest, tmp_path / "transport").reused
    reader = corpus.reader()
    values: list[dict] = []
    for fact in reader.records("native_facts"):
        assert isinstance(fact, NativeFact)
        value = read_field(reader, "native_facts", revision_of(fact), "/raw/item")
        assert isinstance(value, dict)
        values.append(value)
    assert {
        next(iter(item["inner"])) if isinstance(item["inner"], dict) else item["inner"]
        for item in values
    } == FAMILIES
    assert {str(item["id"]): item for item in values} == expected
    assert {
        item["name"].removeprefix("type_")
        for item in values
        if isinstance(item["name"], str)
        and item["name"].startswith("type_")
        and isinstance(item["inner"], dict)
        and "type_alias" in item["inner"]
    } == TYPE_VARIANTS
    assert not tuple(reader.records("qualifications"))
    destination = tmp_path / "export"
    export_view(reader, destination)
    restored = Corpus(tmp_path / "restored")
    assert import_view(restored, destination) == reader.manifest_id
    again = restored.reader("release")
    for fact in again.records("native_facts"):
        assert isinstance(fact, NativeFact)
        item = read_field(again, "native_facts", revision_of(fact), "/raw/item")
        assert isinstance(item, dict)
        assert item == expected[str(item["id"])]
