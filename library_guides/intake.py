"""Manifest-driven source intake with persisted, non-vacuous extraction receipts."""

from __future__ import annotations

import importlib.metadata
import json
import sys
import tempfile
from compression import zstd
from pathlib import Path
from typing import Literal

import yaml
from attrs import evolve, frozen
from cattrs import Converter

from library_guides.adapters.acquire import fetch_cached
from library_guides.adapters.python import semantic as python_api
from library_guides.adapters.rust import semantic as rust_api
from library_guides.collection import CollectionError, confined, save, subjects
from library_guides.knowledge import Evidence, Knowledge, Obligation, Profile, Source
from library_guides.linking import link
from library_guides.processes import execute
from library_guides.store.digests import canonical_bytes, digest_bytes, digest_file
from library_guides.store.staging import write_atomic


@frozen(kw_only=True)
class IntakeEntry:
    """An explicit acquisition job for one package and applicability profile."""

    id: str
    adapter: Literal["rustdoc", "python_static", "python_native", "registry", "markdown"]
    package: str
    version: str
    profile: str
    locator: str
    attribution: str
    input: str = ""
    helper: str = ""
    python: str = ""
    module: str = ""
    acquisition: str = "local-import"
    search_paths: tuple[str, ...] = ()
    url: str = ""
    cache: str = ""
    command: tuple[str, ...] = ()


def _acquire(entry: IntakeEntry, directory: Path) -> bytes:
    adapter = entry.adapter
    if adapter == "python_static":
        _verify_static_version(entry)
        path = directory / "python.json"
        python_api.acquire(entry.module, path, search_paths=tuple(entry.search_paths))
        return path.read_bytes()
    if adapter == "python_native":
        worker = Path(python_api.__file__).with_name("native_worker.py")
        result = execute(
            (entry.python, "-I", str(worker), entry.module),
            cwd=directory,
            max_bytes=50_000_000,
            timeout=180,
        )
        if result.returncode:
            message = result.stderr.decode(errors="replace")
            raise CollectionError(message)
        if json.loads(result.stdout)["version"] != entry.version:
            message = f"installed distribution version mismatch: {entry.id}"
            raise CollectionError(message)
        return result.stdout
    payload = _read_input(entry, directory)
    if adapter == "rustdoc":
        if entry.input.endswith(".zst") or payload.startswith(b"\x28\xb5\x2f\xfd"):
            payload = zstd.decompress(payload)
        path = directory / "rustdoc.json"
        path.write_bytes(payload)
        result = execute(
            (entry.helper, str(path)), cwd=directory, max_bytes=150_000_000, timeout=180
        )
        if result.returncode:
            message = result.stderr.decode(errors="replace")
            raise CollectionError(message)
        document = json.loads(result.stdout)
        if document.get("crate_version") != entry.version:
            message = f"crate version mismatch: {entry.id}"
            raise CollectionError(message)
        return result.stdout
    if adapter in {"registry", "markdown"}:
        return payload
    message = f"unknown intake adapter: {adapter}"
    raise CollectionError(message)


def _verify_static_version(entry: IntakeEntry) -> None:
    distributions = importlib.metadata.distributions(path=list(entry.search_paths) or sys.path)
    versions = {
        distribution.metadata["Name"].lower().replace("_", "-"): distribution.version
        for distribution in distributions
    }
    if versions.get(entry.package.lower().replace("_", "-")) != entry.version:
        message = f"static distribution version mismatch: {entry.id}"
        raise CollectionError(message)


def _read_input(entry: IntakeEntry, directory: Path) -> bytes:
    if entry.command:
        result = execute(entry.command, cwd=directory, timeout=180, max_bytes=50_000_000)
        if result.returncode:
            message = (
                f"acquisition command failed: {entry.id}: {result.stderr.decode(errors='replace')}"
            )
            raise CollectionError(message)
        payload = result.stdout
        if entry.adapter == "registry" and json.loads(payload).get("version") != entry.version:
            message = f"registry distribution version mismatch: {entry.id}"
            raise CollectionError(message)
    elif entry.url:
        acquired = fetch_cached(
            entry.url,
            cache_root=Path(entry.cache) if entry.cache else directory,
            cache_name=entry.id + ".source",
        )
        if acquired.payload is None:
            message = f"acquisition failed: {entry.id}: {acquired.detail}"
            raise CollectionError(message)
        payload = acquired.payload
    else:
        payload = Path(entry.input).read_bytes()
    return payload


