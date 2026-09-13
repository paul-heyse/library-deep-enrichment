> **Migrated 2026-09-13** from `smartref/tooling/library_guides/docs/foundational_behavior_characterization_status_and_repo_handover_2026-09-13.md` (final handover delta, incorporated after the initial import). Frozen provenance: paths inside refer to the pre-migration layout (`library_guides/` is now `src/library_deep_enrichment/`, `native/` and `rustdoc-helper/` are now `crates/`, `LIBRARY_GUIDES_*` is now `LDE_*`).

# Foundational behavior characterization: implementation status and repository handover

Date: 2026-09-13. Author and reviewer: the implementation agent; no independent human review is claimed.

**Concurrent relocation observed during finalization:** the workspace cache directories moved out of `/home/paul/smartref/.cache/`. The foundational run is now at `/home/paul/.cache/library-deep-enrichment/foundational/20260913T101230Z`; its final logs, prior checkpoint and preservation receipt were located there. Corresponding cache groups now use `intelligence/`, `implementation/`, `runtime/`, `acquired/`, `examples/`, `source-semantics/` and `recovery/` beneath `/home/paul/.cache/library-deep-enrichment/`. Absolute SMARTREF cache paths below and inside historical receipts describe acquisition-time provenance. This task did not perform that relocation or validate the concurrently created successor repository. Final source/documents are being completed in `/home/paul/smartref/tooling/library_guides`; the migration owner must incorporate this final handover delta into the successor checkout.

**The foundational implementation plan is incomplete. FB00/G0 is accepted; G1–G7 remain open. Implementation is stopping at the user's requested checkpoint before migration to a standalone repository.** The current constant-memory extraction increment has been finished as a bounded fact-collection feature. It does not complete native binding composition or the larger behavior-characterization plan.

The scope authority remains the [implementation plan](foundational_behavior_characterization_implementation_plan_v1_2026-09-13.md), its [package/gate ledger](foundational_behavior_characterization_implementation_plan_v1_2026-09-13.json), and the [design assessment](foundational_behavior_characterization_design_assessment_2026-09-13.md). The [execution ledger](../pilot/intelligence/foundational/execution.json) and [checkpoint index](../pilot/intelligence/foundational/STATUS.md) retain detailed chronological evidence. This document consolidates the state for a new maintainer; historical checkpoint counts are not current-run qualification.

## 1. Completion boundary and preservation

There are 19 mandatory packages. At this handover, one is complete, 13 are in progress (including the native-boundary preflight), and five have not started. No mandatory package has been removed or converted to optional work. No percentage-complete estimate is justified by the available evidence.

The earlier [semantic-intelligence completion report](../pilot/intelligence/COMPLETION.md) concerns an earlier seven-step plan. Its completion does **not** mean this foundational plan is complete. Similarly, the existing [24-task assessment](../pilot/intelligence/TASK_ASSESSMENT.md) remains the historical consumer baseline: **16 gaps, four partial results and four supported controls**. These judgments have not yet been regenerated through the new foundational pipeline.

The task began from a 270-file core freeze, `89cb8d1665f7d4e06a2cc48b80a19a936679aa1617500a4c36d8ad3444343b3e`. A larger 329-file preservation snapshot records the initial relevant source and documentation bytes. Implementation changed the working tooling source while retaining those originals under the run directory's `before/` tree. The original corpus and releases were not replaced.

| Preserved authority | Identity/location |
| --- | --- |
| Original analysis manifest | `f61eabbd4fe17866ca3bd5c6a3d7b1d8875e3f53ee32b204a693ce4292fa9913` |
| Main historical task release | `7e7b42b41bafcfca619a6f5e8856effe6f0a566e21af99259b63fb58abfa1596` |
| Original corpus | `/home/paul/smartref/.cache/library-guides-intelligence/pilot-v4/corpus` |
| Foundational run root | `/home/paul/smartref/.cache/library-guides-foundational/20260913T101230Z` |
| Baseline acceptance | [baseline-acceptance.json](../pilot/intelligence/foundational/baseline-acceptance.json) |
| Frozen population and independent expectations | [benchmark.json](../pilot/intelligence/foundational/benchmark.json), [expectations.json](../pilot/intelligence/foundational/expectations.json), [reservation.json](../pilot/intelligence/foundational/reservation.json) |

