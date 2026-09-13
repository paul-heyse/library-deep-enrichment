"""Linux process-tree resident-memory observation for supervised worker limits."""

from pathlib import Path


def resident_bytes(pid: int) -> int:
    """Observe worker and descendant resident memory, conservatively counting shared pages.

    Returns:
        Aggregate sampled RSS; exited processes no longer contribute.

    """
    pending = [pid]
    seen: set[int] = set()
    total = 0
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        path = Path(f"/proc/{current}")
        try:
            for line in (path / "status").read_text().splitlines():
                if line.startswith("VmRSS:"):
                    total += int(line.split()[1]) * 1024
            for thread in (path / "task").iterdir():
                pending.extend(int(value) for value in (thread / "children").read_text().split())
        except FileNotFoundError, ProcessLookupError:
            continue
    return total
