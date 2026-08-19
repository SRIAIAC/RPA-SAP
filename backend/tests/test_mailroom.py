from tests.conftest import auth_headers


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


def test_mailroom_requires_auth(client):
    resp = client.get("/api/mailroom/messages")
    assert resp.status_code == 401
