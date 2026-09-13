"""Validate owned constant allocations and physical layouts without interpreting pointer bytes."""

from __future__ import annotations

import re
from itertools import pairwise

from library_guides.analyses.behavior import mir_callables, mir_instances
from library_guides.analyses.behavior.integrity import require

SCHEMA = "library-guides.mir-memory.v1"
MAX_NODES = 4096
MAX_TYPES = 1024
MAX_BYTES = 1_048_576
MAX_POINTERS = 32_768
MAX_ROOTS = 100_000
MAX_BYTE = 255


def _index(value: object, size: int) -> bool:
    return type(value) is int and 0 <= value < size


def _optional_index(value: object, size: int) -> bool:
    return value is None or _index(value, size)


def _definition(value: object) -> bool:
    return isinstance(value, str) and bool(
        re.fullmatch(r"definition:[0-9a-f]{16}:[0-9a-f]{32}:[0-9a-f]{32}", value)
    )


def _alignment(value: object) -> bool:
    return type(value) is int and value > 0 and value & (value - 1) == 0


def _function_view(raw: dict, node: dict) -> dict:
    identity, selection = node["identity"], node["selection"]
    call = {
        "block": selection["block"],
        "declaration": node["definition"],
        "target": identity["definition"],
        "substitutions": identity["substitutions"],
        "instance_kind": identity["kind"],
        "complete": True,
        "frontier": [],
    }
    return {
        **raw,
        "behavior": {**raw["behavior"], "calls": [call]},
        "execution": {**raw["execution"], "calls": [selection]},
    }


def validate(raw: dict) -> dict:
    """Require exact operand/local denominators, graph bounds and provenance correspondence.

    Returns:
        The original memory projection after checking its owned invariants.

    """
    memory = raw.get("memory")
    require("missing constant memory denominator", condition=isinstance(memory, dict))
    assert isinstance(memory, dict)
    roots, nodes, types = memory["roots"], memory["nodes"], memory["types"]
    require(
        "constant memory population budget exceeded",
        condition=len(nodes) <= MAX_NODES and len(types) <= MAX_TYPES and len(roots) <= MAX_ROOTS,
    )
    expected = {
        point: value
        for point, value in mir_callables.operands(raw).items()
        if value["mode"] == "constant"
    }
    seen = set()
    for root in roots:
        point = root["point"]
        key = point["block"], point["statement"], point["role"], point["operand"]
        require(
            "duplicate or missing constant operand", condition=key in expected and key not in seen
        )
        seen.add(key)
        require(
            "constant root escaped allocation/type catalog",
            condition=_optional_index(root["ty"], len(types))
            and _optional_index(root["allocation"], len(nodes))
            and (root["allocation"] is None or root["state"] == "allocated"),
        )
        if root["ty"] is not None:
            require(
                "constant root type differs from original operand",
                condition=types[root["ty"]]["ty"] == expected[key]["ty"],
            )
        require(
            "invalid constant acquisition disposition",
            condition=root["state"]
            in {
                "allocated",
                "zero_sized",
                "type_constant_not_evaluated",
                "unevaluated_constant",
                "generic_constant",
                "allocation_node_budget",
                "outside_requested_root_closure",
            }
            and root["evaluation"]
            in {
                "not_requested",
                "already_evaluated",
                "evaluated",
                "unavailable",
                "generic_or_symbolic",
            }
            and (root["state"] != "allocated" or root["allocation"] is not None),
        )
    require("constant operand denominator is incomplete", condition=seen == set(expected))
    _locals(raw, memory, types)
    require(
        "unselected memory contains acquired evidence",
        condition=memory["selected"]
        or (
            not nodes
            and not types
            and all(
                root["ty"] is None
                and root["allocation"] is None
                and root["state"] == "outside_requested_root_closure"
                and root["evaluation"] == "not_requested"
                for root in roots
            )
        ),
    )
    pointer_bytes = raw["behavior"]["target"]["pointer_bits"] // 8
    retained = pointers = 0
    for node in nodes:
        if node["kind"] == "memory":
            data = node["bytes"]
            retained += len(data)
            offsets = [pointer["offset"] for pointer in node["pointers"]]
            pointers += len(offsets)
            require(
                "invalid initialized bytes or allocation alignment",
                condition=_alignment(node["alignment"])
                and all(
                    value is None or (type(value) is int and 0 <= value <= MAX_BYTE)
                    for value in data
                ),
            )
            require(
                "invalid or overlapping pointer provenance",
                condition=offsets == sorted(set(offsets))
                and all(
                    type(offset) is int and 0 <= offset <= len(data) - pointer_bytes
                    for offset in offsets
                )
                and all(right - left >= pointer_bytes for left, right in pairwise(offsets))
                and all(
                    _optional_index(pointer["target"], len(nodes)) for pointer in node["pointers"]
                ),
            )
        elif node["kind"] in {"function", "static"}:
            require(
                "constant target definition or type is invalid",
                condition=_definition(node["definition"])
                and _optional_index(node["ty"], len(types)),
            )
            if node["kind"] == "static":
                require(
                    "static initializer escaped graph",
                    condition=_optional_index(node["initializer"], len(nodes)),
                )
            elif node["identity"] is not None:
                identity = node["identity"]
                require(
                    "constant function target identity mismatch",
                    condition=not node["foreign"]
                    and node["selection"] is not None
                    and identity["definition"] == node["definition"]
                    and identity["key"] == node["selection"]["instance"]
                    and identity["phase"] == mir_instances.PHASE,
                )
                mir_instances.validate(_function_view(raw, node))
            else:
                require(
                    "unresolved memory target was selected", condition=node["selection"] is None
                )
        else:
            require(
                "invalid allocation node disposition",
                condition=node["kind"] == "unresolved" and bool(node["reason"]),
            )
    require(
        "constant memory retained byte/pointer budget mismatch",
        condition=retained == memory["retained_bytes"]
        and retained <= MAX_BYTES
        and pointers <= MAX_POINTERS,
    )
    for ty in types:
        _type(ty, types)
    return memory


