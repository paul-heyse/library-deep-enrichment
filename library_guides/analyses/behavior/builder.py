"""Deterministic construction of finite owned execution graphs."""

from __future__ import annotations

from attrs import define, field, frozen

from library_guides.analyses.behavior.contracts import (
    BehaviorProgram,
    Edge,
    Frontier,
    Instruction,
    Language,
    Limits,
    Term,
)
from library_guides.analyses.behavior.integrity import limits_valid
from library_guides.analyses.behavior.projection_budget import bound
from library_guides.corpus.contracts import Selection


@frozen(kw_only=True)
class Origin:
    """Exact contextual coordinates for one source-backed executable owner."""

    request: str
    owner: str
    artifact: str
    context: str
    profile: str
    symbol: str
    language: Language
    support: tuple[Selection, ...] = ()


@define
class GraphBuilder:
    """Intern expressions and preserve operation/edge ordering without executing source."""

    origin: Origin
    model: str
    limits: Limits = field(factory=Limits, kw_only=True)
    phase: str = "invoke"
    terms: list[Term] = field(factory=list)
    instructions: list[Instruction] = field(factory=list)
    edges: list[Edge] = field(factory=list)
    frontier: list[Frontier] = field(factory=list)
    blocks: list[int] = field(factory=lambda: [0])
    current: int = 0
    local_types: dict[str, str] = field(factory=dict)
    _term_ids: dict[Term, int] = field(factory=dict)

    def __attrs_post_init__(self) -> None:
        """Reject invalid independent budgets before allocating executable collections."""
        limits_valid(self.limits)

    def term(
        self, op: str, args: tuple[int, ...] = (), value: str = "", ty: str = "unknown"
    ) -> int:
        """Intern one acyclic expression.

        Returns:
            Its stable body-local index.

        """
        item = Term(op=op, args=args, value=value, ty=ty)
        if item not in self._term_ids:
            bound("terms", len(self.terms) + 1, self.limits.terms)
            self._term_ids[item] = len(self.terms)
            self.terms.append(item)
        return self._term_ids[item]

    def block(self) -> int:
        """Allocate a block even when its body is empty.

        Returns:
            The new block identity.

        """
        result = len(self.blocks)
        bound("blocks", result + 1, self.limits.steps)
        self.blocks.append(result)
        return result

    def emit(
        self,
        op: str,
        *,
        destination: str = "",
        value: int = -1,
        call: tuple[str, tuple[int, ...]] = ("", ()),
        span: tuple[int, int] = (0, 0),
    ) -> int:
        """Retain an evaluated instruction.

        Returns:
            Its unique body point.

        """
        index = len(self.instructions)
        bound("instructions", index + 1, self.limits.steps)
        self.instructions.append(
            Instruction(
                block=self.current,
                index=index,
                op=op,
                destination=destination,
                value=value,
                arguments=call[1],
                target=call[0],
                start=span[0],
                end=span[1],
            )
        )
        return index

    def edge(
        self, target: int, *, condition: int = -1, positive: bool = True, kind: str = "normal"
    ) -> None:
        """Connect the current block under an explicit edge guard."""
        bound("edges", len(self.edges) + 1, self.limits.steps)
        self.edges.append(
            Edge(
                source=self.current,
                target=target,
                kind=kind,
                condition=condition,
                positive=positive,
            )
        )

    def unknown(self, code: str, dimension: str, point: str, detail: str) -> int:
        """Retain an unsupported semantic boundary.

        Returns:
            An expression identifying the unknown value.

        """
        item = Frontier(code=code, dimension=dimension, point=point, detail=detail)
        if item not in self.frontier:
            self.frontier.append(item)
        return self.term("unknown", value=f"{code}:{point}")

    def finish(self, parameters: tuple[str, ...]) -> BehaviorProgram:
        """Freeze a projection whose producer inputs remain explicit.

        Returns:
            The complete body projection, including unsupported boundaries.

        """
        origin = self.origin
        bound("blocks", len(self.blocks), self.limits.steps)
        return BehaviorProgram(
            logical_id=f"behavior-program:{origin.request}:{origin.owner}",
            profile=origin.profile,
            request=origin.request,
            owner=origin.owner,
            artifact=origin.artifact,
            context=origin.context,
            language=origin.language,
            symbol=origin.symbol,
            model=self.model,
            parameters=parameters,
            terms=tuple(self.terms),
            instructions=tuple(self.instructions),
            edges=tuple(self.edges),
            blocks=tuple(self.blocks),
            entry=0,
            frontier=tuple(self.frontier),
            support=origin.support,
            phase=self.phase,
        )
