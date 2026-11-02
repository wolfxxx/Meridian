"""Independent implementation of the SA family funeral valuation: plain Python loops.

Written from the product description (one policy at a time, month by month, explicit
in-force bookkeeping per life) rather than from Meridian's formulas, to check Meridian's
``lives`` mechanics and the BEL end to end. Deliberately slow and simple.
"""

from __future__ import annotations

import math

from . import sa_funeral as f


def bel_one_policy(lives: list[dict], basis: list[float], years: int = 50) -> float:
    """BEL (rand) of one policy: PV(claims + expenses + commission) - PV(premiums).

    ``lives``: dicts with role, sex, age, cover, premium; the main member is the role "main".
    Policy duration is the same for all lives (``duration_mth``).
    """
    tb = f.tables()
    q_tab = tb["mortality"].values            # [sex][age]
    loading = dict(zip(f.ROLES, tb["role_loading"].values))
    lapse = list(tb["lapse"].values)
    spot = list(tb["spot"].values)
    mort_mult, cat_add, lapse_mult, mass, exp_mult, infl_add = basis
    duration = lives[0]["duration_mth"]

    def q_month(life, t):
        age = life["age"] + t // 12
        q = q_tab[0 if life["sex"] == "M" else 1][min(age, 120)] * loading[life["role"]] * mort_mult
        q += cat_add if t < 12 else 0.0
        return 1 - (1 - min(1.0, q)) ** (1 / 12)

    def covered(life, t):
        return not (life["role"] == "child" and life["age"] + t // 12 >= f.CHILD_COVER_ENDS)

    def disc(month):
        return (1 + spot[min(month // 12, len(spot) - 1)]) ** (-month / 12)

    main = next(lv for lv in lives if lv["role"] == "main")
    others = [lv for lv in lives if lv is not main]
    policy_in_force = 1.0 - mass                  # mass lapse at the valuation date
    alive = [1.0 for _ in others]                 # given the policy is in force
    bel = 0.0
    for t in range(12 * years):
        infl = (1 + f.EXPENSE_INFLATION + infl_add) ** (t / 12)
        premium = deaths_count = claims = 0.0
        # main member: covered while the policy is in force
        qm = q_month(main, t)
        premium += policy_in_force * main["premium"]
        deaths_count += policy_in_force * qm
        claims += policy_in_force * qm * main["cover"]
        # other lives
        for i, lv in enumerate(others):
            if not covered(lv, t):
                alive[i] = 0.0
            exposure = policy_in_force * alive[i]
            q = q_month(lv, t)
            premium += exposure * lv["premium"]
            deaths_count += exposure * q
            claims += exposure * q * lv["cover"]
            alive[i] *= (1 - q)
        expenses = (policy_in_force * f.EXPENSE_PER_POLICY + deaths_count * f.CLAIM_EXPENSE) * infl * exp_mult
        commission = f.COMMISSION * premium
        bel += claims * disc(t + 1) + (expenses + commission - premium) * disc(t)
        # end of month: main member deaths end the policy, then lapses
        year = (duration + t) // 12
        w = min(1.0, lapse[min(year, len(lapse) - 1)] * lapse_mult)
        policy_in_force *= (1 - qm) * (1 - (1 - (1 - w) ** (1 / 12)))
    return bel


def check_policy(lives_rows: dict, policy_id: str, basis_name: str) -> float:
    idx = [i for i, p in enumerate(lives_rows["policy_id"]) if p == policy_id]
    lives = [{k: (lives_rows[k][i].item() if hasattr(lives_rows[k][i], "item") else lives_rows[k][i])
              for k in ["role", "sex", "age", "cover", "premium", "duration_mth"]} for i in idx]
    for lv in lives:
        lv["age"] = int(lv["age"])
        lv["duration_mth"] = int(lv["duration_mth"])
    return bel_one_policy(lives, f.BASES[basis_name])


if __name__ == "__main__":  # pragma: no cover
    rows = f.synthetic_lives(5)
    for pid in sorted(set(rows["policy_id"])):
        print(pid, round(check_policy(rows, pid, "base"), 6), math.nan)
