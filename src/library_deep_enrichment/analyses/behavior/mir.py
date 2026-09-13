"""Normalize retained compiler MIR into the owned execution graph without source heuristics."""

from __future__ import annotations

from attrs import evolve

from library_deep_enrichment.analyses.behavior import (
    mir_abi,
    mir_callables,
    mir_instances,
    mir_lifecycle,
)
from library_deep_enrichment.analyses.behavior.builder import GraphBuilder, Origin
from library_deep_enrichment.analyses.behavior.contracts import BehaviorProgram, Limits
from library_deep_enrichment.analyses.behavior.integrity import program_valid
from library_deep_enrichment.analyses.behavior.mir_types import nominals, target_types, type_name

MODEL = "rust-mir-execution.v2"
_TYPED_OPERATORS = {
    "add": "add",
    "subtract": "sub",
    "multiply": "mul",
    "divide": "div",
    "remainder": "mod",
    "xor": "bit_xor",
    "and": "bit_and",
    "or": "bit_or",
    "shift_left": "shl",
    "shift_right": "shr",
    "equal": "eq",
    "not_equal": "ne",
    "less": "lt",
    "less_equal": "le",
    "greater": "gt",
    "greater_equal": "ge",
    "not": "invert",
    "negate": "neg",
}
_OPERATORS = {
    "Add": "add",
    "Sub": "sub",
    "Mul": "mul",
    "Div": "div",
    "Rem": "mod",
    "BitXor": "bit_xor",
    "BitAnd": "bit_and",
    "BitOr": "bit_or",
    "Shl": "shl",
    "Shr": "shr",
    "Eq": "eq",
    "Ne": "ne",
    "Lt": "lt",
    "Le": "le",
    "Gt": "gt",
    "Ge": "ge",
    "Not": "invert",
    "Neg": "neg",
}
_SIMPLE = {
    "use": "",
    "copy_for_deref": "",
    "borrow": "borrow",
    "address_of": "address",
    "length": "length",
    "discriminant": "discriminant",
    "cast": "cast",
}


def _type(raw: dict | None) -> str:
    return type_name(raw)


def _span(builder: GraphBuilder, raw: dict) -> tuple[int, int]:
    if raw.get("mapping") != "exact_original_file_bytes":
        builder.unknown(
            "source_mapping",
            "source",
            str(builder.current),
            "compiler source has no exact byte mapping",
        )
    return int(raw.get("byte_start") or 0), int(raw.get("byte_end") or 0)


def _project(builder: GraphBuilder, value: int, projection: dict) -> int:
    kind = projection["kind"]
    if kind == "field":
        return builder.term("field", (value,), str(projection["index"]), _type(projection["ty"]))
    if kind == "deref":
        return builder.term("deref", (value,))
    if kind == "index":
        index = builder.term("local", value=f"_{projection['local']}")
        return builder.term("index", (value, index))
    if kind == "constant_index":
        index = builder.term("literal", value=str(projection["offset"]), ty="rust:usize")
        return builder.term(
            "index", (value, index), "from_end" if projection["from_end"] else "from_start"
        )
    if kind == "downcast":
        return builder.term("downcast", (value,), str(projection["variant"]))
    return _slice_projection(builder, value, projection)


def _slice_projection(builder: GraphBuilder, value: int, projection: dict) -> int:
    kind = projection["kind"]
    if kind == "subslice":
        start = builder.term("literal", value=str(projection["from"]), ty="rust:usize")
        end = builder.term("literal", value=str(projection["to"]), ty="rust:usize")
        return builder.term(
            "slice", (value, start, end), "from_end" if projection["from_end"] else "from_start"
        )
    return builder.unknown("projection", "memory", str(builder.current), kind)


def _place(builder: GraphBuilder, raw: dict, ty: str = "unknown") -> int:
    name = f"_{raw['local']}"
    value = builder.term("local", value=name, ty=builder.local_types.get(name, ty))
    for projection in raw["projection"]:
        value = _project(builder, value, projection)
    return value


