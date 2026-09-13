# decision:arrow-schema:construction-routes

Profile: `rust-docsrs-54.1-58.4`

## decision:arrow-schema:construction-routes

Choose an Arrow Rust schema construction route from the available inputs.

Requirements: Use the retained Arrow schema 58.4.0 documentation context.; Choose by available input representation, required metadata and whether reconciliation is intended.; Do not infer ordinary consumer availability or complete merge/conflict behavior from this declaration guide.

- capability:draft:b2ad7b8782353e844424de2e6fd8b029f6d3cc2ff01b1e81dc1e4fd34c3ccde4: You have field values and do not need to supply schema metadata in this call. (claim:draft:b2ad7b8782353e844424de2e6fd8b029f6d3cc2ff01b1e81dc1e4fd34c3ccde4:signature, claim:draft:b2ad7b8782353e844424de2e6fd8b029f6d3cc2ff01b1e81dc1e4fd34c3ccde4:documentation)
- capability:draft:90d663776c42f41d5f62a1db7847e162b8388df05be3fc56ebe000ea51800f40: You have field values plus a HashMap<String, String> of schema metadata. (claim:draft:90d663776c42f41d5f62a1db7847e162b8388df05be3fc56ebe000ea51800f40:signature, claim:draft:90d663776c42f41d5f62a1db7847e162b8388df05be3fc56ebe000ea51800f40:documentation)
- capability:draft:d5332af7390c435f7c6fab12975ff9fa74b415a38f5927bbe3e0422f5c60ff9f: You already have a schema and want only specified column indices; the upstream documentation states that parent metadata carries over. (claim:draft:d5332af7390c435f7c6fab12975ff9fa74b415a38f5927bbe3e0422f5c60ff9f:signature, claim:draft:d5332af7390c435f7c6fab12975ff9fa74b415a38f5927bbe3e0422f5c60ff9f:documentation)
- capability:draft:6ca3b36c0d9f63f199e9c2a45fcf43ebdba9c9aa7a7c5c0712b4e30b85aca545: You have multiple schemas to reconcile and require the documented compatible recursive struct-field merge; the precise conflict policy still needs separate evidence. (claim:draft:6ca3b36c0d9f63f199e9c2a45fcf43ebdba9c9aa7a7c5c0712b4e30b85aca545:signature, claim:draft:6ca3b36c0d9f63f199e9c2a45fcf43ebdba9c9aa7a7c5c0712b4e30b85aca545:documentation)
- capability:draft:c8c759a8342ac1b428e0c660ea5a48b6548d22fff44fb3c9eeeb92d3712eef7a: You already have a SchemaBuilder and are ready to consume it for the final schema. (claim:draft:c8c759a8342ac1b428e0c660ea5a48b6548d22fff44fb3c9eeeb92d3712eef7a:signature, claim:draft:c8c759a8342ac1b428e0c660ea5a48b6548d22fff44fb3c9eeeb92d3712eef7a:documentation)

Schema::new and Schema::new_with_metadata construct from fields; the latter takes explicit schema metadata. Schema::project selects columns from an existing schema, with metadata retention stated by its documentation. Schema::try_merge accepts an iterator of schemas and returns a Result, with compatible recursive struct-field merging documented separately. SchemaBuilder::finish consumes an existing builder. These five nominated routes cover the reviewed input choices; the retained 65-record neighborhood also includes accessors, trait implementations and other operations, which remain unreviewed alternatives outside this bounded task.

Reversing conditions: Explicit metadata input favors new_with_metadata over new.; Selecting existing columns favors project; combining schemas instead requires reconciliation evidence.; An existing builder can be finished without first reconstructing its fields.; Nullability, metadata-conflict precedence, copying, allocation, or feature-specific availability requirements remain open and may reverse the choice.

## claim:draft:b2ad7b8782353e844424de2e6fd8b029f6d3cc2ff01b1e81dc1e4fd34c3ccde4:signature

Declared callable: fn arrow_schema::<impl Schema>::new(fields: impl Into<Fields>) -> Self. Its complete generic obligations and qualifiers are retained in the cited function contract.

