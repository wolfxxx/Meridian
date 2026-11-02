"""South African family funeral cover, valued on a SAM-style best-estimate basis.

**Product.** One policy covers up to 8 lives: the main member, a spouse, up to four children and
up to two extended-family members (parents, in-laws). Each life has its own cover amount and
monthly premium. The policy stays in force until it lapses or the main member dies; a death
of any other life pays that life's cover and stops its premium; children's cover ends at 21.

**Model.** Each life is a lane; the 8 lanes of a policy form one group (``Model(lives=8)``).
Policy-level quantities use ``sum_lives``: the main member's mortality, applied to every
life's cover, comes from ``sum_lives(where(is_main, q, 0))``.

**Valuation.** Best-estimate liability (BEL) = PV of claims, expenses and commission less PV
of premiums. SAM-style life underwriting stresses — mortality, lapse up / down / mass, expense,
catastrophe — are separate runs with a different assumption set (a Prophet user would call
these run numbers); the SCR aggregates them with the standard-formula life correlation
matrix, and the risk margin is a 6% cost of capital on SCRs projected in proportion to the
number of policies in force.

**All assumptions are illustrative.** The mortality table is a Gompertz-Makeham curve shaped
to resemble South African population mortality (with elevated young-adult mortality); it is
not an ASSA or SA85-90 table. Lapse, expense and economic assumptions are plausible round
numbers. The SAM calculation is simplified (stresses applied at portfolio level, risk margin
by the proportional method).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ..dsl import Model, floor, minimum, sum_lives, t, where
from ..lives import group_lives
from ..runner import Results, run
from ..tables import Table

LIVES = 8
ROLES = ["main", "spouse", "child", "extended", "none"]
CHILD_COVER_ENDS = 21
COMMISSION = 0.12            # as-and-when, % of premium
EXPENSE_PER_POLICY = 18.0    # rand per policy per month
CLAIM_EXPENSE = 350.0        # rand per claim
EXPENSE_INFLATION = 0.055    # p.a.
COST_OF_CAPITAL = 0.06
MASS_LAPSE = 0.40

# Assumption sets (bases), one per run: a Prophet user would call these run numbers.
# Parameters are looked up by name, e.g. tb.basis["mass_lapse"].
BASIS_PARAMS = ["mortality_mult", "cat_add", "lapse_mult", "mass_lapse", "expense_mult", "inflation_add"]
B_MORT, B_CAT, B_LAPSE, B_MASS, B_EXP, B_INFL = BASIS_PARAMS
BASES = {
    "base":      [1.00, 0.0000, 1.0, 0.0, 1.00, 0.00],
    "mortality": [1.15, 0.0000, 1.0, 0.0, 1.00, 0.00],
    "lapse_up":  [1.00, 0.0000, 1.5, 0.0, 1.00, 0.00],
    "lapse_down": [1.00, 0.0000, 0.5, 0.0, 1.00, 0.00],
    "mass_lapse": [1.00, 0.0000, 1.0, MASS_LAPSE, 1.00, 0.00],
    "expense":   [1.00, 0.0000, 1.0, 0.0, 1.10, 0.01],
    "catastrophe": [1.00, 0.0015, 1.0, 0.0, 1.00, 0.00],
}
STRESS_LABELS = {
    "mortality": "Mortality +15%",
    "lapse_up": "Lapse rates +50%",
    "lapse_down": "Lapse rates -50%",
    "mass_lapse": f"Mass lapse {MASS_LAPSE:.0%} at the valuation date",
    "expense": "Expenses +10%, expense inflation +1% p.a.",
    "catastrophe": "Catastrophe: +1.5 per mille mortality for 12 months",
}
# Standard-formula life correlations (mortality, lapse, expense, catastrophe).
LIFE_RISKS = ["mortality", "lapse", "expense", "catastrophe"]
LIFE_CORR = np.array([
    [1.00, 0.00, 0.25, 0.25],
    [0.00, 1.00, 0.50, 0.25],
    [0.25, 0.50, 1.00, 0.25],
    [0.25, 0.25, 0.25, 1.00],
])


def build(years: int = 50) -> Model:
    m = Model("sa_family_funeral", n_steps=12 * years, lives=LIVES)
    v, mp, tb = m.v, m.mp, m.tables

    # ---- who is covered --------------------------------------------------------------------
    @m.var
    def is_main():
        return (mp.role == "main") * mp.life_active

    @m.var
    def age():
        """Age last birthday, advancing each projection year."""
        return mp.age + floor(t / 12)

    @m.var
    def policy_year():
        return floor((mp.duration_mth + t) / 12)

    @m.var
    def covered():
        """1 while this life can claim: real life, and children only until age 21."""
        return mp.life_active * where(mp.role == "child", v.age < CHILD_COVER_ENDS, 1.0)

    # ---- decrements ------------------------------------------------------------------------
    @m.var
    def q_annual():
        """Mortality: illustrative table by sex and age, loaded by role; basis stress applied."""
        base = tb.mortality[mp.sex, v.age] * tb.role_loading[mp.role] * tb.basis[B_MORT]
        return minimum(1.0, base + where(t < 12, tb.basis[B_CAT], 0.0))

    @m.var
    def q_month():
        return 1 - (1 - v.q_annual) ** (1 / 12)

    @m.var
    def main_q_month():
        """The main member's monthly mortality, the same on every life of the policy."""
        return sum_lives(where(v.is_main == 1, v.q_month, 0.0))

    @m.var
    def lapse_month():
        return 1 - (1 - minimum(1.0, tb.lapse[v.policy_year] * tb.basis[B_LAPSE])) ** (1 / 12)

    @m.var(init=0.0)
    def policy_if():
        """Probability the policy is still in force at the start of month t."""
        return where(t == 0, 1 - tb.basis[B_MASS],
                     v.policy_if.lag(1) * (1 - v.main_q_month.lag(1)) * (1 - v.lapse_month.lag(1)))

    @m.var(init=0.0)
    def life_if():
        """Probability this life is alive and covered, given the policy is in force.

        The main member's survival is already part of policy_if, so it is 1 for them."""
        others = where(t == 0, 1.0, v.life_if.lag(1) * (1 - v.q_month.lag(1)))
        return where(v.is_main == 1, mp.life_active, others * v.covered)

    @m.var(total=True)
    def exposure():
        return v.policy_if * v.life_if

    @m.var(total=True)
    def deaths():
        return v.exposure * v.q_month

    @m.var(total=True)
    def policies_if():
        """Policies in force (counted on the main member's lane)."""
        return where(v.is_main == 1, v.policy_if, 0.0)

    # ---- cash flows (rand) ---------------------------------------------------------------------
    @m.var
    def inflation_index():
        return (1 + EXPENSE_INFLATION + tb.basis[B_INFL]) ** (t / 12)

    @m.var(total=True)
    def premiums():
        return v.exposure * mp.premium

    @m.var(total=True)
    def claims():
        return v.deaths * mp.cover

    @m.var(total=True)
    def commission():
        return COMMISSION * v.premiums

    @m.var(total=True)
    def expenses():
        per_policy = v.policies_if * EXPENSE_PER_POLICY
        per_claim = v.deaths * CLAIM_EXPENSE
        return (per_policy + per_claim) * v.inflation_index * tb.basis[B_EXP]

    @m.var(total=True)
    def net_outgo():
        return v.claims + v.expenses + v.commission - v.premiums

    # ---- discounting (illustrative SA nominal risk-free curve) ---------------------------------
    @m.var
    def v_start():
        return (1 + tb.spot[floor(t / 12)]) ** (-t / 12)

    @m.var
    def v_end():
        return (1 + tb.spot[floor((t + 1) / 12)]) ** (-(t + 1) / 12)

    @m.var(policy_sum=True)
    def bel():
        """Discounted outgo; summed over time it is this life's share of the BEL."""
        return v.claims * v.v_end + (v.expenses + v.commission - v.premiums) * v.v_start

    @m.var(policy_sum=True)
    def pv_premiums():
        return v.premiums * v.v_start

    @m.var(policy_sum=True)
    def pv_claims():
        return v.claims * v.v_end

    return m


