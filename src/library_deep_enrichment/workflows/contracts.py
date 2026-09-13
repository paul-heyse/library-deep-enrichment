"""Declared stage dependencies, producer identity, and finite resource budgets."""

from __future__ import annotations

from attrs import frozen

from library_deep_enrichment.corpus.contracts import Record


@frozen(kw_only=True)
class InputFamily:
    """An independent selected population and the logical fields actually consumed."""

    family: str
    fields: tuple[str, ...]


@frozen(kw_only=True)
class StageDefinition(Record):
    """Acyclic stage contract admitted in the same fabric as its execution receipts."""

    inputs: tuple[InputFamily, ...]
    outputs: tuple[str, ...]
    dependencies: tuple[str, ...]
    implementation: str
    max_records: int
    max_bytes: int
    max_seconds: float


@frozen(kw_only=True)
class FamilySelector:
    """Independent membership query, including populations that are currently empty."""

    family: str
    profiles: tuple[str, ...] = ()
    logical_ids: tuple[str, ...] = ()
    prefix: str = ""


@frozen(kw_only=True)
class InputReceipt(Record):
    """Compact exact input membership; the original stage/job wire contracts stay readable."""

    stage: str
    definition: str
    selector: FamilySelector
    fields: tuple[str, ...]
    count: int
    membership: str


@frozen(kw_only=True)
class ExecutionReceipt(Record):
    """Supervisor observations; transport completion is separate from semantic completeness."""

    definition: str
    request: str
    input_manifest: str
    route: str
    elapsed_seconds: float
    peak_sampled_tree_rss_bytes: int
    output_bytes: int
    records: int
    rss_limit_bytes: int
    address_space_limit_bytes: int
