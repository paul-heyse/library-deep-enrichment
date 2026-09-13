# Library guides: admitted evidence and semantic decisions

This standalone tooling package retains source bytes, contextual declarations,
semantic models, checked consequences, task comparisons, and releases in one
LanceDB/Arrow corpus. It does not depend on SMARTREF's application runtime.
Markdown guides are generated views of the admitted records.

The active implementation and its remaining gates are recorded in
[pilot/intelligence/STATUS.md](pilot/intelligence/STATUS.md). Use
[the continuation handover](pilot/intelligence/RESUME_AFTER_REBOOT.md) for this
workspace. Earlier collections, YAML authoring files, SQLite indexes, and
publication directories are archival inputs; they are not active query or
publication authorities.

## Environment and current corpus

Use `tooling/library_guides/.venv/bin` explicitly from the repository root.
Do not synchronize the root environment to run this tool. The present tooling
`pyproject.toml` and lockfile include concurrent dependency work; do not rewrite
them incidentally during continuation.

The complete implementation qualification uses a separate 125-package environment
at `.cache/library-guides-implementation/completion-20260912T220757Z/full-environment`.
The installed-wheel qualification uses another fresh environment. Neither replaces
the working tooling environment. From this tooling directory, use an explicit
`UV_PROJECT_ENVIRONMENT` when installing the frozen all-extras lock into a new
environment. The lock selects the declared PyTorch index and the retained
[metadata-corrected scikit-mine wheel](vendor/README.md); distribute that wheel
alongside an offline wheelhouse because its local version is not on public PyPI.

Analytical requests retain their resolved worker memory budget. The optional
`LIBRARY_GUIDES_ANALYTICAL_MEMORY_BYTES` setting accepts a positive integer up to
64 GiB; malformed values fail explicitly. The full-corpus refresh uses an
explicit 8 GiB worker limit. This bounds supervised worker RSS, not the
coordinator's admission memory. Failure receipts remain distinct from admitted
successes, and a named release remains readable while its analysis head advances.

The current main corpus is
`.cache/library-guides-intelligence/pilot-v4/corpus`. The CLI uses a finite
2,500,000-row scan bound. Direct Python `Corpus` calls must request this bound
for the expanded main corpus; the constructor otherwise defaults to 250,000.

```bash
tooling/library_guides/.venv/bin/library-guides \
  --corpus .cache/library-guides-intelligence/pilot-v4/corpus status

tooling/library_guides/.venv/bin/library-guides \
  --corpus .cache/library-guides-intelligence/pilot-v4/corpus records operations --limit 10

tooling/library_guides/.venv/bin/library-guides \
  --corpus .cache/library-guides-intelligence/pilot-v4/corpus build --stage shapes

tooling/library_guides/.venv/bin/library-guides \
  --corpus .cache/library-guides-intelligence/pilot-v4/corpus build --stage semantics
```

`build` executes the requested stage and admits its result. It is not the old
preview/build command. Stage inputs, producer identity, outputs, and failure
currentness are recorded through the coordinator. An unchanged stage performs
no producer work. Readers pin immutable manifests and physical table versions;
bounded batch reads enforce the same exact selected membership as point reads.

## Managed local embedding runtime

Runtime lifecycle actions plan by default; `--apply` executes the selected action.
The existing container must have the exact ownership label before it can be
started or stopped. The service binds loopback port 18080.

```bash
tooling/library_guides/.venv/bin/library-guides \
  --corpus .cache/library-guides-intelligence/pilot-v4/corpus \
  --runtime-root /home/paul/.cache/library-guides-intelligence \
  runtime --action start

tooling/library_guides/.venv/bin/library-guides \
  --corpus .cache/library-guides-intelligence/pilot-v4/corpus \
  --runtime-root /home/paul/.cache/library-guides-intelligence \
  runtime --action start --apply
```

