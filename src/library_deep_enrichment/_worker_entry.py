"""Apply process limits before exec; used only by the supervised worker runtime."""

from __future__ import annotations

import os
import resource
import sys


def main() -> None:
    """Set hard resource ceilings and replace this process with the literal command."""
    memory, cpu, size = (int(value) for value in sys.argv[1:4])
    resource.setrlimit(resource.RLIMIT_AS, (memory, memory))
    resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu))
    resource.setrlimit(resource.RLIMIT_FSIZE, (size, size))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    os.execv(sys.argv[4], sys.argv[4:])


if __name__ == "__main__":
    main()