Mechanism: Typed Rustdoc declaration; nominal occurrences do not establish assignability or executable effects.

Conditions: Documentation-generation context; ordinary consumer availability is not established.

Exceptions: not specified

Evidence class: source_reviewed.

- Evidence `evidence:draft:b2ad7b8782353e844424de2e6fd8b029f6d3cc2ff01b1e81dc1e4fd34c3ccde4:signature`: **arrow_schema::<impl Schema>::new**; `json:/item/inner/function`; SHA-256 `39e4d2d804bceb4e1d8047e6e850b4d9b2ee34d6109473f9402022abaa0a849f`; [source](./projections/declarations/6b1dc99d5d93dbe3dfc6691d37c05ecec96208ee9bbf3be71bbd05c65a0c6ff5.json).

### Fact support: signature

- `decl:9f641ce14fb9ae319530bc9e5e6b1c4359ef97db192e04dee2cda28ad1f9919b:1198` · `json:/item/inner/function` · SHA-256 `39e4d2d804bceb4e1d8047e6e850b4d9b2ee34d6109473f9402022abaa0a849f` · profile `rust-docsrs-54.1-58.4` · context `context:aad8d79659f3925be8c7411fec575812437cedcf4d87653c81d2f0a0a2c92302`.

- `decl:9f641ce14fb9ae319530bc9e5e6b1c4359ef97db192e04dee2cda28ad1f9919b:1198` · `json:/owner_contract` · SHA-256 `f759e60b773ecbdd74bef6923310a42c9866ddc91ac1276f8b7156fbec7ebe3c` · profile `rust-docsrs-54.1-58.4` · context `context:aad8d79659f3925be8c7411fec575812437cedcf4d87653c81d2f0a0a2c92302`.

## claim:draft:b2ad7b8782353e844424de2e6fd8b029f6d3cc2ff01b1e81dc1e4fd34c3ccde4:documentation

Creates a new [`Schema`] from a sequence of [`Field`] values.

Mechanism: Upstream item documentation states this behavior; extraction has not independently verified its implementation or execution.

Conditions: not specified

Exceptions: not specified

Evidence class: documented.

- Evidence `evidence:draft:b2ad7b8782353e844424de2e6fd8b029f6d3cc2ff01b1e81dc1e4fd34c3ccde4:documentation`: **arrow_schema::<impl Schema>::new**; `json:/item/docs`; SHA-256 `29079ebb3e2582df76cec579649c25ddd0a4ba7170bb840ca0b2727e4277fc7b`; [source](./projections/declarations/6b1dc99d5d93dbe3dfc6691d37c05ecec96208ee9bbf3be71bbd05c65a0c6ff5.json).

### Fact support: upstream_statement

- `decl:9f641ce14fb9ae319530bc9e5e6b1c4359ef97db192e04dee2cda28ad1f9919b:1198` · `json:/item/docs` · SHA-256 `29079ebb3e2582df76cec579649c25ddd0a4ba7170bb840ca0b2727e4277fc7b` · profile `rust-docsrs-54.1-58.4` · context `context:aad8d79659f3925be8c7411fec575812437cedcf4d87653c81d2f0a0a2c92302`.

## claim:draft:90d663776c42f41d5f62a1db7847e162b8388df05be3fc56ebe000ea51800f40:signature

Declared callable: fn arrow_schema::<impl Schema>::new_with_metadata(fields: impl Into<Fields>, metadata: HashMap<String, String>) -> Self. Its complete generic obligations and qualifiers are retained in the cited function contract.

Mechanism: Typed Rustdoc declaration; nominal occurrences do not establish assignability or executable effects.

Conditions: Documentation-generation context; ordinary consumer availability is not established.

Exceptions: not specified

Evidence class: source_reviewed.

- Evidence `evidence:draft:90d663776c42f41d5f62a1db7847e162b8388df05be3fc56ebe000ea51800f40:signature`: **arrow_schema::<impl Schema>::new_with_metadata**; `json:/item/inner/function`; SHA-256 `2a71cf5e9c724d4fb0b9006a6791dbd0d73606f326d8bd6ddad83d7cccad98b1`; [source](./projections/declarations/cf2ad7a1da54d2efc20e060c457f3e125db310a7bd5076f13a02228fa09e1985.json).

