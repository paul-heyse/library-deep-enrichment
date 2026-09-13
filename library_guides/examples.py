"""Execute declared verification jobs and bind receipts to exact inputs."""

from __future__ import annotations

import importlib.metadata
import json
import shutil
import sys
from pathlib import Path

from attrs import asdict

from library_guides.collection import CollectionError, confined
from library_guides.evidence_graph import EvidenceGraph
from library_guides.knowledge import Example, Knowledge
from library_guides.processes import execute
from library_guides.store.digests import canonical_bytes, digest_bytes, digest_file
from library_guides.store.staging import write_atomic


def arguments(example: Example) -> tuple[str, ...]:
    """Expand documented runtime placeholders without invoking a shell.

    Returns:
        The exact argument vector used for execution.

    """
    cache = Path.home() / ".cache" / "library-guides" / "examples"
    cache_placeholder = "{" + "cache" + "}"
    return tuple(
        argument.replace("{python}", sys.executable).replace(cache_placeholder, str(cache))
        for argument in example.argv
    )


def environment(example: Example, *, root: Path | None = None) -> dict[str, object]:
    """Fingerprint the interpreter or executable and declared distributions.

    Returns:
        The exact executable identity and installed distribution versions.

    """
    argv = arguments(example)
    executable = shutil.which(argv[0]) if argv else None
    return {
        "argv": argv,
        "executable": str(Path(executable).resolve()) if executable else None,
        "executable_digest": digest_file(Path(executable)) if executable else None,
        "versions": {name: importlib.metadata.version(name) for name, _ in example.requirements},
        "argument_files": {
            argument: digest_file(path)
            for argument in argv
            if (path := (root or Path()) / argument).is_file()
        },
    }


def run(root: Path, knowledge: Knowledge, example: Example) -> dict[str, object]:
    """Run a behavior check, retaining its environment and semantic input closure.

    Returns:
        The persisted execution receipt or verified reuse disposition.

    Raises:
        CollectionError: If verification or a required build stage fails.

    """
    graph = EvidenceGraph(root, knowledge)
    argv = arguments(example)
    versions = {name: importlib.metadata.version(name) for name, _ in example.requirements}
    if any(versions[name] != expected for name, expected in example.requirements):
        message = f"example environment mismatch: {example.id}: {versions}"
        raise CollectionError(message)
    executable = shutil.which(argv[0]) if argv else None
    if executable is None:
        message = f"verification executable unavailable: {example.id}"
        raise CollectionError(message)
    inputs = {path: digest_file(confined(root, path)) for path in example.inputs}
    claims = {key: graph.fingerprint(key) for key in example.claims}
    result = execute(argv, cwd=root, timeout=example.timeout_seconds)
    receipt: dict[str, object] = {
        "example": asdict(example),
        "input_fingerprint": graph.fingerprint(example.id),
        "versions": versions,
        "inputs": inputs,
        "claims": claims,
        "executable": str(Path(executable).resolve()),
        "executable_digest": digest_file(Path(executable)),
        "returncode": result.returncode,
        "stdout": result.stdout.decode(errors="replace"),
        "stderr": result.stderr.decode(errors="replace"),
        "elapsed_seconds": result.elapsed_seconds,
    }
    write_atomic(
        root / "verification" / f"{digest_bytes(example.id.encode())}.json",
        canonical_bytes(receipt),
    )
    if result.returncode:
        message = f"verification failed: {example.id}\n{receipt['stderr']}"
        raise CollectionError(message)
    return receipt


def verify(root: Path, knowledge: Knowledge) -> None:
    """Require successful receipts bound to every declared verification input.

    Raises:
        CollectionError: If a receipt is absent, failed or for different inputs.

    """
    graph = EvidenceGraph(root, knowledge)
    for example in knowledge.examples:
        path = root / "verification" / f"{digest_bytes(example.id.encode())}.json"
        receipt = json.loads(path.read_bytes()) if path.is_file() else {}
        inputs = {item: digest_file(confined(root, item)) for item in example.inputs}
        claims = {key: graph.fingerprint(key) for key in example.claims}
        if not (
            receipt.get("returncode") == 0
            and receipt.get("input_fingerprint") == graph.fingerprint(example.id)
            and canonical_bytes(receipt.get("example")) == canonical_bytes(asdict(example))
            and receipt.get("inputs") == inputs
            and receipt.get("claims") == claims
            and receipt.get("versions") == dict(example.requirements)
            and receipt.get("executable_digest")
        ):
            message = f"missing, failed or stale verification receipt: {example.id}"
            raise CollectionError(message)
