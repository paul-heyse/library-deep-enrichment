"""Supervised streaming extraction with hard limits and process-group cleanup."""

from __future__ import annotations

import os
import selectors
import signal
import subprocess
import sys
import tempfile
import time
from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING

from attrs import frozen

from library_deep_enrichment.collection import CollectionError
from library_deep_enrichment.facts.protocol import Frames
from library_deep_enrichment.worker_observations import (
    ObservedWorkerFailureError,
    WorkerObservation,
    WorkerProgress,
)
from library_deep_enrichment.worker_resources import resident_bytes

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import BinaryIO

    from library_deep_enrichment.facts.contracts import Budget


class WorkerExecutionError(CollectionError):
    """A failed child with an explicit exit status and bounded diagnostic bytes."""

    def __init__(self, returncode: int, diagnostics: bytes) -> None:
        """Retain the exit classification and bounded child diagnostics."""
        self.returncode = returncode
        super().__init__(f"worker failed ({returncode}): {diagnostics.decode(errors='replace')}")


class WorkerLimitError(CollectionError):
    """The supervisor enforced a declared resource ceiling."""


@frozen(kw_only=True)
class WorkerRequest:
    """Pinned worker request, with explicit input, output and enforcement policy."""

    argv: tuple[str, ...]
    cwd: Path
    request_id: str
    input_digest: str
    budget: Budget
    read_roots: tuple[Path, ...] = ()
    write_roots: tuple[Path, ...] = ()
    isolate: bool = False
    address_space_bytes: int | None = None


def _interpreter_roots() -> tuple[Path, ...]:
    """Bind every directory the interpreter symlink chain passes through.

    A uv-managed virtual environment links ``.venv/bin/python`` to a versioned alias directory
    that is itself a symlink; binding only the endpoint and the venv leaves the alias unbound
    and ``execvp`` fails inside the sandbox.

    Returns:
        Two-levels-up roots for the executable and each intermediate link target.

    """
    found: list[Path] = []
    current = Path(sys.executable)
    while True:
        root = current.parent.parent
        if root not in found:
            found.append(root)
        if not current.is_symlink():
            return tuple(found)
        target = current.readlink()
        current = target if target.is_absolute() else current.parent / target


def command(request: WorkerRequest) -> tuple[str, ...]:
    """Construct the limited command; isolation has no silent fallback.

    Returns:
        Literal process arguments.

    Raises:
        CollectionError: If required isolation or command configuration is unavailable.

    """
    if not request.argv or not Path(request.argv[0]).is_absolute():
        message = "worker executable must be an absolute path"
        raise CollectionError(message)
    limits = request.budget
    if min(limits.wall_seconds, limits.cpu_seconds, limits.memory_bytes, limits.output_bytes) <= 0:
        message = "worker budgets must be positive"
        raise CollectionError(message)
    if (
        request.address_space_bytes is not None
        and request.address_space_bytes < limits.memory_bytes
    ):
        message = "address-space ceiling must cover the resident-memory budget"
        raise CollectionError(message)
    entry = Path(__file__).with_name("_worker_entry.py")
    argv = (
        sys.executable,
        "-I",
        str(entry),
        str(request.address_space_bytes or limits.memory_bytes),
        str(limits.cpu_seconds),
        str(limits.output_bytes),
        *request.argv,
    )
    if not request.isolate:
        return argv
    sandbox = Path("/usr/bin/bwrap")
    if not sandbox.is_file():
        message = "required filesystem/network isolation is unavailable"
        raise CollectionError(message)
    roots = tuple(Path(value) for value in ("/usr", "/bin", "/lib", "/lib64", "/etc/alternatives"))
    bindings = [
        str(sandbox),
        "--die-with-parent",
        "--unshare-net",
        "--unshare-pid",
        "--new-session",
        "--proc",
        "/proc",
        "--dev",
        "/dev",
        "--tmpfs",
        "/tmp",
    ]
    for path in (*roots, *request.read_roots, entry.parent, *_interpreter_roots()):
        if path.exists():
            bindings.extend(("--ro-bind", str(path), str(path)))
    for path in request.write_roots:
        bindings.extend(("--bind", str(path), str(path)))
    bindings.extend(("--chdir", str(request.cwd), "--", *argv))
    return tuple(bindings)


