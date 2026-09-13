# Library-intelligence implementation handoff

Start with **IMPLEMENTATION_SPEC.md**. It finalizes a local LanceDB/Arrow evidence store, NetworkX with an igraph/leidenalg adapter, Qwen3-Embedding-8B through vLLM, source-derived labels, and FCApy formal concepts.

The original supplied plan is included unchanged as `library_guide_source_semantic_evidence_lanes_implementation_plan_v2_2026-09-11.md`. The new specification is an extension, not a replacement for its extraction lanes, exact evidence semantics, review gates or standalone-codebase boundary.

## Files

| File | Purpose |
|---|---|
| `IMPLEMENTATION_SPEC.md` | Architecture, typed tables, corpus commits, algorithms, source-linked APIs, integration, defaults, work packages and tests |
| `compose.yaml` | Local vLLM service template; requires a tested pinned image and downloaded pinned model snapshot |
| `.env.example` | Required deployment-variable examples; no automatically selected moving model/image |
| `default_config.yaml` | Initial application policy; validate through the existing typed configuration system |
| `ctfidf_reference.py` | Small independently checked numerical helper for extractive group labels |
| `VALIDATION_NOTES.json` | Exact checks performed and integrations not executed |
| `library_guide_source_semantic_evidence_lanes_implementation_plan_v2_2026-09-11.md` | Unmodified supplied baseline |

## Instructions to the implementing agent

Work only within `tooling/library_guides/` and its standalone tooling/dependency boundary. Inspect the active code paths named by the baseline before editing. Preserve attrs/cattrs and the existing authoring/qualification/publication authority. Do not import other repository extractors or change the root application workspace/toolchain.

Implement the work packages in specification section 15, starting with retained D0/document evidence and a complete small vertical slice. Replace the physical shard/SQLite fact-store strategy with typed LanceDB tables and explicit corpus manifests; preserve logical scope, receipts, exact selectors and semantic/provenance digests. Treat the local vLLM daemon as an inference service, not a source watcher or automatic review runner.

Use real embeddings and real library facts in the end-to-end demonstration. Keep unknowns, unsupported surfaces and candidate versus reviewed status visible. Do not call the system complete because classes, tables or commands exist. Run the source-plan gates plus the new database, inference, graph, labeling and FCA correctness fixtures.

Pin the actual package lock, model revision and container image after compatibility smoke tests on the target machine. No extensive model comparison or throughput tuning is a prerequisite. The deployment template is not a claim that this exact launch has already run on an RTX 5090.

## Validation status

The specification's Python snippets were syntax-checked; both YAML documents parsed; the independent c-TF-IDF helper passed small numerical and error-handling checks. LanceDB/Leiden/FCA integrations, Docker/vLLM, the target GPU, and the user's repository were not executed here. See `VALIDATION_NOTES.json` for details.