### Fact support: signature

- `decl:9f641ce14fb9ae319530bc9e5e6b1c4359ef97db192e04dee2cda28ad1f9919b:1199` · `json:/item/inner/function` · SHA-256 `2a71cf5e9c724d4fb0b9006a6791dbd0d73606f326d8bd6ddad83d7cccad98b1` · profile `rust-docsrs-54.1-58.4` · context `context:aad8d79659f3925be8c7411fec575812437cedcf4d87653c81d2f0a0a2c92302`.

- `decl:9f641ce14fb9ae319530bc9e5e6b1c4359ef97db192e04dee2cda28ad1f9919b:1199` · `json:/owner_contract` · SHA-256 `f759e60b773ecbdd74bef6923310a42c9866ddc91ac1276f8b7156fbec7ebe3c` · profile `rust-docsrs-54.1-58.4` · context `context:aad8d79659f3925be8c7411fec575812437cedcf4d87653c81d2f0a0a2c92302`.

## claim:draft:90d663776c42f41d5f62a1db7847e162b8388df05be3fc56ebe000ea51800f40:documentation

Creates a new [`Schema`] from a sequence of [`Field`] values and adds additional metadata in form of key value pairs.

Mechanism: Upstream item documentation states this behavior; extraction has not independently verified its implementation or execution.

Conditions: not specified

Exceptions: not specified

Evidence class: documented.

- Evidence `evidence:draft:90d663776c42f41d5f62a1db7847e162b8388df05be3fc56ebe000ea51800f40:documentation`: **arrow_schema::<impl Schema>::new_with_metadata**; `json:/item/docs`; SHA-256 `95c377e5b2db4e6371d4c921f89e9d9e21ce882e62440f11a65efe1fb82e1251`; [source](./projections/declarations/cf2ad7a1da54d2efc20e060c457f3e125db310a7bd5076f13a02228fa09e1985.json).

### Fact support: upstream_statement

- `decl:9f641ce14fb9ae319530bc9e5e6b1c4359ef97db192e04dee2cda28ad1f9919b:1199` · `json:/item/docs` · SHA-256 `95c377e5b2db4e6371d4c921f89e9d9e21ce882e62440f11a65efe1fb82e1251` · profile `rust-docsrs-54.1-58.4` · context `context:aad8d79659f3925be8c7411fec575812437cedcf4d87653c81d2f0a0a2c92302`.

## claim:draft:d5332af7390c435f7c6fab12975ff9fa74b415a38f5927bbe3e0422f5c60ff9f:signature

Declared callable: fn arrow_schema::<impl Schema>::project(self: &Self, indices: &[usize]) -> Result<Schema, ArrowError>. Its complete generic obligations and qualifiers are retained in the cited function contract.

Mechanism: Typed Rustdoc declaration; nominal occurrences do not establish assignability or executable effects.

Conditions: Documentation-generation context; ordinary consumer availability is not established.

Exceptions: not specified

Evidence class: source_reviewed.

- Evidence `evidence:draft:d5332af7390c435f7c6fab12975ff9fa74b415a38f5927bbe3e0422f5c60ff9f:signature`: **arrow_schema::<impl Schema>::project**; `json:/item/inner/function`; SHA-256 `f689c3f179ce38b98c868915ba8d2257d1817910158a5e8a3d3c18c84eceeab1`; [source](./projections/declarations/eac5f1b6f1e7c4e1fc4bc41d2c5198214784cf5ed277ffe15d9bda99dfb16b9b.json).

### Fact support: signature

- `decl:9f641ce14fb9ae319530bc9e5e6b1c4359ef97db192e04dee2cda28ad1f9919b:1201` · `json:/item/inner/function` · SHA-256 `f689c3f179ce38b98c868915ba8d2257d1817910158a5e8a3d3c18c84eceeab1` · profile `rust-docsrs-54.1-58.4` · context `context:aad8d79659f3925be8c7411fec575812437cedcf4d87653c81d2f0a0a2c92302`.