def _operand(builder: GraphBuilder, raw: dict) -> int:
    ty = _type(raw.get("ty"))
    if raw.get("callable_target"):
        return builder.term("function", value=raw["callable_target"], ty="rust:function_pointer")
    if raw.get("callable_frontier"):
        return builder.unknown(
            "function_reference", "call", str(builder.current), raw["callable_frontier"]
        )
    if raw.get("place") is not None:
        return _place(builder, raw["place"], ty)
    if raw.get("literal") is not None:
        literal = raw["literal"]
        return builder.term("literal", value=str(literal["value"]), ty=ty)
    return builder.unknown(
        "operand", "value", str(builder.current), str(raw.get("unknown") or raw["mode"])
    )


def _rvalue(builder: GraphBuilder, event: dict) -> int:
    operands = tuple(_operand(builder, raw) for raw in event["values"])
    if event.get("function_pointer_coercion"):
        return operands[0]
    kind = event["kind"]
    qualifier = str(event.get("qualifier") or "")
    if kind in _SIMPLE and operands:
        destination = event.get("destination") or {}
        ty = builder.local_types.get(f"_{destination.get('local')}", "unknown")
        return (
            builder.term(_SIMPLE[kind], operands, qualifier, ty) if _SIMPLE[kind] else operands[0]
        )
    if kind in {"binary", "unary", "checked_binary"}:
        return _scalar_operation(builder, event, operands)
    if kind == "aggregate" and event.get("constructor"):
        constructor = event["constructor"]
        variant = constructor.get("variant_index")
        label = str(constructor.get("nominal") or constructor["kind"])
        if variant is not None:
            label += f"#variant:{variant}"
        return builder.term("aggregate", operands, label, "rust:" + label)
    return builder.unknown("rvalue", "value", str(builder.current), kind + ":" + qualifier)


def _scalar_operation(builder: GraphBuilder, event: dict, operands: tuple[int, ...]) -> int:
    typed = event.get("scalar_operator")
    qualifier = str(event.get("qualifier") or "")
    op = _TYPED_OPERATORS.get(typed["operator"]) if typed else _OPERATORS.get(qualifier)
    mode = (
        typed["mode"]
        if typed
        else "checked_pair"
        if event["kind"] == "checked_binary"
        else "ordinary"
    )
    if op is None or mode == "unchecked":
        return builder.unknown(
            "scalar_operation",
            "value",
            str(builder.current),
            "unsupported operator or unchecked precondition: " + str(typed or qualifier),
        )
    ty = builder.terms[operands[0]].ty if operands else "unknown"
    if op == "invert" and ty == "rust:bool":
        op = "not"
    if op in {"eq", "ne", "lt", "le", "gt", "ge"}:
        ty = "rust:bool"
    if mode == "checked_pair":
        op = "checked_" + op
    return builder.term(op, operands, ty=ty)


def _store(builder: GraphBuilder, destination: dict, value: int, span: tuple[int, int]) -> None:
    if destination["projection"]:
        place = _place(builder, destination)
        builder.emit("write", value=value, call=("", (place,)), span=span)
    else:
        builder.emit("assign", destination=f"_{destination['local']}", value=value, span=span)


def _event(builder: GraphBuilder, event: dict) -> None:
    builder.current = event["block"]
    span = _span(builder, event["source"])
    kind = event["kind"]
    if kind in {"storage_live", "storage_dead"}:
        builder.emit(kind, destination=f"_{event['destination']['local']}", span=span)
    elif kind == "non_transfer":
        builder.emit("nop", span=span)
    elif kind == "set_discriminant":
        old = _place(builder, event["destination"])
        value = builder.term("set_variant", (old,), str(event["qualifier"]))
        _store(builder, event["destination"], value, span)
    elif event.get("destination") is not None:
        _store(builder, event["destination"], _rvalue(builder, event), span)
    else:
        builder.unknown("statement", "effects", str(builder.current), kind)
        builder.emit("unknown", span=span)


