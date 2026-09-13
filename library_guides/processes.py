"""Bounded subprocess protocol for probes, examples and model runners."""

from __future__ import annotations

import os
import signal
import subprocess
import tempfile
import time
from pathlib import Path

from attrs import frozen

from library_guides.collection import CollectionError


@frozen(kw_only=True)
class ProcessResult:
    """Captured process outcome without inventing success from empty output."""

    returncode: int
    stdout: bytes
    stderr: bytes
    elapsed_seconds: float


def execute(
    argv: tuple[str, ...],
    *,
    cwd: Path,
    stdin: bytes = b"",
    timeout: float = 60,
    max_bytes: int = 2_000_000,
) -> ProcessResult:
    """Execute literal arguments with bounded time/output and process-tree cleanup.

    Returns:
        The process exit status, captured output and elapsed time.

    Raises:
        CollectionError: If process arguments or resource limits are invalid or exceeded.

    """
    if not argv or timeout <= 0 or max_bytes <= 0:
        message = "a nonempty command and positive process limits are required"
        raise CollectionError(message)
    started = time.monotonic()
    with (
        tempfile.TemporaryFile() as input_file,
        tempfile.TemporaryFile() as output,
        tempfile.TemporaryFile() as errors,
    ):
        input_file.write(stdin)
        input_file.seek(0)
        with subprocess.Popen(
            argv, cwd=cwd, stdin=input_file, stdout=output, stderr=errors, start_new_session=True
        ) as process:
            while process.poll() is None:
                elapsed = time.monotonic() - started
                if elapsed > timeout or output.tell() + errors.tell() > max_bytes:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                    message = f"process exceeded time/output budget: {argv[0]}"
                    raise CollectionError(message)
                time.sleep(0.02)
            if output.tell() + errors.tell() > max_bytes:
                message = f"process exceeded output budget: {argv[0]}"
                raise CollectionError(message)
            output.seek(0)
            errors.seek(0)
            return ProcessResult(
                returncode=process.returncode,
                stdout=output.read(),
                stderr=errors.read(),
                elapsed_seconds=time.monotonic() - started,
            )
