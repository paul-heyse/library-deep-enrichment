"""Bounded rule matching produces candidates for independent consequence checks."""

from __future__ import annotations

from typing import TYPE_CHECKING

import regex as re

from library_guides.corpus.backend import BudgetExceededError, CorpusError
from library_guides.corpus.contracts import Operation, Passage, Record, RegistryEntry, TypeUse
from library_guides.corpus.encoding import digest, payload
from library_guides.corpus.evidence import field_value, select
from library_guides.corpus.schemas import codec_for, revision_of
from library_guides.semantics.contracts import (
    Assertion,
    Interpretation,
    Proof,
    Rule,
    State,
    Value,
    ValueKind,
)
from library_guides.semantics.enrichment_contracts import WitnessObservation

if TYPE_CHECKING:
    from collections.abc import Iterator

    from library_guides.corpus.store import CorpusReader

CHECKER = "library-guides.typed-consequence.v1"
MAX_PATTERN_BYTES = 2048
MAX_SOURCE_CHARACTERS = 65_536
MAX_MATCH_SECONDS = 0.05
_QUALIFIERS = re.compile(
    r"\b(?:not|never|unless|except|may|might|could|if|depending|typically|usually|optionally)\b",
    re.IGNORECASE,
)


def _direct_output(source: Record) -> bool:
    return (
        isinstance(source, TypeUse)
        and source.role == "output"
        and source.direct
        and source.resolution == "exact"
    )


def _interpretation_matches(rule: Rule, source: Record) -> bool:
    if rule.algorithm == "witness-field":
        return (
            isinstance(source, WitnessObservation)
            and rule.interpretation == Interpretation.WITNESSED
            and rule.quantifier == "retained-inputs"
            and rule.domain == "exact-execution-scope"
            and rule.selector == "/field"
        )
    expected = (
        Interpretation.UPSTREAM_CONTRACT
        if rule.algorithm in {"document-sentence", "document-template"}
        else Interpretation.DECLARATION
    )
    return rule.interpretation == expected


def matching_text(rule: Rule, source: Record) -> str | None:
    """Apply a finite source rule without discarding sentence qualifications.

    Returns:
        The matched source text, or no consequence when the rule cannot establish it.

    Raises:
        CorpusError: The rule requests an unsupported algorithm or oversized pattern.

    """
    if codec_for(source).family != rule.source_family:
        return None
    if (
        rule.algorithm
        not in {
            "declaration-pattern",
            "document-sentence",
            "document-template",
            "direct-output-type",
            "registry-field",
            "witness-field",
        }
        or len(rule.pattern) > MAX_PATTERN_BYTES
    ):
        message = f"unsupported or oversized semantic rule: {rule.logical_id}"
        raise CorpusError(message)
    value = field_value(payload(source), rule.selector)
    if (
        not isinstance(value, str)
        or len(value) > MAX_SOURCE_CHARACTERS
        or (rule.algorithm == "direct-output-type" and not _direct_output(source))
    ):
        return None
    if not _interpretation_matches(rule, source):
        return None
    if (
        isinstance(source, RegistryEntry)
        and rule.algorithm == "registry-field"
        and rule.selector != "/kind"
        and not any(
            item.field.endswith(rule.selector) and item.digest == digest(value)
            for item in source.evidence
        )
    ):
        # Added registry facets require their own exact observed source field.
        # A normalized adapter label without that evidence remains unresolved.
        return None
    if rule.algorithm == "document-sentence":
        # A summary match is insufficient when the retained document adds a
        # condition or exception. Richer clause rules must bind those explicitly.
        paragraph = value.split("\n\n", 1)[0]
        if _QUALIFIERS.search(value if rule.version != "1" else paragraph):
            return None
        value = paragraph
    matched = _bounded_match(rule, value)
    return value if matched else None


def _bounded_match(rule: Rule, value: str) -> bool:
    match = re.fullmatch if rule.algorithm == "document-template" else re.search
    try:
        return match(rule.pattern, value, timeout=MAX_MATCH_SECONDS) is not None
    except TimeoutError as error:
        message = f"semantic template exceeded its execution budget: {rule.logical_id}"
        raise BudgetExceededError(message) from error


def consequence(rule: Rule, source: Record, operation: Operation) -> Assertion | None:
    """Construct the exact consequence of one supported rule application.

    Returns:
        A narrow assertion candidate with all model qualifiers retained.

    """
    if source.profile != operation.profile or matching_text(rule, source) is None:
        return None
    operation_revision = revision_of(operation)
    if isinstance(source, (Passage, TypeUse)):
        if source.owner != operation_revision:
            return None
    elif isinstance(source, (RegistryEntry, WitnessObservation)):
        if source.operation != operation_revision:
            return None
    elif source != operation:
        return None
    support = (
        select(source, rule.selector, "premise"),
        select(operation, "/profile", "context"),
    )
    if isinstance(source, TypeUse):
        support = (
            *support,
            *(
                select(source, f"/{field}", "nominal-role")
                for field in ("role", "direct", "resolution", "nominal_scope")
            ),
        )
    if isinstance(source, WitnessObservation):
        support = (
            *support,
            *(
                select(source, f"/{field}", "finite-observation")
                for field in ("value", "run", "scope")
            ),
        )
    value = (
        source.value
        if isinstance(source, WitnessObservation)
        else Value(kind=ValueKind.TEXT, text=source.nominal)
        if isinstance(source, TypeUse)
        else Value(kind=ValueKind.TEXT, text=str(field_value(payload(source), rule.selector)))
        if isinstance(source, RegistryEntry)
        else rule.value
    )
    key = digest([rule.logical_id, operation.logical_id, rule.predicate, revision_of(source)])
    return Assertion(
        logical_id=f"assertion:{key}",
        profile=operation.profile,
        subject=operation_revision,
        predicate=rule.predicate,
        value=value,
        condition=rule.condition,
        quantifier=rule.quantifier,
        domain=rule.domain,
        phase=rule.phase,
        interpretation=rule.interpretation,
        state=State.SUPPORTED,
        support=support,
        rule=revision_of(rule),
        scope=source.scope if isinstance(source, WitnessObservation) else "",
    )


def derive(reader: CorpusReader) -> Iterator[tuple[Assertion, Proof]]:
    """Derive finite operation consequences without fabricating interpretation reviews.

    Yields:
        Candidate assertions and reproducible certificates, still subject to qualification.

    """
    from library_guides.semantics.relational import candidates

    for rule, source, operation in candidates(reader):
        assertion = consequence(rule, source, operation)
        if assertion is not None:
            yield (
                assertion,
                Proof(
                    logical_id=f"proof:{revision_of(assertion)}",
                    profile=assertion.profile,
                    conclusion=revision_of(assertion),
                    rule=revision_of(rule),
                    premises=assertion.support,
                    read_set=(*assertion.support, select(rule, "/pattern", "model")),
                    scopes=(assertion.scope,) if assertion.scope else (),
                    steps=(rule.algorithm, "contextual-owner", "exact-consequence"),
                    checker=CHECKER,
                ),
            )
