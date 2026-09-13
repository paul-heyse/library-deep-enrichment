use pyo3::prelude::*;
use pyo3_arrow::{PyDataType, PyField};
#[pymodule]
fn foundational_arrow_binding(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_class::<PyDataType>()?;
    module.add_class::<PyField>()?;
    Ok(())
}
