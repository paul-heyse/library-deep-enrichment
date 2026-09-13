"""Cargo process observations kept distinct from declaration and unit evidence."""

from __future__ import annotations

import os
import signal
import subprocess
import time
from contextlib import suppress
from pathlib import Path

from library_guides.collection import CollectionError
from library_guides.store.digests import digest_file
from library_guides.worker_runtime import WorkerRequest, command


def capture(
    request: WorkerRequest, directory: Path, environment: dict[str, str]
) -> dict[str, object]:
    """Capture bounded raw Cargo streams with explicit environment and process cleanup.

    Returns:
        Actual exit, streams, digests and elapsed time; a nonzero exit is retained.

    Raises:
        CollectionError: If any declared resource budget is exceeded.

    """
    directory.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    stdout, stderr = directory / "stdout", directory / "stderr"
    with (
        stdout.open("wb") as output,
        stderr.open("wb") as errors,
        subprocess.Popen(
            command(request),
            cwd=request.cwd,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=output,
            stderr=errors,
            start_new_session=True,
        ) as process,
    ):
        try:
            while process.poll() is None:
                if (
                    time.monotonic() - started > request.budget.wall_seconds
                    or stdout.stat().st_size > request.budget.output_bytes
                    or stderr.stat().st_size > request.budget.stderr_bytes
                ):
                    message = "Cargo process exceeded declared time or output budget"
                    raise CollectionError(message)
                time.sleep(0.05)
        finally:
            with suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
            process.wait()
    if (
        stdout.stat().st_size > request.budget.output_bytes
        or stderr.stat().st_size > request.budget.stderr_bytes
    ):
        message = "Cargo process exceeded output budget before exit"
        raise CollectionError(message)
    return {
        "argv": request.argv,
        "cwd": str(request.cwd),
        "environment": environment,
        "returncode": process.returncode,
        "elapsed_seconds": time.monotonic() - started,
        "stdout": str(stdout),
        "stdout_digest": digest_file(stdout),
        "stderr": str(stderr),
        "stderr_digest": digest_file(stderr),
        "isolation": "filesystem-network"
        if request.isolate
        else "resource_limits_network_acquisition",
        "limits": "per-process address-space and CPU; wall/output supervision; no aggregate cgroup memory guarantee",
    }


def environment() -> dict[str, str]:
    """Construct a minimal process environment without inherited compiler flags/wrappers.

    Returns:
        Executable/cache locations and a fixed diagnostic locale.

    """
    return {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(Path.home()),
        "CARGO_HOME": os.environ.get("CARGO_HOME", str(Path.home() / ".cargo")),
        "RUSTUP_HOME": os.environ.get("RUSTUP_HOME", str(Path.home() / ".rustup")),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "CARGO_TERM_COLOR": "never",
    }
