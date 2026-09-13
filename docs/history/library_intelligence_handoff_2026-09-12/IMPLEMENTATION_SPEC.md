# Library intelligence: database, embeddings, communities, and concept induction

**Implementation specification — 2026-09-12**

**Status:** proposed implementation extension, not a report of completed integration. Public APIs were researched; the target repository and RTX 5090 were not available for execution. Values identified as defaults are engineering choices, not benchmark findings. Examples specify API usage and invariants; adapt them to the active contracts rather than introducing a parallel model.

**Source baseline:** `library_guide_source_semantic_evidence_lanes_implementation_plan_v2_2026-09-11.md` (hereafter **V2 plan**). Relevant anchors: §§4–7 ownership/contracts/storage; §§8–11 extraction; §12 derivation and qualification; §13 invalidation; §14 authoring/publication; §§15–17 work packages and gates.

**Implementation boundary:** `tooling/library_guides/`. Preserve the active CLI, attrs/cattrs contracts, Cargo context C0, declaration tier D0, L1 Tree-sitter, L2 Ruff, L3 Pyrefly, L4 MIR, central identity service, qualification, and immutable publication. Do not depend on the application's other extractors, change its root workspace/toolchain, or replace its authoring workflow.

## 1. Final decisions

| Concern | Adopted choice | Boundary |
|---|---|---|
| Graph interface | NetworkX | Materialized analytical views, not another persistent authority |
| Community detection | `igraph` + `leidenalg` | Narrow CPU adapter from NetworkX projections; NetworkX does not implement Leiden itself |
| Persistent structured corpus | LanceDB OSS | Primary storage for normalized observations, relationships, provenance, analytical outputs, and retrieval units |
| Data representation | Explicit PyArrow schemas and RecordBatches | attrs/cattrs remains the validation/semantic contract; Arrow is the physical representation |
| On-disk table format | Lance | Do not describe LanceDB tables as Parquet tables |
| Portable export/import | Parquet + manifest; Arrow IPC for temporary staging | Export is not a second live fact authority |
| Embedding | `Qwen/Qwen3-Embedding-8B` | BF16 inference, native 4096-dimensional output, normalized float32 persisted vectors |
| Serving | One local vLLM Docker Compose service | NVIDIA GPU, loopback exposure, pinned image and model snapshot |
| Lexical/dense retrieval | LanceDB native FTS + vector search | Explicit vectors, not implicit database-managed embedding callbacks |
| Initial ranking | Reciprocal-rank fusion (RRF) + typed candidate expansion | No model tournament or learned reranker required for first completion |
| Semantic neighbors | scikit-learn `NearestNeighbors` | Bounded, exact cosine neighborhoods initially |
| Labels | Source phrase extraction + class-based TF-IDF | NumPy/SciPy/scikit-learn primitives; no generative model required |
| Formal concepts | FCApy `FormalContext`, `ConceptLattice` with `algo="CbO"` | Bounded exact contexts; support/unknown semantics explicit |
| Ontology/navigation | Typed concept graph + several DAG/tree views | Do not identify community membership with subtype truth |
| Correctness | Existing fixtures, explicit invariants, qualitative pilot | Functionality first; tuning/leaderboard comparisons deferred |

NetworkX has native Louvain, label propagation, modularity-related routines and many graph utilities, but its current Leiden entry points are backend-only. `leidenalg` adds an actual CPU implementation and explicit multi-layer optimization. This is why the adapter is justified; it is not a replacement for NetworkX. [S1–S4]

### 1.1 Explicit changes to the V2 plan

This specification **supersedes the storage implementation**, not the evidence semantics, in V2 §4/§7/§14: normalized facts now live in LanceDB family tables rather than permanent per-owner JSON shards with SQLite as the query index. Logical shard manifests remain useful for scope, receipts, and hashing, but their members are database record IDs.

The vLLM service is a narrowly scoped exception to V2's daemon deferral. It is an inference service, not a repository watcher, new source-analysis daemon, or automated review agent. Frozen-snapshot extraction remains the model. Qualitative review still requires no generative model service/API key; stored guides remain readable when vLLM is stopped.

Existing authored manifests, obligations, and reviews may remain version-controlled files owned by the existing authoring system. Store immutable snapshots/projections of them in LanceDB for generation-wide querying; those projections cannot become a competing write authority. All **extracted facts** and their normalized provenance move to the database. Transport files, temporary compilation workspaces, and export bundles are not competing fact stores.

### 1.2 Non-goals

No mandatory Neo4j, DuckDB, Polars, FAISS, LangChain, LlamaIndex, GPU graph backend, UMAP, HDBSCAN, or general BERTopic pipeline. No universal type solver, automatic semantic approval, complete dynamic-call recovery, automatic change to obligations, or replacement of existing native lanes. No claim that this stack has been tuned for throughput.

## 2. Component and authority boundaries

```text
Existing frozen sources / C0 / D0 / L1-L4 / Griffe / registries / examples
    -> existing supervised transport + strict DTO validation
    -> Arrow batches in private staging
    -> LanceDB normalized evidence tables + complete receipts
    -> committed corpus manifest with exact table versions
         |-> typed graph projections -> NetworkX -> Leiden -> communities
         |-> retrieval-unit renderer -> vLLM -> embeddings
         |-> evidence-backed attribute selectors -> FCApy -> formal concepts
         |-> source phrase extraction -> cluster/concept labels
    -> typed concept graph and retrieval services
    -> existing packet -> proposal -> entailment review -> qualified generation
```

A **corpus generation** selects source observations and analytical products. A **published guide generation** selects reviewed claims and their complete support closure. They may advance separately: a newly indexed corpus is not automatically an approved guide.

Separate three notions of truth:

* Source observations and their exact context are authoritative evidence records.
* Communities, vectors, labels, and concept occurrences are versioned derived records.
* Accepted capabilities/claims remain governed by the existing review/qualification path.

## 3. Database schema and record design

### 3.1 General physical rules

Use a small registry of family-specific Arrow schemas, not one table per owner and not one generic JSON column for all evidence. Scalar filter keys must be top-level columns. Use bounded `struct` and `list` values for naturally bounded nesting; represent recursive types as nodes and ordered links, not infinitely recursive Arrow structs. Interned type-expression identities must preserve generic/lifetime/const positions, polarity, wrappers, and contexts from D0.

Keep the following common envelope on observations:

```text
record_id             immutable application ID of this observation revision
entity_id             central entity identity, if applicable
artifact_id           producing fact artifact
logical_shard_id      receipt/shard grouping, independent of physical storage
snapshot_id           immutable source snapshot
profile_id            effective semantic profile, not just a display name
producer_id           versioned normalizer/extractor/analysis identity
fact_kind             validated tag
semantic_digest       normalized semantic content digest
provenance_digest     exact artifact/support provenance digest
schema_version        normalized record schema
```

Do not use a Lance row offset, internal `_rowid`, fragment number, Arrow row number, or igraph vertex index as a durable evidence identity. Those are temporary execution coordinates.

Separate **entity identity** from **observation revision**. Multiple versions/profiles/lanes can describe one entity without overwriting one another. Different sources or versions with similar names must not accidentally share an entity ID.

### 3.2 Table families

The table names below are proposed physical names; the active contract names in the V2 plan take precedence.

| Table family | Important typed contents |
|---|---|
| `source_snapshots`, `source_files` | Source identities, file manifest, source byte digests, encodings, licenses, file disposition |
| `blob_objects`, `blob_chunks` | Content-addressed raw bytes: source, raw compiler output, transport audit artifacts; bounded byte chunks and reconstruction metadata |
| `profiles`, `cargo_projects`, `cargo_dependencies`, `compilation_units`, `rustdoc_contexts` | Existing C0/build/doc-purpose distinctions |
| `entities`, `public_routes` | Stable identities, defining/exported views, route chains, kind, visibility |
| `declarations`, `type_nodes`, `type_links`, `impl_contracts` | D0 contracts; ordered recursive type links; polarity, bounds and applicability |
| `body_owners`, `cfg_blocks`, `cfg_edges`, `access_events`, `call_sites` | Owner-local MIR/Python mechanism observations; keep high-volume families separate |
| `relations`, `relation_support` | Typed source/target relations and exact support links; dispatch, identity, availability, uncertainty remain distinct |
| `evidence_selections`, `source_anchors`, `source_map_segments` | Exact source/fact selections and byte-coordinate mappings |
| `artifacts`, `logical_shards`, `receipts`, `coverage_dispositions` | Producer/run reconciliation and exact universes |
| `derivations`, `support_dependencies`, `candidate_universes`, `facet_seeds` | Existing derived-fact semantics and invalidation dependencies |
| `example_discoveries`, `example_runs` | Located/parsed/resolved/typechecked/executed distinctions |
| `retrieval_units`, `retrieval_unit_support`, `embedding_jobs` | Canonical text views, chunk trees, dependencies, inference status |
| `search_units_qwen3_8b_v1` | Denormalized searchable text + vectors + keys; derived from retrieval units and embeddings |
| `projection_runs`, `projection_nodes`, `projection_edges`, `projection_edge_support` | Versioned graph views and edge explanations |
| `community_runs`, `communities`, `community_memberships`, `community_links` | Structural/semantic/fused assignments, parent-child hierarchy, boundary statistics |
| `attributes`, `attribute_assertions`, `fca_contexts`, `formal_concepts`, `formal_concept_memberships` | Explicit property vocabulary, supported/unknown observations, closed sets and scoped membership |
| `concepts`, `concept_edges`, `concept_labels`, `label_evidence` | Typed navigational concept graph and source-grounded names |
| `authoring_snapshots`, `review_snapshots`, `guide_generations` | Read projections of active authoring/review objects, not another approval interface |
| `corpus_manifests`, `corpus_heads` | Application-level publication metadata and exact multi-table snapshot selection |

