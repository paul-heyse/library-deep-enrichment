# Foundational behavior characterization — implementation plan v1

Date: 2026-09-13. State: **implementation in progress; G0 baseline/reservation accepted, G1–G7 open**.

Execution progress and remaining obligations: [foundational status](../pilot/intelligence/foundational/STATUS.md). The acceptance scope below remains unchanged.

Design authority: [foundational design assessment](foundational_behavior_characterization_design_assessment_2026-09-13.md). Execution ledger: [work packages and dependencies](foundational_behavior_characterization_implementation_plan_v1_2026-09-13.json). The Markdown defines scope and acceptance; the JSON mirrors the dependency graph and records execution status. It is a planning artifact, not a new runtime or admission authority.

## 1. Outcome and completion boundary

Implement a reusable pipeline that derives guarded behavioral summaries from contextual executable facts, composes them across calls and qualified language boundaries, and exposes them through the existing library-guide decision and publication machinery.

The completed pipeline must describe conditional output/value relationships, field and buffer lineage, effects, lifecycle transitions, availability and explicit unknowns. It must support reusable collection/schema/reduction/serialization/buffer/request models, generate challenging witnesses, and discover behavior outside the retained task questions. Input-sensitive cost, ambient-state dependence and concurrency obligations are included at a bounded analysis depth.

Completion requires all mandatory work packages and terminal gates below. It does **not** require declaring all 24 retained tasks supported. The current baseline is four supported, four partial and 16 gaps; a remaining gap is acceptable only when its actual unresolved obligation is attributed and the applicable foundational work and acceptance cases have been completed. An all-unknown analyzer, a bigger inventory, or unchanged task results without demonstrated new behavioral characterization cannot satisfy this plan.

The first milestone is a working Rust/Python vertical slice across at least three libraries and two semantic families. It is followed by lifecycle/boundary analysis, semantic families, discovery and consumer integration. Implementing the first milestone alone does not complete the plan.

### Preservation and baseline

The assessment and its [evidence record](foundational_behavior_characterization_evidence_2026-09-13.json) still match. All 270 files in core freeze `89cb8d1665f7d4e06a2cc48b80a19a936679aa1617500a4c36d8ad3444343b3e` were verified unchanged during planning. The entire tooling directory is currently untracked in the shared checkout; Git status alone cannot attribute later changes. Preserve exact file snapshots, existing corpora, releases and concurrent work before execution.

The [completion ledger](../pilot/intelligence/COMPLETION.md) records historical qualification, including 315 distinct passing tests. These checks were not rerun for planning. Establish a fresh executable baseline in FB00; do not convert historical results into current-run receipts.

## 2. Implementation decisions

1. **Extend the active architecture.** Use the existing corpus coordinator, typed records, checked derivation, stage ownership, portable closure and publication paths. Native producers remain standalone tooling workers. No dependency on the SMARTREF application runtime or its code-intelligence daemon is introduced.
2. **Keep frontend semantics explicit.** Rust and Python feed an owned execution representation with language-specific extensions. Rust unwind is not Python exception routing; a Python type candidate is not an exact native call target.
3. **Put general interpretation in pure analysis modules initially.** Reuse the existing Python analysis service and graph/constraint libraries. Move a measured hotspot into a qualified Rust worker only when evidence justifies the additional boundary. No new graph store, mandatory GPU service or general-purpose compiler platform is required.
4. **Separate semantics from evidence status.** Abstract values/effects are distinct from body-derived, documented, witnessed, assumed or unresolved evidence. Unknown effects are not empty effects. Solver `unknown`, failed extraction and exhausted budgets never imply absence.
5. **Model conditions and relationships.** Keep guarded input/output/region/state relationships beneath capability labels. Family bindings require exact implementation evidence; identifiers, documentation phrases and clustering can nominate but cannot prove behavior.
6. **Preserve contextual identity.** Join source, declarations, compiler units, executable instances and native bindings using actual context. Never use display names or raw rustdoc IDs as cross-artifact identity.
7. **Develop qualification alongside semantics.** Each transfer or frontend increment includes independent behavioral controls, failure cases and finite budgets. Do not postpone correctness testing until the 24-task reassessment.
8. **Keep external obligations visible.** Backend consistency, actual input uniqueness, device synchronization and deployment requirements remain conditional unless separately evidenced.

The provider choices and constraints remain those investigated by the [code-facts-lib-ref](../../../.codex/skills/code-facts-lib-ref/SKILL.md) and [rust-api-extraction-ref](../../../.codex/skills/rust-api-extraction-ref/SKILL.md) navigators. Recheck the pinned API before implementation; the assessment's source-backed capability inventory is the starting point, not a reason to upgrade dependencies.

## 3. Work packages and dependency order

Every package starts `not_started`. Dependencies below are completion dependencies; code and fixtures may be prepared earlier against agreed contracts, but milestone acceptance cannot bypass required predecessor evidence. A package completes against its own acceptance criteria in §4. The last column names the milestone that consumes its evidence; it is not an additional prerequisite that would prevent dependent packages from starting before the aggregate milestone passes. Package IDs are execution units, not separate stores or mandatory processes.

