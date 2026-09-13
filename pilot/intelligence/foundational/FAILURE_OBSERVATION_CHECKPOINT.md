# Failed worker observation checkpoint

Date: 2026-09-13. FB16 remains in progress; G5 remains open. This increment preserves observed interrupted work without admitting a prefix as a completed behavioral result.

The new `stage_failures` family records the exact failed job, stage definition, input manifest, request, coordinator phase, collected record/byte counts and elapsed time. Worker observations retain the request identity, received bytes, delivered and consumed records, optional declared denominator, terminal presence, exit status and sampled process-tree RSS. An absent handshake means the denominator is unobserved. The worker can perform internal computation before producing its stream, so its internal completed-owner count remains explicitly unobserved.

Coordinator RSS is recorded separately as Linux process-lifetime high-water RSS before and after the attempt. It excludes child usage and is not presented as the stage's isolated memory peak. Failure provenance and observational counter invariants are checked at admission. A resumed or invalidated job withdraws its prior failure record from the current view through existing dependency handling; the original failed manifest and its portable archive retain that record. Existing job and execution schemas keep their original meaning.

The supervisor preserves original exception types, attaches typed observations through exception translation, and cleans the process group before reporting failure. Truncated zero-exit streams, nonzero exits, timeouts, callback rejection and `KeyboardInterrupt` retain exact observed prefixes. No decoded prefix is admitted as a semantic product. Implementation fingerprints now include the stage engine and its observation helpers.

Validation in `/home/paul/smartref/.cache/library-guides-foundational/20260913T101230Z`:

- `observed-failure-tests-v2.log`: 25 focused controls passed in 8.27 seconds, including portable failed-view restoration, impossible-counter/provenance rejection and retry without duplicate admission.
- `observed-failure-full-suite.log`: 440 tests passed in 149.91 seconds, with the same two dependency warnings. This precedes the final addition of observation helpers to the stage implementation fingerprint; the subsequent focused stage/discovery run covers that change.
- `observed-failure-ruff.log`, `observed-failure-pyrefly-v2.log`, `observed-failure-format.log`: plan-scope Ruff/formatting and zero Pyrefly diagnostics.
- `real-worker-recovery-v3.json` and `.log`: a real analytical child failed the deliberately undersized 1,000,000-byte RSS limit in a separate copy of the held-out archive. The supervisor observed 48,119,808 bytes across two RSS samples, no output or handshake, and exit `-9`. The coordinator process-lifetime high-water reading was 1,371,320,320 bytes. The exact six-family input receipts remained available. All 46 unrelated held-out summaries remained selected; retry produced the two requested control summaries and the unchanged retry reused them. The current failure observation was withdrawn after successful retry.

The real control failed manifest is `3bf3f45be05762a21761a6939c7daa69b7a5eb2e9c575de4539a481a9f1369f0`; its resumed manifest is `adbea9e8271388b38b7ac310317d796747556c5430785d5bcfc0080c210ce410`. Original benchmark selections, corpora and releases were not changed. The original one-owner and expanded two-owner recovery control are separate from the 190-candidate reservation.

Remaining FB16 scope includes complete normalization/interruption owner accounting, coordinator admission memory qualification, per-SCC/specialization resumability, aggregate finite population budgets and the remaining invalidation/failure cases. This checkpoint does not close prerequisite behavioral gates or terminal delivery.
