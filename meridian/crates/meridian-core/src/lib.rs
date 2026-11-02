//! Meridian core engine (prototype).
//!
//! A model is a set of named variables, each defined by an expression that may reference
//! model-point inputs, tables, scenario paths, the projection time `t`, other variables at
//! the same time step (lag 0) or earlier time steps (lag >= 1), and policy aggregates
//! (`sum_policies`).
//!
//! Execution is vectorised over *lanes* = scenarios x policies (scenario-major). The compiler
//! classifies the model by dependency class (spec section 19.4) and the engine picks a
//! strategy:
//!
//! * **C1** (policy-independent): every variable only depends on its own lane, so each chunk
//!   of lanes runs through all time steps independently (no global synchronisation).
//! * **C2** (aggregate feedback): some variable depends on a `sum_policies` reduction at the
//!   current time step, so the engine steps all lanes in lockstep. Within a step, variables
//!   are grouped into segments that only break where a reduction needs every lane finished;
//!   each segment is one parallel pass in which every chunk evaluates all its variables.
//!
//! Reductions use fixed-block pairwise summation, so results are bit-for-bit identical
//! regardless of strategy, chunk size or thread count (spec NF-12 / NF-13).

pub mod compile;
pub mod engine;
mod error;
pub mod ir;
pub mod sum;
pub mod table;

pub use compile::{compile, CompiledModel, Segment, VarClass};
pub use engine::{Inputs, Results, RunOptions, Strategy};
pub use error::{MeridianError, Result};
pub use ir::{BinaryOp, ModelIr, Node, Outputs, UnaryOp, VarDef};
pub use table::{TableData, TableDim};