| ID | Work package | Depends on | Evidence contributes to |
| --- | --- | --- | --- |
| FB00 | Baseline, coverage denominator and evaluation reservation | — | G0 |
| FB01 | Typed executable/summary contracts and admission | FB00 | G1 |
| FB02 | Context, public reachability and callable identity | FB01 | G1 |
| FB03 | Rust executable projection | FB01, FB02 | G1 |
| FB04 | Python executable projection and type reconciliation | FB01, FB02 | G1 |
| FB05 | Guarded value analysis and solver boundary | FB03, FB04 | G2 |
| FB06 | Fields, regions, aliasing and representation lineage | FB05 | G2 |
| FB07 | Interprocedural and higher-order summaries | FB02, FB06 | G2 |
| FB08 | Witness generation, independent oracles and shrinking | FB01, FB05 | G2 |
| FB09 | First cross-library vertical-slice qualification | FB07, FB08 | G2 |
| FB10 | Protocols, deferred execution, cleanup and failures | FB09 | G3 |
| FB11 | Native binding and conversion composition | FB09 | G3 |
| FB12 | Reusable semantic-family models and laws | FB07, FB10, FB11 | G4 |
| FB13 | Availability, placement and extension obligations | FB02, FB12 | G4 |
| FB14 | Cost, ambient dependence and interference | FB07, FB10 | G4 |
| FB15 | Population characterization, discovery and refinement | FB08, FB12, FB14 | G4 |
| FB16 | Incremental execution, resource control and recovery | FB09 | G5 |
| FB17 | Consumer integration and retained-task reassessment | FB11, FB13, FB15, FB16 | G6 |
| FB18 | Terminal qualification, portable delivery and handover | FB17 | G7 |

Suggested sequence:

- **Foundation:** FB00–FB04, followed by FB05–FB08 and FB09.
- **Broader characterization:** start FB16 hardening after FB09; complete FB10/FB11, then FB12–FB15. Small bounded experiments can precede FB16 completion; large population runs require G5.
- **Delivery:** FB17 and FB18, retaining all preceding gate evidence.

Rust/Python projection work has independent implementation surfaces after FB01/FB02. Protocol/binding work has similar independence after FB09. This describes dependency freedom; it does not require multiple agents or concurrent heavy compiler/test processes.

## 4. Detailed work packages

### FB00 — Baseline, coverage denominator and evaluation reservation

**Actions.** Snapshot task-relevant files and the current manifest/release identities; record runtime, native toolchain and dependency selections without modifying the root environment. Establish fresh tooling checks and distinguish pre-existing failures. Inventory existing emitted facts, normalized fields and analyzed semantics by construct and language. Classify deficiencies as missing observation, lossy normalization, missing derivation or external obligation.

Define a finite characterization population from public reachability and structural criteria, independent of task IDs. Record every selected owner, missing body, configuration and native boundary. Reserve development and held-out populations before tuning transfers. Select at least three source-available libraries across Rust/Python and two semantic families; reserve at least one library from transfer development. Freeze exact selections and independently specified expected relations for the vertical slice.

**Outputs.** Baseline receipt; source/construct coverage matrix; benchmark manifest with selection rule, immutable splits and explicit unknown cases; initial cost/budget policy. Store new execution evidence under proposed `pilot/intelligence/foundational/`, with disposable run data under a uniquely named cache directory.

**Acceptance.** Every selected owner has an explicit disposition. There is no silent denominator reduction after a failed extraction. Corpus heads and historical artifacts are preserved. Held-out selection changes require an attributed reason and a new split before further tuning.

### FB01 — Typed executable/summary contracts and admission

**Actions.** Implement owned records for contextual executable facts, guarded summaries, coverage frontiers and derivation dependencies. Represent program points, typed value expressions, control edges, accesses/regions, call bindings, deferred execution, availability constraints and boundary bindings. Define typed language-specific payloads and version gates.

Specify abstract bottom/top, outcome kinds, may/must interpretation, assumptions, target-set completeness, precision loss and analysis termination. Add request budgets and deterministic canonicalization. Admit results through the existing coordinator with exact read sets, model identities and replay/validation; include new families in portable closure and historical schema handling. Do not reinterpret old `SourceAnalysis` records as stronger summaries.

**Implementation surface.** Extend [analysis contracts](../library_guides/analyses/fabric_contracts.py), [schemas](../library_guides/analyses/fabric_schemas.py), [catalog](../library_guides/corpus/catalog.py), [analysis service](../library_guides/analyses/fabric.py), [validation](../library_guides/corpus/validation.py) and their reference/invalidation integration. Proposed cohesive modules under `library_guides/analyses/behavior/` may hold the new pure model; that directory does not yet exist.

**Acceptance.** Malformed guards, cross-context identities, unsupported schema versions, omitted prerequisites and fabricated summaries are rejected. Unknown, unreachable, interrupted and unsupported cases remain distinct through encode/decode, admission and export/import. An old archive retains its old meaning.

### FB02 — Context, public reachability and callable identity

**Actions.** Join existing Cargo resolution, compiler-unit receipts, rustdoc public routes and MIR definition/instance identities. Preserve declared/requested/resolved features separately. Add exact generic substitutions and cross-unit target links where evidence supports them; keep unresolved candidates and finite configuration scopes explicit.

