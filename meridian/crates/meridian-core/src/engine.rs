//! Vectorised interpreter with two execution strategies.
//!
//! Lanes are laid out scenario-major: `lane = scenario * n_policies + policy`.
//!
//! * **Per-chunk** (used for C1 models, which have no cross-policy dependency): the lanes are
//!   split into work units of whole reduction blocks, and each unit runs through *all* time
//!   steps independently on one thread, with its own small ring buffers. There is no global
//!   synchronisation, and a unit's working set stays in cache.
//! * **Scenario-partitioned lockstep** (C2 models with several scenarios): `sum_policies`
//!   totals are per scenario, so scenarios are independent. Each group of scenarios runs the
//!   lockstep strategy below through all time steps on its own, keeping its state in cache.
//! * **Lockstep** (C2 models): all lanes advance one time step at a time. Within
//!   a step, variables are grouped into *segments* (see `compile::build_segments`) that break
//!   only where a `sum_policies` reduction needs every lane finished. Each segment is one
//!   parallel pass in which every chunk evaluates all the segment's variables back to back.
//!
//! Per-scenario totals are defined over fixed reduction blocks (`sum::blocked_sum`), so both
//! strategies, any chunk size and any thread count give bit-identical results.
//!
//! This is deliberately an interpreter, not a JIT: every node is applied to a whole chunk of
//! lanes at once, so dispatch overhead is amortised over thousands of policies x scenarios.
//! Fusion / code generation is a later optimisation (spec section 25.1).

use std::collections::HashMap;

use rayon::prelude::*;

use crate::compile::{CompiledModel, RNode};
use crate::error::{MeridianError, Result};
use crate::ir::{BinaryOp, UnaryOp};
use crate::sum::{blocked_sum, pairwise_sum, REDUCTION_BLOCK};
use crate::table::TableData;

/// Run inputs. All arrays are float64.
#[derive(Debug, Clone, Default)]
pub struct Inputs {
    pub n_policies: usize,
    /// Number of economic scenarios (1 for a deterministic run).
    pub n_scenarios: usize,
    /// Model-point columns, each of length `n_policies`.
    pub model_points: HashMap<String, Vec<f64>>,
    /// Assumption tables (1-D vectors or multi-dimensional range/category tables).
    pub tables: HashMap<String, TableData>,
    /// Scenario paths, each of length `n_scenarios * n_steps` (row-major `[scenario][t]`).
    pub scenarios: HashMap<String, Vec<f64>>,
}

/// How lanes are scheduled. Results never depend on the choice.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Strategy {
    /// Per-chunk for C1 models; scenario-partitioned lockstep for C2 models with several
    /// scenarios; global lockstep otherwise.
    Auto,
    /// Force global lockstep over all lanes (always valid). Useful for testing and benchmarks.
    Lockstep,
}

#[derive(Debug, Clone)]
pub struct RunOptions {
    /// Keep every variable's full history (for single-policy traces; memory heavy).
    pub keep_history: bool,
    /// Lanes per work unit (rounded to whole reduction blocks in per-chunk mode).
    /// Results do not depend on this value.
    pub chunk_size: usize,
    pub strategy: Strategy,
}

impl Default for RunOptions {
    fn default() -> Self {
        RunOptions {
            keep_history: false,
            chunk_size: 2048,
            strategy: Strategy::Auto,
        }
    }
}

/// Run outputs, in declaration order.
#[derive(Debug, Clone)]
pub struct Results {
    pub n_steps: usize,
    pub n_policies: usize,
    pub n_scenarios: usize,
    /// Which strategy actually ran: `"per_chunk"`, `"lockstep_by_scenario"` or `"lockstep"`.
    pub strategy: &'static str,
    /// `(name, values)` with values of length `n_scenarios * n_steps`, row-major `[s][t]`.
    pub totals: Vec<(String, Vec<f64>)>,
    /// `(name, values)` with values of length `n_scenarios * n_policies` (one per lane).
    pub policy_sums: Vec<(String, Vec<f64>)>,
    /// `(name, values)` with values of length `n_steps * lanes`, row-major `[t][lane]`.
    pub history: Vec<(String, Vec<f64>)>,
}

struct Data<'a> {
    mp: Vec<&'a [f64]>,
    tables: Vec<&'a TableData>,
    scen: Vec<&'a [f64]>,
    n_pol: usize,
    n_scen: usize,
    n_steps: usize,
}

