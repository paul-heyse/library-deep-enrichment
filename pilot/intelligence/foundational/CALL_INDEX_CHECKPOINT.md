# Contextual call indexing and helper selection checkpoint

FB02/FB07 now include a reusable native call index and a bounded helper-selection stage. Package and gate acceptance remain open. These additions use captured compiler identities; public symbol names do not determine target selection.

`CallIndexRequest` selects complete native artifacts with independent fact and byte bounds. `CallIndex` retains every captured owner and every explicit MIR call terminator, including unresolved, intrinsic and virtual dispatch. It retains original definition identities, compilation contexts, body phases, callsites and observed substitution positions/scalars. Complete typed substitutions remain in the referenced native records; type-projection fingerprints are not semantic type equality. Missing native owners or call observations fail validation. Indexing currently accepts the pinned generic-definition MIR execution schema; unsupported schemas cannot enter by fallback.

`CallClosureRequest` selects explicit roots from that finite catalog. Deterministic breadth-first traversal follows only exact item targets with one captured body. Missing bodies, multiple captured bodies, unresolved dispatch, depth limits, owner limits and selected-byte limits remain separate dispositions. Observed generic substitutions are retained but are not applied to generic bodies. Explicit calls do not account for every function reference, drop glue, vtable or executable instance.

The selection stage emits an ordinary `BehaviorRequest` and owns it together with the `CallClosure`. Changing the underlying index withdraws this generated request and its dependent programs/summaries. This does not weaken the existing request contract or claim whole-program effect closure. Both stages use the existing supervisor, exact dependency selection, admission replay and portable archive mechanism.

## Executable controls

The pinned-compiler fixture starts from a public wrapper alone. Exact cross-unit lookup selects its private helper, and the existing interpreter carries the helper's guarded field result into the wrapper. Same-name/wrong-build targets remain missing. Adding the correct captured body withdraws the earlier generated request and summaries. Zero-depth and one-owner requests retain budget dispositions and the original root. Fabricated index omissions and helper lists are rejected. Portable restoration replays exactly, and unchanged requests launch no analytical producer.

Twelve call-index, MIR, callable-population and stage-input regression controls pass in 25.41 seconds (`call-index-regression-v2.log`). The driver and characterization driver both pass explicit Pyrefly checks. No compiler binary or native schema changed in this increment.

## Arrow development experiment

`python -m pilot.intelligence.foundational.qualify_calls` imports a retained archive into a new corpus and records complete before/after owner outcomes. This run used the original Arrow development archive, all 79 mapped reserved roots, depth 12 and a 128-owner selection bound. The original 86-candidate public reservation, including seven unresolved source mappings, remains unchanged.

Run directory: `/home/paul/smartref/.cache/library-guides-foundational/20260913T101230Z/call-expansion-arrow-v1`. `report.json` contains the complete index, selected calls, roots/helpers, request, timings and before/after dispositions.

- Complete index: **389 captured bodies and 2,179 explicit calls**.
- Selection: **79 roots plus 27 helpers**, 106 owners total.
- Selected-owner callsites: 109 target captured generic bodies; 367 have no body in the finite catalog; 52 have unresolved dispatch.
- Interpretation: 93 summaries and 13 explicit budget outcomes across all selected owners.
- Original public roots: **69 summaries and ten budget outcomes**, compared with 75 summaries and four budget outcomes in the original smaller request. Fourteen roots remain closed under the existing model in both requests. Twenty root outcomes or summary metrics change.
- Index / selection / interpretation stage times: 2.402 / 1.620 / 8.871 seconds. End-to-end qualification, including archive restoration: 52.205 seconds. Coordinator process-lifetime RSS high-water: 1,595,207,680 bytes.
- All 9,204 portable records restore; index, selection and owner outcomes replay exactly. Unchanged index, selection and behavior requests launch zero new producers.

Result head: `3a01b8669105113bba8f4189b7eae04f0a4bb9165da0601d4fb840ca4f4a17d1`. The original Arrow corpus and its 75 summaries were not replaced. No Serde transfer refinement or new holdout claim follows from this development experiment.

## Consequence for remaining implementation

Selecting more exact helpers exposes more paths and effects, and can exhaust a previously successful public-owner request. The increase in explicit budget outcomes is a measured limitation, not a characterization gain. Stronger bounded interprocedural composition needs control of path partitions and reusable specialized summaries while preserving unknown/error outcomes and exact resource accounting. Concrete instance bodies are also needed where retained const/type substitutions affect behavior. The pinned compiler exposes `Instance::body()` for this purpose, but instance acquisition, identity, phase, selection limits and old-schema compatibility still require implementation and qualification. Broad effect, lifecycle, native-boundary and family closure remain open.