For Python, join exact source/import context, declaration locations and typed call candidates without equating stubs with executable bodies. Define stable contextual identity across regenerated local numbering. Derive a public candidate denominator through re-exports and registry membership, including membership dependencies that can invalidate a negative result.

**Implementation surface.** [Rust declaration helper](../rustdoc-helper/src/declarations.rs), [Cargo messages](../rustdoc-helper/src/cargo_messages.rs), [MIR wrapper](../native/mir-facts/src/main.rs), [corpus identities](../library_guides/corpus/identities.py), [Python reconciliation](../library_guides/analyses/python_fabric.py), [universe analysis](../library_guides/analyses/universes.py).

**Acceptance.** Re-exports and duplicate package versions resolve contextually; renumbering preserves semantic identity; distinct feature/unit contexts remain distinct. An added candidate, target or configuration invalidates an affected closed judgment. No all-feature or whole-program completeness claim follows from a finite catalog.

### FB03 — Rust executable projection

**Actions.** Audit each retained MIR variant against the new contract. Reuse existing literals, constructor variants, place projections, guards and unwind edges. Replace behavior-relevant debug strings with typed operator payloads. Retain scalar semantics, const-generic values where available, source/expansion mappings, access kinds and supported instance substitutions.

Represent closure captures, deferred bodies, drop/shim and indirect/virtual uses with exact or candidate targets. Keep definition bodies separate from concrete instances and preserve compiler body phase. Add private compiler enrichment only for a named unresolved analysis requirement; unsupported regions, binders, aliases or executable uses remain explicit frontiers.

**Implementation surface.** [MIR projection](../native/mir-facts/src/projection.rs), [values](../native/mir-facts/src/values.rs), worker protocol/schema assets and native normalization/validation. Preserve the existing nightly and compiler isolation unless a recorded compatibility need requires a change.

**Acceptance.** Real pinned-compiler fixtures cover branches, variants, projected reads/writes, arithmetic modes, calls, unwind and deferred/drop relationships. Every encountered construct is either modeled or attributed as unsupported. Mutation controls verify source and context fidelity; a complete producer receipt does not imply complete behavioral semantics.

### FB04 — Python executable projection and type reconciliation

**Actions.** Build an evaluated operation/CFG projection on the populated Ruff traversal, incorporating Pyrefly types/candidates. Do not adopt the pinned Ruff `build_cfg` as complete: its major branch, loop and exception cases are unimplemented.

Implement sequential evaluation, short-circuiting, branches/match, loops and break/continue, calls/returns, exception routing, `finally`, context managers, comprehensions, generator/async suspension and deferred bodies. Represent implicit calls from operators, attributes/descriptors, iteration and context entry. Unsupported dynamic features must create explicit call/effect frontiers.

Keep declared, computed, expected and narrowed types separate. Resolve retained TSP declaration locations and substitutions where possible; use existing subtype/member APIs for bounded obligations. If qualified-name resolution is used, validate input and supervise its failure-prone provider boundary. Capture traversal-local exception/context state at the relevant operation.

**Implementation surface.** [Ruff facade](../native/source-facts/src/lexical.rs), owned source-facts modules/patch, [Pyrefly worker](../native/python-semantics/src/main.rs), [targeted projection](../native/python-semantics/src/targeted.rs), [Python analysis service](../library_guides/analyses/python_fabric.py).

**Acceptance.** Executed trace fixtures distinguish evaluation order, normal/error/finally cleanup, loops and suspension. Branch/exception edges cannot silently disappear. An opaque descriptor, native call or `Any`-dependent dispatch prevents an unjustified universal claim. Complete coverage of arbitrary Python runtime behavior is not asserted.

### FB05 — Guarded value analysis and solver boundary

**Actions.** Implement a language-aware abstract interpreter with constant/boolean/variant/optional domains, intervals or symbolic lengths, argument/configuration provenance and bounded relational predicates. Refine state on edge guards; retain outcome clauses for normal, error and suspended results. Model integer width/overflow and relevant floating-point semantics explicitly.

Use finite-height domains or widening with a checked post-fixed-point condition. Bound path partitions, solver calls and specializations. Define how unsupported transfers conservatively lose precision. Z3 is a bounded feasibility/implication helper, not the interpreter or an authority over unencoded behavior.

**Implementation surface.** New pure modules alongside [flow analysis](../library_guides/analyses/flow.py), integrated through the active analysis service. Existing origin-only summaries remain available with their existing model identity.

**Acceptance.** Independent concrete executions lie within the modeled outcomes for the fixture domain. Guard reversal changes the corresponding summary clauses. Infeasible, unknown, timeout and widened cases remain distinct. Tests include loops, overflow, null/variant splits, exceptional exits and deliberate unsound-transfer mutations.

### FB06 — Fields, regions, aliasing and representation lineage

**Actions.** Introduce local/field/allocation-site locations, bounded index partitions, region extents and owner/escape relationships. Implement strong updates only for proven unique locations; otherwise weak updates. Track field forwarding, reconstruction, copying, aliasing and retention independently. Separate handle movement, descriptor allocation, reference counting and payload copy.

