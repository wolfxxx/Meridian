//! Validation, name resolution, dependency ordering and dependency-class analysis.

use std::collections::{BTreeSet, HashMap};

use crate::error::{MeridianError, Result};
use crate::ir::{BinaryOp, ModelIr, Node, UnaryOp};

/// Dependency class of a variable (spec section 19.4).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum VarClass {
    /// Depends only on its own policy lane.
    C1,
    /// Depends, directly or through other variables, on a cross-policy aggregate.
    C2,
}

impl VarClass {
    pub fn as_str(self) -> &'static str {
        match self {
            VarClass::C1 => "C1",
            VarClass::C2 => "C2",
        }
    }
}

/// Node with names resolved to slot indices.
#[derive(Debug, Clone)]
pub(crate) enum RNode {
    Const(f64),
    Input(usize),
    Time,
    Var { var: usize, lag: usize },
    Table { table: usize, index: usize },
    Scenario(usize),
    Unary(UnaryOp, usize),
    Binary(BinaryOp, usize, usize),
    Select(usize, usize, usize),
    SumPolicies(usize),
}

/// A group of consecutive variables (in evaluation order) that can be evaluated in one
/// parallel pass within a time step: every chunk of lanes evaluates all of them back to back.
/// The policy aggregates in `aggs` are computed (across all lanes) before the pass starts.
/// The boundary between two segments is the only place a C2 model must synchronise.
#[derive(Debug, Clone, Default)]
pub struct Segment {
    /// `SumPolicies` nodes to reduce before the pass.
    pub aggs: Vec<usize>,
    /// Variables evaluated in the pass, in dependency order.
    pub vars: Vec<usize>,
}

/// A validated model ready to run.
#[derive(Debug, Clone)]
pub struct CompiledModel {
    pub name: String,
    pub n_steps: usize,
    pub(crate) nodes: Vec<RNode>,
    pub var_names: Vec<String>,
    pub(crate) var_expr: Vec<usize>,
    pub(crate) var_init: Vec<f64>,
    /// Evaluation order of variables within a time step.
    pub order: Vec<usize>,
    /// Ring-buffer depth per variable (max lag referenced + 1).
    pub ring: Vec<usize>,
    pub classes: Vec<VarClass>,
    /// Nodes whose value is identical for every lane at a given time step (depend only on
    /// `t`, constants, tables indexed by such values, and lane-uniform variables). They are
    /// computed once per chunk and broadcast.
    pub(crate) uniform: Vec<bool>,
    /// Variables whose value is lane-uniform.
    pub var_uniform: Vec<bool>,
    pub input_names: Vec<String>,
    pub table_names: Vec<String>,
    pub scenario_names: Vec<String>,
    pub(crate) totals: Vec<usize>,
    pub(crate) policy_sums: Vec<usize>,
    /// Barrier segments for lockstep execution (one segment for a C1 model).
    pub segments: Vec<Segment>,
}

impl CompiledModel {
    /// Variable names per lockstep segment (for inspection and diagnostics).
    pub fn segment_names(&self) -> Vec<Vec<String>> {
        self.segments
            .iter()
            .map(|s| s.vars.iter().map(|&v| self.var_names[v].clone()).collect())
            .collect()
    }

    pub fn order_names(&self) -> Vec<String> {
        self.order
            .iter()
            .map(|&v| self.var_names[v].clone())
            .collect()
    }

    pub fn class_of(&self, name: &str) -> Option<VarClass> {
        self.var_names
            .iter()
            .position(|n| n == name)
            .map(|i| self.classes[i])
    }

    pub fn is_c2(&self) -> bool {
        self.classes.contains(&VarClass::C2)
    }
}

/// Per-variable facts gathered by walking its expression.
#[derive(Default)]
struct VarFacts {
    same_time_deps: BTreeSet<usize>,
    all_refs: BTreeSet<usize>,
    max_lag_of: HashMap<usize, usize>,
    agg_nodes: BTreeSet<usize>,
}