- `decl:9f641ce14fb9ae319530bc9e5e6b1c4359ef97db192e04dee2cda28ad1f9919b:1201` · `json:/owner_contract` · SHA-256 `f759e60b773ecbdd74bef6923310a42c9866ddc91ac1276f8b7156fbec7ebe3c` · profile `rust-docsrs-54.1-58.4` · context `context:aad8d79659f3925be8c7411fec575812437cedcf4d87653c81d2f0a0a2c92302`.

## claim:draft:d5332af7390c435f7c6fab12975ff9fa74b415a38f5927bbe3e0422f5c60ff9f:documentation

Returns a new schema with only the specified columns in the new schema This carries metadata from the parent schema over as well

Mechanism: Upstream item documentation states this behavior; extraction has not independently verified its implementation or execution.

Conditions: not specified

Exceptions: not specified

Evidence class: documented.

- Evidence `evidence:draft:d5332af7390c435f7c6fab12975ff9fa74b415a38f5927bbe3e0422f5c60ff9f:documentation`: **arrow_schema::<impl Schema>::project**; `json:/item/docs`; SHA-256 `789908078b087a621c8f3289652d743171fbb005f754470fa42e6794c86d6514`; [source](./projections/declarations/eac5f1b6f1e7c4e1fc4bc41d2c5198214784cf5ed277ffe15d9bda99dfb16b9b.json).

### Fact support: upstream_statement

- `decl:9f641ce14fb9ae319530bc9e5e6b1c4359ef97db192e04dee2cda28ad1f9919b:1201` · `json:/item/docs` · SHA-256 `789908078b087a621c8f3289652d743171fbb005f754470fa42e6794c86d6514` · profile `rust-docsrs-54.1-58.4` · context `context:aad8d79659f3925be8c7411fec575812437cedcf4d87653c81d2f0a0a2c92302`.

## claim:draft:6ca3b36c0d9f63f199e9c2a45fcf43ebdba9c9aa7a7c5c0712b4e30b85aca545:signature

Declared callable: fn arrow_schema::<impl Schema>::try_merge(schemas: impl IntoIterator<Item = Self>) -> Result<Self, ArrowError>. Its complete generic obligations and qualifiers are retained in the cited function contract.

Mechanism: Typed Rustdoc declaration; nominal occurrences do not establish assignability or executable effects.

Conditions: Documentation-generation context; ordinary consumer availability is not established.

Exceptions: not specified

Evidence class: source_reviewed.

- Evidence `evidence:draft:6ca3b36c0d9f63f199e9c2a45fcf43ebdba9c9aa7a7c5c0712b4e30b85aca545:signature`: **arrow_schema::<impl Schema>::try_merge**; `json:/item/inner/function`; SHA-256 `b3213a647cfdbcedc606345f18abde5b1c113d783f7dcf935897de9628ab20f5`; [source](./projections/declarations/c8b6a564c9d11008c401637a21c61a34ce9dd4bc359c050b8f81cad5621b662e.json).

### Fact support: signature

- `decl:9f641ce14fb9ae319530bc9e5e6b1c4359ef97db192e04dee2cda28ad1f9919b:1202` · `json:/item/inner/function` · SHA-256 `b3213a647cfdbcedc606345f18abde5b1c113d783f7dcf935897de9628ab20f5` · profile `rust-docsrs-54.1-58.4` · context `context:aad8d79659f3925be8c7411fec575812437cedcf4d87653c81d2f0a0a2c92302`.

- `decl:9f641ce14fb9ae319530bc9e5e6b1c4359ef97db192e04dee2cda28ad1f9919b:1202` · `json:/owner_contract` · SHA-256 `f759e60b773ecbdd74bef6923310a42c9866ddc91ac1276f8b7156fbec7ebe3c` · profile `rust-docsrs-54.1-58.4` · context `context:aad8d79659f3925be8c7411fec575812437cedcf4d87653c81d2f0a0a2c92302`.

## claim:draft:6ca3b36c0d9f63f199e9c2a45fcf43ebdba9c9aa7a7c5c0712b4e30b85aca545:documentation

