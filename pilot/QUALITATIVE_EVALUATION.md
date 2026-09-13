# Qualitative pilot evaluation

This is an attributed task review, not a model benchmark. It establishes no statistical improvement or token-saving estimate.

Tasks SHA-256: `3876571531235c2bbea93c2e2679c2d4f63a35f8f883617a156087cc32cd680b`

## rust-placement: Choose expression composition, direct Arrow compute, or a scalar extension

Disposition: **supported**. Profile: `rust-docsrs-54.1-58.4`.

Required: Execution placement; Overflow policy; Conditional extension use

The comparison distinguishes query-plan composition, direct Arrow arithmetic and the scalar extension mechanism. Overflow is explicit, and custom extension use remains conditional on a scoped search; no blanket optimizer-opacity claim is inherited.

Comparison with previous approach: The previous generated briefs and navigator did not bind their recommendations to current item-level review fingerprints. This route retains the conditions and exact supporting artifacts.

Reversing condition: Need a direct Arrow operation on already materialized values.; Required scalar semantics remain unexpressed after a scoped catalog search.

Follow-up: Retain the stated evidence class and applicability limits; re-review if the recorded inputs or requirement changes.

Reviewed by: Codex qualitative task review 2026-09-11

- `decision:rust-placement` — SHA-256 `29095af86a9d9823a8f82a9e7ab45cdf9d6155f1015752339fd6eaaf16fa93d0`

## python-placement: Transform an already materialized Arrow column or a query column

Disposition: **supported**. Profile: `python-installed-54.0-25.0.1`.

Required: Representation; Query versus kernel; Checked versus wrapping overflow

The query and array placements are distinct. The real fixture produces the same nullable projected values through DataFusion and Arrow compute, and separates wrapping addition from checked overflow.

Comparison with previous approach: The previous generated briefs and navigator did not bind their recommendations to current item-level review fingerprints. This route retains the conditions and exact supporting artifacts.

Reversing condition: Already materialized arrays or a different overflow policy are required.

Follow-up: Retain the stated evidence class and applicability limits; re-review if the recorded inputs or requirement changes.

Reviewed by: Codex qualitative task review 2026-09-11

- `decision:python-placement` — SHA-256 `f04b5b226095d35ad8f19eaedef70cd4e017fc3451fc865004ae065d9124d8e3`

## rust-results: Consume a large Rust query result incrementally

Disposition: **supported**. Profile: `rust-docsrs-54.1-58.4`.

Required: Stream versus collect; Drop behavior; No blanket operator-memory guarantee

The brief preserves the documented collect/stream distinction and drop-driven cancellation scope. The executable consumes both paths and compares their batch results; it does not claim a process-wide memory bound or measure cancellation latency.

Comparison with previous approach: The previous generated briefs and navigator did not bind their recommendations to current item-level review fingerprints. This route retains the conditions and exact supporting artifacts.

Reversing condition: Incremental consumption or drop-driven cancellation is required.

Follow-up: Retain the stated evidence class and applicability limits; re-review if the recorded inputs or requirement changes.

Reviewed by: Codex qualitative task review 2026-09-11

- `decision:rust-results` — SHA-256 `95e0ab5efd61cdd87a9e00d2d1c02a3f1aaf9bd9e4799335939651123f445b27`

## python-results: Choose a Python batch stream or collected results

Disposition: **supported**. Profile: `python-installed-54.0-25.0.1`.

Required: Result type; No borrowed Rust cancellation guarantee

The Python wrapper documentation distinguishes a list of collected batches from a stream. The comparison explicitly declines to import a Rust cancellation guarantee. Stream cancellation itself is not behavior-qualified here.

Comparison with previous approach: The previous generated briefs and navigator did not bind their recommendations to current item-level review fingerprints. This route retains the conditions and exact supporting artifacts.

Reversing condition: The consumer can process a record-batch stream.

Follow-up: Retain the stated evidence class and applicability limits; re-review if the recorded inputs or requirement changes.

Reviewed by: Codex qualitative task review 2026-09-11

- `decision:python-results` — SHA-256 `286c218f237d466817404f87d1a36df0aef260a984d8f406d5e23d5c8f322e20`

## python-representation: Adapt Table and RecordBatchReader consumers

Disposition: **supported**. Profile: `python-installed-54.0-25.0.1`.

Required: Conversion direction; Materialization; Scoped copy claims

The comparison preserves conversion direction: expose a Table as a reader or materialize a reader as a Table. The fixture checks schema metadata and values; the prose does not generalize a local zero-copy statement to arbitrary consumers.

