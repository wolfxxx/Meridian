"""Reconciliation and behaviour tests: Rust engine vs the independent NumPy reference."""

import numpy as np
import pytest

import meridian as mr
from meridian.models import term_life, with_profits

RTOL = 1e-11
ATOL = 1e-6  # currency units


def assert_reconciles(a: mr.Results, b: mr.Results):
    assert a.totals.keys() == b.totals.keys()
    assert a.policy_sums.keys() == b.policy_sums.keys()
    for k in a.totals:
        np.testing.assert_allclose(a.totals[k], b.totals[k], rtol=RTOL, atol=ATOL, err_msg=k)
    for k in a.policy_sums:
        np.testing.assert_allclose(a.policy_sums[k], b.policy_sums[k], rtol=RTOL, atol=ATOL, err_msg=k)


def test_term_life_reconciles_with_reference():
    m = term_life.build(n_years=25)
    mp, tb = term_life.synthetic_portfolio(400), term_life.default_tables()
    assert_reconciles(mr.run(m, mp, tb), mr.run(m, mp, tb, engine="numpy"))


def test_with_profits_c2_reconciles_with_reference():
    m = with_profits.build(n_years=10)
    mp, tb = with_profits.synthetic_portfolio(150), with_profits.default_tables()
    sc = with_profits.scenarios(12, m.n_steps)
    assert_reconciles(mr.run(m, mp, tb, sc), mr.run(m, mp, tb, sc, engine="numpy"))


def test_results_identical_across_chunk_sizes():
    m = with_profits.build(n_years=5)
    mp, tb = with_profits.synthetic_portfolio(333), with_profits.default_tables()
    sc = with_profits.scenarios(5, m.n_steps)
    base = mr.run(m, mp, tb, sc, chunk_size=2048)
    for chunk in (1, 13, 100_000):
        other = mr.run(m, mp, tb, sc, chunk_size=chunk)
        for k in base.totals:
            assert np.array_equal(base.totals[k], other.totals[k]), (k, chunk)
        for k in base.policy_sums:
            assert np.array_equal(base.policy_sums[k], other.policy_sums[k]), (k, chunk)


def test_c1_per_chunk_matches_lockstep_bit_for_bit():
    m = term_life.build(n_years=15)
    mp, tb = term_life.synthetic_portfolio(5_003), term_life.default_tables()
    auto = mr.run(m, mp, tb, keep_history=True)
    lock = mr.run(m, mp, tb, keep_history=True, strategy="lockstep", chunk_size=777)
    assert (auto.strategy, lock.strategy) == ("per_chunk", "lockstep")
    for part in ("totals", "policy_sums", "history"):
        a, b = getattr(auto, part), getattr(lock, part)
        assert a.keys() == b.keys()
        for k in a:
            assert np.array_equal(a[k], b[k]), (part, k)


def test_c2_scenario_partitioning_matches_global_lockstep_bit_for_bit():
    m = with_profits.build(n_years=3)
    mp, tb = with_profits.synthetic_portfolio(1_234), with_profits.default_tables()
    sc = with_profits.scenarios(41, m.n_steps)
    part = mr.run(m, mp, tb, sc, keep_history=True)
    glob = mr.run(m, mp, tb, sc, keep_history=True, strategy="lockstep", chunk_size=999)
    assert (part.strategy, glob.strategy) == ("lockstep_by_scenario", "lockstep")
    for name in ("totals", "policy_sums", "history"):
        a, b = getattr(part, name), getattr(glob, name)
        for k in a:
            assert np.array_equal(a[k], b[k]), (name, k)
    one = mr.run(m, mp, tb, {k: v[:1] for k, v in sc.items()})
    assert one.strategy == "lockstep"  # a single scenario has nothing to partition


