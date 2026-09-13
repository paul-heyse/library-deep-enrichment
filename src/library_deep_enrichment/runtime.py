"""Explicit, reproducible local inference lifecycle; query paths never start services."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import httpx
from attrs import evolve, frozen

from library_deep_enrichment.corpus.backend import CorpusError
from library_deep_enrichment.corpus.encoding import bytes_digest, canonical, digest
from library_deep_enrichment.discovery.embeddings import EmbeddingClient, Endpoint
from library_deep_enrichment.processes import execute
from library_deep_enrichment.runtime_identity import model_identity
from library_deep_enrichment.workflows.discovery import qwen_recipe

IMAGE = "vllm/vllm-openai@sha256:c2914767605584b6d8f45686b82de173ecc99e781897aa3d0a66dacd72c51ae1"
MODEL_REVISION = "1d8ad4ca9b3dd8059ad90a75d4983776a23d44af"
LABEL = "io.github.paul-heyse.library-deep-enrichment.runtime"
SOUFFLE_URL = "https://github.com/souffle-lang/souffle/releases/download/2.5/x86_64-ubuntu-2404-souffle-2.5-Linux.deb"
SOUFFLE_SHA512 = "6b86e554f6aa5abf8a8b55d8312ae37c0957c5bd6c9edeea89246db9406f645ec5e600b84fe6636b1c163da556f0da6c3d2dad46c1083413f2fcf4f95b9ac62c"


@frozen(kw_only=True)
class RuntimeConfig:
    """Operator-selected cache/device/port; model and image identities are pinned."""

    root: Path
    name: str = "lde-embeddings"
    port: int = 18080
    device: str = "0"

    @property
    def snapshot(self) -> Path:
        """Resolve the pinned local model snapshot.

        Returns:
            A tooling-owned immutable revision directory.

        """
        return self.root / "models/hub/models--Qwen--Qwen3-Embedding-8B/snapshots" / MODEL_REVISION

    @property
    def identity(self) -> str:
        """Fingerprint service options for scoped lifecycle ownership.

        Returns:
            A configuration digest used as an exact container ownership label.

        """
        return digest(
            [str(self.root.resolve()), self.name, self.port, self.device, IMAGE, MODEL_REVISION]
        )


def _run(config: RuntimeConfig, arguments: tuple[str, ...], *, timeout: float = 60.0) -> str:
    result = execute(arguments, cwd=config.root, timeout=timeout, max_bytes=2 * 1024 * 1024)
    if result.returncode:
        message = f"runtime command failed: {arguments[0]}: {result.stderr.decode(errors='replace')[:2000]}"
        raise CorpusError(message)
    return result.stdout.decode()


def _container(config: RuntimeConfig) -> dict[str, object] | None:
    result = execute(
        ("docker", "container", "ls", "-a", "--format", "{{.Names}}"),
        cwd=config.root,
        max_bytes=1024 * 1024,
    )
    if result.returncode:
        message = "Docker inventory is unavailable"
        raise CorpusError(message)
    if config.name not in result.stdout.decode().splitlines():
        return None
    value = json.loads(_run(config, ("docker", "inspect", config.name)))[0]
    if value["Config"]["Labels"].get(LABEL) != config.identity:
        message = "container name belongs to an unqualified configuration; no lifecycle mutation is authorized"
        raise CorpusError(message)
    return value


def _start_command(config: RuntimeConfig) -> tuple[str, ...]:
    snapshot = f"/models/hub/models--Qwen--Qwen3-Embedding-8B/snapshots/{MODEL_REVISION}"
    return (
        "docker",
        "run",
        "-d",
        "--name",
        config.name,
        "--label",
        f"{LABEL}={config.identity}",
        "--gpus",
        f"device={config.device}",
        "-p",
        f"127.0.0.1:{config.port}:8000",
        "--shm-size",
        "1g",
        "--memory",
        "40g",
        "--pids-limit",
        "512",
        "-e",
        "HF_HUB_OFFLINE=1",
        "--mount",
        f"type=bind,source={config.root.resolve()}/models/hub,target=/models/hub,readonly",
        IMAGE,
        "--model",
        snapshot,
        "--served-model-name",
        "lde-qwen",
        "--runner",
        "pooling",
        "--dtype",
        "bfloat16",
        "--max-model-len",
        "4096",
        "--max-num-seqs",
        "4",
        "--max-num-batched-tokens",
        "8192",
        "--gpu-memory-utilization",
        "0.85",
        "--enforce-eager",
    )


def embedding_client(config: RuntimeConfig) -> EmbeddingClient:
    """Connect to an explicitly requested local service without lifecycle mutation.

    Returns:
        A client with the pinned local tokenizer and numerical recipe.

    """
    identity = model_identity(config.snapshot)
    recipe = qwen_recipe()
    return EmbeddingClient(
        Endpoint(
            url=f"http://127.0.0.1:{config.port}",
            served_model="lde-qwen",
            tokenizer_path=config.snapshot,
        ),
        evolve(
            recipe,
            runtime=(
                f"{recipe.runtime};model-bytes={identity['model_digest']};"
                f"tokenizer-bytes={identity['tokenizer_digest']}"
            ),
        ),
    )


def canary(config: RuntimeConfig) -> dict[str, object]:
    """Exercise actual inference and record a finite service qualification witness.

    Returns:
        Exact input, model, dimensions, normalization, and distinctness observations.

    Raises:
        CorpusError: The service returns identical vectors for the contrastive inputs.

    """
    client = embedding_client(config)
    queries = ("Consume rows as incremental Arrow batches", "Construct a schema retaining metadata")
    vectors = tuple(client.embed_query(query) for query in queries)
    if vectors[0] == vectors[1]:
        message = "contrastive service canary returned identical embeddings"
        raise CorpusError(message)
    report: dict[str, object] = {
        "configuration": config.identity,
        "image": IMAGE,
        "revision": MODEL_REVISION,
        "queries": queries,
        "dimensions": [len(vector) for vector in vectors],
        "vector_digests": [digest(vector) for vector in vectors],
        "distinct": True,
        "recipe": client.recipe.runtime,
    }
    (config.root / "embedding-runtime-canary.json").write_bytes(canonical(report))
    return report


def provision_souffle(root: Path) -> Path:
    """Acquire and verify the qualified Souffle 2.5 rule runtime under a runtime root.

    Idempotent: an executable that already matches the qualified digest is left alone.

    Returns:
        The verified ``souffle`` executable.

    Raises:
        CorpusError: The download exceeded its size boundary or a checksum did not match.

    """
    from library_deep_enrichment.semantics.relational import SOFTWARE_DIGEST

    destination = root / "tools/souffle-2.5"
    executable = destination / "runtime/usr/bin/souffle"
    if not executable.is_file() or bytes_digest(executable.read_bytes()) != SOFTWARE_DIGEST:
        destination.mkdir(parents=True, exist_ok=True)
        package = destination / "souffle-2.5.deb"
        checksum = hashlib.sha512()
        with (
            httpx.stream("GET", SOUFFLE_URL, follow_redirects=True, timeout=60) as response,
            package.open("wb") as stream,
        ):
            response.raise_for_status()
            size = 0
            for chunk in response.iter_bytes():
                size += len(chunk)
                if size > 64 * 1024 * 1024:
                    message = "Souffle acquisition exceeded its package size boundary"
                    raise CorpusError(message)
                checksum.update(chunk)
                stream.write(chunk)
        if checksum.hexdigest() != SOUFFLE_SHA512:
            message = "Souffle release checksum mismatch"
            raise CorpusError(message)
        subprocess.run(("dpkg-deb", "-x", str(package), str(destination / "runtime")), check=True)
        if bytes_digest(executable.read_bytes()) != SOFTWARE_DIGEST:
            message = "Souffle executable differs from the qualified runtime"
            raise CorpusError(message)
    return executable


def _provision(config: RuntimeConfig) -> None:
    from huggingface_hub import snapshot_download

    provision_souffle(config.root)
    snapshot_download(
        repo_id="Qwen/Qwen3-Embedding-8B",
        revision=MODEL_REVISION,
        cache_dir=config.root / "models/hub",
        max_workers=4,
    )
    _run(config, ("docker", "pull", IMAGE), timeout=1800.0)


def lifecycle(config: RuntimeConfig, action: str, *, apply: bool = False) -> dict[str, object]:
    """Plan by default; explicitly provision/start/stop or qualify the owned service.

    Returns:
        The concrete plan or executed lifecycle outcome, without touching corpus heads.

    Raises:
        CorpusError: An action is unknown or the pinned model is not available.
        KeyboardInterrupt: An interrupted action is recorded before cancellation propagates.

    """
    if action not in {"provision", "start", "stop", "status", "canary"}:
        message = "runtime action must be provision, start, stop, status, or canary"
        raise CorpusError(message)
    if not apply and action != "status":
        return {
            "action": action,
            "apply": False,
            "configuration": config.identity,
            "image": IMAGE,
            "model_revision": MODEL_REVISION,
            "cache_root": str(config.root),
            "start_command": _start_command(config),
            "souffle_sha512": SOUFFLE_SHA512,
        }
    config.root.mkdir(parents=True, exist_ok=True)
    receipt: dict[str, object] = {
        "action": action,
        "configuration": config.identity,
        "started_at": datetime.now(UTC).isoformat(),
    }
    try:
        result = _apply_lifecycle(config, action)
    except (Exception, KeyboardInterrupt) as error:
        receipt.update(state="failed", error_type=type(error).__name__, reason=str(error)[:4000])
        _record_lifecycle(config, receipt)
        raise
    receipt.update(state="complete", result=result)
    _record_lifecycle(config, receipt)
    return result


def _record_lifecycle(config: RuntimeConfig, receipt: dict[str, object]) -> None:
    receipt["finished_at"] = datetime.now(UTC).isoformat()
    destination = config.root / "lifecycle"
    destination.mkdir(parents=True, exist_ok=True)
    data = canonical(receipt)
    temporary = destination / f".{uuid4().hex}.tmp"
    with temporary.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(destination / f"{digest(receipt)}.json")
    descriptor = os.open(destination, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _apply_lifecycle(config: RuntimeConfig, action: str) -> dict[str, object]:
    if action == "provision":
        _provision(config)
        return {
            "action": action,
            "configuration": config.identity,
            "state": "provisioned",
            "model_identity": model_identity(config.snapshot),
        }
    if action == "canary":
        return canary(config)
    container = _container(config)
    if action == "start":
        _run(config, ("nvidia-smi", "--query-gpu=name,driver_version", "--format=csv,noheader"))
        if not config.snapshot.is_dir():
            message = "provision the pinned model snapshot before starting inference"
            raise CorpusError(message)
        identity = model_identity(config.snapshot)
        command = ("docker", "start", str(container["Id"])) if container else _start_command(config)
        return {
            "action": action,
            "container": _run(config, command, timeout=120.0).strip(),
            "state": "started; run the canary after model loading",
            "model_identity": identity,
        }
    if action == "stop" and container:
        _run(config, ("docker", "stop", "--timeout", "30", str(container["Id"])))
    return {
        "action": action,
        "configuration": config.identity,
        "container": container,
        "model_available": config.snapshot.is_dir(),
    }