Apply unknown-call effects to reachable regions under explicit separation assumptions. Preserve value/guard relationships across memory operations. Emit conditional layout, null representation and metadata lineage facts without declaring semantic metadata validity.

**Implementation surface.** New memory/lineage domains and transfers consuming FB03/FB04 facts; integration with [flow](../library_guides/analyses/flow.py) and [effects](../library_guides/analyses/effects.py).

**Acceptance.** Alias/non-alias controls distinguish strong and weak update; nested-field reconstruction identifies omitted fields; guarded view/copy cases separate payload reuse from new allocation. Opaque mutation cannot yield a preservation guarantee. Address equality alone cannot pass an ownership/lifetime obligation.

### FB07 — Interprocedural and higher-order summaries

**Actions.** Substitute values, regions, guards and callback contracts through exact contextual calls. Compute recursive SCC summaries to a convergent abstract result. Propagate return/error, heap, resource and effect transformations across compilation units. Support observed generic instances, function-pointer candidates, closures and virtual targets with explicit target-set completeness.

Bound specialization and recursion precision; cache summaries by context, abstract inputs and model/dependency identity. A missing or open callee yields a frontier and conservative transfer. A callback precondition stays a precondition until discharged. Record full dependency closure without creating circular proof support.

**Implementation surface.** [Effects fixed point](../library_guides/analyses/effects.py), new summary/call modules, contextual joins and [active service](../library_guides/analyses/fabric.py). Replace the one-artifact request limitation through a new validated request contract, not by weakening old records' meaning.

**Acceptance.** Helper extraction and public wrapping preserve qualified relationships; changed callee behavior invalidates callers. Recursion converges or reports a bounded failure. An added virtual/callback target removes unsupported closure claims. At least one real cross-unit composition carries field/guard information through a callee.

### FB08 — Witness generation, independent oracles and shrinking

**Actions.** Build a bounded harness generator from admitted types, constructor/invocation contracts, guard clauses and state transitions. Start with values/regions; extend action vocabularies as protocols and families arrive. Use Hypothesis for input/action generation and shrinking. Record exact programs, contexts, seeds, observations, budgets and minimized counterexamples.

Separate static hypotheses from observations and family laws. Supply independent executable reference models, relational/metamorphic checks or instrumented allocation/release traces. A witness generator must not simply call the same abstract transfer as its oracle. Native compilation and execution are separate evidence outcomes.

**Implementation surface.** Extend [semantic experiments](../library_guides/semantics/experiments.py), [composition programs](../library_guides/semantics/composition_programs.py), existing witness contracts and new qualification fixtures.

**Acceptance.** Guard alternatives and negative controls are exercised; a deliberately faulty transfer produces a reproducible minimized disagreement. A passing finite witness cannot automatically approve unrelated operations. Unreachable harnesses, failed compilation, timeouts and inconclusive observations remain visible. Optional Kani/Loom integration is not necessary for this package.

### FB09 — First cross-library vertical-slice qualification

**Actions.** Run the frozen FB00 selection through extraction/admission, guarded value/field analysis, direct-call composition, witness checks and portable export/restore. Include constructors, wrappers and conditional transforms. Demonstrate both Rust and Python paths and a held-out library without per-function semantic overrides or a new task-specific analysis.

**Acceptance.** G2 requires at least three libraries and two semantic families, with at least two nontrivial independently checked guarded relationships per library. At least one relationship must propagate through a helper/callee; the cohort must include both field-lineage and input-conditioned behavior. Publish results for the entire selection, including unknowns. A shared transfer refinement must improve more than one public operation. Raw row count or unguarded constant return detection is insufficient.

Record first measured costs and freeze numeric performance budgets for later population qualification. If held-out results drive a transfer change, that cohort becomes development evidence and a new untouched holdout is required for the generalization claim. This is a milestone gate, not terminal completion.

### FB10 — Protocols, deferred execution, cleanup and failures

**Actions.** Infer guarded state-transition candidates from fields, control flow and resource events. Represent construction, configuration, activation, iteration/poll, suspension, completion, error, cancellation and release. Summarize retry multiplicity, partial reads/writes, EOF requirements and owner consumption.

Integrate Rust drop/unwind and Python exception/finally/context-manager semantics, including cleanup that itself fails or suppresses an error. Preserve callbacks and external cleanup as obligations when unresolved. State-machine structure can be inferred; public protocol meaning still needs a verified semantic binding.

**Implementation surface.** Extend executable projections, new protocol/effect domains and FB08 stateful harnesses; reuse existing [Python boundary workflow](../library_guides/workflows/python_boundaries.py) and analysis service integration.

**Acceptance.** Stateful witnesses cover ordinary completion, error, early abandonment and repeated consumption. Constructing a generator/future/plan cannot inherit execution effects as though it were activated. Terminating-normal-path postdominance cannot prove release under cancellation/nontermination. Demonstrate one reusable protocol model across distinct library interfaces.

### FB11 — Native binding and conversion composition

**Actions.** Collect exact wrapper/registration/native-target relationships, argument/result conversions, exception translation and ownership handoff. Join build context, original/generated source and ABI/layout evidence. Start with a real available PyO3 or equivalent source-backed binding; carry its verified body summaries through the wrapper.

