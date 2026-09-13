> **Migrated 2026-09-13** from `smartref/docs/reviews/library_guides_recovery_implementation_2026-09-11.md` (smartref commit 5e2464345a). Frozen provenance: paths inside refer to the monorepo layout.

# Library-guide recovery implementation and qualitative pilot

Date: 2026-09-11

The failed implementation has been recovered into a standalone evidence compiler
and a bounded reviewed pilot. The essential change is that functionality now has
an explicit contract: capabilities connect bindings, claims, applicable facets,
principle realizations, alternatives and exact evidence. An API name or a
nonempty file citation cannot qualify a behavioral recommendation.

The final evaluation is qualitative, as requested. No automated model runner or
API key is needed. No numerical improvement in decision quality, token use or
reviewer effort is claimed.

## Delivered artifacts

- [Tooling and reproducible commands](../../tooling/library_guides/README.md).
- [Portable source manifest](../../tooling/library_guides/pilot/intake.yaml),
  [document scope](../../tooling/library_guides/pilot/documents.yaml), and
  [broad inventory report](../../tooling/library_guides/pilot/reports/inventory.json).
- [Reviewed semantic collection](../../tooling/library_guides/pilot/qualified/knowledge.yaml)
  and its independent
  [obligation policy](../../tooling/library_guides/pilot/qualified/obligations.yaml).
- [Qualitative task catalog](../../tooling/library_guides/pilot/tasks.yaml),
  [attributed observations](../../tooling/library_guides/pilot/observations.yaml), and
  [task-by-task evaluation](../../tooling/library_guides/pilot/QUALITATIVE_EVALUATION.md).
- Updated bounded pilot routes in
  [the Rust guide](../../.codex/skills/datafusion-arrow-rust-guide/SKILL.md) and
  [the Python guide](../../.codex/skills/datafusion-pyarrow-guide/SKILL.md), with
  matching Claude copies.

The original `datafusion-pyarrow-rust-ref` and `datafusion-pyarrow-ref` skills and
all seven long references remain preserved. The new guides explicitly use them
for uncovered tasks. This is not a declaration that the full reference scope has
been semantically migrated.

## How the shortfalls were addressed

| Original failure | Implemented correction | Qualification boundary |
|---|---|---|
| Rust records retained paths and item-kind labels instead of functionality | Version-matched rustdoc-types helper reads complete `index`; normalization retains callable parameters/results/generics, associated methods, public fields, aliases, impl/type/member/doc relationships and original compiler structure | Unknown, ambiguous and external relationships remain visible; uncommon type syntax can retain raw compiler structure |
| Public trait methods missing through private modules | Traverse public type paths as ownership roots; inherit explicit public re-export aliases for members | Regression fixture and actual `TableProvider::scan` recovery |
| Python parameter-name lists without reliable types | Griffe source/stub extraction, isolated native inspection, explicit parameter kinds/defaults/annotations, separate documentation-derived types | Native/static gaps are not upgraded to compiler certainty |
| Useful registry observations disconnected from functionality | Generic registry records become item-cited draft capabilities with descriptions, conditions and attributes | Registry-derived drafts receive no automatic semantic acceptance |
| No capability node | Typed capabilities, facets, claims, realizations, principles, decisions and integration contracts | Required facets come from independently declared obligations |
| Whole-file citation gestures | Exact JSON pointers or byte selections, selected-content hashes, source provenance, origin checks and dependency fingerprints | Structural validation cannot itself establish prose entailment; attributed review remains necessary |
| Unsupported polished briefs | Withdraw old acceptance; replace active routes with v2 reviewed comparisons, conditions and exceptions | Old nine briefs and ten derived-behavior files remain review inputs, not accepted authority |
| Coverage measured mentions in prose | Separate surface/use-case/decision/composition policy; reject denominator drift and missing targets; require current accepted dependency closure | Full inventory counts are reported separately from bounded semantic coverage |
| Decisions did not reopen on added alternatives | Fingerprint candidate families and unclassified additions, not only the selected APIs | Conservative invalidation is preferable to silently retaining a stale recommendation |
| Review state survived changed evidence, profiles or examples | Hash exact selections, profile definitions, semantic fields, principles and example inputs | Withdrawing a claim review also removes dependent coverage |
| Stage registry contained placeholders | Active v2 qualification/build path through doit, with real artifact receipts and per-product verified caches | No-op generation reuse and changed-build product reuse are tested |
| Failed/partial acquisition could overwrite good state | Per-input outcomes, explicit failure receipts and atomic authority replacement only on complete intake | A partial run can retain new immutable source blobs, but cannot replace prior knowledge |
| Publication was a sequence of file writes | Immutable staged snapshot, source/review/example gates, manifest verification, file and directory flushing, locked predecessor check and atomic pointer | Readers pin one verified generation; failed candidates do not advance it |
| A valid-looking bundle could omit execution | Publication verifies successful receipts against exact example configuration, input and claim fingerprints | Explicitly cacheable receipts additionally key executable, argument-file and distribution identities |
| Tool package depended on the application checkout | Own package, environment, lockfile, tests and packaged assets; runtime collection paths explicit; root runtime dependency removed | Wheel was installed and exercised outside the repository without SMARTREF or pilot libraries |
| Evaluation assumed unavailable model infrastructure | File-based proposal/review workflow and digest-pinned qualitative task audit | No model repetitions, model scores or estimated cost reductions are fabricated |

## Breadth and semantic depth