def _switch(builder: GraphBuilder, exit_: dict) -> None:
    operand = _operand(builder, exit_["args"][0])
    remaining = builder.term("literal", value="true", ty="rust:bool")
    for branch in exit_["branches"]:
        literal = builder.term("literal", value=str(branch["value"]), ty=builder.terms[operand].ty)
        condition = builder.term("eq", (operand, literal), ty="rust:bool")
        builder.edge(branch["target"], condition=condition)
        opposite = builder.term("not", (condition,), ty="rust:bool")
        remaining = builder.term("and", (remaining, opposite), ty="rust:bool")
    if exit_.get("otherwise") is not None:
        builder.edge(exit_["otherwise"], condition=remaining)


def _call(builder: GraphBuilder, exit_: dict, native_id: str) -> None:
    arguments = mir_abi.arguments(
        builder, exit_, tuple(_operand(builder, raw) for raw in exit_["args"])
    )
    instance = exit_.get("instance") or {}
    definition = instance.get("local_definition")
    target = exit_.get("contextual_target") or (
        native_id.rsplit(":", 1)[0] + ":" + definition if definition else ""
    )
    dynamic = not target and exit_.get("callable_flow", False)
    if not target and not dynamic:
        builder.unknown("callee", "effects", str(builder.current), str(instance))
    destination = exit_["destination"]
    temporary = f"$call:{builder.current}"
    builder.emit(
        "call",
        destination=temporary,
        value=_operand(builder, exit_["callee"]) if dynamic else -1,
        call=(target, arguments),
        span=_span(builder, exit_["source"]),
    )
    # The return destination is initialized only along a successful return edge.
    original = builder.current
    for successor in exit_["successors"]:
        builder.current = original
        if successor == exit_.get("unwind_block"):
            builder.edge(successor, kind="unwind")
        else:
            returned = builder.block()
            builder.edge(returned)
            builder.current = returned
            _store(
                builder,
                destination,
                builder.term("local", value=temporary),
                _span(builder, exit_["source"]),
            )
            builder.edge(successor)
    builder.current = original


def _exit(builder: GraphBuilder, exit_: dict, native_id: str) -> None:
    builder.current = exit_["block"]
    kind = exit_["kind"]
    if kind == "switch":
        _switch(builder, exit_)
    elif kind == "call":
        _call(builder, exit_, native_id)
    elif kind in {"return", "resume", "abort", "unreachable"}:
        if kind != "unreachable":
            op = {"return": "return", "resume": "unwind", "abort": "abort"}[kind]
            value = (
                builder.term("aggregate", value="tuple", ty="rust:tuple")
                if kind == "return" and exit_.get("unit_return")
                else builder.term("local", value="_0")
            )
            builder.emit(op, value=value, span=_span(builder, exit_["source"]))
        else:
            builder.emit("effect", call=("unreachable", ()))
    else:
        _control(builder, exit_)


def _control(builder: GraphBuilder, exit_: dict) -> None:
    kind = exit_["kind"]
    if kind == "drop" and exit_.get("drop_target"):
        _drop_call(builder, exit_)
        return
    condition = _operand(builder, exit_["args"][0]) if kind == "assert" else -1
    if kind == "drop":
        builder.emit(
            "drop",
            value=_place(builder, exit_["destination"]),
            span=_span(builder, exit_["source"]),
        )
        builder.unknown("drop", "lifecycle", str(builder.current), "drop glue target not retained")
    elif kind not in {"assert", "goto"}:
        builder.emit("unknown", span=_span(builder, exit_["source"]))
        builder.unknown("terminator", "effects", str(builder.current), kind)
    for successor in exit_["successors"]:
        unwind = successor == exit_.get("unwind_block")
        builder.edge(
            successor,
            condition=condition,
            positive=(not bool(exit_.get("expected")))
            if unwind
            else bool(exit_.get("expected", True)),
            kind="unwind" if unwind else "normal",
        )
    if kind == "assert" and exit_.get("unwind_block") is None:
        failure = builder.block()
        builder.edge(
            failure, condition=condition, positive=not bool(exit_["expected"]), kind="unwind"
        )
        builder.current = failure
        builder.emit("abort" if exit_.get("unwind") == "Terminate" else "unwind")


