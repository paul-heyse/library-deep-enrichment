"""Check concrete invocation types without treating annotations as runtime enforcement."""

from __future__ import annotations

from typing import TYPE_CHECKING

from library_deep_enrichment.analyses.behavior.integrity import require
from library_deep_enrichment.analyses.behavior.witness_values import Concrete

if TYPE_CHECKING:
    from library_deep_enrichment.analyses.behavior.contracts import BehaviorProgram


def validate(program: BehaviorProgram, inputs: dict[str, Concrete]) -> None:
    """Reject observations outside compiler-enforced Rust scalar and nominal input domains."""
    for name, value in inputs.items():
        types = {
            term.ty
            for term in program.terms
            if term.op in {"local", "argument"} and term.value == name and term.ty != "unknown"
        }
        if len(types) == 1:
            _typed(program, next(iter(types)), value)


def _typed(program: BehaviorProgram, ty: str, value: Concrete) -> None:
    if not ty.startswith("rust:"):
        return
    if ty == "rust:bool":
        require("witness input is not a Rust boolean", condition=value.kind == "bool")
    elif ty.startswith(("rust:i", "rust:u")) and ty[6:] in {"8", "16", "32", "64", "128"}:
        require("witness input is not a machine integer", condition=value.kind == "int")
        bits, signed = int(ty[6:]), ty.startswith("rust:i")
        lower = -(2 ** (bits - 1)) if signed else 0
        upper = 2 ** (bits - int(signed)) - 1
        require(
            "witness integer escapes the compiler input domain",
            condition=lower <= int(value.scalar) <= upper,
        )
    elif ty.startswith("rust:reference<") and ty.endswith(">"):
        require(
            "witness reference input lacks an observed referent",
            condition=value.kind == "reference" and len(value.children) == 1,
        )
        _typed(program, ty[len("rust:reference<") : -1], value.children[0])
    else:
        names = {
            item.definition
            for item in program.nominals
            if item.name == ty.removeprefix("rust:").split("<", 1)[0]
        }
        if names:
            require(
                "witness input belongs to another nominal build/context",
                condition=value.definition in names,
            )