def _locals(raw: dict, memory: dict, types: list[dict]) -> None:
    local_types = {local["local"]: local["ty"] for local in memory["locals"]}
    original_locals = {local["index"]: local["ty"] for local in raw["payload"]["locals"]}
    require(
        "constant memory local type denominator is incomplete",
        condition=len(local_types) == len(memory["locals"])
        and (set(local_types) == set(original_locals) if memory["selected"] else not local_types),
    )
    for local, ty in local_types.items():
        require(
            "physical local type differs from original body",
            condition=_optional_index(ty, len(types))
            and (ty is None or types[ty]["ty"] == original_locals[local]),
        )


def _type(ty: dict, types: list[dict]) -> None:
    require(
        "physical type element escaped catalog",
        condition=_optional_index(ty["element"], len(types)),
    )
    require(
        "invalid physical nominal identity",
        condition=ty["definition"] is None or _definition(ty["definition"]),
    )
    for variant in ty["variants"]:
        members = variant["members"]
        require(
            "physical field denominator is invalid",
            condition=[member["index"] for member in members] == list(range(len(members)))
            and all(_optional_index(member["ty"], len(types)) for member in members)
            and all(
                member["definition"] is None or _definition(member["definition"])
                for member in members
            ),
        )
    signature = ty["signature"]
    if signature is not None:
        require(
            "function signature escaped physical type catalog",
            condition=bool(signature["abi"])
            and _optional_index(signature["output"], len(types))
            and all(_optional_index(item, len(types)) for item in signature["inputs"]),
        )
    layout = ty["layout"]
    if layout is None:
        require(
            "missing layout lacks a disposition",
            condition="physical_layout_unavailable" in ty["frontier"],
        )
        return
    require(
        "invalid physical layout size/alignment",
        condition=type(layout["size"]) is int
        and layout["size"] >= 0
        and _alignment(layout["alignment"]),
    )
    fields = layout["fields"]
    offsets = fields.get("offsets", [])
    require(
        "physical field offset exceeds its layout",
        condition=all(type(offset) is int and 0 <= offset <= layout["size"] for offset in offsets)
        and all(
            type(offset) is int and 0 <= offset <= layout["size"]
            for variant in layout["variant_offsets"]
            for offset in variant
        ),
    )
    if fields["kind"] == "array":
        require(
            "array stride/count differs from exact sized layout",
            condition=fields["stride"] >= 0
            and fields["count"] >= 0
            and (not layout["sized"] or fields["stride"] * fields["count"] == layout["size"]),
        )
    tag = layout["tag"]
    if tag is not None:
        require(
            "invalid physical discriminant location",
            condition=layout["variant_kind"] == "multiple"
            and fields["kind"] == "arbitrary"
            and _index(tag["field"], len(offsets))
            and tag["bits"] > 0
            and offsets[tag["field"]] + (tag["bits"] + 7) // 8 <= layout["size"],
        )


def qualify(raw: dict, bodies: dict[str, dict], *, complete_catalog: bool = False) -> None:
    """Join allocation function targets to the exact captured instance, retaining missing bodies."""
    if "memory" not in raw:
        return
    for node in validate(raw)["nodes"]:
        if node["kind"] != "function" or node["identity"] is None:
            continue
        mir_instances.qualify_calls(
            _function_view(raw, node), bodies, complete_catalog=complete_catalog
        )
        if node["selection"]["state"] == "captured" and node["identity"]["key"] in bodies:
            require(
                "constant target differs from captured instance identity",
                condition=bodies[node["identity"]["key"]]["execution"]["identity"]
                == node["identity"],
            )