The completed intake enumerated and processed 64 source jobs. Its current draft
inventory contains 45,957 bindings, 146,158 relationships and 121,307 evidence
selections. It includes 755 registry-derived capability drafts. Seven preserved
reference documents were mapped into 11,701 structural sections.

These counts measure acquired structure. They do not establish public-surface
completeness or semantic quality. The report explicitly retains 2,833 unresolved
bindings and separates resolved, ambiguous, external and unresolved relationships.
An external type endpoint is not necessarily a library defect: standard-library
and dependency types can be outside the acquired scope.

The reviewed pilot contains **26 capabilities, 28 claims, ten decisions and one
integration**, supported by exact source artifacts and five executable jobs
(including the Rust build prerequisite). Its independent coverage policy covers
that scope only. It covers the six initial decision areas:

1. Query expressions, direct Arrow compute and conditional scalar extension.
2. Relation joins, provider scan contracts and remote scalar integration.
3. Grouped, window and conditional custom aggregate placement.
4. Collected versus streamed results.
5. Dataset Scanner versus direct Parquet Table reading.
6. A concrete Python/Rust Arrow C Stream boundary.

Pydantic object/JSON validation and serde_json text/reader decoding demonstrate
reuse beyond the original columnar libraries. Their capability, evidence,
review, rendering and publication code is the same compiler code.

## Concrete behavioral evidence

The Python fixture checks nullable projection through DataFusion and registered
Arrow kernels, wrapping versus checked integer overflow, reader/Table schema
metadata, and matching filtered projections through Dataset Scanner and direct
Parquet reading. It uses the registry dispatch API for native kernels, avoiding
pretend static type information for dynamically generated Python wrappers.

The Rust fixture compares collected and streamed output, verifies checked Arrow
integer overflow, exercises serde_json text/reader decoding and invalid input,
and tests relational cardinality. Two left keys joined against a duplicated
right key produce three rows with one unmatched null label; grouped and window
queries over three fixture rows produce two and three rows respectively.

The compiled pyo3-arrow extension round-trips a nullable int64 reader. The fixture
preserves schema metadata and the data-buffer address, remains readable after
producer deletion, and rejects a second import of the consumed capsule. The
behavioral claim is limited to this fixture and recorded build. It is not a
universal zero-copy or ownership guarantee.

Documentation-only statements keep that evidence class. For example,
`TableProvider::scan` documents filter/limit/projection order and the inexact-filter
limit restriction, but no custom provider has been behavior-certified. Python
stream cancellation and arbitrary external-service consistency are not borrowed
from another language or inferred from method names.

## Qualitative assessment

The frozen task catalog has 24 questions and changed-condition probes. Fifteen
have supported observations within their stated scope; nine remain gaps. These
are inspectable review dispositions, not an experimental success rate.

The useful qualitative improvement is that a reader can now distinguish an
interface fact, documented behavior, observed fixture behavior and an unanswered
question. Changed conditions can reverse a recommendation without discarding its
underlying evidence. The enrichment brief no longer invents snapshot consistency;
the dataset brief recognizes that both compared front doors support filters;
the result-consumption brief preserves the distinction between returned batches
and operator state.

The remaining task gaps are Rust/Python schema evolution, a complete custom
scalar recipe, a custom accumulator with unusual empty-group behavior,
conditional object-store writes, Flight versus IPC, async-service consistency,
NumPy/DLPack boundaries, and qualification of an optional API under a reduced
consumer feature profile. Those tasks can use the acquired inventory and preserved
references, but require additional semantic review or executable evidence before
new guidance is accepted.

## Verification

The standalone suite passes **168 tests**. It includes negative controls for
whole-file citations, missing inputs, wrong profiles, fabricated citations,
withdrawn reviews, denominator shrinkage, added alternatives, changed examples,
failed executions, missing execution receipts, stale publication predecessors,
model-proposal updates, syntax lookalikes, re-exported traits, structured
RST/Sphinx parsing, stale qualitative observations and real cache reuse.

Ruff checks and formatting cover all 110 owned Python files explicitly, including
the documentation adapters that the repository's directory-level defaults would
otherwise omit. Pyrefly reports zero diagnostics for the package, tests and pilot
scripts. The Rust helper and example pass formatting and Clippy with warnings
denied. Both lockfiles pass offline consistency checks. Task-scoped Git whitespace
checks pass.

The wheel includes schemas, manifests, rules, classifier controls and templates.
It was installed into an isolated environment under `/tmp` and used to build and
publish a synthetic collection from `/tmp`, without SMARTREF or PyArrow installed.
An absent collection returns a failing CLI status. The real pilot was separately
built and published with its pinned libraries and compiled extension. A subsequent
unchanged build verifies and reuses the existing candidate with zero model calls.

The machine-readable final receipts are retained in
[`pilot/reports/verification.json`](../../tooling/library_guides/pilot/reports/verification.json).
The qualitative receipt and exact observations are separate from those deterministic
checks.

## Working boundaries

No root application or native extension rebuild is needed for this tooling-only
change. The repository was already dirty; unrelated edits were preserved. The
pre-recovery task snapshot remains at
`/home/paul/.cache/library-guides/recovery/20260911T215907Z`.

Optional hosted services, DocETL/DSPy optimization and automated model comparisons
have not been adopted. They are not required for the implemented local workflow.
The next semantic additions should be small reviewed task packets from the visible
gap list, rather than a fresh generation of broad unsupported prose.
