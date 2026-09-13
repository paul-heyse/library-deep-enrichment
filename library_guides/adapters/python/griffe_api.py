"""Static Python API extraction through Griffe.

Loading is static: ``allow_inspection`` is disabled so importing a package can
never execute its side effects during inventory. That also means dynamically
created or natively defined members can be missing, which is why a registry
probe is a separate evidence origin rather than a fallback inside this adapter.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

import griffe
from attrs import field, frozen

from library_guides.models.enums import Ecosystem, EvidenceOrigin, ResolutionState
from library_guides.models.ids import ApiIdentity
from library_guides.models.records import ApiBinding

if TYPE_CHECKING:
    from collections.abc import Iterator

__all__ = ["PythonApiModel", "load_python_api"]

_MAX_DEPTH: Final = 12


@frozen(kw_only=True)
class PythonApiModel:
    """One statically loaded package surface and what it could not resolve."""

    module: str = field()
    bindings: tuple[ApiBinding, ...] = field()
    unresolved_aliases: tuple[str, ...] = field(default=())
    failed_members: tuple[str, ...] = field(default=())

    def gap_summary(self) -> str:
        """Describe what static loading could not resolve.

        Returns:
            A short human-readable summary.

        """
        return (
            f"{len(self.unresolved_aliases)} unresolved aliases, "
            f"{len(self.failed_members)} members that could not be read"
        )


def _kind_of(obj: object) -> str:
    try:
        kind = getattr(obj, "kind", None)
    except griffe.AliasResolutionError:
        return "alias"
    value = getattr(kind, "value", None)
    return value if isinstance(value, str) else "unknown"


def _canonical_path(member: object, fallback: str) -> str:
    """Return the member's own canonical path, or ``fallback``.

    Returns:
        A dotted path used to deduplicate the traversal.

    """
    try:
        path = getattr(member, "canonical_path", None)
    except griffe.AliasResolutionError:
        return fallback
    return path if isinstance(path, str) and path else fallback


def _walk(
    root: object,
    prefix: str,
    depth: int,
    seen: set[str],
) -> Iterator[tuple[str, object]]:
    """Yield every public member beneath ``root``.

    Re-exports make the member graph cyclic and wide: one class is reachable
    from many modules. Deduplicating by *canonical path* rather than object
    identity is what keeps this bounded, because Griffe hands out a fresh alias
    wrapper on each access.

    Aliases are yielded but never descended into: their target is already
    reachable at its own canonical location, and following them is what turns a
    traversal of a large package into an unbounded one.

    Yields:
        Dotted path and member pairs.

    """
    if depth > _MAX_DEPTH:
        return
    try:
        members = getattr(root, "members", None)
    except griffe.AliasResolutionError:
        return
    if not isinstance(members, dict):
        return
    for name, member in members.items():
        if name.startswith("_"):
            continue
        path = f"{prefix}.{name}"
        canonical = _canonical_path(member, path)
        if canonical in seen:
            continue
        seen.add(canonical)
        yield path, member
        if _kind_of(member) in {"module", "class"}:
            yield from _walk(member, path, depth + 1, seen)


def load_python_api(
    module: str,
    *,
    library_id: str,
    profile_id: str,
    package: str,
) -> PythonApiModel:
    """Return the statically visible public API of one package.

    Args:
        module: Top-level import name to load.
        library_id: Owning library identifier.
        profile_id: Profile the model is evidence for.
        package: Distribution name, which may differ from ``module``.

    Returns:
        The extracted model, including its own gaps.

    """
    # Aliases are not resolved eagerly: one unresolvable re-export would abort
    # the whole load. Each is recorded as a gap instead.
    loaded = griffe.load(module, allow_inspection=False, resolve_aliases=False)
    bindings: list[ApiBinding] = []
    unresolved: list[str] = []
    failed: list[str] = []
    seen: set[str] = set()
    for path, member in _walk(loaded, module, 0, seen):
        kind = _kind_of(member)
        if kind == "alias":
            unresolved.append(path)
        try:
            docstring = getattr(member, "docstring", None)
            summary = ""
            if docstring is not None and isinstance(docstring.value, str):
                summary = docstring.value.strip().splitlines()[0]
        except AttributeError, IndexError, ValueError, griffe.AliasResolutionError:
            failed.append(path)
            summary = ""
        bindings.append(
            ApiBinding(
                library_id=library_id,
                profile_id=profile_id,
                identity=ApiIdentity(
                    ecosystem=Ecosystem.PYTHON,
                    package=package,
                    public_path=path,
                    item_kind=kind,
                ),
                signature=_signature_of(member),
                documentation_refs=(summary,) if summary else (),
                evidence_origin=EvidenceOrigin.STATIC_API,
                resolution_state=(
                    ResolutionState.CANDIDATE if kind == "alias" else ResolutionState.RESOLVED
                ),
            )
        )
    return PythonApiModel(
        module=module,
        bindings=tuple(sorted(bindings, key=_binding_sort_key)),
        unresolved_aliases=tuple(sorted(unresolved)),
        failed_members=tuple(sorted(failed)),
    )


def _binding_sort_key(binding: ApiBinding) -> tuple[str, str, str, str, str]:
    return binding.identity.sort_key()


def _signature_of(member: object) -> str | None:
    try:
        parameters = getattr(member, "parameters", None)
        if parameters is None:
            return None
        names = [str(parameter.name) for parameter in parameters]
    except AttributeError, TypeError, griffe.AliasResolutionError:
        return None
    return f"({', '.join(names)})" if names else "()"