Do not require every table on the first delivery. Register/activate a family only when its producer exists. Missing families remain explicit in coverage; empty unsupported tables are not proof of successful extraction.

### 3.3 Suggested relation schema

```python
import pyarrow as pa

RELATION_SCHEMA = pa.schema(
    [
        pa.field("record_id", pa.string(), nullable=False),
        pa.field("relation_id", pa.string(), nullable=False),
        pa.field("artifact_id", pa.string(), nullable=False),
        pa.field("logical_shard_id", pa.string(), nullable=False),
        pa.field("snapshot_id", pa.string(), nullable=False),
        pa.field("profile_id", pa.string(), nullable=False),
        pa.field("source_entity_id", pa.string(), nullable=False),
        pa.field("target_entity_id", pa.string()),
        pa.field("kind", pa.string(), nullable=False),
        pa.field("site_id", pa.string()),
        pa.field("identity_resolution", pa.string(), nullable=False),
        pa.field("dispatch_certainty", pa.string(), nullable=False),
        pa.field("analysis_certainty", pa.string(), nullable=False),
        pa.field("body_availability", pa.string(), nullable=False),
        pa.field("applicability_id", pa.string()),
        pa.field("producer_id", pa.string(), nullable=False),
        pa.field("semantic_digest", pa.string(), nullable=False),
        pa.field("provenance_digest", pa.string(), nullable=False),
    ],
    metadata={b"library_guides.schema": b"relations.v1"},
)
```

This is an envelope example, not permission to discard family payloads. Add typed family tables for variant-specific data. Non-null Arrow fields supplement, rather than replace, attrs/cattrs validation, referential checks and qualification.

Use `pa.RecordBatch.from_pylist(..., schema=...)`, `pa.RecordBatchReader.from_batches(...)`, and `db.create_table(..., schema=...)` / `table.add(...)` for the ingestion boundary. Validate DTOs before Arrow construction; reject schema drift rather than infer types separately in every batch. [S5, S6]

### 3.4 Raw bytes and logical shards

A unified database does not eliminate the need to retain original source bytes. Store raw bytes in `blob_chunks`, with a separate object manifest:

```text
blob_objects: digest, total_bytes, chunk_count, media_type, encoding, provenance
blob_chunks: object_digest, ordinal, byte_offset, chunk_digest, bytes: binary
```

Start with fixed maximum chunks of 4 MiB; the last may be shorter. A source file/anchor refers to the **original object digest and original byte range**, not a chunk-local offset. Reconstruct a range by fetching the overlapping chunks, verifying each digest and the mapping. Whole-object verification is required on acquisition/export.

This simple Arrow-binary representation avoids making large-blob APIs a launch dependency. Keep bytes in separate tables and never select them during graph/vector scans. A later Lance blob-storage encoding can replace the physical layout behind the same content API after exact-range and export fixtures pass.

A logical shard stores its owner/file/family scope, ordered `(record_id, digest)` membership and receipt. Compaction can move rows without changing this identity. Large membership lists themselves use a membership table, not a giant array cell.

## 4. Commit, snapshot, and recovery protocol

Lance supplies atomic table transactions and versioned snapshots. The architecture must not assume a transaction across all application tables; the public table transaction contract is the boundary used here. Implement coherent multi-table publication above it. [S7, S8]

### 4.1 One local writer, many pinned readers

Use the existing coordinator plus an OS advisory writer lock. Native extraction may run in parallel, but only the coordinator commits corpus-table writes and generation publication. Use a local filesystem for the database; do not put active Lance table directories inside a live Dropbox/network-sync folder.

Every production read resolves a corpus manifest, opens fresh table handles and checks out the recorded versions. No production analytical pass should silently read each table's independent latest version.

### 4.2 Write sequence

1. Read and retain the expected current corpus head; allocate a run ID.
2. Supervise the worker and validate frames into private Arrow IPC staging. Keep V2's sequence, digest, memory and terminal-receipt rules.
3. Accept only reconciled successful shards; retain failures/partial dispositions separately. A partial run cannot masquerade as a complete generation.
4. Acquire the coordinator write lock and ensure the expected head still matches.
5. Validate immutable IDs: an existing record ID with different canonical content is an error. Insert only new records in batches; do not update source observations in place.
6. Commit family tables, support links, raw bytes and receipts. Check referential closure and per-shard ordered digests. Verify the admitted run membership, not merely whole-table row counts.
7. Build/update the applicable FTS/scalar indexes. Capture each resulting table version after data/index work is complete.
8. Write an immutable corpus manifest containing table names, exact versions, schema digests, selected artifact/run IDs, input and analytical recipe fingerprints, authoring snapshot identity, and completeness dispositions. A manifest does not recursively include its own table version.
9. Tag referenced data-table versions with the generation identity; do not delete tags still referenced by a corpus or guide generation.
10. Update `corpus_heads` last, under the same writer lock, using the expected predecessor check. This final single-table commit publishes the new manifest.
11. Release the lock. Retain private staging until the admission receipt is durable; clean it through explicit recovery policy.

The manifest's selected artifact/run sets are important. A table version may contain historic observations and rows from a failed attempt; a reader must also apply the manifest's membership scope. A version alone does not mean every row in the table belongs to the selected corpus.

A crash before step 10 leaves the old head valid. Unpublished rows are orphans, not approved evidence. Recovery records which run they belong to, then retries idempotently or schedules explicit garbage collection. Database clients outside this reader abstraction could see staging/history; do not describe application-level publication as global transactional invisibility.

### 4.3 Built-in methods and cautions

```python
import lancedb

db = lancedb.connect("/absolute/local/path/library-intelligence.lancedb")
table = db.open_table("relations")
version = table.version
# After publication selection, use a fresh read handle:
reader = db.open_table("relations")
reader.checkout(version)
# Pin retained versions against pruning:
table.tags.create("corpus-<generation-id>", version)
```

Relevant APIs: `create_table`, `open_table`, `add`, `merge_insert`, `count_rows`, `list_versions`, `checkout`, `checkout_latest`, `tags.create`, `tags.list`, `create_scalar_index`, `create_fts_index`, `search`, `select`, `where`, `to_batches`. [S6, S8]

Use `merge_insert(...).when_not_matched_insert_all().execute(...)` only after explicit duplicate-content checks when implementing idempotent admission. It is not a license to overwrite immutable evidence or an assumed unique-key constraint. Enforce record uniqueness and foreign-key validity in the coordinator.

Do not use `.restore()` for normal corpus selection; restoration mutates the latest state. Do not call `cleanup_old_versions` or broad `optimize()` automatically until retention/tag protection is tested. Compaction, index maintenance and version pruning require separate policies. No source selector may depend on a physical row address.

## 5. Query indexes, scans, and portable storage

### 5.1 Scalar and lexical indexes

Create scalar indexes for actually queried top-level keys: `record_id`, `entity_id`, `artifact_id`, `profile_id`, relation source/target IDs, and shard ID. Start with `BTREE`; use `BITMAP` for low-cardinality status/kind fields only where supported by the selected SDK. Avoid indexing every column. [S9]

FTS indexes belong on curated `search_text`, not huge JSON payloads. Preserve code identifiers and split aliases in the rendered search text. Configure no stemming/stop-word removal for identifier-heavy text; the ordinary defaults may remove meaningful tokens such as `not`. Exact path lookup remains a scalar operation.

```python
search_table.create_fts_index(
    "search_text",
    stem=False,
    remove_stop_words=False,
    ascii_folding=False,
    max_token_length=256,
    with_position=True,
)
```

These are documented native FTS configuration knobs. Check them against the pinned SDK; do not reintroduce legacy Tantivy-only flags. [S10]

### 5.2 Bounded scans

Use projected Arrow batches. Never call `.to_pandas()` or `.to_arrow()` on an entire fact family merely to filter it afterward.

```python
batches = (
    table.search()
    .where(validated_filter)
    .select(required_columns)
    .limit(explicit_limit)
    .to_batches(batch_size=4096)
)
```

For a complete declared projection, obtain the manifest-scoped count and use that explicit bound, then reconcile consumed rows. SDK search defaults must not silently restrict graph input to 10 rows. Use typed predicate construction over validated IDs/enum values; never interpolate arbitrary user text into filter expressions. Token/row/byte bounds belong to the query contract, with explicit continuation or truncation metadata. [S6]

### 5.3 Parquet is an export, not LanceDB's internal file format

Use `pyarrow.parquet.ParquetWriter` over streamed batches, preserving schema metadata and an external generation manifest. Import through `pyarrow.dataset.dataset(path, format="parquet").scanner(...).to_reader()` into new Lance tables. [S11, S26]

