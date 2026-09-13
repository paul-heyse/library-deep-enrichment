"""Effective context receipts that distinguish observations from unknown settings."""

from __future__ import annotations

from attrs import asdict, evolve

from library_guides.collection import CollectionError
from library_guides.facts.contracts import Purpose, SemanticProfile, Setting
from library_guides.store.digests import canonical_bytes, digest_bytes


def identify(profile: SemanticProfile) -> SemanticProfile:
    """Cover every effective setting and limitation.

    Returns:
        A profile with its content-derived identity.

    """
    body = asdict(evolve(profile, id=""))
    return evolve(profile, id="context:" + digest_bytes(canonical_bytes(body)))


def observed(header: dict[str, object], kind: str, source_digest: str) -> SemanticProfile:
    """Describe only observed context; absent build settings remain unknown.

    Returns:
        A content-addressed profile that cannot certify consumer availability.

    """
    purposes: dict[str, Purpose] = {
        "declarations": "documentation",
        "cargo": "metadata",
        "cargo_messages": "check",
        "types": "python",
        "mir": "mir",
        "mir_execution": "mir",
        "mir_instances": "mir",
        "mir_callables": "mir",
        "mir_lifecycle": "mir",
        "mir_memory": "mir",
    }
    purpose = purposes.get(kind, "source")
    settings = [
        Setting(name=name, value=None, origin="unknown")
        for name in (
            "features",
            "target_cfg",
            "dependencies",
            "panic",
            "overflow_checks",
            "build_script_outputs",
        )
    ]
    settings.extend(
        Setting(name=name, value=canonical_bytes(header[name]).decode(), origin="observed")
        for name in (
            "target",
            "private",
            "format",
            "phase",
            "python_version",
            "platform",
            "environment",
            "sysroot",
            "instance_options",
        )
        if name in header
    )
    if purpose == "documentation":
        settings.append(Setting(name="cfg(doc)", value="true", origin="observed"))
    return identify(
        SemanticProfile(
            id="",
            purpose=purpose,
            package=str(header.get("package", "unknown")),
            version=str(header.get("version") or "unknown"),
            source_digest=source_digest,
            toolchain=str(header.get("compiler", "unknown")),
            target=header["target"] if isinstance(header.get("target"), str) else None,
            settings=tuple(settings),
            limitations=(
                "Input digest identifies acquired evidence; a library source snapshot is separate.",
                "No ordinary consumer-unit availability or complete effects established by this normalization receipt.",
            ),
        )
    )


def verify(profile: SemanticProfile) -> None:
    """Reject changed settings beneath a retained effective-context identity.

    Raises:
        CollectionError: If the profile is not content-addressed or has contradictory settings.

    """
    if identify(profile).id != profile.id or len({item.name for item in profile.settings}) != len(
        profile.settings
    ):
        message = "effective context identity or setting uniqueness is invalid"
        raise CollectionError(message)
    if any((item.value is None) != (item.origin == "unknown") for item in profile.settings):
        message = (
            "unknown context settings must be null, observed/requested settings must have values"
        )
        raise CollectionError(message)