Inventory Cython/C++ boundaries and rank their unresolved fanout. A focused C/C++ extraction increment is triggered when source and actual compilation commands are available and the boundary blocks either two semantic families or three retained task obligations. If triggered, qualify a bounded compilation-database/AST/CFG adapter for the selected constructs and keep unsupported C++ semantics explicit. If prerequisites are unavailable or the trigger is not met, record a reasoned deferral, affected tasks and exact external obligations. Do not claim native closure through a stub or matching name.

**Implementation surface.** Existing source/native producers, [Python analysis service](../library_guides/analyses/python_fabric.py), boundary contracts and supervised native-stage infrastructure. Any additional frontend is a standalone tooling worker, with a selected version, owned wire schema and compatibility fixtures.

**Acceptance.** One real cross-language composition has exact binding identity, conversion and failure/ownership evidence. Wrong-build and same-name/wrong-target controls fail. Native unknowns remain visible in summaries and guides. The C/C++ decision and any triggered implementation are resolved before this package completes; a documented optional deferral cannot satisfy a dependent behavioral guarantee.

### FB12 — Reusable semantic-family models and laws

**Actions.** Implement all six family groups from assessment §5.6, with typed carriers, primitives, laws, assumptions, source-backed binding checks and counterexamples:

| Family | Required initial relationships and controls |
| --- | --- |
| Collections/relations | Length bounds, filter/expand, key multiplicity, unmatched-null behavior, ordering; duplicate and empty inputs |
| Records/schemas | Recursive field lineage, merge conditions, nullability and metadata precedence/loss; conflicting metadata and incompatible fields |
| Reductions/accumulators | Initialize/update/merge/finalize, empty/null cases and partition equivalence obligations; non-associative and overflow/order-sensitive controls |
| Serialization/framing | Input/output domain, frame boundaries, EOF and partial progress; persistent/open input and incomplete frames |
| Buffers/interchange | Layout/validity/device/extent, conditional alias/copy and release; null incompatibility and premature/double consumption |
| Requests/transactions | Condition propagation, retry/failure classes and local effect ordering; externally assumed atomicity, idempotency and consistency |

Use body-derived transfers to establish implementation relationships, then apply the family vocabulary. Do not turn method names into laws. Distinguish declared axioms, discharged obligations and observations; mathematical reduction laws cannot silently substitute for machine arithmetic.

**Implementation surface.** [Transfer contracts](../library_guides/semantics/enrichment_contracts.py), [transfers](../library_guides/semantics/transfers.py), [conditions](../library_guides/semantics/conditions.py), [relational derivation](../library_guides/semantics/relational.py), approved pack assets and witness infrastructure.

**Acceptance.** Every family has a real implementation binding, an independent positive check and a counterexample/negative control. Each claimed reusable family must demonstrate unchanged transfer logic on at least two distinct libraries; count library/operation bindings separately from engine changes. At least one binding is evaluated on the reserved holdout. All six families retain explicit external or unproved obligations where necessary.

### FB13 — Availability, placement and extension obligations

**Actions.** Combine public/registry candidate coverage, type and feature constraints, phase/representation summaries and semantic family requirements. Generate elimination reasons and counterfactual applicability from the same predicates. Unresolved candidates block a closed “no suitable built-in” conclusion.

Derive required/default trait or protocol members, associated types, state/error/null laws, registration and execution constraints for extensions. Generate a concrete ordinary-consumer specialization and evaluate its compilation and behavior separately. Integrate reusable logic from legacy declaration helpers through the active service without reactivating legacy writer paths.

**Implementation surface.** [Applicability](../library_guides/semantics/applicability.py), [composition models](../library_guides/semantics/composition_models.py), [composition programs](../library_guides/semantics/composition_programs.py), [contract analysis](../library_guides/analyses/contracts.py), [task matching](../library_guides/semantics/task_matching.py).

**Acceptance.** Changing representation, overflow policy or configuration changes eligibility without a separate task-specific rule. A new registry candidate invalidates an extension-necessity claim. One scalar and one stateful extension exercise generated obligations, ordinary compilation and behavior; passing compilation cannot discharge semantic laws.

### FB14 — Cost, ambient dependence and interference

**Actions.** Add dependency sources for clocks, randomness, environment, caches, globals and external reads. Track whether they affect guards, outputs or effects. Add symbolic counters for calls, allocations, iterations and retained/buffered elements, with bounds only where supported by loop/callee invariants.

Retain spawn/await/join, synchronization and shared-region events; derive candidate interference and ordering obligations. Separate lexical sequencing from actual inter-task order. Label static bounds, runtime observations and estimates distinctly. This package supplies bounded characterization, not unrestricted worst-case complexity, deterministic execution or race-freedom proof.

**Implementation surface.** Executable fact extensions, summary domains, protocol/call composition and FB08 instrumentation. Optional compiler facts or proof tools require a measured unresolved need, selected context and their own qualification.

**Acceptance.** Real-source examples expose an ambient dependency and an input-dependent resource relationship. Mutation controls add a global read, retained buffer or shared write and change the corresponding summary. A missing loop invariant or unmodeled synchronization produces an obligation, not a fabricated bound or race-free result.

