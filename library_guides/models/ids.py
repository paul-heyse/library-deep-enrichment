"""Durable identities, separated from snapshot identities.

Capability and principle records carry human-owned identifiers. API identity
carries ecosystem, package, public path, item kind, and owner context. Neither
uses a build-specific identifier: rustdoc item identifiers are opaque and public
paths may move, so renames are reconciled through explicit aliases rather than
inferred from a shared internal identifier.
"""

from __future__ import annotations

import re
from typing import Final

from attrs import field, frozen

from library_guides.models.enums import Ecosystem

__all__ = [
    "ApiIdentity",
    "LibraryId",
    "ProfileId",
    "SurfaceId",
    "authored_id",
    "is_authored_id",
]

_AUTHORED_ID: Final = re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$")


def is_authored_id(value: str) -> bool:
    """Return whether ``value`` is a well-formed human-owned identifier.

    Returns:
        ``True`` when the identifier uses lowercase dotted or dashed segments.

    """
    return bool(_AUTHORED_ID.match(value))


def authored_id(value: str, *, context: str) -> str:
    """Return ``value`` when it is a well-formed human-owned identifier.

    Args:
        value: Candidate identifier.
        context: Where the identifier was declared, used in the error message.

    Returns:
        The validated identifier.

    Raises:
        ValueError: When the identifier is not well formed.

    """
    if not is_authored_id(value):
        message = f"{context}: {value!r} is not a lowercase dotted or dashed identifier"
        raise ValueError(message)
    return value


@frozen(kw_only=True)
class LibraryId:
    """Durable identity of one library within one packaging ecosystem."""

    value: str = field()
    ecosystem: Ecosystem = field()

    @value.validator
    def _check_value(self, _attribute: object, value: str) -> None:
        authored_id(value, context="library id")

    def __str__(self) -> str:
        """Return the identifier text.

        Returns:
            The library identifier.

        """
        return self.value


@frozen(kw_only=True)
class ProfileId:
    """Identity of one coherent resolved environment for a library."""

    value: str = field()
    library: LibraryId = field()

    @value.validator
    def _check_value(self, _attribute: object, value: str) -> None:
        authored_id(value, context="profile id")

    def __str__(self) -> str:
        """Return the identifier text.

        Returns:
            The profile identifier.

        """
        return self.value


@frozen(kw_only=True)
class ApiIdentity:
    """Identity of one public API item.

    ``package`` is the distribution or Cargo package name; ``public_path`` is the
    import or crate path an author must actually write. The two differ routinely
    and are therefore never collapsed.
    """

    ecosystem: Ecosystem = field()
    package: str = field()
    public_path: str = field()
    item_kind: str = field()
    owner_path: str | None = field(default=None)
    aliases: tuple[str, ...] = field(default=())

    def sort_key(self) -> tuple[str, str, str, str, str]:
        """Return a deterministic ordering key.

        Returns:
            Tuple ordering by ecosystem, package, path, owner, and kind.

        """
        return (
            str(self.ecosystem),
            self.package,
            self.public_path,
            self.owner_path or "",
            self.item_kind,
        )


@frozen(kw_only=True)
class SurfaceId:
    """Identity of one non-symbol surface, such as a feature or configuration key."""

    ecosystem: Ecosystem = field()
    package: str = field()
    surface_kind: str = field()
    name: str = field()

    def sort_key(self) -> tuple[str, str, str, str]:
        """Return a deterministic ordering key.

        Returns:
            Tuple ordering by ecosystem, package, surface kind, and name.

        """
        return (str(self.ecosystem), self.package, self.surface_kind, self.name)
