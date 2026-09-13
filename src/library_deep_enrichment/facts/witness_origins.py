"""Preserve acquisition path-to-byte attribution after witness transport relocation."""

from library_deep_enrichment.collection import CollectionError

MODEL = "library-guides.witness-origins.v1"
MAX_ENTRIES = 100_000


def read(receipt: dict) -> tuple[tuple[str, dict], ...]:
    """Validate optional acquisition attribution without opening any original path.

    Returns:
        Original paths paired with retained file entries; old receipts remain unattributed.

    Raises:
        CollectionError: The version, denominator or byte identities are inconsistent.

    """
    origins = receipt.get("witness_origins")
    if origins is None:
        return ()
    if (
        not isinstance(origins, dict)
        or set(origins) != {"model", "entries"}
        or origins["model"] != MODEL
        or not isinstance(origins["entries"], list)
        or len(origins["entries"]) > MAX_ENTRIES
    ):
        message = "unsupported or malformed witness origin catalog"
        raise CollectionError(message)
    pairs = []
    for entry in origins["entries"]:
        if (
            not isinstance(entry, dict)
            or set(entry) != {"original_path", "retained"}
            or not isinstance(entry["original_path"], str)
            or not entry["original_path"]
            or not isinstance(entry["retained"], dict)
        ):
            message = "malformed witness origin entry"
            raise CollectionError(message)
        pairs.append((entry["original_path"], entry["retained"]))
    if [item for _, item in pairs] != receipt.get("witnesses", []):
        message = "witness origin denominator or retained bytes disagree"
        raise CollectionError(message)
    by_path: dict[str, dict] = {}
    for path, item in pairs:
        if path in by_path and by_path[path] != item:
            message = "ambiguous witness acquisition path"
            raise CollectionError(message)
        by_path[path] = item
    return tuple(pairs)
