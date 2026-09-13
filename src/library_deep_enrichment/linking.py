"""Resolve cross-crate relationships only under matching recorded profiles."""

from __future__ import annotations

from attrs import evolve

from library_deep_enrichment.knowledge import Knowledge


def link(knowledge: Knowledge) -> Knowledge:
    """Resolve exact type identities across source artifacts without suffix guesses.

    Returns:
        A collection whose relationships retain exact, ambiguous and external states.

    """
    sources = {source.id: source for source in knowledge.sources}
    evidence = {item.id: item for item in knowledge.evidence}
    bindings = {item.id: item for item in knowledge.bindings}
    symbols: dict[tuple[str, str], list[str]] = {}
    for binding in knowledge.bindings:
        for symbol in (binding.symbol, *binding.aliases):
            symbols.setdefault((binding.profile, symbol), []).append(binding.id)
    relations = []
    for relation in knowledge.relations:
        profile = sources[evidence[relation.evidence].source].profile
        origin = symbols.get((profile, relation.source_symbol), [])
        destinations = symbols.get((profile, relation.target_symbol), [])
        if relation.kind in {"consumes", "produces", "implements"}:
            destinations = [
                key
                for key in destinations
                if bindings[key].kind
                in {"struct", "enum", "trait", "type_alias", "primitive", "union"}
            ]
        source = origin[0] if len(origin) == 1 else relation.source
        if len(destinations) == 1:
            relations.append(
                evolve(relation, source=source, target=destinations[0], resolution="resolved")
            )
        elif destinations:
            relations.append(evolve(relation, source=source, resolution="ambiguous"))
        else:
            relations.append(evolve(relation, source=source))
    return evolve(knowledge, relations=tuple(relations))
