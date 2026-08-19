from tests.conftest import auth_headers


def test_manager_cannot_list_other_departments_users(client):
    # rahul.verma is Maintenance Manager - below Senior Manager, should be 403
    # (avoid asha.rao here: the lockout test in test_auth.py locks that account)
    headers = auth_headers(client, "rahul.verma")
    resp = client.get("/api/admin/users", headers=headers)
    assert resp.status_code == 403


def test_dept_head_only_sees_own_department_users(client):
    # neha.kapoor is Procurement Department Head
    headers = auth_headers(client, "neha.kapoor")
    resp = client.get("/api/admin/users", headers=headers)
    assert resp.status_code == 200
    users = resp.json()
    assert len(users) > 0
    assert all(u["department"] == "Procurement" for u in users)


def test_dept_head_cannot_manage_other_department(client):
    # neha.kapoor (Procurement Dept Head) tries to update a Maintenance user
    headers = auth_headers(client, "neha.kapoor")
    # rahul.verma is Maintenance Manager, id lookup via admin list from a maintenance dept head
    maint_headers = auth_headers(client, "suresh.iyer")
    maint_users = client.get("/api/admin/users", headers=maint_headers).json()
    rahul = next(u for u in maint_users if u["username"] == "rahul.verma")

    resp = client.patch(f"/api/admin/users/{rahul['id']}", json={"full_name": "Hacked Name"}, headers=headers)
    assert resp.status_code == 403


def test_admin_sees_all_departments(client):
    headers = auth_headers(client, "admin")
    resp = client.get("/api/admin/users", headers=headers)
    assert resp.status_code == 200
    depts = {u["department"] for u in resp.json()}
    assert "Procurement" in depts
    assert "Maintenance" in depts