Inspect actual model readiness in the owned container's logs, then run
`runtime --action canary --apply` with the same global options. `provision`,
`status`, and `stop` are also supported actions. Provisioning and startup verify
the pinned model's actual bytes. Lifecycle outcomes, including failures, are
retained under the runtime cache's `lifecycle/` directory. Query paths never
start a container or provision a model.

Qwen3-Embedding-8B produces 4,096-dimensional vectors through the pinned vLLM
image. Model/tokenizer byte identities, query/document recipes, normalization,
and numerical representation distinguish embedding spaces. Lexical discovery
remains usable when local initialization or inference fails. Actual-vector
qualification is separate from synthetic cache-protocol tests.

## Acquisition, discovery, and decisions

- `extract-native` runs an explicitly selected native producer through a tracked
  fabric stage. `import-native`, `import-declarations`, and `import-legacy` read
  retained acquisition inputs. `probe-registry` captures an installed adapter's
  actual registry. Use each command's `--help` for its required paths and context.
- `build --stage structure` produces source statements and parameter modes;
  `shapes` preserves contextual input/output wrappers; `semantics` derives
  qualified assertions, guarded modes, and capabilities under approved models.
- `build --stage retrieval`, `embeddings`, `graphs`, `concepts`, and `labels`
  produce analytical views. Embedding builds require an explicit runtime root.
  Retrieval, embedding, and graph builds accept `--scope SELECTOR.json` with
  explicit profiles, packages, native-artifact revisions, and a finite unit bound.
  The same scopes select FCA and source-label populations; excessive selections
  fail without truncation.
- `discover QUERY --profile PROFILE` returns lexical/dense relevance evidence.
  `discover-scoped QUERY SELECTOR.json` searches an explicitly built population.
  `match-task TASK.json` evaluates an independent operation universe;
  `--save` admits the comparison. `plan-evidence` and `why-unknown` expose the
  next finite evidence questions.
- `compose TASK.json` returns bounded multi-input plans. Admitted composition
  goals and approved invocation contracts add explicit intermediate semantic
  evaluations. An approved concrete specialization retains the original
  declaration's wrappers and requires a matching compiler/execution witness.
- `analyze-native REQUEST.json` runs the existing MIR flow/control/effect models
  over 1–200 exact owners from one admitted native artifact. Typed consequences
  are independently replayed on admission; unselected/external callees remain
  open frontiers. The command reads no legacy authoring and invokes no extractor.
- `records`, `evidence`, and `explain` resolve exact current or release records.
  `scan FAMILY` provides ordered manifest-pinned pages. `candidate-results
  COMPARISON_REVISION` pages the full candidate list; `sequence REQUEST.json`
  pages another exact nested array, such as a scope's sources or proof premises.
  Both retain the exact denominator and reject continuations from a different
  manifest, record, or field. A byte-limited value leaves the cursor unconsumed
  for narrower inspection. These bound the response; the selected typed record
  is still materialized internally.
  `admit` requires an attributed authority and predecessor. `install-pack`
  admits reusable model data; `--approve` records the named approval authority.

The current demonstration generates both `Schema::new_with_metadata → project`
and `Schema::new → project`. Modeled propagation rejects the latter when dataset
metadata must survive. Both exact Rust programs compile and execute, and the
finite observations corroborate the differing metadata results. See
[the generated comparison](pilot/intelligence/guides/generated-schema-composition.md)
and [its receipt](pilot/intelligence/reports/resume-generated-composition.json).
The same agent authored and reviewed the three concrete invocation mappings;
this is not independent review or general trait/borrow/availability inference.

The retained native scope is
`pilot/intelligence/scopes/arrow-schema-native.json`. For example:

```bash
tooling/library_guides/.venv/bin/library-guides \
  --corpus .cache/library-guides-intelligence/pilot-v4/corpus \
  build --stage retrieval --scope tooling/library_guides/pilot/intelligence/scopes/arrow-schema-native.json

tooling/library_guides/.venv/bin/library-guides \
  --corpus .cache/library-guides-intelligence/pilot-v4/corpus \
  --runtime-root /home/paul/.cache/library-guides-intelligence \
  discover-scoped 'preserve schema metadata' tooling/library_guides/pilot/intelligence/scopes/arrow-schema-native.json
```