Merge schema into self if it is compatible. Struct fields will be merged recursively.

Mechanism: Upstream item documentation states this behavior; extraction has not independently verified its implementation or execution.

Conditions: not specified

Exceptions: not specified

Evidence class: documented.

- Evidence `evidence:draft:6ca3b36c0d9f63f199e9c2a45fcf43ebdba9c9aa7a7c5c0712b4e30b85aca545:documentation`: **arrow_schema::<impl Schema>::try_merge**; `json:/item/docs`; SHA-256 `672f066953032ebf575def89e971532cf2146dd398288f4e4c3cb2e60d497163`; [source](./projections/declarations/c8b6a564c9d11008c401637a21c61a34ce9dd4bc359c050b8f81cad5621b662e.json).

### Fact support: upstream_statement

- `decl:9f641ce14fb9ae319530bc9e5e6b1c4359ef97db192e04dee2cda28ad1f9919b:1202` · `json:/item/docs` · SHA-256 `672f066953032ebf575def89e971532cf2146dd398288f4e4c3cb2e60d497163` · profile `rust-docsrs-54.1-58.4` · context `context:aad8d79659f3925be8c7411fec575812437cedcf4d87653c81d2f0a0a2c92302`.

## claim:draft:c8c759a8342ac1b428e0c660ea5a48b6548d22fff44fb3c9eeeb92d3712eef7a:signature

Declared callable: fn arrow_schema::<impl SchemaBuilder>::finish(self: Self) -> Schema. Its complete generic obligations and qualifiers are retained in the cited function contract.

Mechanism: Typed Rustdoc declaration; nominal occurrences do not establish assignability or executable effects.

Conditions: Documentation-generation context; ordinary consumer availability is not established.

Exceptions: not specified

Evidence class: source_reviewed.

- Evidence `evidence:draft:c8c759a8342ac1b428e0c660ea5a48b6548d22fff44fb3c9eeeb92d3712eef7a:signature`: **arrow_schema::<impl SchemaBuilder>::finish**; `json:/item/inner/function`; SHA-256 `3370b9c242c94a899f67db0b721f6bfa376dbd039d2e528ae96280faa2afe92e`; [source](./projections/declarations/5bcfda97cc41148d5b04149500c4813084cf51e2bde6179c5d9ec9db6142519e.json).

### Fact support: signature

- `decl:9f641ce14fb9ae319530bc9e5e6b1c4359ef97db192e04dee2cda28ad1f9919b:1168` · `json:/item/inner/function` · SHA-256 `3370b9c242c94a899f67db0b721f6bfa376dbd039d2e528ae96280faa2afe92e` · profile `rust-docsrs-54.1-58.4` · context `context:aad8d79659f3925be8c7411fec575812437cedcf4d87653c81d2f0a0a2c92302`.

- `decl:9f641ce14fb9ae319530bc9e5e6b1c4359ef97db192e04dee2cda28ad1f9919b:1168` · `json:/owner_contract` · SHA-256 `40f40eb02cd82f9d54390dd8ecac2fe8b9e74fd89771e8856eb72bf28fff830e` · profile `rust-docsrs-54.1-58.4` · context `context:aad8d79659f3925be8c7411fec575812437cedcf4d87653c81d2f0a0a2c92302`.

## claim:draft:c8c759a8342ac1b428e0c660ea5a48b6548d22fff44fb3c9eeeb92d3712eef7a:documentation

Consume this [`SchemaBuilder`] yielding the final [`Schema`]

Mechanism: Upstream item documentation states this behavior; extraction has not independently verified its implementation or execution.

Conditions: not specified

Exceptions: not specified

Evidence class: documented.

- Evidence `evidence:draft:c8c759a8342ac1b428e0c660ea5a48b6548d22fff44fb3c9eeeb92d3712eef7a:documentation`: **arrow_schema::<impl SchemaBuilder>::finish**; `json:/item/docs`; SHA-256 `8b9691f19049206efc2ea1a4e0cc8f72146359c651b9fd6aafc93978ce09b86d`; [source](./projections/declarations/5bcfda97cc41148d5b04149500c4813084cf51e2bde6179c5d9ec9db6142519e.json).