pub fn compile(ir: ModelIr) -> Result<CompiledModel> {
    if ir.n_steps == 0 {
        return Err(MeridianError::InvalidIr(
            "n_steps must be at least 1".into(),
        ));
    }
    if ir.variables.is_empty() {
        return Err(MeridianError::InvalidIr("model has no variables".into()));
    }

    // Variable names must be unique.
    let mut var_index: HashMap<String, usize> = HashMap::new();
    for (i, v) in ir.variables.iter().enumerate() {
        if var_index.insert(v.name.clone(), i).is_some() {
            return Err(MeridianError::InvalidIr(format!(
                "variable `{}` is defined more than once",
                v.name
            )));
        }
        if v.expr >= ir.nodes.len() {
            return Err(MeridianError::InvalidIr(format!(
                "variable `{}` points at node {} but there are only {} nodes",
                v.name,
                v.expr,
                ir.nodes.len()
            )));
        }
    }

    // Children must precede parents: guarantees an acyclic expression DAG.
    for (i, n) in ir.nodes.iter().enumerate() {
        for c in n.children() {
            if c >= i {
                return Err(MeridianError::InvalidIr(format!(
                    "node {i} references child {c}; children must precede parents"
                )));
            }
        }
    }

    // Resolve names to slots.
    let mut inputs: Vec<String> = Vec::new();
    let mut tables: Vec<String> = Vec::new();
    let mut scenarios: Vec<String> = Vec::new();
    fn slot(list: &mut Vec<String>, name: &str) -> usize {
        match list.iter().position(|n| n == name) {
            Some(i) => i,
            None => {
                list.push(name.to_string());
                list.len() - 1
            }
        }
    }

    // Which variable "owns" each node is not unique (nodes are shared), so unknown-variable
    // errors are reported against the first variable whose expression reaches the node.
    let owner = first_owner(&ir);

    let mut nodes = Vec::with_capacity(ir.nodes.len());
    for (i, n) in ir.nodes.iter().enumerate() {
        let r = match n {
            Node::Const { value } => RNode::Const(*value),
            Node::Input { name } => RNode::Input(slot(&mut inputs, name)),
            Node::Time => RNode::Time,
            Node::Var { name, lag } => {
                let var = *var_index
                    .get(name)
                    .ok_or_else(|| MeridianError::UnknownVariable {
                        name: name.clone(),
                        context: owner
                            .get(&i)
                            .map(|&v| ir.variables[v].name.clone())
                            .unwrap_or_else(|| "<unreachable node>".into()),
                    })?;
                RNode::Var { var, lag: *lag }
            }
            Node::Table { name, index } => RNode::Table {
                table: slot(&mut tables, name),
                index: *index,
            },
            Node::Scenario { name } => RNode::Scenario(slot(&mut scenarios, name)),
            Node::Unary { func, a } => RNode::Unary(*func, *a),
            Node::Binary { func, a, b } => RNode::Binary(*func, *a, *b),
            Node::Select { cond, a, b } => RNode::Select(*cond, *a, *b),
            Node::SumPolicies { a } => RNode::SumPolicies(*a),
        };
        nodes.push(r);
    }

    let nvar = ir.variables.len();
    let mut facts: Vec<VarFacts> = Vec::with_capacity(nvar);
    for v in &ir.variables {
        let mut f = VarFacts::default();
        walk(
            &nodes,
            v.expr,
            false,
            &mut f,
            &mut vec![false; nodes.len()],
            &v.name,
        )?;
        facts.push(f);
    }

    // Ring sizes.
    let mut ring = vec![1usize; nvar];
    for f in &facts {
        for (&var, &lag) in &f.max_lag_of {
            ring[var] = ring[var].max(lag + 1);
        }
    }

    // Topological order over same-time dependencies, with cycle reporting.
    let order = topo_order(&ir, &facts)?;

    // Dependency classes: C2 if the variable contains an aggregate or references (at any lag)
    // a C2 variable. Iterate to a fixed point.
    let mut c2: Vec<bool> = facts.iter().map(|f| !f.agg_nodes.is_empty()).collect();
    loop {
        let mut changed = false;
        for v in 0..nvar {
            if !c2[v] && facts[v].all_refs.iter().any(|&r| c2[r]) {
                c2[v] = true;
                changed = true;
            }
        }
        if !changed {
            break;
        }
    }
    let classes = c2
        .iter()
        .map(|&b| if b { VarClass::C2 } else { VarClass::C1 })
        .collect();

    let resolve_outputs = |names: &[String], kind: &str| -> Result<Vec<usize>> {
        names
            .iter()
            .map(|n| {
                var_index
                    .get(n)
                    .copied()
                    .ok_or_else(|| MeridianError::UnknownVariable {
                        name: n.clone(),
                        context: format!("outputs.{kind}"),
                    })
            })
            .collect()
    };
    let totals = resolve_outputs(&ir.outputs.totals, "totals")?;
    let policy_sums = resolve_outputs(&ir.outputs.policy_sums, "policy_sums")?;

    // Lane-uniform analysis: greatest fixed point (start optimistic, remove until stable).
    let var_expr: Vec<usize> = ir.variables.iter().map(|v| v.expr).collect();
    let mut var_uniform = vec![true; nvar];
    let mut uniform = vec![false; nodes.len()];
    loop {
        for i in 0..nodes.len() {
            uniform[i] = match &nodes[i] {
                RNode::Const(_) | RNode::Time => true,
                RNode::Input(_) | RNode::Scenario(_) | RNode::SumPolicies(_) => false,
                RNode::Var { var, .. } => var_uniform[*var],
                RNode::Table { index, .. } => uniform[*index],
                RNode::Unary(_, a) => uniform[*a],
                RNode::Binary(_, a, b) => uniform[*a] && uniform[*b],
                RNode::Select(c, a, b) => uniform[*c] && uniform[*a] && uniform[*b],
            };
        }
        let mut changed = false;
        for v in 0..nvar {
            let u = uniform[var_expr[v]];
            if var_uniform[v] && !u {
                var_uniform[v] = false;
                changed = true;
            }
        }
        if !changed {
            break;
        }
    }

    let segments = build_segments(&nodes, &order, &facts);

    Ok(CompiledModel {
        name: ir.name.clone(),
        n_steps: ir.n_steps,
        nodes,
        var_names: ir.variables.iter().map(|v| v.name.clone()).collect(),
        var_expr,
        var_init: ir.variables.iter().map(|v| v.init).collect(),
        order,
        ring,
        classes,
        uniform,
        var_uniform,
        input_names: inputs,
        table_names: tables,
        scenario_names: scenarios,
        totals,
        policy_sums,
        segments,
    })
}

