"""Month/quarter filter validation and the quarterly report built on the same helper."""
import pytest


def _dates(client, month):
    return [o["order_date"] for o in client.get(f"/api/orders?month={month}").json()]


def test_month_matches_by_prefix(client):
    dates = _dates(client, "2025-01")
    assert dates and all(d.startswith("2025-01") for d in dates)


def test_quarter_matches_its_three_months(client):
    dates = _dates(client, "Q1-2025")
    assert dates and all(d[:7] in ("2025-01", "2025-02", "2025-03") for d in dates)


def test_quarter_of_other_year_is_empty_not_everything(client):
    assert _dates(client, "Q1-2024") == []


@pytest.mark.parametrize("bad", ["Q5-2025", "2024-Q1", "-0", "2025-13", "junk"])
def test_invalid_month_is_rejected(client, bad):
    assert client.get(f"/api/orders?month={bad}").status_code == 400
    assert client.get(f"/api/dashboard/summary?month={bad}").status_code == 400


def test_quarterly_report_has_consistent_keys_and_order(client):
    rows = client.get("/api/reports/quarterly").json()
    assert rows
    assert all({"fulfillment_rate", "avg_order_value"} <= r.keys() for r in rows)
    assert [r["quarter"] for r in rows] == sorted((r["quarter"] for r in rows), key=lambda q: (q[3:], q))