The entire `tooling/library_guides/` directory currently appears **untracked** to the parent SMARTREF Git repository. The two generated guide-skill directories under `.codex/skills/` also appear untracked. A parent-repository commit or `git diff` alone is therefore not a complete handover. Preserve the actual files and content manifests before constructing the new repository. No repository creation, Git reset, cleanup, environment migration or GPU service change was performed for this handover.

## 2. What is implemented

### Executable facts and contextual identity

New owned Python/Arrow contracts represent executable programs, symbolic terms, guarded outcomes, provenance, coverage and derivation support. They use the existing corpus coordinator, exact selected prerequisites, reference validation, model fingerprints, archive transport and replay. Old native/source-analysis records retain their original model meanings.

Rust now has opt-in, versioned acquisition formats for typed executable operators, concrete instances, callable operands, closure/drop/ABI uses, and constant allocation/layout facts. Identities include compiler unit, definition path/build hash, phase and observed substitutions. Exact source byte witnesses qualify mappings, including referenced helper files outside the primary source input. Capture budgets and unavailable targets are retained as outcomes.

Python acquisition uses an owned Ruff execution projection from the populated semantic traversal. The normalizer models sequential and short-circuit evaluation, guarded control flow, exception/finally/context handling, match cases, nested comprehensions, private target scopes, ordered tuple/list expansion and finite iterator behavior. It separates generator construction from activation. The Pyrefly integration reconciles source coordinates and declaration/re-export locations while retaining computed/declared/expected roles, stub boundaries and unresolved dispatch.

Cargo/compiler correspondence, callable population selection and public-route accounting are implemented over retained evidence. Feature roles and duplicate dependency versions remain contextual; neither documentation presence nor successful extraction establishes ordinary-consumer availability.

### General behavior analysis and witnesses

The interpreter supports guarded symbolic values, boolean/variant/null relationships, machine-width integer operations and checked overflow pairs, selected IEEE literal comparisons, field forwarding/reconstruction, private collection regions, finite ordered iteration and conservative unknown-call escape. Z3 supplies bounded feasibility checks. Recursive SCC summaries compute bounded envelopes and check the post-fixed-point condition.

Cross-unit concrete calls, function items flowing through assignments/returns/fields/arguments, closure captures and Rust-call tuple spreading feed composition. Automatic helper selection retains direct calls, callable references and drop uses separately. Exact-definition demand preserves the full generic inventory while concentrating instance acquisition on explicitly selected roots.

Witness infrastructure retains contextual inputs, executable observations, outcome comparisons, expression/operator correspondence, negative controls and bounded shrinking. Separate ordinary compiler/runtime executions have checked real Rust and Python relationships. Finite observations and model assumptions remain separate; a successful observed case is not promoted into a universal library law.

### Operational and population infrastructure

Behavior coverage records preserve completed peers alongside owner normalization/interpretation exhaustion. Worker failure records include exact attempted inputs, observed transport prefixes, missing denominators, exit state, sampled worker memory and predecessor identity. Real forced-worker failure/resume controls preserved unrelated summaries and reused unchanged results. Partial transport is not admitted as successful behavioral output.

A characterization layer profiles dependency sources, structural cost counts, region relationships and ordering/interference obligations for the entire mapped population. Existing graph/FCA/label facilities remain available, but the new task-independent discovery package has not been implemented.

## 3. Work-package status and remaining acceptance

“In progress” below means implemented and tested increments exist; it does not mean the package acceptance criteria have passed.

