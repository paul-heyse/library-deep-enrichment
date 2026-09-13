"""Generic registry functionality normalization; acceptance is always separate."""

from __future__ import annotations

import json
from pathlib import Path

from library_guides.knowledge import Binding, Capability, Claim, Evidence, Facet, Knowledge, Source
from library_guides.store.digests import canonical_bytes, digest_bytes


def extract(path: Path, source: Source, *, package: str, version: str) -> Knowledge:
    """Preserve runtime facts as item-cited draft capabilities, not just names.

    Returns:
        Registry bindings, exact evidence and unreviewed functionality descriptions.

    """
    document = json.loads(path.read_bytes())
    records = document.get("records", document)
    prefix = "json:/records/" if "records" in document else "json:/"
    evidence, bindings, claims, capabilities = [], [], [], []
    for name, value in sorted(records.items()):
        suffix = f"{source.profile}:{package}:registry:{name}"
        ref, binding_id, claim_id = (
            f"evidence:{source.id}:{name}",
            f"api:{suffix}",
            f"claim:{suffix}",
        )
        evidence.append(
            Evidence(
                id=ref,
                source=source.id,
                selector=prefix + name.replace("~", "~0").replace("/", "~1"),
                digest=digest_bytes(canonical_bytes(value)),
                subject=name,
                kind="registry",
            )
        )
        attributes = value.get("attributes", {})
        description = value.get("description", "")
        family = "registry:" + value.get("kind", "function")
        bindings.append(
            Binding(
                id=binding_id,
                symbol=name,
                package=package,
                version=version,
                profile=source.profile,
                language="python",
                kind=family,
                evidence=(ref,),
                signature=attributes.get("syntax_example", name),
                conditions=tuple(value.get("conditions", ())),
                families=(family,),
            )
        )
        if description:
            claims.append(
                Claim(
                    id=claim_id,
                    profile=source.profile,
                    statement=description,
                    mechanism="Functionality reported by the live library registry",
                    evidence=(ref,),
                    conditions=tuple(value.get("conditions", ())),
                    exceptions=("Observation applies only to the recorded runtime registry.",),
                )
            )
            facets = tuple(
                Facet(name=key, value=str(item), claims=(claim_id,))
                for key, item in sorted(attributes.items())
            )
            capabilities.append(
                Capability(
                    id=f"cap:{suffix}",
                    title=name,
                    intent=description,
                    profile=source.profile,
                    family=family,
                    bindings=(binding_id,),
                    claims=(claim_id,),
                    facets=facets,
                )
            )
    return Knowledge(
        schema_version="library-guides.knowledge.v2",
        collection_id=source.id,
        sources=(source,),
        evidence=tuple(evidence),
        bindings=tuple(bindings),
        claims=tuple(claims),
        capabilities=tuple(capabilities),
    )
