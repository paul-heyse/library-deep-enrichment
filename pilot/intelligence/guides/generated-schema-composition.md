# Generated composition comparison

Models describe explicit intermediate state changes. Compiler and execution results apply only to the retained finite inputs.

## arrow_schema::<impl Schema>::new → arrow_schema::<impl Schema>::project

Task: Construct a schema, then project valid field indices while retaining dataset metadata

Profile: `rust-docsrs-54.1-58.4`. Modeled disposition: **rejected**.

Final modeled properties:

- `result.metadata` = ``

Finite witness: corroborated.

Evaluation: `91d07b0ab536b356515cc75d5b05e86d5411962e7a27b421a5923944454b0be5`. Plan: `e8eff027c28bf1170731c816c84dd70c3148f7f421ec2c5337a35e823185f318`.

Invocation and scope qualifications:

- Finite owned inputs and valid indices; borrowing and Result handling remain explicit in generated Rust; compiler/execution witness required
- Input semantic properties are not presumed preserved by type compatibility
- Native invocation, bounds, ownership, and effects require a matching witness or model

## arrow_schema::<impl Schema>::new_with_metadata → arrow_schema::<impl Schema>::project

Task: Construct a schema, then project valid field indices while retaining dataset metadata

Profile: `rust-docsrs-54.1-58.4`. Modeled disposition: **modeled-requires-witness**.

Final modeled properties:

- `result.metadata` = `measurements`

Finite witness: corroborated.

Evaluation: `867d9419ae7d1e5aa4b44d7f9eaa2b436eac2c75dab6ffe53a67d62180332f43`. Plan: `93d9b7a0cb15ee7d52c69a3eb7d14bd67c45dd955e2d8f88e31893a9be1e54a2`.

Invocation and scope qualifications:

- Finite owned inputs and valid indices; borrowing and Result handling remain explicit in generated Rust; compiler/execution witness required
- Input semantic properties are not presumed preserved by type compatibility
- Native invocation, bounds, ownership, and effects require a matching witness or model