### Fact support: upstream_statement

- `decl:9f641ce14fb9ae319530bc9e5e6b1c4359ef97db192e04dee2cda28ad1f9919b:1168` · `json:/item/docs` · SHA-256 `8b9691f19049206efc2ea1a4e0cc8f72146359c651b9fd6aafc93978ce09b86d` · profile `rust-docsrs-54.1-58.4` · context `context:aad8d79659f3925be8c7411fec575812437cedcf4d87653c81d2f0a0a2c92302`.

## capability:draft:b2ad7b8782353e844424de2e6fd8b029f6d3cc2ff01b1e81dc1e4fd34c3ccde4

Creates a new [`Schema`] from a sequence of [`Field`] values.

Creates a new [`Schema`] from a sequence of [`Field`] values.

- declaration: fn arrow_schema::<impl Schema>::new(fields: impl Into<Fields>) -> Self (claim:draft:b2ad7b8782353e844424de2e6fd8b029f6d3cc2ff01b1e81dc1e4fd34c3ccde4:signature)



Unresolved evidence:

- evaluation_timing: evaluation_timing is not established by declarations; inspect source, registry or execution evidence.
- failure_semantics: failure_semantics is not established by declarations; inspect source, registry or execution evidence.
- null_behavior: null_behavior is not established by declarations; inspect source, registry or execution evidence.
- ownership_effects: ownership_effects is not established by declarations; inspect source, registry or execution evidence.
- resource_lifecycle: resource_lifecycle is not established by declarations; inspect source, registry or execution evidence.
- consumer_availability: consumer_availability is not established by declarations; inspect source, registry or execution evidence.

## binding:draft:b2ad7b8782353e844424de2e6fd8b029f6d3cc2ff01b1e81dc1e4fd34c3ccde4

`arrow_schema::<impl Schema>::new` (rust, arrow_schema 58.4.0, resolved)

```text
fn arrow_schema::<impl Schema>::new(fields: impl Into<Fields>) -> Self
```

## capability:draft:90d663776c42f41d5f62a1db7847e162b8388df05be3fc56ebe000ea51800f40

Creates a new [`Schema`] from a sequence of [`Field`] values and adds additional metadata in form of key value pairs.

Creates a new [`Schema`] from a sequence of [`Field`] values and adds additional metadata in form of key value pairs.

- declaration: fn arrow_schema::<impl Schema>::new_with_metadata(fields: impl Into<Fields>, metadata: HashMap<String, String>) -> Self (claim:draft:90d663776c42f41d5f62a1db7847e162b8388df05be3fc56ebe000ea51800f40:signature)



Unresolved evidence:

- evaluation_timing: evaluation_timing is not established by declarations; inspect source, registry or execution evidence.
- failure_semantics: failure_semantics is not established by declarations; inspect source, registry or execution evidence.
- null_behavior: null_behavior is not established by declarations; inspect source, registry or execution evidence.
- ownership_effects: ownership_effects is not established by declarations; inspect source, registry or execution evidence.
- resource_lifecycle: resource_lifecycle is not established by declarations; inspect source, registry or execution evidence.
- consumer_availability: consumer_availability is not established by declarations; inspect source, registry or execution evidence.

## binding:draft:90d663776c42f41d5f62a1db7847e162b8388df05be3fc56ebe000ea51800f40

`arrow_schema::<impl Schema>::new_with_metadata` (rust, arrow_schema 58.4.0, resolved)

```text
fn arrow_schema::<impl Schema>::new_with_metadata(fields: impl Into<Fields>, metadata: HashMap<String, String>) -> Self
```

## capability:draft:d5332af7390c435f7c6fab12975ff9fa74b415a38f5927bbe3e0422f5c60ff9f

Returns a new schema with only the specified columns in the new schema This carries metadata from the parent schema over as well

Returns a new schema with only the specified columns in the new schema This carries metadata from the parent schema over as well

- declaration: fn arrow_schema::<impl Schema>::project(self: &Self, indices: &[usize]) -> Result<Schema, ArrowError> (claim:draft:d5332af7390c435f7c6fab12975ff9fa74b415a38f5927bbe3e0422f5c60ff9f:signature)