Comparison with previous approach: The previous generated briefs and navigator did not bind their recommendations to current item-level review fingerprints. This route retains the conditions and exact supporting artifacts.

Reversing condition: The caller requires a materialized Table.

Follow-up: Retain the stated evidence class and applicability limits; re-review if the recorded inputs or requirement changes.

Reviewed by: Codex qualitative task review 2026-09-11

- `decision:python-representation` — SHA-256 `059b486fef9f95d44585a014da7f9c8bf986b58b238d7ea389783daf1fba98a0`

## pydantic-input: Validate Python objects or JSON input

Disposition: **supported**. Profile: `pydantic-2.13.4`.

Required: Representation; Strictness caveat

The same contracts and compiler work for an unrelated Python library. Object and JSON front doors are distinguished, and the fixture verifies successful decoding and strict integer rejection without claiming identical semantics for all input types.

Comparison with previous approach: The previous generated briefs and navigator did not bind their recommendations to current item-level review fingerprints. This route retains the conditions and exact supporting artifacts.

Reversing condition: The input is JSON data.

Follow-up: Retain the stated evidence class and applicability limits; re-review if the recorded inputs or requirement changes.

Reviewed by: Codex qualitative task review 2026-09-11

- `decision:pydantic-input` — SHA-256 `1eb0f56c9b614b9c73a75abd520e795e1f2404dc8c4e9231671200c3d60d5722`

## serde-input: Deserialize JSON text or a persistent IO connection

Disposition: **supported**. Profile: `serde-json-1.0.151`.

Required: from_str versus from_reader; EOF; Buffering

The unrelated Rust transfer case retains an operationally useful EOF/buffering caveat from the exact reader documentation. The executable verifies text/reader agreement on a fixture and malformed-input failure.

Comparison with previous approach: The previous generated briefs and navigator did not bind their recommendations to current item-level review fingerprints. This route retains the conditions and exact supporting artifacts.

Reversing condition: Input is an IO stream; consider EOF and buffering requirements.

Follow-up: Retain the stated evidence class and applicability limits; re-review if the recorded inputs or requirement changes.

Reviewed by: Codex qualitative task review 2026-09-11

- `decision:serde-input` — SHA-256 `292e36270ac0276a53012ac75e86eed220d41c3ca5ac15ae213e9ec539f30cc7`

## c-stream: Transfer a nullable Arrow reader through Rust and back

Disposition: **supported**. Profile: `interop-pilot`.

Required: Schema and metadata; Ownership lifetime; Capsule single use; Fixture-scoped buffer evidence

A real compiled pyo3-arrow extension round-trips a nullable int64 reader. The recorded fixture preserves schema metadata and buffer address, survives producer deletion, and rejects repeated capsule import. These observations are intentionally limited to that fixture and build.

Comparison with previous approach: The previous generated briefs and navigator did not bind their recommendations to current item-level review fingerprints. This route retains the conditions and exact supporting artifacts.

Reversing condition: Change the representation, applicability profile or required guarantee; reacquire and review the corresponding evidence before applying this result.

Follow-up: Retain the stated evidence class and applicability limits; re-review if the recorded inputs or requirement changes.

Reviewed by: Codex qualitative task review 2026-09-11

- `integration:c-stream` — SHA-256 `514aa36118aa15f5ef6a22f7774ac332075590c0a5cf8ccb0a59787592ee40b1`

## rust-enrichment: Choose relation join, source provider, or remote scalar integration

Disposition: **supported**. Profile: `rust-docsrs-54.1-58.4`.

Required: Source acquisition; Duplicate-key cardinality; Explicit freshness policy

The alternatives are a relation join, a provider scan contract and an async remote scalar interface. The decision requires an external freshness policy rather than inventing snapshot guarantees. The duplicate-key fixture demonstrates why a left join alone does not establish row-count preservation.

Comparison with previous approach: The previous generated briefs and navigator did not bind their recommendations to current item-level review fingerprints. This route retains the conditions and exact supporting artifacts.

Reversing condition: The source needs a reusable scan plan with explicit projection, filters and limit contracts.; Remote scalar invocation itself is required under an explicit caller-owned consistency and retry policy.

Follow-up: Retain the stated evidence class and applicability limits; re-review if the recorded inputs or requirement changes.

Reviewed by: Codex qualitative task review 2026-09-11

- `decision:rust-enrichment` — SHA-256 `2eb903edf5bb024713bf4de8fd7796c0ec056a0a8d95b5abbce77ada22e97087`

