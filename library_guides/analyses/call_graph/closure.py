"""Bounded helper selection over exact captured targets, preserving every open edge."""

from __future__ import annotations

import json
from collections import defaultdict, deque
from typing import TYPE_CHECKING

from attrs import define, fields

from library_guides.analyses.behavior import mir_callables, mir_instances, mir_lifecycle
from library_guides.analyses.behavior.contracts import BehaviorRequest
from library_guides.analyses.behavior.integrity import limits_valid, require
from library_guides.analyses.behavior.service import MAX_NATIVE_BYTES
from library_guides.analyses.call_graph import index as call_index
from library_guides.analyses.call_graph.contracts import (
    CallableClosure,
    CallClosure,
    CallClosureRequest,
    CallIndex,
    CallObservation,
    LifecycleClosure,
    OwnerObservation,
    SelectedCall,
    SelectedReference,
)
from library_guides.corpus.evidence import resolve_bytes, select
from library_guides.corpus.native_contracts import NativeFact
from library_guides.corpus.schemas import revision_of

if TYPE_CHECKING:
    from library_guides.corpus.store import CorpusReader

MODEL = "library-guides.bounded-contextual-helper-selection.v1"
MAX_DEPTH = 64
FRONTIER = (
    "helper_selection_is_not_closed_behavior_or_whole_program_reachability",
    "only_observed_exact_item_calls_are_traversed",
    "generic_definition_transfer_does_not_apply_instance_substitutions",
    "call_graph_depth_differs_from_interpreter_recursion_depth",
)


@define(kw_only=True)
class Traversal:
    """Finite breadth-first selection state with independent depth, owner and byte bounds."""

    request: CallClosureRequest
    owners: dict[str, OwnerObservation]
    selected: set[str]
    pending: deque[tuple[str, int]]
    total: int

    def references(
        self,
        reader: CorpusReader,
        owner: OwnerObservation,
        targets: dict[str, list[OwnerObservation]],
        depth: int,
    ) -> tuple[SelectedReference, ...]:
        """Select exact captured function operands under the same traversal budgets.

        Returns:
            Potential body selections with separate original operand coordinates.

        """
        fact = reader.get("native_facts", owner.owner)
        assert isinstance(fact, NativeFact)
        raw = json.loads(resolve_bytes(reader, fact.original, max_bytes=MAX_NATIVE_BYTES))
        if "callables" not in raw:
            return ()
        result = []
        for item in mir_callables.validate(raw).values():
            point, call, capture = item["point"], item["call"], item["selection"]
            # A reference only becomes a callable term from a captured concrete item.
            target = capture["instance"] if capture["state"] == "captured" else ""
            observed = CallObservation(
                block=point["block"],
                declaration=call["declaration"] or "",
                target=target,
                instance_kind=call["instance_kind"],
                complete=bool(target),
                substitutions=(),
                frontier=tuple(call["frontier"]),
            )
            matches = tuple(sorted(value.owner for value in targets.get(target, ())))
            result.append(
                SelectedReference(
                    statement=point["statement"] if point["statement"] is not None else -1,
                    role=point["role"],
                    operand=point["operand"],
                    selection=SelectedCall(
                        caller=owner.owner,
                        block=point["block"],
                        target=target,
                        candidates=matches,
                        state=self.edge(observed, matches, depth),
                        frontier=(*call["frontier"], "instance_capture:" + capture["state"]),
                    ),
                )
            )
        return tuple(result)

    def drops(
        self,
        reader: CorpusReader,
        owner: OwnerObservation,
        targets: dict[str, list[OwnerObservation]],
        depth: int,
    ) -> tuple[SelectedCall, ...]:
        """Follow exact compiler drop glue under the common finite traversal budgets.

        Returns:
            Every original drop observation, including unresolved and bounded targets.

        """
        fact = reader.get("native_facts", owner.owner)
        assert isinstance(fact, NativeFact)
        raw = json.loads(resolve_bytes(reader, fact.original, max_bytes=MAX_NATIVE_BYTES))
        if "lifecycle" not in raw:
            return ()
        result = []
        for use in mir_lifecycle.validate(raw).values():
            capture = use["selection"]
            target = capture["instance"] if capture["state"] == "captured" else ""
            matches = tuple(sorted(value.owner for value in targets.get(target, ())))
            observed = CallObservation(
                block=use["block"],
                declaration="",
                target=target,
                instance_kind="shim",
                complete=bool(target),
                substitutions=(),
                frontier=(),
            )
            result.append(
                SelectedCall(
                    caller=owner.owner,
                    block=use["block"],
                    target=target,
                    candidates=matches,
                    state=self.edge(observed, matches, depth),
                    frontier=(
                        "instance_capture:" + capture["state"],
                        "drop_target_is_not_release_proof",
                    ),
                )
            )
        return tuple(result)

    def edge(self, call: CallObservation, matches: tuple[str, ...], depth: int) -> str:
        """Resolve one observed edge, adding a helper only within all selection bounds.

        Returns:
            A disposition retained even when the target cannot be selected.

        """
        if not call.complete:
            return "unresolved_dispatch"
        if not matches:
            return "body_absent_from_finite_catalog"
        if len(matches) > 1:
            return "ambiguous_contextual_bodies"
        target = matches[0]
        selected_state = (
            "selected_concrete_instance"
            if self.owners[target].phase == mir_instances.PHASE
            else "selected_generic_definition"
        )
        if target in self.selected:
            return selected_state
        rejection = self.reserve(target, depth)
        if rejection:
            return rejection
        self.selected.add(target)
        self.total += self.owners[target].native_bytes
        self.pending.append((target, depth + 1))
        return selected_state

    def reserve(self, target: str, depth: int) -> str:
        """Check the next complete owner before growing traversal state.

        Returns:
            The first exhausted dimension, or an empty string when within bounds.

        """
        if depth >= self.request.max_depth:
            return "depth_budget_exhausted"
        if len(self.selected) >= self.request.limits.owners:
            return "owner_budget_exhausted"
        if self.total + self.owners[target].native_bytes > MAX_NATIVE_BYTES:
            return "native_byte_budget_exhausted"
        return ""


