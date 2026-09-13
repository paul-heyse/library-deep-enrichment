"""Independent consequence qualification; valid citations alone never entail prose."""

from __future__ import annotations

from typing import TYPE_CHECKING

from library_deep_enrichment.corpus.backend import CorpusError
from library_deep_enrichment.corpus.contracts import (
    Disposition,
    Operation,
    Policy,
    Qualification,
    Scope,
)
from library_deep_enrichment.corpus.evidence import resolve, select
from library_deep_enrichment.corpus.schemas import revision_of
from library_deep_enrichment.semantics.contracts import Assertion, Predicate, Proof, Rule
from library_deep_enrichment.semantics.rules import CHECKER, consequence

if TYPE_CHECKING:
    from library_deep_enrichment.corpus.store import CorpusReader


def check_consequence(reader: CorpusReader, proof: Proof) -> Qualification:
    """Reconstruct a precise consequence from retained input and model revisions.

    Returns:
        A successful receipt only for an approved rule and exact consequence.

    Raises:
        CorpusError: A purported certificate is malformed, altered, or unsupported.

    """
    assertion = reader.get("assertions", proof.conclusion)
    rule = reader.get("rules", proof.rule)
    if not isinstance(assertion, Assertion) or not isinstance(rule, Rule):
        message = "invalid consequence certificate contract"
        raise CorpusError(message)
    if proof.checker != CHECKER or not proof.premises or proof.premises != assertion.support:
        message = "certificate does not retain its exact consequence premises"
        raise CorpusError(message)
    expected_scopes = (assertion.scope,) if assertion.scope else ()
    if (
        proof.read_set != (*assertion.support, select(rule, "/pattern", "model"))
        or proof.scopes != expected_scopes
        or proof.steps != (rule.algorithm, "contextual-owner", "exact-consequence")
    ):
        message = "certificate omits or changes its declared read set, scope, or derivation steps"
        raise CorpusError(message)
    for selection in (*proof.premises, *proof.read_set):
        resolve(reader, selection)
    source = reader.get(proof.premises[0].family, proof.premises[0].revision)
    operation = reader.get("operations", assertion.subject)
    if not isinstance(operation, Operation) or consequence(rule, source, operation) != assertion:
        message = "predicate, value, context, or qualifier is not entailed by the cited rule inputs"
        raise CorpusError(message)
    predicate = reader.get("predicates", assertion.predicate)
    if not isinstance(predicate, Predicate) or (
        assertion.value.kind != predicate.value_kind
        or assertion.interpretation not in predicate.interpretations
        or (predicate.allowed_values and assertion.value.text not in predicate.allowed_values)
    ):
        message = "consequence violates its typed predicate definition"
        raise CorpusError(message)
    approvals = [
        policy
        for policy in reader.records("policies")
        if isinstance(policy, Policy)
        and policy.kind == "rule-approval"
        and policy.subject == revision_of(rule)
        and assertion.predicate in policy.allowed_predicates
        and set(policy.required_scopes) <= set(proof.scopes)
        and all(
            isinstance(scope := reader.get("scopes", revision), Scope)
            and scope.disposition == Disposition.COMPLETE
            for revision in policy.required_scopes
        )
    ]
    approvals.sort(key=revision_of)
    qualified = bool(approvals)
    return Qualification(
        logical_id=f"qualification:{proof.conclusion}",
        profile=assertion.profile,
        subject=proof.conclusion,
        method="checked-rule-consequence",
        authority=revision_of(approvals[0]) if approvals else "",
        support=(revision_of(proof), revision_of(rule), *[revision_of(item) for item in approvals]),
        disposition=Disposition.COMPLETE if qualified else Disposition.PARTIAL,
        reason="Exact approved consequence verified"
        if qualified
        else "Rule has no independent approval",
    )
