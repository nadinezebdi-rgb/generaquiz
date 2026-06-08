"""Backend tests for the promo codes feature."""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@quizdantan.fr"
ADMIN_PASSWORD = "Admin2026!"


# --------------------------- Fixtures ---------------------------
@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=20)
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture
def free_user_session():
    s = requests.Session()
    email = f"test_promo_{uuid.uuid4().hex[:10]}@example.com"
    r = s.post(f"{API}/auth/register", json={"email": email, "password": "Pass1234!", "name": "Tester Promo"}, timeout=20)
    assert r.status_code == 200, f"Register failed: {r.status_code} {r.text}"
    s.user_email = email
    return s


@pytest.fixture(scope="module")
def created_codes():
    """Track ids created during test run for cleanup."""
    ids = []
    yield ids


@pytest.fixture(scope="module", autouse=True)
def cleanup(admin_session, created_codes):
    yield
    for pid in created_codes:
        try:
            admin_session.delete(f"{API}/admin/promo/{pid}", timeout=10)
        except Exception:
            pass


# --------------------------- Admin CRUD ---------------------------
class TestAdminPromoAuth:
    def test_non_admin_create_forbidden(self, free_user_session):
        r = free_user_session.post(f"{API}/admin/promo", json={"duration_days": 30}, timeout=15)
        assert r.status_code == 403

    def test_non_admin_list_forbidden(self, free_user_session):
        r = free_user_session.get(f"{API}/admin/promo", timeout=15)
        assert r.status_code == 403

    def test_unauthenticated_create_unauth(self):
        r = requests.post(f"{API}/admin/promo", json={"duration_days": 30}, timeout=15)
        assert r.status_code == 401