### FB15 — Population characterization, discovery and refinement

**Actions.** Produce a profile for every selected public operation, with analyzed and unknown dimensions. Implement reusable searches over guard partitions, field-lineage discontinuities, deferred effects, protocol asymmetries, ambient/cost dependencies, family exceptions and version/configuration differences. Compare documented claims with derived/witnessed behavior and preserve disagreement.

Reuse existing graph/FCA/label facilities for candidate organization. Clustering is not semantic equivalence. Expose the underlying typed summaries so a new query can investigate retained facts without another extractor. Connect hypotheses to FB08 counterexamples and classify failures by frontend, transfer, binding, assumption or oracle. Reanalysis must invalidate affected dependents.

**Implementation surface.** [Discovery graphs](../library_guides/discovery/graphs.py), [FCA](../library_guides/discovery/fca.py), [labels](../library_guides/discovery/labels.py), workflow schemas, summary query/rendering and witness/refinement records.

**Acceptance.** Run over a task-independent population, retaining the entire denominator. Demonstrate at least one source-derived finding absent from the task requirements and prior tooling capability facts, with an independent observation or check; do not claim novelty relative to all upstream documentation. Identifier/docstring and helper-refactoring controls preserve executable conclusions where semantics are unchanged. Publish false hypotheses and counterexamples as well as successes.

### FB16 — Incremental execution, resource control and recovery

**Actions.** Batch evidence/membership reads and reuse contextual summaries. Schedule bounded SCC/specialization work with explicit limits for state size, partitions, solver queries, time, memory and child processes. Separate worker RSS from coordinator/admission memory. Prioritize refinement using unresolved fanout, public reachability, affected dimensions and measured cost.

Cache source/context/model/abstract-input dependencies and candidate-membership dependencies. Currentness must respond to added callees, registry members and configurations as well as changed source bytes. Retain interrupted-run denominators, outcomes, completed counts and resumable checkpoints without admitting partial output as successful completion.

**Implementation surface.** [Source-analysis workflow](../library_guides/workflows/source_analysis.py), [stage engine](../library_guides/workflows/engine.py), [inputs](../library_guides/workflows/inputs.py), [direct dependencies](../library_guides/corpus/direct_dependencies.py), [invalidation](../library_guides/corpus/invalidation.py), worker supervision and paging.

**Acceptance.** Unchanged warm runs invoke zero producers and zero summary recomputations for the unchanged selection; planning/read costs are still measured. A local change updates affected summaries and preserves unrelated results. Added candidates invalidate negative claims. Forced worker/solver/budget failures preserve the previous admitted view and resume without loss or duplicate admission. Run the declared population within the numeric budgets frozen at FB09; budget changes require attributed evidence, not silent denominator reduction.

### FB17 — Consumer integration and retained-task reassessment

**Actions.** Connect admitted behavioral summaries to existing qualification, applicability, composition, explanation and publication. Make preconditions, assumptions, competing candidates and frontiers inspectable. Approved summary-to-family mappings remain attributed separately from derived facts; portable releases include necessary models and evidence.

Reassess all 24 original tasks and their reversal conditions against unchanged consumer requirements. Use the task mapping in §7 as coverage accounting. Retain historical task assessments and releases; publish a new comparison rather than rewriting the baseline. Also publish the task-independent characterization/discovery results.

**Implementation surface.** [Semantic realization](../library_guides/semantics/realization.py), [comparison](../library_guides/semantics/comparison.py), [publication closure](../library_guides/publication/closure.py), [rendering](../library_guides/publication/render.py), [CLI](../library_guides/cli.py) and new qualification scripts.

**Acceptance.** All 24 tasks have attributed outcomes and full candidate accounting; every remaining partial/gap names the exact missing fact, model, source boundary or external obligation. Existing supported controls retain their original limits. At least one consumer decision obtains a newly derived composed behavioral premise through the normal admission-to-guide path. Task-specific overrides cannot substitute for missing foundation packages.

### FB18 — Terminal qualification, portable delivery and handover

**Actions.** Freeze the implemented core/models and run G7. Build and install a fresh wheel in an isolated environment; restore both a new behavioral release and required historical views with source trees/native workers unavailable. Include all new schemas/rules/models in packaging. Run installed analytical work over retained evidence where that is part of the supported reader contract.

Run current package tests, relevant real native producers/consumers, static checks, scope-wide characterization, held-out evaluation and incremental failure/recovery. Attribute author/reviewer and any non-independent evaluation honestly. Finalize execution status, remaining semantic obligations, resource measurements and exact resume/reproduction commands. Leave no task-owned process running.

**Acceptance.** All mandatory packages and G0–G7 pass on the recorded final revision/context. Every triggered optional integration is either qualified or explicitly deferred without a dependent guarantee being claimed. Documentation, JSON status, task judgments and actual receipts agree. A green unit suite, an inventory or an export alone cannot complete this package.

## 5. Gate definitions and required evidence

