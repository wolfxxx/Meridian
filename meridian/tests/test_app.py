"""The app's local service: workspace, models, assumptions, data, runs, explain, validation."""

import time

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from meridian.app.server import create_app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    return TestClient(create_app())


def wait(client, url, key="status", done=("done", "failed"), timeout=60):
    end = time.time() + timeout
    while time.time() < end:
        r = client.get(url).json()
        if r[key] in done:
            return r
        time.sleep(0.1)
    raise AssertionError(f"timed out waiting for {url}")


def test_workspace_lists_three_models(client):
    ids = [m["id"] for m in client.get("/api/workspace").json()]
    assert ids == ["term", "savings", "funeral"]


def test_model_detail_has_variables_tables_and_dependencies(client):
    d = client.get("/api/models/term").json()
    names = [v["name"] for v in d["variables_spec"]]
    assert names.index("pols_if") < names.index("claims")       # calculation order
    claims = next(v for v in d["variables_spec"] if v["name"] == "claims")
    assert ["pols_death", 0] in claims["refs"] and claims["inputs"] == ["sum_assured"]
    deaths = next(v for v in d["variables_spec"] if v["name"] == "pols_death")
    assert ["claims", 0] in deaths["used_by"]


def test_table_edit_validation_and_reset(client):
    t = client.get("/api/models/term/tables/mort_table").json()
    assert t["shape"] == [103, 6] and t["dims"][0]["labels"][0] == "18"
    bad = client.put("/api/models/term/tables/mort_table", json={"values": [[1.0]]})
    assert bad.status_code == 400
    vals = [[v * 1.1 for v in row] for row in t["values"]]
    assert client.put("/api/models/term/tables/mort_table", json={"values": vals}).json()["modified"]
    assert client.get("/api/workspace").json()[0]["modified_tables"] == ["mort_table"]
    locked = client.put("/api/models/savings/tables/is_wl", json={"values": [1, 1, 1, 1]})
    assert locked.status_code == 400
    client.post("/api/models/term/tables/reset")
    assert client.get("/api/workspace").json()[0]["modified_tables"] == []


def test_data_paging_and_search(client):
    page = client.get("/api/models/funeral/data?offset=0&limit=5").json()
    assert page["total"] > 20_000 and len(page["rows"]) == 5
    hit = client.get("/api/models/funeral/data?search=FUN0000003").json()
    assert hit["total"] >= 1 and all(r["policy_id"] == "FUN0000003" for r in hit["rows"])


def test_run_lifecycle_and_results(client):
    r = client.post("/api/models/term/runs", json={"options": {}}).json()
    assert r["status"] in ("queued", "running", "done")
    done = wait(client, f"/api/runs/{r['id']}?full=false")
    assert done["status"] == "done", done["error"]
    full = client.get(f"/api/runs/{r['id']}").json()
    assert full["result"]["kpis"][0]["value"] == pytest.approx(14_489_630.534601538, rel=1e-12)
    assert len(full["result"]["series"]["premiums"]["values"]) == 241


def test_explain_a_family_policy(client):
    ex = client.get("/api/models/funeral/explain?policy=1").json()
    assert ex["family"] and len(ex["values"]["claims"]) == ex["steps"]
    assert client.get("/api/models/funeral/explain?policy=99999999").status_code == 400


def test_validation_runs_and_passes(client):
    client.post("/api/models/term/validation")
    v = wait(client, "/api/models/term/validation")
    assert v["status"] == "done"
    assert all(c["passed"] for c in v["result"][0]["checks"])