Unresolved evidence:

- evaluation_timing: evaluation_timing is not established by declarations; inspect source, registry or execution evidence.
- failure_semantics: failure_semantics is not established by declarations; inspect source, registry or execution evidence.
- null_behavior: null_behavior is not established by declarations; inspect source, registry or execution evidence.
- ownership_effects: ownership_effects is not established by declarations; inspect source, registry or execution evidence.
- resource_lifecycle: resource_lifecycle is not established by declarations; inspect source, registry or execution evidence.
- consumer_availability: consumer_availability is not established by declarations; inspect source, registry or execution evidence.

## binding:draft:d5332af7390c435f7c6fab12975ff9fa74b415a38f5927bbe3e0422f5c60ff9f

`arrow_schema::<impl Schema>::project` (rust, arrow_schema 58.4.0, resolved)

```text
fn arrow_schema::<impl Schema>::project(self: &Self, indices: &[usize]) -> Result<Schema, ArrowError>
```

## capability:draft:6ca3b36c0d9f63f199e9c2a45fcf43ebdba9c9aa7a7c5c0712b4e30b85aca545

Merge schema into self if it is compatible. Struct fields will be merged recursively.

Merge schema into self if it is compatible. Struct fields will be merged recursively.

- declaration: fn arrow_schema::<impl Schema>::try_merge(schemas: impl IntoIterator<Item = Self>) -> Result<Self, ArrowError> (claim:draft:6ca3b36c0d9f63f199e9c2a45fcf43ebdba9c9aa7a7c5c0712b4e30b85aca545:signature)



Unresolved evidence:

- evaluation_timing: evaluation_timing is not established by declarations; inspect source, registry or execution evidence.
- failure_semantics: failure_semantics is not established by declarations; inspect source, registry or execution evidence.
- null_behavior: null_behavior is not established by declarations; inspect source, registry or execution evidence.
- ownership_effects: ownership_effects is not established by declarations; inspect source, registry or execution evidence.
- resource_lifecycle: resource_lifecycle is not established by declarations; inspect source, registry or execution evidence.
- consumer_availability: consumer_availability is not established by declarations; inspect source, registry or execution evidence.

## binding:draft:6ca3b36c0d9f63f199e9c2a45fcf43ebdba9c9aa7a7c5c0712b4e30b85aca545

`arrow_schema::<impl Schema>::try_merge` (rust, arrow_schema 58.4.0, resolved)

```text
fn arrow_schema::<impl Schema>::try_merge(schemas: impl IntoIterator<Item = Self>) -> Result<Self, ArrowError>
```

## capability:draft:c8c759a8342ac1b428e0c660ea5a48b6548d22fff44fb3c9eeeb92d3712eef7a

Consume this [`SchemaBuilder`] yielding the final [`Schema`]

Consume this [`SchemaBuilder`] yielding the final [`Schema`]

- declaration: fn arrow_schema::<impl SchemaBuilder>::finish(self: Self) -> Schema (claim:draft:c8c759a8342ac1b428e0c660ea5a48b6548d22fff44fb3c9eeeb92d3712eef7a:signature)



Unresolved evidence:

- evaluation_timing: evaluation_timing is not established by declarations; inspect source, registry or execution evidence.
- failure_semantics: failure_semantics is not established by declarations; inspect source, registry or execution evidence.
- null_behavior: null_behavior is not established by declarations; inspect source, registry or execution evidence.
- ownership_effects: ownership_effects is not established by declarations; inspect source, registry or execution evidence.
- resource_lifecycle: resource_lifecycle is not established by declarations; inspect source, registry or execution evidence.
- consumer_availability: consumer_availability is not established by declarations; inspect source, registry or execution evidence.

## binding:draft:c8c759a8342ac1b428e0c660ea5a48b6548d22fff44fb3c9eeeb92d3712eef7a

`arrow_schema::<impl SchemaBuilder>::finish` (rust, arrow_schema 58.4.0, resolved)

```text
fn arrow_schema::<impl SchemaBuilder>::finish(self: Self) -> Schema
```