Scope receipts retain exact independent populations and separate output ownership.
Stage input receipts retain exact selected populations, including empty selections
and newly admitted competitors. Profile, logical-ID and prefix selectors narrow
the dependency where declared. Field paths identify a stage's contract, while
currentness remains conservative at whole-record revision granularity; a field-only
semantic equivalence optimization is not claimed. Zero producer work on a warm
build does not imply zero planning/read-set cost.

## Publication and portable readers

`release COMPARISON_REVISION` rechecks an admitted task comparison, resolves its
evidence closure, and advances a named release head. `export DESTINATION`
exports that selected view; `import SOURCE` restores a supported portable view.
The typed `publication.compositions.publish` entry point uses the same closure
and coordinator to publish modeled plans and finite witnesses.

```bash
tooling/library_guides/.venv/bin/library-guides \
  --corpus /path/to/corpus export /path/to/new-export

tooling/library_guides/.venv/bin/library-guides \
  --corpus /path/to/clean-corpus import /path/to/new-export
```

Original byte objects and required model/review authority travel with the release.
Selected objective evidence and admitted counterfactual comparisons also enter
that closure and the generated guide. Lexicographic selection uses the best
fully observed objective tuple while retaining candidates with unknown values.
Installed-wheel qualification uses all 125 declared runtime distributions inside
a network-isolated namespace with original source trees, native workers, GPU
service and model cache unavailable. It verifies guides, paging, export/reimport
and an installed analytical worker. See the [final delivery evidence](pilot/intelligence/STATUS.md).

All seven original portable views now restore exactly. Two releases preceding
capability-schema authority use their recovered historical checker and remain
immutable. Three separately qualified current successors use the active semantics;
historical bytes are not rewritten to make them conform to a later model.

## Verification and qualification

The completed seven-step pilot has 315 distinct passing tests and 40 finite acceptance
checks. Its 24-task semantic assessment remains 4 supported, 4 partial and 16 gaps.
See the [completion ledger](pilot/intelligence/COMPLETION.md) and
[acceptance matrix](pilot/intelligence/ACCEPTANCE.md) for exact receipts and limitations.
Final qualification used the isolated all-extras environment recorded in
[the handover](pilot/intelligence/RESUME_AFTER_REBOOT.md); the original `.venv` commands
below require those declared dependencies and the documented native binaries.

```bash
tooling/library_guides/.venv/bin/pytest tooling/library_guides/tests -q --tb=short
tooling/library_guides/.venv/bin/ruff check tooling/library_guides/library_guides tooling/library_guides/tests tooling/library_guides/pilot/intelligence
tooling/library_guides/.venv/bin/ruff format --check tooling/library_guides/library_guides tooling/library_guides/tests tooling/library_guides/pilot/intelligence
# Run from tooling/library_guides:
.venv/bin/pyrefly check --min-severity warn --output-format min-text
```

`pilot/intelligence/qualify_runtime.py` performs actual inference and additive/
recipe reuse checks in a fresh scoped corpus. `qualify_composition.py` creates a
fresh native-source composition corpus and runs the ordinary Rust witnesses.
`qualify_source_analysis.py` replays five real Arrow Schema MIR owners and
restores their portable analysis. `qualify_scoped_discovery.py` builds the real
427-operation native Arrow Schema selection in the main corpus, and
`qualify_decision_publication.py` publishes real arithmetic preferences and
counterfactuals. These programs retain new run directories; they do not clean
historical evidence.

`pilot/tasks.yaml` remains the independent 24-task catalog. Its attributed
assessments distinguish supported choices, partial mappings and unresolved gaps.
Four-library chains and frozen-core Pydantic/serde_json reuse use exact released
evidence. See the completion ledger for current acceptance and limitations.
No automated generative-model runner, API key, or decision-accuracy percentage
is used.