struct StepCtx<'a> {
    t: usize,
    /// Ring buffers per variable; each buffer covers lanes `base .. base + len`.
    state: &'a [Vec<Vec<f64>>],
    base: usize,
    data: &'a Data<'a>,
    /// Per-scenario values of the `SumPolicies` nodes needed by the variable being evaluated.
    agg: &'a HashMap<usize, Vec<f64>>,
    /// Current-step values of variables already evaluated earlier in the same lockstep
    /// segment for this chunk (their global buffers are being filled during the pass).
    /// Each slice covers lanes `overlay_base .. overlay_base + len`.
    overlay: &'a [(usize, &'a [f64])],
    overlay_base: usize,
}

/// Output of one per-chunk work unit: lanes `lo .. lo + len` of scenario `s`.
struct UnitOut {
    lo: usize,
    len: usize,
    /// Per total output: `[t][block]` block sums for this unit's blocks.
    block_sums: Vec<Vec<f64>>,
    n_blocks: usize,
    /// Per policy-sum output: one value per lane of the unit.
    psums: Vec<Vec<f64>>,
    /// Per variable (only with keep_history): `[t][lane]` for the unit's lanes.
    history: Vec<Vec<f64>>,
}

impl CompiledModel {
    pub fn run(&self, inputs: &Inputs, opts: &RunOptions) -> Result<Results> {
        if inputs.n_policies == 0 {
            return Err(MeridianError::Shape("n_policies must be at least 1".into()));
        }
        if inputs.n_scenarios == 0 {
            return Err(MeridianError::Shape(
                "n_scenarios must be at least 1".into(),
            ));
        }
        let data = self.bind(inputs)?;
        Ok(match (opts.strategy, self.is_c2(), data.n_scen > 1) {
            (Strategy::Auto, false, _) => self.run_per_chunk(&data, opts),
            (Strategy::Auto, true, true) => self.run_by_scenario(&data, opts),
            _ => self.run_lockstep(&data, opts, true),
        })
    }

    // ---- per-chunk strategy (C1) ---------------------------------------------------------

    fn run_per_chunk(&self, data: &Data, opts: &RunOptions) -> Results {
        let (n_pol, n_scen, n_steps) = (data.n_pol, data.n_scen, data.n_steps);
        let blocks_per_scen = n_pol.div_ceil(REDUCTION_BLOCK);
        // Blocks per unit: honour chunk_size, but keep enough units for load balancing.
        let total_blocks = blocks_per_scen * n_scen;
        let min_units = 4 * rayon::current_num_threads();
        let by_chunk = (opts.chunk_size / REDUCTION_BLOCK).max(1);
        let by_balance = (total_blocks / min_units).max(1);
        let g = by_chunk.min(by_balance);

        // Units never cross a scenario boundary, so block sums map to one scenario.
        let units: Vec<(usize, usize, usize)> = (0..n_scen)
            .flat_map(|s| {
                (0..blocks_per_scen)
                    .step_by(g)
                    .map(move |b0| (s, b0, (b0 + g).min(blocks_per_scen)))
            })
            .collect();

        let outs: Vec<UnitOut> = units
            .par_iter()
            .map(|&(s, b0, b1)| {
                let lo = s * n_pol + b0 * REDUCTION_BLOCK;
                let hi = s * n_pol + (b1 * REDUCTION_BLOCK).min(n_pol);
                self.run_unit(data, lo, hi - lo, opts.keep_history)
            })
            .collect();

        // Assemble totals: for each scenario and time, pairwise over the block sums in block
        // order — exactly blocked_sum over the scenario's lanes.
        let mut totals = vec![vec![0.0; n_scen * n_steps]; self.totals.len()];
        let units_per_scen = blocks_per_scen.div_ceil(g);
        let mut blocks = vec![0.0; blocks_per_scen];
        for (k, tot) in totals.iter_mut().enumerate() {
            for s in 0..n_scen {
                let scen_units = &outs[s * units_per_scen..(s + 1) * units_per_scen];
                for t in 0..n_steps {
                    let mut j = 0;
                    for u in scen_units {
                        blocks[j..j + u.n_blocks].copy_from_slice(
                            &u.block_sums[k][t * u.n_blocks..(t + 1) * u.n_blocks],
                        );
                        j += u.n_blocks;
                    }
                    tot[s * n_steps + t] = pairwise_sum(&blocks);
                }
            }
        }

        let lanes = n_pol * n_scen;
        let mut psums = vec![vec![0.0; lanes]; self.policy_sums.len()];
        for u in &outs {
            for (k, ps) in psums.iter_mut().enumerate() {
                ps[u.lo..u.lo + u.len].copy_from_slice(&u.psums[k]);
            }
        }

        let nvar = self.var_names.len();
        let history = if opts.keep_history {
            let mut h = vec![vec![0.0; n_steps * lanes]; nvar];
            for u in &outs {
                for (v, hv) in h.iter_mut().enumerate() {
                    for t in 0..n_steps {
                        hv[t * lanes + u.lo..t * lanes + u.lo + u.len]
                            .copy_from_slice(&u.history[v][t * u.len..(t + 1) * u.len]);
                    }
                }
            }
            h
        } else {
            Vec::new()
        };

        self.package(data, "per_chunk", totals, psums, history, opts.keep_history)
    }