## rust-rows: Choose grouped, window or custom aggregate placement

Disposition: **supported**. Profile: `rust-docsrs-54.1-58.4`.

Required: Output cardinality; Function-specific empty/null rules; Conditional custom accumulator

Grouped aggregation and window placement are distinguished by their documented contracts and the fixture row counts. A custom accumulator is conditional; function-specific empty/null behavior remains a required separate check.

Comparison with previous approach: The previous generated briefs and navigator did not bind their recommendations to current item-level review fingerprints. This route retains the conditions and exact supporting artifacts.

Reversing condition: Results should be attached to existing rows with an explicit frame and ordering.; A required statistic remains unexpressed after searching the scoped aggregate catalog.

Follow-up: Retain the stated evidence class and applicability limits; re-review if the recorded inputs or requirement changes.

Reviewed by: Codex qualitative task review 2026-09-11

- `decision:rust-rows` — SHA-256 `84bf4ae0cd87f98e32fbb50399c0518352475f4e7e4d5f6f53539cae6d08726b`

## python-dataset: Read selected Parquet columns and filtered rows

Disposition: **supported**. Profile: `python-installed-54.0-25.0.1`.

Required: Scanner versus Table; Shared filter support; Conditional physical pruning

Both Scanner and direct Parquet Table reading support projection and filters. The fixture compares the same result through both. Scanner adds deferred consumption and batch controls; physical pruning remains conditional rather than asserted from the API name.

Comparison with previous approach: The previous generated briefs and navigator did not bind their recommendations to current item-level review fingerprints. This route retains the conditions and exact supporting artifacts.

Reversing condition: The consumer wants a Table directly from a Parquet source.

Follow-up: Retain the stated evidence class and applicability limits; re-review if the recorded inputs or requirement changes.

Reviewed by: Codex qualitative task review 2026-09-11

- `decision:python-dataset` — SHA-256 `2279f45b864fb6f4a88a9f4a0b29af00206f95b052921dc75c860c7dd74a54df`

## reverse-rust-placement: Change the consumer to an already materialized array

Disposition: **supported**. Profile: `rust-docsrs-54.1-58.4`.

Required: Decision reverses to a direct kernel under the changed requirement

Changing the consumer to already materialized Arrow operands makes the direct kernel the applicable route. The comparison still requires a separate arithmetic policy; it does not force all transformations through a query.

Comparison with previous approach: The previous generated briefs and navigator did not bind their recommendations to current item-level review fingerprints. This route retains the conditions and exact supporting artifacts.

Reversing condition: Need a direct Arrow operation on already materialized values.; Required scalar semantics remain unexpressed after a scoped catalog search.

Follow-up: Retain the stated evidence class and applicability limits; re-review if the recorded inputs or requirement changes.

Reviewed by: Codex qualitative task review 2026-09-11

- `decision:rust-placement` — SHA-256 `29095af86a9d9823a8f82a9e7ab45cdf9d6155f1015752339fd6eaaf16fa93d0`

## reverse-python-overflow: Require an error on integer overflow

Disposition: **supported**. Profile: `python-installed-54.0-25.0.1`.

Required: Checked operation; No accidental wrapping

The error-on-overflow requirement reverses the default wrapping choice toward checked arithmetic. The real fixture observes an error for checked int8 overflow and a wrapped value for ordinary addition.

Comparison with previous approach: The previous generated briefs and navigator did not bind their recommendations to current item-level review fingerprints. This route retains the conditions and exact supporting artifacts.

Reversing condition: Already materialized arrays or a different overflow policy are required.

Follow-up: Retain the stated evidence class and applicability limits; re-review if the recorded inputs or requirement changes.

Reviewed by: Codex qualitative task review 2026-09-11

- `decision:python-placement` — SHA-256 `f04b5b226095d35ad8f19eaedef70cd4e017fc3451fc865004ae065d9124d8e3`

## duplicate-reference: Keep unmatched enrichment rows with duplicate reference keys

Disposition: **supported**. Profile: `rust-docsrs-54.1-58.4`.

Required: Unmatched null; Duplicate multiplication; No invented uniqueness

The exact SQL fixture retains the unmatched left key but produces two matches for the duplicated right key. The brief therefore requires a key-uniqueness or duplicate-resolution policy, instead of claiming that left joins preserve row count.

Comparison with previous approach: The previous generated briefs and navigator did not bind their recommendations to current item-level review fingerprints. This route retains the conditions and exact supporting artifacts.