# ---- assumptions ---------------------------------------------------------------------------------

def mortality_table() -> Table:
    """Illustrative Gompertz-Makeham mortality, ages 0-120, by sex (not an actual SA table)."""
    ages = np.arange(0, 121)
    q = {}
    for sex, (a, b, c, hump) in {"M": (0.0012, 0.000045, 1.098, 0.0045),
                                 "F": (0.0008, 0.000030, 1.100, 0.0035)}.items():
        mu = a + b * c ** ages + hump * np.exp(-((ages - 35) / 12.0) ** 2)   # young-adult hump
        mu = np.where(ages < 15, 0.0012 + 0.004 * np.exp(-ages), mu)          # childhood
        q[sex] = np.minimum(1.0, 1 - np.exp(-mu))
        q[sex][ages >= 110] = 1.0
    return Table(np.vstack([q["M"], q["F"]]), dims=[["M", "F"], 0])


def tables(basis: str = "base") -> dict[str, Table]:
    years = np.arange(0, 61)
    spot = np.minimum(0.0745 + 0.0022 * years, 0.105)    # illustrative SA nominal curve
    return {
        "mortality": mortality_table(),
        "role_loading": Table([1.00, 1.00, 1.00, 1.30, 0.0], dims=[ROLES]),
        "lapse": Table([0.35, 0.25, 0.18, 0.14, 0.12, 0.10, 0.09, 0.08]),  # by policy year
        "spot": Table(spot),
        "basis": Table(BASES[basis], dims=[BASIS_PARAMS]),
    }


# ---- synthetic portfolio --------------------------------------------------------------------------

