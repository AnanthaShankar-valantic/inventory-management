"""
Tests for restocking API endpoints.
"""
from datetime import date, timedelta


class TestRestockRecommendations:
    """Test suite for the restock recommendation endpoint."""

    def test_zero_budget_recommends_nothing(self, client):
        """Test that a zero budget returns no items."""
        response = client.get("/api/restock/recommendations?budget=0")
        assert response.status_code == 200

        data = response.json()
        assert data["items"] == []
        assert data["total_cost"] == 0
        assert data["remaining_budget"] == 0

    def test_negative_budget_returns_400(self, client):
        """Test that a negative budget is rejected."""
        response = client.get("/api/restock/recommendations?budget=-1")
        assert response.status_code == 400

    def test_total_stays_within_budget(self, client):
        """Test that the recommendation never exceeds the budget."""
        for budget in (500, 5000, 12345.67, 100000):
            data = client.get(f"/api/restock/recommendations?budget={budget}").json()
            assert data["total_cost"] <= budget
            assert round(data["total_cost"] + data["remaining_budget"], 2) == budget
            assert round(sum(i["line_cost"] for i in data["items"]), 2) == data["total_cost"]

    def test_ranking_by_shortfall_and_trend(self, client):
        """Test that the highest shortfall x trend item is recommended first."""
        data = client.get("/api/restock/recommendations?budget=100000").json()
        skus = [i["sku"] for i in data["items"]]
        # FLT-405 has the largest shortfall and an increasing trend
        assert skus[0] == "FLT-405"
        # Items with no shortfall (stock covers forecast) are never recommended
        assert "BRG-102" not in skus
        assert "MTR-304" not in skus

    def test_small_budget_buys_partial_quantity(self, client):
        """Test that a budget below the full shortfall cost buys a partial quantity."""
        data = client.get("/api/restock/recommendations?budget=64").json()
        assert data["items"][0]["sku"] == "FLT-405"
        assert data["items"][0]["quantity"] == 10  # 64 / 6.40
        assert data["remaining_budget"] == 0


class TestRestockOrders:
    """Test suite for the restock order endpoints."""

    def test_create_order(self, client):
        """Test placing an order returns 201 with lead time and delivery date."""
        response = client.post(
            "/api/restock-orders",
            json={"items": [{"sku": "FLT-405", "quantity": 10}, {"sku": "MTR-304", "quantity": 1}]},
        )
        assert response.status_code == 201

        data = response.json()
        # Longest item lead time wins: FLT-405 = 5 days, MTR-304 = 21 days
        assert data["lead_time_days"] == 21
        today = date.today()
        assert data["order_date"] == today.isoformat()
        assert data["expected_delivery"] == (today + timedelta(days=21)).isoformat()
        assert data["total_cost"] == 10 * 6.4 + 320.0
        assert data["status"] == "Submitted"

    def test_created_order_is_listed(self, client):
        """Test that a placed order appears in the list, newest first."""
        created = client.post(
            "/api/restock-orders", json={"items": [{"sku": "WDG-001", "quantity": 5}]}
        ).json()

        response = client.get("/api/restock-orders")
        assert response.status_code == 200
        assert response.json()[0]["id"] == created["id"]

    def test_empty_order_returns_400(self, client):
        """Test that an order without items is rejected."""
        response = client.post("/api/restock-orders", json={"items": []})
        assert response.status_code == 400

    def test_unknown_sku_returns_400(self, client):
        """Test that an unknown SKU is rejected."""
        response = client.post(
            "/api/restock-orders", json={"items": [{"sku": "NOPE-000", "quantity": 1}]}
        )
        assert response.status_code == 400

    def test_non_positive_quantity_returns_400(self, client):
        """Test that zero or negative quantity is rejected."""
        response = client.post(
            "/api/restock-orders", json={"items": [{"sku": "WDG-001", "quantity": 0}]}
        )
        assert response.status_code == 400

    def test_sales_orders_unchanged(self, client):
        """Test that restock orders do not leak into sales orders."""
        before = len(client.get("/api/orders").json())
        client.post("/api/restock-orders", json={"items": [{"sku": "WDG-001", "quantity": 1}]})
        assert len(client.get("/api/orders").json()) == before
