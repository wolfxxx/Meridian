//! Python bindings: `meridian._engine`.
//!
//! Data crosses the boundary as float64 NumPy arrays. The heavy work runs with the GIL
//! released, so Python threads are not blocked during a projection.

use std::collections::HashMap;

use meridian_core::{
    compile, Inputs, MeridianError, ModelIr, RunOptions, Strategy, TableData, TableDim,
};
use numpy::{PyArray1, PyReadonlyArray1, PyReadonlyArray2, PyUntypedArrayMethods};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyDict;

fn err(e: MeridianError) -> PyErr {
    PyValueError::new_err(e.to_string())
}

/// Compile a model and report its structure without running it.
///
/// Returns a dict with `order` (evaluation order within a time step), `classes`
/// (variable -> "C1"/"C2"), `ring` (history depth kept per variable) and the input,
/// table and scenario names the model needs.
#[pyfunction]
fn inspect<'py>(py: Python<'py>, ir_json: &str) -> PyResult<Bound<'py, PyDict>> {
    let model = compile(ModelIr::from_json(ir_json).map_err(err)?).map_err(err)?;
    let out = PyDict::new(py);
    out.set_item("order", model.order_names())?;
    let classes = PyDict::new(py);
    let ring = PyDict::new(py);
    for (i, name) in model.var_names.iter().enumerate() {
        classes.set_item(name, model.classes[i].as_str())?;
        ring.set_item(name, model.ring[i])?;
    }
    out.set_item("classes", classes)?;
    out.set_item("ring", ring)?;
    let uniform: Vec<String> = model
        .var_names
        .iter()
        .zip(&model.var_uniform)
        .filter(|(_, u)| **u)
        .map(|(n, _)| n.clone())
        .collect();
    out.set_item("uniform", uniform)?;
    // Lockstep barrier segments: variables evaluated in one parallel pass per time step.
    out.set_item("segments", model.segment_names())?;
    out.set_item("inputs", model.input_names.clone())?;
    out.set_item("tables", model.table_names.clone())?;
    out.set_item("scenarios", model.scenario_names.clone())?;
    Ok(out)
}

/// Run a model.
///
/// * `model_points`: name -> 1-D float64 array of length `n_policies`
/// * `tables`: name -> 1-D float64 array
/// * `scenarios`: name -> 2-D float64 array of shape `(n_scenarios, n_steps)`
///
/// Returns a dict with flat float64 arrays: `totals` (`n_scenarios * n_steps`, row-major),
/// `policy_sums` (`n_scenarios * n_policies`), `history` (`n_steps * lanes`, only when
/// `keep_history`), plus `order` and `strategy` (`"per_chunk"` or `"lockstep"`).
/// `strategy="auto"` runs C1 models per chunk and C2 models in lockstep; `"lockstep"` forces
/// lockstep. Results are bit-identical either way.
#[pyfunction]
#[pyo3(signature = (ir_json, model_points, tables, scenarios, n_policies, n_scenarios=1, keep_history=false, chunk_size=2048, strategy="auto", table_dims=None))]
#[allow(clippy::too_many_arguments)]
fn run<'py>(
    py: Python<'py>,
    ir_json: &str,
    model_points: HashMap<String, PyReadonlyArray1<'py, f64>>,
    tables: HashMap<String, PyReadonlyArray1<'py, f64>>,
    scenarios: HashMap<String, PyReadonlyArray2<'py, f64>>,
    n_policies: usize,
    n_scenarios: usize,
    keep_history: bool,
    chunk_size: usize,
    strategy: &str,
    table_dims: Option<HashMap<String, Vec<(f64, usize, Vec<f64>)>>>,
) -> PyResult<Bound<'py, PyDict>> {
    let strategy = match strategy {
        "auto" => Strategy::Auto,
        "lockstep" => Strategy::Lockstep,
        other => {
            return Err(PyValueError::new_err(format!(
                "strategy must be 'auto' or 'lockstep', got '{other}'"
            )))
        }
    };
    let model = compile(ModelIr::from_json(ir_json).map_err(err)?).map_err(err)?;

    let model_points = model_points
        .into_iter()
        .map(|(k, v)| (k, v.as_array().to_vec()))
        .collect();
    // Tables arrive as flat row-major values plus, optionally, their dimensions: one
    // `(start, len, category_codes)` per dimension (empty codes = integer range).
    let table_dims = table_dims.unwrap_or_default();
    let mut table_data = HashMap::new();
    for (k, v) in tables {
        let values = v.as_array().to_vec();
        let td = match table_dims.get(&k) {
            None => TableData::vector(values),
            Some(dims) => {
                let dims = dims
                    .iter()
                    .map(|(start, len, codes)| {
                        if codes.is_empty() {
                            TableDim::Range {
                                start: *start,
                                len: *len,
                            }
                        } else {
                            TableDim::Categories(codes.clone())
                        }
                    })
                    .collect();
                TableData::new(values, dims)
                    .map_err(|e| PyValueError::new_err(format!("table `{k}`: {e}")))?
            }
        };
        table_data.insert(k, td);
    }
    let tables = table_data;
    let mut scen = HashMap::new();
    for (k, v) in scenarios {
        let shape = v.shape();
        if shape[0] != n_scenarios || shape[1] != model.n_steps {
            return Err(PyValueError::new_err(format!(
                "scenario `{k}` has shape ({}, {}), expected (n_scenarios, n_steps) = ({}, {})",
                shape[0], shape[1], n_scenarios, model.n_steps
            )));
        }
        // Logical (row-major) iteration order, whatever the array's memory layout.
        scen.insert(k, v.as_array().iter().copied().collect::<Vec<f64>>());
    }
    let inputs = Inputs {
        n_policies,
        n_scenarios,
        model_points,
        tables,
        scenarios: scen,
    };
    let opts = RunOptions {
        keep_history,
        chunk_size,
        strategy,
    };

    let res = py
        .allow_threads(|| model.run(&inputs, &opts))
        .map_err(err)?;

    let out = PyDict::new(py);
    let section = |pairs: Vec<(String, Vec<f64>)>| -> PyResult<Bound<'py, PyDict>> {
        let d = PyDict::new(py);
        for (name, values) in pairs {
            d.set_item(name, PyArray1::from_vec(py, values))?;
        }
        Ok(d)
    };
    out.set_item("totals", section(res.totals)?)?;
    out.set_item("policy_sums", section(res.policy_sums)?)?;
    out.set_item("history", section(res.history)?)?;
    out.set_item("order", model.order_names())?;
    out.set_item("strategy", res.strategy)?;
    Ok(out)
}

#[pymodule]
fn _engine(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(run, m)?)?;
    m.add_function(wrap_pyfunction!(inspect, m)?)?;
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    Ok(())
}