Export a selected corpus or a guide's support closure, not every historic database row. Retain original blob bytes (as binary columns/chunks), exact evidence IDs, schemas, normalization versions, scope certificates, reviews, and logical membership. Recreated table version numbers will differ after import; evidence identity must not.

A round trip must rebuild the corpus manifest's physical table bindings and retain original logical generation identity with an import receipt. Compare canonical observation/support digests, source-range bytes and qualified outputs, not Parquet byte equality.

## 6. Embedding service: fixed model, stable local deployment

### 6.1 Model and representation

Choose `Qwen/Qwen3-Embedding-8B`, BF16, native 4096 output dimensions. Store L2-normalized float32 vectors. Do not truncate dimensions or quantize weights in the initial implementation. This deliberately removes optimization decisions from the first milestone. The Qwen model card documents the family, supported dimensionality, query instructions and normalization. [S12]

The 5090 deployment must pass a local smoke test. Model weights alone do not establish peak memory; batch size, backend and runtime buffers matter. Use a current vLLM image with an NVIDIA/PyTorch build that actually supports the card. Do not equate data-center Blackwell support with proof of every consumer SM120 kernel. Record GPU model, compute capability, driver, CUDA runtime, PyTorch and vLLM versions in the service receipt. [S13, S14]

### 6.2 Container deployment

Use Docker Compose with NVIDIA Container Toolkit and a model snapshot mounted read-only. Choose a specific official vLLM image digest after the device smoke test, not a permanently moving `latest` tag. Download the exact Hugging Face revision in a separate explicit acquisition step and record its files/digests. Container Python/CUDA dependencies remain separate from the tooling's existing Python environment. [S14–S17]

```yaml
services:
  embeddings:
    image: ${VLLM_IMAGE:?Set a tested immutable vLLM image tag or digest}
    entrypoint: ["vllm", "serve"]
    command:
      - /models/qwen3-embedding-8b
      - --served-model-name
      - library-qwen3-embedding
      - --runner
      - pooling
      - --dtype
      - bfloat16
      - --host
      - 0.0.0.0
      - --port
      - "8000"
      - --max-model-len
      - "4096"
      - --max-num-seqs
      - "4"
      - --max-num-batched-tokens
      - "8192"
      - --gpu-memory-utilization
      - "0.85"
    ports:
      - "127.0.0.1:8000:8000"
    volumes:
      - ${QWEN_MODEL_DIR:?Set the verified local snapshot directory}:/models/qwen3-embedding-8b:ro
      - vllm_cache:/root/.cache/vllm
    environment:
      HF_HUB_OFFLINE: "1"
      HF_HUB_DISABLE_TELEMETRY: "1"
    shm_size: "2gb"
    restart: unless-stopped
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
volumes:
  vllm_cache:
```

The numeric limits are conservative starting configuration, not measured guarantees. Reduce simultaneous sequences/token batching first after an OOM; use the pinned image's documented compatible backend rather than blindly forcing FlashAttention. A fixed 4096-token service cap is intentional despite the model's longer capability: the retrieval units below are much smaller. No `trust_remote_code` is required merely because this is a Qwen checkpoint.

Start/stop with `docker compose up -d embeddings` and `docker compose stop embeddings`. A container health endpoint is a liveness signal; the application must also perform a known embedding request to establish readiness. Offline flags prevent model-hub fetching, not all outbound network traffic; bind loopback and do not claim a network sandbox without enforcing one.

### 6.3 Client contract

Use `httpx.Client` / `httpx.AsyncClient` against `/v1/embeddings`, with explicit timeouts, small bounded concurrency and retry only on transient service/transport failures. Send:

```json
{
  "model": "library-qwen3-embedding",
  "input": ["<fully rendered input 1>", "<fully rendered input 2>"],
  "encoding_format": "float"
}
```

Sort response records by their `index`; require exactly one result for each input, a 4096-length vector, finite components and a nonzero norm. Normalize with NumPy. Reject mismatched counts/indexes, wrong dimensions, NaN/Inf or empty vectors. Persist the actual model recipe and input digest with each result. Do not mark a batch successful on HTTP 200 alone. vLLM supports embedding/pooling models and this endpoint; use the current `--runner pooling` interface rather than copying older `--task embed` launch recipes. [S13]

Use the pinned tokenizer snapshot with `transformers.AutoTokenizer.from_pretrained(..., local_files_only=True)` for client-side budgeting. Ensure token counting includes the same special-token policy as the server. Never request silent input truncation.

### 6.4 Query versus document encoding

For user retrieval queries:

```text
Instruct: Given a software engineering requirement, retrieve library contracts, capabilities, examples, and constraints useful for implementing it.
Query:<user task>
```

For stored document/operation cards, encode the rendered text without the retrieval-query prefix. Do not apply a conversational chat template to text-embedding inputs. Store the prompt-role policy in the recipe. [S12]

For semantic graph construction, compare **document-view embeddings with document-view embeddings**. Do not mix query-prefixed vectors, newly generated community summaries and source-grounded operation cards in the same graph without a separately declared view policy.

### 6.5 Model/recipe identity and outage behavior

`EmbeddingRecipe` includes model repository, exact revision, tokenizer files/revision, renderer version, prompt role, pooling behavior, service image/configuration digest, dtype, dimension, normalization and chunk policy. Cache key = domain-separated hash of recipe plus exact rendered input bytes. Preserve output vectors; GPU inference need not be bitwise identical across runtime changes.

If the service is unavailable, fact extraction, exact/lexical retrieval and reading published guides continue. New embedding jobs remain pending; do not substitute another model, zero vectors or unrecorded dimension changes. A semantic-index build can be explicitly incomplete without invalidating source evidence.


## 7. Retrieval units, views, and chunk boundaries

### 7.1 A retrieval unit is not a storage shard

Use the existing attrs/cattrs contracts to add a versioned `RetrievalUnit` record. A logical fact shard groups transport/scope observations; a retrieval unit groups information that answers a coherent question; a packet assembles several units and their exact evidence. Never reuse one boundary for all three.

Required fields:

```text
unit_id, unit_revision_id
entity_refs, scope/profile refs
unit_kind, view_kind, facet_kind (where applicable)
parent_unit_ref, child_order
embedding_text, search_text
source_support_refs, derivation_ref, review_disposition
renderer_version, chunk_policy_version
input_semantic_digest, exact_rendered_bytes_digest
counted_tokens, tokenizer_recipe_ref
completeness, retained_limitations, omitted_support_cursor
```

`embedding_text` is coherent prose plus concise contracts, rendered deterministically where possible. `search_text` may additionally include original qualified identifiers, split identifier words, aliases and headings for lexical matching. Source-support references and opaque hashes are structured metadata, not large blocks of tokenized text.

Keep `retrieval_units` as canonical text/view records and `search_units_qwen3_8b_v1` as a materialized query table containing the relevant scalar scope keys, text, vector, parent/entity references and recipe IDs. Both are in the same database. A materialized retrieval table does not displace the normalized evidence tables.

Use `pa.list_(pa.float32(), 4096)` for the vector column. A changed model/dimension/embedding-space recipe uses a new physical search table or an explicitly segregated vector column; do not mix incompatible vectors in one searchable space. Source/profile/view filtering must be possible without fetching full evidence payloads.

### 7.2 Units to generate

| Unit kind | Embedded information | Initial target tokens |
|---|---|---:|
| Operation contract | Qualified identity, receiver, concise declaration, relevant bounds, input/output roles, exact upstream purpose, applicability | 250–700 |
| Mechanism facet | One question; supported observations; relevant conditions; phase/profile; unknown or opaque frontier | 150–450 |
| Documentation passage | Heading breadcrumb, coherent explanation, referenced symbols, exceptions/qualifications | 300–800 |
| Example composition | Stated task, prerequisite setup, essential call sequence, outcome/discovery status | 300–1,000 |
| Capability/decision | Outcome, entry points, choices, reversing constraints, source/review status | 300–800 |
| Community/concept descriptor | Distinguishing source terms, representative members, common contracts, external interfaces | 250–600 |

These are implementation defaults, not empirically optimal sizes. Set a 2,048-token hard limit for one ordinary stored unit, including its context header. The service accepts 4,096 so queries and exceptional separately governed units have headroom. A hard limit is not permission to truncate a qualifier; oversize input produces a split or an explicit unsupported/oversize disposition.

Generate operation-contract units from D0/Griffe plus exact upstream documentation before MIR is available. Mechanism units enrich them later. Candidate and undocumented operations remain searchable; an accepted capability card is not a prerequisite for discovery.

### 7.3 Two source-grounded entity views

Maintain an **intent/contract view** and a **mechanism view**. The former explains what is documented and declared; the latter answers a bounded behavioral question using actual analysis. Both include limitations. Their different retrieval roles must survive in metadata and packet rendering.

Example deterministic contract text:

```text
Operation: <qualified path>
Declared role: accepts a borrowed <type>; returns a Result whose success value is <type>.
Public routes: <verified routes>
Generic applicability: <recorded constraints>
Upstream purpose: <bounded source statement or documented unknown>
Profile: <relevant target/feature/doc-purpose distinctions>
Behavioral limits: declaration alone does not establish copying, mutation, or metadata preservation.
```

