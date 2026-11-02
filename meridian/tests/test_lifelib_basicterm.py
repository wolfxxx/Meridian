"""Reconciliation against lifelib's BasicTerm model — an independent, public reference.

lifelib's own results for its 10,000 sample policies were produced by
``tools/make_lifelib_reference.py`` and are stored in ``tests/data/lifelib_basicterm``.
"""

import csv
import json
from pathlib import Path

import numpy as np
import pytest

import meridian as mr
from meridian.models import lifelib_basicterm as bt

DATA = Path(__file__).resolve().parent / "data" / "lifelib_basicterm"


def _read(name):
    with open(DATA / name, newline="") as f:
        rows = list(csv.DictReader(f))
    return {k: np.array([float(r[k]) for r in rows]) for k in rows[0]}


@pytest.fixture(scope="module")
def result():
    return bt.run_basicterm()


@pytest.fixture(scope="module")
def lifelib_policy():
    return _read("lifelib_M_per_policy.csv")


def rel(a, b):
    return np.abs(a - b) / np.maximum(1.0, np.abs(b))


def test_premiums_match_lifelib_to_the_cent(result, lifelib_policy):
    assert np.array_equal(result.premium_pp, lifelib_policy["premium_pp"])


@pytest.mark.parametrize("name", ["pv_premiums", "pv_claims", "pv_expenses",
                                  "pv_commissions", "pv_pols_if", "pv_net_cf"])
def test_present_values_match_lifelib_per_policy(result, lifelib_policy, name):
    ours = result.projection.policy_sums[name][0]
    assert ours.shape == lifelib_policy[name].shape
    assert rel(ours, lifelib_policy[name]).max() < 1e-11, name


def test_portfolio_pv_matches_lifelib(result):
    meta = json.loads((DATA / "meta.json").read_text())
    ours = result.projection.policy_sums["pv_net_cf"].sum()
    assert ours == pytest.approx(meta["portfolio_pv_net_cf"], rel=1e-13)


@pytest.mark.parametrize("name", ["premiums", "claims", "expenses", "commissions", "net_cf",
                                  "pols_if", "pols_death", "pols_lapse"])
def test_monthly_cashflows_match_lifelib(result, name):
    cf = _read("lifelib_M_cashflows.csv")
    assert rel(result.projection.totals[name][0], cf[name]).max() < 1e-12, name


def test_lifelib_seriatim_and_vectorised_agree_on_sample():
    """lifelib's own BasicTerm_S (seriatim) and BasicTerm_M agree, so M is a sound reference."""
    s = _read("lifelib_S_sample.csv")
    m = _read("lifelib_M_per_policy.csv")
    idx = s["point_id"].astype(int) - 1
    for k in ["premium_pp", "pv_net_cf", "pv_claims", "pv_premiums"]:
        assert rel(s[k], m[k][idx]).max() < 1e-12, k


def test_numpy_reference_engine_agrees(result):
    """Third, in-house implementation (pure NumPy) on a subset of policies."""
    mp = bt.load_model_points()
    sub = {k: v[:300] for k, v in mp.items()}
    ours = bt.run_basicterm(sub)
    ref = bt.run_basicterm(sub, engine="numpy")
    assert np.array_equal(ours.premium_pp, ref.premium_pp)
    for k, v in ours.projection.policy_sums.items():
        assert rel(v, ref.projection.policy_sums[k]).max() < 1e-11, k


def test_select_mortality_uses_attained_age_and_capped_duration():
    tb = bt.load_tables()
    m = bt.build(max_policy_term=10)
    mp = {"age_at_entry": [40.0], "policy_term": [10.0], "sum_assured": [100_000.0],
          "premium_pp": [0.0], "policy_count": [1.0], "sex": np.array(["M"])}
    tr = mr.trace(m, mp, tb)
    q = tb["mort_table"].values
    for step, (age, dur) in {0: (40, 0), 12: (41, 1), 84: (47, 5), 119: (49, 5)}.items():
        assert tr.values["mort_rate"][step] == q[age - 18, dur], step
