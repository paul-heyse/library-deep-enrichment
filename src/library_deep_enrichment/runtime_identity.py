"""Verify pinned model bytes against the retained upstream commit's file inventory."""

from __future__ import annotations

import hashlib
import json
from importlib.resources import files
from typing import TYPE_CHECKING

from library_deep_enrichment.corpus.backend import CorpusError
from library_deep_enrichment.corpus.encoding import digest

if TYPE_CHECKING:
    from pathlib import Path


def model_identity(snapshot: Path) -> dict[str, object]:
    """Hash the actual files; directory names and previous availability receipts are insufficient.

    Returns:
        Exact model and tokenizer content identities and consumed byte/file denominators.

    Raises:
        CorpusError: A snapshot is incomplete, foreign, or differs from pinned upstream bytes.

    """
    manifest = json.loads(
        files("library_deep_enrichment").joinpath("assets/runtime/qwen3-embedding-8b.json").read_bytes()
    )
    expected = manifest["files"]
    actual = {str(path.relative_to(snapshot)) for path in snapshot.rglob("*") if path.is_file()}
    if snapshot.name != manifest["revision"] or actual != set(expected):
        message = "model snapshot differs from the pinned commit's exact file inventory"
        raise CorpusError(message)
    observed: list[tuple[str, int, str]] = []
    for name, metadata in sorted(expected.items()):
        path = snapshot / name
        size = path.stat().st_size
        if size != metadata["size"]:
            message = f"model file size differs from the pinned commit: {name}"
            raise CorpusError(message)
        sha256 = hashlib.sha256()
        git_blob = hashlib.sha1(f"blob {size}\0".encode(), usedforsecurity=False)
        with path.open("rb") as stream:
            while block := stream.read(8 * 1024 * 1024):
                sha256.update(block)
                if "lfs_sha256" not in metadata:
                    git_blob.update(block)
        valid = (
            sha256.hexdigest() == metadata["lfs_sha256"]
            if "lfs_sha256" in metadata
            else git_blob.hexdigest() == metadata["blob_id"]
        )
        if not valid:
            message = f"model content differs from the pinned commit: {name}"
            raise CorpusError(message)
        observed.append((name, size, sha256.hexdigest()))
    tokenizer_names = {"tokenizer.json", "tokenizer_config.json", "vocab.json", "merges.txt"}
    return {
        "repository": manifest["repository"],
        "revision": manifest["revision"],
        "manifest_digest": digest(manifest),
        "model_digest": digest(observed),
        "tokenizer_digest": digest([item for item in observed if item[0] in tokenizer_names]),
        "files": len(observed),
        "bytes": sum(item[1] for item in observed),
    }
