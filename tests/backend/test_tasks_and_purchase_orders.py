"""Tests for the /api/tasks and /api/purchase-orders endpoints."""


def _po_payload(backlog_item_id, **overrides):
    payload = {
        "backlog_item_id": backlog_item_id,
        "supplier_name": "Acme Supply",
        "quantity": 50,
        "unit_cost": 12.5,
        "expected_delivery_date": "2025-12-01",
    }
    payload.update(overrides)
    return payload


def _free_backlog_id(client):
    """Return a backlog item id without a PO (state is shared across tests in-process)."""
    items = client.get("/api/backlog").json()
    return next(i["id"] for i in items if not i["has_purchase_order"])


def test_task_lifecycle(client):
    created = client.post("/api/tasks", json={"title": "Check stock", "priority": "high", "dueDate": "2025-12-01"})
    assert created.status_code == 201
    task = created.json()
    assert task["status"] == "pending"
    assert task["id"] >= 1000  # must not collide with client-side mock ids

    assert any(t["id"] == task["id"] for t in client.get("/api/tasks").json())

    toggled = client.patch(f"/api/tasks/{task['id']}")
    assert toggled.json()["status"] == "completed"
    assert client.patch(f"/api/tasks/{task['id']}").json()["status"] == "pending"

    assert client.delete(f"/api/tasks/{task['id']}").status_code == 200
    assert not any(t["id"] == task["id"] for t in client.get("/api/tasks").json())


def test_task_errors(client):
    assert client.post("/api/tasks", json={"title": "  ", "dueDate": "2025-12-01"}).status_code == 400
    assert client.delete("/api/tasks/999999").status_code == 404
    assert client.patch("/api/tasks/999999").status_code == 404


def test_create_and_get_purchase_order(client):
    item_id = _free_backlog_id(client)
    created = client.post("/api/purchase-orders", json=_po_payload(item_id))
    assert created.status_code == 201
    po = created.json()
    assert po["backlog_item_id"] == item_id
    assert po["status"] == "Submitted"

    assert client.get(f"/api/purchase-orders/{item_id}").json()["id"] == po["id"]

    # The backlog now reports the PO, so "View PO" survives a reload
    item = next(i for i in client.get("/api/backlog").json() if i["id"] == item_id)
    assert item["has_purchase_order"] is True
    assert item["purchase_order_id"] == po["id"]

    # One PO per backlog item
    assert client.post("/api/purchase-orders", json=_po_payload(item_id)).status_code == 409


def test_purchase_order_validation(client):
    item_id = _free_backlog_id(client)
    assert client.post("/api/purchase-orders", json=_po_payload("nope")).status_code == 404
    assert client.post("/api/purchase-orders", json=_po_payload(item_id, quantity=0)).status_code == 400
    assert client.post("/api/purchase-orders", json=_po_payload(item_id, unit_cost=-1)).status_code == 400
    assert client.post("/api/purchase-orders", json=_po_payload(item_id, expected_delivery_date="soon")).status_code == 400
    assert client.get("/api/purchase-orders/nope").status_code == 404