Do not infer the purpose from the identifier. An identifier supplies searchable words; an upstream statement supplies documented purpose; a qualified mechanism supplies a narrower observed fact. Keep those roles explicit.

For semantic graph construction, initially use **one bounded canonical intent/contract unit per operation**. Additional facet units improve retrieval but should not give a heavily documented operation fifteen times the graph influence. If the entity summary cannot fit, use a recorded bounded summary and retain child references; do not silently omit constraints required to interpret it.

### 7.4 Deterministic boundary rules

**Declarations:** begin at a callable or coherent operation family. Preserve receiver, relevant type wrappers and bounds together. Large traits get overview, required-member checklist, provided-member overview and method units. Keep exact recursive contracts in structured tables and retrieve them on demand.

**Documentation:** split on heading/paragraph/list/example boundaries using existing Markdown/RST adapters. Carry the heading breadcrumb. Keep a claim and its exception in the same unit. Source maps continue to refer to original bytes, not the renderer's offsets.

**Mechanisms:** render owner/facet slices from qualified analysis, not arbitrary source windows. An error-propagation slice can connect noncontiguous construction/conversion/return observations; a configuration slice connects the read and the nominated site. Its support set and unknown frontier must be retrievable.

**Examples:** retain setup sufficient to understand the sequence, exact status (`located`, `parsed`, `names_resolved`, `type_checked`, executed outcome), and environment. A long example has a parent and sequential child stages. A fragment is not promoted to a runnable witness.

**Long source bodies:** split only at syntax boundaries after the owning signature and relevant controlling context are identified. Prefer a mechanism slice plus exact-source retrieval where a source fragment cannot be made coherent within the budget.

Do not use blanket percentage overlap. Repeat a small semantic header and necessary qualifiers; use parent links for the remainder. Never create n-grams or source spans that cross unrelated source blocks.

### 7.5 Rendering, admission, and refresh

Pipeline: validated facts -> typed renderer input -> rendered unit -> tokenizer budget check -> chunk verification -> embedding job -> validated embedding -> materialized search row.

A source-byte change can refresh citations without changing the embedding input. Retain a new unit/evidence revision and reuse its vector only when the exact rendered bytes and complete embedding recipe match. A changed semantic qualifier, unit membership or prompt changes the relevant digest. Never reuse an embedding merely because the entity's name stayed the same.

Community/concept descriptors are derived search conveniences. They are not fed back into the base entity embedding graph that created those same communities. This keeps the dependency graph acyclic and avoids treating recycled summaries as new corroboration.

## 8. Graph projections and community detection

### 8.1 Four projections with different semantics

Implement a strict `GraphProjectionSpec` over a pinned corpus manifest. It declares entity selection, profile, allowed relation kinds, certainty/availability treatment, direction policy, weighting, aggregation, budgets and support-universe dependencies.

| Projection | Nodes and edges | Main operations |
|---|---|---|
| Architecture | Operation/type/family nodes with calls, delegation, construction and registration relations | Subsystems, interfaces, paths, community discovery |
| Capability resemblance | Public operations/families with explicit common contracts and semantic similarity | Alternatives, cross-cutting capabilities |
| Owner mechanism | CFG/events/places for selected owners | Existing bounded flow/control/effect analyses |
| Support dependency | Artifacts, facts, recipes, reviews and universe dependencies | Invalidation, support closure, publication |

Use `nx.MultiDiGraph` for bounded heterogeneous evidence neighborhoods. Retain parallel supported relationships and source-site details. [S27] Community detection receives a separately constructed positive-weight simple graph, never the raw entire fact graph. The support dependency DAG remains distinct from cyclic call/CFG graphs.

Useful native NetworkX operations include `subgraph`, `connected_components`, `strongly_connected_components`, `condensation`, `ancestors`, `descendants`, `pagerank`, `immediate_dominators`, `is_directed_acyclic_graph`, and `transitive_reduction`. Follow each algorithm's graph-type requirements. A post-dominator/control-dependence implementation still needs the explicit exceptional-exit/nontermination policy required by V2; a graph function alone does not supply that analysis. [S2, S23, S28, S29]

### 8.2 Initial structural projection policy

Create nodes in sorted application-ID order. Record all eligible isolated nodes even when no edges survive. Restrict one run to a stated coherent library/profile scope; cross-package relations retain their exact package identities.

Start with supported identity-resolved `calls`, `delegates_to`, `constructs`, `registers` and explicit contract-family relationships, selected through the existing typed fact definitions. Uncertain dispatch stays in the source relations and in an explicitly marked candidate layer, not silently promoted into a certain structural edge. The primary structural layer may omit an uncertain edge while reporting that omission; a later exploratory layer may admit it with a different recipe.

For each node pair and relation family, initially count presence once rather than the number of repeated call sites. Add the contributions of distinct relation families, with an initial declared weight of 1 per included family. Preserve all supporting sites in `graph_edge_support`; the analytical weight is not evidence certainty.

For an undirected architectural community view, combine `u -> v` and `v -> u` contributions using the declared reducer and remove self-loops. Preserve the directed view for interface/dependency explanations. Self-recursion is still present in source evidence and owner analysis.

Do not create all-pairs cliques merely because operations mention `Result`, `Option`, `Arc`, or another ubiquitous type. A meaningful producer/consumer role or explicit extension contract can contribute via a separate typed layer. If a shared-feature bipartite projection is used, cap feature degree and apply a declared inverse-frequency/degree policy; retain excluded hubs in the report. Similar identifiers are not structural edges.

### 8.3 NetworkX-to-Leiden adapter

The following illustrates the narrow interface. Its numeric resolution is an initial policy choice. Run native optimization under the existing supervisor or an equivalent tooling-owned subprocess limit when the declared graph is large.

```python
from __future__ import annotations

import math
import igraph as ig
import leidenalg as la
import networkx as nx


def leiden_groups(
    graph: nx.Graph,
    *,
    resolution: float = 1.0,
    seed: int = 13,
) -> tuple[tuple[str, ...], ...]:
    """Partition a validated undirected simple positive-weight projection.

    Returned groups are deterministic in representation, not promised to be
    identical across different library versions or graph recipes.
    """
    if graph.is_directed() or graph.is_multigraph():
        raise ValueError("Expected a simple undirected projection")
    if not math.isfinite(resolution) or resolution <= 0:
        raise ValueError("resolution must be finite and positive")
    if any(not isinstance(node, str) for node in graph):
        raise TypeError("Projection nodes must be application-owned string IDs")

    ids = sorted(graph.nodes)
    if not ids:
        return ()
    positions = {node: i for i, node in enumerate(ids)}
    pairs: list[tuple[int, int, float]] = []
    for source, target, data in graph.edges(data=True):
        if source == target:
            raise ValueError("Self-loops must be handled by the projection recipe")
        weight = float(data.get("weight", 1.0))
        if not math.isfinite(weight) or weight <= 0:
            raise ValueError("Leiden projection requires positive finite weights")
        left, right = sorted((positions[source], positions[target]))
        pairs.append((left, right, weight))
    pairs.sort()
    if not pairs:
        return tuple((node,) for node in ids)

    native = ig.Graph(
        n=len(ids),
        edges=[(left, right) for left, right, _ in pairs],
        directed=False,
    )
    native.vs["entity_id"] = ids
    native.es["weight"] = [weight for _, _, weight in pairs]
    partition = la.find_partition(
        native,
        la.RBConfigurationVertexPartition,
        weights="weight",
        resolution_parameter=resolution,
        n_iterations=-1,
        seed=seed,
    )
    isolates = set(nx.isolates(graph))
    grouped: dict[int, list[str]] = {}
    for node, membership in zip(ids, partition.membership, strict=True):
        if node not in isolates:
            grouped.setdefault(membership, []).append(node)
    groups = [tuple(sorted(members)) for members in grouped.values()]
    groups.extend((node,) for node in sorted(isolates))
    return tuple(sorted(groups))
```

`find_partition`, `RBConfigurationVertexPartition`, edge weights, resolution, seed and negative `n_iterations` are documented API choices. Negative iterations means until no improvement, not a global optimum. The wrapper separately handles isolates because their algorithmic placement is not a meaningful subsystem assignment. [S3]

Persist run metadata, canonical node/edge digests, seed, parameters, installed dependency versions, partition membership and modularity/quality as a diagnostic. Community IDs are derived from run/policy plus canonical members; do not persist the optimizer's ordinal as the concept identity.

Use native NetworkX Louvain only as a fallback explicitly selected by configuration, not silently after a Leiden failure. Fallback changes the derivation recipe and must appear in the run receipt.

### 8.4 Semantic-neighbor projection

Use normalized, source-grounded intent/contract embeddings, one chosen unit per eligible entity. Build a directed candidate k-nearest-neighbor table, then a conservative undirected mutual-neighbor graph.

Use:

```python
from sklearn.neighbors import NearestNeighbors

neighbors = NearestNeighbors(
    n_neighbors=min(16, len(entity_vectors)),
    metric="cosine",
    algorithm="brute",
    n_jobs=1,
).fit(entity_vectors)
# Call in bounded query blocks, not with an unbounded all-pairs matrix:
# distances, indices = neighbors.kneighbors(query_block)
```

