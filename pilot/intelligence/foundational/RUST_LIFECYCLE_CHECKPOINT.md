# Rust closure, calling convention and drop-glue checkpoint

FB01/FB02/FB03/FB07/FB08/FB10 now include additional compiler facts and guarded composition. The original 190-candidate reservation, historical corpora and G0–G7 acceptance requirements remain unchanged. This fixture qualification does not complete lifecycle or native-boundary acceptance.

## Fundamental facts and bounded acquisition

The separate opt-in `library-guides.mir-lifecycle.v1` format requires `LIBRARY_GUIDES_MIR_LIFECYCLE=1`, callable capture, behavior capture and explicit instance budgets. Its schema command is `lifecycle-schema`; the source lane is `mir_lifecycle` and the packaged schema is `mir-lifecycle.v1.schema.json`. Historical generic, instance and callable schema outputs match the preceding frozen worker exactly.

Each body retains its compiler-declared spread argument and one function-signature ABI observation per original call. Every closure aggregate retains its exact contextual definition, substitutions and capture count. Every original drop terminator retains its place/type, resolved drop-glue identity or explicit generic frontier, native selection disposition and compiler empty-shim observation. Non-foreign compiler shims now share the existing finite instance selection budget. Drop glue is resolved by `Instance::resolve_drop_in_place`; generated closure invocation shims and their actual concrete bodies remain distinct identities. No compiler handle leaves the callback.

The first closure probe exposed a transfer error that simple arity matching would miss: a closure receives a packed tuple at a Rust-call boundary but its body may declare individual argument locals. Retaining `Body::spread_arg` and operand `FnSig` facts permits one shared normalization: Rust-call arguments expand by their exact tuple type, and spread-argument bodies reconstruct their local tuple on entry. Zero-, one- and two-argument cases use the same rule. Captured body joins reject incompatible expanded tuple shapes. Unit return types establish the unique unit value without reading an uninitialized return local.

`facts.mir_sources.witnesses` derives the complete source-byte witness selection from validated compiler frames. It checks per-path digest consistency, actual source bytes and finite source/stream budgets. This is necessary when generated helpers or standard-library bodies refer to files beyond the original package source. The normal source pipeline then retains those bytes and their acquisition paths before corpus admission.

## Analysis and automatic selection

MIR projection v4 composes verified drop targets through the existing call interpreter. It retains distinct drop-entry and successful-drop-return events and explicit unwind edges. Missing or unresolved glue remains opaque. An empty shim observation is not a public release guarantee, and a mutation through an unresolved reference remains a may-alias write.

Native call index v4 validates every captured body, signature, callable reference, closure aggregate and drop use against the complete original catalog. Helper selection v4 follows calls, callable operands and drop targets under the existing independent depth/owner/byte limits. The new `lifecycle_closures` family records drop selections separately from ordinary calls and callable references; existing record families retain their historical schemas. Selected bodies feed the ordinary behavior workflow and guarded transfer v3.

## Executable checks

The real compiler fixture covers owned and borrowed captures, an ordinary wrapper around a borrowed closure, zero- and two-argument closure calls, a custom `Drop` implementation and explicit disposal through the standard library. A separate ordinary compiler invocation executes four guarded closure interfaces at two flags and five byte inputs. All 40 observed results match derived summaries; all 40 complemented output mutations disagree. Automatic selection finds all required closure/shim/drop bodies without a manually assembled helper list. The disposal summary retains drop entry/return and the unresolved mutation obligation.

Missing drop or ABI denominators, a non-tuple spread local, a wrong Rust-call tuple shape and a wrong ABI at a captured body boundary are rejected. The complete index, selection, behavior and source witnesses survive portable export/import; unchanged restored stages reuse their receipts and exact summaries. Ten lifecycle/callable/instance/call-index controls pass in 43.90 seconds (`lifecycle-tests-v3.log`).

The full tooling suite passes **454 tests in 209.26 seconds**, with the same two pre-existing dependency warnings (`lifecycle-full-suite.log`). Plan-scope Ruff/format and Pyrefly pass (`lifecycle-final-ruff-v2.log`, `lifecycle-final-format-v2.log`, `lifecycle-final-pyrefly-v1.log`). Pinned MIR build, Clippy, Cargo test and formatting pass; Cargo contains zero unit tests, so native semantics are checked by the actual compiler fixtures. An extra Ruff invocation over the entire tooling directory found five pre-existing diagnostics in the archived handoff example outside the plan's check scope; its log is retained and no exclusions or suppressions were introduced.

## Remaining scope

The lifecycle capture has not yet been evaluated against the real reserved library population. These checks do not establish release under cancellation/nontermination, callback cleanup semantics, protocol reuse or a real native Python boundary. Ordered event multiplicity and stateful repeated-consumption qualification remain separate from the existing may-effect summaries. PyO3 registration, constant-allocation provenance, generated wrapper/native-target composition, broader family models, discovery, resource qualification, task reassessment and installed delivery remain required.
