"""Strict owned Ruff node input; no source evaluation or secondary parser is involved."""

from __future__ import annotations

from attrs import frozen

from library_deep_enrichment.analyses.behavior.integrity import require
from library_deep_enrichment.corpus.encoding import CONVERTER


@frozen(kw_only=True)
class Slot:
    """Ordered children with their original structural role."""

    role: str
    nodes: tuple[Node, ...]


@frozen(kw_only=True)
class Node:
    """A producer-owned source node, prior to evaluated execution normalization."""

    kind: str
    start: int
    end: int
    value: str
    fields: tuple[Slot, ...]

    def children(self, role: str) -> tuple[Node, ...]:
        """Select one named child role.

        Returns:
            Ordered nodes, including an explicit empty optional role.

        """
        return next((slot.nodes for slot in self.fields if slot.role == role), ())

    def one(self, role: str) -> Node:
        """Require a single child instead of silently dropping malformed input.

        Returns:
            The unique node in the named role.

        """
        children = self.children(role)
        require("Python execution requires one " + role, condition=len(children) == 1)
        return children[0]

    @property
    def span(self) -> tuple[int, int]:
        """The exact UTF-8 source interval."""
        return self.start, self.end


def read(raw: dict, *, source_size: int, node_limit: int) -> Node:
    """Decode a bounded Ruff projection, rejecting duplicate roles and invalid ranges.

    Returns:
        A typed node tree under an explicit source and allocation bound.

    """
    pending = [(raw, 0)]
    count = 0
    max_depth = 100
    while pending:
        item, depth = pending.pop()
        count += 1
        require(
            "Python execution node budget exceeded",
            condition=count <= node_limit and depth <= max_depth,
        )
        require(
            "Python execution range escaped source",
            condition=0 <= item["start"] <= item["end"] <= source_size,
        )
        roles = [field["role"] for field in item["fields"]]
        require("Python execution repeats a child role", condition=len(roles) == len(set(roles)))
        pending.extend((child, depth + 1) for field in item["fields"] for child in field["nodes"])
    return CONVERTER.structure(raw, Node)


def walk(root: Node, *, descend_functions: bool = True) -> tuple[Node, ...]:
    """Enumerate structural nodes with explicit deferred-owner boundaries.

    Returns:
        A deterministic finite node population.

    """
    result = []
    pending = [root]
    while pending:
        item = pending.pop()
        result.append(item)
        if (
            item is not root
            and item.kind in {"function", "lambda", "class"}
            and not descend_functions
        ):
            continue
        pending.extend(reversed([child for slot in item.fields for child in slot.nodes]))
    return tuple(result)