| Gate | Required result | Minimum retained evidence |
| --- | --- | --- |
| G0 — Baseline and evaluation | Preserved baseline; fixed populations; independent expected relationships; explicit environment and budgets | Source/context hashes, manifest/release IDs, construct coverage, benchmark split, actual baseline commands/outcomes |
| G1 — Fact and admission integrity | Exact contextual facts; supported/unsupported distinctions; validated schemas/references and historical compatibility | Native fixture artifacts, source maps, rejection controls, replay and archive round trips |
| G2 — Reusable vertical slice | Rust/Python, ≥3 libraries, ≥2 families, held-out transfer, ≥2 nontrivial guarded relationships per library, actual callee composition | Entire selected denominator, derived summaries, independent observations, mutation controls, first cold/warm cost measurements |
| G3 — Lifecycle and boundary | Stateful failure/cleanup behavior and one exact real cross-language composition | Normal/error/abandonment/reuse traces, binding/ABI/context evidence, unresolved native obligations and C/C++ decision |
| G4 — Characterization and discovery | Six semantic families, placement/extension integration, bounded ambient/cost/interference analysis, finding beyond task requirements | Model/binding inventory, positive and counterexample results, held-out results, population profiles and attributed discovery evidence |
| G5 — Operational execution | Measured bounded population run, zero unchanged producer/summary work, invalidation and resumable failure | Per-stage/owner/SCC counters, coordinator and worker memory, dependency changes, failure/resume receipts, preserved predecessor |
| G6 — Consumer evidence | All 24 tasks and reversals reassessed through the active pipeline; new composed behavioral premise delivered | Exact comparisons, candidate populations, requirement mapping, approved bindings, guides and remaining obligations |
| G7 — Delivery | Final code/model freeze, current static/test/native gates and installed portable behavior | Commands, exit codes, logs, frozen hashes, wheel contents, clean-environment replay and consistent final status |

Tests of approximation must cover false universal and negative claims, not only successful examples. For the finite declared fixture suite, any such false claim is a gate failure. Report unknown rates separately from accuracy. Replay with the same analysis implementation checks reproducibility and tampering; it is not an independent proof of transfer soundness. Concrete/reference oracles and mutation controls supply a different check.

Performance thresholds are fixed from FB09 measurements before tuning the broader cohort. No percentage improvement or wall-time promise is invented during planning. Full-world Python dispatch, every Rust instantiation and all feature combinations are outside the finite guarantee; those exclusions must remain visible in profiles.

## 6. Validation commands and execution boundaries

Follow the [tooling README](../README.md) and [native README](../native/README.md). Use the standalone tooling environment, verified in FB00; do not synchronize or rebuild the SMARTREF root environment incidentally. If the working tooling environment lacks the declared qualification dependencies, use an explicitly selected isolated environment as documented, and record its interpreter path and lock. Do not silently substitute a partially provisioned environment.

These are existing command patterns to run during implementation, **not checks run while writing this plan**. From the repository root, with the documented working environment qualified:

```bash
tooling/library_guides/.venv/bin/pytest tooling/library_guides/tests -q --tb=short
tooling/library_guides/.venv/bin/ruff check tooling/library_guides/library_guides tooling/library_guides/tests tooling/library_guides/pilot/intelligence
tooling/library_guides/.venv/bin/ruff format --check tooling/library_guides/library_guides tooling/library_guides/tests tooling/library_guides/pilot/intelligence
```

From `tooling/library_guides`:

```bash
.venv/bin/pyrefly check --min-severity warn --output-format min-text
cargo +stable test --locked --manifest-path native/source-facts/Cargo.toml
cargo +stable clippy --locked --no-deps --manifest-path native/source-facts/Cargo.toml --all-targets -- -D warnings
cargo +stable fmt --manifest-path native/source-facts/Cargo.toml -- --check
cargo +nightly-2026-08-18 test --locked --manifest-path native/mir-facts/Cargo.toml
cargo +nightly-2026-08-18 clippy --locked --no-deps --manifest-path native/mir-facts/Cargo.toml --all-targets -- -D warnings
cargo +nightly-2026-08-18 fmt --manifest-path native/mir-facts/Cargo.toml -- --check
```

Apply the stable-worker patterns to `native/python-semantics/Cargo.toml`, `native/protocol/Cargo.toml` and `rustdoc-helper/Cargo.toml` when those workspaces change. Build/test/Clippy/format are distinct checks. Real producer/consumer canaries are also required; a Cargo workspace with no tests does not establish semantics. Use cataloged harness/module paths to focus individual Rust tests. Do not run overlapping full suites or uncontrolled compiler populations.

Existing tests to extend include [MIR analysis](../tests/test_mir_analyses.py), [native fabric](../tests/test_native_fabric.py), [Python boundaries](../tests/test_python_boundaries.py), [stage inputs](../tests/test_stage_inputs.py), [semantic enrichment](../tests/test_semantic_enrichment.py), [composition](../tests/test_composition_search.py) and [task applicability](../tests/test_task_applicability.py). Add behavioral tests by domain and frontend, not by mirroring the implementation line-for-line or creating a test per API name.

