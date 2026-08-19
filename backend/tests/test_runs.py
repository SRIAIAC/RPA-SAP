import time

from tests.conftest import auth_headers


def test_workflow_run_lifecycle(client):
    headers = auth_headers(client, "admin")
    workflows = client.get("/api/workflows", headers=headers).json()
    assert len(workflows) > 0
    workflow = workflows[0]

    resp = client.post(f"/api/runs?workflow_id={workflow['id']}", headers=headers)
    assert resp.status_code == 201
    run = resp.json()
    assert run["status"] == "Running"

    # poll status until it finishes (background task runs ~1s per step)
    deadline = time.time() + 30
    final = run
    while time.time() < deadline:
        resp2 = client.get(f"/api/runs/{run['id']}", headers=headers)
        assert resp2.status_code == 200
        final = resp2.json()
        if final["status"] in ("Completed", "Exception"):
            break
        time.sleep(1)

    assert final["status"] in ("Completed", "Exception")
    assert final["result_summary"]