    /// Run lanes `lo .. lo + len` (whole reduction blocks of one scenario) through all steps.
    fn run_unit(&self, data: &Data, lo: usize, len: usize, keep_history: bool) -> UnitOut {
        let n_steps = data.n_steps;
        let nvar = self.var_names.len();
        let n_blocks = len.div_ceil(REDUCTION_BLOCK);
        let mut state: Vec<Vec<Vec<f64>>> = (0..nvar)
            .map(|v| vec![vec![0.0; len]; self.ring[v]])
            .collect();
        let mut block_sums = vec![vec![0.0; n_steps * n_blocks]; self.totals.len()];
        let mut psums = vec![vec![0.0; len]; self.policy_sums.len()];
        let mut history: Vec<Vec<f64>> = if keep_history {
            (0..nvar)
                .map(|_| Vec::with_capacity(n_steps * len))
                .collect()
        } else {
            Vec::new()
        };
        let empty = HashMap::new();

        for t in 0..n_steps {
            for &v in &self.order {
                let slot = t % self.ring[v];
                let mut out = std::mem::take(&mut state[v][slot]);
                {
                    let ctx = StepCtx {
                        t,
                        state: &state,
                        base: lo,
                        data,
                        agg: &empty,
                        overlay: &[],
                        overlay_base: 0,
                    };
                    self.eval_chunk(self.var_expr[v], &ctx, lo, &mut out);
                }
                state[v][slot] = out;
            }
            for (k, &v) in self.totals.iter().enumerate() {
                let cur = &state[v][t % self.ring[v]];
                for (j, block) in cur.chunks(REDUCTION_BLOCK).enumerate() {
                    block_sums[k][t * n_blocks + j] = pairwise_sum(block);
                }
            }
            for (k, &v) in self.policy_sums.iter().enumerate() {
                let cur = &state[v][t % self.ring[v]];
                for (a, b) in psums[k].iter_mut().zip(cur) {
                    *a += *b;
                }
            }
            if keep_history {
                for (v, h) in history.iter_mut().enumerate() {
                    h.extend_from_slice(&state[v][t % self.ring[v]]);
                }
            }
        }
        UnitOut {
            lo,
            len,
            block_sums,
            n_blocks,
            psums,
            history,
        }
    }

    // ---- scenario-partitioned lockstep (C2 with several scenarios) ------------------------