Reversing condition: The source needs a reusable scan plan with explicit projection, filters and limit contracts.; Remote scalar invocation itself is required under an explicit caller-owned consistency and retry policy.

Follow-up: Retain the stated evidence class and applicability limits; re-review if the recorded inputs or requirement changes.

Reviewed by: Codex qualitative task review 2026-09-11

- `decision:rust-enrichment` — SHA-256 `2eb903edf5bb024713bf4de8fd7796c0ec056a0a8d95b5abbce77ada22e97087`

## provider-limit: A provider receives inexact filters and a limit

Disposition: **supported**. Profile: `rust-docsrs-54.1-58.4`.

Required: Limit pushdown condition; Filter-before-limit-before-projection

The recovered TableProvider.scan documentation explicitly orders filters before limit before projection and disallows pushed limits with inexact filters. This is documentation-backed; no custom provider implementation has been certified.

Comparison with previous approach: The previous generated briefs and navigator did not bind their recommendations to current item-level review fingerprints. This route retains the conditions and exact supporting artifacts.

Reversing condition: Change the representation, applicability profile or required guarantee; reacquire and review the corresponding evidence before applying this result.

Follow-up: Retain the stated evidence class and applicability limits; re-review if the recorded inputs or requirement changes.

Reviewed by: Codex qualitative task review 2026-09-11

- `cap:rust-provider` — SHA-256 `2c3a36a0bbbe1437b121492a1484db701e2528bce3b0bd22ec0dfd0ef33e56e7`

## rust-schema: Reconcile evolving Rust Arrow schemas

Disposition: **gap**. Profile: `rust-docsrs-54.1-58.4`.

Required: Metadata precedence; Nested compatibility; Nullability policy

The broad acquisition makes relevant APIs and documentation discoverable, but this task lacks a reviewed decision with the complete required semantic contract. The pilot must not answer it with a generic recommendation.

Comparison with previous approach: The preserved deep dives remain useful starting points. The new tooling exposes this as unfinished semantic work instead of manufacturing coverage from an API mention.

Reversing condition: Change the representation, applicability profile or required guarantee; reacquire and review the corresponding evidence before applying this result.

Follow-up: Use scoped discovery and the original reference skill to acquire the missing contract, compare alternatives, and add the required semantic or executable evidence.

Reviewed by: Codex qualitative task review 2026-09-11


## python-schema: Govern Python dataset schema evolution

Disposition: **gap**. Profile: `python-installed-54.0-25.0.1`.

Required: Fragment versus dataset schema; Evolution conditions

The broad acquisition makes relevant APIs and documentation discoverable, but this task lacks a reviewed decision with the complete required semantic contract. The pilot must not answer it with a generic recommendation.

Comparison with previous approach: The preserved deep dives remain useful starting points. The new tooling exposes this as unfinished semantic work instead of manufacturing coverage from an API mention.

Reversing condition: Change the representation, applicability profile or required guarantee; reacquire and review the corresponding evidence before applying this result.

Follow-up: Use scoped discovery and the original reference skill to acquire the missing contract, compare alternatives, and add the required semantic or executable evidence.

Reviewed by: Codex qualitative task review 2026-09-11


## custom-scalar: Implement a custom scalar operation after a failed built-in search

Disposition: **gap**. Profile: `rust-docsrs-54.1-58.4`.

Required: Concrete missing semantics; Signature and null behavior; Working custom extension

The broad acquisition makes relevant APIs and documentation discoverable, but this task lacks a reviewed decision with the complete required semantic contract. The pilot must not answer it with a generic recommendation.

Comparison with previous approach: The preserved deep dives remain useful starting points. The new tooling exposes this as unfinished semantic work instead of manufacturing coverage from an API mention.

Reversing condition: Change the representation, applicability profile or required guarantee; reacquire and review the corresponding evidence before applying this result.

Follow-up: Use scoped discovery and the original reference skill to acquire the missing contract, compare alternatives, and add the required semantic or executable evidence.

Reviewed by: Codex qualitative task review 2026-09-11


## custom-aggregate: Implement a statistic with a nonstandard empty-group policy

Disposition: **gap**. Profile: `rust-docsrs-54.1-58.4`.

Required: Accumulator state; Merge behavior; Empty/null fixture

The broad acquisition makes relevant APIs and documentation discoverable, but this task lacks a reviewed decision with the complete required semantic contract. The pilot must not answer it with a generic recommendation.

Comparison with previous approach: The preserved deep dives remain useful starting points. The new tooling exposes this as unfinished semantic work instead of manufacturing coverage from an API mention.

