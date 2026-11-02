"""SA family funeral model: lives-within-a-policy mechanics, SAM valuation, reconciliations."""

import numpy as np
import pytest

import meridian as mr
from meridian.models import sa_funeral as f

from meridian.models import sa_funeral_check as ind


@pytest.fixture(scope="module")
def portfolio():
    rows = f.synthetic_lives(40, seed=5)
    return rows, f.model_points(rows)


def one_policy(members, duration=0):
    rows = {k: [] for k in ["policy_id", "role", "sex", "age", "cover", "premium", "duration_mth"]}
    for role, sex, age, cover, prem in members:
        for k, val in zip(rows, ["P1", role, sex, age, cover, prem, duration]):
            rows[k].append(val)
    return f.model_points({k: np.array(v) for k, v in rows.items()})


# ---- group_lives -----------------------------------------------------------------------------

def test_group_lives_pads_each_policy_to_eight_slots():
    rows = {"policy_id": np.array(["B", "A", "B", "A", "A"]), "role": np.array(["main", "main", "child", "spouse", "child"]),
            "age": np.array([40, 50, 10, 48, 12])}
    g = mr.group_lives(rows, "policy_id", 8, pad={"role": "none"})
    assert len(g["policy_id"]) == 16
    assert list(g["role"][:8]) == ["main", "child"] + ["none"] * 6            # policy B first (first seen)
    assert list(g["role"][8:11]) == ["main", "spouse", "child"]
    assert g["life_active"].tolist() == [1, 1, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0]
    assert g["policy_index"].tolist() == [0.0] * 8 + [1.0] * 8
    with pytest.raises(ValueError, match="allows 2"):
        mr.group_lives(rows, "policy_id", 2)


# ---- independent reconciliation ----------------------------------------------------------------

@pytest.mark.parametrize("basis", list(f.BASES))
def test_bel_matches_independent_loop_implementation(portfolio, basis):
    rows, mp = portfolio
    res = mr.run(f.build(), mp, f.tables(basis))
    bel_pol = res.policy_sums["bel"][0].reshape(-1, f.LIVES).sum(axis=1)
    pids = list(dict.fromkeys(rows["policy_id"]))
    ref = np.array([ind.check_policy(rows, pid, basis) for pid in pids])
    assert (np.abs(bel_pol - ref) / np.maximum(1.0, np.abs(ref))).max() < 1e-11


def test_rust_matches_numpy_reference(portfolio):
    _, mp = portfolio
    m = f.build(years=20)
    a, b = mr.run(m, mp, f.tables()), mr.run(m, mp, f.tables(), engine="numpy")
    for k in a.policy_sums:
        np.testing.assert_allclose(a.policy_sums[k], b.policy_sums[k], rtol=1e-11, atol=1e-6, err_msg=k)
    for k in a.totals:
        np.testing.assert_allclose(a.totals[k], b.totals[k], rtol=1e-11, atol=1e-6, err_msg=k)


def test_runs_per_chunk_and_matches_lockstep_bit_for_bit(portfolio):
    _, mp = portfolio
    m = f.build(years=10)
    assert set(mr.inspect(m)["classes"].values()) == {"C1"}
    a = mr.run(m, mp, f.tables())
    b = mr.run(m, mp, f.tables(), strategy="lockstep", chunk_size=24)
    assert (a.strategy, b.strategy) == ("per_chunk", "lockstep")
    for k in a.policy_sums:
        assert np.array_equal(a.policy_sums[k], b.policy_sums[k]), k


# ---- product mechanics ---------------------------------------------------------------------------

def test_main_member_death_ends_cover_for_everyone():
    # Main member aged 115: q = 1, so the policy ends after month 0.
    mp = one_policy([("main", "M", 115, 10_000, 100.0), ("spouse", "F", 40, 10_000, 20.0)])
    res = mr.run(f.build(years=2), mp, f.tables())
    cl = res.totals["claims"][0]
    assert cl[0] > 0                                              # claims in month 0
    assert np.all(cl[1:] == 0.0)                                  # nothing after the policy ends
    assert np.all(res.totals["premiums"][0][1:] == 0.0)


def test_childrens_cover_ends_at_21():
    mp = one_policy([("main", "F", 35, 20_000, 60.0), ("child", "M", 20, 10_000, 3.0)])
    tr = mr.trace(f.build(years=3), mp, f.tables(), life=1)
    assert np.all(tr.values["covered"][:12] == 1.0) and np.all(tr.values["covered"][12:] == 0.0)
    assert np.all(tr.values["claims"][12:] == 0.0)
    assert tr.values["main_q_month"][0] == mr.trace(f.build(years=3), mp, f.tables(), life=0).values["q_month"][0]


def test_padding_lanes_are_inert(portfolio):
    _, mp = portfolio
    res = mr.run(f.build(years=5), mp, f.tables(), keep_history=True)
    pad = mp["life_active"] == 0
    for name in ["exposure", "deaths", "claims", "premiums", "bel"]:
        h = res.history[name][:, 0, :]
        assert np.all(h[:, pad] == 0.0), name
        assert np.isfinite(h).all(), name


# ---- SAM aggregation -----------------------------------------------------------------------------

def test_sam_scr_and_risk_margin_follow_their_definitions(portfolio):
    _, mp = portfolio
    r = f.value(mp, years=50)
    d = {k: r.bel[k] - r.bel["base"] for k in r.bel}
    assert r.scr["lapse"] == max(d["lapse_up"], d["lapse_down"], d["mass_lapse"], 0.0)
    s = np.array([r.scr[k] for k in f.LIFE_RISKS])
    assert r.scr["life"] == pytest.approx(np.sqrt(s @ f.LIFE_CORR @ s), rel=1e-15)
    assert r.scr["life"] <= s.sum() + 1e-6                        # diversification
    assert r.risk_margin > 0 and r.projected_scr[0] == pytest.approx(r.scr["life"])
    assert r.technical_provisions == pytest.approx(r.bel["base"] + r.risk_margin)
    assert r.bel_by_policy.sum() == pytest.approx(r.bel["base"], rel=1e-12)