    fn run_by_scenario(&self, data: &Data, opts: &RunOptions) -> Results {
        let (n_pol, n_scen, n_steps) = (data.n_pol, data.n_scen, data.n_steps);
        let threads = rayon::current_num_threads();
        // Small groups keep each group's state cache-resident; enough groups keep threads busy.
        let per_group = (n_scen / (4 * threads)).max(1);
        let groups: Vec<(usize, usize)> = (0..n_scen)
            .step_by(per_group)
            .map(|s0| (s0, (s0 + per_group).min(n_scen)))
            .collect();
        // With too few groups to occupy every thread, also parallelise inside each group.
        let inner_par = groups.len() < 2 * threads;

        let parts: Vec<Results> = groups
            .par_iter()
            .map(|&(s0, s1)| {
                let view = Data {
                    mp: data.mp.clone(),
                    tables: data.tables.clone(),
                    scen: data
                        .scen
                        .iter()
                        .map(|sc| &sc[s0 * n_steps..s1 * n_steps])
                        .collect(),
                    n_pol,
                    n_scen: s1 - s0,
                    n_steps,
                };
                self.run_lockstep(&view, opts, inner_par)
            })
            .collect();

        // Stitch: totals are [s][t] and policy sums are scenario-major, so groups concatenate;
        // history is [t][lane] and is interleaved per time step.
        let totals: Vec<Vec<f64>> = (0..self.totals.len())
            .map(|k| {
                parts
                    .iter()
                    .flat_map(|p| p.totals[k].1.iter().copied())
                    .collect()
            })
            .collect();
        let psums: Vec<Vec<f64>> = (0..self.policy_sums.len())
            .map(|k| {
                parts
                    .iter()
                    .flat_map(|p| p.policy_sums[k].1.iter().copied())
                    .collect()
            })
            .collect();
        let lanes = n_pol * n_scen;
        let history: Vec<Vec<f64>> = if opts.keep_history {
            (0..self.var_names.len())
                .map(|v| {
                    let mut h = vec![0.0; n_steps * lanes];
                    for (p, &(s0, s1)) in parts.iter().zip(&groups) {
                        let gl = (s1 - s0) * n_pol;
                        let src = &p.history[v].1;
                        for t in 0..n_steps {
                            let dst = t * lanes + s0 * n_pol;
                            h[dst..dst + gl].copy_from_slice(&src[t * gl..(t + 1) * gl]);
                        }
                    }
                    h
                })
                .collect()
        } else {
            Vec::new()
        };
        self.package(
            data,
            "lockstep_by_scenario",
            totals,
            psums,
            history,
            opts.keep_history,
        )
    }

    // ---- lockstep strategy (C2, or forced) -------------------------------------------------

    /// Lockstep over all lanes of `data`. `par` parallelises within the run (set to false when
    /// the caller already runs many lockstep groups in parallel).
    fn run_lockstep(&self, data: &Data, opts: &RunOptions, par: bool) -> Results {
        let (n_pol, n_scen, n_steps) = (data.n_pol, data.n_scen, data.n_steps);
        let lanes = n_pol * n_scen;
        let chunk = opts.chunk_size.max(1);
        let nvar = self.var_names.len();
        let mut state: Vec<Vec<Vec<f64>>> = (0..nvar)
            .map(|v| vec![vec![0.0; lanes]; self.ring[v]])
            .collect();
        let mut totals: Vec<Vec<f64>> = vec![vec![0.0; n_scen * n_steps]; self.totals.len()];
        let mut psums: Vec<Vec<f64>> = vec![vec![0.0; lanes]; self.policy_sums.len()];
        let mut history: Vec<Vec<f64>> = if opts.keep_history {
            (0..nvar)
                .map(|_| Vec::with_capacity(n_steps * lanes))
                .collect()
        } else {
            Vec::new()
        };

        let empty: HashMap<usize, Vec<f64>> = HashMap::new();
        let n_chunks = lanes.div_ceil(chunk);
        for t in 0..n_steps {
            for seg in &self.segments {
                // 1. Cross-policy reductions for this segment (the C2 barrier). Their inputs
                //    were all completed by earlier segments.
                let mut agg: HashMap<usize, Vec<f64>> = HashMap::new();
                for &node in &seg.aggs {
                    let inner = match self.nodes[node] {
                        RNode::SumPolicies(a) => a,
                        _ => unreachable!("segment aggs only hold SumPolicies nodes"),
                    };
                    let ctx = StepCtx {
                        t,
                        state: &state,
                        base: 0,
                        data,
                        agg: &empty,
                        overlay: &[],
                        overlay_base: 0,
                    };
                    agg.insert(node, self.reduce_per_scenario(inner, &ctx, par));
                }

                // 2. One parallel pass: every chunk evaluates all the segment's variables back
                //    to back, reading this step's earlier segment variables from its own slices.
                let mut taken: Vec<Vec<f64>> = seg
                    .vars
                    .iter()
                    .map(|&v| std::mem::take(&mut state[v][t % self.ring[v]]))
                    .collect();
                {
                    let mut per_chunk: Vec<Vec<&mut [f64]>> = (0..n_chunks)
                        .map(|_| Vec::with_capacity(seg.vars.len()))
                        .collect();
                    for buf in taken.iter_mut() {
                        for (i, sl) in buf.chunks_mut(chunk).enumerate() {
                            per_chunk[i].push(sl);
                        }
                    }
                    let state_ref = &state;
                    let agg_ref = &agg;
                    let work = |(i, slices): (usize, Vec<&mut [f64]>)| {
                        let lo = i * chunk;
                        let mut overlay: Vec<(usize, &[f64])> = Vec::with_capacity(slices.len());
                        for (j, sl) in slices.into_iter().enumerate() {
                            {
                                let ctx = StepCtx {
                                    t,
                                    state: state_ref,
                                    base: 0,
                                    data,
                                    agg: agg_ref,
                                    overlay: &overlay,
                                    overlay_base: lo,
                                };
                                self.eval_chunk(self.var_expr[seg.vars[j]], &ctx, lo, &mut *sl);
                            }
                            // Finished: downgrade to a shared slice for later variables.
                            overlay.push((seg.vars[j], sl));
                        }
                    };
                    if par {
                        per_chunk.into_par_iter().enumerate().for_each(work);
                    } else {
                        per_chunk.into_iter().enumerate().for_each(work);
                    }
                }
                for (q, &v) in seg.vars.iter().enumerate() {
                    state[v][t % self.ring[v]] = std::mem::take(&mut taken[q]);
                }
            }

            // 3. Outputs for time t.
            for (k, &v) in self.totals.iter().enumerate() {
                let cur = &state[v][t % self.ring[v]];
                for s in 0..n_scen {
                    totals[k][s * n_steps + t] = blocked_sum(&cur[s * n_pol..(s + 1) * n_pol]);
                }
            }
            for (k, &v) in self.policy_sums.iter().enumerate() {
                let cur = &state[v][t % self.ring[v]];
                let add = |(acc, x): (&mut [f64], &[f64])| {
                    for (a, b) in acc.iter_mut().zip(x) {
                        *a += *b;
                    }
                };
                if par {
                    psums[k]
                        .par_chunks_mut(chunk)
                        .zip(cur.par_chunks(chunk))
                        .for_each(add);
                } else {
                    psums[k]
                        .chunks_mut(chunk)
                        .zip(cur.chunks(chunk))
                        .for_each(add);
                }
            }
            if opts.keep_history {
                for (v, h) in history.iter_mut().enumerate() {
                    h.extend_from_slice(&state[v][t % self.ring[v]]);
                }
            }
        }

        self.package(data, "lockstep", totals, psums, history, opts.keep_history)
    }

