"""Multi-dimensional tables and text categories: Rust engine vs NumPy reference, semantics."""

import numpy as np
import pytest

import meridian as mr
from meridian import Table, t, where


def _model():
    m = mr.Model("tables", n_steps=24)
    v, mp, tb = m.v, m.mp, m.tables

    @m.var
    def dur():
        return mp.duration + t / 12

    @m.var(total=True, policy_sum=True)
    def q():
        """Select & ultimate rate by attained age and duration, adjusted by sex and smoker."""
        return tb.mort[mp.age + v.dur, v.dur] * tb.sex_factor[mp.sex] * tb.smoker[mp.sex, mp.smoker]

    @m.var(total=True, policy_sum=True)
    def lapse():
        return tb.lapse[mp.product, v.dur]

    @m.var(total=True)
    def female_count():
        return where(mp.sex == "F", 1.0, 0.0)

    return m


def _tables():
    ages, durs = np.arange(18, 101), np.arange(0, 3)
    mort = 0.0005 * np.exp(0.08 * (ages[:, None] - 30)) * (0.7 + 0.15 * durs[None, :])
    return {
        "mort": Table(mort, dims=[18, 0]),
        "sex_factor": Table([1.0, 0.85], dims=[["M", "F"]]),
        "smoker": Table([[1.0, 1.6], [1.0, 1.5]], dims=[["M", "F"], ["NS", "S"]]),
        "lapse": Table([[0.12, 0.08, 0.05, 0.04], [0.06, 0.05, 0.04, 0.03]],
                       dims=[["TERM", "WL"], 0]),
    }


def _mp(n=500, seed=3):
    rng = np.random.default_rng(seed)
    return {
        "age": rng.integers(15, 105, n).astype(float),   # includes out-of-range ages
        "duration": rng.integers(0, 6, n).astype(float),
        "sex": rng.choice(["M", "F"], n),
        "smoker": rng.choice(["NS", "S"], n),
        "product": rng.choice(["TERM", "WL"], n),
    }


def test_rust_matches_numpy_reference_with_nd_and_category_tables():
    m, tb, mp = _model(), _tables(), _mp()
    a, b = mr.run(m, mp, tb), mr.run(m, mp, tb, engine="numpy")
    for k in a.totals:
        np.testing.assert_allclose(a.totals[k], b.totals[k], rtol=1e-13, err_msg=k)
    for k in a.policy_sums:
        np.testing.assert_allclose(a.policy_sums[k], b.policy_sums[k], rtol=1e-13, err_msg=k)


def test_category_comparison_and_counts():
    m, tb, mp = _model(), _tables(), _mp()
    res = mr.run(m, mp, tb)
    assert res.totals["female_count"][0, 0] == np.sum(mp["sex"] == "F")


def test_lookup_values_by_hand():
    m, tb = _model(), _tables()
    mp = {"age": [40.0, 200.0], "duration": [1.0, 9.0], "sex": np.array(["F", "M"]),
          "smoker": np.array(["S", "NS"]), "product": np.array(["WL", "TERM"])}
    tr = mr.trace(m, mp, tb, policy=0)
    mort = tb["mort"].values
    # t=0: attained age 41 (40 + dur 1), duration 1; female smoker factors 0.85 * 1.5
    assert tr.values["q"][0] == pytest.approx(mort[41 - 18, 1] * 0.85 * 1.5, rel=1e-15)
    assert tr.values["lapse"][0] == 0.05
    tr1 = mr.trace(m, mp, tb, policy=1)
    # age 209 and duration 9 clamp to the last row and column
    assert tr1.values["q"][0] == pytest.approx(mort[-1, -1], rel=1e-15)
    assert tr1.values["lapse"][0] == 0.04


def test_unknown_category_gives_nan_not_a_silent_value():
    m, tb = _model(), _tables()
    mp = {"age": [40.0], "duration": [0.0], "sex": np.array(["X"]),
          "smoker": np.array(["NS"]), "product": np.array(["TERM"])}
    res = mr.run(m, mp, tb)
    assert np.isnan(res.policy_sums["q"]).all()
    ref = mr.run(m, mp, tb, engine="numpy")
    assert np.isnan(ref.policy_sums["q"]).all()


def test_wrong_number_of_keys_is_an_error():
    m = mr.Model("bad", n_steps=1)

    @m.var
    def a():
        return m.tables.mort[m.mp.age]

    with pytest.raises(ValueError, match="dimension"):
        mr.run(m, {"age": [40.0]}, {"mort": Table(np.ones((3, 2)))})


def test_table_validation_and_formula_text():
    with pytest.raises(ValueError):
        Table([1.0, 2.0], dims=[["A"]])
    with pytest.raises(ValueError):
        Table([1.0, 2.0], dims=[["A", "A"]])
    assert "where((mp.sex == 'F')" in _model().formula("female_count")
    assert mr.category_code("F") == mr.category_code("F") != mr.category_code("M")
    assert mr.category_code("F") < -2.0 ** 52
