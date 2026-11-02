"""What-if levers, sensitivities, policy-data import/export, result export and settings."""

import time

import numpy as np
import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from meridian.app.dataio import Field, check_csv  # noqa: E402
from meridian.app.server import create_app  # noqa: E402


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    mp = pytest.MonkeyPatch()
    mp.setenv("MERIDIAN_HOME", str(tmp_path_factory.mktemp("home")))
    yield TestClient(create_app())
    mp.undo()


def run(client, model, options=None, **kw):
    r = client.post(f"/api/models/{model}/runs", json={"options": options or {}, **kw})
    assert r.status_code == 200, r.text
    rid = r.json()["id"]
    end = time.time() + 120
    while time.time() < end:
        out = client.get(f"/api/runs/{rid}").json()
        if out["status"] in ("done", "failed"):
            assert out["status"] == "done", out["error"]
            return out
        time.sleep(0.1)
    raise AssertionError("run timed out")


def kpi(run_, label):
    return next(k["value"] for k in run_["result"]["kpis"] if k["label"] == label)


# ---- levers ------------------------------------------------------------------------------------

def test_detail_lists_levers_sensitivities_and_schema(client):
    d = client.get("/api/models/funeral").json()
    assert [lv["key"] for lv in d["levers"]] == ["mortality", "lapse", "interest"]
    assert len(d["sensitivities"]) == 6
    assert [f["key"] for f in d["input_schema"]][:3] == ["policy_id", "role", "sex"]


def test_term_mortality_lever_keeps_premiums_and_raises_claims(client):
    base = run(client, "term")
    up = run(client, "term", {"levers": {"mortality": 10}}, group="g1")
    assert up["label"] == "What-if: Mortality +10%" and up["levers"] == {"mortality": 10.0}
    assert up["group"] == "g1"
    # premiums are as charged, so they do not move; claims rise and profit falls
    assert kpi(up, "Average premium") == kpi(base, "Average premium")
    pv = {r["label"]: r["value"] for r in up["result"]["pv_table"]}
    pv0 = {r["label"]: r["value"] for r in base["result"]["pv_table"]}
    assert pv["Claims"] > pv0["Claims"]
    assert kpi(up, "PV of net cash flow") < kpi(base, "PV of net cash flow")


def test_interest_lever_shifts_discounting(client):
    base = run(client, "term")
    lo = run(client, "term", {"levers": {"interest": -1}})
    assert "Discount rate −1 pp" in lo["label"]
    assert abs(kpi(lo, "PV of premiums")) > abs(kpi(base, "PV of premiums"))


def test_funeral_lapse_lever_changes_bel(client):
    base = run(client, "funeral")
    up = run(client, "funeral", {"levers": {"lapse": 25}})
    assert kpi(up, "Best-estimate liability") != kpi(base, "Best-estimate liability")


def test_bad_levers_are_rejected(client):
    assert client.post("/api/models/term/runs", json={"options": {"levers": {"mortality": 500}}}).status_code == 400
    assert client.post("/api/models/term/runs", json={"options": {"levers": {"lapse": 5}}}).status_code == 400


def test_probability_scaling_keeps_terminal_rate():
    from meridian.app.catalog import make_catalog
    e = make_catalog()["savings"]
    q = e.run_overrides({"levers": {"mortality": -20}})["mort_table"].values
    q0 = e.base_tables()["mort_table"].values
    assert np.all(q[q0 >= 1] == 1) and np.allclose(q[q0 < 1], q0[q0 < 1] * 0.8)


# ---- import / export ---------------------------------------------------------------------------

def test_export_then_import_roundtrip_and_reset(client):
    text = client.get("/api/models/term/data/export.csv").text
    assert text.splitlines()[0] == "point_id,sex,age_at_entry,policy_term,policy_count,sum_assured"
    small = "\n".join(text.splitlines()[:501])
    rep = client.post("/api/models/term/data/import", json={"csv": small, "name": "mine.csv"}).json()
    assert rep["ok"] and rep["rows"] == 500 and not rep["missing"] and len(rep["preview"]) == 8
    assert client.get("/api/models/term").json()["policies"] == 10_000      # preview changes nothing
    rep = client.post("/api/models/term/data/import", json={"csv": small, "name": "mine.csv", "apply": True}).json()
    assert rep["applied"]
    d = client.get("/api/models/term").json()
    assert d["policies"] == 500 and d["data_source"]["name"] == "mine.csv"
    r = run(client, "term")
    assert r["result"]["policies"] == 500 and r["data"] == "mine.csv"
    client.post("/api/models/term/data/reset")
    assert client.get("/api/models/term").json()["policies"] == 10_000