Remove self by exact entity ID, retain at most 15 other neighbors, use deterministic distance/ID tie ordering within retrieved ties, and retain only mutual neighbors with positive similarity. Weight = `max(0, 1 - cosine_distance)`. Equal-distance ties at the k boundary can depend on the numerical implementation; record that limit instead of claiming a cross-platform canonical partition. [S18]

This default avoids materializing an N-by-N distance matrix but still has quadratic distance-computation cost. Bound the corpus/projection and query blocks. If it exceeds the declared budget, report the projection incomplete or partition by a declared scope; do not silently subsample. An approximate nearest-neighbor replacement is a future implementation option, not a first-build requirement.

### 8.5 Keep structural and semantic outputs; also implement a fused view

Produce three named products:

1. `architecture_structural`: the default subsystem/navigation input.
2. `capability_semantic`: similarity-based cross-cutting groups and alternatives.
3. `architecture_semantic_fused`: a supplementary combined view, never the only retained explanation.

For the fused view, use the same node order in both igraph layers. Normalize each layer's total positive edge weight to 1 so sheer edge volume does not dictate its contribution. Initially use structural/semantic layer weights 0.75/0.25. These are policy settings, not truth/confidence probabilities. Skip an empty layer with an explicit disposition; do not send a zero-total layer to an objective requiring positive total weight.

```python
partitions = [
    la.RBConfigurationVertexPartition(
        structural_native, weights="weight", resolution_parameter=1.0
    ),
    la.RBConfigurationVertexPartition(semantic_native, weights="weight", resolution_parameter=1.0),
]
optimizer = la.Optimiser()
optimizer.set_rng_seed(13)
improvement = optimizer.optimise_partition_multiplex(
    partitions,
    layer_weights=[0.75, 0.25],
    n_iterations=-1,
)
membership = partitions[0].membership
```

Use aligned initial membership across layers and verify the resulting memberships agree. The optimizer returns improvement while mutating partitions. `find_partition_multiplex` is a convenient alternative that returns membership and improvement. Multiplex optimization shares a partition; it does not itself give overlapping memberships. [S3, S4]

Keep relation contributions, similarity scores and membership reasons inspectable. Structural/semantic agreement is useful navigation evidence, not independent proof of behavior. A semantic-only association can nominate an alternative without proving interface substitutability.

### 8.6 Hierarchy and representatives

Start with the chosen top-level partition. Recursively run the same declared projection within a community containing more than 80 eligible entities, up to depth 3. Admit a split only when it creates genuine smaller groups; stop a repeated/no-op split. Small children below 5 can remain small explicit communities; do not forcibly attach them to a semantically unrelated sibling. An oversized unsplittable leaf is a valid reported outcome. These thresholds are navigation defaults.

Each parent contains its children by construction. Do not assume partitions obtained by an unconstrained resolution sweep are nested. Keep cross-cutting semantic groups and extension-family memberships outside this strict tree.

Choose a few representative members with complementary rules: a verified public entry point, a central node under the projection, and a semantic medoid/near-centroid exemplar. Use `nx.pagerank` as one centrality input, not an importance verdict. Always retain coverage of interfaces and isolated public operations. Cache representative evidence pointers, not copies of all neighbor bodies.

## 9. Extractive labels and descriptions

### 9.1 Candidate phrases come from sources

Generate candidates from source/document headings, upstream description phrases, doc aliases, registry names, qualified symbol names and existing reviewed labels. Identifier splitting is allowed through a recorded transform: `PhysicalOptimizerRule` -> `Physical Optimizer Rule`, `record_batch_stream` -> `record batch stream`. Preserve original spelling, acronym boundaries and source references; do not invent expansions for unknown abbreviations.

Keep each source block separate while generating one-to-three-word phrase candidates. Never concatenate member documents before n-gram extraction: the final word of one function description and the first word of another must not form a candidate phrase.

Use `CountVectorizer` with a tooling-owned tokenizer/analyzer policy and a conservative stop list for documentation boilerplate. Preserve meaningful negation in retrieval text. Label-token filtering is a separate recipe and must not change the underlying contracts or source statements. [S19]

### 9.2 Aggregate counts, then use class-based TF-IDF

Let `X` be a source-block-by-term sparse count matrix. Let `M` be a group-by-source-block membership matrix. Compute `C = M @ X`. For a disjoint structural partition the memberships are simple 0/1. For overlapping groups, either label each sibling/cohort family independently or divide one block's contribution among its selected groups; record the choice. Do not let one ubiquitous source paragraph dominate every concept.

Use the class-based TF-IDF formula documented by BERTopic without requiring BERTopic's complete pipeline:

```python
import numpy as np
from scipy import sparse
from sklearn.preprocessing import normalize


def class_tfidf(class_counts: sparse.csr_matrix) -> sparse.csr_matrix:
    """Own small implementation of the documented default c-TF-IDF formula."""
    counts = sparse.csr_matrix(class_counts, dtype=np.float64)
    if counts.shape[0] == 0 or counts.shape[1] == 0:
        return counts
    if not np.isfinite(counts.data).all() or (counts.data < 0).any():
        raise ValueError("Counts must be finite and nonnegative")
    row_lengths = np.asarray(counts.sum(axis=1)).ravel()
    average_length = float(row_lengths.mean())
    if average_length == 0:
        return counts
    term_totals = np.asarray(counts.sum(axis=0)).ravel()
    idf = np.zeros_like(term_totals)
    present = term_totals > 0
    idf[present] = np.log1p(average_length / term_totals[present])
    tf = normalize(counts, norm="l1", axis=1)
    return (tf @ sparse.diags(idf)).tocsr()
```

This is an application-owned function using NumPy/SciPy/scikit-learn, not a claim that `TfidfTransformer` computes class-based TF-IDF by default. `bertopic.vectorizers.ClassTfidfTransformer` is the direct built-in alternative if BERTopic is already a justified dependency; it is not necessary here. [S20]

Rank top phrases by c-TF-IDF, then prefer terms present in several representative members and supported by strong naming surfaces such as a common trait or source heading. Tie-break deterministically by normalized phrase and source identity. A phrase's occurrence is label evidence, not support for a behavioral claim.

The first implementation can choose the highest-scoring admissible phrase as `preferred_label`, retain up to five alternatives, and add a scope suffix when two sibling labels collide. Use the same recipe for subsystem groups and FCA concepts, but compare within the appropriate sibling/context population rather than one unrelated global corpus.

### 9.3 Label contract and fallbacks

`ConceptLabel` records concept/run reference, display text, normalized form, exact source/identifier selections, transformation, rank components, recipe, and status (`source_phrase`, `identifier_transform`, `selector_fallback`, optionally `reviewed_override`).

When candidates are absent or indistinct, use an honest selector-based label such as `Operations producing <type>` or `Implementations of <trait>`; otherwise use the qualified scope plus a stable short concept ID. Mark it low-specificity. Do not request an LLM to fabricate a fluent label in order to make the build pass.

Generate short descriptors from templates listing common supported contracts, representative entry points, external interfaces and unresolved dimensions. A later agent may polish a label or draft an explanation through normal review, without changing the underlying membership or qualification automatically.

## 10. Formal Concept Analysis

### 10.1 What the formal context means

Use FCApy to derive concepts from an **evidence-backed object–attribute matrix**, not from cosine similarity. An object is a profile-scoped operation/family. An attribute is a versioned selector over recorded contract fields, reviewed statements or supported mechanism outputs.

Initial attribute examples:

```text
declared_async
receiver_is_shared_reference
declared_success_output_contains_<nominated_type>
requires_implementation_of_<nominated_trait>
has_required_associated_type
has_recorded_configuration_read
has_reviewed_registration_role
```

These are not equivalent to `nonblocking`, `no_mutation`, `bounded_memory`, or `active_at_runtime`. Nominal/type-declaration observations must retain their narrower meaning.

Store an `AttributeAssessment` with value `supported`, `refuted`, `unknown`, `not_applicable`, or `conflicting`, plus support and scope. Preserve distinctions rather than reducing the authoritative evidence to booleans.

The default boolean matrix means **positive support is present**. `False` means no admitted positive support in this matrix; it does not mean the library property is false. Name resulting concepts accordingly: they group operations sharing supported attributes. A stronger complete-property context can be constructed only when its selected attributes are fully assessed under an adequate scope/model. Explicit negative attributes require actual qualified negative evidence; unknowns never become negative attributes.

### 10.2 Scope and budgets

Construct bounded contexts by coherent library/profile and a declared operation or extension family. Structural communities can nominate additional local cohorts, but do not make one community the only possible boundary: cross-cutting extension families may span several subsystems.

Initial bounds: at most 256 objects and 24 selected attributes per context, 60 seconds wall time, and a 20,000-concept output cap. These are safety limits, not proof the computation will finish. Concept lattices can grow combinatorially even below those input limits.

Apply the existing process supervision to the FCA task. A timeout/memory kill produces a failed/incomplete analysis record, not a partial graph labeled a complete lattice. An output cap checked after enumeration does not bound enumeration cost; enforce the process budget during computation and reject an oversized result. An alternate bounded closure-seed mode may be added later but must not impersonate full lattice enumeration.

If the cohort exceeds input limits, subdivide using an explicit family/context recipe and record the original denominator and exclusions. Do not arbitrarily take the first 256 operations or conceal omitted attributes.

### 10.3 Built-in APIs