/// Same-time (lag 0) variable references inside an expression.
fn lag0_refs(nodes: &[RNode], root: usize) -> BTreeSet<usize> {
    let mut out = BTreeSet::new();
    let mut stack = vec![root];
    let mut seen = vec![false; nodes.len()];
    while let Some(i) = stack.pop() {
        if std::mem::replace(&mut seen[i], true) {
            continue;
        }
        match &nodes[i] {
            RNode::Var { var, lag: 0 } => {
                out.insert(*var);
            }
            RNode::Var { .. }
            | RNode::Const(_)
            | RNode::Input(_)
            | RNode::Time
            | RNode::Scenario(_) => {}
            RNode::Table { index, .. } => stack.push(*index),
            RNode::Unary(_, a) | RNode::SumPolicies(a) => stack.push(*a),
            RNode::Binary(_, a, b) => stack.extend([*a, *b]),
            RNode::Select(c, a, b) => stack.extend([*c, *a, *b]),
        }
    }
    out
}

/// Split the evaluation order into barrier segments.
///
/// Walking the order, a variable that contains `sum_policies` needs its reductions computed
/// across all lanes. If every same-time variable those reductions read was finished in an
/// earlier segment, the reductions are hoisted to the start of the current segment (no new
/// barrier). Otherwise the current segment is closed and a new one starts with them.
fn build_segments(nodes: &[RNode], order: &[usize], facts: &[VarFacts]) -> Vec<Segment> {
    let mut segments = Vec::new();
    let mut cur = Segment::default();
    let mut completed: BTreeSet<usize> = BTreeSet::new();
    for &v in order {
        if !facts[v].agg_nodes.is_empty() {
            let mut needs: BTreeSet<usize> = BTreeSet::new();
            for &a in &facts[v].agg_nodes {
                needs.extend(lag0_refs(nodes, a));
            }
            if !needs.is_subset(&completed) {
                completed.extend(cur.vars.iter().copied());
                segments.push(std::mem::take(&mut cur));
            }
            for &a in &facts[v].agg_nodes {
                if !cur.aggs.contains(&a) {
                    cur.aggs.push(a);
                }
            }
        }
        cur.vars.push(v);
    }
    segments.push(cur);
    segments.retain(|s| !s.vars.is_empty() || !s.aggs.is_empty());
    segments
}