    /// Per-scenario `blocked_sum` of expression `inner` over all policies, computed block by
    /// block from scratch buffers (no full-width intermediate). Uses exactly the reduction tree
    /// of `sum::blocked_sum`, so results are bit-identical to reducing a materialised buffer.
    fn reduce_per_scenario(&self, inner: usize, ctx: &StepCtx, par: bool) -> Vec<f64> {
        let (n_pol, n_scen) = (ctx.data.n_pol, ctx.data.n_scen);
        let bps = n_pol.div_ceil(REDUCTION_BLOCK);
        let block = |u: usize| {
            let (s, b) = (u / bps, u % bps);
            let start = b * REDUCTION_BLOCK;
            let len = REDUCTION_BLOCK.min(n_pol - start);
            let mut buf = take_buf(len);
            self.eval_chunk(inner, ctx, s * n_pol + start, &mut buf);
            let r = pairwise_sum(&buf);
            give_buf(buf);
            r
        };
        let block_sums: Vec<f64> = if par {
            (0..n_scen * bps).into_par_iter().map(block).collect()
        } else {
            (0..n_scen * bps).map(block).collect()
        };
        (0..n_scen)
            .map(|s| {
                if bps == 1 {
                    block_sums[s] // blocked_sum of a single block is its pairwise sum
                } else {
                    pairwise_sum(&block_sums[s * bps..(s + 1) * bps])
                }
            })
            .collect()
    }

    // ---- shared ---------------------------------------------------------------------------

    fn package(
        &self,
        data: &Data,
        strategy: &'static str,
        totals: Vec<Vec<f64>>,
        psums: Vec<Vec<f64>>,
        history: Vec<Vec<f64>>,
        keep_history: bool,
    ) -> Results {
        let name = |v: usize| self.var_names[v].clone();
        Results {
            n_steps: data.n_steps,
            n_policies: data.n_pol,
            n_scenarios: data.n_scen,
            strategy,
            totals: self.totals.iter().map(|&v| name(v)).zip(totals).collect(),
            policy_sums: self
                .policy_sums
                .iter()
                .map(|&v| name(v))
                .zip(psums)
                .collect(),
            history: if keep_history {
                (0..self.var_names.len()).map(name).zip(history).collect()
            } else {
                Vec::new()
            },
        }
    }