```python
from fcapy.context import FormalContext
from fcapy.lattice import ConceptLattice

context = FormalContext(
    data=positive_support_matrix,  # list[list[bool]]
    object_names=ordered_operation_ids,
    attribute_names=ordered_attribute_ids,
    description="Profile-scoped positive-evidence context",
)
lattice = ConceptLattice.from_context(context, algo="CbO")
hierarchy = lattice.to_networkx(direction="down")
```

Choose the exact `CbO` route; do not silently use the package's decision-tree/random-forest approximations. `FormalContext` exposes `extension`/`intention` (and index-based counterparts) for closed-set checks; `ConceptLattice` exposes a NetworkX hierarchy. [S21, S22]

Use application-owned IDs for contexts, attributes and formal concepts. Export each concept's extent (objects) and intent (shared attributes) as member/attribute tables; attach exact supporting assessments. Do not use a lattice node's integer as a persistent identity.

### 10.4 Required mathematical and semantic checks

For every retained formal concept `(extent, intent)`, validate the derivation operators in the exact recorded context:

```text
extension(intent) = extent
intention(extent) = intent
```

Within one context, a more specific concept has a smaller/equal extent and a larger/equal intent. Use this order to derive the FCA hierarchy. The empty-extent bottom may satisfy all attributes vacuously; retain it for mathematical integrity but normally hide it from user-facing capability recommendations.

A lattice edge means `more_specific_supported_attribute_set`, not necessarily class inheritance or a real-world behavioral subtype. Never elevate an empirical attribute implication into a universal library guarantee. Do not compute inclusion across incompatible contexts/profiles and label it a subtype relation.

Structural communities and FCA concepts are complementary: a community explains cohesion; a formal concept explains an exact conjunction of recorded properties. Store both and link their overlapping members rather than choosing one to replace the other.

## 11. Concept graph and programmatic navigation

### 11.1 Small explicit schema; discovered instances

Keep the ontology schema explicit and compact. Derive its instances, memberships and navigation from selectors, communities, formal contexts and source labels.

Node kinds:

```text
SubsystemCommunity
SemanticCapabilityGroup
ExtensionContractFamily
FormalSupportConcept
CapabilityCandidate
ReviewedCapability
ProblemClass (only when explicitly sourced/authored)
```

Relation kinds must retain their different semantics:

```text
member_of_community
satisfies_supported_attribute
implements_declared_contract
broader_topic / narrower_topic
more_specific_supported_attribute_set
candidate_alternative_to
related_by_semantic_similarity
candidate_realization_of
supported_by / reviewed_as
```

Do not manufacture `is_a`, `part_of`, or `depends_on` from undirected similarity. Retain the source relation direction and policy that actually supports each meaning. A SKOS-like label/broader/related representation is useful for navigation; an RDF/OWL server is not required. [S24]

### 11.2 Three separate derivation routes

**Architecture:** structural communities -> recursive containment -> source-derived labels -> subsystem navigation.

**Extension/use contracts:** exact trait/protocol/registry-family selectors -> related operation/implementation sets -> source-derived labels -> extension navigation.

**Attribute semantics:** scoped assessments -> FCA lattice -> labeled attribute concepts -> property-driven exploration.

Semantic groups supply cross-links and alternative candidates to all three. A fused community view can propose additional groupings; it does not overwrite their membership provenance.

This is how to produce useful analogues of “Query interface”, “Planning”, “Execution” and “Extensibility” without forcing that exact tree onto every library. “Extensibility” can be an explicit generic lens over recorded extension contracts; its individual families and members are derived. An algorithm need not rediscover a particular English heading to be correct.

### 11.3 Identity, overlaps, and trees

A concept occurrence ID depends on its kind, context, membership/intent and derivation recipe. A cross-generation concept identity may be reused only through an explicit reconciliation record; a changed label alone does not change membership identity. Ordinals, centroids and display labels are not entity keys.

Store membership overlaps as relations. For navigation, select one declared primary parent per view where a tree is required; retain other parents as cross-links. A different view may select a different parent without changing the underlying graph.

Use `nx.is_directed_acyclic_graph` and `nx.transitive_reduction` only on relations with a valid DAG/order meaning, such as one FCA context's order or recursive containment. NetworkX transitive reduction does not preserve attributes automatically: reattach node metadata and direct-edge support after reduction. Never reduce a mixed graph of dependencies, alternatives and topic relations as though all edges were transitive. [S23]

Persist all derivation and labeling inputs. An LLM is optional for interpretation or reviewed wording; it is not required to generate these memberships, labels or concept orders.

## 12. Retrieval and agent-facing execution

### 12.1 Search-view membership must be explicit

Define `search_view_id` as a content-addressed selection of evidence snapshot, admitted unit revisions, embedding recipe and renderer policy. Add it as a top-level scalar column to the materialized search table. The corpus manifest selects this view and exact table version. It must not include its own storage version in its content hash.

This provides a simple prefilter and prevents historical, orphaned or incompatible unit revisions from entering a query. A first implementation may materialize complete selected rows for each search view while reusing cached inference results. This duplicates some physical search rows but not inference work or fact authority. Later storage optimization must retain exactly the same membership semantics.

Analytical outputs similarly record their input evidence snapshot and recipe. The corpus manifest then selects them. Avoid circular keys such as “analysis ID hashes a manifest that contains that same analysis ID.”

### 12.2 Typed query contract

Extend the active reader with `DiscoverRequest` containing:

```text
query_text
corpus_generation_id / selected search_view_id
library/package/profile selection
exact identifiers and optional declared required attributes
matching mode: exact | nominal | exploratory
availability policy: documented | compiled | include_unknown
review policy: reviewed_only | candidates_allowed
result/neighbor/evidence/token budgets
```

Do not automatically convert a free-text requirement into a verified constraint. The agent may provide typed requirements; phrase/embedding matches can only nominate them. Return rejected/unknown applicability separately when that explains a choice.

### 12.3 First-stage retrieval

Use three entry channels: exact path/alias lookup, lexical BM25, and dense semantic retrieval. Exact identity resolution remains independent of ranking.

Start with **exact flat vector search**, not an approximate index requirement. This is a correctness-first deployment choice appropriate until corpus size demonstrates otherwise. The SDK offers `bypass_vector_index()`; it also avoids accidentally changing semantics if an index is added later. [S6]

```python
dense_rows = (
    search_table.search(query_vector, vector_column_name="vector")
    .distance_type("cosine")
    .where(validated_scope_filter, prefilter=True)
    .bypass_vector_index()
    .select(["unit_revision_id", "entity_id", "unit_kind", "search_view_id"])
    .limit(50)
    .to_arrow()
)

lexical_rows = (
    search_table.search(query_text, query_type="fts", fts_columns="search_text")
    .where(validated_scope_filter, prefilter=True)
    .select(["unit_revision_id", "entity_id", "unit_kind", "search_view_id"])
    .limit(50)
    .to_arrow()
)
```

These are bounded result materializations. For graph/full-family reads, use the streaming complete-scan route instead. Do not use `fast_search` in a route that must include the unindexed tail. [S6, S10]

LanceDB also provides a convenient combined route with explicit vectors, so the database need not call the embedder itself:

```python
from lancedb.rerankers import RRFReranker

hybrid_rows = (
    search_table.search(
        query_type="hybrid",
        vector_column_name="vector",
        fts_columns="search_text",
    )
    .vector(query_vector)
    .text(query_text)
    .where(validated_scope_filter, prefilter=True)
    .distance_type("cosine")
    .bypass_vector_index()
    .rerank(RRFReranker())
    .limit(50)
    .to_arrow()
)
```

Use either the explicit channel implementation or this combined baseline; do not count both as independent channels. Separate channels make entity-level deduplication and explanatory ranks easier. Test the chosen SDK's exact builder chain in the compatibility canary. [S25]

For several channels, use an application-owned RRF combiner: sum `channel_weight / (60 + rank)` across channels after per-channel entity deduplication. Keep the strongest hit per entity per channel, plus its other useful support units, so having many chunks does not itself boost an operation's score. The constant 60 and equal initial channel weights are engineering defaults; no numerical similarity threshold is treated as a guarantee of relevance.

### 12.4 Graph, community, and FCA expansion

For the first 20 candidate entities, retrieve bounded typed neighbors:

* Required/associated types, constraints and public routes needed to invoke the operation.
* Built-in implementations and alternatives from the relevant exact family universe.
* Examples and mechanism units tied to the operation.
* Community representatives and interfaces that explain architectural position.
* Formal concepts containing the operation or satisfying explicitly requested attribute conjunctions.

Default expansion budget: up to two selected-relation hops, 200 entities, 500 projected edges, and the existing packet byte/token limits. These are hard execution limits with an omitted-count/cursor report; they are not a claim that two hops closes semantic dependencies. Qualification obtains its own exact required support closure and cannot accept a truncated proof.

Do not fill the whole packet with graph neighbors at the expense of globally retrieved alternatives. Reserve at least one candidate lane for semantically relevant results outside the seed community. Parent/community context is explanatory; it does not automatically increase an API's relevance score or qualification.

FCA provides exact **attribute-conjunction selection** under its recorded evidence semantics. A request for “operations with a declared shared-reference receiver and recorded configuration reads” can query those attributes directly. A request for “thread-safe nonblocking operations” needs adequate attributes/evidence for those stronger properties; similar words cannot substitute.

