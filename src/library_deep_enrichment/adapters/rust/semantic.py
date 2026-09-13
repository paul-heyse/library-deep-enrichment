"""Normalize the complete typed rustdoc item index without discarding its graph."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

from library_deep_enrichment.adapters.rust.shapes import RustBody, RustDocument, RustItem, RustSignature
from library_deep_enrichment.knowledge import Binding, Evidence, Knowledge, Parameter, Relation, Source
from library_deep_enrichment.store.digests import canonical_bytes, digest_bytes


def _references(value: object) -> Iterator[str]:
    if isinstance(value, dict):
        if "id" in value and "path" in value:
            yield str(value["id"])
        for child in value.values():
            yield from _references(child)
    elif isinstance(value, list):
        for child in value:
            yield from _references(child)


def type_text(value: object, names: dict[str, str]) -> str:
    """Render common type constructors, retaining unknown structure losslessly.

    Returns:
        A readable type expression or the preserved compiler structure.

    """
    if not isinstance(value, dict):
        return "()" if value is None else str(value)
    for kind, inner in value.items():
        if kind in {"generic", "primitive"}:
            return str(inner)
        if kind == "resolved_path":
            name = names.get(str(inner["id"]), inner["path"])
            args = inner.get("args") or {}
            values = args.get("angle_bracketed", {}).get("args", [])
            rendered = [type_text(arg.get("type", arg), names) for arg in values]
            return name + ("<" + ", ".join(rendered) + ">" if rendered else "")
        if kind == "borrowed_ref":
            lifetime = (inner.get("lifetime") or "") + " " if inner.get("lifetime") else ""
            mutable = "mut " if inner.get("is_mutable") else ""
            return "&" + lifetime + mutable + type_text(inner["type"], names)
        if kind in {"tuple", "slice"}:
            return (
                "(" + ", ".join(type_text(item, names) for item in inner) + ")"
                if kind == "tuple"
                else "[" + type_text(inner, names) + "]"
            )
    return canonical_bytes(value).decode()


class RustIndex:
    """Resolve public paths, associated methods, types, impls and doc links."""

    def __init__(self, document: RustDocument, source: Source, package: str) -> None:
        """Retain all raw compiler structure in the source artifact."""
        self.document = document
        self.source = source
        self.package = package
        self.items = document["index"]
        self.paths = document["paths"]
        self.names = {key: "::".join(item["path"]) for key, item in self.paths.items()}
        self.owners: dict[str, str] = {}
        self.aliases: dict[str, list[str]] = {}
        self.impl_traits: dict[str, str] = {}
        self.symbol_kinds: dict[str, list[str]] = {}

    def resolve(self) -> None:
        """Walk module and associated-item ownership before extracting bindings."""
        root = str(self.document["root"])
        self.names[root] = self.package.replace("-", "_")
        visited: set[str] = set()
        self._children(root, visited)
        # Public paths can expose a trait/type through a private defining module.
        # Its associated items are not themselves present in rustdoc's paths map.
        for key in tuple(self.names):
            if key in self.items and self.items[key]["crate_id"] == 0:
                self._children(key, visited)
        self._resolve_impls()
        for key, item in self.items.items():
            imported = item["inner"].get("use")
            if imported and not imported["is_glob"] and imported.get("id") is not None:
                target = str(imported["id"])
                if key in self.names:
                    self.aliases.setdefault(target, []).append(self.names[key])
        self._inherit_aliases()
        for key, item in self.items.items():
            if key in self.names:
                self.symbol_kinds.setdefault(self.names[key], []).append(next(iter(item["inner"])))

    def _inherit_aliases(self) -> None:
        owner_aliases = {
            self.names[key]: values for key, values in self.aliases.items() if key in self.names
        }
        for key, owner in self.owners.items():
            if owner in owner_aliases:
                leaf = self.items[key].get("name")
                if leaf:
                    self.aliases.setdefault(key, []).extend(
                        alias + "::" + leaf for alias in owner_aliases[owner]
                    )

    def _resolve_impls(self) -> None:
        for key, item in self.items.items():
            implementation = item["inner"].get("impl")
            if implementation is None:
                continue
            owner = type_text(implementation["for"], self.names)
            trait = implementation.get("trait")
            if trait:
                trait_name = type_text({"resolved_path": trait}, self.names)
                self.impl_traits[key] = trait_name
                owner = f"<{owner} as {trait_name}>"
            for child in implementation["items"]:
                child_key = str(child)
                if child_key not in self.items:
                    continue
                child_name = self.items[child_key].get("name")
                if child_name:
                    qualified = f"{owner}::{child_name}"
                    if child_key in self.owners:
                        self.aliases.setdefault(child_key, []).append(qualified)
                    else:
                        self.names[child_key] = qualified
                        self.owners[child_key] = owner

    def _children(self, key: str, visited: set[str]) -> None:
        if key in visited or key not in self.items:
            return
        visited.add(key)
        item = self.items[key]
        inner = next(iter(item["inner"].values()))
        if not isinstance(inner, dict):
            return
        children = inner.get("items", inner.get("variants", []))
        if "kind" in inner and isinstance(inner["kind"], dict):
            shape = inner["kind"]
            children = [
                *children,
                *shape.get("plain", {}).get("fields", []),
                *(child for child in shape.get("tuple", []) if child is not None),
            ]
        fields = inner.get("fields", [])
        if isinstance(fields, list):
            children = [*children, *fields]
        for child in children:
            child_key = str(child)
            child_item = self.items.get(child_key)
            if child_item is None:
                continue
            child_name = child_item.get("name") or child_item["inner"].get("use", {}).get("name")
            if not child_name:
                continue
            if child_item.get("visibility") not in {"public", "default"}:
                continue
            self.names.setdefault(child_key, self.names[key] + "::" + child_name)
            self.owners[child_key] = self.names[key]
            self._children(child_key, visited)

    def binding(self, key: str, item: RustItem) -> Binding:
        """Convert one callable or type, retaining the actual signature components.

        Returns:
            A binding carrying callable parameters, return type and generics.

        """
        kind = next(iter(item["inner"]))
        content = item["inner"][kind]
        function: RustBody = content if kind == "function" else {}
        signature: RustSignature = function.get("sig", {"inputs": [], "output": None})
        parameters = tuple(
            Parameter(name=name, type=type_text(typ, self.names))
            for name, typ in signature.get("inputs", [])
        )
        returns = type_text(signature.get("output"), self.names) if function else ""
        generics = (
            canonical_bytes(content.get("generics", {})).decode()
            if isinstance(content, dict)
            else ""
        )
        symbol = self.names[key]
        header = function.get("header", {})
        prefix = "async " if header.get("is_async") else ""
        readable = (
            (
                f"{prefix}fn {symbol}("
                + ", ".join(f"{p.name}: {p.type}" for p in parameters)
                + f") -> {returns}"
            )
            if function
            else self._declaration(kind, symbol, content)
        )
        return Binding(
            id=self.identifier(symbol, kind),
            symbol=symbol,
            package=self.package,
            version=self.document.get("crate_version") or "unknown",
            profile=self.source.profile,
            language="rust",
            kind=kind,
            evidence=(self.evidence_id(key, "api"),),
            parameters=parameters,
            returns=returns,
            generics=generics,
            signature=readable,
            aliases=tuple(sorted(set(self.aliases.get(key, [])))),
            owner=self.owners.get(key, ""),
            conditions=tuple(canonical_bytes(attr).decode() for attr in item.get("attrs", [])),
        )

    def _declaration(self, kind: str, symbol: str, content: object) -> str:
        if kind == "struct_field":
            return f"{symbol}: {type_text(content, self.names)}"
        if isinstance(content, dict) and content.get("type") is not None:
            return f"{kind} {symbol} = {type_text(content['type'], self.names)}"
        return f"{kind} {symbol}"

    def identifier(self, symbol: str, kind: str = "") -> str:
        """Return a version/profile-scoped durable binding identity.

        Returns:
            A profile, package, kind and public-path identity.

        """
        kinds = self.symbol_kinds.get(symbol, [])
        if not kind:
            kind = next(
                (item for item in kinds if item in {"struct", "enum", "trait", "type_alias"}),
                kinds[0] if kinds else "external",
            )
        return f"api:{self.source.profile}:{self.package}:{kind}:{symbol}"

    def evidence_id(self, key: str, kind: str) -> str:
        """Return a snapshot-local selector identity distinct from public symbols.

        Returns:
            An artifact-local identity for one concrete source selection.

        """
        return f"evidence:{self.source.id}:{key}:{kind}"

    def evidence_for(self, key: str, item: RustItem) -> list[Evidence]:
        """Produce separate signature and behavioral-documentation selections.

        Returns:
            Separate API and documentation evidence selections.

        """
        result = [
            Evidence(
                id=self.evidence_id(key, "api"),
                source=self.source.id,
                selector=f"json:/index/{key}",
                digest=digest_bytes(canonical_bytes(item)),
                subject=self.names[key],
                kind="api",
            )
        ]
        if item.get("docs"):
            result.append(
                Evidence(
                    id=self.evidence_id(key, "docs"),
                    source=self.source.id,
                    selector=f"json:/index/{key}/docs",
                    subject=self.names[key],
                    digest=digest_bytes(canonical_bytes(item["docs"])),
                    kind="statement",
                )
            )
        return result

    def relations_for(self, key: str, item: RustItem) -> list[Relation]:
        """Expose callable type flow and compiler-resolved intra-doc references.

        Returns:
            Typed input, output and intra-document relationships.

        """
        content = next(iter(item["inner"].values()))
        function = item["inner"].get("function", {}).get("sig", {})
        groups = {
            "consumes": function.get("inputs", []),
            "produces": function.get("output"),
            "type_reference": content if "function" not in item["inner"] else None,
            "constrained_by": content.get("generics") if isinstance(content, dict) else None,
        }
        edges = [(kind, target) for kind, value in groups.items() for target in _references(value)]
        edges.extend(("intradoc_link", str(target)) for target in item.get("links", {}).values())
        result = []
        for kind, target in sorted(set(edges)):
            name = self.names.get(target)
            local = target in self.items and name is not None
            result.append(
                Relation(
                    source=self.identifier(self.names[key], next(iter(item["inner"]))),
                    target=self.identifier(name) if local else name or f"unresolved:{target}",
                    kind=kind,
                    evidence=self.evidence_id(key, "api"),
                    source_symbol=self.names[key],
                    target_symbol=name or "",
                    resolution="resolved" if local else "external" if name else "unresolved",
                )
            )
        owner = self.owners.get(key)
        if owner:
            result.append(
                Relation(
                    source=self.identifier(self.names[key], next(iter(item["inner"]))),
                    target=self.identifier(owner),
                    kind="member_of",
                    evidence=self.evidence_id(key, "api"),
                    source_symbol=self.names[key],
                    target_symbol=owner,
                    resolution="external",
                )
            )
        return result

    def impl_relations(self) -> tuple[list[Evidence], list[Relation]]:
        """Retain trait implementation edges and their exact compiler selections.

        Returns:
            Exact implementation evidence and directed trait relationships.

        """
        evidence: list[Evidence] = []
        relations: list[Relation] = []
        for key, item in self.items.items():
            implementation = item["inner"].get("impl")
            if not implementation or not implementation.get("trait"):
                continue
            trait = implementation["trait"]
            owner_ids = tuple(_references(implementation["for"]))
            if trait is None or not owner_ids:
                continue
            owner = self.names.get(owner_ids[0])
            target = self.names.get(str(trait["id"]))
            if owner is None or target is None:
                continue
            ref = self.evidence_id(key, "impl")
            evidence.append(
                Evidence(
                    id=ref,
                    source=self.source.id,
                    selector=f"json:/index/{key}",
                    subject=f"{owner} implements {target}",
                    kind="api",
                    digest=digest_bytes(canonical_bytes(item)),
                )
            )
            local = str(trait["id"]) in self.items
            relations.append(
                Relation(
                    source=self.identifier(owner),
                    target=self.identifier(target) if local else target,
                    kind="implements",
                    evidence=ref,
                    source_symbol=owner,
                    target_symbol=target,
                    resolution="resolved" if local else "external",
                )
            )
        return evidence, relations


def extract(path: Path, source: Source, *, package: str) -> Knowledge:
    """Extract a helper-validated document, preserving methods absent from paths.

    Returns:
        The normalized source, binding, relationship and evidence records.

    """
    document: RustDocument = json.loads(path.read_bytes())
    index = RustIndex(document, source, package)
    index.resolve()
    bindings = []
    evidence = []
    relations = []
    for key, item in sorted(index.items.items()):
        if item["crate_id"] != 0 or not item.get("name") or key not in index.names:
            continue
        if item["visibility"] not in {"public", "default"} or "use" in item["inner"]:
            continue
        bindings.append(index.binding(key, item))
        evidence.extend(index.evidence_for(key, item))
        relations.extend(index.relations_for(key, item))
    impl_evidence, impl_relations = index.impl_relations()
    evidence.extend(impl_evidence)
    relations.extend(impl_relations)
    return Knowledge(
        schema_version="library-guides.knowledge.v2",
        collection_id=package,
        sources=(source,),
        bindings=tuple(bindings),
        evidence=tuple(evidence),
        relations=tuple(relations),
    )
