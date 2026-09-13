# Construct an Arrow Schema with a direct Schema result

Profile: `rust-docsrs-54.1-58.4`.

Comparison: `59e29a5629c42c3780af1526a51a38337c14eca1cd88b0c6cb624348a219706a`. Universe: `084805c870736327c5dfe48a370bb595f4005a021ab9c4c37ba91e6c542793b7`.

Candidates are drawn from the admitted interface universe. Retrieval rank does not exclude alternatives.

## arrow_schema::<impl VariableShapeTensor>::uniform_shapes

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl VariableShapeTensor>::uniform_shapes(self: &Self) -> Option<&[Option<i32>]>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `c4392c8ec47404517e478f3d5161f7b1bfd840d7ad3edb0b34199cd00d853153`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl UnionFields as PartialEq>::eq

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl UnionFields as PartialEq>::eq(self: &Self, other: &UnionFields) -> bool`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl Schema as Clone>::clone

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl Schema as Clone>::clone(self: &Self) -> Schema`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **supported**. An applicable qualified assertion satisfies the requirement.
  Evidence assertions: `396182c2edfacd1e9ddba86da4f430dd1ff962794faca6e5dd3566d0cc583c3b`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Flags>::empty

Disposition: **rejected**.

Interface: `const fn arrow_schema::<impl Flags>::empty() -> Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `e6f833b6cde5645f0af7492db72df74545f425872edce5ba32032b11631f13be`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Json as Clone>::clone

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Json as Clone>::clone(self: &Self) -> Json`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `1fb228e2fed1c4fefcd8c2f76c16bd520eec98d69a498eb2a15d69fe0b810d67`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl ArrowError as From<IntoInnerError<W>>>::from

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl ArrowError as From<IntoInnerError<W>>>::from(error: std::io::IntoInnerError<W>) -> Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `07298932ff8486ab833e5b247390c198c9ed80baf2b366e358f7e5c161a124ac`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Opaque as From<OpaqueMetadata>>::from

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Opaque as From<OpaqueMetadata>>::from(value: OpaqueMetadata) -> Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `632a66cc30b7976bd419ac4a7dda07eb7be8da348abe20a2f7fe56b70ec2eb7a`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Json as ExtensionType>::try_new

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Json as ExtensionType>::try_new(data_type: &DataType, metadata: <Self as >::Metadata) -> Result<Self, ArrowError>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `f6a29e90563a779a3b2006304ec91ef3eb58760483a6d753716681950109b832`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl FixedShapeTensorMetadata>::dimension_names

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl FixedShapeTensorMetadata>::dimension_names(self: &Self) -> Option<&[String]>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `cfc4a4e7ef2f1fdd8b900615deb08c19a61263ecc2b70ab5b8ee9445cbefc514`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Flags as IntoIterator>::into_iter

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl Flags as IntoIterator>::into_iter(self: Self) -> <Self as >::IntoIter`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl DataType as Any>::type_id

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl DataType as Any>::type_id(self: &Self) -> TypeId`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `b68680da25da163d832777d8294ca67c91965f27095ace5d1b244356ba630036`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl UnionMode as Deserialize<'de>>::deserialize

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl UnionMode as Deserialize<'de>>::deserialize<__D>(__deserializer: __D) -> _serde::__private229::Result<Self, <__D as >::Error> where __D: _serde::Deserializer<'de>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `3e86e1df6c66fed8c36d1f1d697326b5ef9003c913f21c6f68a900653a765073`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Schema>::field

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl Schema>::field(self: &Self, i: usize) -> &Field`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl VariableShapeTensorMetadata as Deserialize<'de>>::deserialize

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl VariableShapeTensorMetadata as Deserialize<'de>>::deserialize<D>(deserializer: D) -> Result<Self, <D as >::Error> where D: Deserializer<'de>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `ccbf3e399b573ea7588b54f32fc73e2d6aaec2b6727ce5da6ba51400affec2e4`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl DataType>::is_list

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl DataType>::is_list(self: &Self) -> bool`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl VariableShapeTensor as ExtensionType>::serialize_metadata

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl VariableShapeTensor as ExtensionType>::serialize_metadata(self: &Self) -> Option<String>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `ad80429fdd6d2e56472c89c3b81b7f81794aa211f4771f11b461cdb8b602384f`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Uuid as Clone>::clone

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Uuid as Clone>::clone(self: &Self) -> Uuid`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `2ddb7cc440d010f9b0e3aad7ad04f28a7b19a4a59ae971ff6981987ed7a5a821`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Json as Debug>::fmt

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Json as Debug>::fmt(self: &Self, f: &mut $crate::fmt::Formatter<'_>) -> $crate::fmt::Result`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `b5668de74b05f10ff326f6b113036c05d4f9cdecea88cf7d8a7d79e3026b0a7a`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl FFI_ArrowSchema as TryFrom<Schema>>::try_from

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl FFI_ArrowSchema as TryFrom<Schema>>::try_from(schema: Schema) -> Result<Self, ArrowError>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `7c2e6a3ac7d55fd1637b21b73c8d6761a39026deb5b4c42d9141a4ef945da526`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Schema>::flattened_fields

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Schema>::flattened_fields(self: &Self) -> Vec<&Field>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `48a19c7d2cd7bfd654fff427c9ced44cff97cfd6180f0e4ceacb3f73e1ffbe6a`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl ArrowError as From<Utf8Error>>::from

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl ArrowError as From<Utf8Error>>::from(error: std::str::Utf8Error) -> Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `02df1023af51e43a30b7c64dd05ad9130a470f8e4b59f32eb8e6982a4c4c6fa0`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Flags>::intersects

Disposition: **conditional**.