fn walk(
    nodes: &[RNode],
    i: usize,
    inside_agg: bool,
    f: &mut VarFacts,
    seen: &mut Vec<bool>,
    var_name: &str,
) -> Result<()> {
    // Nodes under an aggregate are walked even if seen outside one, so nesting is detected.
    if seen[i] && !inside_agg {
        return Ok(());
    }
    if !inside_agg {
        seen[i] = true;
    }
    match &nodes[i] {
        RNode::Var { var, lag } => {
            f.all_refs.insert(*var);
            let e = f.max_lag_of.entry(*var).or_insert(0);
            *e = (*e).max(*lag);
            if *lag == 0 {
                f.same_time_deps.insert(*var);
            }
        }
        RNode::SumPolicies(a) => {
            if inside_agg {
                return Err(MeridianError::InvalidIr(format!(
                    "nested sum_policies in the definition of `{var_name}` is not supported"
                )));
            }
            f.agg_nodes.insert(i);
            walk(nodes, *a, true, f, seen, var_name)?;
        }
        RNode::Table { index, .. } => walk(nodes, *index, inside_agg, f, seen, var_name)?,
        RNode::Unary(_, a) => walk(nodes, *a, inside_agg, f, seen, var_name)?,
        RNode::Binary(_, a, b) => {
            walk(nodes, *a, inside_agg, f, seen, var_name)?;
            walk(nodes, *b, inside_agg, f, seen, var_name)?;
        }
        RNode::Select(c, a, b) => {
            walk(nodes, *c, inside_agg, f, seen, var_name)?;
            walk(nodes, *a, inside_agg, f, seen, var_name)?;
            walk(nodes, *b, inside_agg, f, seen, var_name)?;
        }
        RNode::Const(_) | RNode::Input(_) | RNode::Time | RNode::Scenario(_) => {}
    }
    Ok(())
}

/// Depth-first topological sort in declaration order; reports the cycle path on failure.
fn topo_order(ir: &ModelIr, facts: &[VarFacts]) -> Result<Vec<usize>> {
    #[derive(Clone, Copy, PartialEq)]
    enum Mark {
        New,
        Active,
        Done,
    }
    let n = facts.len();
    let mut mark = vec![Mark::New; n];
    let mut order = Vec::with_capacity(n);
    let mut stack: Vec<usize> = Vec::new();

    fn visit(
        v: usize,
        facts: &[VarFacts],
        mark: &mut [Mark],
        order: &mut Vec<usize>,
        stack: &mut Vec<usize>,
        ir: &ModelIr,
    ) -> Result<()> {
        match mark[v] {
            Mark::Done => return Ok(()),
            Mark::Active => {
                let start = stack.iter().position(|&s| s == v).unwrap_or(0);
                let mut path: Vec<&str> = stack[start..]
                    .iter()
                    .map(|&s| ir.variables[s].name.as_str())
                    .collect();
                path.push(ir.variables[v].name.as_str());
                return Err(MeridianError::Cycle(format!(
                    "{} (break the loop with a lagged reference such as `.lag(1)`)",
                    path.join(" -> ")
                )));
            }
            Mark::New => {}
        }
        mark[v] = Mark::Active;
        stack.push(v);
        for &d in &facts[v].same_time_deps {
            visit(d, facts, mark, order, stack, ir)?;
        }
        stack.pop();
        mark[v] = Mark::Done;
        order.push(v);
        Ok(())
    }

    for v in 0..n {
        visit(v, facts, &mut mark, &mut order, &mut stack, ir)?;
    }
    Ok(order)
}

/// Map each node to the first variable (in declaration order) whose expression reaches it.
fn first_owner(ir: &ModelIr) -> HashMap<usize, usize> {
    let mut owner = HashMap::new();
    for (vi, v) in ir.variables.iter().enumerate() {
        let mut stack = vec![v.expr];
        while let Some(i) = stack.pop() {
            if owner.contains_key(&i) {
                continue;
            }
            owner.insert(i, vi);
            stack.extend(ir.nodes[i].children());
        }
    }
    owner
}
