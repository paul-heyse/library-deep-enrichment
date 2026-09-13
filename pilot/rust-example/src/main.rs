//! Behavioral pilot: projection, stream consumption, checked arithmetic and JSON IO.

use datafusion::{arrow::array::Int8Array, prelude::SessionContext};
use futures::StreamExt;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let context = SessionContext::new();
    let frame = context.sql("SELECT 1 + 1 AS result").await?;
    let collected = frame.clone().collect().await?;
    assert_eq!(
        collected
            .iter()
            .map(|batch| batch.num_rows())
            .sum::<usize>(),
        1
    );
    let mut stream = frame.execute_stream().await?;
    let batch = stream.next().await.ok_or("missing stream output")??;
    assert_eq!(batch, collected[0]);
    drop(stream);

    let lhs = Int8Array::from(vec![127_i8]);
    let rhs = Int8Array::from(vec![1_i8]);
    assert!(arrow_arith::numeric::add(&lhs, &rhs).is_err());

    let source = r#"{"count":3}"#;
    let from_text: serde_json::Value = serde_json::from_str(source)?;
    let from_reader: serde_json::Value = serde_json::from_reader(source.as_bytes())?;
    assert_eq!(from_text, from_reader);
    assert!(serde_json::from_str::<serde_json::Value>("{").is_err());
    let join = context.sql("SELECT l.id, r.label FROM (VALUES (1), (2)) l(id) LEFT JOIN (VALUES (1, 'a'), (1, 'b')) r(id, label) ON l.id = r.id").await?.collect().await?;
    assert_eq!(join.iter().map(|batch| batch.num_rows()).sum::<usize>(), 3);
    assert_eq!(
        join.iter()
            .map(|batch| batch.column(1).null_count())
            .sum::<usize>(),
        1
    );
    let groups = context
        .sql("SELECT k, SUM(v) FROM (VALUES ('a', 1), ('a', 2), ('b', 3)) t(k, v) GROUP BY k")
        .await?
        .collect()
        .await?;
    let windows = context.sql("SELECT k, SUM(v) OVER (PARTITION BY k) FROM (VALUES ('a', 1), ('a', 2), ('b', 3)) t(k, v)").await?.collect().await?;
    assert_eq!(
        groups.iter().map(|batch| batch.num_rows()).sum::<usize>(),
        2
    );
    assert_eq!(
        windows.iter().map(|batch| batch.num_rows()).sum::<usize>(),
        3
    );
    println!(
        "{}",
        serde_json::json!({"observations": {
            "duplicate_reference_left_join_rows": 3,
            "unmatched_label_nulls": 1,
            "grouped_rows": 2,
            "window_rows": 3,
            "fixture": "two left keys; duplicate right key; three group/window input rows"
        }})
    );
    Ok(())
}