class TestAdminPromoCRUD:
    def test_admin_can_create_with_explicit_code(self, admin_session, created_codes):
        code_input = f"TEST-{uuid.uuid4().hex[:6]}".lower()
        r = admin_session.post(f"{API}/admin/promo", json={
            "code": code_input,
            "duration_days": 30,
            "max_uses": 5,
            "label": "Unit test 30j",
        }, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["code"] == code_input.upper()  # normalized
        assert data["duration_days"] == 30
        assert data["max_uses"] == 5
        assert data["used_count"] == 0
        assert data["active"] is True
        assert data["is_lifetime"] is False
        assert "id" in data and isinstance(data["id"], str)
        created_codes.append(data["id"])

    def test_admin_can_create_lifetime_random_code(self, admin_session, created_codes):
        r = admin_session.post(f"{API}/admin/promo", json={
            "duration_days": 36500,
            "label": "Lifetime test",
        }, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["code"] and data["code"] == data["code"].upper()
        assert data["is_lifetime"] is True
        assert data["max_uses"] is None
        created_codes.append(data["id"])

    def test_admin_duplicate_code_rejected(self, admin_session, created_codes):
        code = f"DUP{uuid.uuid4().hex[:6].upper()}"
        r1 = admin_session.post(f"{API}/admin/promo", json={"code": code, "duration_days": 7}, timeout=15)
        assert r1.status_code == 200
        created_codes.append(r1.json()["id"])
        r2 = admin_session.post(f"{API}/admin/promo", json={"code": code, "duration_days": 7}, timeout=15)
        assert r2.status_code == 400

    def test_admin_list_sorted_desc(self, admin_session):
        r = admin_session.get(f"{API}/admin/promo", timeout=15)
        assert r.status_code == 200
        rows = r.json()
        assert isinstance(rows, list)
        # Expect seeded codes
        codes = [p["code"] for p in rows]
        assert "FAMILLE2026" in codes
        # Check sort desc by created_at
        created = [p.get("created_at") for p in rows if p.get("created_at")]
        assert created == sorted(created, reverse=True)

    def test_admin_toggle_active(self, admin_session, created_codes):
        r = admin_session.post(f"{API}/admin/promo", json={"duration_days": 7, "label": "toggle"}, timeout=15)
        pid = r.json()["id"]
        created_codes.append(pid)
        # Toggle off
        r1 = admin_session.patch(f"{API}/admin/promo/{pid}", timeout=15)
        assert r1.status_code == 200
        assert r1.json()["active"] is False
        # Toggle back on
        r2 = admin_session.patch(f"{API}/admin/promo/{pid}", timeout=15)
        assert r2.status_code == 200
        assert r2.json()["active"] is True

    def test_admin_delete(self, admin_session):
        r = admin_session.post(f"{API}/admin/promo", json={"duration_days": 7, "label": "to-delete"}, timeout=15)
        pid = r.json()["id"]
        r1 = admin_session.delete(f"{API}/admin/promo/{pid}", timeout=15)
        assert r1.status_code == 200
        # Verify it's gone
        listing = admin_session.get(f"{API}/admin/promo", timeout=15).json()
        ids = [p["id"] for p in listing]
        assert pid not in ids


# --------------------------- Redeem ---------------------------
class TestPromoRedeem:
    def test_redeem_unauth(self):
        r = requests.post(f"{API}/promo/redeem", json={"code": "FAMILLE2026"}, timeout=15)
        assert r.status_code == 401

    def test_redeem_invalid_code_404(self, free_user_session):
        r = free_user_session.post(f"{API}/promo/redeem", json={"code": f"NOPE{uuid.uuid4().hex[:6]}"}, timeout=15)
        assert r.status_code == 404
        assert "invalide" in r.json().get("detail", "").lower()

    def test_redeem_lifetime_makes_user_premium(self, free_user_session):
        r = free_user_session.post(f"{API}/promo/redeem", json={"code": "famille2026"}, timeout=15)  # mixed-case
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["plan"] == "premium"
        assert data["is_lifetime"] is True
        assert data["duration_days"] >= 36500
        # Verify /auth/me
        me = free_user_session.get(f"{API}/auth/me", timeout=15)
        assert me.status_code == 200
        assert me.json()["plan"] == "premium"

    def test_redeem_same_code_twice_400(self, free_user_session):
        r1 = free_user_session.post(f"{API}/promo/redeem", json={"code": "FAMILLE2026"}, timeout=15)
        assert r1.status_code == 200
        r2 = free_user_session.post(f"{API}/promo/redeem", json={"code": "FAMILLE2026"}, timeout=15)
        assert r2.status_code == 400
        assert "déjà" in r2.json().get("detail", "").lower()

    def test_redeem_deactivated_code_404(self, admin_session, created_codes, free_user_session):
        # Create a code, deactivate it, then try redeeming
        code = f"DEACT{uuid.uuid4().hex[:6].upper()}"
        c = admin_session.post(f"{API}/admin/promo", json={"code": code, "duration_days": 30}, timeout=15).json()
        created_codes.append(c["id"])
        admin_session.patch(f"{API}/admin/promo/{c['id']}", timeout=15)  # deactivate
        r = free_user_session.post(f"{API}/promo/redeem", json={"code": code}, timeout=15)
        assert r.status_code == 404

    def test_redeem_max_uses_reached_410(self, admin_session, created_codes):
        # Create code with max_uses=1, use once, then second user should get 410
        code = f"MAX{uuid.uuid4().hex[:6].upper()}"
        c = admin_session.post(f"{API}/admin/promo", json={"code": code, "duration_days": 30, "max_uses": 1}, timeout=15).json()
        created_codes.append(c["id"])

        # First user redeems
        s1 = requests.Session()
        e1 = f"max1_{uuid.uuid4().hex[:8]}@example.com"
        s1.post(f"{API}/auth/register", json={"email": e1, "password": "Pass1234!", "name": "M1"}, timeout=15)
        r1 = s1.post(f"{API}/promo/redeem", json={"code": code}, timeout=15)
        assert r1.status_code == 200

        # Second user gets 410
        s2 = requests.Session()
        e2 = f"max2_{uuid.uuid4().hex[:8]}@example.com"
        s2.post(f"{API}/auth/register", json={"email": e2, "password": "Pass1234!", "name": "M2"}, timeout=15)
        r2 = s2.post(f"{API}/promo/redeem", json={"code": code}, timeout=15)
        assert r2.status_code == 410

    def test_redeem_normalizes_case_and_whitespace(self, free_user_session):
        r = free_user_session.post(f"{API}/promo/redeem", json={"code": "  FaMiLlE2026  "}, timeout=15)
        assert r.status_code == 200
        assert r.json()["plan"] == "premium"
