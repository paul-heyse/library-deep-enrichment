"""Declaration change evidence distinguishes compiler item numbering from API changes."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from library_deep_enrichment.facts.contracts import Budget
from library_deep_enrichment.source_pipeline import SourceJob, extract

from tests.support.workers import worker_binary

TOOLING = Path(__file__).parents[1]
ID_FIELDS = {
    "id",
    "root",
    "parent",
    "items",
    "fields",
    "impls",
    "implementations",
    "variants",
    "tuple",
}


def _rekey(value: object, ids: dict[int, int], key: str = "") -> object:
    if isinstance(value, dict):
        if key == "links":
            return {
                name: ids.get(target, target) for name, target in reversed(tuple(value.items()))
            }
        if key in {"index", "paths"}:
            return {
                str(ids[int(name)]): _rekey(item, ids)
                for name, item in reversed(tuple(value.items()))
            }
        return {name: _rekey(item, ids, name) for name, item in reversed(tuple(value.items()))}
    if isinstance(value, list):
        return [_rekey(item, ids, key) for item in value]
    if type(value) is int and key in ID_FIELDS:
        return ids.get(value, value)
    return value


def _extract(root: Path, name: str, document: object) -> dict[int, dict]:
    root.mkdir(exist_ok=True)
    source = root / f"{name}.json"
    source.write_text(json.dumps(document))
    artifact = extract(
        root / name,
        SourceJob(
            id=name,
            kind="declarations",
            input=str(source),
            helper=str(worker_binary("rustdoc-facts")),
            profile="declaration-identity-control",
            schema=str(TOOLING / "src/library_deep_enrichment/assets/schemas/declaration.v1.schema.json"),
        ),
        Budget(),
    )
    values = [
        json.loads(line)
        for shard in artifact.shards
        for line in (root / name / shard.path).read_bytes().splitlines()
    ]
    return {item["local_id"]: item for item in values}


@pytest.mark.native_lanes
def test_item_numbering_and_mapping_order_do_not_change_contract_digests(tmp_path: Path) -> None:
    """All declared items survive renumbering, including tuple slots and restricted parents."""
    document = json.loads((TOOLING / "tests/fixtures/declaration-format-matrix.json").read_bytes())
    ids = {int(key): int(key) + 4_000_000 for key in {*document["index"], *document["paths"]}}
    original = _extract(tmp_path, "original", document)
    shifted = _extract(tmp_path, "shifted", _rekey(document, ids))
    assert len(original) == len(document["index"]) == len(shifted)
    for key, item in original.items():
        assert item["artifact"] != shifted[ids[key]]["artifact"]
        assert item["semantic_digest"] == shifted[ids[key]]["semantic_digest"], item["symbol"]
        assert item["public_routes"] == shifted[ids[key]]["public_routes"], item["symbol"]


@pytest.mark.native_lanes
def test_bound_default_mutability_and_public_route_changes_remain_observable(
    tmp_path: Path,
) -> None:
    """Real contract mutations remain visible after removing compiler-numbering noise."""
    document = json.loads((TOOLING / "tests/fixtures/declaration-format-matrix.json").read_bytes())
    original = _extract(tmp_path, "original", document)
    changed = copy.deepcopy(document)
    mutations = []
    for key, item in changed["index"].items():
        if item["name"] == "type_borrowed_ref":
            item["inner"]["type_alias"]["type"]["borrowed_ref"]["is_mutable"] = False
            mutations.append(int(key))
        if item["name"] == "Consumer":
            item["inner"]["trait"]["generics"]["params"][0]["kind"]["type"]["bounds"] = []
            mutations.append(int(key))
        if item["name"] == "LIMIT":
            item["inner"]["assoc_const"]["value"] = "5"
            mutations.append(int(key))
        if isinstance(item["inner"], dict) and item["inner"].get("use", {}).get("name") == "Layout":
            item["visibility"] = "default"
    revised = _extract(tmp_path, "changed", changed)
    assert mutations
    assert all(
        original[key]["semantic_digest"] != revised[key]["semantic_digest"] for key in mutations
    )
    constructor = next(
        key for key, item in original.items() if item["symbol"].endswith("<impl Schema>::new")
    )
    assert "reference_fixture::Layout::new" in original[constructor]["public_routes"]
    assert "reference_fixture::Layout::new" not in revised[constructor]["public_routes"]
    assert "reference_fixture::Schema::new" in revised[constructor]["public_routes"]


@pytest.mark.native_lanes
@pytest.mark.parametrize("change", ["associated-requirement", "impl-polarity", "stability"])
def test_additional_contract_changes_do_not_disappear(tmp_path: Path, change: str) -> None:
    """Required associated types, negative impls and stability keep semantic sensitivity."""
    document = json.loads((TOOLING / "tests/fixtures/declaration-format-matrix.json").read_bytes())
    original = _extract(tmp_path, "original", document)
    changed = copy.deepcopy(document)
    if change == "associated-requirement":
        key, item = next(
            (key, item)
            for key, item in changed["index"].items()
            if item["name"] == "Output" and item["inner"]["assoc_type"]["type"] is None
        )
        item["inner"]["assoc_type"]["type"] = {"primitive": "u8"}
    elif change == "impl-polarity":
        key, item = next(
            (key, item)
            for key, item in changed["index"].items()
            if item["inner"].get("impl", {}).get("is_negative")
        )
        item["inner"]["impl"]["is_negative"] = False
    else:
        key, item = next(
            (key, item) for key, item in changed["index"].items() if item["name"] == "derive_macro"
        )
        item["stability"]["level"]["stable"]["since"] = "2.0.0"
    revised = _extract(tmp_path, "changed", changed)
    assert original[int(key)]["semantic_digest"] != revised[int(key)]["semantic_digest"]
    unrelated = next(
        key for key, item in original.items() if item["symbol"].endswith("<impl Schema>::new")
    )
    assert original[unrelated]["semantic_digest"] == revised[unrelated]["semantic_digest"]
