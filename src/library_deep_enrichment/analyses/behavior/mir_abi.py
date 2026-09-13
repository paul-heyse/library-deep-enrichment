"""Normalize compiler Rust-call tuple spreading without inferring callable signatures."""

from __future__ import annotations

from typing import TYPE_CHECKING

from library_deep_enrichment.analyses.behavior.integrity import require
from library_deep_enrichment.analyses.behavior.mir_types import type_name

if TYPE_CHECKING:
    from library_deep_enrichment.analyses.behavior.builder import GraphBuilder


def validate(raw: dict) -> dict[int, dict]:
    """Check calling convention observations against original MIR argument denominators.

    Returns:
        The exact signature observation for every original call terminator.

    """
    uses = raw["lifecycle"]
    locals_ = {item["index"]: item for item in raw["payload"]["locals"]}
    spread = uses["spread_arg"]
    require(
        "spread argument must be the final tuple argument local",
        condition=spread is None
        or (
            spread in locals_
            and locals_[spread]["role"] == "argument"
            and locals_[spread]["ty"]["kind"] == "tuple"
            and spread == max(key for key, item in locals_.items() if item["role"] == "argument")
        ),
    )
    calls = {item["block"]: item for item in raw["payload"]["exits"] if item["kind"] == "call"}
    result = {}
    for signature in uses["call_abis"]:
        block = signature["block"]
        require("duplicate or missing call ABI", condition=block in calls and block not in result)
        inputs = signature["inputs"]
        if signature["abi"] is None:
            require(
                "unknown call ABI must not manufacture a signature",
                condition=not inputs and signature["output"] is None,
            )
        if signature["abi"] == "RustCall":
            arguments = calls[block]["args"]
            require(
                "Rust-call requires a final tuple with the observed argument shape",
                condition=bool(inputs)
                and len(inputs) == len(arguments)
                and inputs[-1]["kind"] == "tuple"
                and arguments[-1]["ty"] == inputs[-1],
            )
        result[block] = signature
    require("call ABI denominator is incomplete", condition=set(result) == set(calls))
    return result


def parameters(builder: GraphBuilder, raw: dict) -> tuple[str, ...]:
    """Reconstitute a spread tuple local from compiler-declared scalar entry arguments.

    Returns:
        Parameters in the same expanded Rust-call convention used for call transfers.

    """
    spread = raw["lifecycle"]["spread_arg"]
    parameters_ = []
    for local in raw["payload"]["locals"]:
        if local["role"] != "argument":
            continue
        name = f"_{local['index']}"
        if local["index"] != spread:
            parameters_.append(name)
            continue
        fields = []
        for index, ty in enumerate(local["ty"]["args"]):
            parameter = f"{name}:spread:{index}"
            parameters_.append(parameter)
            builder.local_types[parameter] = type_name(ty)
            fields.append(builder.term("local", value=parameter, ty=type_name(ty)))
        builder.emit(
            "assign",
            destination=name,
            value=builder.term("aggregate", tuple(fields), "tuple", type_name(local["ty"])),
        )
    return tuple(parameters_)


def qualify(raw: dict, bodies: dict[str, dict]) -> None:
    """Reject incompatible expanded tuple shapes at captured concrete body boundaries."""
    signatures = validate(raw)
    for call in raw["execution"]["calls"]:
        target = bodies.get(call["instance"]) if call["state"] == "captured" else None
        if target is None or "lifecycle" not in target:
            continue
        signature = signatures[call["block"]]
        if signature["abi"] is None:
            continue
        passed = signature["inputs"]
        if signature["abi"] == "RustCall":
            passed = [*passed[:-1], *passed[-1]["args"]]
        received = []
        for local in target["payload"]["locals"]:
            if local["role"] == "argument":
                received.extend(
                    local["ty"]["args"]
                    if local["index"] == target["lifecycle"]["spread_arg"]
                    else [local["ty"]]
                )
        require(
            "captured call ABI differs from expanded body argument shapes",
            condition=len(passed) == len(received)
            and all(
                _tuple_shape(left) == _tuple_shape(right)
                for left, right in zip(passed, received, strict=True)
            ),
        )


def _tuple_shape(ty: dict) -> tuple:
    return (
        tuple(_tuple_shape(child) for child in ty["args"]) if ty["kind"] == "tuple" else ("scalar",)
    )


def arguments(builder: GraphBuilder, exit_: dict, values: tuple[int, ...]) -> tuple[int, ...]:
    """Expand only a retained Rust-call tuple signature.

    Returns:
        Scalar component projections, including the empty tuple's zero arguments.

    """
    signature = exit_.get("call_abi") or {}
    if signature.get("abi") != "RustCall":
        return values
    fields = tuple(
        builder.term("field", (values[-1],), str(index), type_name(ty))
        for index, ty in enumerate(signature["inputs"][-1]["args"])
    )
    return (*values[:-1], *fields)
