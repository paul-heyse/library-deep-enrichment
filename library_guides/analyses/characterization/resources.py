"""Region extent relationships and explicit ordering/interference obligations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from library_guides.analyses.characterization.contracts import OrderingObligation, ResourceRelation

if TYPE_CHECKING:
    from library_guides.analyses.behavior.contracts import BehaviorSummary
    from library_guides.analyses.characterization.dependencies import Ancestry

_SOURCES = frozenset({"argument", "global", "call", "unknown"})
_OBLIGATIONS = {
    "memory_write": "exposure_aliasing_and_synchronization_needed_before_interference_judgment",
    "release": "cleanup_target_ownership_and_nontermination_or_cancellation_need_separate_evidence",
    "unknown_call": "callee_may_access_shared_state_or_synchronize; effects_and_order_unresolved",
    "unknown": "unmodeled_effect_may_interfere_or_change_order",
    "unknown_dispatch": "dispatch_and_effect_target_set_unresolved",
    "descriptor_allocation": "descriptor_creation_does_not_prove_payload_ownership_or_activation",
}


def relations(summary: BehaviorSummary, ancestry: Ancestry) -> tuple[ResourceRelation, ...]:
    """Expose input/ambient dependence of existing guarded abstract region extents.

    Returns:
        Finite expression references; extent units and actual lifetime remain qualified.

    """
    result = []
    for ordinal, clause in enumerate(summary.clauses):
        for region in clause.regions:
            terms = tuple(
                summary.terms[index] for index in ancestry.sources(region.extent, _SOURCES)
            )
            result.append(
                ResourceRelation(
                    clause=ordinal,
                    root=region.root,
                    extent=region.extent,
                    kind=region.kind,
                    argument_dependencies=tuple(
                        sorted({term.value for term in terms if term.op == "argument"})
                    ),
                    ambient_dependencies=tuple(
                        sorted({term.value for term in terms if term.op in {"global", "call"}})
                    ),
                    escaped=region.escaped,
                    unique=region.unique,
                    frontier=(
                        "extent_is_the_summary_model_measure_not_a_byte_or_peak_memory_bound",
                        "guard_assumptions_and_summary_frontiers_remain_applicable",
                        "escape_is_not_a_proof_of_retention_duration_or_owner_lifetime",
                        *(
                            ("extent_contains_unresolved_values",)
                            if any(term.op == "unknown" for term in terms)
                            else ()
                        ),
                    ),
                )
            )
    return tuple(result)


def ordering(summary: BehaviorSummary) -> tuple[OrderingObligation, ...]:
    """Retain effect/suspension evidence while preventing lexical order from proving concurrency.

    Returns:
        Reusable obligations at exact outcome clauses and retained effect locations.

    """
    result = []
    for ordinal, clause in enumerate(summary.clauses):
        result.extend(
            OrderingObligation(
                clause=ordinal,
                kind=effect.kind,
                target=effect.target,
                point=effect.point,
                phase=effect.phase,
                obligation=_OBLIGATIONS[effect.kind],
            )
            for effect in clause.effects
            if effect.kind in _OBLIGATIONS
        )
        if clause.outcome == "suspend":
            result.append(
                OrderingObligation(
                    clause=ordinal,
                    kind="suspension",
                    target="",
                    point="",
                    phase="suspend",
                    obligation="resumption_cancellation_and_intertask_order_require_protocol_and_scheduler_evidence",
                )
            )
    return tuple(result)
