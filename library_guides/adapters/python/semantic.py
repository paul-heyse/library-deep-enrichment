"""Static Python semantics with explicit alias, stub and native gaps."""

from __future__ import annotations

import json
from pathlib import Path

import griffe
from attrs import evolve

from library_guides.knowledge import Binding, Evidence, Knowledge, Parameter, Source
from library_guides.store.digests import canonical_bytes, digest_bytes
from library_guides.store.staging import write_atomic


def _entry(member: griffe.Object | griffe.Alias, path: str) -> dict[str, object]:
    try:
        parameters = getattr(member, "parameters", ())
        signature = [
            {
                "name": parameter.name,
                "type": str(parameter.annotation or ""),
                "kind": parameter.kind.value,
                "default": str(parameter.default) if parameter.default is not None else None,
            }
            for parameter in parameters
        ]
        docstring = member.docstring
        return {
            "path": path,
            "canonical": member.canonical_path,
            "kind": member.kind.value,
            "parameters": signature,
            "returns": str(getattr(member, "returns", None) or ""),
            "docs": docstring.value if docstring else "",
            "file": str(member.filepath),
            "line": member.lineno,
            "end_line": member.endlineno,
            "labels": sorted(member.labels),
            "bases": [str(base) for base in getattr(member, "bases", ())],
            "resolution": "resolved",
        }
    except griffe.AliasResolutionError, griffe.CyclicAliasError, griffe.BuiltinModuleError:
        return {
            "path": path,
            "canonical": path,
            "kind": "alias",
            "parameters": [],
            "returns": "",
            "docs": "",
            "resolution": "unresolved",
        }


def acquire(
    module: str, destination: Path, *, search_paths: tuple[str, ...] = ()
) -> dict[str, object]:
    """Collect public source and stub declarations without importing the package.

    Returns:
        The static declaration document, including unresolved aliases.

    """
    loader = griffe.GriffeLoader(allow_inspection=False, search_paths=search_paths or None)
    loaded = loader.load(module, find_stubs_package=True)
    unresolved, iterations = loader.resolve_aliases(
        implicit=False, external=False, max_iterations=5
    )
    records: dict[str, object] = {}
    visited: set[str] = set()

    def visit(member: griffe.Object | griffe.Alias, path: str, depth: int) -> None:
        maximum_depth = 12
        if depth > maximum_depth:
            return
        entry = _entry(member, path)
        records[path] = entry
        canonical = str(entry["canonical"])
        if entry["resolution"] == "unresolved" or canonical in visited:
            return
        visited.add(canonical)
        if member.kind.value not in {"class", "module"}:
            return
        for name, child in sorted(member.members.items()):
            if not name.startswith("_"):
                visit(child, f"{path}.{name}", depth + 1)

    visit(loaded, module, 0)
    result: dict[str, object] = {
        "adapter": "griffe-static-v2",
        "module": module,
        "records": records,
        "unresolved_aliases": sorted(unresolved),
        "alias_iterations": iterations,
    }
    write_atomic(destination, canonical_bytes(result))
    return result


def extract(path: Path, source: Source, *, package: str, version: str) -> Knowledge:
    """Normalize static or isolated native records with exact record citations.

    Returns:
        The normalized source, binding, relationship and evidence records.

    """
    document = json.loads(path.read_bytes())
    bindings = []
    evidence = []
    for symbol, item in sorted(document["records"].items()):
        escaped = symbol.replace("~", "~0").replace("/", "~1")
        identifier = f"evidence:{source.id}:{symbol}"
        parameters = tuple(Parameter(**parameter) for parameter in item["parameters"])
        documented_parameters, documented_returns = _documented_types(item["docs"])
        parameters = tuple(
            evolve(parameter, documented_type=documented_parameters.get(parameter.name, ""))
            for parameter in parameters
        )
        returns = item["returns"]
        signature = symbol + "(" + ", ".join(f"{p.name}: {p.type or '?'}" for p in parameters) + ")"
        bindings.append(
            Binding(
                id=f"api:{source.profile}:{package}:{symbol}",
                symbol=symbol,
                package=package,
                version=version,
                profile=source.profile,
                language="python",
                kind=item["kind"],
                evidence=(identifier,),
                parameters=parameters,
                returns=returns,
                signature=signature + (f" -> {returns}" if returns else ""),
                documented_returns=documented_returns,
                aliases=(item["canonical"],) if item["canonical"] != symbol else (),
                owner=symbol.rpartition(".")[0],
                resolution=item["resolution"],
                conditions=tuple(item.get("labels", [])),
            )
        )
        evidence.append(
            Evidence(
                id=identifier,
                source=source.id,
                selector=f"json:/records/{escaped}",
                digest=digest_bytes(canonical_bytes(item)),
                subject=symbol,
                kind="api",
            )
        )
        if item["docs"]:
            evidence.append(
                Evidence(
                    id=f"{identifier}:docs",
                    source=source.id,
                    selector=f"json:/records/{escaped}/docs",
                    subject=symbol,
                    digest=digest_bytes(canonical_bytes(item["docs"])),
                    kind="statement",
                )
            )
    return Knowledge(
        schema_version="library-guides.knowledge.v2",
        collection_id=package,
        sources=(source,),
        bindings=tuple(bindings),
        evidence=tuple(evidence),
    )


def _documented_types(text: str) -> tuple[dict[str, str], str]:
    if "\nParameters\n" not in text and "\nReturns\n" not in text:
        return {}, ""
    parameters: dict[str, str] = {}
    returns = ""
    for section in griffe.Docstring(text).parse("numpy"):
        if isinstance(section, griffe.DocstringSectionParameters):
            parameters.update((item.name, str(item.annotation or "")) for item in section.value)
        elif isinstance(section, griffe.DocstringSectionReturns):
            returns = ", ".join(str(item.annotation or "") for item in section.value)
    return parameters, returns