def _drop_call(builder: GraphBuilder, exit_: dict) -> None:
    span = _span(builder, exit_["source"])
    argument = builder.term("address", (_place(builder, exit_["destination"]),))
    builder.emit("effect", call=("drop_enter", (argument,)), span=span)
    builder.emit(
        "call",
        destination=f"$drop:{builder.current}",
        call=(exit_["drop_target"], (argument,)),
        span=span,
    )
    original = builder.current
    for successor in exit_["successors"]:
        builder.current = original
        if successor == exit_.get("unwind_block"):
            builder.edge(successor, kind="unwind")
        else:
            completed = builder.block()
            builder.edge(completed)
            builder.current = completed
            builder.emit("effect", call=("drop_return", ()), span=span)
            builder.edge(successor)
    builder.current = original


def normalize(origin: Origin, raw: dict, limits: Limits) -> BehaviorProgram:
    """Project an actual retained MIR owner and preserve unmodeled boundaries.

    Returns:
        A validated executable graph with its original source/context references.

    """
    contextual = raw.get("behavior") or {}
    target = contextual.get("target") or {}
    normalized = target_types(raw, target.get("pointer_bits", 0))
    assert isinstance(normalized, dict)
    raw = normalized
    callable_flow = "callables" in raw
    if callable_flow:
        mir_callables.overlay(raw)
    lifecycle = "lifecycle" in raw
    if lifecycle:
        mir_lifecycle.overlay(raw)
    contextual = raw.get("behavior") or {}
    body = raw["payload"]
    operators = {
        (item["block"], item["statement"]): item for item in contextual.get("operators", ())
    }
    calls = {item["block"]: item for item in contextual.get("calls", ())}
    instances = mir_instances.validate(raw) if "execution" in raw else {}
    builder = GraphBuilder(
        origin,
        mir_lifecycle.MODEL if lifecycle else mir_callables.MODEL if callable_flow else MODEL,
        limits=limits,
    )
    builder.local_types = {f"_{local['index']}": _type(local["ty"]) for local in body["locals"]}
    for name, ty in builder.local_types.items():
        builder.term("local", value=name, ty=ty)
    builder.blocks = sorted(exit_["block"] for exit_ in body["exits"])
    parameters = (
        mir_abi.parameters(builder, raw)
        if lifecycle
        else tuple(f"_{local['index']}" for local in body["locals"] if local["role"] == "argument")
    )
    for event in sorted(body["events"], key=lambda row: (row["block"], row["statement"])):
        _event(
            builder,
            {**event, "scalar_operator": operators.get((event["block"], event["statement"]))},
        )
    for exit_ in body["exits"]:
        call = calls.get(exit_["block"], {})
        target = mir_instances.target(call, instances.get(exit_["block"]))
        _exit(
            builder,
            {**exit_, "contextual_target": target, "callable_flow": callable_flow},
            raw["id"],
        )
        instance = instances.get(exit_["block"])
        if instance is not None and instance["state"] != "captured":
            builder.unknown("instance_selection", "call", str(exit_["block"]), instance["state"])
    for reason in body.get("frontier", ()):
        if not reason.endswith(":callee_effects"):
            builder.unknown("compiler_frontier", "execution", "body", reason)
    program = evolve(builder.finish(parameters), nominals=nominals(contextual))
    program_valid(program, limits)
    return program