def test_closed_form_single_policy():
    """Constant mortality, no lapses, flat expense: in-force decays geometrically."""
    m = term_life.build(n_years=10)
    q = 0.01
    tb = term_life.default_tables()
    tb["mort_qx"] = np.full(121, q)
    tb["lapse_rate"] = np.zeros(50)
    mp = {"policy_count": [1.0], "age_at_entry": [40.0], "term_m": [120.0], "duration_m": [0.0],
          "sum_assured": [100_000.0], "annual_premium": [1_200.0]}
    res = mr.run(m, mp, tb)
    qm = 1 - (1 - q) ** (1 / 12)
    expected = (1 - qm) ** np.arange(120)
    np.testing.assert_allclose(res.totals["pols_if"][0], expected, rtol=1e-13)
    np.testing.assert_allclose(res.totals["claims"][0], expected * qm * 100_000, rtol=1e-12)


def test_policies_past_term_contribute_nothing():
    m = term_life.build(n_years=5)
    tb = term_life.default_tables()
    mp = {"policy_count": [1.0], "age_at_entry": [40.0], "term_m": [24.0], "duration_m": [12.0],
          "sum_assured": [100_000.0], "annual_premium": [1_200.0]}
    res = mr.run(m, mp, tb)
    assert np.all(res.totals["pols_if"][0, 12:] == 0.0)
    assert res.totals["pols_if"][0, 11] > 0.0


def test_dependency_classes():
    info = mr.inspect(with_profits.build(n_years=1))
    cls = info["classes"]
    assert cls["total_assets"] == "C2"
    assert cls["bonus_rate"] == "C2"
    assert cls["guaranteed_pp"] == "C2"       # via bonus_rate[t-1]
    assert cls["asset_share_pp"] == "C1"      # depends only on its own lane and the scenario
    # Only one barrier per step: the bonus feedback loop needs every policy's asset share and
    # guarantee before the company totals can be formed.
    assert len(info["segments"]) == 2
    assert info["segments"][1][:2] == ["total_assets", "total_guarantees"]
    info_term = mr.inspect(term_life.build(n_years=1))
    assert set(info_term["classes"].values()) == {"C1"}
    assert len(info_term["segments"]) == 1


def test_trace_matches_full_run_for_c1_and_c2():
    m = term_life.build(n_years=3)
    mp, tb = term_life.synthetic_portfolio(50), term_life.default_tables()
    full = mr.run(m, mp, tb, keep_history=True)
    tr = mr.trace(m, mp, tb, policy=7)
    np.testing.assert_array_equal(tr.values["pv_net_cf"], full.history["pv_net_cf"][:, 0, 7])
    assert "formula:" in tr.explain("deaths", 5)

    w = with_profits.build(n_years=2)
    wmp, wtb = with_profits.synthetic_portfolio(40), with_profits.default_tables()
    sc = with_profits.scenarios(3, w.n_steps)
    wfull = mr.run(w, wmp, wtb, sc, keep_history=True)
    wtr = mr.trace(w, wmp, wtb, sc, policy=4, scenario=2)
    np.testing.assert_array_equal(wtr.values["guaranteed_pp"], wfull.history["guaranteed_pp"][:, 2, 4])


def test_cycle_error_names_the_loop():
    m = mr.Model("cyc", n_steps=3)

    @m.var
    def a():
        return m.v.b + 1

    @m.var
    def b():
        return m.v.a * 2

    with pytest.raises(ValueError, match="a -> b -> a"):
        mr.run(m, {"x": [1.0]})


def test_unknown_variable_and_missing_input():
    m = mr.Model("bad", n_steps=2)

    @m.var
    def a():
        return m.v.typo + m.mp.age

    with pytest.raises(ValueError, match="unknown variable `typo`"):
        mr.run(m, {"age": [1.0]})

    m2 = mr.Model("bad2", n_steps=2)

    @m2.var(total=True)
    def a2():
        return m2.mp.age * 2

    with pytest.raises(ValueError, match="model-point column `age`"):
        mr.run(m2, {"other": [1.0]})


def test_python_if_on_expressions_is_rejected():
    m = mr.Model("bool", n_steps=1)
    with pytest.raises(TypeError, match="where"):
        @m.var
        def a():
            return 1 if mr.t > 0 else 0


def test_common_subexpressions_are_shared_in_ir():
    m = mr.Model("cse", n_steps=1)

    @m.var
    def a():
        return (m.mp.x * 2) + (m.mp.x * 2)

    nodes = m.to_ir()["nodes"]
    assert sum(1 for n in nodes if n["op"] == "binary" and n["func"] == "mul") == 1
