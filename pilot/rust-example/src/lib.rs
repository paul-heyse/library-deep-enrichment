//! Minimal real Rust/Python C Stream boundary used by the semantic pilot.

use pyo3::{prelude::*, types::PyCapsule};
use pyo3_arrow::PyRecordBatchReader;

#[pyfunction]
fn round_trip<'py>(
    py: Python<'py>,
    capsule: &Bound<'py, PyCapsule>,
) -> PyResult<Bound<'py, PyAny>> {
    PyRecordBatchReader::from_arrow_pycapsule(capsule)?.into_pyarrow(py)
}

#[pymodule]
fn lde_interop(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(round_trip, module)?)
}