| Package | Status | Implemented evidence | Remaining scope before completion |
| --- | --- | --- | --- |
| **FB00** Baseline/reservation | **Complete** | Preservation, environment, 315-test initial baseline, construct matrix, finite 190-candidate split and six expectations frozen before evaluation. | Retain the reservation and provenance during migration; do not silently replace the holdout or denominator. |
| **FB01** Contracts/admission | In progress | Typed executable, summary, origin, typing, coverage, call and characterization records; source-backed admission/replay; historical schemas; explicit unknown/budget/failure outcomes. | Complete contracts for protocols, boundary bindings and family laws; qualify all malformed/cross-context cases and new release closures together under G1. |
| **FB02** Context/public identity | In progress | Cargo/compiler/rustdoc correspondence, public candidate inventories, exact source/context identity, duplicate versions, feature roles, instance/substitution and Python declaration joins. | Complete effective target/build inputs, boundary/registry membership and negative-claim invalidation; broaden renumbering/configuration controls. Diagnose the recorded PyO3 crate-hash mismatch rather than assuming captures are interchangeable. |
| **FB03** Rust projection | In progress | Typed scalars/operators, logical types, fields, source mappings, concrete bodies, function references, closures, Rust-call ABI, shims/drop and constant-memory layouts. | Full construct disposition audit; remaining virtual/vtable, coroutine, binder, region and alias semantics; qualify new fact uses as behavior rather than merely collected bytes. |
| **FB04** Python projection/types | In progress | Execution graph and order/exception/context/comprehension controls; static type/location reconciliation over real Pydantic sources. | Broader descriptors/implicit dispatch, traversal-local context, set/dict accumulation, generator-body binding, async cancellation and higher-order target qualification. Preserve dynamic/native uncertainty. |
| **FB05** Guarded values/solver | In progress | Symbolic guards, bounded solver, scalar arithmetic/overflow, outcome separation, recursive envelope checks and negative controls. | Broader loop/widening/implication qualification, precision under real dispatch and path growth, and independent controls that discriminate currently inconclusive relationships. |
| **FB06** Regions/lineage | In progress | Direct field reconstruction, private allocation identity/content/extents, escape invalidation, finite indexing; new constant provenance and physical member layouts. | General strong/weak updates, deeper aliases/retention, view/copy conditions, interprocedural heap and lifetime/ownership laws; connect constant graphs to typed interpretation. |
| **FB07** Calls/higher order | In progress | Contextual call index, bounded helper closures, cross-unit instances, function-value flow, closure arguments and exact drop targets. | Python higher-order/virtual targets, richer heap/error/resource substitution and specialization. Add constant-table function references to automatic helper-selection products; the current call-index service does not accept the new `mir_memory` lane. |
| **FB08** Witnesses/shrinking | In progress | Contextual witness formats, independent concrete observations, guarded/operator checks, mutation controls, bounded input generation/shrinking and portable replay. | Stateful action harnesses, broader failure/allocation/release oracles, stronger real Python dispatch checks and qualification across later family models. |
| **FB09** Cross-library slice | In progress | All 190 candidates accounted for; Arrow and Pydantic development runs, unchanged-transfer Serde holdout, independent observations and portable/warm reuse. | Satisfy the complete G2 matrix: two discriminating nontrivial guarded relationships per library, two reusable semantic families, callee/field/input-conditioned composition and a shared refinement improving multiple public operations. Freeze broader-population numeric budgets from accepted measurements. |
| **FB10** Protocols/lifecycle | In progress | Python cleanup/suspension fixtures; Rust closure/drop/ABI facts and scalar composition. | Reusable guarded state transitions, ordered/multiplicity-aware traces, completion/error/abandonment/repeated-use witnesses, cancellation/nontermination and a shared protocol model on distinct interfaces. Current may-effect sets cannot prove ordered release protocols. |
| **FB11** Native composition | In progress, preflight | Real PyO3/Arrow extension built and exercised; generated wrappers and native helpers captured; real registration constants, target identities and layouts now retained. | Derive/admit exact Python registration→wrapper→native relationships; compose conversions, errors and ownership with verified summaries; wrong-build/wrong-target binding controls. Inventory Cython/C++ fanout and resolve the plan's conditional C/C++ adapter decision. No binding guarantee is accepted yet. |
| **FB12** Six families | Not started | Existing older semantic packs and new generic interpreter provide inputs, not this package's qualification. | Implement all six typed carrier/law groups with real bindings, independent positives, negatives and unchanged transfer logic across at least two libraries per claimed reusable family; include a reserved holdout binding. See §6. |
| **FB13** Availability/extensions | Not started | Existing declarations, applicability and registry mechanisms are reusable infrastructure. | Compose type/feature/phase/family requirements; derive eliminations/counterfactuals and extension obligations; invalidate missing-built-in conclusions on added candidates. Qualify an ordinary compiled scalar and stateful extension, separately from behavioral laws. |
| **FB14** Cost/ambient/interference | In progress | 169 mapped-owner profiles, ambient/module dependencies, local structural counts and region/order obligations; portable reuse. | Real input-dependent retained-resource relationship, callee/loop bounds and mutation controls for global reads, retained buffers and shared writes; model synchronization uncertainty. Current real-population input-dependent region count is zero. |
| **FB15** Discovery/refinement | Not started | Population summaries and existing graph/FCA/label tools are available. | Reusable behavior searches, source-versus-document disagreement, a checked finding beyond task requirements, false hypotheses/counterexamples, semantic rename/helper-refactoring controls and attributed refinement invalidation. |
| **FB16** Incremental/resources/recovery | In progress | Exact selected prerequisites, zero unchanged producer/summary work, invalidation fixtures, failure prefixes and real predecessor-preserving recovery. | Per-owner/SCC internal counters/checkpoints, resumable bounded specialization, added-candidate/configuration invalidation, solver/budget failure matrix and measured full declared population within frozen budgets. Worker RSS and coordinator memory remain separate. |
| **FB17** Consumers/all tasks | Not started | Earlier active applicability/composition/publication pipeline remains intact. | Reassess all 24 tasks and reversals through new summaries, retain every candidate/frontier, deliver at least one newly derived composed behavioral premise through normal guide publication, and publish independent population/discovery results. |
| **FB18** Terminal delivery | Not started | Historical wheel/portable qualifications and current source tests are retained. | Freeze final completed core/models; pass all G0–G7, fresh wheel installation and source/native-worker-unavailable replay of both new and historical views; reconcile every status/receipt and document limits. Migration itself does not satisfy G7. |

