import io
from datetime import datetime
from unittest.mock import patch

from PIL import Image

from tests.conftest import auth_headers
from app.services.gmail_import import ImportedMessage


def test_list_messages_returns_15(client):
    headers = auth_headers(client, "admin")
    resp = client.get("/api/mailroom/messages", headers=headers)
    assert resp.status_code == 200
    messages = resp.json()
    assert len(messages) == 15


def test_classify_all_flags_exactly_5_invoices(client):
    headers = auth_headers(client, "admin")
    resp = client.post("/api/mailroom/classify-all", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 15
    assert body["flagged_as_invoice"] == 5

    flagged = [r for r in body["results"] if r["is_invoice"]]
    assert len(flagged) == 5

    for result in flagged:
        extraction = result["extraction"]
        assert extraction is not None
        assert extraction["vendor_name"], f"missing vendor_name for {result['subject']}"
        assert extraction["total_amount"], f"missing total_amount for {result['subject']}"
        assert extraction["invoice_number"] or extraction["po_number"], (
            f"missing both invoice_number and po_number for {result['subject']}"
        )


def test_get_message_detail_includes_source_and_attachment(client):
    headers = auth_headers(client, "admin")
    list_resp = client.get("/api/mailroom/messages", headers=headers)
    with_attachment = next(m for m in list_resp.json() if m["has_attachment"])

    resp = client.get(f"/api/mailroom/messages/{with_attachment['id']}", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "seed"
    assert body["attachment"] is not None
    assert body["attachment"]["id"] > 0


def test_mailroom_requires_auth(client):
    resp = client.get("/api/mailroom/messages")
    assert resp.status_code == 401


def test_import_gmail_requires_senior_manager(client):
    headers = auth_headers(client, "rahul.verma")  # Maintenance Manager
    resp = client.post("/api/mailroom/import-gmail", headers=headers)
    assert resp.status_code == 403


def test_import_gmail_without_credentials_returns_400(client, monkeypatch):
    # Force "unset" regardless of what backend/.env has configured on this
    # machine — this test must never make a real IMAP connection.
    monkeypatch.setattr("app.services.gmail_import.settings.gmail_address", None)
    monkeypatch.setattr("app.services.gmail_import.settings.gmail_app_password", None)

    headers = auth_headers(client, "vikram.shah")  # Procurement Senior Manager
    resp = client.post("/api/mailroom/import-gmail", headers=headers)
    assert resp.status_code == 400
    assert "GMAIL_ADDRESS" in resp.json()["detail"]


def test_import_gmail_creates_messages_and_skips_duplicates_on_replay(client):
    headers = auth_headers(client, "vikram.shah")
    fake_messages = [
        ImportedMessage(
            external_id="<msg-1@example.com>",
            sender="vendor@example.com",
            sender_name="Vendor One",
            subject="Test invoice from real inbox",
            body="Please find attached invoice.",
            received_at=datetime(2026, 1, 1),
            attachment=None,
        ),
        ImportedMessage(
            external_id="<msg-2@example.com>",
            sender="colleague@example.com",
            sender_name="Colleague",
            subject="Lunch plans",
            body="Want to grab lunch?",
            received_at=datetime(2026, 1, 1),
            attachment=None,
        ),
    ]

    with patch("app.routers.mailroom.fetch_recent_messages", return_value=fake_messages):
        resp = client.post("/api/mailroom/import-gmail?limit=10", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body == {"imported": 2, "skipped_duplicates": 0, "total_fetched": 2}

        # Replaying the same fetch must skip both as already-imported (matched
        # by IMAP Message-ID -> external_id), not create duplicate rows.
        resp2 = client.post("/api/mailroom/import-gmail?limit=10", headers=headers)
        assert resp2.status_code == 200
        assert resp2.json() == {"imported": 0, "skipped_duplicates": 2, "total_fetched": 2}

    list_resp = client.get("/api/mailroom/messages", headers=headers)
    imported = [m for m in list_resp.json() if m["source"] == "gmail_import"]
    assert len(imported) == 2
    assert all(m["department"] == "Admin" for m in imported)


def _png_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (10, 10), color="white").save(buf, format="PNG")
    return buf.getvalue()


def test_upload_document_creates_message_with_attachment(client):
    headers = auth_headers(client, "admin")
    resp = client.post(
        "/api/mailroom/upload",
        headers=headers,
        files={"file": ("test-invoice.png", _png_bytes(), "image/png")},
        data={"subject": "A real test invoice"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "upload"
    assert body["subject"] == "A real test invoice"
    assert body["department"] == "Admin"
    assert body["attachment"]["filename"] == "test-invoice.png"

    # It flows through the exact same classify pipeline as any other message.
    classify_resp = client.post(f"/api/mailroom/messages/{body['id']}/classify", headers=headers)
    assert classify_resp.status_code == 200


def test_upload_document_rejects_unsupported_content_type(client):
    headers = auth_headers(client, "admin")
    resp = client.post(
        "/api/mailroom/upload",
        headers=headers,
        files={"file": ("notes.txt", b"just some text", "text/plain")},
    )
    assert resp.status_code == 400


def test_upload_document_requires_auth(client):
    resp = client.post(
        "/api/mailroom/upload",
        files={"file": ("test-invoice.png", _png_bytes(), "image/png")},
    )
    assert resp.status_code == 401
