"""Stochastic reconciliation against lifelib's CashValue_ME (savings library).

lifelib ran one scenario at a time; Meridian runs all scenarios in one pass. Targets were
produced by ``tools/make_lifelib_cashvalue_reference.py``:
* ``portfolio.npz``: lifelib's 10,000 new-business policies x 10 scenarios;
* ``inforce.npz``: 1,000 policies made in-force (durations, account values) x 3 scenarios.
"""

import json
from pathlib import Path

import numpy as np
import pytest

from meridian.models import lifelib_cashvalue as cv

DATA = Path(cv.__file__).resolve().parents[1] / "validation_data" / "lifelib_cashvalue"
GROSS = ["pv_premiums", "pv_inv_income", "pv_claims_death", "pv_claims_lapse",
         "pv_claims_maturity", "pv_expenses", "pv_commissions", "pv_av_change"]
SETS = {
    "portfolio": ("model_point_10000.csv", "portfolio.npz", None),
    "inforce": ("model_point_inforce_1000.csv", "inforce.npz", [1, 2, 3]),
}


@pytest.fixture(scope="module", params=list(SETS))
def case(request):
    mpfile, ref_file, scen = SETS[request.param]
    ref = np.load(DATA / ref_file)
    res = cv.run_cashvalue(cv.load_model_points(mpfile), scenarios=scen)
    return request.param, res, ref


def rel(a, b):
    return np.abs(a - b) / np.maximum(1.0, np.abs(b))


def test_shapes_and_projection_length(case):
    _, res, ref = case
    assert res.n_steps == int(ref["n_steps"])
    assert res.policy_sums["pv_net_cf"].shape == ref["pv_net_cf"].shape  # (scenarios, policies)


@pytest.mark.parametrize("name", GROSS + ["pv_pols_if"])
def test_gross_present_values_per_policy_and_scenario(case, name):
    label, res, ref = case
    # Paths compound over up to 1,100 months; allow last-digit drift of exp/pow along the path.
    tol = 1e-13 if label == "portfolio" and name != "pv_av_change" else 1e-12
    assert rel(res.policy_sums[name], ref[name]).max() < tol, name


def test_net_cash_flow_relative_to_gross_flows(case):
    _, res, ref = case
    gross = sum(np.abs(ref[k]) for k in GROSS)
    diff = np.abs(res.policy_sums["pv_net_cf"] - ref["pv_net_cf"])
    assert (diff / np.maximum(gross, 1.0)).max() < 1e-13


def test_portfolio_net_cash_flow_by_scenario(case):
    label, res, ref = case
    meta = json.loads((DATA / "meta.json").read_text())[label]
    np.testing.assert_allclose(res.policy_sums["pv_net_cf"].sum(axis=1),
                               meta["pv_net_cf_by_scenario"], rtol=1e-14)


@pytest.mark.parametrize("name", ["premiums", "claims", "expenses", "commissions", "inv_income",
                                  "av_change", "net_cf", "pols_if"])
def test_monthly_cashflows_by_scenario(case, name):
    _, res, ref = case
    assert rel(res.totals[name], ref[f"cf_{name}"]).max() < 1e-12, name


def test_no_nans_anywhere(case):
    _, res, _ = case
    for k, v in res.policy_sums.items():
        assert np.isfinite(v).all(), k


def test_one_pass_equals_scenario_by_scenario():
    """Running all scenarios together gives exactly the per-scenario results."""
    mp = {k: v[:200] for k, v in cv.load_model_points().items()}
    together = cv.run_cashvalue(mp, scenarios=[1, 2, 3])
    for i, s in enumerate([1, 2, 3]):
        alone = cv.run_cashvalue(mp, scenarios=[s])
        for k in together.policy_sums:
            assert np.array_equal(together.policy_sums[k][i], alone.policy_sums[k][0]), (k, s)


def test_numpy_reference_engine_agrees():
    mp = {k: v[:150] for k, v in cv.load_model_points("model_point_inforce_1000.csv").items()}
    a = cv.run_cashvalue(mp, scenarios=[1, 2])
    b = cv.run_cashvalue(mp, scenarios=[1, 2], engine="numpy")
    for k in a.policy_sums:
        assert rel(a.policy_sums[k], b.policy_sums[k]).max() < 1e-11, k