## 4. Measured library results and their limits

The frozen reservation remains **86 Arrow Schema 58.4.0 + 44 Pydantic 2.13.4 + 60 Serde JSON 1.0.149 = 190 candidates**. These are distinct library selections, not the broad historical pilot corpus.

| Population run | Summaries | Interpretation budgets | Unmapped/generated bodies | Interpretation |
| --- | ---: | ---: | ---: | --- |
| Original Arrow development selection | 75 | 4 | 7 | Exact public denominator retained. |
| Pydantic development selection | 31 | 13 | 0 | All summaries conservative; static types do not close dynamic calls. |
| Frozen-model Serde holdout | 46 | 0 | 14 | 13 closed under the selected model, 33 conservative. |
| Combined original reservation | **152** | **17** | **21** | A summary count is not a supported-operation count. |

Arrow's later fuller-helper experiments are separate preserved results. Generic helper selection adds 27 helpers; concrete/callable capture selects 45 helpers and 124 total analyzed owners. It produces 111 summaries and 13 budgets overall, but public-root results are **69 summaries, ten budgets, seven unmapped**. More composition increased path expansion and reduced completed public summaries. The original 75/4 result was not overwritten. The callable experiment took 58.39 seconds and reported 1,889,390,592 bytes of coordinator process-lifetime high-water RSS; that value is not an isolated-stage allocation peak. All 9,803 exported records restored and replayed, with zero new producer work on unchanged requests.

