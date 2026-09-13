"""Compact exact selected-head dependencies, including empty query populations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from library_deep_enrichment.corpus.backend import CorpusError
from library_deep_enrichment.corpus.encoding import digest
from library_deep_enrichment.corpus.schemas import revision_of
from library_deep_enrichment.workflows.contracts import (
    ExecutionReceipt,
    FamilySelector,
    InputReceipt,
    StageDefinition,
)
from library_deep_enrichment.workflows.failure_records import FailureReceipt

if TYPE_CHECKING:
    from library_deep_enrichment.corpus.contracts import Member, Record
    from library_deep_enrichment.corpus.store import CorpusReader


def references(record: Record) -> tuple[tuple[str, str], ...]:
    """Return the stage declaration required by a compact input receipt.

    Returns:
        The exact definition revision, or no workflow references.

    """
    if isinstance(record, FailureReceipt):
        return (("stage_definitions", record.definition), ("jobs", record.job))
    return (
        (("stage_definitions", record.definition),)
        if isinstance(record, (InputReceipt, ExecutionReceipt))
        else ()
    )


def matches(selector: FamilySelector, member: Member) -> bool:
    """Test a current or newly admitted head against the independent query.

    Returns:
        Whether the exact logical head belongs to the selected population.

    """
    return (
        member.family == selector.family
        and (not selector.profiles or member.profile in selector.profiles)
        and (not selector.logical_ids or member.logical_id in selector.logical_ids)
        and member.logical_id.startswith(selector.prefix)
    )


def capture(
    reader: CorpusReader,
    definition: StageDefinition,
    selectors: tuple[FamilySelector, ...] = (),
) -> tuple[InputReceipt, ...]:
    """Fingerprint exact membership without loading native bodies or vectors.

    Returns:
        One bounded receipt per declared family, including zero-member populations.

    Raises:
        CorpusError: Selectors are duplicate or refer to an undeclared input family.

    """
    selected = {item.family: item for item in selectors}
    families = {item.family for item in definition.inputs}
    if len(selected) != len(selectors) or selected.keys() - families:
        message = "stage selectors must name distinct declared input families"
        raise CorpusError(message)
    result = []
    for item in definition.inputs:
        selector = selected.get(item.family, FamilySelector(family=item.family))
        members = sorted(
            (member.logical_id, member.profile, member.revision)
            for member in reader.members(item.family)
            if matches(selector, member)
        )
        result.append(
            InputReceipt(
                logical_id=f"stage-input:{definition.logical_id}:{item.family}",
                profile=definition.profile,
                stage=definition.logical_id,
                definition=revision_of(definition),
                selector=selector,
                fields=item.fields,
                count=len(members),
                membership=digest(members),
            )
        )
    return tuple(result)


def validate(reader: CorpusReader, receipt: InputReceipt) -> None:
    """Independently replay the selected membership at the proposed admission boundary.

    Raises:
        CorpusError: A receipt changes its denominator, selector, or owning declaration.

    """
    definition = reader.get("stage_definitions", receipt.definition)
    if not isinstance(definition, StageDefinition) or receipt.stage != definition.logical_id:
        message = "input receipt does not identify its stage definition"
        raise CorpusError(message)
    specification = next(
        (item for item in definition.inputs if item.family == receipt.selector.family), None
    )
    members = sorted(
        (member.logical_id, member.profile, member.revision)
        for member in reader.members(receipt.selector.family)
        if matches(receipt.selector, member)
    )
    identity = (
        f"stage-input:{definition.logical_id}:{receipt.selector.family}",
        definition.profile,
        len(members),
        digest(members),
    )
    if (
        specification is None
        or receipt.fields != specification.fields
        or identity != (receipt.logical_id, receipt.profile, receipt.count, receipt.membership)
    ):
        message = "input receipt differs from its exact selected population"
        raise CorpusError(message)