New qualification entry points under `pilot/intelligence/foundational/` must accept explicit source/selection/output locations, retain predecessor/run identity and avoid overwriting existing reports. Their exact CLI contracts are implemented in the owning work packages; no nonexistent command is presented here as runnable. Use [existing source-analysis qualification](../pilot/intelligence/qualify_source_analysis.py) as a mechanism reference, not as the terminal gate for this expanded scope.

Before signature, protocol/trait or deletion changes, follow the root [AGENTS.md](../../../AGENTS.md) code-intelligence obligations. If those tools remain unavailable, apply the documented [search fallback](../../../.codex/skills/search-tools-ref/SKILL.md) and qualify claim strength. Preserve the no-suppression rules and use normal relevant checks; no lint/type exclusions are introduced.

## 7. Assessment-to-plan traceability

The design's fact contract and precision semantics map to FB01–FB07; lifecycle/native collection to FB10/FB11; all six families to FB12; availability/extensions to FB02/FB13; cost/ambient/interference to FB14; unexpected-behavior discovery to FB15; witnesses to FB08 and every later domain; execution/invalidation to FB16; publication and generalization acceptance to FB09/FB17/FB18. No assessment dimension is dropped merely because it is absent from the task list.

| Retained task | Foundation packages supplying new evidence | Limit retained during reassessment |
| --- | --- | --- |
| `rust-placement` | FB02, FB07, FB10, FB12, FB13 | Consumer phase and closed built-in scope |
| `python-placement` | FB04, FB11, FB12, FB13 | Exact wrapper/native behavior |
| `python-representation` | FB06, FB10, FB11, FB12 | Conversion, layout and owner context |
| `serde-input` | FB07, FB10, FB12 | Framing/EOF and actual transport assumptions |
| `c-stream` | FB06, FB10, FB11, FB12 | ABI, single use, release, null/metadata compatibility |
| `rust-enrichment` | FB07, FB10, FB12, FB13 | Input key properties and external freshness |
| `rust-rows` | FB05, FB07, FB12 | Operation-specific empty/null and cardinality laws |
| `python-dataset` | FB10, FB11, FB12, FB14 | Requested pushdown versus observed physical pruning |
| `reverse-rust-placement` | FB12, FB13 | Same model under changed representation |
| `duplicate-reference` | FB06, FB12 | Key uniqueness cannot be assumed |
| `provider-limit` | FB07, FB10, FB12, FB13 | Exact/inexact ordering and selected provider scope |
| `rust-schema` | FB06, FB07, FB12 | Semantic metadata/units interpretation |
| `python-schema` | FB06, FB11, FB12 | Fragment population and evolution policy |
| `custom-scalar` | FB02, FB12, FB13 | Missing-built-in proof, compilation and behavior are separate |
| `custom-aggregate` | FB10, FB12, FB13 | State/merge laws and arithmetic/order assumptions |
| `conditional-store` | FB10, FB11, FB12, FB14 | Remote atomicity and backend conformance |
| `flight-ipc` | FB06, FB10, FB11, FB12 | Transport/deployment requirements and failure boundary |
| `async-consistency` | FB10, FB12, FB14 | Async does not establish service consistency |
| `numpy-dlpack` | FB06, FB10, FB11, FB12 | Device, null, synchronization and ownership context |
| `feature-profile` | FB02, FB13 | Finite actual compilation catalog |
| `rust-results` | FB10, FB14, FB17 | Streaming does not imply bounded total memory or latency |
| `python-results` | FB04, FB10, FB11, FB17 | No automatic inheritance of Rust cancellation semantics |
| `pydantic-input` | FB04, FB05, FB12, FB17 | Model/strictness choice and finite coercion observations |
| `reverse-python-overflow` | FB05, FB11, FB12, FB13 | Exact arithmetic/type contract |

The first 20 entries are the current gaps/partial results; the final four are supported controls. All require FB17 reassessment and FB18 delivery regardless of the shorter evidence-package lists above.

## 8. Status, change control and handover

Update package status only from evidence: `not_started`, `in_progress`, `blocked` or `complete`. Record exact prerequisites, actions, tests, new artifacts, source/model freeze and remaining obligations. A package cannot be complete while its mandatory acceptance evidence is missing. A blocked optional provider does not justify marking its dependent semantic claims supported.

The execution ledger starts with empty receipts and no completed packages. Keep status in that ledger and summarize milestone progress in a new foundational status document during FB00. Do not change the original assessment or completion ledger into an apparent acceptance record for this new scope. At milestones, write a new core/model freeze and compare it with the initial preservation snapshot; changes to frozen code are expected implementation work and require attribution and renewed relevant qualification.

If an implementation choice changes materially, update this plan's scope/dependencies and ledger together, retaining the reason. Do not narrow the reserved cohort, drop a family or replace a behavioral gate with static checks to obtain completion. Optional private compiler enrichment, C/C++ extraction, Kani/Loom and Rust execution placement have bounded decision points; they are not untracked commitments to build whole new analysis platforms.

At any interruption, record the current admitted predecessor, exact selected population, process outcome, completed counts, remaining frontier and next command. Preserve historical releases and concurrent edits. Final handover includes the completed package ledger, G0–G7 evidence, full task reassessment, held-out/generalization results, newly characterized phenomena, measured resource use and remaining semantic limits.
