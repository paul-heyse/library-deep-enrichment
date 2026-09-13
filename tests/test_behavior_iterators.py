"""Independent builtin iterator lifecycle controls, including mutation and exhaustion."""

from library_deep_enrichment.analyses.behavior import iterators, regions
from library_deep_enrichment.analyses.behavior.contracts import Term
from library_deep_enrichment.analyses.behavior.state import State
from library_deep_enrichment.analyses.behavior.values import Values


def test_exhausted_iterator_stays_exhausted_after_source_growth() -> None:
    """A completed list iterator never revives, even if the original list later grows."""
    concrete: list[int] = []
    ordinary = iter(concrete)
    sentinel = object()
    assert next(ordinary, sentinel) is sentinel
    concrete.append(1)
    assert next(ordinary, sentinel) is sentinel

    values, state = Values(200), State()
    source = regions.allocate(values, state, Term(op="list"), "source")
    iterator = iterators.create(values, state, source, "iter")
    assert iterator is not None
    first = iterators.advance(values, state, iterator, "next")
    assert first is not None
    assert values.terms[first].value == "StopIteration"
    element = values.add(Term(op="literal", value="1", ty="python:int"))
    regions.append(values, state, (source, element), "append")
    second = iterators.advance(values, state, iterator, "next-again")
    assert second is not None
    assert values.terms[second].value == "StopIteration"
    assert state.flow == "error"


def test_live_iterator_observes_source_growth_before_exhaustion() -> None:
    """A private list iterator reads current contents without snapshotting its input."""
    concrete = [1]
    ordinary = iter(concrete)
    assert next(ordinary) == 1
    concrete.append(2)
    expected = next(ordinary)

    values, state = Values(200), State()
    one = values.add(Term(op="literal", value="1", ty="python:int"))
    two = values.add(Term(op="literal", value="2", ty="python:int"))
    source = regions.allocate(values, state, Term(op="list", args=(one,)), "source")
    iterator = iterators.create(values, state, source, "iter")
    assert iterator is not None
    assert iterators.advance(values, state, iterator, "first") == one
    regions.append(values, state, (source, two), "append")
    result = iterators.advance(values, state, iterator, "second")
    assert result is not None
    assert values.terms[result].value == str(expected)


def test_escaped_iterator_does_not_keep_a_closed_cursor_guarantee() -> None:
    """An unknown caller can consume an exposed iterator or change reachable sequence state."""
    values, state = Values(200), State()
    source = regions.allocate(values, state, Term(op="list"), "source")
    iterator = iterators.create(values, state, source, "iter")
    assert iterator is not None
    regions.escape(values, state, (iterator,))
    regions.havoc(values, state, "external")
    assert iterators.advance(values, state, iterator, "next") is None
    assert state.regions[source].escaped
