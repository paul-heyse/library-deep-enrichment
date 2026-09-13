# Failure denominator and recovery checkpoint — 2026-09-13

The shared stage failure path now retains its captured input-membership receipts and producer-contract selection. Previously it wrote a failed job with empty inputs even though the exact requested denominator had already been captured. Failed jobs now preserve the same finite input identity used by the attempted run, including an empty selected catalog on a first-ever attempt. An emitted prefix remains unadmitted.

The last-success link now passes through invalidated or failed attempts without replacing the actual successful predecessor with an unsuccessful receipt. This corrects newly written job history; it does not rewrite historical receipts. The change affects generic stage orchestration and does not alter the frozen heldout transfer semantics.

Four new test cases cover producer exceptions, budget exceptions, `KeyboardInterrupt`, repeated failure, an invalidated source dependency, first-run empty membership, failed-view export/restore and successful retry without duplicate admission. They also check that the immutable prior successful reader remains usable. Thirteen stage/input/discovery controls passed in 12.25 seconds after the history-link correction. The full suite passed 434 tests in 162.13 seconds with the two existing warnings before that final history-link correction; the later focused controls validate the correction. Static checks remain green in the recorded tooling environment.

An additional test used the actual supervised worker in a separate corpus restored from the holdout archive. A control selection expanded from one owner to two. A deliberately undersized 1,000,000-byte RSS limit killed the child before admission. Its failed job retained exact receipts for the behavior request, both native owners, artifact, context, 21 source files and 24 blobs. It retained the original successful job identity. All 46 original holdout summaries remained available as unrelated results. Removing the deliberately undersized limit produced exactly two control summaries; a subsequent unchanged request reused them. The original development/holdout corpora and benchmark budgets were not changed by this failure experiment.

Actual worker recovery evidence:

- Imported holdout head: `285b2bc498bb7043d03dfe908c66776b84be8d9b636e7828dbb08bda78ba91e9`.
- Separate control success: `4d6638be6082d0859c03fdbf89ef32bac779543005de502046aedb8533c2f61d`.
- Failed control: `352ecbe458bef68b063f0ab98d01fe2d8124edaff6fdc75673d2c2e27cd13822`.
- Resumed control: `aeebef823600e4d67e47173067d766495ecb7c76d2659fa2a58d31fcf7f0304a`.

Receipts under `.cache/library-guides-foundational/20260913T101230Z`: `stage-failure-input-tests-v3.log`, `failure-input-full-suite.log`, `failure-input-ruff.log`, `failure-input-pyrefly.log`, and `real-worker-recovery-v2.json`/`.log`. Initial test and recovery diagnostics are retained separately.

FB16/G5 remain open. Native/source normalization failures, worker-prefix/owner progress counters, supervised interruption beyond the in-process control, solver failures, coordinator memory measurements and full numeric-budget qualification still require work. Retaining failed input receipts is a shared recovery improvement, not completion of those obligations.
