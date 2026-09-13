---
paths:
  - "tests/**"
  - "pilot/**"
  - "STATUS.md"
  - "docs/adr/**"
---

# Evidence truthfulness

Four test states, and only four: `passed`, `failed`, `blocked`, `not_run`. A missing worker
binary, an absent Souffle runtime, or an unavailable embedding container is **blocked** with
the prerequisite named (`tests/support/workers.py` skips with that reason); it is never a
pass. `just test-native` sets `LDE_REQUIRE_WORKERS=1` so a blocked worker test fails there.

No mocking of workers, the sandbox, or the corpus backend in tests that exist to prove the
boundary. Unit tests may mock freely.

Pilot receipts under `pilot/intelligence/reports` and `pilot/qualified/sources` are recorded
evidence from real runs. Do not hand-edit them; regenerate them by running the qualification
script that produced them, against the corpus under `LDE_HOME`.

`STATUS.md` reports counts that were measured by a command whose output is cited. Do not
carry a number forward from a previous run.

Empty search results are not proof of absence. `ok` means successful within the declared
scope. Keep declared, statically extracted, compiler-derived, type-checker-observed,
runtime-observed and agent-inferred facts distinct; they are categories, not a confidence
scale.
