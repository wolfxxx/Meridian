//! Intermediate representation exchanged between the Python front end and the engine.
//!
//! The IR is a flat list of expression nodes in which every child index is smaller than its
//! parent's index (the Python tracer emits children first and de-duplicates identical
//! sub-expressions). Variables point at a root node.

use serde::{Deserialize, Serialize};

use crate::error::{MeridianError, Result};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum UnaryOp {
    Neg,
    Abs,
    Exp,
    Ln,
    Floor,
    Sqrt,
}

impl UnaryOp {
    #[inline(always)]
    pub fn apply(self, x: f64) -> f64 {
        match self {
            UnaryOp::Neg => -x,
            UnaryOp::Abs => x.abs(),
            UnaryOp::Exp => x.exp(),
            UnaryOp::Ln => x.ln(),
            UnaryOp::Floor => x.floor(),
            UnaryOp::Sqrt => x.sqrt(),
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum BinaryOp {
    Add,
    Sub,
    Mul,
    Div,
    Pow,
    Min,
    Max,
    Lt,
    Le,
    Gt,
    Ge,
    Eq,
    Ne,
    And,
    Or,
}

#[inline(always)]
fn b2f(b: bool) -> f64 {
    if b {
        1.0
    } else {
        0.0
    }
}

impl BinaryOp {
    #[inline(always)]
    pub fn apply(self, a: f64, b: f64) -> f64 {
        match self {
            BinaryOp::Add => a + b,
            BinaryOp::Sub => a - b,
            BinaryOp::Mul => a * b,
            BinaryOp::Div => a / b,
            BinaryOp::Pow => a.powf(b),
            BinaryOp::Min => a.min(b),
            BinaryOp::Max => a.max(b),
            BinaryOp::Lt => b2f(a < b),
            BinaryOp::Le => b2f(a <= b),
            BinaryOp::Gt => b2f(a > b),
            BinaryOp::Ge => b2f(a >= b),
            BinaryOp::Eq => b2f(a == b),
            BinaryOp::Ne => b2f(a != b),
            BinaryOp::And => b2f(a != 0.0 && b != 0.0),
            BinaryOp::Or => b2f(a != 0.0 || b != 0.0),
        }
    }
}

/// One expression node.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "op", rename_all = "snake_case")]
pub enum Node {
    /// A literal constant.
    Const {
        value: f64,
    },
    /// A model-point column (constant over time, one value per policy).
    Input {
        name: String,
    },
    /// The projection time index `t` (0-based).
    Time,
    /// Another variable's value at time `t - lag`. Before the start of the projection the
    /// variable's `init` value is used.
    Var {
        name: String,
        #[serde(default)]
        lag: usize,
    },
    /// 1-D table lookup: `table[floor(index)]`, clamped to the table's bounds (NaN -> 0).
    Table {
        name: String,
        index: usize,
    },
    /// A scenario path value for the lane's scenario at time `t`.
    Scenario {
        name: String,
    },
    Unary {
        func: UnaryOp,
        a: usize,
    },
    Binary {
        func: BinaryOp,
        a: usize,
        b: usize,
    },
    /// `cond != 0 ? a : b`
    Select {
        cond: usize,
        a: usize,
        b: usize,
    },
    /// Sum of the inner expression over all policies of the lane's scenario at time `t`
    /// (broadcast back to every lane of that scenario). Introduces C2 coupling.
    SumPolicies {
        a: usize,
    },
}

impl Node {
    /// Child node indices.
    pub fn children(&self) -> Vec<usize> {
        match self {
            Node::Const { .. }
            | Node::Input { .. }
            | Node::Time
            | Node::Var { .. }
            | Node::Scenario { .. } => vec![],
            Node::Table { index, .. } => vec![*index],
            Node::Unary { a, .. } | Node::SumPolicies { a } => vec![*a],
            Node::Binary { a, b, .. } => vec![*a, *b],
            Node::Select { cond, a, b } => vec![*cond, *a, *b],
        }
    }
}

/// A named model variable.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VarDef {
    pub name: String,
    pub expr: usize,
    /// Value used for references before the start of the projection (`t - lag < 0`).
    #[serde(default)]
    pub init: f64,
}

/// Which variables to report.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct Outputs {
    /// Summed over the policies of each scenario, for every time step.
    #[serde(default)]
    pub totals: Vec<String>,
    /// Summed over time, for every lane (e.g. a present value per policy and scenario).
    #[serde(default)]
    pub policy_sums: Vec<String>,
}

/// A complete model.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelIr {
    pub name: String,
    pub n_steps: usize,
    pub nodes: Vec<Node>,
    pub variables: Vec<VarDef>,
    #[serde(default)]
    pub outputs: Outputs,
}

impl ModelIr {
    pub fn from_json(s: &str) -> Result<Self> {
        serde_json::from_str(s).map_err(|e| MeridianError::InvalidIr(e.to_string()))
    }

    pub fn to_json(&self) -> String {
        serde_json::to_string(self).expect("IR is always serialisable")
    }
}
