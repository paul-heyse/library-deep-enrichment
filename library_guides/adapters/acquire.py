"""Bounded HTTP acquisition with a cache and an explicit result for every input.

An acquisition either produces bytes with a digest, or records why it did not.
A fetch that returns a partial listing stays partial; nothing here converts a
failure into an empty success.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import TYPE_CHECKING, Final

from attrs import field, frozen

from library_guides.collection import confined
from library_guides.store.digests import digest_bytes
from library_guides.store.staging import write_atomic

if TYPE_CHECKING:
    from pathlib import Path

__all__ = ["USER_AGENT", "AcquisitionResult", "fetch_cached"]

USER_AGENT: Final = "smartref-library-guides/0.1"
_TIMEOUT_SECONDS: Final = 30
_MAX_BYTES: Final = 128 * 1024 * 1024


@frozen(kw_only=True)
class AcquisitionResult:
    """What one acquisition attempt produced."""

    locator: str = field()
    outcome: str = field()
    payload: bytes | None = field(default=None, repr=False)
    content_digest: str | None = field(default=None)
    detail: str | None = field(default=None)

    @property
    def succeeded(self) -> bool:
        """Whether usable bytes are available.

        Returns:
            ``True`` when the attempt produced a payload.

        """
        return self.payload is not None


def fetch_cached(
    url: str, *, cache_root: Path, cache_name: str, refresh: bool = False
) -> AcquisitionResult:
    """Return bytes for ``url``, reusing a cached copy when one exists.

    The cache is keyed by an explicit name rather than by URL hash so a human
    can see what was downloaded.

    Args:
        url: Absolute URL to fetch.
        cache_root: Directory holding cached payloads.
        cache_name: File name inside the cache.
        refresh: Fetch again even when a URL-bound digest verifies cached bytes.

    Returns:
        The acquisition result.

    """
    cached = confined(cache_root, cache_name)
    metadata_path = cached.with_name(cached.name + ".receipt.json")
    if not refresh and cached.is_file() and metadata_path.is_file():
        payload = cached.read_bytes()
        try:
            metadata = json.loads(metadata_path.read_bytes())
        except ValueError, OSError:
            metadata = {}
        if (
            isinstance(metadata, dict)
            and metadata.get("locator") == url
            and metadata.get("digest") == digest_bytes(payload)
        ):
            return AcquisitionResult(
                locator=url,
                outcome="reused_cache",
                payload=payload,
                content_digest=digest_bytes(payload),
            )
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
            payload = response.read(_MAX_BYTES + 1)
    except urllib.error.HTTPError as error:
        return AcquisitionResult(
            locator=url,
            outcome="unavailable",
            detail=f"HTTP {error.code}",
        )
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        return AcquisitionResult(
            locator=url,
            outcome="failed",
            detail=f"{type(error).__name__}: {error}",
        )
    if len(payload) > _MAX_BYTES:
        return AcquisitionResult(
            locator=url, outcome="failed", detail="response exceeds byte budget"
        )
    write_atomic(cached, payload)
    write_atomic(
        metadata_path, json.dumps({"locator": url, "digest": digest_bytes(payload)}).encode()
    )
    return AcquisitionResult(
        locator=url,
        outcome="fetched",
        payload=payload,
        content_digest=digest_bytes(payload),
    )