def test_template_has_header_and_examples(client):
    lines = client.get("/api/models/funeral/data/template.csv").text.splitlines()
    assert lines[0] == "policy_id,role,sex,age,cover,premium,duration_mth" and len(lines) == 6


def test_import_reports_errors_with_rows(client):
    bad = "Policy,Gender,Age,Term,Count,SA\n1,M,40,10,1,100000\n2,X,40,10,1,abc\n3,F,15,10,1,5000\n"
    rep = client.post("/api/models/term/data/import", json={"csv": bad}).json()
    assert not rep["ok"] and rep["error_count"] == 3
    msgs = {(e["row"], e["column"]): e["message"] for e in rep["errors"]}
    assert msgs[(3, "Sex")] == "must be one of M, F"
    assert msgs[(3, "Sum assured")] == "is not a number"
    assert msgs[(4, "Age at entry")] == "must be at least 18"
    r = client.post("/api/models/term/data/import", json={"csv": bad, "apply": True})
    assert r.status_code == 400


def test_import_reports_missing_columns(client):
    rep = client.post("/api/models/term/data/import", json={"csv": "point_id,sex\n1,M\n"}).json()
    assert not rep["ok"] and {m["key"] for m in rep["missing"]} == {"age_at_entry", "policy_term", "policy_count", "sum_assured"}


def test_funeral_policy_rules(client):
    text = ("policy_id;role;sex;age;cover;premium;duration_mth\n"
            "P1;main;F;40;R 20 000;45,50;12\n"
            "P1;child;M;5;10000;5,25;12\n"
            "P2;spouse;M;41;20000;40;3\n")
    rep = client.post("/api/models/funeral/data/import", json={"csv": text}).json()
    assert not rep["ok"]
    assert rep["errors"] == [{"row": 4, "column": "Policy", "value": "P2", "message": "has no main member"}]


def test_semicolon_and_decimal_comma_are_understood():
    schema = [Field("a", "A", "number"), Field("b", "B", "text", choices=["x", "y"])]
    rep = check_csv("A;B\n1 234,5;X\nR 10;y\n", schema)
    assert rep["ok"] and list(rep["columns"]["a"]) == [1234.5, 10.0] and list(rep["columns"]["b"]) == ["x", "y"]


def test_run_export_csv(client):
    r = run(client, "funeral")
    text = client.get(f"/api/runs/{r['id']}/export.csv").text
    assert text.startswith("Meridian results,Base run") and "Technical provisions" in text and "\nMonth," in text


# ---- settings ----------------------------------------------------------------------------------

def test_settings_persist_and_ignore_unknown(client):
    assert client.get("/api/settings").json() == {"theme": None, "tour_done": False}
    out = client.put("/api/settings", json={"tour_done": True, "theme": "dark", "evil": 1}).json()
    assert out == {"theme": "dark", "tour_done": True}
    assert client.get("/api/settings").json() == out
    assert client.put("/api/settings", json={"tour_done": "yes"}).json()["tour_done"] is True


def test_policy_rules_are_reported_alongside_cell_errors(client):
    text = ("policy_id,role,sex,age,cover,premium,duration_mth\n"
            "P1,main,X,40,20000,45,12\n"
            "P2,spouse,M,41,20000,40,3\n")
    rep = client.post("/api/models/funeral/data/import", json={"csv": text}).json()
    assert {(e["row"], e["message"]) for e in rep["errors"]} == {(2, "must be one of M, F"), (3, "has no main member")}


def test_savings_surrender_and_loading_levers(client):
    base = run(client, "savings")
    r = run(client, "savings", {"levers": {"surrender": -50, "loading": 50}})
    assert r["label"] == "What-if: Surrender charges \u221250%, Premium loading +50%"
    assert kpi(r, "Mean PV of net cash flow") != kpi(base, "Mean PV of net cash flow")
