# Meridian prototype: Python modelling language over a Rust engine

This is the technical spike behind ADR-001 in
[`../Prophet_Analysis_and_Competitor_Spec.md`](../Prophet_Analysis_and_Competitor_Spec.md) (§25.1).
It tests the riskiest part of the spec. Actuaries write models in Python. The models are traced
into an intermediate representation (IR) and executed by a vectorised Rust engine across
**policies × scenarios × time**. The engine handles both dependency classes from spec §19.4:

- **C1:** policy-independent models.
- **C2:** models with company-level feedback, such as with-profits bonus declaration.

> This is a prototype. Its reference models illustrate the modelling style and are not
> certified actuarial libraries.

## Headline: lifelib's BasicTerm model, rebuilt and reconciled

[lifelib](https://lifelib.io)'s `BasicTerm` model is an open-source, published term-assurance
projection: 10,000 policies, monthly, select-and-ultimate mortality, a premium set from present
values. It was rebuilt in Meridian and reconciled policy by policy against lifelib's own output
(`examples/run_lifelib_basicterm.py`, `tests/test_lifelib_basicterm.py`):

| Check | Result |
|---|---|
| Premium per policy | **10,000 / 10,000 identical to the cent** |
| PV of premiums, claims, expenses, commissions per policy | worst relative difference ≤ 2e-15 |
| PV of net cash flow per policy | worst relative difference 1.5e-12 (difference of large numbers) |
| Portfolio PV of net cash flow | **14,489,630.534602 in both** |
| Monthly portfolio cash flows (8 series × 241 months) | worst relative difference ≤ 6e-16 |
| Speed, 10,000 policies (pricing + projection passes) | Meridian 0.03 s; lifelib's NumPy-vectorised `BasicTerm_M` 0.38 s |
| Speed, 1,000,000 policies | Meridian 1.6 s (about 300m policy-months/s) |

lifelib's data is redistributed under its MIT licence: see
`python/meridian/models/data/lifelib_basicterm/NOTICE.md`. The reference results come from
`tools/make_lifelib_reference.py`, which runs lifelib itself. It also checks that lifelib's
seriatim `BasicTerm_S` and vectorised `BasicTerm_M` agree, to 4e-14.

## Layout

```
meridian/
├─ Cargo.toml                    Rust workspace
├─ crates/meridian-core/         engine: IR, compiler (validation, ordering, C1/C2 + uniform analysis), interpreter
│  └─ tests/engine.rs            Rust tests (closed forms, cycles, C2 sums, strategy equivalence, determinism)
├─ crates/meridian-py/           PyO3 bindings -> Python module `meridian._engine`
├─ python/meridian/
│  ├─ dsl.py                     the modelling language (traced Python expressions)
│  ├─ reference.py               independent pure-NumPy implementation (reconciliation baseline)
│  ├─ runner.py                  run(), inspect(), trace() (single-policy explain)
│  ├─ tables.py                  multi-dimensional range/category tables, text categories
│  └─ models/                    term_life (C1), with_profits (C2, stochastic), lifelib_basicterm
├─ tests/                        reconciliation and behaviour tests (Rust vs NumPy vs lifelib)
├─ tools/make_lifelib_reference.py  regenerates lifelib's reference results (separate venv)
└─ examples/                     demos and benchmark
```

## Build and test (Windows / PowerShell)

Prerequisites: Rust stable (MSVC toolchain), Python ≥ 3.10.

```powershell
cd meridian
python -m venv .venv
.\.venv\Scripts\python -m pip install "maturin>=1.7,<2.0" pytest numpy
$env:VIRTUAL_ENV = (Resolve-Path .venv).Path
.\.venv\Scripts\python -m maturin develop --release   # builds the Rust extension into the venv

cargo test -p meridian-core                            # Rust tests
.\.venv\Scripts\python -m pytest -q                     # Python reconciliation tests

.\.venv\Scripts\python examples\run_lifelib_basicterm.py  # lifelib reconciliation showcase
.\.venv\Scripts\python examples\run_term_life.py       # C1 demo + trace/explain
.\.venv\Scripts\python examples\run_with_profits.py    # C2 stochastic demo (CTE70)
.\.venv\Scripts\python examples\bench.py               # NumPy vs Rust throughput
```

On macOS or Linux, use `.venv/bin/python` and `source .venv/bin/activate` instead.

## Writing a model

```python
import meridian as mr
from meridian import t, where, floor, sum_policies

m = mr.Model("term", n_steps=240)          # monthly, 20 years
v, mp, tb = m.v, m.mp, m.tables             # variables, model-point inputs, tables

@m.var(init=0.0, total=True)
def pols_if():
    """Policies in force at the start of month t."""
    return where(t == 0, mp.policy_count, v.pols_if.lag(1) - v.deaths.lag(1))

@m.var(total=True)
def deaths():
    return v.pols_if * (1 - (1 - tb.mort_qx[mp.age + floor(t / 12)]) ** (1 / 12))

res = mr.run(m, model_points, tables)        # or engine="numpy" for the reference
res.totals["deaths"]                         # (n_scenarios, n_steps)
print(mr.trace(m, model_points, tables, policy=0).explain("deaths", 3))
```

Language rules:
- **Tracing.** Each decorated function is called once and its returned expression is recorded.
- **No Python control flow on model values.** Use `where()` for conditions, and `&` / `|` instead of `and` / `or`. Using Python `if` on an expression raises an error that suggests `where`.
- **Referencing variables.** Refer to variables through `v.<name>`, so definition order doesn't matter. `.lag(k)` gives the value `k` steps earlier, and the variable's `init` is used before the projection starts.
- **Ordering and cycles.** The engine orders evaluation within a time step itself. A same-step loop is reported with its path, e.g. `a -> b -> a`.
- **Cross-policy aggregates.** `sum_policies(x)` makes a model C2: it sums `x` over all policies of the same scenario at the current step.
- **Tables.** `tb.name[k1, k2, ...]` takes one key per dimension of a `mr.Table`:
  - **Integer-range dimensions** (e.g. `Table(q, dims=[18, 0])` for ages from 18 × durations from 0) floor and clamp the key.
  - **Category dimensions** (e.g. `dims=[["M", "F"], ["NS", "S"]]`) must match a label exactly. An unknown label gives NaN rather than a silent wrong value.
- **Text.** Model-point columns may be text, e.g. `sex = "F"`, and formulas can compare them: `where(mp.sex == "F", ...)`. Labels become deterministic numeric codes, so no list has to be declared.

## What the prototype demonstrates (spec mapping)

| Spec item | Demonstrated by |
|---|---|
| L-1/L-2/L-3: Python language, automatic dependency ordering, vectorised execution | `dsl.py`, `compile.rs`, `engine.rs` |
| §19.4 C1/C2 classes, per-step barrier for `sum_policies` | `compile.rs` class analysis; `with_profits` model; `test_dependency_classes` |
| L-11/NF-12/NF-13: deterministic, bit-identical results regardless of strategy, chunk size or threads | fixed-block pairwise summation in `sum.rs`; per-chunk vs lockstep equality tests in `engine.rs` and `test_engine.py` |
| §19.4 execution strategies: C1 per-chunk with no barriers; C2 partitioned by scenario, each a segmented lockstep with barriers only where a total needs them | `engine.rs` `run_per_chunk` / `run_by_scenario` / `run_lockstep`; `compile.rs` `build_segments`; `inspect(model)["segments"]` |
| §31.1: independent implementation for reconciliation | `reference.py` (Rust vs NumPy, 1e-11 relative); **external: lifelib BasicTerm**, with every premium identical and PVs within 2e-15 |
| Tables and categories (the successor to Prophet's generic and parameter tables) | `tables.py`, `table.rs`; `tests/test_tables.py` |
| DX-3: single-policy trace and "explain this number" | `runner.trace()`, `Trace.explain()` |
| MS-12: assumption sets as data | `assumptions` and `wp_params` tables (swap them to run a sensitivity) |

## Benchmark (i7-14700K, 28 logical CPUs, Windows 11, `examples/bench.py`, best of 3)

Strategies are chosen automatically (`Results.strategy` reports which one ran). C1 models run **per chunk**: each block of policies goes through all time steps independently,
with no synchronisation. C2 models run in **lockstep**. Each time step is split into
*segments* that break only where a `sum_policies` total needs every policy finished. Each
segment is one parallel pass, and each chunk evaluates all of the segment's variables while
they are in cache. All strategies give bit-identical results; `strategy="lockstep"` forces
lockstep for comparison.

**term_life (C1)**, 100k policies × 360 months (36m policy-months):

| Engine | Time | Throughput | vs NumPy |
|---|---|---|---|
| NumPy reference (1 thread) | 13.8 s | 2.6m policy-months/s | 1× |
| Rust lockstep, 1 thread | 1.88 s | 19.1m/s | 7.3× |
| Rust lockstep, 28 threads | 0.39 s | 92m/s | 35× |
| Rust per-chunk, 1 thread | 1.63 s | 22.1m/s | 8.5× |
| **Rust per-chunk, 28 threads** | **0.14 s** | **262m/s** | **100×** |

term_life at 1m policies × 360 months: per-chunk about 1.4 s.

**with_profits (C2, stochastic).** With several scenarios, C2 runs are **partitioned by
scenario**. `sum_policies` totals are per scenario, so scenarios are independent: each group
of scenarios runs its own segmented lockstep through all time steps. `strategy="lockstep"`
forces global lockstep over all lanes.

| Size | Engine | Time | vs NumPy |
|---|---|---|---|
| 2k policies × 50 scenarios × 240 months (24m lane-months) | NumPy (1 thread) | 5.4 s | 1× |
| | Rust, 1 thread | 0.48 s | 11× |
| | **Rust, 28 threads** | **0.07 s** | **81×** |
| 20k × 200 × 240 (960m lane-months) | Rust global lockstep | 12.1 s (79m/s) | — |
| | **Rust scenario-partitioned** | **6–7.5 s (127–160m/s)** | — |

History of the 960m lane-month C2 run:

| Version | Time |
|---|---|
| First prototype | 26.8 s |
| Allocation and uniform-folding fixes | 16–20 s |
| Segments | 13.4 s |
| Block-wise reductions | 12.1 s |
| **Scenario partitioning** | **6.0–7.5 s** |

The PV-of-guarantee results (mean 34,087,164; CTE70 71,043,727) are identical in every
version.

These numbers were measured with other applications using about a third of the CPU. Expect ±15–30% run to run.

## Known limitations and next steps

1. **Cache footprint of large scenarios.** Done so far for C2: segmented lockstep, block-wise reductions and scenario partitioning. Each scenario group still holds every variable's buffers for all of its policies, about 4 MB for 20k policies. With 28 threads that exceeds this CPU's 33 MB shared L3, so large C2 runs remain partly memory-bound. Operator fusion (next item) shrinks the number of buffers. Holding state at narrower precision for non-governed exploratory runs is another option.
2. **Operator fusion / code generation.** The interpreter materialises every intermediate node into a buffer. The next step is to fuse expression trees into single loops, then generate code with Cranelift or LLVM (spec §25.1).
3. **Shared subexpressions are recomputed in the engine.** The Python tracer de-duplicates them in the IR, but the engine re-evaluates shared nodes. Add per-chunk memoisation.
4. **Missing language features** (done: multi-dimensional range/category tables and text categories):
   - arrays with named axes
   - procedural blocks
   - multiple time granularities
   - nested (C3) runs
   - goal-seek
5. **C2 at scale.** Within one scenario the engine is single-node today. Cross-node sharding with a per-step all-reduce is designed in spec §19.4 but not built.
6. **GPU back end** (generated CUDA/Triton kernels launched from Rust) is not started.
7. **Governance features** are out of scope for this spike: run manifests, Git integration, assumption store, results store.

## License

Apache-2.0. This is the intended licence of the community edition (spec §28).