| Independent observation | Result | Remaining qualification |
| --- | --- | --- |
| Arrow conditional fields and wrapper | 64 ordinary Rust invocations; 448 result/field comparisons matched. | Full ownership/layout/configuration and broader behavioral scope. |
| Pydantic whole operators | All 21 observed cases matched after operator-origin refinement. | All 29 guard/order mutation cases were **inconclusive**, not discriminating disagreements. No Pydantic soundness or dispatch closure claim follows. |
| Serde `as_bool` / `as_array` holdout | 32 dimensions matched across 13 values; actual-copy and false-payload controls disagreed where applicable. | Some reversed-guard cases remain inconclusive; pointer identity does not prove lifetime. |
| Function-value compiler fixtures | 40 matches and 40 complemented-output disagreements; admitted witness path additionally checked ten matches/ten disagreements. | Finite exact targets, not general dynamic dispatch. |
| Closure/Rust-call fixtures | 40 matches and 40 complemented-output disagreements across zero/one/two argument and owned/borrowed captures. | Drop facts remain distinct from public release/cancellation protocols. |

The Serde holdout was evaluated against the [pre-heldout freeze](../pilot/intelligence/foundational/pre_heldout_freeze_v1.json), with no transfer change made for its results. That historical claim belongs to that frozen model. Later implementation changes are not automatically held-out-qualified. If Serde results guide new transfer tuning, reserve a new untouched cohort before claiming generalization again.

## 5. Last finished increment: constant-memory facts

See the [constant-memory checkpoint](../pilot/intelligence/foundational/CONSTANT_MEMORY_CHECKPOINT.md) for the precise feature boundary and validation. The new owned wire schema is `library-guides.mir-memory.v1`, selected by `LIBRARY_GUIDES_MIR_MEMORY=1` alongside explicit behavior/instance/callable/lifecycle options. Existing schemas retain their old identities.

The extractor retains evaluated constant operands, initialized bytes and uninitialized padding, pointer provenance, lazy static identities/initializers, exact function targets, instantiated member types, physical field offsets, enum direct/niche tags, logical function signatures and local-type correspondence. Cyclic allocation references use bounded indices; equal bytes do not collapse distinct compiler allocation identities. Concrete generic-body constants use a narrow pinned compiler evaluation bridge; instantiated field normalization uses the exact compiler definition and arguments. Raw compiler handles stay inside the callback.

Retained allocation bounds are 1 MiB per body, 32 MiB per compiler unit, 4,096 nodes and 32,768 pointer entries per body. Type graphs are bounded at 1,024 types, with a 4,096-member limit per inspected nominal/tuple. Constant roots have a 100,000 observation limit. These are acquisition bounds, not a whole-compiler RSS guarantee. Roots outside requested demand remain inventoried with explicit dispositions. The observation scope covers projected assignment/call operands; vtables, symbolic type IDs, generic or unavailable constants and other unsupported cases remain visible.

The new lane supports source extraction, contextual invocation validation, native admission, existing conservative behavior interpretation and portable replay. The interpreter **does not yet load values from these allocation graphs or derive registration/binding semantics from them**. Automatic call indexing/helper closure for memory-held function targets remains future FB07/FB11 work.

The real preflight uses unmodified `pyo3-arrow 0.17.0` classes registered by a small test extension, PyO3 0.28.3 and Arrow Schema 58.4.0. Ordinary Python checks observed `Field.nullable` forwarding both booleans and rejecting six non-bool forms. These observations have not been composed with static summaries into a qualified Python API binding.

The memory capture retained all **2,000 generic bodies plus 32 concrete bodies**, with deeper memory capture selected for 36 bodies. It records 20,883 constant-root observations, 184 allocation nodes, 3,059 retained allocation bytes and 4,754 type-node observations across bodies. The generic `py_methods::ITEMS` initializer alone has 45 allocation nodes/1,299 bytes. The real capture passed the new structural validator. Capture took 24.58 seconds, with 940,544 KiB maximum child RSS reported by `/usr/bin/time -v`. Its full frame artifact is roughly 200 MB and exceeds the existing 128 MiB call-index request ceiling; no ceiling was silently raised and no candidate denominator was truncated.

