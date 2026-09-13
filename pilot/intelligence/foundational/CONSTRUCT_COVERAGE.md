# Foundational construct baseline and reserved evaluation

The baseline concerns emitted facts and analyses in the preserved implementation, separately from new prototypes. More rows do not establish more behavioral coverage. The baseline core is `89cb8d1665f7d4e06a2cc48b80a19a936679aa1617500a4c36d8ad3444343b3e`; exact initial files and the 315-test baseline logs are retained in the run directory identified by `execution.json`.

| Construct/dimension | Existing fundamental observation | Baseline normalized/analyzed semantics | General shortfall and implementation owner |
| --- | --- | --- | --- |
| Rust public items, re-exports, impls and signatures | Typed rustdoc items, owner contracts, public routes, semantic digests and type occurrences | Public candidate inventories and type structure | Cross-context callable/instance identity and executable availability require further joins: FB02/FB13 |
| Cargo compilation context | Metadata, resolved graph, message streams and selected compiler invocation receipts | Contextual identity, observed/unknown settings | Separate requested/resolved features, doc versus ordinary compilation, substitutions and membership: FB02 |
| Rust literals and aggregates | Scalar literal kind/value, typed locals, nominal/variant constructors | Origin/dependency propagation; some semantic nominations | Missing language-aware value transfer and conditional consequences: FB03/FB05 |
| Rust locations | Local, dereference, field, index, constant index, downcast and subslice projections | Retained facts; coarse local dependence/effects | Missing regions, strong/weak updates, alias/retention distinction and field reconstruction: FB06 |
| Rust branches and unwind | Block successors, SwitchInt alternatives, assertion polarity and unwind destination | Reachability/control dependence and may-effects | Missing guarded outcome and exceptional heap/value transfer: FB05/FB10 |
| Rust arithmetic and casts | Rvalue kinds and retained qualifiers | Behavior-relevant operators partly remain debug strings | Lossy normalization and absent overflow/float model: FB03/FB05 |
| Rust direct/indirect calls | Arguments/destination, local definition target where available, dispatch/instance frontiers | One-artifact may-effect fixed point | Missing exact cross-unit substitution, higher-order target completeness and recursive value summaries: FB02/FB07 |
| Python definitions and syntax | Tree-sitter ranges, fields and owner relationships | Structural inventory and source-aligned documents | Missing evaluated operation and CFG projection: FB04 |
| Python bindings and scopes | Populated Ruff Checker binding/reference traversal and callee lexical observations | Exact source alignment; lexical resolution is explicitly not runtime dispatch | Missing traversal-local context and evaluated implicit operations: FB04 |
| Python types and call candidates | Pyrefly bulk facts and targeted computed/declared/expected TSP surfaces | Source-aligned call packets with candidates and native uncertainty | Underused type distinctions, declaration locations, substitutions and bounded obligations: FB04 |
| Python short-circuit, loop and exception control | Syntax is observed; pinned Ruff CFG has incomplete major constructs | No complete execution graph in baseline | Missing owned sequential evaluation, exception/finally, context, match and suspension transfer: FB04/FB10 |
| Native wrappers/ABI/conversions | Source and native artifact boundaries, selected callable declarations | Explicit unresolved native frontiers | Missing exact registration/target/context and conversion composition: FB11 |
| Collections, records, reductions, framing, buffers and requests | Relevant primitive source/type facts and hand-reviewed semantic evidence | Finite existing approved operation semantics | Missing reusable body-derived conditional carriers/laws and independent counterexamples: FB12 |
| Protocols, ownership and deferred execution | Some local drop/call/async syntax facts | Coarse event/effect facts | Missing phase-sensitive transition and failure/abandonment composition: FB10 |
| Ambient state, cost and interference | Relevant source/global/call/loop facts may be retained | No general input-dependent resource or interference domain | Missing general derivation; external scheduling/backend semantics remain obligations: FB14 |
| Witnesses and discovery | Existing experiments, graph/FCA/labels and source nominations | Finite task-focused checks and candidate organization | Missing generic guard/action harness generation, counterexample shrinking and task-independent behavioral findings: FB08/FB15 |
| Incremental admission and delivery | Exact source support, coordinated stages, currentness and portable closure | Established infrastructure with historical reader semantics | New semantic dependencies, finite budgets and operational controls must extend existing authority: FB01/FB16/FB18 |

The opt-in new Ruff node projection and new behavior modules are implementation progress against this matrix. They do not rewrite the baseline entries or discharge the broader package criteria.

## Reserved denominator

`benchmark.json` now enumerates 190 public candidates in six complete source files: 86 Arrow Schema, 44 Pydantic and 60 Serde JSON. The source/declaration inventory corrected an initial undercount by including Rust trait members on public receivers and Python public protocol methods. This expanded the population before library transfer evaluation; no candidate was removed.

For Rust, public-route candidates and trait-member candidates are identified separately. The selected context is the pinned documentation build with the exact consumer manifest, lock, metadata and private/hidden item extraction retained in the run directory. This is not an ordinary-compilation, all-feature or whole-world availability claim. The selected source declarations include 21 generated or unmapped bodies whose absence from the structural function inventory remains explicit.

For Python, public names and protocol members of public source classes form a conservative static candidate population. Dynamic exports and registration are not assumed closed. Fifteen selected overload declarations contain no executable implementation; two source spans require reconciliation. These records remain in the denominator and cannot silently become successful empty behavior summaries.

`expectations.json` reserves six challenging guarded relationships across both languages and at least two family contexts before library transfer evaluation. Every other candidate remains a characterization/unknown-accounting obligation. Ordinary consumer execution supplies a different checking mechanism from the abstract interpreter; authorship is shared and no independent human review is claimed. `reservation.json` pins the benchmark and expectation hashes.

Serde JSON is held out from transfer tuning. Declaration/source acquisition is permitted; no behavior result from that library has yet been evaluated. If its later results drive a transfer change, it becomes development evidence and a new untouched holdout must be reserved.

## Resource and preservation boundary

Initial independent limits are 500 owners, 200,000 steps, 10,000 states, 256 clauses, call depth 12, solver deadline 1,000 ms, worker RSS 8 GiB and worker deadline 600 seconds. These are starting caps, not promised throughput. FB09 freezes measured population performance budgets before broader tuning. Extraction, interpretation, admission and coordinator memory remain separately accountable.

`environment.json` records the actual isolated interpreter, package versions, native toolchains, input locks and the unchanged historical corpus manifest `f61eabbd4fe17866ca3bd5c6a3d7b1d8875e3f53ee32b204a693ce4292fa9913`. Runtime packages and the separately pinned Ruff/Pyrefly provider source versions are distinct selections. The SMARTREF application environment, GPU service and original pilot releases have not been modified by this implementation.
