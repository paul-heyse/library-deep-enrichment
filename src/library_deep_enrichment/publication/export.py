"""Portable typed Parquet publication with stable application identities."""

from __future__ import annotations

import json
from itertools import batched
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING

import pyarrow as pa
import pyarrow.parquet as pq
from attrs import frozen

from library_deep_enrichment.corpus.admission import Coordinator, WriterIdentity
from library_deep_enrichment.corpus.backend import CorpusError
from library_deep_enrichment.corpus.contracts import Member, Record
from library_deep_enrichment.corpus.encoding import CONVERTER, canonical
from library_deep_enrichment.corpus.manifests import logical_digest, membership_digest
from library_deep_enrichment.corpus.schemas import REGISTRY
from library_deep_enrichment.store.digests import digest_file

if TYPE_CHECKING:
    from library_deep_enrichment.corpus.store import Corpus, CorpusReader


@frozen(kw_only=True)
class PortableFamily:
    """A portable family product verified independently of its local table version."""

    name: str
    digest: str
    rows: int


@frozen(kw_only=True)
class PortableManifest:
    """Portable logical identity and the finite set of typed family products."""

    format: str
    manifest: str
    predecessor: str
    members_digest: str
    count: int
    families: tuple[PortableFamily, ...]
    checker: str = "current"
    checker_implementation: str = "current"


def _export_family(reader: CorpusReader, family: str, directory: Path) -> PortableFamily:
    path = directory / f"{family}.parquet"
    schema = REGISTRY[family].schema
    count = 0
    with pq.ParquetWriter(
        path, schema, compression="zstd", use_compliant_nested_type=False
    ) as writer:
        for batch in batched(reader.rows(family), 1024, strict=False):
            count += len(batch)
            writer.write_table(pa.Table.from_pylist(list(batch), schema=schema))
    return PortableFamily(name=family, digest=digest_file(path), rows=count)


def export_view(reader: CorpusReader, destination: Path) -> PortableManifest:
    """Export an exact selected view, including owned original bytes and assurance.

    Returns:
        The verified portable manifest; physical database versions are excluded.

    Raises:
        CorpusError: The view is empty or the destination already exists.

    """
    if reader.manifest is None or destination.exists():
        message = "export requires an admitted view and a new destination directory"
        raise CorpusError(message)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".library-guide-export-", dir=destination.parent) as temporary:
        staging = Path(temporary) / "bundle"
        staging.mkdir()
        families = tuple(
            _export_family(reader, binding.family, staging) for binding in reader.manifest.bindings
        )
        from library_deep_enrichment.corpus.checker_epochs import fingerprint

        manifest = PortableManifest(
            format="library-guides.portable.v4",
            manifest=reader.manifest_id,
            predecessor=reader.manifest.predecessor,
            members_digest=reader.manifest.members_digest,
            count=reader.manifest.count,
            families=families,
            checker=reader.semantic_checker,
            checker_implementation=fingerprint(reader.semantic_checker),
        )
        (staging / "manifest.json").write_bytes(canonical(CONVERTER.unstructure(manifest)) + b"\n")
        Path(staging).replace(destination)
    return manifest


def _read_family(directory: Path, family: PortableFamily) -> list[Record]:
    if family.name not in REGISTRY:
        message = f"unsupported portable family: {family.name}"
        raise CorpusError(message)
    path = directory / f"{family.name}.parquet"
    codec = REGISTRY[family.name]
    if digest_file(path) != family.digest or not pq.read_schema(path).equals(
        codec.schema, check_metadata=True
    ):
        message = f"portable bytes or schema mismatch: {family.name}"
        raise CorpusError(message)
    records: list[Record] = []
    for batch in pq.ParquetFile(path).iter_batches(batch_size=1024):
        records.extend(codec.decode(row) for row in batch.to_pylist())
    if len(records) != family.rows:
        message = f"portable family count mismatch: {family.name}"
        raise CorpusError(message)
    return records


def import_view(
    corpus: Corpus, directory: Path, *, head: str = "release", historical_checker: str = ""
) -> str:
    """Verify and restore a portable selection into a clean named view.

    Returns:
        The original logical manifest identity, despite different table versions.

    Raises:
        CorpusError: Format, membership, or logical identity verification fails.

    """
    manifest = CONVERTER.structure(
        json.loads((directory / "manifest.json").read_bytes()), PortableManifest
    )
    from library_deep_enrichment.corpus.checker_epochs import check_manifest, fingerprint

    checker = historical_checker or manifest.checker
    check_manifest(manifest.manifest, checker)
    implementation = fingerprint(checker)
    if not historical_checker and implementation != manifest.checker_implementation:
        message = "portable checker implementation is not the retained verifier"
        raise CorpusError(message)
    if manifest.format != "library-guides.portable.v4" or corpus.reader(head).manifest_id:
        message = "portable import requires the supported format and an empty named view"
        raise CorpusError(message)
    names = [item.name for item in manifest.families]
    if len(names) != len(set(names)) or any(item.rows < 0 for item in manifest.families):
        message = "portable families repeat a name or declare a negative denominator"
        raise CorpusError(message)
    if sum(item.rows for item in manifest.families) > corpus.max_rows:
        message = "portable import exceeds the declared corpus row budget"
        raise CorpusError(message)
    records: list[Record] = []
    members: list[Member] = []
    for family in manifest.families:
        decoded = _read_family(directory, family)
        records.extend(decoded)
        codec = REGISTRY[family.name]
        members.extend(
            Member(
                family=family.name,
                logical_id=item.logical_id,
                profile=item.profile,
                revision=str(codec.encode(item)["revision"]),
            )
            for item in decoded
        )
    if len(members) != manifest.count or membership_digest(members) != manifest.members_digest:
        message = "portable membership does not match the retained logical manifest"
        raise CorpusError(message)
    if len({(item.family, item.logical_id, item.profile) for item in members}) != len(members):
        message = "portable selection contains duplicate logical heads"
        raise CorpusError(message)
    if logical_digest(manifest.predecessor, manifest.members_digest) != manifest.manifest:
        message = "portable logical manifest identity is invalid"
        raise CorpusError(message)
    return Coordinator(
        corpus,
        WriterIdentity(principal="verified-portable-import", role="migration"),
        imported_predecessor=manifest.predecessor,
        historical_checker=checker,
    ).commit(
        records,
        expected="",
        head=head,
        replace=True,
    )
