"""Reusable bounded source-rule scans retaining exact bytes and syntactic certainty."""

from __future__ import annotations

import json
from pathlib import Path

from attrs import frozen

from library_deep_enrichment.collection import CollectionError
from library_deep_enrichment.processes import execute
from library_deep_enrichment.store.digests import digest_bytes


@frozen(kw_only=True)
class Match:
    """An exact syntactic match; it never claims resolved binding semantics."""

    path: str
    selector: str
    digest: str
    source_digest: str
    rule: str
    text: str
    certainty: str = "syntactic"


def ast_scan(root: Path, *, rule: str, pattern: str, language: str) -> tuple[Match, ...]:
    """Run an ast-grep pattern with source-span validation and no shell interpolation.

    Returns:
        Verified syntactic selections for the requested source tree.

    Raises:
        CollectionError: If the scanner fails or its matches disagree with source bytes.

    """
    result = execute(
        ("ast-grep", "run", "--lang", language, "--pattern", pattern, "--json=stream", "."),
        cwd=root,
    )
    if result.returncode not in {0, 1}:
        message = result.stderr.decode(errors="replace")
        raise CollectionError(message)
    matches = []
    for line in result.stdout.splitlines():
        raw = json.loads(line)
        path = (root / raw["file"]).resolve()
        if not path.is_relative_to(root.resolve()):
            message = "scanner returned a file outside its declared source scope"
            raise CollectionError(message)
        payload = path.read_bytes()
        span = raw["range"]["byteOffset"]
        selected = payload[span["start"] : span["end"]]
        if selected.decode() != raw["text"]:
            message = "scanner match changed before source capture"
            raise CollectionError(message)
        matches.append(
            Match(
                path=path.relative_to(root.resolve()).as_posix(),
                selector=f"bytes:{span['start']}:{span['end']}",
                digest=digest_bytes(selected),
                source_digest=digest_bytes(payload),
                rule=rule,
                text=raw["text"],
            )
        )
    return tuple(matches)


def text_scan(root: Path, *, pattern: str) -> tuple[dict[str, object], ...]:
    """Run ripgrep as a separate explicitly textual evidence lane.

    Returns:
        Source-file and match offsets from ripgrep's structured event stream.

    Raises:
        CollectionError: If the scan fails instead of returning a genuine empty result.

    """
    result = execute(("rg", "--json", "--", pattern, "."), cwd=root)
    if result.returncode not in {0, 1}:
        message = result.stderr.decode(errors="replace")
        raise CollectionError(message)
    events = [json.loads(line) for line in result.stdout.splitlines()]
    return tuple(event["data"] for event in events if event["type"] == "match")
