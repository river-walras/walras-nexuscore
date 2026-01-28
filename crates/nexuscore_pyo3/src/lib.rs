use pyo3::prelude::*;

use nautilus_cryptography::python::signing::{
    py_ed25519_signature,
    py_hmac_signature,
    py_rsa_signature,
};

#[pymodule]
fn _nexuscore_pyo3(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(py_hmac_signature, m)?)?;
    m.add_function(wrap_pyfunction!(py_rsa_signature, m)?)?;
    m.add_function(wrap_pyfunction!(py_ed25519_signature, m)?)?;
    Ok(())
}