### 12.5 Result and packet structure

Each candidate response should contain:

```text
entity and routes; relevant unit IDs
why returned: exact/lexical/dense/family/community/FCA reasons
rank components (not truth scores)
recorded applicability; unresolved constraints and native/opaque boundaries
relevant alternative universe and exclusions
supported facets and missing evidence
source/fact selections and required review state
continuations for omitted evidence
```

Relevance selection, applicability checking and claim qualification remain separate functions. Source text is untrusted content; documentation cannot change query policy, budgets, tool execution permissions or approval state.

A learned reranker is deliberately deferred. The initial system implements real retrieval, typed expansion, source labels and concept matching without another GPU-resident model. Its extension interface may later rescore bounded candidates, but cannot override hard constraints or review policy. No extensive embedding comparison or numerical model-quality gate is required for completion.

## 13. Caching, invalidation, and lifecycle

Extend the V2 digest/dependency model instead of hashing the whole tooling package or all source data into every product.

| Change | Required work |
|---|---|
| Raw source movement with equivalent relevant content | Refresh anchors/provenance; reuse rendering/vector only after exact recipe/input checks; review reuse still needs V2 revalidation |
| Relevant declaration, condition or documentation changes | Re-render affected units; re-embed changed text; recompute dependent projections/concepts and candidate decisions |
| Embedding model/tokenizer/prompt changes | New embedding-space recipe/search view; regenerate semantic neighbors/fused groups; structural evidence remains reusable |
| Graph projection/Leiden settings change | New graph/community derivations and labels; source extraction does not rerun |
| Label recipe changes | Recompute labels/descriptors; do not recreate base entity embeddings or use label agreement as validation |
| Attribute recipe or assessment changes | Rebuild affected formal contexts/lattices and their dependent selectors |
| A new implementation/alternative appears | Update candidate-universe dependencies and reopen relevant decisions, even if old cited APIs are unchanged |
| Review wording changes with unchanged unit source views | Requalify affected authored records; source observations and unrelated embeddings remain reusable |
| Table compaction/index maintenance | New physical bindings/manifest where needed; logical evidence IDs remain stable |

An unchanged warm build should invoke no source workers and no embedding calls. A lexical-index change should not rerun MIR. A source-only pilot can finish while the embedding service is stopped, but its semantic-search product reports pending/incomplete status rather than pretending to be current.

Retain explicit disk budgets and garbage-collection reports. Keeping all historic fact revisions and 4096-dimensional vectors indefinitely has a storage cost; define deletion eligibility through retained corpus/guide manifests, tags and support closure. Never prune data that a published exact citation or scope certificate still requires.

## 14. Integration into the active codebase

The following module names are proposed additions, not claims about files already present:

```text
tooling/library_guides/
  library_guides/
    facts/
      store.py                      # keep interface; use primary Lance backend
      arrow_schemas.py              # registry, typed schema adapters
      lance_store.py                # bounded reads, append-only admission
      corpus_manifest.py            # exact versions + membership + heads
      blob_store.py                 # byte ranges and exact reconstruction
      parquet_bundle.py             # portable export/import
    retrieval/
      contracts.py                  # attrs/cattrs request/unit/view DTOs
      rendering.py                  # source-grounded text views
      chunking.py                   # semantic boundaries + token budget
      embedding_recipe.py           # model/runtime/input fingerprints
      vllm_client.py                # typed HTTP and validation
      search_views.py               # explicit current unit memberships
      hybrid.py                     # exact/FTS/dense/RRF
      expansion.py                  # typed graph/family/FCA neighborhoods
    analyses/
      graph_projection.py           # read selected fact families
      graph_adapters.py             # NetworkX -> igraph only here
      communities.py                # structural, semantic, fused, recursive
      semantic_neighbors.py         # bounded cosine kNN
      label_phrases.py               # source phrase inventory
      labels.py                     # sparse counts + c-TF-IDF
      attributes.py                 # finite evidence-backed selectors
      formal_concepts.py            # supervised FCApy adapter
      concept_views.py               # typed graph and navigation
    assets/
      analyses/                     # projection/attribute/label recipes
      schemas/                      # normalized and physical schema metadata
      deployment/                   # distributable Compose template/config
  tests/
    database/ embeddings/ graphs/ labels/ fca/ retrieval/ publication/
```

Integrate these through existing `source_pipeline.py`, `build_system.py`, `nominations.py`, `reader.py`, `authoring.py`, `impact.py`, `qualification.py`, and `generations.py`. Do not build a second authoring CLI or copy the root application's extraction services.

### 14.1 Owned service interfaces

Define typed interfaces before changing storage callers. Names below are application APIs to implement, not third-party methods:

```text
CorpusStore.open_generation(generation_id) -> CorpusReader
CorpusStore.stage_batch(run_id, family, validated_batch) -> StagedChunk
CorpusStore.commit_run(run_id, expected_predecessor) -> CorpusManifest
CorpusReader.scan(family, typed_selector, columns, budget) -> BatchCursor
CorpusReader.resolve_evidence(selection) -> ExactEvidence
CorpusReader.read_blob_range(digest, start, end) -> VerifiedBytes

RetrievalUnitBuilder.build(entity_or_facet, scope) -> UnitBuildResult
EmbeddingService.embed(inputs, recipe) -> ValidatedEmbeddingBatch
SearchViewBuilder.materialize(selection, embedding_recipe) -> SearchView

GraphProjector.build(spec, corpus) -> GraphProjection
CommunityAnalyzer.run(projection, recipe) -> CommunityRun
Labeler.label(groups, phrase_inventory, recipe) -> LabelRun
AttributeEvaluator.assess(cohort, recipes) -> AttributeAssessments
ConceptAnalyzer.build(context_spec, assessments) -> FormalConceptRun
ConceptViewBuilder.build(selected_runs) -> NavigationViews

LibraryDiscovery.discover(request) -> CandidatePacket
```

Each result carries a completion disposition, exact inputs, limits and derivation identity. Iterators/cursors must not silently hide unsupported records or terminate at a query default.

### 14.2 Dependency policy

Tooling Python dependencies: existing attrs/cattrs stack plus `lancedb`, `pyarrow`, `networkx`, `igraph`, `leidenalg`, `numpy`, `scipy`, `scikit-learn`, `fcapy`, `httpx`, and `transformers` for the pinned tokenizer. `tokenizers` may be transitive; record its resolved version. Existing Markdown/RST parsers continue to own document structure.

vLLM/PyTorch/CUDA live in the container, not in the tooling environment. The chosen checkpoint and image are explicitly acquired/pinned. There is no requirement to install SentenceTransformers in the application merely to call vLLM, or to add Pydantic through LanceDB's optional schema helpers.

Resolve compatible versions in the existing standalone lock, run the canaries below, then record exact package versions and image/model digests. This specification deliberately does not fabricate a supposedly tested complete dependency pin set. A publicly documented API is not a wheel/platform compatibility certificate.

## 15. Implementation work packages and acceptance

### 15.1 Delivery sequence

| Extension | Existing WP integration | Executable result |
|---|---|---|
| A. Arrow contracts + Lance corpus storage | WP01/WP03/WP10 | Existing retained facts ingest, exact citations resolve, immutable manifest publishes, crash recovery works |
| B. Pinned local Qwen/vLLM service | WP00/WP03 | Real 5090 embedding request returns validated 4096-vectors; tokenizer and offline configuration recorded |
| C. Retrieval units + lexical/dense discovery | WP09/WP11 | D0 contract/doc units retrieve useful operations with exact scope and evidence |
| D. NetworkX projections + Leiden + labels | WP09 | Real structural communities and source-backed names; isolates and uncertainty retained |
| E. Attributes + FCA + concept views | WP09 | Exact bounded contexts produce verified closure/order and meaningful cross-cutting groups |
| F. Combined discovery and maintenance | WP10/WP11 | Query returns alternatives, facets, examples and reasons; mutations invalidate the correct products |
| G. Portable publication + pilot | WP11/WP12 | Bundle imports on another local installation; reviewed guide reads without vLLM or native extractors |

Deliver a complete D0-only vertical slice before waiting for full MIR coverage. Add mechanism units as the existing lanes become available. The final scope still includes source-lane, full-pilot and review requirements from V2; this extension does not declare the original plan complete merely because clustering works.

### 15.2 Correctness fixtures, not a model tournament