    fn bind<'a>(&self, inputs: &'a Inputs) -> Result<Data<'a>> {
        let n_pol = inputs.n_policies;
        let n_scen = inputs.n_scenarios;
        let mut mp = Vec::new();
        for name in &self.input_names {
            let col = inputs.model_points.get(name).ok_or_else(|| {
                MeridianError::MissingInput(format!("model-point column `{name}`"))
            })?;
            if col.len() != n_pol {
                return Err(MeridianError::Shape(format!(
                    "model-point column `{name}` has {} values, expected n_policies = {n_pol}",
                    col.len()
                )));
            }
            mp.push(col.as_slice());
        }
        let mut tables = Vec::new();
        for name in &self.table_names {
            let tb = inputs
                .tables
                .get(name)
                .ok_or_else(|| MeridianError::MissingInput(format!("table `{name}`")))?;
            tables.push(tb);
        }
        // Every lookup must supply one key per table dimension.
        for node in &self.nodes {
            if let RNode::Table { table, indices } = node {
                let td = tables[*table];
                if td.ndim() != indices.len() {
                    return Err(MeridianError::Shape(format!(
                        "table `{}` has {} dimension(s) but is looked up with {} key(s)",
                        self.table_names[*table],
                        td.ndim(),
                        indices.len()
                    )));
                }
            }
        }
        let mut scen = Vec::new();
        for name in &self.scenario_names {
            let sc = inputs
                .scenarios
                .get(name)
                .ok_or_else(|| MeridianError::MissingInput(format!("scenario path `{name}`")))?;
            if sc.len() != n_scen * self.n_steps {
                return Err(MeridianError::Shape(format!(
                    "scenario path `{name}` has {} values, expected n_scenarios x n_steps = {} x {}",
                    sc.len(),
                    n_scen,
                    self.n_steps
                )));
            }
            scen.push(sc.as_slice());
        }
        Ok(Data {
            mp,
            tables,
            scen,
            n_pol,
            n_scen,
            n_steps: self.n_steps,
        })
    }

    /// Evaluate node `i` for global lanes `lo .. lo + out.len()` into `out`.
    fn eval_chunk(&self, i: usize, ctx: &StepCtx, lo: usize, out: &mut [f64]) {
        let n = out.len();
        let n_pol = ctx.data.n_pol;
        // Lane-uniform sub-expressions (e.g. discount factors, inflation indices): compute one
        // lane and broadcast. Same operations on the same operands, so results are identical.
        if n > 1 && self.uniform[i] {
            let mut one = [0.0f64; 1];
            self.eval_chunk(i, ctx, lo, &mut one);
            out.fill(one[0]);
            return;
        }
        match &self.nodes[i] {
            RNode::Const(c) => out.fill(*c),
            RNode::Time => out.fill(ctx.t as f64),
            RNode::Input(k) => {
                let col = ctx.data.mp[*k];
                let mut p = lo % n_pol;
                for o in out.iter_mut() {
                    *o = col[p];
                    p += 1;
                    if p == n_pol {
                        p = 0;
                    }
                }
            }
            RNode::Var { var, lag } => {
                if ctx.t < *lag {
                    out.fill(self.var_init[*var]);
                } else if let Some((_, src)) =
                    ctx.overlay.iter().find(|(v, _)| *lag == 0 && *v == *var)
                {
                    let off = lo - ctx.overlay_base;
                    out.copy_from_slice(&src[off..off + n]);
                } else {
                    let src = &ctx.state[*var][(ctx.t - lag) % self.ring[*var]];
                    let off = lo - ctx.base;
                    out.copy_from_slice(&src[off..off + n]);
                }
            }
            RNode::Table { table, indices } => {
                let td = ctx.data.tables[*table];
                // Accumulate the flat row-major offset per lane in `out` (NaN = unknown
                // category), then replace it with the looked-up value.
                out.fill(0.0);
                let mut key = take_buf(n);
                for (d, &k) in indices.iter().enumerate() {
                    self.eval_chunk(k, ctx, lo, &mut key);
                    let dim = &td.dims[d];
                    let stride = td.stride(d) as f64;
                    for (o, x) in out.iter_mut().zip(key.iter()) {
                        *o = match dim.position(*x) {
                            Some(p) => *o + p as f64 * stride,
                            None => f64::NAN,
                        };
                    }
                }
                give_buf(key);
                for o in out.iter_mut() {
                    *o = if o.is_nan() {
                        f64::NAN
                    } else {
                        td.values[*o as usize]
                    };
                }
            }
            RNode::Scenario(k) => {
                let sc = ctx.data.scen[*k];
                let n_steps = ctx.data.n_steps;
                broadcast_per_scenario(out, lo, n_pol, |s| sc[s * n_steps + ctx.t]);
            }
            RNode::Unary(op, a) => {
                self.eval_chunk(*a, ctx, lo, out);
                apply_unary(*op, out);
            }
            RNode::Binary(op, a, b) => {
                self.eval_chunk(*a, ctx, lo, out);
                let mut rhs = take_buf(n);
                self.eval_chunk(*b, ctx, lo, &mut rhs);
                apply_binary(*op, out, &rhs);
                give_buf(rhs);
            }
            RNode::Select(c, a, b) => {
                self.eval_chunk(*c, ctx, lo, out);
                let mut va = take_buf(n);
                let mut vb = take_buf(n);
                self.eval_chunk(*a, ctx, lo, &mut va);
                self.eval_chunk(*b, ctx, lo, &mut vb);
                for j in 0..n {
                    out[j] = if out[j] != 0.0 { va[j] } else { vb[j] };
                }
                give_buf(va);
                give_buf(vb);
            }
            RNode::SumPolicies(_) => {
                let vals = ctx
                    .agg
                    .get(&i)
                    .expect("aggregate must be precomputed before evaluating its variable");
                broadcast_per_scenario(out, lo, n_pol, |s| vals[s]);
            }
        }
    }
}

