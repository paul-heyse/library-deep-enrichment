"""Shared immutable source chunks fit their actual bounded byte representation."""

from library_deep_enrichment.corpus.cache import MAX_BYTES, RecordCache
from library_deep_enrichment.corpus.contracts import BlobChunk
from library_deep_enrichment.corpus.encoding import bytes_digest
from library_deep_enrichment.corpus.evidence import CHUNK_SIZE


def test_binary_chunks_reuse_without_json_inflation_and_still_evict() -> None:
    """A source shard can reuse many chunks, while the same hard cache bound applies."""
    cache = RecordCache()
    retained = []
    for index in range(12):
        data = bytes([index]) * CHUNK_SIZE
        record = BlobChunk(logical_id=f"chunk-{index}", data=data, digest=bytes_digest(data))
        retained.append(record)
        cache.put(("blob_chunks", record.digest), record)
    assert all(cache.get(("blob_chunks", item.digest)) is item for item in retained)
    before = cache.size
    cache.put(("blob_chunks", retained[0].digest), retained[0])
    assert cache.size == before
    for index in range(12, 20):
        data = bytes([index]) * CHUNK_SIZE
        record = BlobChunk(logical_id=f"chunk-{index}", data=data, digest=bytes_digest(data))
        cache.put(("blob_chunks", record.digest), record)
    assert cache.size <= MAX_BYTES
    assert cache.get(("blob_chunks", retained[1].digest)) is None