def _selection(
    reader: CorpusReader, request: CallClosureRequest, index: CallIndex
) -> tuple[
    tuple[str, ...],
    tuple[SelectedCall, ...],
    tuple[SelectedReference, ...],
    tuple[SelectedCall, ...],
]:
    owners = {item.owner: item for item in index.owners}
    require(
        "invalid helper roots, context or graph budget",
        condition=index.profile == request.profile
        and 0 <= request.max_depth <= MAX_DEPTH
        and 0 < len(request.roots) <= request.limits.owners
        and len(set(request.roots)) == len(request.roots)
        and set(request.roots) <= set(owners),
    )
    total = sum(owners[key].native_bytes for key in request.roots)
    require("helper roots exceed native byte limit", condition=total <= MAX_NATIVE_BYTES)
    targets: dict[str, list[OwnerObservation]] = defaultdict(list)
    for owner in index.owners:
        if owner.phase == mir_instances.PHASE:
            fact = reader.get("native_facts", owner.owner)
            assert isinstance(fact, NativeFact)
            targets[fact.native_id].append(owner)
        else:
            targets[owner.definition].append(owner)
    traversal = Traversal(
        request=request,
        owners=owners,
        selected=set(request.roots),
        pending=deque((key, 0) for key in sorted(request.roots)),
        total=total,
    )
    calls = []
    references = []
    drops = []
    while traversal.pending:
        key, depth = traversal.pending.popleft()
        owner = owners[key]
        for call in owner.calls:
            matches = tuple(sorted(item.owner for item in targets.get(call.target, ())))
            frontier = list(call.frontier)
            if call.substitutions and not call.target.startswith("mir-instance:"):
                frontier.append("observed_substitutions_not_applied_to_generic_definition_body")
            state = traversal.edge(call, matches, depth)
            calls.append(
                SelectedCall(
                    caller=key,
                    block=call.block,
                    target=call.target,
                    candidates=matches,
                    state=state,
                    frontier=tuple(frontier),
                )
            )
        if index.model in {call_index.CALLABLE_MODEL, call_index.LIFECYCLE_MODEL}:
            references.extend(traversal.references(reader, owner, targets, depth))
        if index.model == call_index.LIFECYCLE_MODEL:
            drops.extend(traversal.drops(reader, owner, targets, depth))
    return (
        tuple(sorted(traversal.selected)),
        tuple(sorted(calls, key=lambda item: (item.caller, item.block))),
        tuple(
            sorted(
                references,
                key=lambda item: (
                    item.selection.caller,
                    item.selection.block,
                    item.statement,
                    item.role,
                    item.operand,
                ),
            )
        ),
        tuple(sorted(drops, key=lambda item: (item.caller, item.block))),
    )


def analyze(
    reader: CorpusReader, request: CallClosureRequest
) -> tuple[CallClosure, BehaviorRequest]:
    """Produce an ordinary finite behavior request and an auditable helper-selection result.

    Returns:
        Checked selection metadata and the existing interpreter's unweakened request contract.

    """
    limits_valid(request.limits)
    index = reader.get("call_indexes", request.index)
    require("helper selection requires a typed call index", condition=isinstance(index, CallIndex))
    assert isinstance(index, CallIndex)
    selected, calls, references, drops = _selection(reader, request, index)
    behavior = BehaviorRequest(
        logical_id="call-closure-behavior:" + request.logical_id,
        profile=request.profile,
        owners=selected,
        artifacts=tuple(sorted({item.artifact for item in index.owners if item.owner in selected})),
        limits=request.limits,
    )
    result = CallClosure(
        logical_id="call-closure:" + request.logical_id,
        profile=request.profile,
        request=revision_of(request),
        index=request.index,
        model=MODEL
        if index.model.endswith(".v1")
        else "library-guides.bounded-contextual-helper-selection.v2",
        roots=tuple(sorted(request.roots)),
        helpers=tuple(sorted(set(selected) - set(request.roots))),
        calls=calls,
        behavior=revision_of(behavior),
        frontier=FRONTIER,
        support=(
            select(request, "/roots", "explicit-root-denominator"),
            select(index, "/owners", "complete-finite-target-membership"),
        ),
    )
    if index.model in {call_index.CALLABLE_MODEL, call_index.LIFECYCLE_MODEL}:
        result = CallableClosure(
            logical_id=result.logical_id,
            profile=result.profile,
            request=result.request,
            index=result.index,
            model="library-guides.bounded-contextual-helper-selection.v3",
            roots=result.roots,
            helpers=result.helpers,
            calls=result.calls,
            behavior=result.behavior,
            support=result.support,
            frontier=("references_select_potential_bodies_not_executed_calls", *FRONTIER),
            references=references,
        )
        if index.model == call_index.LIFECYCLE_MODEL:
            attributes = {
                field.name: getattr(result, field.name) for field in fields(CallableClosure)
            }
            attributes["model"] = "library-guides.bounded-contextual-helper-selection.v4"
            attributes["frontier"] = (
                "drop_glue_selected_without_protocol_or_release_guarantee",
                *result.frontier,
            )
            result = LifecycleClosure(**attributes, drops=drops)
    return result, behavior
