"""Sprint E — Admin analytics + /pourquoi page tests."""
import os
import time
import uuid
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://caricature-saas.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@generaquiz.fr"
ADMIN_PASSWORD = "Admin2026!"


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def user_session():
    s = requests.Session()
    email = f"TEST_sprinte_{uuid.uuid4().hex[:8]}@example.com"
    r = s.post(f"{API}/auth/register", json={"email": email, "password": "TestPass123!", "name": "Test SprintE"})
    assert r.status_code in (200, 201), f"register failed: {r.status_code} {r.text}"
    return s


ENDPOINTS = [
    "/admin/analytics/overview",
    "/admin/analytics/signups",
    "/admin/analytics/revenue",
    "/admin/analytics/categories",
    "/admin/analytics/atelier",
]


class TestAuthorization:
    @pytest.mark.parametrize("ep", ENDPOINTS)
    def test_unauthenticated_rejected(self, ep):
        r = requests.get(f"{API}{ep}")
        assert r.status_code in (401, 403), f"{ep} unauth got {r.status_code}"

    @pytest.mark.parametrize("ep", ENDPOINTS)
    def test_non_admin_forbidden(self, user_session, ep):
        r = user_session.get(f"{API}{ep}")
        assert r.status_code == 403, f"{ep} non-admin got {r.status_code} {r.text}"


class TestOverview:
    def test_overview_shape(self, admin_session):
        r = admin_session.get(f"{API}/admin/analytics/overview")
        assert r.status_code == 200
        d = r.json()
        assert "generated_at" in d
        for k in ("total", "new_30d", "new_24h", "paid", "conversion_pct"):
            assert k in d["users"], f"users.{k} missing"
        for k in ("dau", "mau", "dau_mau_pct"):
            assert k in d["engagement"]
        for k in ("mrr_estimate_eur", "revenue_mtd_eur", "transactions_mtd", "arpu_paid_eur"):
            assert k in d["revenue"]


class TestSignups:
    def test_default_30(self, admin_session):
        r = admin_session.get(f"{API}/admin/analytics/signups")
        assert r.status_code == 200
        d = r.json()
        assert isinstance(d, list)
        assert len(d) == 30
        for item in d:
            assert "date" in item and "count" in item
            assert len(item["date"]) == 10
            assert isinstance(item["count"], int)

    def test_days_clamp_high(self, admin_session):
        r = admin_session.get(f"{API}/admin/analytics/signups?days=500")
        assert r.status_code == 200
        assert len(r.json()) == 180

    def test_days_clamp_low(self, admin_session):
        r = admin_session.get(f"{API}/admin/analytics/signups?days=0")
        assert r.status_code == 200
        assert len(r.json()) == 1


class TestRevenue:
    def test_default_30(self, admin_session):
        r = admin_session.get(f"{API}/admin/analytics/revenue")
        assert r.status_code == 200
        d = r.json()
        assert isinstance(d, list) and len(d) == 30
        for item in d:
            assert "date" in item and "amount" in item
            assert isinstance(item["amount"], (int, float))


class TestCategories:
    def test_list(self, admin_session):
        r = admin_session.get(f"{API}/admin/analytics/categories")
        assert r.status_code == 200
        d = r.json()
        assert isinstance(d, list)
        for row in d:
            for k in ("category_id", "title", "attempts", "correct", "total", "accuracy_pct"):
                assert k in row


class TestAtelier:
    def test_shape(self, admin_session):
        r = admin_session.get(f"{API}/admin/analytics/atelier")
        assert r.status_code == 200
        d = r.json()
        for k in ("total_entries", "total_sessions", "unique_users", "avg_entries_per_session", "by_theme"):
            assert k in d
        assert isinstance(d["by_theme"], list)


class TestNoRegression:
    def test_categories_public(self):
        r = requests.get(f"{API}/categories")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_packages(self):
        r = requests.get(f"{API}/packages")
        assert r.status_code == 200