Interface: `const fn arrow_schema::<impl Flags>::intersects(self: &Self, other: Self) -> bool`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl TimestampWithOffset as PartialEq>::eq

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl TimestampWithOffset as PartialEq>::eq(self: &Self, other: &TimestampWithOffset) -> bool`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl Bool8 as ExtensionType>::metadata

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl Bool8 as ExtensionType>::metadata(self: &Self) -> &<Self as >::Metadata`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl IntervalUnit as PartialEq>::eq

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl IntervalUnit as PartialEq>::eq(self: &Self, other: &IntervalUnit) -> bool`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl Flags as Extend<Flags>>::extend

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl Flags as Extend<Flags>>::extend<T: $crate::__private::core::iter::IntoIterator<Item = Self>>(self: &mut Self, iterator: T) -> ()`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl FixedShapeTensor>::dimensions

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl FixedShapeTensor>::dimensions(self: &Self) -> usize`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl VariableShapeTensorMetadata>::dimension_names

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl VariableShapeTensorMetadata>::dimension_names(self: &Self) -> Option<&[String]>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `ca5705cc1855b161a785614514c77d428cdcd819a7344ea312c554c2301a205e`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl DataType as TryInto<U>>::try_into

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl DataType as TryInto<U>>::try_into(self: Self) -> Result<U, <U as TryFrom<T>>::Error>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `c2cf21438a091fa8230c09611632f6f2eb2a349094567e211021447143ef768a`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl VariableShapeTensorMetadata>::permutations

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl VariableShapeTensorMetadata>::permutations(self: &Self) -> Option<&[usize]>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `9c42b0f208a26ee3e56e5a825c5beca6e929b31a9445b3ca0a03b7c43d2de2e0`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Opaque>::vendor_name

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl Opaque>::vendor_name(self: &Self) -> &str`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl UnionMode as PartialOrd>::partial_cmp

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl UnionMode as PartialOrd>::partial_cmp(self: &Self, other: &UnionMode) -> $crate::option::Option<$crate::cmp::Ordering>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `0520a648cac0e235e6247d973cbe1592f6ebf8e943cc4f57478fded093fdca64`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Field>::new_dictionary

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Field>::new_dictionary(name: impl Into<String>, key: DataType, value: DataType, nullable: bool) -> Self`.

- `documented_operation_class = construct-object`: **supported**. An applicable qualified assertion satisfies the requirement.
  Evidence assertions: `606c253af207af01ebb581cd37c67dd1ce182c0bc4cd759e23be86da426b4dba`.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `3a9b3fe33002e480bf829be24fb429dd044a8e2b5bcc598540b55becc092d298`.

Re-evaluation triggers:

- Re-evaluate fab91b62e1b7ed7c2e7af229c2cd135058515f889362efe9533ceb7649042b64 when required value or applicability changes.
- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl UnionFields as Clone>::clone

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl UnionFields as Clone>::clone(self: &Self) -> UnionFields`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `bfe0a2e529ef3f2ba2aae96be8a2c353fc625dc0f7c7ea44808558816bbd48e6`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Uuid as ExtensionType>::try_new

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Uuid as ExtensionType>::try_new(data_type: &DataType, _metadata: <Self as >::Metadata) -> Result<Self, ArrowError>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `3b66963978b2ec902c910a11b6b82cd5c6669fccb8c6ec13a7e2fe99679b4969`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl crate::DataType as TryFrom<&FFI_ArrowSchema>>::try_from

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl crate::DataType as TryFrom<&FFI_ArrowSchema>>::try_from(c_schema: &FFI_ArrowSchema) -> Result<Self, ArrowError>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `1b42914d9531e46d93d4afe4f88626488146f87bfa8127b8c99d01bf4c4102c0`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl TimeUnit as Display>::fmt

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl TimeUnit as Display>::fmt(self: &Self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `c0af0953d74433dd30711686052688e076bd3ddb41cf81ef2a57c8333a0149dc`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Flags>::union

Disposition: **rejected**.

Interface: `const fn arrow_schema::<impl Flags>::union(self: Self, other: Self) -> Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `ccf0ed5dc6dc2252acc40c2c8c6eebda0385eb83a07bbb2f813595b1d355600b`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl CanonicalExtensionType as From<Uuid>>::from

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl CanonicalExtensionType as From<Uuid>>::from(value: Uuid) -> Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `15329fee187b22fca8d034506cd8fc0a901b5391cee287b22f227c4e65366298`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::extension::ExtensionType::supports_data_type

Disposition: **rejected**.

Interface: `fn arrow_schema::extension::ExtensionType::supports_data_type(self: &Self, data_type: &DataType) -> Result<(), ArrowError>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `41627be125e5102058ac3a05f2bf4b041280e49da170428775d79c57d6fdf555`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Field>::extension_type_metadata

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Field>::extension_type_metadata(self: &Self) -> Option<&str>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `fea623c29117da5f6cdc5e50de930fd299865773cfcd6d6638f50437b02f2fbb`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl FFI_ArrowSchema>::with_flags

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl FFI_ArrowSchema>::with_flags(self: Self, flags: Flags) -> Result<Self, ArrowError>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `800ee09f47f513b8a5e21f75f616df8bc61035e9c7dcc7fed1ff0297dc6d058c`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl TimeUnit as Ord>::cmp

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl TimeUnit as Ord>::cmp(self: &Self, other: &TimeUnit) -> $crate::cmp::Ordering`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `212b12ea284eec7b13e6e56114ea28876c73e3cae6c265b7a64ad5788a5de257`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Fields as Debug>::fmt

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Fields as Debug>::fmt(self: &Self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `cbca3e0f8cd5fa360348f62373087a7e084f18d44363a6e982ce054a5b5cc15e`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Json as ExtensionType>::serialize_metadata

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Json as ExtensionType>::serialize_metadata(self: &Self) -> Option<String>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `7fb19e0cdb5c91fe40613208dcee5d6a886ba7aefe8836c61d6fe42095d5d8d6`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl DataType>::new_list

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl DataType>::new_list(data_type: DataType, nullable: bool) -> Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `420d4f793091004cd6e72ab30525e53ff1221d1d019c679180b0f1f2b84463a3`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Schema>::fields_with_dict_id

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Schema>::fields_with_dict_id(self: &Self, dict_id: i64) -> Vec<&Field>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `b9286822872696516be81dea0d3ea6ce53412411357a41534e94eef2b99efed3`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Fields as Clone>::clone

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Fields as Clone>::clone(self: &Self) -> Fields`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `fa5d20c0fb34f8a710a182211688c1f1dfb9e201ac1d0cd3e234ef4ac6f5765b`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Field as Debug>::fmt

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Field as Debug>::fmt(self: &Self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `5710ea25425dac9a5dbee11bcabd7a5764837fa67bcaf0e072e4b0b7cef06383`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Field>::data_type

Disposition: **conditional**.

Interface: `const fn arrow_schema::<impl Field>::data_type(self: &Self) -> &DataType`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl Uuid as ExtensionType>::supports_data_type

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Uuid as ExtensionType>::supports_data_type(self: &Self, data_type: &DataType) -> Result<(), ArrowError>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `d7ccf55b06d6a60d2a53a752aaee4e5cece121c6563ce0b5665d4a56d05009c5`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl FixedShapeTensor>::permutations

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl FixedShapeTensor>::permutations(self: &Self) -> Option<&[usize]>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `9d9e6769f05f85118088fdb157340534f00722ff0532ca48befbcd537e9c2ea4`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl DataType as PartialOrd>::partial_cmp

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl DataType as PartialOrd>::partial_cmp(self: &Self, other: &DataType) -> $crate::option::Option<$crate::cmp::Ordering>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `913e465deffa73aff4e266f480b52fe8a0152f60cb642c2dfde5b154f0e0ff5e`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl DataType>::new_large_list

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl DataType>::new_large_list(data_type: DataType, nullable: bool) -> Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `acd7b26ebb83c69881debde0f9e42abbf76b5cc1a2898196ed16544cbb035747`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl UnionFields>::is_empty

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl UnionFields>::is_empty(self: &Self) -> bool`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl OpaqueMetadata as Debug>::fmt

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl OpaqueMetadata as Debug>::fmt(self: &Self, f: &mut $crate::fmt::Formatter<'_>) -> $crate::fmt::Result`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `1b44be411b44b16d34e969641bfe24cad37994b0d24d4b07a7643ec9f3bbbcbc`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl JsonMetadata as Clone>::clone

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl JsonMetadata as Clone>::clone(self: &Self) -> JsonMetadata`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `ec11c8729f5b6a323b1793ff99bc542800aa2c2244533f53afa6416357a6e365`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Schema>::with_metadata

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl Schema>::with_metadata(self: Self, metadata: HashMap<String, String>) -> Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **supported**. An applicable qualified assertion satisfies the requirement.
  Evidence assertions: `4eb95db52a87c2db089967c7b57c8994869469523d934e9037a6e376d2edd0b5`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl SchemaBuilder as Extend<Arc<Field>>>::extend

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl SchemaBuilder as Extend<Arc<Field>>>::extend<T: IntoIterator<Item = FieldRef>>(self: &mut Self, iter: T) -> ()`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl VariableShapeTensor>::dimension_names

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl VariableShapeTensor>::dimension_names(self: &Self) -> Option<&[String]>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `3cb65c0234151e1285bb54d345a2174aee52ec9c1be5c4f14771c4daaef4ec2d`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Schema>::project

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Schema>::project(self: &Self, indices: &[usize]) -> Result<Schema, ArrowError>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `b616a0e56773a46f82e818960d7cac833be93207b8d2e35367f0a2cd64a82b89`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl TimeUnit as Clone>::clone

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl TimeUnit as Clone>::clone(self: &Self) -> TimeUnit`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `e9c28fe1c8f523ab317e07f9b3de2a2d356b3b82a5e5fd0a94b80a35572312f7`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl TimeUnit as Hash>::hash

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl TimeUnit as Hash>::hash<__H: $crate::hash::Hasher>(self: &Self, state: &mut __H) -> ()`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl Schema>::try_merge

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Schema>::try_merge(schemas: impl IntoIterator<Item = Self>) -> Result<Self, ArrowError>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `dc56394aa45977d8b72673907a419d2624a229d279c7dfa2b3ca365e17f01485`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl FixedShapeTensor>::dimension_names

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl FixedShapeTensor>::dimension_names(self: &Self) -> Option<&[String]>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `55cd35bd3ffc41d7e0043042857dad839d16dbfc89de97e77d2530a9e90c57e2`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Fields as FromIterator<Field>>::from_iter

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Fields as FromIterator<Field>>::from_iter<T: IntoIterator<Item = Field>>(iter: T) -> Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `09460f595063f12e69a63e6fa362562a3a146a2b8c78e31f75bd22976aae4046`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Fields>::filter_leaves

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Fields>::filter_leaves<F: FnMut(usize, &FieldRef) -> bool>(self: &Self, filter: F) -> Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `c7ce73352f47cc0d446a686c213f644385fe38b7c4d5fe242bac88aca277457d`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl VariableShapeTensor as ExtensionType>::metadata

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl VariableShapeTensor as ExtensionType>::metadata(self: &Self) -> &<Self as >::Metadata`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl &'a Fields as IntoIterator>::into_iter

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl &'a Fields as IntoIterator>::into_iter(self: Self) -> <Self as >::IntoIter`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl OpaqueMetadata as PartialEq>::eq

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl OpaqueMetadata as PartialEq>::eq(self: &Self, other: &OpaqueMetadata) -> bool`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl SchemaBuilder as From<Schema>>::from

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl SchemaBuilder as From<Schema>>::from(value: Schema) -> Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `bf3bea79fea764a95586500047aeadbd1b0dbe059416f56d86bb87c68e781bad`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl DataType as CloneToUninit>::clone_to_uninit

Disposition: **conditional**.

Interface: `unsafe fn arrow_schema::<impl DataType as CloneToUninit>::clone_to_uninit(self: &Self, dest: *mut u8) -> ()`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl Flags as Flags>::bits

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl Flags as Flags>::bits(self: &Self) -> i64`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl Field>::with_name

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Field>::with_name(self: Self, name: impl Into<String>) -> Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `0c7e9ef9d9be0a1ee64c12d214a5035b9fc6f2bcf92e497d89d71747f6feaddb`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Flags>::all

Disposition: **rejected**.

Interface: `const fn arrow_schema::<impl Flags>::all() -> Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `2660e46ad3d854c4fd5650ff0ef4da75826b5a048fddac0d1fe148a21e723a85`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl FFI_ArrowSchema as TryFrom<&Field>>::try_from

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl FFI_ArrowSchema as TryFrom<&Field>>::try_from(field: &Field) -> Result<Self, ArrowError>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `1eba0abaf646274df9152accf538c61d354dc86961ea056952104be004a60a5b`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Fields>::size

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl Fields>::size(self: &Self) -> usize`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl FixedShapeTensor as Debug>::fmt

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl FixedShapeTensor as Debug>::fmt(self: &Self, f: &mut $crate::fmt::Formatter<'_>) -> $crate::fmt::Result`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `10a776fb9e519b15bc62220368afb2de814c811c6726dc10434c1f45ac400858`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Schema>::field_with_name

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Schema>::field_with_name(self: &Self, name: &str) -> Result<&Field, ArrowError>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `5554f24373207b07f4812813631756b99ca887d83c89092f510729b216097a9f`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Field>::set_name

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl Field>::set_name(self: &mut Self, name: impl Into<String>) -> ()`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl Field>::extension_type

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl Field>::extension_type<E: ExtensionType>(self: &Self) -> E`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl Field as Deserialize<'de>>::deserialize

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Field as Deserialize<'de>>::deserialize<__D>(__deserializer: __D) -> _serde::__private229::Result<Self, <__D as >::Error> where __D: _serde::Deserializer<'de>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `01110da7c4ff4286ab419989c7125d0b7c58e317af910da9fe59b11e58e090f1`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl UnionFields as Hash>::hash

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl UnionFields as Hash>::hash<__H: $crate::hash::Hasher>(self: &Self, state: &mut __H) -> ()`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl DataType>::primitive_width

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl DataType>::primitive_width(self: &Self) -> Option<usize>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `7575716049842f35bdca7e179d3091f4e0d7bea49145fc88e5b6fd3f85db0d0c`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Flags as BitXor>::bitxor

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Flags as BitXor>::bitxor(self: Self, other: Self) -> Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `9bcb9e054f5781719799e5634e0f1312b94be28f3c61cbb2060149642f43f164`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Flags>::from_bits

Disposition: **rejected**.

Interface: `const fn arrow_schema::<impl Flags>::from_bits(bits: i64) -> $crate::__private::core::option::Option<Self>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `a8805190b9cf539638edb39253f68ddd5e61199befbc92ac3af0b3453cd251bb`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl FixedShapeTensor>::list_size

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl FixedShapeTensor>::list_size(self: &Self) -> usize`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::extension::ExtensionType::metadata

Disposition: **conditional**.

Interface: `fn arrow_schema::extension::ExtensionType::metadata(self: &Self) -> &<Self as >::Metadata`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl VariableShapeTensorMetadata as Clone>::clone

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl VariableShapeTensorMetadata as Clone>::clone(self: &Self) -> VariableShapeTensorMetadata`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `50a67f00f8e9b4e965a4b539fb107fe36617ac2cb40ceec9cfd98fa5474ce4d6`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Fields>::try_filter_leaves

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Fields>::try_filter_leaves<F: FnMut(usize, &FieldRef) -> Result<bool, ArrowError>>(self: &Self, filter: F) -> Result<Self, ArrowError>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `9dff276a776862175f41bd3c24137b140d6a4d61d770b7dd41b28644762501bf`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Flags>::symmetric_difference

Disposition: **rejected**.

Interface: `const fn arrow_schema::<impl Flags>::symmetric_difference(self: Self, other: Self) -> Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `15d8d7e3e5db1154fe472978513fc45267010e91091be5001b1cf9d509419290`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl VariableShapeTensorMetadata>::try_new

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl VariableShapeTensorMetadata>::try_new(dimensions: usize, dimension_names: Option<Vec<String>>, permutations: Option<Vec<usize>>, uniform_shapes: Option<Vec<Option<i32>>>) -> Result<Self, ArrowError>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `63330ede5d6c870aff09208f61c0595a9894ed1f8f2ce3cdfc5121402210f8ec`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl DataType>::equals_datatype

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl DataType>::equals_datatype(self: &Self, other: &DataType) -> bool`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl Bool8 as ExtensionType>::validate

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Bool8 as ExtensionType>::validate(data_type: &DataType, _metadata: <Self as >::Metadata) -> Result<(), ArrowError>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `a4dd468a1efc6971cb88e97627a744f3c07f317b865bd0a6e9500142cbbeb928`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl SortOptions as Default>::default

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl SortOptions as Default>::default() -> Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `a9ac217f1453a863b0e9f283e228baf2a44633926c5ab64dd62c361f71405d48`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl DataType as Hash>::hash

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl DataType as Hash>::hash<__H: $crate::hash::Hasher>(self: &Self, state: &mut __H) -> ()`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl Uuid as ExtensionType>::validate

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Uuid as ExtensionType>::validate(data_type: &DataType, _metadata: <Self as >::Metadata) -> Result<(), ArrowError>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `84226c9046aeb3541ced06a733bc085507127ca4ee9082919d413386aab2b5e5`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Field>::has_valid_extension_type

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl Field>::has_valid_extension_type<E: ExtensionType>(self: &Self) -> bool`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl FFI_ArrowSchema>::map_keys_sorted

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl FFI_ArrowSchema>::map_keys_sorted(self: &Self) -> bool`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl Flags as BitXorAssign>::bitxor_assign

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl Flags as BitXorAssign>::bitxor_assign(self: &mut Self, other: Self) -> ()`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl TimestampWithOffset as Default>::default

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl TimestampWithOffset as Default>::default() -> TimestampWithOffset`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `c9eb9e3051cfa0fd1d554ddb0ab3731e7dffc2c2b4a4019d6ece7c17e42b1bac`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Schema as Deserialize<'de>>::deserialize

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Schema as Deserialize<'de>>::deserialize<__D>(__deserializer: __D) -> _serde::__private229::Result<Self, <__D as >::Error> where __D: _serde::Deserializer<'de>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `c5397bab73a572ab6014c5f15b1ea3060cfd601289096ee6cb19c6790fa54149`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Schema>::new

Disposition: **eligible**.

Interface: `fn arrow_schema::<impl Schema>::new(fields: impl Into<Fields>) -> Self`.

- `documented_operation_class = construct-object`: **supported**. An applicable qualified assertion satisfies the requirement.
  Evidence assertions: `4e888892b8ab0063f226169411e5d98d84c0c6616f8d73c0238c9926386c91b3`.
- `declares_nominal_output = arrow_schema::schema::Schema`: **supported**. An applicable qualified assertion satisfies the requirement.
  Evidence assertions: `48c41bf6432149f32171f90ec9ffc238d2788db0d8d31a6447523cd97dd582dc`.

Re-evaluation triggers:

- Re-evaluate fab91b62e1b7ed7c2e7af229c2cd135058515f889362efe9533ceb7649042b64 when required value or applicability changes.
- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Field>::try_merge

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Field>::try_merge(self: &mut Self, from: &Field) -> Result<(), ArrowError>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `56d62c54203536625fc95a2336444612e66e2c691da3194373fca9ab383db6df`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Json as ExtensionType>::deserialize_metadata

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Json as ExtensionType>::deserialize_metadata(metadata: Option<&str>) -> Result<<Self as >::Metadata, ArrowError>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `5a52857c616d09a4ccff7c890054473a34dd0050edc3dd9fbe64839714eeba45`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl SchemaBuilder>::push

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl SchemaBuilder>::push(self: &mut Self, field: impl Into<FieldRef>) -> ()`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl Field>::metadata_mut

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl Field>::metadata_mut(self: &mut Self) -> &mut HashMap<String, String>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl Field>::set_nullable

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl Field>::set_nullable(self: &mut Self, nullable: bool) -> ()`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl Flags>::intersection

Disposition: **rejected**.

Interface: `const fn arrow_schema::<impl Flags>::intersection(self: Self, other: Self) -> Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `28be8c49577d9ea6ad3751598e5bd6ca17e8471026e73f327c692810fe206039`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl FixedShapeTensorMetadata>::try_new

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl FixedShapeTensorMetadata>::try_new(shape: impl IntoIterator<Item = usize>, dimension_names: Option<Vec<String>>, permutations: Option<Vec<usize>>) -> Result<Self, ArrowError>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `b351802258a5b24b196fa11ef8d2496463a05d3de5af3d4bb23aca6452239325`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl TimestampWithOffset as ExtensionType>::deserialize_metadata

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl TimestampWithOffset as ExtensionType>::deserialize_metadata(metadata: Option<&str>) -> Result<<Self as >::Metadata, ArrowError>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `0afaf9cb5fde473a85e3edc30bc0d5abdf95dc5f789c1090c4a0f66b6e08a347`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl UnionMode as Serialize>::serialize

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl UnionMode as Serialize>::serialize<__S>(self: &Self, __serializer: __S) -> _serde::__private229::Result<<__S as >::Ok, <__S as >::Error> where __S: _serde::Serializer`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `23a7da33802daaa2b819cb482055fb2970ed9c5ab73b87b335c5e5830dcaaff0`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Bool8 as ExtensionType>::try_new

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Bool8 as ExtensionType>::try_new(data_type: &DataType, _metadata: <Self as >::Metadata) -> Result<Self, ArrowError>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `5422ba5e599ec45eb3ccf66b2eabc86218a40df1dd367d0edd9885375bd095e9`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl DataType as TryFrom<&str>>::try_from

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl DataType as TryFrom<&str>>::try_from(value: &str) -> Result<Self, <Self as >::Error>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `11832f4e48fb332cbcc0de47677953d42b5603c4505a9a3494f86431dd9b4c11`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl JsonMetadata as Default>::default

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl JsonMetadata as Default>::default() -> JsonMetadata`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `dee72a54602cd52129896841edd039578f1934ca43795bf52eaccb991270bfcc`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl DataType>::is_decimal

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl DataType>::is_decimal(self: &Self) -> bool`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl SchemaBuilder>::metadata

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl SchemaBuilder>::metadata(self: &mut Self) -> &HashMap<String, String>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl DataType as Deserialize<'de>>::deserialize

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl DataType as Deserialize<'de>>::deserialize<__D>(__deserializer: __D) -> _serde::__private229::Result<Self, <__D as >::Error> where __D: _serde::Deserializer<'de>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `296dbd18920c59784df1e42df2308ffb4534c6a8890be23f587bcb72540d0f07`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Bool8 as Clone>::clone

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Bool8 as Clone>::clone(self: &Self) -> Bool8`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `5f7d30cda458aefdd8601ea5de99876e85d21c35f4fb91bfa922f7392fb4b609`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Flags>::bits

Disposition: **conditional**.

Interface: `const fn arrow_schema::<impl Flags>::bits(self: &Self) -> i64`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl FixedShapeTensor>::value_type

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl FixedShapeTensor>::value_type(self: &Self) -> &DataType`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl FixedShapeTensor as ExtensionType>::serialize_metadata

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl FixedShapeTensor as ExtensionType>::serialize_metadata(self: &Self) -> Option<String>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `2575c87dfb0c46d91c47351779c6bb8049d50006ba0f7e58b9214e25a4632c35`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl SortOptions as Not>::not

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl SortOptions as Not>::not(self: Self) -> SortOptions`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `f311e539dfe930f86bcf7a9b66e264d2c422cbba773fa8f633ec2c28f93612f7`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl CanonicalExtensionType as From<Bool8>>::from

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl CanonicalExtensionType as From<Bool8>>::from(value: Bool8) -> Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `35b8e214d8240a3df0acd5f274b79f7b3f0d523c4ae44360b0adb69c8a4f5f23`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Field>::name

Disposition: **conditional**.

Interface: `const fn arrow_schema::<impl Field>::name(self: &Self) -> &String`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl Opaque as ExtensionType>::validate

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Opaque as ExtensionType>::validate(_data_type: &DataType, _metadata: <Self as >::Metadata) -> Result<(), ArrowError>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `14276cfa3b970ae3618f9acfdf173d428268f9065988e8504249f98036c02b15`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl VariableShapeTensor as ExtensionType>::deserialize_metadata

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl VariableShapeTensor as ExtensionType>::deserialize_metadata(metadata: Option<&str>) -> Result<<Self as >::Metadata, ArrowError>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `73ba674fe9d64db5b72c378788bb3b320456f1e520d4bb8640ce24de8c3cbcb9`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl SortOptions as Debug>::fmt

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl SortOptions as Debug>::fmt(self: &Self, f: &mut $crate::fmt::Formatter<'_>) -> $crate::fmt::Result`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `b7ba9cf0fc9bf61ded9badadecda89644596fbaa6d9452d4cb7995f7e0ebe456`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl IntervalUnit as PartialOrd>::partial_cmp

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl IntervalUnit as PartialOrd>::partial_cmp(self: &Self, other: &IntervalUnit) -> $crate::option::Option<$crate::cmp::Ordering>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `640cf4c6cc8086dcffdae33ebd97b7c1d48d4b030cd34035993234f50bd604e2`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl VariableShapeTensor>::permutations

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl VariableShapeTensor>::permutations(self: &Self) -> Option<&[usize]>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `b9108e096b0856ae866eacbc35396b343abb3b36e852a9e589e8693c77c1c193`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Fields>::contains

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl Fields>::contains(self: &Self, other: &Fields) -> bool`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl Flags as FromIterator<Flags>>::from_iter

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Flags as FromIterator<Flags>>::from_iter<T: $crate::__private::core::iter::IntoIterator<Item = Self>>(iterator: T) -> Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `e66d1dc1ef196c2d1110cfc75a5b1a403952fb6cfb2c0290ceebbc54d7093a4d`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl FFI_ArrowSchema>::with_name

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl FFI_ArrowSchema>::with_name(self: Self, name: &str) -> Result<Self, ArrowError>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `e7e2c732fa9bb275fe2c5abea9a85b9d9ec3ed7465ab64d85db93ac41ce11a74`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl DataType as PartialEq>::eq

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl DataType as PartialEq>::eq(self: &Self, other: &DataType) -> bool`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl SchemaBuilder>::try_merge

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl SchemaBuilder>::try_merge(self: &mut Self, field: &FieldRef) -> Result<(), ArrowError>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `6a6bf3103132dd52338242cb500f73dec5aa765c5cc70de3cdbd1a3c2dc96a96`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Field>::new_union

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Field>::new_union<S, F, T>(name: S, type_ids: T, fields: F, mode: UnionMode) -> Self where S: Into<String>, F: IntoIterator, <F as >::Item: Into<FieldRef>, T: IntoIterator<Item = i8>`.

- `documented_operation_class = construct-object`: **supported**. An applicable qualified assertion satisfies the requirement.
  Evidence assertions: `1ee909737c2de8f67497e226fb5742494b656cb372f1f47281827d40b32f6bd7`.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `9281ffd9f25aa98d9b1775f346073901a441108becf82bc8c4a409c516e6e2d4`.

Re-evaluation triggers:

- Re-evaluate fab91b62e1b7ed7c2e7af229c2cd135058515f889362efe9533ceb7649042b64 when required value or applicability changes.
- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl FFI_ArrowSchema>::format

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl FFI_ArrowSchema>::format(self: &Self) -> &str`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl UnionFields>::iter

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl UnionFields>::iter(self: &Self) -> impl Iterator<Item = (i8, &FieldRef)> + '_`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl FFI_ArrowSchema>::name

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl FFI_ArrowSchema>::name(self: &Self) -> Option<&str>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `5dc8ca163109daa5acf76fe2a70038345b1020ae80c96f70fee80b9893cf4fed`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Field>::new_map

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Field>::new_map(name: impl Into<String>, entries: impl Into<String>, keys: impl Into<FieldRef>, values: impl Into<FieldRef>, sorted: bool, nullable: bool) -> Self`.

- `documented_operation_class = construct-object`: **supported**. An applicable qualified assertion satisfies the requirement.
  Evidence assertions: `45e6d1abb11d445aa24b243170ed1dcd56cdb1789526ac6b07ccb565e30338ab`.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `ab4ea1342a8619235ef2869b0a6bfde112a8af8a68d46394aaea8fc637ea28d7`.

Re-evaluation triggers:

- Re-evaluate fab91b62e1b7ed7c2e7af229c2cd135058515f889362efe9533ceb7649042b64 when required value or applicability changes.
- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl VariableShapeTensorMetadata>::uniform_shapes

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl VariableShapeTensorMetadata>::uniform_shapes(self: &Self) -> Option<&[Option<i32>]>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `c5a77af4721b12b3427284f6b9b57770c06ba6cb45ecb215365ae59ea219026d`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl VariableShapeTensorMetadata as PartialEq>::eq

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl VariableShapeTensorMetadata as PartialEq>::eq(self: &Self, other: &VariableShapeTensorMetadata) -> bool`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl Field>::new_large_list

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Field>::new_large_list(name: impl Into<String>, value: impl Into<FieldRef>, nullable: bool) -> Self`.

- `documented_operation_class = construct-object`: **supported**. An applicable qualified assertion satisfies the requirement.
  Evidence assertions: `3c34effb3de6b095dd21e66781443de2a0f88c857b9989b3c16be4f21ae38cb7`.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `ea5756d4b63344aef2f4cffb69683ca5b91a2e106d37bd0deeff97ef0148afd4`.

Re-evaluation triggers:

- Re-evaluate fab91b62e1b7ed7c2e7af229c2cd135058515f889362efe9533ceb7649042b64 when required value or applicability changes.
- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl FixedShapeTensor as ExtensionType>::try_new

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl FixedShapeTensor as ExtensionType>::try_new(data_type: &DataType, metadata: <Self as >::Metadata) -> Result<Self, ArrowError>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `bd1756983198a47b8b7111569655998bf7f8162a9134400939bdcc9dcaba4912`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl TimestampWithOffset as Debug>::fmt

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl TimestampWithOffset as Debug>::fmt(self: &Self, f: &mut $crate::fmt::Formatter<'_>) -> $crate::fmt::Result`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `438927ecb05d1710ae28b7cb6b0d66c78dd4acb99fad722fb68cde20f04224f3`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl DataType as ToOwned>::clone_into

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl DataType as ToOwned>::clone_into(self: &Self, target: &mut T) -> ()`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl Flags as Flags>::all_named

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Flags as Flags>::all_named() -> Flags`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `37ad6a18aa660b4f08e3c7c177881a248f5d0c793ed8057710f7c0e9a042b5b9`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl CanonicalExtensionType as From<FixedShapeTensor>>::from

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl CanonicalExtensionType as From<FixedShapeTensor>>::from(value: FixedShapeTensor) -> Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `7586ab4062bd021d0b68ff95033190ebdcc27c4e7d976eeebe39bf4d08f7f94a`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl DataType as Serialize>::serialize

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl DataType as Serialize>::serialize<__S>(self: &Self, __serializer: __S) -> _serde::__private229::Result<<__S as >::Ok, <__S as >::Error> where __S: _serde::Serializer`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `1df2e364aea817c7d6a45e0735079c1b69925f86ed748e0367c822d9de6f8ace`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Opaque as ExtensionType>::metadata

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl Opaque as ExtensionType>::metadata(self: &Self) -> &<Self as >::Metadata`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl DataType as Debug>::fmt

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl DataType as Debug>::fmt(self: &Self, f: &mut $crate::fmt::Formatter<'_>) -> $crate::fmt::Result`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `f0a09c9d2d3732aebfecd5b58eb80deb2505d65c596c7eb3ea0b11dc35f2755e`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl UnionFields as Ord>::cmp

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl UnionFields as Ord>::cmp(self: &Self, other: &UnionFields) -> $crate::cmp::Ordering`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `0aeaf3e2d0a1df08b2a26eb2d417f0ee27dec04e64610b86bb5d831c0bf91373`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl UnionFields>::try_from_fields

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl UnionFields>::try_from_fields<F>(fields: F) -> Result<Self, ArrowError> where F: IntoIterator, <F as >::Item: Into<FieldRef>`.

- `documented_operation_class = construct-object`: **supported**. An applicable qualified assertion satisfies the requirement.
  Evidence assertions: `755d636b286afcec5c57810461eaca51c2b0b1cdf3758e39e49b6195beb46241`.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `8b928afbb826410a6f0e1a896326147baced72500d880070bc89d26262f5c208`.

Re-evaluation triggers:

- Re-evaluate fab91b62e1b7ed7c2e7af229c2cd135058515f889362efe9533ceb7649042b64 when required value or applicability changes.
- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Flags>::set

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl Flags>::set(self: &mut Self, other: Self, value: bool) -> ()`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl Uuid as Debug>::fmt

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Uuid as Debug>::fmt(self: &Self, f: &mut $crate::fmt::Formatter<'_>) -> $crate::fmt::Result`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `fac8c0da8f695e5dcc6c44517932109f61c1ab6b292bbe45e3b21dba775787ae`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl SortOptions>::asc

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl SortOptions>::asc(self: Self) -> Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `d0917a8c305bc906a817289dc1ba3af8ecb7ec1c98c07bc877fd84128876c576`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl ArrowError as From<Error>>::from

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl ArrowError as From<Error>>::from(error: std::io::Error) -> Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `f970cc08d8e49a85d6d34c22f912dbd76b5c233d7b85cc71cd75772628653450`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Field>::new_list

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Field>::new_list(name: impl Into<String>, value: impl Into<FieldRef>, nullable: bool) -> Self`.

- `documented_operation_class = construct-object`: **supported**. An applicable qualified assertion satisfies the requirement.
  Evidence assertions: `d95a38a387e48dde3cfac1241f417a3a8526e8072b2cf44ecc9e0b68d5312b7a`.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `4c52abefaba52ca1ecc56d98029ea9524303e53ec51226458d208ec773398871`.

Re-evaluation triggers:

- Re-evaluate fab91b62e1b7ed7c2e7af229c2cd135058515f889362efe9533ceb7649042b64 when required value or applicability changes.
- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Field>::contains

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl Field>::contains(self: &Self, other: &Field) -> bool`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::extension::ExtensionType::serialize_metadata

Disposition: **rejected**.

Interface: `fn arrow_schema::extension::ExtensionType::serialize_metadata(self: &Self) -> Option<String>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `6fffae6364125609d3fa26d591c8b25575b5465ce35c53422ecdef155395d8d4`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Field>::try_extension_type

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Field>::try_extension_type<E: ExtensionType>(self: &Self) -> Result<E, ArrowError>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `63e86bbdafc40d314d4f461451c4015997fb6dc58d7db503cf783c3857744ccf`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl FFI_ArrowSchema>::dictionary_ordered

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl FFI_ArrowSchema>::dictionary_ordered(self: &Self) -> bool`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl Schema as PartialEq>::eq

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl Schema as PartialEq>::eq(self: &Self, other: &Schema) -> bool`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl Field as Hash>::hash

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl Field as Hash>::hash<H: Hasher>(self: &Self, state: &mut H) -> ()`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl ArrowError as Display>::fmt

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl ArrowError as Display>::fmt(self: &Self, f: &mut Formatter<'_>) -> std::fmt::Result`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `2161a9238381af810d609d85aa538ea00a43fa1cc108cc96a0d2dd7467daadea`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Field>::with_nullable

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Field>::with_nullable(self: Self, nullable: bool) -> Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `f98347c33c4e68e36ba5a155435150d98300504e9a25625db660a6c509fa0ae5`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl VariableShapeTensor as ExtensionType>::try_new

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl VariableShapeTensor as ExtensionType>::try_new(data_type: &DataType, metadata: <Self as >::Metadata) -> Result<Self, ArrowError>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `d349c44c77a51db8d76a5b253e735c6a1f56b7d445ccf019cae853dddcb6c80a`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl FFI_ArrowSchema as TryFrom<&Schema>>::try_from

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl FFI_ArrowSchema as TryFrom<&Schema>>::try_from(schema: &Schema) -> Result<Self, ArrowError>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `78f0352d2c667ad2d5c5b70f787c4a838561951ac6004dab3abee715e965229a`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Schema>::fields

Disposition: **conditional**.

Interface: `const fn arrow_schema::<impl Schema>::fields(self: &Self) -> &Fields`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl VariableShapeTensor>::dimensions

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl VariableShapeTensor>::dimensions(self: &Self) -> usize`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl Json as ExtensionType>::supports_data_type

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Json as ExtensionType>::supports_data_type(self: &Self, data_type: &DataType) -> Result<(), ArrowError>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `a4c937fe5d6742b752e7ddaebebd7bfe7385ac9f75745c02a139d4c65332523f`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl crate::Field as TryFrom<&FFI_ArrowSchema>>::try_from

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl crate::Field as TryFrom<&FFI_ArrowSchema>>::try_from(c_schema: &FFI_ArrowSchema) -> Result<Self, ArrowError>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `b5a04bb12e89b64eefab132b1e63c637a4efc1a530e183bc6af328e6f24bcb87`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Field>::new_struct

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Field>::new_struct(name: impl Into<String>, fields: impl Into<Fields>, nullable: bool) -> Self`.

- `documented_operation_class = construct-object`: **supported**. An applicable qualified assertion satisfies the requirement.
  Evidence assertions: `3ef1dc4994ddc39792eda44b4bf5cd1786d0465ab0fbc0a5937a914d1c0a2d98`.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `6c678daaf6195393282bd604ceac5d4f6fec09292f0d83fe79597a708cc2c53f`.

Re-evaluation triggers:

- Re-evaluate fab91b62e1b7ed7c2e7af229c2cd135058515f889362efe9533ceb7649042b64 when required value or applicability changes.
- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Flags>::from_bits_retain

Disposition: **rejected**.

Interface: `const fn arrow_schema::<impl Flags>::from_bits_retain(bits: i64) -> Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `8b484a6fb0f6bee95d1fadcd6f04110342945d38e67ccd4e8fc13ae3324426ec`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Flags as Not>::not

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Flags as Not>::not(self: Self) -> Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `a471f8bcca30b0cedbee180e1401cdc049560d0c470dc91f997f8f22a67f3a8d`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl FFI_ArrowSchema as Debug>::fmt

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl FFI_ArrowSchema as Debug>::fmt(self: &Self, f: &mut $crate::fmt::Formatter<'_>) -> $crate::fmt::Result`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `63a2e0287f96231b2a17388a7295b9e908b9f305332919421548f988b2090cf2`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Field as Serialize>::serialize

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Field as Serialize>::serialize<__S>(self: &Self, __serializer: __S) -> _serde::__private229::Result<<__S as >::Ok, <__S as >::Error> where __S: _serde::Serializer`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `a0ccdd261c46cb2352e70afe8b9e7e316e8c9fa046d3a614b480359d30139c4d`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Opaque as PartialEq>::eq

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl Opaque as PartialEq>::eq(self: &Self, other: &Opaque) -> bool`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl JsonMetadata as Debug>::fmt

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl JsonMetadata as Debug>::fmt(self: &Self, f: &mut $crate::fmt::Formatter<'_>) -> $crate::fmt::Result`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `f9571fdf03fa725c698ae035f2823f69455936cf99389e200841a43c65326a2d`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl OpaqueMetadata as Deserialize<'de>>::deserialize

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl OpaqueMetadata as Deserialize<'de>>::deserialize<D>(deserializer: D) -> Result<Self, <D as >::Error> where D: Deserializer<'de>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `f7f1f166ee903d2477f14256fdb4e265c36898593af5441958cf6967681d4ac6`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Field>::new_list_field

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Field>::new_list_field(data_type: DataType, nullable: bool) -> Self`.

- `documented_operation_class = construct-object`: **supported**. An applicable qualified assertion satisfies the requirement.
  Evidence assertions: `fec4159fde8374a01fe0169e3132884d5f440de37bbb47f8b19bca7e435fe44b`.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `182a0b277e9f8673bdfc1b16a626fcd0b0d17020d14a31121b499a3f415d86f3`.

Re-evaluation triggers:

- Re-evaluate fab91b62e1b7ed7c2e7af229c2cd135058515f889362efe9533ceb7649042b64 when required value or applicability changes.
- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl SchemaBuilder>::field

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl SchemaBuilder>::field(self: &mut Self, idx: usize) -> &FieldRef`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl TimestampWithOffset as ExtensionType>::metadata

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl TimestampWithOffset as ExtensionType>::metadata(self: &Self) -> &<Self as >::Metadata`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl SchemaBuilder>::reverse

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl SchemaBuilder>::reverse(self: &mut Self) -> ()`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl Field>::try_with_extension_type

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Field>::try_with_extension_type<E: ExtensionType>(self: &mut Self, extension_type: E) -> Result<(), ArrowError>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `1fce36db48d70116f3a1ab95ac0b848209b365351b93f4b3dcf68367e76ccffa`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Schema>::empty

Disposition: **eligible**.

Interface: `fn arrow_schema::<impl Schema>::empty() -> Self`.

- `documented_operation_class = construct-object`: **supported**. An applicable qualified assertion satisfies the requirement.
  Evidence assertions: `dcfd2976f89d8a72a9e39c95b02f686c3167f1053e4930851f9bb2707b8895af`.
- `declares_nominal_output = arrow_schema::schema::Schema`: **supported**. An applicable qualified assertion satisfies the requirement.
  Evidence assertions: `407f3ad98dde4084342ba811f686e6c8dd2f3fe91339c05c87367f34f0cf4385`.

Re-evaluation triggers:

- Re-evaluate fab91b62e1b7ed7c2e7af229c2cd135058515f889362efe9533ceb7649042b64 when required value or applicability changes.
- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl ArrowError as Error>::source

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl ArrowError as Error>::source(self: &Self) -> Option<&dyn Error + 'static>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `c38a3ba466c8d245666b98f7df505375f5df77fbdd31bf2796cd12efcae3e8a5`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Field as Display>::fmt

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Field as Display>::fmt(self: &Self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `cc8489ec74fe45cb21f7ccb556c244f3fc6fc25485439b93591367450fc7cf5b`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl UnionFields>::try_new

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl UnionFields>::try_new<F, T>(type_ids: T, fields: F) -> Result<Self, ArrowError> where F: IntoIterator, <F as >::Item: Into<FieldRef>, T: IntoIterator<Item = i8>`.

- `documented_operation_class = construct-object`: **supported**. An applicable qualified assertion satisfies the requirement.
  Evidence assertions: `299e9c381dcbf51d6b41d862273cf6f25a3b57ecf05edac74343dd21256a90cb`.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `0f6f591827dc88f054345cef115a0f90cd8692e9330671c048d55a155fd80b50`.

Re-evaluation triggers:

- Re-evaluate fab91b62e1b7ed7c2e7af229c2cd135058515f889362efe9533ceb7649042b64 when required value or applicability changes.
- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl UnionFields as PartialOrd>::partial_cmp

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl UnionFields as PartialOrd>::partial_cmp(self: &Self, other: &UnionFields) -> $crate::option::Option<$crate::cmp::Ordering>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `3b64dae355f4226cd778786c27795dd23ec3e0014cee4c7ecaccaf26130d601b`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl SortOptions as PartialOrd>::partial_cmp

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl SortOptions as PartialOrd>::partial_cmp(self: &Self, other: &SortOptions) -> $crate::option::Option<$crate::cmp::Ordering>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `27cf091cfab422b87d13286550663076b5316f87829a18d2eda9d6a059133b42`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl UnionMode as Debug>::fmt

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl UnionMode as Debug>::fmt(self: &Self, f: &mut $crate::fmt::Formatter<'_>) -> $crate::fmt::Result`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `9b4af193d32f1c64f05591fa59ae86b31eb01474f569228a569412617172c850`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl FixedShapeTensor as ExtensionType>::supports_data_type

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl FixedShapeTensor as ExtensionType>::supports_data_type(self: &Self, data_type: &DataType) -> Result<(), ArrowError>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `5ff9039495ae14a053981eacf67d75ef8a2fc9e55bf659fc2a98cbdf3d9e2602`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl FixedShapeTensorMetadata>::list_size

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl FixedShapeTensorMetadata>::list_size(self: &Self) -> usize`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl Json as Default>::default

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Json as Default>::default() -> Json`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `dd243809dc7838732e20d5364f86046dec08a671db5684772ec15c3638d19b62`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Opaque as ExtensionType>::supports_data_type

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Opaque as ExtensionType>::supports_data_type(self: &Self, _data_type: &DataType) -> Result<(), ArrowError>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `d273c56b89daa54e3d904bc908ad826f95732c7aebddfc90065a416df7c0ad4e`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl FFI_ArrowSchema as Drop>::drop

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl FFI_ArrowSchema as Drop>::drop(self: &mut Self) -> ()`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl Field as Clone>::clone

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Field as Clone>::clone(self: &Self) -> Field`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `1e95d0887ded3e9a54627cddb52d6ab002745f49c231fc20f60898e76b86ee4f`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl FixedShapeTensor as PartialEq>::eq

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl FixedShapeTensor as PartialEq>::eq(self: &Self, other: &FixedShapeTensor) -> bool`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl SchemaBuilder as Extend<Field>>::extend

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl SchemaBuilder as Extend<Field>>::extend<T: IntoIterator<Item = Field>>(self: &mut Self, iter: T) -> ()`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl Flags as Octal>::fmt

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Flags as Octal>::fmt(self: &Self, f: &mut $crate::__private::core::fmt::Formatter<'_>) -> $crate::__private::core::fmt::Result`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `407e11f6c9913139d6cacecd42ab295e88bbcf45fffc27fdbc811c840927ff1b`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Field>::with_data_type

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Field>::with_data_type(self: Self, data_type: DataType) -> Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `dc8d0fa5a0b288b420bc62df5cc82de6a253ffa86996a3a7ac9e128b6238df0e`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl FixedShapeTensorMetadata as Serialize>::serialize

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl FixedShapeTensorMetadata as Serialize>::serialize<S>(self: &Self, serializer: S) -> Result<<S as >::Ok, <S as >::Error> where S: Serializer`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `e239c48544c5702d4c1084787c5162f3819688962aa4c983e252b5ce4049d8d1`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Flags>::is_all

Disposition: **conditional**.

Interface: `const fn arrow_schema::<impl Flags>::is_all(self: &Self) -> bool`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl SchemaBuilder>::remove

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl SchemaBuilder>::remove(self: &mut Self, idx: usize) -> FieldRef`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `01705f82b7f9ccca53c93da6634ae222986007511e5b18847b7a2820bd3d9806`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::extension::ExtensionType::validate

Disposition: **rejected**.

Interface: `fn arrow_schema::extension::ExtensionType::validate(data_type: &DataType, metadata: <Self as >::Metadata) -> Result<(), ArrowError>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `9eb0c2f97d41da0b81ce23cd1ba946afc0a06a14e482bbded70de6803c311af7`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl FixedShapeTensorMetadata as PartialEq>::eq

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl FixedShapeTensorMetadata as PartialEq>::eq(self: &Self, other: &FixedShapeTensorMetadata) -> bool`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl Field>::with_metadata

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Field>::with_metadata(self: Self, metadata: HashMap<String, String>) -> Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `76e9aee37481db7dec245b2c898f19278e4c04a175024aa46dce70fae94a0811`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl IntervalUnit as Deserialize<'de>>::deserialize

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl IntervalUnit as Deserialize<'de>>::deserialize<__D>(__deserializer: __D) -> _serde::__private229::Result<Self, <__D as >::Error> where __D: _serde::Deserializer<'de>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `1152e5764cc21622091562ffbfdd7a4d8b07efafd6c3f70bf41ef540794b2667`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl CanonicalExtensionType as From<Json>>::from

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl CanonicalExtensionType as From<Json>>::from(value: Json) -> Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `423934251b22284d83ac982e40f6d9d90682f8d5fff506a541e087a2f241757b`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Uuid as PartialEq>::eq

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl Uuid as PartialEq>::eq(self: &Self, other: &Uuid) -> bool`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl Bool8 as PartialEq>::eq

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl Bool8 as PartialEq>::eq(self: &Self, other: &Bool8) -> bool`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl Schema as Debug>::fmt

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Schema as Debug>::fmt(self: &Self, f: &mut $crate::fmt::Formatter<'_>) -> $crate::fmt::Result`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `25fb1b12b6c25c833a0fdf91ce24dfea896c45d584c02afcfb093cd55f058299`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl SortOptions>::nulls_last

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl SortOptions>::nulls_last(self: Self) -> Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `1ff411b096f03a6b5fbffcb396f12e8705a27fff4d534efc3965dc4fe7fc533a`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl DataType as BorrowMut<T>>::borrow_mut

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl DataType as BorrowMut<T>>::borrow_mut(self: &mut Self) -> &mut T`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl FixedShapeTensorMetadata as Clone>::clone

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl FixedShapeTensorMetadata as Clone>::clone(self: &Self) -> FixedShapeTensorMetadata`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `60c0ca195566011b6f22cf11b763ca5b9f1a80f2e1d5a9a94b924042194cdf60`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl SchemaBuilder as From<&Schema>>::from

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl SchemaBuilder as From<&Schema>>::from(value: &Schema) -> Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `799ab70b0e0ad9a081f6f430f7f794764beb61d039124381427757e16b2e1b02`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl TimeUnit as Deserialize<'de>>::deserialize

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl TimeUnit as Deserialize<'de>>::deserialize<__D>(__deserializer: __D) -> _serde::__private229::Result<Self, <__D as >::Error> where __D: _serde::Deserializer<'de>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `3b8613599c8ab60f139f1ba5a00ccdd25356f80a5fa612c92e1b304b213a2727`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl SortOptions>::with_nulls_first

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl SortOptions>::with_nulls_first(self: Self, nulls_first: bool) -> Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `552231fb7e99208d58a6748767186d9abc8fced0593e6344ca821adda2d15fd2`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Opaque as Clone>::clone

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Opaque as Clone>::clone(self: &Self) -> Opaque`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `63f5000e010fadb377440d2cacd41726bc7b0d4d85a2d21e64920f754a9a5852`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Field>::set_data_type

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl Field>::set_data_type(self: &mut Self, data_type: DataType) -> ()`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl Flags as BitOrAssign>::bitor_assign

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl Flags as BitOrAssign>::bitor_assign(self: &mut Self, other: Self) -> ()`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl TimestampWithOffset as ExtensionType>::try_new

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl TimestampWithOffset as ExtensionType>::try_new(data_type: &DataType, _metadata: <Self as >::Metadata) -> Result<Self, ArrowError>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `7229b4b8283347229f66ed157743028e7517bb445312113f8334b2b6d7f5d7d8`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl FixedShapeTensorMetadata as Deserialize<'de>>::deserialize

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl FixedShapeTensorMetadata as Deserialize<'de>>::deserialize<D>(deserializer: D) -> Result<Self, <D as >::Error> where D: Deserializer<'de>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `b2614474187192ec88a0c32e05cd36f04616744d8645d684875aa98b69972291`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl DataType>::is_run_ends_type

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl DataType>::is_run_ends_type(self: &Self) -> bool`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl DataType>::is_primitive

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl DataType>::is_primitive(self: &Self) -> bool`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl FFI_ArrowSchema>::metadata

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl FFI_ArrowSchema>::metadata(self: &Self) -> Result<HashMap<String, String>, ArrowError>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `d9e474c3392a64c5b04a78394ad4634df3083ad684fc6bea6a1a918dcc6ca410`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Fields as Deserialize<'de>>::deserialize

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Fields as Deserialize<'de>>::deserialize<__D>(__deserializer: __D) -> _serde::__private229::Result<Self, <__D as >::Error> where __D: _serde::Deserializer<'de>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `ca7af8b0b7198e88a4d279ab493dc74ec27af9d8a95f33df873069f58e5f8f0a`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl TimeUnit as Serialize>::serialize

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl TimeUnit as Serialize>::serialize<__S>(self: &Self, __serializer: __S) -> _serde::__private229::Result<<__S as >::Ok, <__S as >::Error> where __S: _serde::Serializer`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `ef0a4b9ad76b9211140053164296b6fff27d7cd32372ac5af830da6b93e489e6`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl CanonicalExtensionType as PartialEq>::eq

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl CanonicalExtensionType as PartialEq>::eq(self: &Self, other: &CanonicalExtensionType) -> bool`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl FixedShapeTensorMetadata>::dimensions

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl FixedShapeTensorMetadata>::dimensions(self: &Self) -> usize`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl OpaqueMetadata>::type_name

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl OpaqueMetadata>::type_name(self: &Self) -> &str`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl DataType as FromStr>::from_str

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl DataType as FromStr>::from_str(s: &str) -> Result<Self, <Self as >::Err>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `f9105d91e0a58ff8289dcf87717d17553d918aaa4e6b78019c6872dbf6789f23`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Schema as Hash>::hash

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl Schema as Hash>::hash<H: std::hash::Hasher>(self: &Self, state: &mut H) -> ()`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl Fields as PartialOrd>::partial_cmp

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Fields as PartialOrd>::partial_cmp(self: &Self, other: &Fields) -> $crate::option::Option<$crate::cmp::Ordering>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `af2891e3394af5c784ac37c1a7525155c1a174a7a1345d74a51d4d64158fca91`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl crate::Schema as TryFrom<&FFI_ArrowSchema>>::try_from

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl crate::Schema as TryFrom<&FFI_ArrowSchema>>::try_from(c_schema: &FFI_ArrowSchema) -> Result<Self, ArrowError>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `fe56e52cfea1cb7058d16eeb2a48c5b01c5e563c2e462e81b0a034f6db916992`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Schema as Serialize>::serialize

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Schema as Serialize>::serialize<__S>(self: &Self, __serializer: __S) -> _serde::__private229::Result<<__S as >::Ok, <__S as >::Error> where __S: _serde::Serializer`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `6116d9da9ced9786b272ba26bf37988f90e758c066ab85577878e76df9fdf4b8`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Field>::size

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl Field>::size(self: &Self) -> usize`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl Fields>::empty

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Fields>::empty() -> Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `a176202dbc0d564ef8e2fefaf89049241a2685170a800b9f94a8968efbe8d728`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Flags>::from_bits_truncate

Disposition: **rejected**.

Interface: `const fn arrow_schema::<impl Flags>::from_bits_truncate(bits: i64) -> Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `9075d21c49f65a9373e6059a2fbc8a9088b0e6ce611ad465cb150048065e834b`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl ArrowError as From<FromUtf8Error>>::from

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl ArrowError as From<FromUtf8Error>>::from(error: std::string::FromUtf8Error) -> Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `1d19cf7fb975444da7b18dcb2cc926035c550c5805e5f163c5258c9d3eb883af`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl FFI_ArrowSchema>::children

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl FFI_ArrowSchema>::children(self: &Self) -> impl Iterator<Item = &Self>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl CanonicalExtensionType as Clone>::clone

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl CanonicalExtensionType as Clone>::clone(self: &Self) -> CanonicalExtensionType`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `bbfc25ced8b388736ec8f8293f841751aeff339e6a43124b983fa3328cf7411f`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl UnionFields>::empty

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl UnionFields>::empty() -> Self`.

- `documented_operation_class = construct-object`: **supported**. An applicable qualified assertion satisfies the requirement.
  Evidence assertions: `e1fa509f702b5b4af983840b4f9bfb4028e44db6c2977419c5d48948c56ddb73`.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `6028bf9924cd86445f646bb9e12cfa6991cbd9e0c44875d96800ddf86c107402`.

Re-evaluation triggers:

- Re-evaluate fab91b62e1b7ed7c2e7af229c2cd135058515f889362efe9533ceb7649042b64 when required value or applicability changes.
- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl SortOptions>::desc

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl SortOptions>::desc(self: Self) -> Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `938531e29f85197ea19782d5043602d7cccc845d1b190ee914a1011f2461d31e`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl CanonicalExtensionType as Debug>::fmt

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl CanonicalExtensionType as Debug>::fmt(self: &Self, f: &mut $crate::fmt::Formatter<'_>) -> $crate::fmt::Result`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `be8f3964e3d9679ab3d7e959d32054ea80abbb8cb3cdd27fe46e3cf8c274b8ac`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl CanonicalExtensionType as From<Opaque>>::from

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl CanonicalExtensionType as From<Opaque>>::from(value: Opaque) -> Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `bfdcab23932578958c1de4a83da3bda8643d04af7ad67b5c61c58251644290f8`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Fields as Serialize>::serialize

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Fields as Serialize>::serialize<__S>(self: &Self, __serializer: __S) -> _serde::__private229::Result<<__S as >::Ok, <__S as >::Error> where __S: _serde::Serializer`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `351d7501397ed1efb7a69550a70779121c6b80826c11a849b3795a85e9183587`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl FFI_ArrowSchema>::flags

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl FFI_ArrowSchema>::flags(self: &Self) -> Option<Flags>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `358a529b18bede022d838ead2d9179775eddb6d386a5515da29670798586b293`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl UnionFields>::find_by_field

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl UnionFields>::find_by_field(self: &Self, field: &Field) -> Option<(i8, &FieldRef)>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `adf403c4553cafdf5e3e88f340f49205792e10d72571cfd7490f30d0fa6ff895`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl DataType>::new_fixed_size_list

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl DataType>::new_fixed_size_list(data_type: DataType, size: i32, nullable: bool) -> Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `f91f2d6ef89d4e1959b6872be0e49db699df96ce493676f9543f76544d291f33`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl OpaqueMetadata>::vendor_name

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl OpaqueMetadata>::vendor_name(self: &Self) -> &str`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl ArrowError as Debug>::fmt

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl ArrowError as Debug>::fmt(self: &Self, f: &mut $crate::fmt::Formatter<'_>) -> $crate::fmt::Result`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `8f2e8af8e7362a761d785014cbab1b1a4e5d1711422db1ccdee96312fc36b1e7`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl TimestampWithOffset as ExtensionType>::supports_data_type

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl TimestampWithOffset as ExtensionType>::supports_data_type(self: &Self, data_type: &DataType) -> Result<(), ArrowError>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `1b03c54dcf30fc596231fb3c6681306e8c12538c7c1f6faf78d3f9a2fff0e046`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl FFI_ArrowSchema as TryFrom<Field>>::try_from

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl FFI_ArrowSchema as TryFrom<Field>>::try_from(field: Field) -> Result<Self, ArrowError>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `f202021f6967e5779c1ab7a3b5535dd69047bb0d90e4575abb426d7779eab1aa`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl DataType>::contains

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl DataType>::contains(self: &Self, other: &DataType) -> bool`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl UnionFields>::from_fields

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl UnionFields>::from_fields<F>(fields: F) -> Self where F: IntoIterator, <F as >::Item: Into<FieldRef>`.

- `documented_operation_class = construct-object`: **supported**. An applicable qualified assertion satisfies the requirement.
  Evidence assertions: `77a959cd5cd80869e785b32005bc9c783c3910e8af3c8e962e8ff2edf8b12a69`.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `a99a9031990e3722e2f458a48071f1340c7521b900c5e0188fa650dd743dc05f`.

Re-evaluation triggers:

- Re-evaluate fab91b62e1b7ed7c2e7af229c2cd135058515f889362efe9533ceb7649042b64 when required value or applicability changes.
- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Flags as BitAnd>::bitand

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Flags as BitAnd>::bitand(self: Self, other: Self) -> Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `ce6b5ab0e5e3c031080a778f8efeae143cb1012913a9221fae222b4903292fed`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl DataType as Clone>::clone

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl DataType as Clone>::clone(self: &Self) -> DataType`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `621ba3ec03486794b6b694405dca385bcb3b924aee456c9cc43412fb7a4a6293`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Schema>::normalize

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Schema>::normalize(self: &Self, separator: &str, max_level: Option<usize>) -> Result<Self, ArrowError>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `77449a9400d582d8a38669a2098a2d30c3e7f4aa527fe84dc05df657b8eec7df`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl OpaqueMetadata as Clone>::clone

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl OpaqueMetadata as Clone>::clone(self: &Self) -> OpaqueMetadata`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `ada5dd7810727a5f4370131bc1877e7600244b3889e9c73bfeee892d4269c2fd`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl TimestampWithOffset as ExtensionType>::validate

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl TimestampWithOffset as ExtensionType>::validate(data_type: &DataType, _metadata: <Self as >::Metadata) -> Result<(), ArrowError>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `e6c14736a5aa907e42924f6b6eeca41e8b40777f63361b5638f0a0a4125b7cdd`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Flags>::remove

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl Flags>::remove(self: &mut Self, other: Self) -> ()`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl DataType as Into<U>>::into

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl DataType as Into<U>>::into(self: Self) -> U`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl FixedShapeTensor as Clone>::clone

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl FixedShapeTensor as Clone>::clone(self: &Self) -> FixedShapeTensor`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `c2a4aa11003c15768ae6989db176828c69a0e7f87afab7f59c20a75f15583f49`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl FixedShapeTensor>::try_new

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl FixedShapeTensor>::try_new(value_type: DataType, shape: impl IntoIterator<Item = usize>, dimension_names: Option<Vec<String>>, permutations: Option<Vec<usize>>) -> Result<Self, ArrowError>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `da4c113715083c1e370b74363aa968c45ac0c03a55e833014666d9569fde8f41`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl DataType>::is_integer

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl DataType>::is_integer(self: &Self) -> bool`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl UnionFields as Index<usize>>::index

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl UnionFields as Index<usize>>::index(self: &Self, index: usize) -> &<Self as >::Output`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl CanonicalExtensionType as From<VariableShapeTensor>>::from

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl CanonicalExtensionType as From<VariableShapeTensor>>::from(value: VariableShapeTensor) -> Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `9b7740ff1b4fd24c363eb8fafae10329d65da9518f9a2bc081e201dee1dccd55`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Field>::new_dict

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Field>::new_dict(name: impl Into<String>, data_type: DataType, nullable: bool, dict_id: i64, dict_is_ordered: bool) -> Self`.

- `documented_operation_class = construct-object`: **supported**. An applicable qualified assertion satisfies the requirement.
  Evidence assertions: `c74f93e7fd3e8b67987a8a6010ff6422c29062cca11fee021b01e38fdeb96db0`.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `bb699d6cf23c87e42be04ba30228c84a3cdac1efe5999352d40ff056efd86ea1`.

Re-evaluation triggers:

- Re-evaluate fab91b62e1b7ed7c2e7af229c2cd135058515f889362efe9533ceb7649042b64 when required value or applicability changes.
- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl SchemaBuilder>::new

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl SchemaBuilder>::new() -> Self`.

- `documented_operation_class = construct-object`: **supported**. An applicable qualified assertion satisfies the requirement.
  Evidence assertions: `f6f072467fadb4f31c0362db2c685f303207ad4c89fb1f7ef3e1ab0afdb163c4`.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `7031af4325b61458f8400a9bfcdc196b5a0dff359e95e2e4de43e004c70a0b3c`.

Re-evaluation triggers:

- Re-evaluate fab91b62e1b7ed7c2e7af229c2cd135058515f889362efe9533ceb7649042b64 when required value or applicability changes.
- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl VariableShapeTensorMetadata as Debug>::fmt

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl VariableShapeTensorMetadata as Debug>::fmt(self: &Self, f: &mut $crate::fmt::Formatter<'_>) -> $crate::fmt::Result`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `6eca1b7c7b9412c45dfb7870d4727e110edcf21d0a6b0283d8a5c852129578c5`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Fields as Deref>::deref

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl Fields as Deref>::deref(self: &Self) -> &<Self as >::Target`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl Field>::metadata

Disposition: **conditional**.

Interface: `const fn arrow_schema::<impl Field>::metadata(self: &Self) -> &HashMap<String, String>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl SchemaBuilder>::metadata_mut

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl SchemaBuilder>::metadata_mut(self: &mut Self) -> &mut HashMap<String, String>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl Flags as Binary>::fmt

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Flags as Binary>::fmt(self: &Self, f: &mut $crate::__private::core::fmt::Formatter<'_>) -> $crate::__private::core::fmt::Result`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `2e160e6b61d6af0817bca6686cac11d25ee72a6f48dcf38d84b503467372b972`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl UnionFields>::get

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl UnionFields>::get(self: &Self, index: usize) -> Option<&(i8, FieldRef)>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `7f43f1da73094180f1fdc300262c494240d8c01f37299c4493367dbb9c57432d`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl UnionFields as FromIterator<(i8, Arc<Field>)>>::from_iter

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl UnionFields as FromIterator<(i8, Arc<Field>)>>::from_iter<T: IntoIterator<Item = (i8, FieldRef)>>(iter: T) -> Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `482b88308304d1d7a1c063c97bc6246abc0c565104e04521b4192357613aafb2`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Flags as Sub>::sub

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Flags as Sub>::sub(self: Self, other: Self) -> Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `4cba25468047e78bdde6845282b739b92196f138505a608530a346592bb57c6d`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl DataType>::is_dictionary_key_type

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl DataType>::is_dictionary_key_type(self: &Self) -> bool`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl UnionFields>::new

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl UnionFields>::new<F, T>(type_ids: T, fields: F) -> Self where F: IntoIterator, <F as >::Item: Into<FieldRef>, T: IntoIterator<Item = i8>`.

- `documented_operation_class = construct-object`: **supported**. An applicable qualified assertion satisfies the requirement.
  Evidence assertions: `6c93c0dfac3aebc01cf2806fbaec5eeec3fa55d1e92ce657e47802a534d3e684`.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `93b5aa5ae1e9221d220893e5f87f3112a4c7373c20098a7a2572d7fe71cc773c`.

Re-evaluation triggers:

- Re-evaluate fab91b62e1b7ed7c2e7af229c2cd135058515f889362efe9533ceb7649042b64 when required value or applicability changes.
- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Bool8 as Default>::default

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Bool8 as Default>::default() -> Bool8`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `5d694e2e8f260a3fe81c3dc56cc9b4975d1ea222da24a7daee1c4896aaba707b`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Flags as UpperHex>::fmt

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Flags as UpperHex>::fmt(self: &Self, f: &mut $crate::__private::core::fmt::Formatter<'_>) -> $crate::__private::core::fmt::Result`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `60288fdd65835df8315730cbecb1c13bc0e8e927b08919c78947968113de1986`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl VariableShapeTensor>::value_type

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl VariableShapeTensor>::value_type(self: &Self) -> &DataType`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl DataType>::is_nested

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl DataType>::is_nested(self: &Self) -> bool`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl VariableShapeTensor as Debug>::fmt

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl VariableShapeTensor as Debug>::fmt(self: &Self, f: &mut $crate::fmt::Formatter<'_>) -> $crate::fmt::Result`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `850f418b784c5b04ece25e03026f79ef2acecf29ba36bb88ded61cd26fcf2411`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl DataType as Borrow<T>>::borrow

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl DataType as Borrow<T>>::borrow(self: &Self) -> &T`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl JsonMetadata as PartialEq>::eq

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl JsonMetadata as PartialEq>::eq(self: &Self, other: &JsonMetadata) -> bool`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl Fields as From<Vec<Arc<Field>>>>::from

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Fields as From<Vec<Arc<Field>>>>::from(value: Vec<FieldRef>) -> Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `5af1a4b75f74a64450e265a83b7625bf4f3006026f5c8a4888ed14ca286016b6`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Field>::new_fixed_size_list

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Field>::new_fixed_size_list(name: impl Into<String>, value: impl Into<FieldRef>, size: i32, nullable: bool) -> Self`.

- `documented_operation_class = construct-object`: **supported**. An applicable qualified assertion satisfies the requirement.
  Evidence assertions: `23ef37811d1445e15eb47a708c509b5ea1696f464f1ee86f2fc276ba6e146414`.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `50613f55a6ba530c4da84ccac94a3cdd19624c108773af8242eb58cf59ef420a`.

Re-evaluation triggers:

- Re-evaluate fab91b62e1b7ed7c2e7af229c2cd135058515f889362efe9533ceb7649042b64 when required value or applicability changes.
- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl TimestampWithOffset as Clone>::clone

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl TimestampWithOffset as Clone>::clone(self: &Self) -> TimestampWithOffset`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `e3c945bdc0ced34a04b376528dfe7524411048d18cfd0e8fea05a16098c79342`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl IntervalUnit as Hash>::hash

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl IntervalUnit as Hash>::hash<__H: $crate::hash::Hasher>(self: &Self, state: &mut __H) -> ()`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl Opaque as ExtensionType>::try_new

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Opaque as ExtensionType>::try_new(_data_type: &DataType, metadata: <Self as >::Metadata) -> Result<Self, ArrowError>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `aac9edb6685571a19f7ccdf2e52179f96cb447749ec76fd7ef98011914b8d048`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl CanonicalExtensionType as From<TimestampWithOffset>>::from

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl CanonicalExtensionType as From<TimestampWithOffset>>::from(value: TimestampWithOffset) -> Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `e1e1b4dc64e4454718e14b4c6f3e23a90ea8d6b94e7e0924ec106a1652c57956`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Flags>::contains

Disposition: **conditional**.

Interface: `const fn arrow_schema::<impl Flags>::contains(self: &Self, other: Self) -> bool`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl Flags>::iter_names

Disposition: **rejected**.

Interface: `const fn arrow_schema::<impl Flags>::iter_names(self: &Self) -> $crate::iter::IterNames<Flags>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `0d7f8701af66018451a0d8c2cc7a0b6ba813846273c75ce863b45724a81b5074`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Json as ExtensionType>::metadata

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl Json as ExtensionType>::metadata(self: &Self) -> &<Self as >::Metadata`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl Bool8 as Debug>::fmt

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Bool8 as Debug>::fmt(self: &Self, f: &mut $crate::fmt::Formatter<'_>) -> $crate::fmt::Result`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `92b2337000bc907ae32774e0e6121b9054cae98a97e79c3c2ad30fcc2b7ef9c4`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Fields as Default>::default

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Fields as Default>::default() -> Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `a3ee41794592da71919b099e868dd7b4f19450b6817cbef1183da350f2a6bc0d`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl UnionFields>::size

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl UnionFields>::size(self: &Self) -> usize`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl FixedShapeTensorMetadata as Debug>::fmt

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl FixedShapeTensorMetadata as Debug>::fmt(self: &Self, f: &mut $crate::fmt::Formatter<'_>) -> $crate::fmt::Result`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `fe63d203165e70531690aceaa1d0943985cdcea5b3102ece623dada1ea874b2d`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Flags>::insert

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl Flags>::insert(self: &mut Self, other: Self) -> ()`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl Field>::with_dict_is_ordered

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Field>::with_dict_is_ordered(self: Self, dict_is_ordered: bool) -> Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `2b6f2a4cd94a3e6029d1d3de7c1f7887b95504bbab9cff0b5cbe264a69599891`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl UnionFields as Deserialize<'de>>::deserialize

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl UnionFields as Deserialize<'de>>::deserialize<__D>(__deserializer: __D) -> _serde::__private229::Result<Self, <__D as >::Error> where __D: _serde::Deserializer<'de>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `53041f2952cae4f6fa7df0e360aca52a001117cff46df42fa6ca960d5e4522e9`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Schema>::column_with_name

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Schema>::column_with_name(self: &Self, name: &str) -> Option<(usize, &Field)>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `36fba6cc67e9608fc85d7bcdf9a3d354952ac53977fb9805552a6709ade63861`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl TimestampWithOffset as ExtensionType>::serialize_metadata

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl TimestampWithOffset as ExtensionType>::serialize_metadata(self: &Self) -> Option<String>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `41e8ce6eaedbb2cc4691a7608dd7fa1d9c232e58bfd0b4c8747e52621ba376e5`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl DataType as Ord>::cmp

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl DataType as Ord>::cmp(self: &Self, other: &DataType) -> $crate::cmp::Ordering`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `e770f16ef6ed584117e825a270349de730fc39a6585289f3004609e425c7b866`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Field>::dict_is_ordered

Disposition: **rejected**.

Interface: `const fn arrow_schema::<impl Field>::dict_is_ordered(self: &Self) -> Option<bool>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `d7a2f5a77f05a6ba429463e7b624f15e905ba0fadc9a598a0f73911f172d40f7`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl DataType>::size

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl DataType>::size(self: &Self) -> usize`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl TimeUnit as PartialOrd>::partial_cmp

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl TimeUnit as PartialOrd>::partial_cmp(self: &Self, other: &TimeUnit) -> $crate::option::Option<$crate::cmp::Ordering>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `04d3e58cc55ce45383c37f60b82ed87863e53a634b4cfd3766b80c1004f9ae37`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl UnionMode as Clone>::clone

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl UnionMode as Clone>::clone(self: &Self) -> UnionMode`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `67ad7374fa8dfd7ca4f5b4e98dfa6baa7a9e82a56082ede02d93305fd943a439`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl IntervalUnit as Serialize>::serialize

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl IntervalUnit as Serialize>::serialize<__S>(self: &Self, __serializer: __S) -> _serde::__private229::Result<<__S as >::Ok, <__S as >::Error> where __S: _serde::Serializer`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `55e5056d26bb5c4c2cf001c36ba6afd34b6a6581b35ee1fbc8de6c846e209fe3`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl TimeUnit as PartialEq>::eq

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl TimeUnit as PartialEq>::eq(self: &Self, other: &TimeUnit) -> bool`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl Field as Ord>::cmp

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Field as Ord>::cmp(self: &Self, other: &Self) -> Ordering`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `35e68c348b90875eba1a06c65fa65bc8fd25bebeb6303751cccdfc64836ee854`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl OpaqueMetadata>::new

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl OpaqueMetadata>::new(type_name: impl Into<String>, vendor_name: impl Into<String>) -> Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `82bd60f945d8998b5ed2cdb95451c464d39af670ad7f6afd0dfbce3be3aef745`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Opaque>::new

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Opaque>::new(type_name: impl Into<String>, vendor_name: impl Into<String>) -> Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `1376cfa96ac0915b7700aee2063f78532f5cac13485255d37c67e90f976b2e14`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl UnionMode as Ord>::cmp

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl UnionMode as Ord>::cmp(self: &Self, other: &UnionMode) -> $crate::cmp::Ordering`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `27bcd3afaa9a8490de757fccc82c24fa2e3535eb26f5db7c38786d4efe5af861`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl IntervalUnit as Clone>::clone

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl IntervalUnit as Clone>::clone(self: &Self) -> IntervalUnit`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `9e1266b5c517ef5d2021861f562839080b301dfe031c0dd22516f6548418491c`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Flags as BitAndAssign>::bitand_assign

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl Flags as BitAndAssign>::bitand_assign(self: &mut Self, other: Self) -> ()`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl DataType>::is_unsigned_integer

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl DataType>::is_unsigned_integer(self: &Self) -> bool`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl Fields as Ord>::cmp

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Fields as Ord>::cmp(self: &Self, other: &Fields) -> $crate::cmp::Ordering`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `b626fc05d8ab1a6546116a7bee8a9f9a87c106c6fd79084459dfe591e1c29d59`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Field>::new

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Field>::new(name: impl Into<String>, data_type: DataType, nullable: bool) -> Self`.

- `documented_operation_class = construct-object`: **supported**. An applicable qualified assertion satisfies the requirement.
  Evidence assertions: `3ab9257117b96cb96a863834ec540d155a913cedb8b0c2f4155915877604d4c3`.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `0d7b1f01b504eefc21e9907b9098e548b3831edadf106ff4511ae81a746421a7`.

Re-evaluation triggers:

- Re-evaluate fab91b62e1b7ed7c2e7af229c2cd135058515f889362efe9533ceb7649042b64 when required value or applicability changes.
- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl CanonicalExtensionType as TryFrom<&Field>>::try_from

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl CanonicalExtensionType as TryFrom<&Field>>::try_from(value: &Field) -> Result<Self, <Self as >::Error>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `b8ecacf167ef830bbef61e0636261c10ccf90431896fbbe3e3a48f8cd0b893d3`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl VariableShapeTensorMetadata as Serialize>::serialize

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl VariableShapeTensorMetadata as Serialize>::serialize<S>(self: &Self, serializer: S) -> Result<<S as >::Ok, <S as >::Error> where S: Serializer`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `3a404a7b551a7f5416691a0fa53f7d94fbff991ad0e65309ba4f4d043ffc91e8`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::extension::ExtensionType::try_new

Disposition: **rejected**.

Interface: `fn arrow_schema::extension::ExtensionType::try_new(data_type: &DataType, metadata: <Self as >::Metadata) -> Result<Self, ArrowError>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `a512cc3c15169d246bc0ea04780ab4473a852ed2cf5b9466f10aea5d45d5575f`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl FFI_ArrowSchema>::dictionary

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl FFI_ArrowSchema>::dictionary(self: &Self) -> Option<&Self>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `0a44767c57a847372fa2dfcf128e72d9ae456471de632b7be08ed2d82ec149e2`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl UnionMode as Hash>::hash

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl UnionMode as Hash>::hash<__H: $crate::hash::Hasher>(self: &Self, state: &mut __H) -> ()`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl DataType>::is_string

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl DataType>::is_string(self: &Self) -> bool`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl Flags>::difference

Disposition: **rejected**.

Interface: `const fn arrow_schema::<impl Flags>::difference(self: Self, other: Self) -> Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `0278a59daca7b9b494b13367e0af07240a4bbfd5cb3899ccda5a47073aba3f64`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl IntervalUnit as Ord>::cmp

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl IntervalUnit as Ord>::cmp(self: &Self, other: &IntervalUnit) -> $crate::cmp::Ordering`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `4b232d86e50db34c16b5dcef6524b33244f47bbc8c83df8c7cc9b1b067284843`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl SchemaBuilder as Default>::default

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl SchemaBuilder as Default>::default() -> SchemaBuilder`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `e4b4a12558a6ce5331b37bb5693ac023286a64e6347362a8c04734cfa471ae6c`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Fields as From<[Arc<Field>; N]>>::from

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Fields as From<[Arc<Field>; N]>>::from(value: [FieldRef; N]) -> Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `7f1fcc8deaf1ecce90d25eff75ed755cb796a9b99879fda8a9350e5826aa5470`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Bool8 as ExtensionType>::serialize_metadata

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Bool8 as ExtensionType>::serialize_metadata(self: &Self) -> Option<String>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `35dfac7f1567c8459c9ad6f35aa8da21a092e15533074d071b2f3f4651ca8c9e`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl FixedShapeTensorMetadata>::permutations

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl FixedShapeTensorMetadata>::permutations(self: &Self) -> Option<&[usize]>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `7666a79c9c8bf4d402d7fef433236d682bc3dcabef0d76f48afa81a86ed1021b`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Uuid as ExtensionType>::metadata

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl Uuid as ExtensionType>::metadata(self: &Self) -> &<Self as >::Metadata`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl UnionFields as Serialize>::serialize

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl UnionFields as Serialize>::serialize<__S>(self: &Self, __serializer: __S) -> _serde::__private229::Result<<__S as >::Ok, <__S as >::Error> where __S: _serde::Serializer`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `55d28910fa4763196b7cbcd15ae15d358226b27b12ba856d6e123dc84ee3ecaa`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Field as PartialOrd>::partial_cmp

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Field as PartialOrd>::partial_cmp(self: &Self, other: &Self) -> Option<Ordering>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `c4464235f7633cf008209c034391cd2262e9f0b28589b3473340182bb2f3f7c3`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Opaque as Debug>::fmt

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Opaque as Debug>::fmt(self: &Self, f: &mut $crate::fmt::Formatter<'_>) -> $crate::fmt::Result`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `3efcdd7615bc88c54f29f13d099eb13b423a37fbf50a2eb1aebf8e2afb9dede7`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Schema>::contains

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl Schema>::contains(self: &Self, other: &Schema) -> bool`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl Fields as From<Vec<Field>>>::from

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Fields as From<Vec<Field>>>::from(value: Vec<Field>) -> Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `980df1d0b2d6d7401a05e0033f8101a038eff8ed36bb895f6cacfd54893b1796`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl FFI_ArrowSchema as TryFrom<DataType>>::try_from

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl FFI_ArrowSchema as TryFrom<DataType>>::try_from(dtype: DataType) -> Result<Self, ArrowError>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `8683bbc02ba2da2b2c19107541a38df2f23d2ed3beebec39725091048afc4ea3`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl DataType>::is_temporal

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl DataType>::is_temporal(self: &Self) -> bool`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl Opaque as ExtensionType>::serialize_metadata

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Opaque as ExtensionType>::serialize_metadata(self: &Self) -> Option<String>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `5b504a9918568f2bbdd91706305f9a050a58751446a58c3ce005349e40eee613`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Schema>::new_with_metadata

Disposition: **eligible**.

Interface: `fn arrow_schema::<impl Schema>::new_with_metadata(fields: impl Into<Fields>, metadata: HashMap<String, String>) -> Self`.

- `documented_operation_class = construct-object`: **supported**. An applicable qualified assertion satisfies the requirement.
  Evidence assertions: `53dd87ecbc4a7d6c754a307a3f8bdaad1ff87370a01a65075904d18d8c297e04`.
- `declares_nominal_output = arrow_schema::schema::Schema`: **supported**. An applicable qualified assertion satisfies the requirement.
  Evidence assertions: `f0954bcbcd42001ba471a91644a2d2c800b5b7eec43d9e02d017a5a017b955d0`.

Re-evaluation triggers:

- Re-evaluate fab91b62e1b7ed7c2e7af229c2cd135058515f889362efe9533ceb7649042b64 when required value or applicability changes.
- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Fields as From<&[Arc<Field>]>>::from

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Fields as From<&[Arc<Field>]>>::from(value: &[FieldRef]) -> Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `8a014da3255b73a97ef8d9630f3ba8a7035197d755de9420c6ad837978f83120`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::extension::ExtensionType::deserialize_metadata

Disposition: **rejected**.

Interface: `fn arrow_schema::extension::ExtensionType::deserialize_metadata(metadata: Option<&str>) -> Result<<Self as >::Metadata, ArrowError>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
  Evidence assertions: `a4d253e1ca22525d5e64dc1b64ce9ce77d60950d9141133fd3ef4c7a7c18601b`.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `97dd8eec75fbbfd579f71b62fd912e433bba878887694c954d45270536ecc0be`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl crate::DataType as Display>::fmt

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl crate::DataType as Display>::fmt(self: &Self, f: &mut fmt::Formatter<'_>) -> fmt::Result`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `73150ad4505d0cfef5896c99c15a7f668688b0732c58f6002620b090d0881dcb`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl DataType as ToOwned>::to_owned

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl DataType as ToOwned>::to_owned(self: &Self) -> T`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl SchemaBuilder>::finish

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl SchemaBuilder>::finish(self: Self) -> Schema`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **supported**. An applicable qualified assertion satisfies the requirement.
  Evidence assertions: `a6588765efd19b84a039924be2f7423d8ddfa584f6fe3e1a91b4eb402e3d5a99`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl DataType>::is_signed_integer

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl DataType>::is_signed_integer(self: &Self) -> bool`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl SortOptions as PartialEq>::eq

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl SortOptions as PartialEq>::eq(self: &Self, other: &SortOptions) -> bool`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl SortOptions>::new

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl SortOptions>::new(descending: bool, nulls_first: bool) -> Self`.

- `documented_operation_class = construct-object`: **supported**. An applicable qualified assertion satisfies the requirement.
  Evidence assertions: `08a54112642d5218457ac6db9b489ee343f2fdc75a2128385e6e8e032ceb577b`.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `04cfd6f78bf5c73da4132736b0a2acde857773d5171e9b48656bbafdf92526f1`.

Re-evaluation triggers:

- Re-evaluate fab91b62e1b7ed7c2e7af229c2cd135058515f889362efe9533ceb7649042b64 when required value or applicability changes.
- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Uuid as ExtensionType>::serialize_metadata

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Uuid as ExtensionType>::serialize_metadata(self: &Self) -> Option<String>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `c981eea660273d2fa2f90fbd081f107d0e3f5380ab0202e1aff523970ea263c7`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl SchemaBuilder as From<Fields>>::from

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl SchemaBuilder as From<Fields>>::from(value: Fields) -> Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `ed35074b1b2048c62d03ad7730f0561c210724f23df5ee738a2a8b4fbeec5206`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Opaque>::type_name

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl Opaque>::type_name(self: &Self) -> &str`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl SortOptions as Clone>::clone

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl SortOptions as Clone>::clone(self: &Self) -> SortOptions`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `65a63f43282219d79a2de0a4b95de59c417c6938c21a8d83ec0559cde804f11a`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Bool8 as ExtensionType>::deserialize_metadata

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Bool8 as ExtensionType>::deserialize_metadata(metadata: Option<&str>) -> Result<<Self as >::Metadata, ArrowError>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `b30b6b087903b9b9eee4e15cf9cc58c1374cb347f9780edeb1bf1aa8c9733b5f`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl DataType>::is_binary

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl DataType>::is_binary(self: &Self) -> bool`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl IntervalUnit as Debug>::fmt

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl IntervalUnit as Debug>::fmt(self: &Self, f: &mut $crate::fmt::Formatter<'_>) -> $crate::fmt::Result`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `f53b13601adcfae5be548c5437f9fb3fe6ea30b86924165490e9a883ab4f6efb`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl DataType>::is_floating

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl DataType>::is_floating(self: &Self) -> bool`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl Json as ExtensionType>::validate

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Json as ExtensionType>::validate(data_type: &DataType, _metadata: <Self as >::Metadata) -> Result<(), ArrowError>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `471a7b5a245b5a28077f07f810017d414713b638498d47b405b32dc99b45ffe4`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl FFI_ArrowSchema>::nullable

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl FFI_ArrowSchema>::nullable(self: &Self) -> bool`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl Bool8 as ExtensionType>::supports_data_type

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Bool8 as ExtensionType>::supports_data_type(self: &Self, data_type: &DataType) -> Result<(), ArrowError>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `52539ff24471cf7c9cdfecfabd3050a4a10d896127d9b60c17f03c2b2323aa0e`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl VariableShapeTensor as PartialEq>::eq

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl VariableShapeTensor as PartialEq>::eq(self: &Self, other: &VariableShapeTensor) -> bool`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl DataType as TryFrom<U>>::try_from

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl DataType as TryFrom<U>>::try_from(value: U) -> Result<T, <T as TryFrom<U>>::Error>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `25bbf30af8620f6ed8d2660167c5e7aec53775ffce7cf2eda1cd70d4f767d7a2`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Field as PartialEq>::eq

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl Field as PartialEq>::eq(self: &Self, other: &Self) -> bool`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl SortOptions>::nulls_first

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl SortOptions>::nulls_first(self: Self) -> Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `016c7cc4f3bc060008702153d9ee60b86c15370b24f678f102ce260a3e7b4810`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl FFI_ArrowSchema>::try_new

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl FFI_ArrowSchema>::try_new(format: &str, children: Vec<FFI_ArrowSchema>, dictionary: Option<FFI_ArrowSchema>) -> Result<Self, ArrowError>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `b808a658db782c889a718fc7e9d993c681cd7626bb9ef844db70e832a91135b2`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Field>::set_metadata

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl Field>::set_metadata(self: &mut Self, metadata: HashMap<String, String>) -> ()`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl SchemaBuilder as From<&Fields>>::from

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl SchemaBuilder as From<&Fields>>::from(value: &Fields) -> Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `44f681923243ff799071e70c34b8510ceb8eb16dce301e1ffff2dcbe2fd81482`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Field as AsRef<Field>>::as_ref

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl Field as AsRef<Field>>::as_ref(self: &Self) -> &Field`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl VariableShapeTensor as Clone>::clone

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl VariableShapeTensor as Clone>::clone(self: &Self) -> VariableShapeTensor`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `297996519c9ecf715867bc4f4b785d1e66cddd83801a38fe266d947b088d20bd`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Field>::is_nullable

Disposition: **conditional**.

Interface: `const fn arrow_schema::<impl Field>::is_nullable(self: &Self) -> bool`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl Uuid as Default>::default

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Uuid as Default>::default() -> Uuid`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `7ec49d160926156d03006ffd2c06c4f6045a608866fafc2eae8ea441208f0e80`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Flags>::iter

Disposition: **rejected**.

Interface: `const fn arrow_schema::<impl Flags>::iter(self: &Self) -> $crate::iter::Iter<Flags>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `47f6bbef1cdb5fe959f2c4529d5c69bd88bc496eabdf445398b55ff211c89d16`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl ArrowError>::from_external_error

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl ArrowError>::from_external_error(error: Box<dyn Error + Send + Sync>) -> Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `38804472b6c08bd2077be10fb504e55b4a04f8186d9e897bf874479d1bbfa055`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl SchemaBuilder as Debug>::fmt

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl SchemaBuilder as Debug>::fmt(self: &Self, f: &mut $crate::fmt::Formatter<'_>) -> $crate::fmt::Result`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `6f49f607016fc8e4cf1972ef237e54412185b583431c7caf75035905b483fc07`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl TimeUnit as Debug>::fmt

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl TimeUnit as Debug>::fmt(self: &Self, f: &mut $crate::fmt::Formatter<'_>) -> $crate::fmt::Result`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `205ef4ad83530de9605d12a83169d8c2210cb8620c06688b1aed14027e2388fb`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Schema>::metadata

Disposition: **conditional**.

Interface: `const fn arrow_schema::<impl Schema>::metadata(self: &Self) -> &HashMap<String, String>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl SortOptions as Hash>::hash

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl SortOptions as Hash>::hash<__H: $crate::hash::Hasher>(self: &Self, state: &mut __H) -> ()`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl Schema as AsRef<Schema>>::as_ref

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl Schema as AsRef<Schema>>::as_ref(self: &Self) -> &Schema`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl Field>::dict_id

Disposition: **rejected**.

Interface: `const fn arrow_schema::<impl Field>::dict_id(self: &Self) -> Option<i64>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `e1e9d9df71d1fd86d06a9f646cacfe6dc94db14ac88928d18c47129839ac5042`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl SchemaBuilder>::with_capacity

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl SchemaBuilder>::with_capacity(capacity: usize) -> Self`.

- `documented_operation_class = construct-object`: **supported**. An applicable qualified assertion satisfies the requirement.
  Evidence assertions: `bb945eb62d1d01be430874fa8bfc7a1611d7b7ca29e0937ca591a43f64d23902`.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `618138e8c6398b64ab37fff89700e757aa6b93278fe83b1af2cd70a1f0bc1d16`.

Re-evaluation triggers:

- Re-evaluate fab91b62e1b7ed7c2e7af229c2cd135058515f889362efe9533ceb7649042b64 when required value or applicability changes.
- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl FixedShapeTensor as ExtensionType>::metadata

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl FixedShapeTensor as ExtensionType>::metadata(self: &Self) -> &<Self as >::Metadata`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl Flags>::is_empty

Disposition: **conditional**.

Interface: `const fn arrow_schema::<impl Flags>::is_empty(self: &Self) -> bool`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl Flags>::toggle

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl Flags>::toggle(self: &mut Self, other: Self) -> ()`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl Json as PartialEq>::eq

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl Json as PartialEq>::eq(self: &Self, other: &Json) -> bool`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl Flags>::complement

Disposition: **rejected**.

Interface: `const fn arrow_schema::<impl Flags>::complement(self: Self) -> Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `f44b8593ac5e26f9ac4b790bf3494edcfb1c7b13e9114b3c1ac7f92ccb6e0251`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl UnionFields>::find_by_type_id

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl UnionFields>::find_by_type_id(self: &Self, type_id: i8) -> Option<(i8, &FieldRef)>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `563d227c5f2431fc6b4dfa602c091961edb0704982186ac1f2b0a84202521c57`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl VariableShapeTensor>::try_new

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl VariableShapeTensor>::try_new(value_type: DataType, dimensions: usize, dimension_names: Option<Vec<String>>, permutations: Option<Vec<usize>>, uniform_shapes: Option<Vec<Option<i32>>>) -> Result<Self, ArrowError>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `9504eb2b2a11b3832a48a9e50307ed102e618b0122c68942804edad76b4adc2f`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Opaque as ExtensionType>::deserialize_metadata

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Opaque as ExtensionType>::deserialize_metadata(metadata: Option<&str>) -> Result<<Self as >::Metadata, ArrowError>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `fd6e245f2519b6a98f05c7f6c8f60523922629d561f3aa5db31e7a461470e162`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Fields as FromIterator<Arc<Field>>>::from_iter

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Fields as FromIterator<Arc<Field>>>::from_iter<T: IntoIterator<Item = FieldRef>>(iter: T) -> Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `689a6201625e0d7e3897a4d6a57bc7a68b05fec98e1ac8ca77be87aee78a3ef0`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Fields as PartialEq>::eq

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl Fields as PartialEq>::eq(self: &Self, other: &Fields) -> bool`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl UnionMode as PartialEq>::eq

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl UnionMode as PartialEq>::eq(self: &Self, other: &UnionMode) -> bool`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl SortOptions as Display>::fmt

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl SortOptions as Display>::fmt(self: &Self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `e262e7ee32b109aab87cb91f434adaa0dc852366812ab0d84b15234bddaffa84`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Field>::try_canonical_extension_type

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Field>::try_canonical_extension_type(self: &Self) -> Result<CanonicalExtensionType, ArrowError>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `613f96f1e7b16aa74e1206b8d539acb851b539fdd115ad73a8031d02c3a842d0`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl DataType as ToString>::to_string

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl DataType as ToString>::to_string(self: &Self) -> String`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `d53bd6f10c5452ed57adb4aebea7b472b234869032b71c86b8f448a859b76003`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Fields as Hash>::hash

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl Fields as Hash>::hash<__H: $crate::hash::Hasher>(self: &Self, state: &mut __H) -> ()`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl SortOptions as Ord>::cmp

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl SortOptions as Ord>::cmp(self: &Self, other: &SortOptions) -> $crate::cmp::Ordering`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `1b73cbcec2160a781430eb659bdcbd9f4d52f8d3565a439bf9aaf4295fe55d15`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl FFI_ArrowSchema>::child

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl FFI_ArrowSchema>::child(self: &Self, index: usize) -> &Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl FFI_ArrowSchema as TryFrom<&Arc<Field>>>::try_from

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl FFI_ArrowSchema as TryFrom<&Arc<Field>>>::try_from(value: &FieldRef) -> Result<Self, <Self as >::Error>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `7418b5821e636e7e288a170ff8b31075fa5e819de776630144238cbe4b0ad2f7`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl FFI_ArrowSchema as TryFrom<&DataType>>::try_from

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl FFI_ArrowSchema as TryFrom<&DataType>>::try_from(dtype: &DataType) -> Result<Self, ArrowError>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `f8c339011bc03ccfbbc5198caac1a930db8892d15ecfda8070f3731c8af5a504`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Uuid as ExtensionType>::deserialize_metadata

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Uuid as ExtensionType>::deserialize_metadata(metadata: Option<&str>) -> Result<<Self as >::Metadata, ArrowError>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `a3e91bda7869ff109156dced077af453337cffd88207948b9f69ca01af321511`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Field>::extension_type_name

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Field>::extension_type_name(self: &Self) -> Option<&str>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `b0ccd2d37a213be1c101a21169b3808f6a8d18ddc1d4f1c24eb58000519b6317`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl FFI_ArrowSchema>::with_metadata

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl FFI_ArrowSchema>::with_metadata<I, S>(self: Self, metadata: I) -> Result<Self, ArrowError> where I: IntoIterator<Item = (S, S)>, S: AsRef<str>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `3f061c06b19bbd683820b44ac42f8e54c3928f9612d70a5471f407d17281f59a`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Schema as Display>::fmt

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Schema as Display>::fmt(self: &Self, f: &mut fmt::Formatter<'_>) -> fmt::Result`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `791dfdb5aef4760c24880acc94d647067afb01d6f190d25c6d7b6e3aed8b8d24`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl FFI_ArrowSchema>::from_raw

Disposition: **rejected**.

Interface: `unsafe fn arrow_schema::<impl FFI_ArrowSchema>::from_raw(schema: *mut FFI_ArrowSchema) -> Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `d78d875e0cf8e129ae6c694bce566cf95e19e7e5b1489927d0dc6291d47cca98`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Fields>::find

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Fields>::find(self: &Self, name: &str) -> Option<(usize, &FieldRef)>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `db06433ad6aac8459d3d6748422a482a33ddbea5d96a19ba7bbd1ae72284f59d`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl DataType>::is_numeric

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl DataType>::is_numeric(self: &Self) -> bool`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl FixedShapeTensor as ExtensionType>::deserialize_metadata

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl FixedShapeTensor as ExtensionType>::deserialize_metadata(metadata: Option<&str>) -> Result<<Self as >::Metadata, ArrowError>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `14a135fd30fd71395ee9e01daa2715b874c50e83a60295d926e437d7f9c9ff74`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Field>::with_extension_type

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Field>::with_extension_type<E: ExtensionType>(self: Self, extension_type: E) -> Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `acd5f25a92a33881194e41d652412db198f5db37cb7c5031f77b01ce2e93863e`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl UnionFields>::len

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl UnionFields>::len(self: &Self) -> usize`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl SchemaBuilder>::field_mut

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl SchemaBuilder>::field_mut(self: &mut Self, idx: usize) -> &mut FieldRef`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl Flags>::from_name

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Flags>::from_name(name: &str) -> $crate::__private::core::option::Option<Self>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `2f517b842fa1b379436a445166a8d0d398c840041d7ffe8d3618560b9d6dc67e`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl DataType as From<T>>::from

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl DataType as From<T>>::from(t: T) -> T`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl Flags as BitOr>::bitor

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Flags as BitOr>::bitor(self: Self, other: Flags) -> Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `59dd59fa692e36b433cec45d4f2dd5645258fda8ec63b8a48236837012a3195c`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl UnionFields as Debug>::fmt

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl UnionFields as Debug>::fmt(self: &Self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `a524266f6a3f90032a390380f14b01f50ef7e19431453c4fee572afe6c49a332`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl SortOptions>::with_descending

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl SortOptions>::with_descending(self: Self, descending: bool) -> Self`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `beb16fa013f6534bf05aa6a7dc2d47c5d00fde3839dae1d8db02cb5327d8d3f3`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl OpaqueMetadata as Serialize>::serialize

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl OpaqueMetadata as Serialize>::serialize<S>(self: &Self, serializer: S) -> Result<<S as >::Ok, <S as >::Error> where S: Serializer`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `d315d47584a3808719bd8f203d8cb47173545fded30d16a327f896a85d902933`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Flags as Flags>::from_bits_retain

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Flags as Flags>::from_bits_retain(bits: i64) -> Flags`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `d9bf959528cf986e36380d729da99913f69f2f27dce2d7fef7c16ae3a42d249f`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl DataType>::is_null

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl DataType>::is_null(self: &Self) -> bool`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::<impl Flags as LowerHex>::fmt

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Flags as LowerHex>::fmt(self: &Self, f: &mut $crate::__private::core::fmt::Formatter<'_>) -> $crate::__private::core::fmt::Result`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `2e9bf0ec3b1e10cc468deaef3fbdab1d30a75282bf213e7d8f303104518670b7`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Flags as SubAssign>::sub_assign

Disposition: **conditional**.

Interface: `fn arrow_schema::<impl Flags as SubAssign>::sub_assign(self: &mut Self, other: Self) -> ()`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **unknown**. No adequate applicable support or refutation.

## arrow_schema::extension::ExtensionType::try_new_from_field_metadata

Disposition: **rejected**.

Interface: `fn arrow_schema::extension::ExtensionType::try_new_from_field_metadata(data_type: &DataType, metadata: &HashMap<String, String>) -> Result<Self, ArrowError>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `23a395cafceaa44dfd0e198e0ef22e740646da54a2dc3595fecf3fa0a3a4d8fa`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl Schema>::index_of

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl Schema>::index_of(self: &Self, name: &str) -> Result<usize, ArrowError>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `0f70854d8c12b207af1c9e24f5e9bce49ff841d327133a5b16088d592adf0109`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl VariableShapeTensor as ExtensionType>::supports_data_type

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl VariableShapeTensor as ExtensionType>::supports_data_type(self: &Self, data_type: &DataType) -> Result<(), ArrowError>`.

- `documented_operation_class = construct-object`: **unknown**. No adequate applicable support or refutation.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `2e1097c965bb8760a2214048aec2501c9b8e2ef28838e50603ef48e76884184c`.

Re-evaluation triggers:

- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## arrow_schema::<impl FFI_ArrowSchema>::empty

Disposition: **rejected**.

Interface: `fn arrow_schema::<impl FFI_ArrowSchema>::empty() -> Self`.

- `documented_operation_class = construct-object`: **supported**. An applicable qualified assertion satisfies the requirement.
  Evidence assertions: `5eebb1c5b4d1b67bb49c92b46de1da5df55c9b6b35849f68e8e58193972eaf24`.
- `declares_nominal_output = arrow_schema::schema::Schema`: **refuted**. An applicable qualified assertion excludes the required value.
  Evidence assertions: `770aec0bd28303a9a07d3fb9d15240684f3298f3e530adfcde88f1f01bed93c3`.

Re-evaluation triggers:

- Re-evaluate fab91b62e1b7ed7c2e7af229c2cd135058515f889362efe9533ceb7649042b64 when required value or applicability changes.
- Re-evaluate 49917e3e75d83eed0e1b884379956f9a4ba591043fa386ce61ce16987c70aab2 when required value or applicability changes.

## Unresolved scope

- No universal optimum is asserted; preferences and incomplete semantic coverage are explicit.
- Candidate membership digest: 59c5eca14b6c179bb372674555b20b8fd490d3b80cfe9ce0ee060b614301b963.
