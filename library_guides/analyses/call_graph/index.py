"""Index complete admitted compiler catalogs without guessing targets from symbols."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from library_guides.analyses.behavior import mir_callables, mir_instances, mir_lifecycle
from library_guides.analyses.behavior.integrity import require
from library_guides.analyses.call_graph.contracts import (
    ArgumentObservation,
    CallIndex,
    CallIndexRequest,
    CallObservation,
    OwnerObservation,
)
from library_guides.corpus.backend import BudgetExceededError
from library_guides.corpus.encoding import digest
from library_guides.corpus.evidence import resolve_bytes, select
from library_guides.corpus.native_contracts import NativeArtifact, NativeFact
from library_guides.corpus.schemas import revision_of

if TYPE_CHECKING:
    from library_guides.corpus.store import CorpusReader

MODEL = "library-guides.contextual-native-call-index.v1"
INSTANCE_MODEL = "library-guides.contextual-native-call-index.v2"
CALLABLE_MODEL = "library-guides.contextual-native-call-index.v3"
LIFECYCLE_MODEL = "library-guides.contextual-native-call-index.v4"
MAX_ARTIFACTS = 128
MAX_FACTS = 100_000
MAX_BYTES = 128 * 1024 * 1024
FRONTIER = (
    "finite_captured_compiler_catalog_not_whole_program_or_all_configurations",
    "generic_definition_bodies_not_monomorphized_instances",
    "explicit_calls_exclude_unobserved_vtable_drop_glue_and_function_reference_uses",
    "exact_item_target_does_not_prove_closed_effects_or_applied_substitutions",
    "type_projection_fingerprint_is_not_semantic_type_equivalence",
)


def _arguments(raw: list[dict]) -> tuple[ArgumentObservation, ...]:
    result = []
    for position, value in enumerate(raw):
        kind = value["kind"]
        frontier = value.get("frontier")
        result.append(
            ArgumentObservation(
                position=position,
                kind=kind,
                scalar=value.get("value") or "",
                encoding=value.get("encoding") or "",
                type_fingerprint=digest(value["ty"]) if value.get("ty") is not None else "",
                frontier=(frontier,) if frontier else (),
            )
        )
    return tuple(result)


def _owner(
    reader: CorpusReader, fact: NativeFact, artifact: NativeArtifact
) -> tuple[OwnerObservation, dict]:
    raw = json.loads(resolve_bytes(reader, fact.original, max_bytes=MAX_BYTES))
    extended = artifact.schema in {mir_instances.SCHEMA, mir_callables.SCHEMA, mir_lifecycle.SCHEMA}
    require(
        "native call indexing requires a typed generic MIR owner",
        condition=raw.get("kind") in ({"mir_owner", "mir_instance"} if extended else {"mir_owner"})
        and isinstance(raw.get("behavior"), dict)
        and raw["behavior"].get("phase")
        in (
            {mir_instances.GENERIC_PHASE, mir_instances.PHASE}
            if extended
            else {mir_instances.GENERIC_PHASE}
        ),
    )
    metadata = raw["behavior"]
    instances: dict[int, dict] = mir_instances.validate(raw) if extended else {}
    calls = tuple(
        CallObservation(
            block=call["block"],
            declaration=call.get("declaration") or "",
            target=mir_instances.target(call, instances.get(call["block"])),
            instance_kind=call["instance_kind"],
            complete=call["complete"],
            substitutions=_arguments(call["substitutions"]),
            frontier=(
                *call["frontier"],
                *(
                    ("instance_capture:" + instances[call["block"]]["state"],)
                    if instances and instances[call["block"]]["state"] != "captured"
                    else ()
                ),
            ),
        )
        for call in metadata["calls"]
    )
    require(
        "native call metadata does not account for every original call terminator",
        condition={call.block for call in calls}
        == {exit_["block"] for exit_ in raw["payload"]["exits"] if exit_["kind"] == "call"}
        and len({call.block for call in calls}) == len(calls),
    )
    require(
        "complete native call target lacks an exact item identity",
        condition=all(
            not call.complete
            or (
                call.instance_kind
                in ({"item", "shim"} if artifact.schema == mir_lifecycle.SCHEMA else {"item"})
                and (
                    call.target.startswith("definition:")
                    or (extended and call.target.startswith("mir-instance:"))
                )
            )
            for call in calls
        ),
    )
    owner = OwnerObservation(
        owner=revision_of(fact),
        artifact=revision_of(artifact),
        context=artifact.context,
        definition=metadata["definition"],
        phase=metadata["phase"],
        native_bytes=fact.original.end - fact.original.start,
        calls=tuple(sorted(calls, key=lambda item: item.block)),
        frontier=tuple(metadata["frontier"]),
    )
    return owner, raw


def analyze(reader: CorpusReader, request: CallIndexRequest) -> CallIndex:
    """Retain the complete native owner and call denominator within explicit read budgets.

    Returns:
        A source-replayable index, including targets without a captured body.

    Raises:
        BudgetExceededError: The complete catalog exceeds an explicit read budget.

    """
    require(
        "invalid native call catalog or budget",
        condition=0 < len(request.artifacts) <= MAX_ARTIFACTS
        and len(set(request.artifacts)) == len(request.artifacts)
        and 0 < request.max_facts <= MAX_FACTS
        and 0 < request.max_bytes <= MAX_BYTES,
    )
    owners, support = [], [select(request, "/artifacts", "finite-compiler-catalog")]
    total = 0
    extended = False
    callables = False
    lifecycle = False
    for artifact in reader.get_many("native_artifacts", sorted(request.artifacts)):
        require(
            "native call catalog escaped its typed compiler profile",
            condition=isinstance(artifact, NativeArtifact)
            and artifact.profile == request.profile
            and (artifact.lane, artifact.schema)
            in {
                ("mir_execution", "library-guides.mir-execution.v1"),
                ("mir_instances", mir_instances.SCHEMA),
                ("mir_callables", mir_callables.SCHEMA),
                ("mir_lifecycle", mir_lifecycle.SCHEMA),
            },
        )
        assert isinstance(artifact, NativeArtifact)
        lifecycle = lifecycle or artifact.schema == mir_lifecycle.SCHEMA
        extended = extended or artifact.schema in {
            mir_instances.SCHEMA,
            mir_callables.SCHEMA,
            mir_lifecycle.SCHEMA,
        }
        callables = callables or artifact.schema in {mir_callables.SCHEMA, mir_lifecycle.SCHEMA}
        count = 0
        originals: dict[str, dict] = {}
        for fact in reader.filtered_records("native_facts", (("artifact", revision_of(artifact)),)):
            assert isinstance(fact, NativeFact)
            count += 1
            total += fact.original.end - fact.original.start
            if len(owners) >= request.max_facts or total > request.max_bytes:
                message = "native call catalog read budget exhausted"
                raise BudgetExceededError(message)
            owner, raw = _owner(reader, fact, artifact)
            owners.append(owner)
            originals[fact.native_id] = raw
            support.append(select(fact, "/original", "complete-native-call-observation"))
        require(
            "native call catalog has an incomplete owner denominator",
            condition=count == artifact.record_count,
        )
        for raw in originals.values():
            mir_instances.qualify_calls(raw, originals, complete_catalog=True)
            if artifact.schema in {mir_callables.SCHEMA, mir_lifecycle.SCHEMA}:
                mir_callables.validate(raw)
                mir_callables.qualify(raw, originals, complete_catalog=True)
            if artifact.schema == mir_lifecycle.SCHEMA:
                mir_lifecycle.qualify(raw, originals, complete_catalog=True)
        support.append(select(artifact, "/record_count", "complete-captured-owner-denominator"))
    return CallIndex(
        logical_id="call-index:" + request.logical_id,
        profile=request.profile,
        request=revision_of(request),
        model=LIFECYCLE_MODEL
        if lifecycle
        else CALLABLE_MODEL
        if callables
        else INSTANCE_MODEL
        if extended
        else MODEL,
        owners=tuple(sorted(owners, key=lambda item: item.owner)),
        frontier=FRONTIER
        if not extended
        else (
            "finite_generic_and_observed_concrete_instance_catalog",
            "instance_capture_limits_and_unavailable_bodies_remain_explicit",
            *(
                ("function_reference_operands_retained_in_original_native_support",)
                if callables
                else ()
            ),
            *FRONTIER[:1],
            *FRONTIER[2:],
        ),
        support=tuple(sorted(support, key=lambda item: (item.family, item.revision, item.field))),
    )