Reversing condition: Change the representation, applicability profile or required guarantee; reacquire and review the corresponding evidence before applying this result.

Follow-up: Use scoped discovery and the original reference skill to acquire the missing contract, compare alternatives, and add the required semantic or executable evidence.

Reviewed by: Codex qualitative task review 2026-09-11


## conditional-store: Choose conditional object-store writes

Disposition: **gap**. Profile: `rust-docsrs-54.1-58.4`.

Required: Concurrency preconditions; Failure semantics; Backend applicability

The broad acquisition makes relevant APIs and documentation discoverable, but this task lacks a reviewed decision with the complete required semantic contract. The pilot must not answer it with a generic recommendation.

Comparison with previous approach: The preserved deep dives remain useful starting points. The new tooling exposes this as unfinished semantic work instead of manufacturing coverage from an API mention.

Reversing condition: Change the representation, applicability profile or required guarantee; reacquire and review the corresponding evidence before applying this result.

Follow-up: Use scoped discovery and the original reference skill to acquire the missing contract, compare alternatives, and add the required semantic or executable evidence.

Reviewed by: Codex qualitative task review 2026-09-11


## flight-ipc: Choose IPC or Flight for a remote Arrow boundary

Disposition: **gap**. Profile: `rust-docsrs-54.1-58.4`.

Required: Transport; Serialization; Ownership and failures

The broad acquisition makes relevant APIs and documentation discoverable, but this task lacks a reviewed decision with the complete required semantic contract. The pilot must not answer it with a generic recommendation.

Comparison with previous approach: The preserved deep dives remain useful starting points. The new tooling exposes this as unfinished semantic work instead of manufacturing coverage from an API mention.

Reversing condition: Change the representation, applicability profile or required guarantee; reacquire and review the corresponding evidence before applying this result.

Follow-up: Use scoped discovery and the original reference skill to acquire the missing contract, compare alternatives, and add the required semantic or executable evidence.

Reviewed by: Codex qualitative task review 2026-09-11


## async-consistency: Guarantee live service consistency during async enrichment

Disposition: **gap**. Profile: `rust-docsrs-54.1-58.4`.

Required: Freshness model; Call multiplicity; Retries

The broad acquisition makes relevant APIs and documentation discoverable, but this task lacks a reviewed decision with the complete required semantic contract. The pilot must not answer it with a generic recommendation.

Comparison with previous approach: The preserved deep dives remain useful starting points. The new tooling exposes this as unfinished semantic work instead of manufacturing coverage from an API mention.

Reversing condition: Change the representation, applicability profile or required guarantee; reacquire and review the corresponding evidence before applying this result.

Follow-up: Use scoped discovery and the original reference skill to acquire the missing contract, compare alternatives, and add the required semantic or executable evidence.

Reviewed by: Codex qualitative task review 2026-09-11


## numpy-dlpack: Move arrays across NumPy and DLPack consumers

Disposition: **gap**. Profile: `python-installed-54.0-25.0.1`.

Required: Null representation; Ownership; Copy conditions

The broad acquisition makes relevant APIs and documentation discoverable, but this task lacks a reviewed decision with the complete required semantic contract. The pilot must not answer it with a generic recommendation.

Comparison with previous approach: The preserved deep dives remain useful starting points. The new tooling exposes this as unfinished semantic work instead of manufacturing coverage from an API mention.

Reversing condition: Change the representation, applicability profile or required guarantee; reacquire and review the corresponding evidence before applying this result.

Follow-up: Use scoped discovery and the original reference skill to acquire the missing contract, compare alternatives, and add the required semantic or executable evidence.

Reviewed by: Codex qualitative task review 2026-09-11


## feature-profile: Use a docs.rs-only optional API in a reduced Cargo build

Disposition: **gap**. Profile: `rust-docsrs-54.1-58.4`.

Required: Feature/target applicability; Compiler verification

The broad acquisition makes relevant APIs and documentation discoverable, but this task lacks a reviewed decision with the complete required semantic contract. The pilot must not answer it with a generic recommendation.

Comparison with previous approach: The preserved deep dives remain useful starting points. The new tooling exposes this as unfinished semantic work instead of manufacturing coverage from an API mention.

Reversing condition: Change the representation, applicability profile or required guarantee; reacquire and review the corresponding evidence before applying this result.

Follow-up: Use scoped discovery and the original reference skill to acquire the missing contract, compare alternatives, and add the required semantic or executable evidence.

Reviewed by: Codex qualitative task review 2026-09-11