Two earlier demand attempts failed because exact roots from the first build did not match the crate hash in replay. Definition paths remained unchanged. A fresh generic replay followed by exact roots from that replay succeeded. The underlying cause of the first hash change is unresolved. Keep the failed invocations and do not join their original runtime binary to later compiler facts by name or path alone.

## 6. Gates and the six missing family groups

| Gate | Acceptance state at handover | Principal missing evidence |
| --- | --- | --- |
| G0 | **Accepted** | Preserve its inputs and reservation. |
| G1 | Open | Integrated fact/admission matrix across remaining contexts/constructs and later owned contracts. |
| G2 | Open | Complete reusable three-library/two-family vertical slice, discriminating Python controls and accepted population budgets. |
| G3 | Open | Reusable stateful protocol plus exact real cross-language conversion/error/ownership composition; C/C++ decision. |
| G4 | Open | All six families, availability/extensions, bounded cost/interference and checked task-independent discovery. |
| G5 | Open | Internal owner/SCC recovery, complete invalidation/failure matrix and measured bounded population acceptance. |
| G6 | Open | All 24 tasks/reversals and a new composed premise delivered through the active publication path. |
| G7 | Open | Completed preceding gates and final installed portable delivery. |

All six FB12 groups remain mandatory: (1) collections/relations—length, filter/expand, key multiplicity, unmatched nulls and order; (2) records/schemas—recursive lineage, merge, nullability and metadata precedence/loss; (3) reductions—initialize/update/merge/finalize, empty/null cases and machine-arithmetic partition laws; (4) serialization/framing—domains, frame boundaries, EOF and partial progress; (5) buffers/interchange—layout, validity, device, extent, conditional alias/copy and release; (6) requests/transactions—conditions, retries, failures and local effect ordering with externally assumed atomicity/consistency kept explicit.

Each group needs a real implementation binding, an independent positive and a counterexample. A reusable family must keep its transfer logic unchanged across at least two libraries. Existing approved semantic packs or method-name labels cannot substitute for those checks.

FB17 must retain every original task and reversal. Supported controls are `rust-results`, `python-results`, `pydantic-input`, `reverse-python-overflow`; partial baselines are `python-placement`, `serde-input`, `rust-schema`, `feature-profile`. The remaining 16 gaps are `rust-placement`, `python-representation`, `c-stream`, `rust-enrichment`, `rust-rows`, `python-dataset`, `reverse-rust-placement`, `duplicate-reference`, `provider-limit`, `python-schema`, `custom-scalar`, `custom-aggregate`, `conditional-store`, `flight-ipc`, `async-consistency`, `numpy-dlpack`. None was newly reassessed by this handover.

## 7. Validation at the stop checkpoint

Final validation results and content hashes are recorded in [handover-validation.json](../pilot/intelligence/foundational/handover-validation.json). The full-suite/static/native logs are copied beside that receipt so the evidence can move with the source. The final source freeze is [handover-source-freeze.json](../pilot/intelligence/foundational/handover-source-freeze.json).

| Check | Final result |
| --- | --- |
| Complete tooling pytest suite | **458 passed**, two existing dependency warnings, **211.07 seconds**. Includes the three new real-compiler constant-memory controls. |
| Ruff | Passed on `library_guides tests pilot/intelligence`. |
| Formatting | All 445 files in that scope already formatted. |
| Pyrefly | Zero diagnostics in the project's configured include scope. |
| MIR worker | Pinned-nightly locked build, all-target Clippy with warnings denied, Cargo test and formatting passed. Cargo's Rust harness has zero unit tests; the Python suite provides the real-compiler semantic controls. |
| Wire schemas | All five commands match their owned JSON contracts. The four existing commands are byte-identical to the previous frozen worker. The older instance asset has whitespace differences from emitted JSON; its meaning is unchanged. |
| Original preservation | All 329 files beneath the original `before/` snapshot verified against the preservation receipt. Working-source changes are attributed separately. |

