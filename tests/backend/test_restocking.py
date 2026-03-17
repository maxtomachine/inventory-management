"""Tests for the restocking recommendation and order endpoints."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'server'))

from fastapi.testclient import TestClient
from main import app
from mock_data import submitted_orders


class TestRestockingRecommendations:
    """Tests for GET /api/restocking/recommendations"""

    def setup_method(self):
        self.client = TestClient(app)

    def test_returns_recommendations(self):
        response = self.client.get("/api/restocking/recommendations?budget=25000")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_default_budget(self):
        response = self.client.get("/api/restocking/recommendations")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_recommendation_fields(self):
        response = self.client.get("/api/restocking/recommendations?budget=50000")
        data = response.json()
        required_fields = [
            "item_sku", "item_name", "current_demand", "forecasted_demand",
            "trend", "demand_gap", "unit_cost", "recommended_qty", "line_total"
        ]
        for item in data:
            for field in required_fields:
                assert field in item, f"Missing field: {field}"

    def test_demand_gap_positive(self):
        response = self.client.get("/api/restocking/recommendations?budget=100000")
        data = response.json()
        for item in data:
            assert item["demand_gap"] > 0

    def test_line_total_matches(self):
        response = self.client.get("/api/restocking/recommendations?budget=50000")
        data = response.json()
        for item in data:
            expected = round(item["recommended_qty"] * item["unit_cost"], 2)
            assert item["line_total"] == expected

    def test_total_within_budget(self):
        budget = 10000
        response = self.client.get(f"/api/restocking/recommendations?budget={budget}")
        data = response.json()
        total = sum(item["line_total"] for item in data)
        assert total <= budget

    def test_increasing_trend_prioritized(self):
        response = self.client.get("/api/restocking/recommendations?budget=100000")
        data = response.json()
        if len(data) > 1:
            increasing_indices = [i for i, item in enumerate(data) if item["trend"] == "increasing"]
            stable_indices = [i for i, item in enumerate(data) if item["trend"] == "stable"]
            if increasing_indices and stable_indices:
                assert max(increasing_indices) < min(stable_indices)

    def test_small_budget_fewer_items(self):
        small = self.client.get("/api/restocking/recommendations?budget=5000").json()
        large = self.client.get("/api/restocking/recommendations?budget=100000").json()
        assert len(small) <= len(large)

    def test_zero_budget_empty(self):
        response = self.client.get("/api/restocking/recommendations?budget=0")
        data = response.json()
        assert data == []


class TestRestockingOrder:
    """Tests for POST /api/restocking/order"""

    def setup_method(self):
        self.client = TestClient(app)
        submitted_orders.clear()

    def test_submit_order(self):
        payload = {
            "items": [
                {"item_sku": "WDG-001", "item_name": "Industrial Widget Type A", "quantity": 50, "unit_cost": 45.0}
            ]
        }
        response = self.client.post("/api/restocking/order", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["order_number"].startswith("RST-2026-")
        assert data["customer"] == "Internal Restocking"
        assert data["status"] == "Processing"
        assert data["source"] == "restocking"
        assert data["lead_time_days"] == 14
        assert data["total_value"] == 2250.0

    def test_submit_order_multiple_items(self):
        payload = {
            "items": [
                {"item_sku": "WDG-001", "item_name": "Industrial Widget Type A", "quantity": 10, "unit_cost": 45.0},
                {"item_sku": "FLT-405", "item_name": "Oil Filter Cartridge", "quantity": 20, "unit_cost": 12.5}
            ]
        }
        response = self.client.post("/api/restocking/order", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total_value"] == 700.0

    def test_submit_order_empty_items(self):
        response = self.client.post("/api/restocking/order", json={"items": []})
        assert response.status_code == 400

    def test_order_has_expected_delivery(self):
        payload = {
            "items": [
                {"item_sku": "WDG-001", "item_name": "Widget", "quantity": 1, "unit_cost": 10.0}
            ]
        }
        response = self.client.post("/api/restocking/order", json=payload)
        data = response.json()
        assert data["expected_delivery"] is not None
        assert data["order_date"] is not None

    def test_order_appears_in_restocking_orders(self):
        payload = {
            "items": [
                {"item_sku": "WDG-001", "item_name": "Widget", "quantity": 5, "unit_cost": 10.0}
            ]
        }
        self.client.post("/api/restocking/order", json=payload)
        response = self.client.get("/api/restocking/orders")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["source"] == "restocking"

    def test_order_appears_in_all_orders(self):
        payload = {
            "items": [
                {"item_sku": "WDG-001", "item_name": "Widget", "quantity": 5, "unit_cost": 10.0}
            ]
        }
        self.client.post("/api/restocking/order", json=payload)
        response = self.client.get("/api/orders")
        data = response.json()
        restocking_orders = [o for o in data if o.get("source") == "restocking"]
        assert len(restocking_orders) == 1


class TestRestockingOrders:
    """Tests for GET /api/restocking/orders"""

    def setup_method(self):
        self.client = TestClient(app)
        submitted_orders.clear()

    def test_empty_initially(self):
        response = self.client.get("/api/restocking/orders")
        assert response.status_code == 200
        assert response.json() == []

    def test_returns_submitted_orders(self):
        payload = {
            "items": [
                {"item_sku": "X", "item_name": "Test", "quantity": 1, "unit_cost": 10.0}
            ]
        }
        self.client.post("/api/restocking/order", json=payload)
        self.client.post("/api/restocking/order", json=payload)
        response = self.client.get("/api/restocking/orders")
        data = response.json()
        assert len(data) == 2