/// Fill `out` (lanes `lo..`) with a per-scenario value, without per-element division.
#[inline]
fn broadcast_per_scenario(out: &mut [f64], lo: usize, n_pol: usize, value: impl Fn(usize) -> f64) {
    let mut s = lo / n_pol;
    let mut p = lo % n_pol;
    let mut j = 0;
    while j < out.len() {
        let run = (n_pol - p).min(out.len() - j);
        out[j..j + run].fill(value(s));
        j += run;
        s += 1;
        p = 0;
    }
}

thread_local! {
    /// Per-thread pool of scratch buffers, so expression evaluation does not allocate per node.
    static POOL: std::cell::RefCell<Vec<Vec<f64>>> = const { std::cell::RefCell::new(Vec::new()) };
}

fn take_buf(n: usize) -> Vec<f64> {
    let mut v = POOL.with(|p| p.borrow_mut().pop()).unwrap_or_default();
    v.clear();
    v.resize(n, 0.0);
    v
}

fn give_buf(v: Vec<f64>) {
    POOL.with(|p| p.borrow_mut().push(v));
}

/// Element-wise unary op; the match is hoisted out of the loop so each arm vectorises.
fn apply_unary(op: UnaryOp, x: &mut [f64]) {
    match op {
        UnaryOp::Neg => x.iter_mut().for_each(|v| *v = -*v),
        UnaryOp::Abs => x.iter_mut().for_each(|v| *v = v.abs()),
        UnaryOp::Floor => x.iter_mut().for_each(|v| *v = v.floor()),
        UnaryOp::Sqrt => x.iter_mut().for_each(|v| *v = v.sqrt()),
        UnaryOp::Exp => x.iter_mut().for_each(|v| *v = v.exp()),
        UnaryOp::Ln => x.iter_mut().for_each(|v| *v = v.ln()),
    }
}

/// Element-wise binary op `a = a (op) b`; arithmetic arms are written out so they vectorise.
fn apply_binary(op: BinaryOp, a: &mut [f64], b: &[f64]) {
    match op {
        BinaryOp::Add => a.iter_mut().zip(b).for_each(|(x, y)| *x += *y),
        BinaryOp::Sub => a.iter_mut().zip(b).for_each(|(x, y)| *x -= *y),
        BinaryOp::Mul => a.iter_mut().zip(b).for_each(|(x, y)| *x *= *y),
        BinaryOp::Div => a.iter_mut().zip(b).for_each(|(x, y)| *x /= *y),
        other => a
            .iter_mut()
            .zip(b)
            .for_each(|(x, y)| *x = other.apply(*x, *y)),
    }
}