No source changes followed the final full-suite run; subsequent changes are checkpoint documentation and receipts. Final checks do not convert historical witness results into qualification of later analyzer changes.

The final suite is a source-tree checkpoint, **not G7**. In particular, no fresh installed wheel containing this new foundational scope was qualified. The earlier installed-wheel run remains historical. The package's pre-existing two NumPy dependency warnings are reported separately from test failures. An exploratory Ruff invocation over the entire tooling directory previously found five diagnostics in archived handoff example code outside the plan's specified lint scope; those archived files were preserved. No suppressions or exclusion flags were introduced.

## 8. What must travel to the standalone repository

### Source, locks and reusable assets

Preserve the entire owned tooling source topology: `library_guides/`, `tests/` and fixture crates, `native/` owned workers/protocol/bootstrap patches, `rustdoc-helper/`, `pilot/`, `docs/`, approved schema/rule/query/model assets, `pyproject.toml`, `uv.lock`, all independent Cargo locks, and `vendor/`. Preserve the pinned upstream patch files and bootstrap instructions even if upstream checkouts are reacquired later.

The distribution is still named `smartref-library-guides` version 0.2.0, with import package `library_guides` and CLI `library-guides`. Branding strings also remain in the HTTP user agent, managed-runtime ownership label and corrected wheel's local version. Renaming these is migration work; do not accidentally change an existing container's ownership identity or historical record namespaces. The `scikit_mine-1.0.0+smartref.1` wheel under `vendor/` is required by the lock and is not available under that version on public PyPI. Its metadata-only correction and provenance are documented in [vendor/README.md](../vendor/README.md).

The owned Cargo workspaces are standalone, with relative dependencies on the owned protocol and pinned Ruff/Pyrefly source checkouts. Bootstrap verifies the exact upstream revision and retained patches. The MIR worker requires nightly `2026-08-18`, compiler commit `8fa1c96cfd489e4c27654c144ae871ce2c4db6c6`, and matching compiler development/source components. Stable workers were built with Rust 1.98.1. Current binaries embed the selected sysroot/rpath; rebuild them for a new host rather than treating copied binaries as universally relocatable.

Preserve the source-independent guide artifacts under `.codex/skills/datafusion-arrow-rust-guide/` and `.codex/skills/datafusion-pyarrow-guide/` if those consumers move too. The reference skills and deep references under the parent `.codex/skills/` and `docs/library_ref/` are outside the proposed repo root: copy or replace their documentation links deliberately. They are development guidance, not evidence that the package imports SMARTREF runtime code.

### Evidence outside the proposed repository root

Copying `tooling/library_guides/` alone does **not** move the corpora, original source selections, compiler captures, qualification environments, model/runtime caches or all run receipts. Treat the following as separately managed artifacts:

| Artifact group | Location below the foundational run root / external root | Purpose |
| --- | --- | --- |
| Original bytes and checkpoints | `before/`, `preservation.json`, `checkpoints/` | Attribution and reproducible historical source/model versions. |
| Reservation sources | `benchmark_sources/`, `rust-population/`, `pydantic-type-snapshot/` | Exact ordinary-consumer sources, dependency locks and acquisition witnesses. |
| Three-library accepted experiment inputs | `population-portable-v1-arrow-schema/`, `population-portable-v1-pydantic/`, `heldout-serde-portable-v1/` | Preserve complete admitted records and source bytes for acquisition-free replay. |
| Later Arrow experiments | `instances-arrow-qualification-v1/`, `callables-arrow-qualification-v1/` and their corpora/transport/frames | Preserve changed helper-selection outcomes instead of replacing original reservation results. |
| Population profiles | `characterization-arrow-v1/`, `characterization-pydantic-v1/`, `characterization-serde-v1/` | Entire mapped denominator and resource/dependency observations. |
| Failure and resume evidence | `worker-recovery-corpus-v*`, `real-worker-recovery-v*.json`, failure logs | Exact failed predecessors, observed prefixes and successful resumption. |
| Native boundary preflight | `pyo3-boundary-v1/` | Source/lock, original and failed invocations, frames, binary/runtime oracle, demand selections and memory observations. |
| Historical pilot | `/home/paul/smartref/.cache/library-guides-intelligence/pilot-v4/` | Existing analysis corpus, releases and acquisition continuity. |
| Qualification environment | `/home/paul/smartref/.cache/library-guides-implementation/completion-20260912T220757Z/full-environment/` | Exact environment used here; recreate from the retained lock for portability. |