| Fixture | Required result |
|---|---|
| attrs -> Arrow -> Lance -> Arrow -> attrs | Exact supported field/qualifier retention; unknown states do not become false/empty |
| Recursive type/family storage | Ordered wrappers/bounds/associated links survive without relying on rendered strings |
| Duplicate record ID with different content | Admission fails; immutable evidence is never overwritten |
| Crash between table writes / before corpus head | Previous corpus remains readable; orphan rows excluded by selected membership |
| Concurrent writer / predecessor conflict | Exactly one coherent head advances; no mixed artifact generations |
| Old table version/tag retention | Published evidence still resolves after allowed maintenance |
| Full projection with more than ten records | All declared eligible rows consumed or a visible budget disposition; no default-limit truncation |
| Raw bytes / Unicode / source maps | Exact original byte ranges survive database storage and Parquet bundle round trip |
| Embedding service canary | Correct result cardinality/indexes/dimension/finiteness, nonzero normalized vectors, prompt role and recipe recorded |
| Embedding outage / OOM / malformed response | Pending or failed job; no zero vectors, silent model substitution or complete-success receipt |
| Chunk boundary exception | “Except when…” and applicable bounds remain with the claim or in a required linked qualifier |
| Two dense graph groups with a bridge | Meaningful grouping on a deliberately controlled fixture; every node accounted for; exact graph recipe retained |
| Isolated public API | Still discoverable and marked unclassified/singleton, never dropped |
| Negative/uncertain impl or call | Does not silently enter a certain applicable-implementation set |
| Multiplex mapping | Same entity order across layers; layer normalization and membership agreement verified |
| Label extraction | Every nonfallback label traces to a source phrase or recorded identifier transform; no cross-document phrase invented |
| c-TF-IDF | Hand-computable sparse fixture matches formula, handles zero rows/terms without NaN |
| FCA closure | Extent/intent round trips, hierarchy order and empty-extent treatment correct |
| Unknown attribute | Not advertised as a negative property; unsupported semantic implication rejected |
| FCA budget failure | Explicit incomplete/failed analysis; no incomplete lattice published as complete |
| Retrieval and graph expansion | Explicit profile, alternatives, exact support, frontier and continuation present within budgets |
| New competitor with old API unchanged | Candidate-universe dependency reopens relevant decision |
| Label-only change | Does not rerun source extraction or base entity embeddings |
| Unchanged warm build | Zero lane worker invocations and zero embedding requests |
| Portable qualified bundle | Evidence closure and current reviews resolve with no original local cache/venv/model service |

Use the existing 24 qualitative pilot tasks to check that agents actually find the needed built-ins, limitations and alternatives. Attribute reviewers and retain unresolved gaps. No broad ranking benchmark, model comparison, automatic LLM judge, or metric threshold is a prerequisite. Deterministic checks plus concrete end-to-end task evidence establish whether the implementation works.

### 15.3 Completion standard for the programming agent

Do not finish with only schemas, CLI names, mock vectors, empty graphs or screenshots. Demonstrate one complete chain:

```text
real frozen D0/doc observations
 -> typed Lance records and exact corpus manifest
 -> source-grounded contract units
 -> real local Qwen vectors
 -> structural/semantic communities + extractive labels
 -> evidence-backed attributes + verified FCA concepts
 -> task query with relevant alternatives and constraints
 -> existing packet/proposal/review path
 -> qualified portable guide and a tested invalidation mutation
```

If a dependency/platform feature is unavailable, record the exact blocked capability and preserve unaffected source/retrieval functions. Do not claim a consumer-GPU deployment, native extraction pass or downstream integration has been tested without actually executing it.

## 16. Default configuration

The values below are initial policy choices, not validated performance promises. Keep them in typed config under the existing packaged assets and user-local deployment config.

```yaml
storage:
  backend: lancedb
  uri: /absolute/local/path/library-intelligence.lancedb
  single_writer: true
  batch_rows: 4096
  raw_blob_chunk_bytes: 4194304
  retained_generation_tags: true
  automatic_version_pruning: false
  portable_format: parquet

embedding:
  model: Qwen/Qwen3-Embedding-8B
  model_revision: REQUIRED_EXACT_REVISION
  service_url: http://127.0.0.1:8000/v1
  served_model_name: library-qwen3-embedding
  dimension: 4096
  inference_dtype: bfloat16
  storage_dtype: float32
  normalize: l2
  document_max_tokens: 2048
  service_max_tokens: 4096
  prompt_policy: qwen_query_instruction_document_plain_v1

retrieval:
  vector_mode: exact_flat
  lexical_index: native_fts
  per_channel_limit: 50
  seed_entity_limit: 20
  rrf_constant: 60
  graph_hops: 2
  graph_node_limit: 200
  graph_edge_limit: 500
  learned_reranker: null

communities:
  backend: igraph_leidenalg
  objective: RBConfigurationVertexPartition
  resolution: 1.0
  seed: 13
  iterations: until_no_improvement
  process_timeout_seconds: 120
  primary_view: architecture_structural
  retain_views:
    - architecture_structural
    - capability_semantic
    - architecture_semantic_fused
  semantic_neighbors: 15
  semantic_edges: mutual_positive_cosine
  fusion_layer_weights: [0.75, 0.25]
  normalize_layer_total_weight: true
  recursive_split_above_nodes: 80
  hierarchy_max_depth: 3

labels:
  method: source_phrase_ctfidf
  ngram_range: [1, 3]
  alternative_labels: 5
  source_boundaries_preserved: true
  allow_generative_fallback: false

formal_concepts:
  backend: fcapy
  algorithm: CbO
  context_semantics: observed_positive_support
  max_objects: 256
  max_attributes: 24
  max_output_concepts: 20000
  process_timeout_seconds: 60
  expose_empty_extent_to_recommendations: false
```

Exact memory limits for CPU graph/FCA workers belong to the existing machine budget configuration. The supplied time/input limits supplement, not replace, memory enforcement.

## 17. Source map and API references

### Baseline attachment

`library_guide_source_semantic_evidence_lanes_implementation_plan_v2_2026-09-11.md` is the authoritative supplied design baseline. This extension deliberately changes primary fact storage and adds a local inference service, clustering, extractive labels and FCA. It does not change the evidence qualification, extraction ownership, exact profile/source semantics, or immutable reviewed publication requirements.

Key baseline line anchors: 15–23 (purpose/boundary), 169–171 (ownership/original storage), 232–257 (contracts), 350–378 (transport), 390–422 (D0), 447–455 (examples), 591–634 (analysis/claims), 636–671 (invalidation), 675–699 (workflow), 707–723 (work packages), 772–807 (pilot/gates). These anchors refer to the provided file's indexed line numbering.

### Official public references researched

- **S1 — NetworkX Leiden backend requirement:** https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.community.leiden.leiden_communities.html
- **S2 — NetworkX community algorithms:** https://networkx.org/documentation/stable/reference/algorithms/community.html
- **S3 — leidenalg functions, objectives and optimizer:** https://leidenalg.readthedocs.io/en/stable/reference.html
- **S4 — leidenalg multiplex optimization:** https://leidenalg.readthedocs.io/en/stable/multiplex.html
- **S5 — LanceDB table creation and Arrow input:** https://docs.lancedb.com/tables/create
- **S6 — LanceDB Python API reference:** https://lancedb.github.io/lancedb/python/python/
- **S7 — Lance table transaction model:** https://lance.org/format/table/transaction/
- **S8 — LanceDB versions, tags and cleanup:** https://docs.lancedb.com/tables/versioning
- **S9 — LanceDB scalar indexes:** https://docs.lancedb.com/indexing/scalar-index
- **S10 — LanceDB native full-text search:** https://docs.lancedb.com/search/full-text-search
- **S11 — PyArrow Parquet:** https://arrow.apache.org/docs/python/parquet.html
- **S12 — Qwen3-Embedding-8B model card:** https://huggingface.co/Qwen/Qwen3-Embedding-8B
- **S13 — vLLM embedding/pooling usage:** https://docs.vllm.ai/en/stable/models/pooling_models/embed/
- **S14 — vLLM GPU installation/compatibility:** https://docs.vllm.ai/en/stable/getting_started/installation/gpu/
- **S15 — vLLM official Docker deployment:** https://docs.vllm.ai/en/stable/deployment/docker/
- **S16 — Docker Compose GPU reservations:** https://docs.docker.com/compose/how-tos/gpu-support/
- **S17 — NVIDIA Container Toolkit installation:** https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html
- **S18 — scikit-learn NearestNeighbors:** https://scikit-learn.org/stable/modules/generated/sklearn.neighbors.NearestNeighbors.html
- **S19 — scikit-learn CountVectorizer:** https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.CountVectorizer.html
- **S20 — BERTopic c-TF-IDF implementation/formula:** https://maartengr.github.io/BERTopic/api/ctfidf.html
- **S21 — FCApy FormalContext:** https://fcapy.readthedocs.io/en/latest/generated/fcapy.context.FormalContext.html
- **S22 — FCApy ConceptLattice:** https://fcapy.readthedocs.io/en/latest/generated/fcapy.lattice.ConceptLattice.html
- **S23 — NetworkX transitive reduction:** https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.dag.transitive_reduction.html
- **S24 — W3C SKOS Reference:** https://www.w3.org/TR/skos-reference/
- **S25 — LanceDB explicit-vector hybrid queries and RRF:** https://docs.lancedb.com/search/hybrid-search
- **S26 — PyArrow dataset scanning:** https://arrow.apache.org/docs/python/generated/pyarrow.dataset.Dataset.html
- **S27 — NetworkX graph types:** https://networkx.org/documentation/stable/reference/classes/multidigraph.html
- **S28 — NetworkX condensation:** https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.components.condensation.html
- **S29 — NetworkX immediate dominators:** https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.dominance.immediate_dominators.html

Documentation APIs and platform compatibility can evolve independently. Pin installed versions after the local compatibility canaries, retain these recipe contracts, and treat upgraded public documentation as a reason to check adapters—not as automatic permission to change a reviewed corpus.