def synthetic_lives(n_policies: int, seed: int = 27) -> dict[str, np.ndarray]:
    """One row per life, as an administration system would hold it."""
    rng = np.random.default_rng(seed)
    q = mortality_table()
    plans = np.array([10_000, 15_000, 20_000, 30_000, 50_000])
    rows = {k: [] for k in ["policy_id", "role", "sex", "age", "cover", "premium", "duration_mth"]}

    def rate(role, sex, age):
        """Monthly premium per rand of cover: loaded expected cost at age + 5 (illustrative)."""
        qa = q.values[0 if sex == "M" else 1, min(age + 5, 120)]
        return float(qa) / 12 * (1.30 if role == "extended" else 1.0) * 1.9 + 0.00008

    for p in range(n_policies):
        main_age = int(np.clip(rng.normal(44, 11), 18, 70))
        main_sex = rng.choice(["M", "F"])
        cover = int(rng.choice(plans, p=[0.30, 0.25, 0.22, 0.15, 0.08]))
        dur = int(min(rng.exponential(30), 180))
        members = [("main", main_sex, main_age, cover)]
        if rng.random() < 0.62:
            sp_age = int(np.clip(main_age + rng.normal(0, 4), 18, 80))
            members.append(("spouse", "F" if main_sex == "M" else "M", sp_age, cover))
        for _ in range(min(rng.poisson(1.3), 4)):
            members.append(("child", rng.choice(["M", "F"]), int(rng.integers(0, 21)), cover // 2))
        for _ in range(rng.choice([0, 1, 2], p=[0.55, 0.30, 0.15])):
            members.append(("extended", rng.choice(["M", "F"]),
                            int(np.clip(main_age + rng.normal(26, 6), 40, 90)), cover // 2))
        for role, sex, age, cov in members:
            rows["policy_id"].append(f"FUN{p:07d}")
            rows["role"].append(role)
            rows["sex"].append(sex)
            rows["age"].append(age)
            rows["cover"].append(cov)
            rows["premium"].append(round(cov * rate(role, sex, age), 2))
            rows["duration_mth"].append(dur)
    return {k: np.array(v) for k, v in rows.items()}


def model_points(lives_rows: dict) -> dict[str, np.ndarray]:
    """Group one-row-per-life data into 8 slots per policy (padding cannot produce NaN)."""
    return group_lives(lives_rows, "policy_id", LIVES, pad={"role": "none", "sex": "M"})


# ---- SAM valuation ------------------------------------------------------------------------------

@dataclass
class SamResult:
    bel: dict[str, float]                  # by basis
    scr: dict[str, float]                  # by risk module, plus "life"
    risk_margin: float
    technical_provisions: float
    bel_by_policy: np.ndarray              # base BEL per policy
    base: Results                          # base projection
    projected_scr: np.ndarray              # by year, for the risk margin
    seconds: float
    runs: int = 0
    notes: list[str] = field(default_factory=list)


def value(mp: dict, years: int = 50, engine: str = "rust",
          overrides: dict | None = None, progress=None, customize=None) -> SamResult:
    """SAM valuation: base + six stress bases. ``overrides`` replaces assumption tables in every
    basis (what-if runs); ``progress(done, total, label)`` is called after each run."""
    model = build(years)
    if customize is not None:  # e.g. formulas edited in the app
        model = customize(model)
    results = {}
    for i, name in enumerate(BASES):
        results[name] = run(model, mp, {**tables(name), **(overrides or {})}, engine=engine)
        if progress:
            progress(i + 1, len(BASES), name)
    bel = {name: float(r.policy_sums["bel"].sum()) for name, r in results.items()}
    d = {name: bel[name] - bel["base"] for name in bel}
    scr = {
        "mortality": max(d["mortality"], 0.0),
        "lapse": max(d["lapse_up"], d["lapse_down"], d["mass_lapse"], 0.0),
        "expense": max(d["expense"], 0.0),
        "catastrophe": max(d["catastrophe"], 0.0),
    }
    s = np.array([scr[k] for k in LIFE_RISKS])
    scr["life"] = float(np.sqrt(s @ LIFE_CORR @ s))
    base = results["base"]
    pols = base.totals["policies_if"][0]
    years_idx = np.arange(0, years) * 12
    driver = pols[years_idx]
    projected = scr["life"] * driver / driver[0]
    spot = {**tables(), **(overrides or {})}["spot"].values
    disc = (1 + spot[np.minimum(np.arange(1, years + 1), len(spot) - 1)]) ** (-np.arange(1, years + 1))
    rm = float(COST_OF_CAPITAL * np.sum(projected * disc))
    n_pol = len(mp["policy_id"]) // LIVES
    bel_pol = base.policy_sums["bel"][0].reshape(n_pol, LIVES).sum(axis=1)
    return SamResult(bel, scr, rm, bel["base"] + rm, bel_pol, base, projected,
                     sum(r.seconds for r in results.values()), runs=len(results),
                     notes=["Stresses are applied to the whole portfolio, not policy by policy.",
                            "Risk margin: SCR projected in proportion to policies in force."])
