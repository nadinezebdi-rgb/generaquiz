"""Iteration 18 — Validate Mistral API key & admin regenerate endpoint integration.

Goals:
  1. Backend healthy (GET /api/)
  2. Admin login returns JWT
  3. POST /api/admin/mistral/regenerate is accepted (200) with admin JWT (no 401),
     and rejected (401/403) without auth.
  4. Background task triggers Mistral SDK without 401 Unauthorized (verified via logs).
  5. No regression on GET /api/categories and GET /api/daily/quiz.
"""
import os
import time

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # Backend tests run inside the container — fall back to local frontend env
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().strip('"').rstrip("/")
                break

ADMIN_EMAIL = "admin@generaquiz.fr"
ADMIN_PASSWORD = "Admin2026!"


# ---------- fixtures ----------
def _new_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture()
def session():
    """Fresh session per test — avoids cross-test cookie pollution
    (the backend sets httpOnly auth cookies on /auth/login)."""
    return _new_session()


@pytest.fixture(scope="module")
def admin_token():
    s = _new_session()
    r = s.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=15,
    )
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    data = r.json()
    token = data.get("access_token") or data.get("token")
    assert token, f"No token in admin login response: {data}"
    assert data.get("user", {}).get("role") == "admin", f"User is not admin: {data}"
    return token


# ---------- tests ----------
# Backend health
class TestBackendHealth:
    def test_api_root_returns_200(self, session):
        r = session.get(f"{BASE_URL}/api/", timeout=10)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("status") == "ok"


# Admin auth (login + JWT)
class TestAdminAuth:
    def test_admin_login_returns_jwt(self, admin_token):
        # the fixture itself asserts a valid token
        assert isinstance(admin_token, str) and len(admin_token) > 20

    def test_admin_me(self, session, admin_token):
        r = session.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=10,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("email") == ADMIN_EMAIL
        assert body.get("role") == "admin"


# Mistral regenerate endpoint
class TestMistralRegenerate:
    URL_SUFFIX = "/api/admin/mistral/regenerate"

    def test_requires_auth(self, session):
        r = session.post(f"{BASE_URL}{self.URL_SUFFIX}", timeout=10)
        # Either 401 (missing token) or 403 — but NOT 200
        assert r.status_code in (401, 403), (
            f"Endpoint accepted unauthenticated call: {r.status_code} {r.text}"
        )

    def test_rejects_non_admin(self, session):
        # Register a fresh non-admin user
        ts = int(time.time())
        email = f"TEST_mistral_{ts}@example.com"
        reg = session.post(
            f"{BASE_URL}/api/auth/register",
            json={"email": email, "password": "Pass1234!", "name": "TestMistral"},
            timeout=15,
        )
        assert reg.status_code in (200, 201), reg.text
        ut = reg.json().get("access_token") or reg.json().get("token")
        assert ut
        r = session.post(
            f"{BASE_URL}{self.URL_SUFFIX}",
            headers={"Authorization": f"Bearer {ut}"},
            timeout=10,
        )
        assert r.status_code in (401, 403), (
            f"Non-admin allowed to trigger regenerate: {r.status_code} {r.text}"
        )

    def test_admin_can_trigger_regenerate(self, session, admin_token):
        r = session.post(
            f"{BASE_URL}{self.URL_SUFFIX}",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=30,
        )
        assert r.status_code == 200, (
            f"Admin regenerate trigger failed: {r.status_code} {r.text}"
        )
        body = r.json()
        assert body.get("ok") is True, body
        assert "Régénération" in body.get("message", "") or "regener" in body.get(
            "message", ""
        ).lower()


# Regression — public catalog & daily quiz
class TestRegressionCriticalRoutes:
    def test_categories(self, session):
        r = session.get(f"{BASE_URL}/api/categories", timeout=15)
        assert r.status_code == 200, r.text
        cats = r.json()
        assert isinstance(cats, list)
        assert len(cats) >= 1, "No categories returned"
        # basic shape check
        first = cats[0]
        for key in ("id", "title"):
            assert key in first, f"Category missing field {key}: {first}"

    def test_daily_quiz(self, session, admin_token):
        # /daily/quiz is the equivalent of '/daily/today' in this codebase
        r = session.get(
            f"{BASE_URL}/api/daily/quiz",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=15,
        )
        # Either fresh quiz available (200) or already played today (a 4xx is also
        # acceptable as a non-regression signal — only 5xx would be a real failure)
        assert r.status_code < 500, f"Daily quiz endpoint 5xx: {r.status_code} {r.text}"
