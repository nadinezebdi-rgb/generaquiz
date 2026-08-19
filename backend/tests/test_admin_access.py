"""Backend tests: admin login flow, role backfill, admin QA endpoints, non-admin 403."""
import os
import time
import uuid
import pytest
import requests

def _read_frontend_env_url():
    p = "/app/frontend/.env"
    if os.path.exists(p):
        for line in open(p):
            if line.startswith("REACT_APP_BACKEND_URL="):
                return line.split("=", 1)[1].strip()
    return None

BASE = (os.environ.get("REACT_APP_BACKEND_URL") or _read_frontend_env_url()).rstrip("/")
ADMIN_EMAIL = "admin@generaquiz.fr"
ADMIN_PWD = "pF44gVBfLdushm3NZ6dN"


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PWD}, timeout=15)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text[:400]}"
    data = r.json()
    assert data.get("user", {}).get("role") == "admin", f"role not admin: {data}"
    return s


@pytest.fixture(scope="module")
def user_session():
    s = requests.Session()
    email = f"testuser_{uuid.uuid4().hex[:8]}@example.com"
    r = s.post(f"{BASE}/api/auth/register", json={"email": email, "password": "Passw0rd!!", "name": "Test User"}, timeout=15)
    assert r.status_code in (200, 201), f"register failed: {r.status_code} {r.text[:300]}"
    # Login (if register doesn't set cookie)
    s.post(f"{BASE}/api/auth/login", json={"email": email, "password": "Passw0rd!!"}, timeout=15)
    return s


class TestAdminAuth:
    def test_admin_login_returns_admin_role(self, admin_session):
        r = admin_session.get(f"{BASE}/api/auth/me", timeout=15)
        assert r.status_code == 200
        me = r.json()
        assert me.get("role") == "admin", f"me: {me}"
        assert me.get("email") == ADMIN_EMAIL

    def test_admin_qa_summary_ok(self, admin_session):
        r = admin_session.get(f"{BASE}/api/admin/qa/summary", timeout=30)
        assert r.status_code == 200, f"{r.status_code} {r.text[:400]}"
        data = r.json()
        # Should contain per-category summary
        assert isinstance(data, (dict, list))

    def test_admin_qa_questions_ok(self, admin_session):
        r = admin_session.get(f"{BASE}/api/admin/qa/questions", params={"quality": "flagged"}, timeout=30)
        assert r.status_code == 200, f"{r.status_code} {r.text[:400]}"
        data = r.json()
        assert isinstance(data, (dict, list))


class TestNonAdmin:
    def test_non_admin_cannot_access_admin_qa(self, user_session):
        r = user_session.get(f"{BASE}/api/admin/qa/summary", timeout=15)
        assert r.status_code == 403, f"expected 403 got {r.status_code}: {r.text[:200]}"

    def test_non_admin_me_role(self, user_session):
        r = user_session.get(f"{BASE}/api/auth/me", timeout=15)
        assert r.status_code == 200
        assert r.json().get("role") != "admin"


class TestQuizRegression:
    def test_categories_list(self, admin_session):
        r = admin_session.get(f"{BASE}/api/categories", timeout=15)
        assert r.status_code == 200
        cats = r.json()
        assert isinstance(cats, list) and len(cats) > 0
        ids = [c.get("id") for c in cats]
        assert "chansons" in ids, f"chansons missing in {ids}"

    def test_chansons_questions(self, admin_session):
        r = admin_session.get(f"{BASE}/api/categories/chansons/questions", timeout=15)
        assert r.status_code == 200
        data = r.json()
        # Could be list or dict with questions key
        qs = data if isinstance(data, list) else data.get("questions", [])
        assert len(qs) > 0