Compiler frame and source-path strings are historical provenance. Do not text-rewrite paths inside content-addressed facts, manifests or invocation receipts to make them resemble the new checkout. Use supported export/import for portable corpus views and explicit path configuration for new acquisition. Unchanged artifacts preserve their original identities; a changed context/producer requires new evidence. Archive restoration alone does not establish that every old analysis model can be recomputed under a later model.

The current main corpus requires a 2,500,000-row scan bound; default direct `Corpus` construction uses 250,000. The frozen foundational populations are separate smaller selections. Resource limits, analysis heads and named releases must remain distinguishable after relocation.

### Environment and path adaptation

This run used Python 3.14.7, attrs 26.1.0, cattrs 26.2.0, PyArrow 25.0.1, DataFusion 54.0.0, LanceDB 0.38.0, Z3 5.1.0.0, Hypothesis 6.168.0, pytest 9.1.1, Ruff 0.16.7 and Pyrefly 1.3.0; see [environment.json](../pilot/intelligence/foundational/environment.json). The native semantic frontends are independently pinned to Ruff 0.16.1 and Pyrefly 1.2.0. Do not conflate checker/runtime/frontend versions.

The source wheel includes portable assets; native builds remain separate. Recreate the tooling environment at the new repo root using its lock and local vendor wheel, without syncing the SMARTREF root environment. Adapt README command prefixes, pilot/run source locations and any environment-selected cache/runtime roots. The GPU embedding service is a separate pre-existing managed runtime and was not restarted or reprovisioned here. A repository move does not authorize changing that service's model/cache/ownership state.

## 9. Resumption order after migration

1. Verify the handover source hashes, vendor wheel, locks and retained export manifests in the new location. Run package static/tests and native canaries there; then exercise existing portable readers. Record relocation as a new context where appropriate.
2. Finish FB01–FB09 acceptance before declaring the foundation complete: prioritize the real Python dispatch/mutation gap, call/path expansion and contextual identity/denominator controls. Freeze explicit broader-population budgets from those accepted measurements.
3. Continue the bounded native-boundary branch from retained PyO3 evidence: implement safe typed constant-graph interpretation and memory-held target indexing; derive a source-backed registration binding; join exact conversion/error/ownership summaries and ordinary runtime evidence from the same build. Resolve C/C++ fanout/prerequisites under FB11's documented trigger.
4. Implement ordered stateful protocol characterization and witnesses (FB10), then all six semantic families (FB12), availability/extensions (FB13), resource/interference completion (FB14) and discovery/refinement (FB15). Harden owner/SCC recovery and population execution in FB16 before large runs.
5. Reassess all 24 tasks and reversals through the normal pipeline (FB17), then perform final installed delivery and all gate reconciliation (FB18). Preserve any remaining library/external obligations in guides even when the tooling package itself becomes qualified.

The existing bounded qualification entry points are `python -m pilot.intelligence.foundational.qualify_calls --help` and `python -m pilot.intelligence.foundational.qualify_characterization --help`, run from the tooling/new-repo root with its selected environment. Both require explicit retained archive, behavior/profile selection and fresh output paths. There is no single implemented command that completes or certifies the entire foundational plan. Many experimental producers and receipts currently live in the run cache; preserve them and consolidate reproducible drivers as implementation proceeds.

The stop condition for this handover is the finished bounded increment, verified source checkpoint, consistent status documents and no task-owned process. It is not completion of the foundational plan or execution of the repository migration.
