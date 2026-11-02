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

## The Meridian app

Meridian has a desktop app: one window where you can open a model, read its formulas,
change assumptions, run it, explain any number and see the validation evidence.

| Screen | What it does |
|---|---|
| Workspace | The models, their size and the latest result; run or open each one |
| Overview | What the model is, latest results, assumptions and validation at a glance |
| Variables | Every formula with its links: what it uses, what uses it, and a dependency graph (Prophet's Diagram View). **Edit any formula in place**: it is checked as you type (unknown names with suggestions, circular references, wrong arguments), with a before/after preview for the first policy. Edited formulas are flagged, used by runs and explanations, and can be reverted; validation always checks the original model |
| Assumptions | Tables as charts and editable grids. Use "adjust every value by %" for quick sensitivities; edited tables are flagged and used by the next run |
| Policy data | Distribution of every field, plus a searchable grid; click a row to explain it. **Import your own data** from CSV: headings are matched by name (with common alternatives such as "SA" or "Gender"), every value is checked, and errors are listed with their spreadsheet row before anything changes. Semicolons, decimal commas and "R 10 000" are understood. Template and export buttons give you a CSV to start from |
| Run & results | One button, live progress, run history and comparison with a baseline run. Shows cash flows, present values, the scenario distribution with CTE70 (savings), and BEL by stress, SCR and risk margin (funeral) |
| What-if | Sliders for mortality, lapses, interest rates and product charges, applied on top of any edited tables. **Standard sensitivities** runs the base plus each assumption up and down and shows a tornado chart of what moves the result most. **Compare runs** puts up to four runs side by side, with differences and overlaid cash flows, and warns when runs use different policy data |
| Explain | Pick a policy or life and a month; follow any number back through its formula and inputs |
| Validation | Reconciliation against lifelib, or against the independent implementation, with pass marks and evidence |

**Your work is kept between sessions**: edited tables and formulas, imported policy data and the last 40 runs of each model are saved in `%APPDATA%\Meridian\workspace` and restored on start-up through the same checks (anything that no longer fits is skipped and reported). Uninstalling leaves this folder in place.

On first start a short guided tour introduces each part (reopen it from the **?** button). Run
results export to CSV. Settings such as the theme are kept in `%APPDATA%\Meridian\settings.json`.

**Install it** (for users): run `Meridian-Setup-<version>.exe` and click the Meridian icon. It
installs for the current user only: no administrator rights, Python, Rust or command line
needed, and it can be removed from Windows "Installed apps". The installer is about 40 MB.

**Start it from source** (after the build steps below): double-click `Start Meridian.cmd`, or run
`.\.venv\Scripts\python -m meridian.app`. It opens in its own window, or in your browser if no
web view (Edge WebView2) is available.

**Build the installer:** `.\.venv\Scripts\python packaging\build_installer.py` builds the
interface, freezes the app with PyInstaller (`packaging/meridian.spec`), and runs two checks:
- the window smoke test;
- `packaging/check_frozen.py`, which runs every model and every validation inside the frozen app.

It then compiles `packaging/meridian.iss` with Inno Setup 6 into `dist/`. In GitHub
Actions, `.github/workflows/release.yml` does the same on a Windows runner. Run it by hand or
push a `v*` tag, which also attaches the installer to a GitHub release.

The interface is in `ui/` (React + TypeScript; `npm install && npm run build` writes it into the
Python package). The local service is in `python/meridian/app/`: `catalog.py` describes each
model to the app, and `server.py` provides the API.

## Headline: two lifelib models, rebuilt and reconciled

[lifelib](https://lifelib.io) is an open-source library of published actuarial models. Two of
its models were rebuilt in Meridian's modelling language and reconciled **policy by policy**
against lifelib's own output:

| Model | What it exercises | Result | Speed (Meridian vs lifelib) |
|---|---|---|---|
| **BasicTerm** (term assurance, 10,000 policies) | select & ultimate mortality, premium from PVs (two-pass) | every premium identical to the cent; portfolio PV identical | 0.03 s vs 0.38 s |
| **CashValue_ME** (savings / UL, stochastic) | account value with intra-month timing, COI on net amount at risk, surrender charges by product, single/level premiums, whole life to age 115, new and in-force business, 10 stochastic fund-return scenarios | gross PVs within 2e-14 (new business) and 4e-13 (in-force) per policy and scenario; portfolio PV by scenario identical to 4 decimals | **1.0 s for all 10 scenarios vs 172 s** |

A third model shows the kind of business this is for:

| Model | What it exercises | Checks | Speed |
|---|---|---|---|
| **South African family funeral** (illustrative SAM basis) | up to 8 lives per policy (main member, spouse, children to age 21, extended family), policy ends on lapse or main-member death; BEL, six SAM-style stresses, SCR with the life correlation matrix, 6% cost-of-capital risk margin | BEL per policy equals an independent plain-Python loop implementation within 2e-13, under all 7 bases; Rust = NumPy reference | 20,000 policies (70,000 lives) × 600 months × 7 runs in about 8–11 s |

`examples/run_sa_funeral.py`, `tests/test_sa_funeral.py`, `tests/independent_funeral.py`. All its
assumptions are invented for illustration. Its mortality curve is shaped like South African
population mortality but is not an ASSA or SA85-90 table. The SAM calculation is simplified:
stresses are applied to the whole portfolio, and the risk margin is projected in proportion to
policies in force.

### BasicTerm in detail

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

### CashValue_ME (stochastic) in detail

`examples/run_lifelib_cashvalue.py`, `tests/test_lifelib_cashvalue.py`. lifelib runs one
scenario per call; Meridian runs all scenarios in one pass (lanes = scenarios × policies).

| Check (every policy × every scenario) | New business (10,000 × 10 scenarios × 1,141 months) | In-force (1,000 × 3 × 1,109) |
|---|---|---|
| 8 gross PV items (premiums, investment income, death, surrender, maturity, expenses, commissions, change in AV) | worst relative difference 2.0e-14 | 4.4e-13 |
| PV of net cash flow, relative to gross flows | 2.8e-15 | 1.1e-15 |
| Portfolio PV of net cash flow by scenario | identical to 4 decimals, e.g. scenario 1: 51,184,096,016.2475 | identical to 4 decimals |
| Monthly cash flows by scenario | ≤ 4e-14 | ≤ 4e-14 |
| Time | Meridian 1.0 s (all 10 scenarios) vs lifelib 172 s | 0.12 s vs 19 s |

The in-force set was made by giving 1,000 policies random durations and account values. It
was then run through lifelib unchanged, so the existing-business logic is reconciled too.
Capacity: 100 generated scenarios × 10,000 policies × 1,141 months (1.1bn policy-scenario-months)
runs in about 12 s.

Reconciliation also surfaced one convention that has to be explicit. After a whole-life policy
matures, the per-policy account value keeps being rolled forward with no policies left, and
ages pass the mortality table's end. lifelib's lookup returns q = 0 outside the table;
Meridian's default clamps to the last row. Tables therefore take an explicit `fill=` setting
(`Table(q, dims=[18, 0], fill=0.0)`), and the model states its choice. Nobody has to discover
it from NaNs.

lifelib's data is redistributed under its MIT licence: see
`python/meridian/models/data/lifelib_basicterm/NOTICE.md` and `.../lifelib_cashvalue/NOTICE.md`. The reference results come from
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
├─ tools/                        lifelib reference generators (separate .venv-lifelib), showcase data/build
├─ showcase/                     shareable report: template.html + showcase_data.json -> meridian_report.html
└─ examples/                     demos and benchmark
```

## Build and test (Windows / PowerShell)

Prerequisites: Rust stable (MSVC toolchain), Python ≥ 3.10.

```powershell
cd meridian
python -m venv .venv
.\.venv\Scripts\python -m pip install "maturin>=1.7,<2.0" pytest numpy fastapi "uvicorn[standard]" pywebview httpx2
cd ui; npm install; npm run build; cd ..                # builds the app interface
$env:VIRTUAL_ENV = (Resolve-Path .venv).Path
.\.venv\Scripts\python -m maturin develop --release   # builds the Rust extension into the venv

cargo test -p meridian-core                            # Rust tests
.\.venv\Scripts\python -m pytest -q                     # Python reconciliation tests

.\.venv\Scripts\python examples\run_lifelib_basicterm.py  # lifelib BasicTerm reconciliation
.\.venv\Scripts\python examples\run_lifelib_cashvalue.py  # lifelib stochastic CashValue reconciliation
.\.venv\Scripts\python examples\run_sa_funeral.py      # SA family funeral, SAM BEL/SCR/risk margin
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
  - **`fill=`** sets an explicit value for any key outside the table, e.g. `fill=0.0`.
- **Lives within a policy.** `Model(..., lives=8)` treats each 8 consecutive model-point rows as one policy's lives. Formulas are written per life. `life` is the slot number, and `sum_lives(x)` is the policy total, broadcast to every life. `mr.group_lives(rows, "policy_id", 8, pad=...)` arranges one-row-per-life data into padded policies. This is Prophet's array variables, and it keeps the fast per-chunk path.
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
| Array variables / lives in a policy; run numbers as assumption sets | `Model(lives=8)`, `sum_lives`, `group_lives`; the funeral model's seven bases (`tb.basis['mass_lapse']`) |
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
4. **Missing language features** (done: multi-dimensional range/category tables, text categories, lives within a policy):
   - general arrays with named axes (funds, benefits)
   - procedural blocks
   - multiple time granularities
   - nested (C3) runs
   - goal-seek
5. **C2 at scale.** Within one scenario the engine is single-node today. Cross-node sharding with a per-step all-reduce is designed in spec §19.4 but not built.
6. **GPU back end** (generated CUDA/Triton kernels launched from Rust) is not started.
7. **Governance features** are out of scope for this spike: run manifests, Git integration, assumption store, results store.

## License

Apache-2.0. This is the intended licence of the community edition (spec §28).
