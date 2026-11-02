"""Editing formulas in the app, and keeping the user's work between sessions."""

import json
import time

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from meridian.app.server import create_app  # noqa: E402


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("MERIDIAN_HOME", str(tmp_path))
    return tmp_path


def run(client, model, options=None):
    rid = client.post(f"/api/models/{model}/runs", json={"options": options or {}}).json()["id"]
    end = time.time() + 120
    while time.time() < end:
        r = client.get(f"/api/runs/{rid}").json()
        if r["status"] in ("done", "failed"):
            assert r["status"] == "done", r["error"]
            return r
        time.sleep(0.1)
    raise AssertionError("timeout")


def spec(client, model, name):
    return next(v for v in client.get(f"/api/models/{model}").json()["variables_spec"] if v["name"] == name)


# ---- formulas ----------------------------------------------------------------------------------

def test_check_reports_errors_with_position(home):
    c = TestClient(create_app())
    r = c.post("/api/models/funeral/formulas/q_month/check", json={"formula": "q_anual / 12"}).json()
    assert not r["ok"] and r["col"] == 0 and "Did you mean q_annual?" in r["error"]
    r = c.post("/api/models/funeral/formulas/policy_if/check", json={"formula": "policy_if * 1"}).json()
    assert not r["ok"] and "Circular dependency" in r["error"] and "name[t-1]" in r["error"]
    assert c.post("/api/models/funeral/formulas/nope/check", json={"formula": "1"}).status_code == 404


def test_check_previews_before_and_after(home):
    c = TestClient(create_app())
    r = c.post("/api/models/funeral/formulas/q_month/check", json={"formula": "q_annual / 12 * 1.5"}).json()
    assert r["ok"] and r["refs"] == [["q_annual", 0]] and not r["unchanged"]
    names = [s["name"] for s in r["preview"]["series"]]
    assert names == ["q_month", "bel"]
    q = r["preview"]["series"][0]
    assert q["changed"] > 0 and q["after"][0] > q["before"][0] and q["invalid_from"] is None


def test_edit_run_and_revert(home):
    c = TestClient(create_app())
    base = run(c, "term")
    d = c.put("/api/models/term/formulas/claims", json={"formula": "pols_death * mp.sum_assured * 1.1"}).json()
    v = next(v for v in d["variables_spec"] if v["name"] == "claims")
    assert v["edited"] and v["formula"] == "pols_death * mp.sum_assured * 1.1" and v["original"]
    assert d["modified_formulas"] == ["claims"]
    r = run(c, "term")
    assert r["label"] == "What-if: formula claims" and r["modified_formulas"] == ["claims"]
    # premiums are re-priced on the edited model (lifelib prices first), so they rise with claims
    assert r["kpis"][3]["value"] > base["kpis"][3]["value"]
    assert c.put("/api/models/term/formulas/claims", json={"formula": "claims[t-1] +"}).status_code == 400
    c.delete("/api/models/term/formulas/claims")
    assert not spec(c, "term", "claims")["edited"]
    assert run(c, "term")["kpis"] == base["kpis"]


def test_saving_the_original_text_clears_the_edit(home):
    c = TestClient(create_app())
    orig = spec(c, "funeral", "q_month")["formula"]
    c.put("/api/models/funeral/formulas/q_month", json={"formula": "q_annual / 12"})
    assert spec(c, "funeral", "q_month")["edited"]
    c.put("/api/models/funeral/formulas/q_month", json={"formula": orig})
    assert not spec(c, "funeral", "q_month")["edited"]


def test_validation_still_checks_the_original_model(home):
    c = TestClient(create_app())
    c.put("/api/models/funeral/formulas/q_month", json={"formula": "q_annual / 6"})
    c.post("/api/models/funeral/validation")
    end = time.time() + 120
    while (v := c.get("/api/models/funeral/validation").json())["status"] not in ("done", "failed"):
        assert time.time() < end
        time.sleep(0.2)
    assert all(ch["passed"] for g in v["result"] for ch in g["checks"])


# ---- keeping work between sessions -------------------------------------------------------------

def test_work_is_restored_after_a_restart(home):
    c = TestClient(create_app())
    t = c.get("/api/models/term/tables/disc_rate_ann").json()
    c.put("/api/models/term/tables/disc_rate_ann", json={"values": [x + 0.01 for x in t["values"]]})
    c.put("/api/models/term/formulas/claims", json={"formula": "pols_death * mp.sum_assured * 1.05"})
    text = c.get("/api/models/term/data/export.csv").text
    c.post("/api/models/term/data/import", json={"csv": "\n".join(text.splitlines()[:301]), "name": "mine.csv", "apply": True})
    r = run(c, "term")

    c2 = TestClient(create_app())          # a new session
    d = c2.get("/api/models/term").json()
    assert d["modified_tables"] == ["disc_rate_ann"] and d["modified_formulas"] == ["claims"]
    assert d["data_source"]["name"] == "mine.csv" and d["policies"] == 300
    runs = c2.get("/api/models/term/runs").json()
    assert [x["id"] for x in runs] == [r["id"]] and runs[0]["restored"]
    assert c2.get(f"/api/runs/{r['id']}").json()["result"]["kpis"] == r["result"]["kpis"]
    assert run(c2, "term")["result"]["kpis"] == r["result"]["kpis"]   # same state, same answer
    assert c2.get("/api/notices").json() == []

    c2.delete(f"/api/runs/{r['id']}")
    c2.post("/api/models/term/data/reset")
    c2.post("/api/models/term/formulas/reset")
    c2.post("/api/models/term/tables/reset")
    c3 = TestClient(create_app())
    d = c3.get("/api/models/term").json()
    assert not d["modified_tables"] and not d["modified_formulas"] and d["data_source"] is None
    assert r["id"] not in [x["id"] for x in c3.get("/api/models/term/runs").json()]


def test_unusable_saved_work_is_skipped_and_reported(home):
    d = home / "workspace" / "funeral"
    d.mkdir(parents=True)
    (d / "formulas.json").write_text(json.dumps({"q_month": "q_monthly_rate * 2", "deaths": "life_if * q_month"}))
    runs = home / "workspace" / "runs"
    runs.mkdir()
    (runs / "abc.json").write_text(json.dumps({"id": "abc", "model": "funeral", "label": "Base run", "status": "running",
                                               "started": 1.0, "finished": None, "kpis": None, "result": None}))
    c = TestClient(create_app())
    notes = c.get("/api/notices").json()
    assert len(notes) == 1 and "q_month" in notes[0] and "q_monthly_rate" in notes[0]
    assert c.get("/api/models/funeral").json()["modified_formulas"] == ["deaths"]
    r = c.get("/api/runs/abc").json()
    assert r["status"] == "failed" and "closed" in r["error"]
    assert c.get("/api/notices").json() == []          # shown once
