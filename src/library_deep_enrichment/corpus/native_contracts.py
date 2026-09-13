"""Typed native transport observations with portable source and context ownership."""

from attrs import frozen

from library_deep_enrichment.corpus.contracts import ByteRange, Disposition, Record


@frozen(kw_only=True)
class NativeArtifact(Record):
    """A verified worker output; transport completeness is not semantic completeness."""

    external_id: str
    lane: str
    schema: str
    context: str
    input: ByteRange
    header: ByteRange
    receipt: ByteRange
    shards: tuple[ByteRange, ...]
    shard_counts: tuple[int, ...]
    sources: tuple[str, ...]
    record_count: int
    disposition: Disposition
    frontier: tuple[str, ...]


@frozen(kw_only=True)
class NativeFact(Record):
    """One original worker fact with indexed ownership and exact payload selectors."""

    artifact: str
    native_id: str
    kind: str
    symbol: str
    file: str
    owner: str
    original: ByteRange
