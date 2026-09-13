# Constant-memory fact checkpoint

The bounded constant-memory acquisition increment is finished. Implementation is paused at the user's request for a standalone-repository handover. This is progress on FB01/FB03/FB06/FB07 and a real FB11 preflight; it does not accept those packages or G1–G7. See the [comprehensive status and migration handover](../../../docs/design/foundational_behavior_characterization_status_and_repo_handover_2026-09-13.md).

## Contract and implementation

The separate `library-guides.mir-memory.v1` wire contract extends the lifecycle lane. Enable `LIBRARY_GUIDES_MIR_MEMORY=1` with explicit behavior, instance, callable and lifecycle options. Use source lane `mir_memory`, owned asset `mir-memory.v1.schema.json`, and worker command `memory-schema`. The constant-memory option is part of the original compiler invocation identity. Existing schema command output is byte-identical to the preceding frozen worker; the older instance asset uses different whitespace but represents the same JSON schema. Default-off options retain their previous serialization.

The owned implementation is in `native/mir-facts/src/memory.rs` and `memory_types.rs`, with collection and invocation plumbing in `instances.rs` and `main.rs`. `library_guides/analyses/behavior/mir_memory.py` validates the resulting graph and joins captured function identities to the exact compiler body catalog. Source extraction, native admission, behavior input validation and portable replay accept the new lane.

Facts retain:

- The exact projected assignment/call constant-operand denominator, program points, evaluation states and root types. Demand selection deepens selected owners while preserving generic observations.
- Initialized bytes and uninitialized padding, alignment, mutability and pointer provenance. Compiler allocation IDs become local graph indices; equal bytes do not merge distinct allocation identities. Shared and cyclic references retain graph identity.
- Lazy static identities and initializers, exact function definition/instance targets, captured or unresolved selections, and explicit foreign/unsupported outcomes.
- Instantiated nominal members, local type correspondence, physical sizes/alignments/offsets, enum direct/niche tags, array/tuple structure and logical function signatures. These do not establish complete physical calling conventions, runtime lifetime or alias validity.

Concrete constants in generic definition bodies use a narrow pinned compiler evaluation bridge; member normalization uses the exact compiler definition and substitutions. Compiler handles remain inside the callback. Generic, unavailable and unsupported evaluations retain frontiers. Vtables and symbolic type IDs remain unresolved. Closure/coroutine physical member reconstruction is incomplete.

Retained allocation bytes are bounded at 1 MiB per body and 32 MiB per compiler unit. Per-body limits are 4,096 nodes, 32,768 pointer entries, 100,000 observed constant roots and 1,024 type nodes; inspected nominal/tuple members are bounded at 4,096. The public compiler API may materialize an allocation before these retention checks, so the limits are not a total compiler-memory guarantee. Complete generic MIR, type observations, frame transport and source bounds are separate denominators.

The validator rejects omitted operand/local observations, inconsistent selection/options, invalid graph/type indices, malformed initialized bytes and pointer ranges, contradictory retained-byte totals and mismatched exact function identities. It preserves unavailable facts rather than fabricating values.

## Qualification

Three real-compiler tests in `tests/test_behavior_constant_memory.py` passed in the final full suite:

1. An independently compiled ordinary Rust consumer exercises a constant table with byte labels, generic `u16` fields and two callbacks. Observed size, alignment, field offsets, label/tag values and eight callback results match captured facts; enum niche layout is retained.
2. Equal-byte statics preserve two identities and repeated aliases preserve one identity. A constant larger than the per-body byte allowance produces an explicit budget outcome. Omitted roots/locals, invalid pointer offsets, mutated function identity and disabled invocation options are rejected.
3. Source-backed admission, conservative behavior interpretation, export/import on the analysis head, exact replay and unchanged reuse pass through the normal tooling path.

The complete tooling suite passed **458 tests, with two existing dependency warnings, in 211.07 seconds**. Ruff and formatting passed on `library_guides tests pilot/intelligence` (445 Python files); configured Pyrefly checking reported zero diagnostics. The pinned MIR worker build, all-target Clippy with warnings denied, formatting and Cargo test passed. The Rust test harness contains zero unit tests; behavioral evidence comes from the real-compiler Python controls above. Commands, logs and hashes are in [handover-validation.json](handover-validation.json). These are current source-tree checks, not final installed-wheel delivery or held-out acceptance of every later analyzer change.

## Real PyO3 preflight

The retained run is `/home/paul/smartref/.cache/library-guides-foundational/20260913T101230Z/pyo3-boundary-v1/`. Its small extension registers unmodified production `pyo3-arrow 0.17.0` classes with PyO3 0.28.3 and Arrow Schema 58.4.0. An ordinary Python oracle observes both `Field.nullable` booleans and TypeError for six non-bool forms. This is runtime preflight evidence, not a derived binding proof.

During handover finalization, an external relocation moved this run to `/home/paul/.cache/library-deep-enrichment/foundational/20260913T101230Z/pyo3-boundary-v1/`. The receipt records the observed location separately from original provenance paths; the moved environment and successor repository have not been requalified here.

The new memory capture completed with all 2,000 generic bodies and 32 concrete bodies. Deeper memory capture selected 36 bodies. The complete denominator has 20,883 constant-root observations, 184 allocation nodes, 3,059 retained allocation bytes and 4,754 type-node observations. The generic `py_methods::ITEMS` initializer retains 45 allocation nodes and 1,299 bytes. All 2,032 records passed structural memory validation and the original invocation option check. The full real-library function-target/body join and normal native admission have not been claimed.

`/usr/bin/time -v` reports 24.58 seconds elapsed and 940,544 KiB maximum child RSS. The frame file is **207,276,482 bytes**, above the existing 128 MiB call-index request ceiling. The bounded retained allocation payload is only one contributor to this full artifact. No limit was raised, no generic population was truncated, and no automatic call-index support for this lane was added.

Two earlier exact-demand attempts failed because roots selected from the original build did not match the replay's crate hash, despite unchanged definition paths. A fresh generic replay followed by demand from that replay succeeded. The first hash-change cause remains unresolved. Preserve failed commands/frames and do not join the first runtime binary to later facts merely by symbol name. The final handover receipt hashes the preflight reports and original files; larger frames, binaries, build targets and original dependency context remain external artifacts listed in the migration handover.

## Remaining work

The interpreter does not yet load values from constant allocation graphs. Memory-held functions are not yet integrated into the native call index or automatic helper closure. Typed registration-table decoding, exact Python registration bindings and conversion/error/ownership composition remain FB07/FB11 work. Physical layouts and names alone do not establish those semantics. Native request scaling, stronger generic/configuration context qualification, stateful/ordered effects and final real-library positive/counterexample witnesses remain open. The current capture supplies reusable fundamental facts for that work; it does not substitute for it.