def _normalize(entry: IntakeEntry, source: Source, path: Path) -> Knowledge:
    adapter = entry.adapter
    if adapter == "rustdoc":
        return rust_api.extract(path, source, package=entry.package)
    if adapter in {"python_static", "python_native"}:
        return python_api.extract(path, source, package=entry.package, version=entry.version)
    if adapter == "registry":
        from library_guides.adapters import registry

        return registry.extract(path, source, package=entry.package, version=entry.version)
    from library_guides.adapters.docs.markdown_sections import index_markdown

    sections = index_markdown(path.read_text(encoding="utf-8"), document_path=source.path)
    evidence = tuple(
        Evidence(
            id=f"evidence:{source.id}:{section.section_id}",
            source=source.id,
            selector=f"bytes:{section.byte_start}:{section.byte_end}",
            subject=section.heading_text,
            kind="statement",
            digest=digest_bytes(path.read_bytes()[section.byte_start : section.byte_end]),
        )
        for section in sections.sections
    )
    return Knowledge(
        schema_version="library-guides.knowledge.v2",
        collection_id=source.id,
        sources=(source,),
        evidence=evidence,
    )


def ingest(manifest_path: Path, destination: Path) -> dict[str, object]:
    """Build an evidence-only draft; any failed input leaves the prior authority intact.

    Returns:
        Per-input outcomes, actual output digests and the extraction state.

    Raises:
        CollectionError: If the manifest does not enumerate any source inputs.

    """
    configuration = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    converter = Converter(forbid_extra_keys=True)
    entries = tuple(
        _resolve_entry(converter.structure(item, IntakeEntry), manifest_path.resolve().parent)
        for item in configuration.get("sources", [])
    )
    if not entries:
        message = "source manifest must enumerate at least one input"
        raise CollectionError(message)
    processed: list[dict[str, object]] = []
    failures: list[dict[str, object]] = []
    receipt: dict[str, object] = {
        "stage": "intake-v2",
        "manifest": digest_file(manifest_path),
        "enumerated": len(entries),
        "processed": processed,
        "failures": failures,
    }
    collection = Knowledge(
        schema_version="library-guides.knowledge.v2",
        collection_id=configuration["collection_id"],
        profiles=tuple(
            converter.structure(item, Profile) for item in configuration.get("profiles", [])
        ),
    )
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="intake-") as temporary:
        work = Path(temporary)
        for entry in entries:
            try:
                fragment = _ingest_one(entry, destination, work)
            except (CollectionError, OSError, ValueError, TypeError, KeyError) as error:
                failures.append({"source": entry.id, "reason": str(error)})
                continue
            collection = evolve(
                collection,
                sources=collection.sources + fragment.sources,
                evidence=collection.evidence + fragment.evidence,
                bindings=collection.bindings + fragment.bindings,
                relations=collection.relations + fragment.relations,
                claims=collection.claims + fragment.claims,
                capabilities=collection.capabilities + fragment.capabilities,
            )
            processed.append(
                {
                    "source": entry.id,
                    "digest": fragment.sources[0].digest,
                    "bindings": len(fragment.bindings),
                    "evidence": len(fragment.evidence),
                }
            )
    try:
        subjects(collection)
    except CollectionError as error:
        failures.append({"source": "collection", "reason": str(error)})
    receipt["state"] = "partial" if receipt["failures"] else "complete"
    if not receipt["failures"]:
        obligations = tuple(
            Obligation(
                id=f"surface:{binding.id}",
                axis="surface",
                profile=binding.profile,
                target=binding.id,
                disposition="reference_only",
                reason="Extracted public inventory; semantic depth tracked separately",
            )
            for binding in collection.bindings
        )
        collection = link(evolve(collection, obligations=obligations))
        save(destination, collection)
        receipt["output_digest"] = digest_file(destination / "knowledge.yaml")
    write_atomic(destination / "intake-receipt.json", canonical_bytes(receipt))
    return receipt


def _resolve_entry(entry: IntakeEntry, directory: Path) -> IntakeEntry:
    def expand(value: str) -> str:
        return (
            value.replace("{python}", sys.executable)
            .replace("{manifest}", str(directory))
            .replace("{cache}", str(Path.home() / ".cache" / "library-guides" / "acquired"))
        )

    return evolve(
        entry,
        input=expand(entry.input),
        helper=expand(entry.helper),
        python=expand(entry.python or "{python}"),
        cache=expand(entry.cache),
        command=tuple(expand(item) for item in entry.command),
        search_paths=tuple(expand(item) for item in entry.search_paths),
    )


def _ingest_one(entry: IntakeEntry, destination: Path, work: Path) -> Knowledge:
    payload = _acquire(entry, work)
    digest = digest_bytes(payload)
    relative = f"sources/{digest}.json" if entry.adapter != "markdown" else f"sources/{digest}.md"
    path = confined(destination, relative)
    write_atomic(path, payload)
    origin: dict[
        str, Literal["compiler_api", "static_api", "runtime_api", "registry", "documentation"]
    ] = {
        "rustdoc": "compiler_api",
        "python_static": "static_api",
        "python_native": "runtime_api",
        "registry": "registry",
        "markdown": "documentation",
    }
    source = Source(
        id=entry.id,
        path=relative,
        digest=digest,
        locator=entry.locator,
        profile=entry.profile,
        origin=origin[entry.adapter],
        attribution=entry.attribution,
        acquisition=entry.acquisition,
    )
    return _normalize(entry, source, path)
