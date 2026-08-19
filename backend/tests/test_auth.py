from tests.conftest import login


def test_login_success(client):
    resp = login(client, "admin", "Demo@123")
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["user"]["username"] == "admin"


def test_login_failure_wrong_password(client):
    resp = login(client, "admin", "wrong-password")
    assert resp.status_code == 401


def test_login_failure_unknown_user(client):
    resp = login(client, "nobody", "whatever")
    assert resp.status_code == 401


def test_login_lockout_after_5_failed_attempts(client):
    username = "asha.rao"
    for _ in range(5):
        resp = login(client, username, "wrong-password")
    # 5th failure should have locked the account
    assert resp.status_code == 429

    # further attempts, even with the correct password, are locked out
    resp = login(client, username, "Demo@123")
    assert resp.status_code == 403
    assert "locked" in resp.json()["detail"].lower()


def test_protected_route_rejects_missing_token(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_protected_route_rejects_invalid_token(client):
    resp = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert resp.status_code == 401


def test_protected_route_accepts_valid_token(client):
    resp = login(client, "admin", "Demo@123")
    token = resp.json()["access_token"]
    resp2 = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp2.status_code == 200
    assert resp2.json()["username"] == "admin"
