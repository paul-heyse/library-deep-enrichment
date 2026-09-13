use arrow_schema::{DataType, Field, Schema};
use std::collections::HashMap;

fn main() {
    let fields = vec![
        Field::new("temperature", DataType::Float64, true)
            .with_metadata(HashMap::from([("units".into(), "K".into())])),
        Field::new("id", DataType::Int64, false),
    ];
    let metadata = HashMap::from([("dataset".into(), "measurements".into())]);
    let source = Schema::new_with_metadata(fields, metadata);
    let projected = source.project(&[0]).expect("valid retained field index");
    let rebuilt = Schema::new(vec![source.field(0).clone()]);
    let reordered = source.project(&[1, 0]).expect("valid field permutation");
    let empty = source.project(&[]).expect("empty projection is valid");
    let duplicate = source.project(&[0, 0]).expect("duplicate valid indices");
    println!(
        "{{\"environment\":{{\"arrow-schema\":\"58.4.0\"}},\
        \"projection_preserves_metadata\":{},\
        \"reconstruction_preserves_metadata\":{},\
        \"projection_preserves_field_metadata\":{},\
        \"projection_preserves_nullability\":{},\
        \"projection_field_count\":{},\
        \"reordered_first_field_is_id\":{},\
        \"empty_projection_retains_metadata\":{},\
        \"duplicate_projection_fields\":{},\
        \"out_of_range_is_error\":{},\
        \"same_nominal_schema_type\":true}}",
        projected.metadata() == source.metadata(),
        rebuilt.metadata() == source.metadata(),
        projected.field(0).metadata() == source.field(0).metadata(),
        projected.field(0).is_nullable() == source.field(0).is_nullable(),
        projected.fields().len(),
        reordered.field(0).name() == "id",
        empty.metadata() == source.metadata(),
        duplicate.fields().len(),
        source.project(&[2]).is_err(),
    );
}