def run(request: WorkerRequest, consume: Callable[[dict[str, object]], None]) -> dict[str, object]:
    """Validate frames while consuming records into private staging.

    Returns:
        Committed header/terminal data and measured process execution metadata.

    Worker, transport and consumer errors retain their original exception type with
    a typed supervisor observation in the cause chain after child cleanup.

    """
    frames = Frames(request.budget, request.request_id, request.input_digest)
    started = time.monotonic()
    progress = WorkerProgress(started=started)
    with (
        tempfile.TemporaryFile() as errors,
        subprocess.Popen(
            command(request),
            cwd=request.cwd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=errors,
            start_new_session=True,
        ) as process,
    ):
        try:
            _receive(process, errors, frames, consume, progress)
        except BaseException as error:
            with suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
            returncode = process.wait()
            expected = frames.header.get("expected_records") if frames.header else None
            observation = WorkerObservation(
                request=request.request_id,
                input_digest=request.input_digest,
                elapsed_seconds=time.monotonic() - started,
                peak_sampled_tree_rss_bytes=progress.peak_rss,
                rss_samples=progress.rss_samples,
                output_bytes=frames.total,
                delivered_records=progress.delivered_records,
                consumed_records=progress.consumed_records,
                expected_records=(expected,) if isinstance(expected, int) else (),
                terminal_seen=frames.terminal is not None,
                returncode=returncode,
                rss_limit_bytes=request.budget.memory_bytes,
                address_space_limit_bytes=request.address_space_bytes
                or request.budget.memory_bytes,
            )
            cause = ObservedWorkerFailureError(observation)
            cause.__cause__ = error.__cause__
            raise error from cause
        finally:
            # Clean descendants even if the parent has already exited or closed stdout.
            with suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
            process.wait()
    return {
        "header": frames.header,
        "terminal": frames.terminal,
        "elapsed_seconds": time.monotonic() - started,
        "returncode": 0,
        "isolation": "filesystem-network" if request.isolate else "resource-limits",
        "command": list(request.argv),
        "peak_sampled_tree_rss_bytes": progress.peak_rss,
        "rss_limit_bytes": request.budget.memory_bytes,
        "address_space_limit_bytes": request.address_space_bytes or request.budget.memory_bytes,
        "output_bytes": frames.total,
    }


def _receive(
    process: subprocess.Popen[bytes],
    errors: BinaryIO,
    frames: Frames,
    consume: Callable[[dict[str, object]], None],
    progress: WorkerProgress,
) -> None:
    _drain(process, errors.fileno(), frames, consume, progress)
    errors.seek(0)
    diagnostics = errors.read(frames.budget.stderr_bytes + 1)
    if process.returncode or len(diagnostics) > frames.budget.stderr_bytes:
        raise WorkerExecutionError(process.returncode or 1, diagnostics)
    frames.finish()


def _drain(
    process: subprocess.Popen[bytes],
    errors: int,
    frames: Frames,
    consume: Callable[[dict[str, object]], None],
    progress: WorkerProgress,
) -> None:
    with selectors.DefaultSelector() as selector:
        if process.stdout is None:
            message = "worker stdout unavailable"
            raise CollectionError(message)
        selector.register(process.stdout, selectors.EVENT_READ)
        finished = False
        while not finished or process.poll() is None:
            if time.monotonic() - progress.started > frames.budget.wall_seconds:
                message = "worker exceeded wall-time budget"
                raise WorkerLimitError(message)
            progress.peak_rss = max(progress.peak_rss, resident_bytes(process.pid))
            progress.rss_samples += 1
            if progress.peak_rss > frames.budget.memory_bytes:
                message = "worker exceeded aggregate resident-memory budget"
                raise WorkerLimitError(message)
            if os.fstat(errors).st_size > frames.budget.stderr_bytes:
                message = "worker exceeded diagnostic budget"
                raise CollectionError(message)
            if finished:
                time.sleep(0.02)
            for key, _ in () if finished else selector.select(timeout=0.05):
                data = os.read(key.fd, 65536)
                if not data:
                    finished = True
                    break
                for record in frames.feed(data):
                    progress.delivered_records += 1
                    consume(record)
                    progress.consumed_records += 1
