"""Lifecycle plans are inert and container ownership is checked before mutation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from library_deep_enrichment.corpus.backend import CorpusError
from library_deep_enrichment.processes import ProcessResult
from library_deep_enrichment.runtime import RuntimeConfig, lifecycle


def test_plan_does_not_create_cache_or_run_docker(tmp_path: Path) -> None:
    """The default runtime action is a reviewable plan with pinned literal arguments."""
    config = RuntimeConfig(root=tmp_path / "absent")
    plan = lifecycle(config, "start")
    assert plan["apply"] is False
    assert not config.root.exists()
    command = plan["start_command"]
    assert isinstance(command, tuple)
    assert "127.0.0.1:18080:8000" in command


def test_unowned_container_cannot_be_stopped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A matching name cannot grant lifecycle ownership over somebody else's container."""
    calls = []

    def execute(arguments: tuple[str, ...], **_options: object) -> ProcessResult:
        calls.append(arguments)
        stdout = (
            b"lde-embeddings\n"
            if arguments[1] == "container"
            else json.dumps([{"Config": {"Labels": {}}, "Id": "foreign"}]).encode()
        )
        return ProcessResult(returncode=0, stdout=stdout, stderr=b"", elapsed_seconds=0.0)

    monkeypatch.setattr("library_deep_enrichment.runtime.execute", execute)
    with pytest.raises(CorpusError, match="unqualified configuration"):
        lifecycle(RuntimeConfig(root=tmp_path), "stop", apply=True)
    assert all("stop" not in command for command in calls)
    receipts = tuple((tmp_path / "lifecycle").glob("*.json"))
    assert len(receipts) == 1
    receipt = json.loads(receipts[0].read_bytes())
    assert receipt["state"] == "failed"
    assert receipt["error_type"] == "CorpusError"
    assert receipt["action"] == "stop"


def test_model_identity_detects_same_size_corruption(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Actual model bytes, including small git objects, must match the committed inventory."""
    import hashlib

    from library_deep_enrichment.runtime_identity import model_identity

    snapshot = tmp_path / "revision"
    snapshot.mkdir()
    config = b"config"
    weights = b"weights"
    (snapshot / "config.json").write_bytes(config)
    (snapshot / "model.safetensors").write_bytes(weights)
    manifest = tmp_path / "assets/runtime/qwen3-embedding-8b.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        json.dumps(
            {
                "repository": "fixture",
                "revision": "revision",
                "files": {
                    "config.json": {
                        "size": len(config),
                        "blob_id": hashlib.sha1(
                            f"blob {len(config)}\0".encode() + config,
                            usedforsecurity=False,
                        ).hexdigest(),
                    },
                    "model.safetensors": {
                        "size": len(weights),
                        "lfs_sha256": hashlib.sha256(weights).hexdigest(),
                    },
                },
            }
        )
    )
    monkeypatch.setattr("library_deep_enrichment.runtime_identity.files", lambda _package: tmp_path)
    assert model_identity(snapshot)["bytes"] == len(config) + len(weights)
    (snapshot / "model.safetensors").write_bytes(b"changed")
    with pytest.raises(CorpusError, match="model content differs"):
        model_identity(snapshot)
    (snapshot / "model.safetensors").write_bytes(weights)
    (snapshot / "config.json").write_bytes(b"damage")
    with pytest.raises(CorpusError, match="model content differs"):
        model_identity(snapshot)
    (snapshot / "extra.json").write_text("{}")
    with pytest.raises(CorpusError, match="exact file inventory"):
        model_identity(snapshot)
