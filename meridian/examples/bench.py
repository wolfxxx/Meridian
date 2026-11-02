"""Throughput comparison: NumPy reference vs Rust engine (lockstep vs per-chunk; 1 vs all threads).

Timings are the best of 3 runs (NumPy: 1 run).

    python examples/bench.py --policies 100000 --years 30
    python examples/bench.py --c2 --policies 2000 --scenarios 50 --years 20   # C2, NumPy-comparable size
    RAYON_NUM_THREADS controls the Rust thread count; this script spawns sub-runs for it.
"""

import argparse
import json
import os
import subprocess
import sys

import meridian as mr
from meridian.models import term_life, with_profits


def c2_run(engine: str, policies: int, scenarios: int, years: int) -> float:
    m = with_profits.build(n_years=years)
    tb = with_profits.default_tables()
    mp, sc = with_profits.synthetic_portfolio(policies), with_profits.scenarios(scenarios, m.n_steps)
    mr.run(m, with_profits.synthetic_portfolio(10), tb, with_profits.scenarios(2, m.n_steps))  # warm-up
    return min(mr.run(m, mp, tb, sc, engine=engine).seconds for _ in range(1 if engine == "numpy" else 3))


def one_run(engine: str, policies: int, years: int) -> float:
    strategy = "auto"
    if engine == "rust-lockstep":
        engine, strategy = "rust", "lockstep"
    m = term_life.build(n_years=years)
    mp, tb = term_life.synthetic_portfolio(policies), term_life.default_tables()
    kw = {"strategy": strategy} if engine == "rust" else {}
    mr.run(m, term_life.synthetic_portfolio(100), tb, engine=engine, **kw)  # warm-up
    return min(mr.run(m, mp, tb, engine=engine, **kw).seconds for _ in range(1 if engine == "numpy" else 3))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--policies", type=int, default=100_000)
    ap.add_argument("--years", type=int, default=30)
    ap.add_argument("--c2", action="store_true",
                    help="benchmark the C2 with_profits model (lockstep) instead of term_life")
    ap.add_argument("--scenarios", type=int, default=200, help="scenarios for --c2")
    ap.add_argument("--child", nargs=2, metavar=("ENGINE", "THREADS"))
    a = ap.parse_args()
    if a.child:
        if a.c2:
            s = c2_run(a.child[0], a.policies, a.scenarios, a.years)
        else:
            s = one_run(a.child[0], a.policies, a.years)
        print(json.dumps({"s": s}))
        return

    def sub(engine, threads):
        env = dict(os.environ)
        if threads:
            env["RAYON_NUM_THREADS"] = str(threads)
        out = subprocess.run([sys.executable, __file__, "--policies", str(a.policies), "--years",
                              str(a.years), "--scenarios", str(a.scenarios), "--child", engine,
                              str(threads)] + (["--c2"] if a.c2 else []),
                             env=env, capture_output=True, text=True, check=True).stdout
        return json.loads(out.strip().splitlines()[-1])["s"]

    if a.c2:
        cells = a.policies * a.scenarios * a.years * 12 / 1e6
        rows = [("NumPy reference (1 thread)", sub("numpy", 0)),
                ("Rust lockstep, 1 thread", sub("rust", 1)),
                ("Rust lockstep, all threads", sub("rust", 0))]
        base = rows[0][1]
        print(f"with_profits (C2): {a.policies:,} policies x {a.scenarios} scenarios x {a.years * 12} "
              f"months ({cells:.0f}m lane-months), {os.cpu_count()} logical CPUs")
        for name, s in rows:
            print(f"  {name:<28} {s:8.2f}s  {cells / s:8.1f}m lane-months/s  x{base / s:.1f} vs NumPy")
        return

    cells = a.policies * a.years * 12 / 1e6
    rows = [("NumPy reference (1 thread)", sub("numpy", 0)),
            ("Rust lockstep, 1 thread", sub("rust-lockstep", 1)),
            ("Rust lockstep, all threads", sub("rust-lockstep", 0)),
            ("Rust per-chunk, 1 thread", sub("rust", 1)),
            ("Rust per-chunk, all threads", sub("rust", 0))]
    base = rows[0][1]
    print(f"term_life: {a.policies:,} policies x {a.years * 12} months ({cells:.0f}m policy-months), "
          f"{os.cpu_count()} logical CPUs")
    for name, s in rows:
        print(f"  {name:<28} {s:8.2f}s  {cells / s:8.1f}m policy-months/s  x{base / s:.1f} vs NumPy")


if __name__ == "__main__":
    main()
