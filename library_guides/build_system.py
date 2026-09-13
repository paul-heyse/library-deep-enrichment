"""Small doit scheduling layer over deterministic, content-addressed stages."""

from __future__ import annotations

import importlib.metadata
import json
from pathlib import Path

from doit.cmd_base import ModuleTaskLoader
from doit.doit_cmd import DoitMain

from library_guides.collection import CollectionError, confined, load
from library_guides.examples import environment
from library_guides.generations import build, verify
from library_guides.knowledge_v3 import KnowledgeV3
from library_guides.store.digests import canonical_bytes, digest_bytes, digest_file
from library_guides.store.staging import write_atomic


def input_key(root: Path) -> str:
    """Fingerprint source/configuration/code/schema inputs, never just path existence.

    Returns:
        The digest of declared inputs and compiler implementation.

    """
    knowledge = load(root)
    inputs = {"knowledge.yaml": digest_file(root / "knowledge.yaml")}
    inputs["obligations.yaml"] = digest_file(root / "obligations.yaml")
    inputs.update((item.path, digest_file(confined(root, item.path))) for item in knowledge.sources)
    inputs.update(
        (path, digest_file(confined(root, path)))
        for example in knowledge.examples
        for path in example.inputs
    )
    if isinstance(knowledge, KnowledgeV3):
        if knowledge.candidate_universes or knowledge.universe_dependencies:
            inputs["candidate-universes.yaml"] = digest_file(root / "candidate-universes.yaml")
        paths = {entry.path for snapshot in knowledge.source_snapshots for entry in snapshot.files}
        paths.update(
            proof.prior_knowledge.path
            for proof in knowledge.revalidations
            if proof.prior_knowledge is not None
        )
        paths.update(
            entry.path for proof in knowledge.revalidations for entry in proof.prior_inputs
        )
        for artifact in knowledge.fact_artifacts:
            paths.update((artifact.input_path, artifact.header_path, artifact.receipt_path))
            paths.update(shard.path for shard in artifact.shards)
            paths.update(item.path for item in artifact.witnesses)
            if artifact.acquisition_path:
                paths.add(artifact.acquisition_path)
        inputs.update((path, digest_file(confined(root, path))) for path in paths)
    package = Path(__file__).parent
    adapters = {
        path.relative_to(package).as_posix(): digest_file(path)
        for path in sorted(package.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts
    }
    versions = {
        name: importlib.metadata.version(name)
        for example in knowledge.examples
        for name, _ in example.requirements
    }
    executables = {example.id: environment(example, root=root) for example in knowledge.examples}
    return digest_bytes(
        canonical_bytes(
            {
                "inputs": inputs,
                "compiler": adapters,
                "versions": versions,
                "executables": executables,
            }
        )
    )


def plan(root: Path, store: Path) -> dict[str, object]:
    """Return an executable build disposition after verifying cached bytes.

    Returns:
        The required stages or a verified reusable candidate.

    """
    key = input_key(root)
    receipt = store / "build-receipt.json"
    previous: dict[str, object] = json.loads(receipt.read_bytes()) if receipt.is_file() else {}
    reusable = False
    if previous.get("input_key") == key and previous.get("candidate"):
        try:
            reusable = verify(Path(str(previous["candidate"]))) == previous.get("generation")
        except OSError, ValueError, KeyError:
            reusable = False
    return {
        "input_key": key,
        "state": "reused" if reusable else "required",
        "candidate": previous.get("candidate") if reusable else None,
        "stages": ["qualify", "verify-examples", "render", "index", "stage-bundle"],
        "model_calls": 0,
    }


def run(root: Path, store: Path) -> dict[str, object]:
    """Run the build through doit; unchanged inputs make no model or build calls.

    Returns:
        The persisted execution receipt or verified reuse disposition.

    Raises:
        CollectionError: If verification or a required build stage fails.

    """
    proposed = plan(root, store)
    if proposed["state"] == "reused":
        return proposed

    def action() -> None:
        candidate = build(root, store)
        if input_key(candidate) != input_key(root):
            message = "authoring inputs changed during compilation; candidate is not reusable"
            raise CollectionError(message)
        receipt = {
            "input_key": input_key(root),
            "candidate": str(candidate.resolve()),
            "generation": verify(candidate),
            "model_calls": 0,
        }
        write_atomic(store / "build-receipt.json", canonical_bytes(receipt))

    def task_build() -> dict[str, object]:
        return {"actions": [action], "verbosity": 0}

    store.mkdir(parents=True, exist_ok=True)
    runner = DoitMain(ModuleTaskLoader({"task_build": task_build}))
    status = runner.run(["--db-file", str(store / "doit.db"), "build"])
    if status:
        message = f"build failed with status {status}; current publication is unchanged"
        raise CollectionError(message)
    return {**json.loads((store / "build-receipt.json").read_bytes()), "state": "executed"}
