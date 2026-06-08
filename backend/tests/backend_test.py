"""Backend API tests for Quiz d'Antan SaaS."""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://caricature-saas.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@quizdantan.fr"
ADMIN_PASSWORD = "Admin2026!"

CATEGORY_IDS = [
    "annees-50-60", "chansons", "cinema",
    "objets-antan", "histoire-france", "cuisine-terroir",
]


# -------- Fixtures --------
@pytest.fixture(scope="session")
def admin_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="session")
def free_user_session():
    s = requests.Session()
    email = f"qa.test.{int(time.time())}@quizdantan.fr"
    r = s.post(f"{API}/auth/register", json={"name": "QA Test", "email": email, "password": "test1234"})
    assert r.status_code == 200, f"register failed: {r.status_code} {r.text}"
    s.email = email
    return s


# -------- Health & catalog --------
class TestHealth:
    def test_root(self):
        r = requests.get(f"{API}/")
        assert r.status_code == 200
        assert r.json().get("status") == "ok"

    def test_categories_list(self):
        r = requests.get(f"{API}/categories")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) == 6
        ids = {c["id"] for c in data}
        assert ids == set(CATEGORY_IDS)
        # required keys
        for c in data:
            for k in ("id", "title", "description", "color", "mascot_image", "mascot_name"):
                assert k in c, f"missing key {k} in category {c.get('id')}"

    def test_packages_list(self):
        r = requests.get(f"{API}/packages")
        assert r.status_code == 200
        pkgs = r.json()
        ids = {p["id"] for p in pkgs}
        assert ids == {"premium_monthly", "premium_yearly"}
        amts = {p["id"]: p["amount"] for p in pkgs}
        assert amts["premium_monthly"] == 9.99
        assert amts["premium_yearly"] == 89.99


# -------- Mascot static assets --------
class TestStaticMascots:
    @pytest.mark.parametrize("cid", CATEGORY_IDS)
    def test_mascot_image(self, cid):
        r = requests.get(f"{API}/static/mascots/{cid}.png")
        assert r.status_code == 200, f"{cid} not 200"
        assert r.headers.get("content-type", "").startswith("image/")
        assert len(r.content) > 5000


# -------- Auth --------
class TestAuth:
    def test_admin_login_sets_cookies(self):
        s = requests.Session()
        r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
        assert r.status_code == 200
        body = r.json()
        assert body["user"]["email"] == ADMIN_EMAIL
        assert body["user"]["plan"] == "premium"
        assert body["user"]["role"] == "admin"
        assert "access_token" in body
        # cookies set
        assert "access_token" in s.cookies
        assert "refresh_token" in s.cookies

    def test_login_wrong_password(self):
        r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": "wrong"})
        assert r.status_code == 401

    def test_me_requires_auth(self):
        r = requests.get(f"{API}/auth/me")
        assert r.status_code == 401

    def test_register_and_me(self):
        s = requests.Session()
        email = f"qa.reg.{int(time.time())}@quizdantan.fr"
        r = s.post(f"{API}/auth/register", json={"name": "Reg User", "email": email, "password": "test1234"})
        assert r.status_code == 200
        u = r.json()["user"]
        assert u["email"] == email
        assert u["plan"] == "free"
        # auth cookie works
        r2 = s.get(f"{API}/auth/me")
        assert r2.status_code == 200
        assert r2.json()["email"] == email

    def test_register_duplicate(self):
        s = requests.Session()
        email = f"qa.dup.{int(time.time())}@quizdantan.fr"
        r = s.post(f"{API}/auth/register", json={"name": "Dup", "email": email, "password": "test1234"})
        assert r.status_code == 200
        r2 = s.post(f"{API}/auth/register", json={"name": "Dup", "email": email, "password": "test1234"})
        assert r2.status_code == 400

    def test_logout_clears_cookies(self):
        s = requests.Session()
        r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
        assert r.status_code == 200
        assert "access_token" in s.cookies
        r2 = s.post(f"{API}/auth/logout")
        assert r2.status_code == 200
        # After logout, accessing /me should fail
        r3 = s.get(f"{API}/auth/me")
        assert r3.status_code == 401


# -------- Quiz gating --------
class TestQuizQuestions:
    def test_questions_require_auth(self):
        r = requests.get(f"{API}/categories/chansons/questions")
        assert r.status_code == 401

    def test_free_user_gets_5_max(self, free_user_session):
        # category with only 4 seeded questions returns 4
        r = free_user_session.get(f"{API}/categories/chansons/questions")
        assert r.status_code == 200
        data = r.json()
        assert data["is_premium"] is False
        assert len(data["questions"]) <= 5
        assert data["category"]["id"] == "chansons"
        # required question structure
        q = data["questions"][0]
        for k in ("id", "question", "options", "correct_index", "explanation"):
            assert k in q
        assert len(q["options"]) == 4

    def test_premium_user_gets_up_to_20(self, admin_session):
        r = admin_session.get(f"{API}/categories/chansons/questions")
        assert r.status_code == 200
        data = r.json()
        assert data["is_premium"] is True
        # seed only has 4 for chansons; ensure limit is enforced upward not downward
        assert len(data["questions"]) <= 20

    def test_invalid_category(self, admin_session):
        r = admin_session.get(f"{API}/categories/does-not-exist/questions")
        assert r.status_code == 404


# -------- Attempts & stats --------
class TestAttempts:
    def test_attempt_and_stats(self, free_user_session):
        # Submit attempt
        payload = {"category_id": "chansons", "score": 3, "total": 4, "duration_seconds": 60}
        r = free_user_session.post(f"{API}/attempts", json=payload)
        assert r.status_code == 200
        assert r.json().get("ok") is True

        # GET attempts
        r2 = free_user_session.get(f"{API}/attempts")
        assert r2.status_code == 200
        rows = r2.json()
        assert any(x["category_id"] == "chansons" and x["score"] == 3 for x in rows)

        # GET stats
        r3 = free_user_session.get(f"{API}/stats")
        assert r3.status_code == 200
        st = r3.json()
        assert st["quizzes_played"] >= 1
        assert st["correct_answers"] >= 3
        assert st["total_answers"] >= 4
        assert 0 <= st["accuracy_pct"] <= 100

    def test_attempts_require_auth(self):
        r = requests.post(f"{API}/attempts", json={"category_id": "chansons", "score": 1, "total": 1})
        assert r.status_code == 401


# -------- Stripe checkout --------
class TestCheckout:
    def test_checkout_requires_auth(self):
        r = requests.post(f"{API}/checkout/session",
                          json={"package_id": "premium_monthly", "origin_url": BASE_URL})
        assert r.status_code == 401

    def test_invalid_package(self, admin_session):
        r = admin_session.post(f"{API}/checkout/session",
                               json={"package_id": "fake", "origin_url": BASE_URL})
        assert r.status_code == 400

    def test_checkout_creates_stripe_session(self, admin_session):
        r = admin_session.post(f"{API}/checkout/session",
                               json={"package_id": "premium_monthly", "origin_url": BASE_URL})
        assert r.status_code == 200, f"checkout failed: {r.status_code} {r.text}"
        body = r.json()
        assert "url" in body
        assert "session_id" in body
        assert "stripe.com" in body["url"], f"unexpected url: {body['url']}"

    def test_checkout_yearly(self, admin_session):
        r = admin_session.post(f"{API}/checkout/session",
                               json={"package_id": "premium_yearly", "origin_url": BASE_URL})
        assert r.status_code == 200
        assert "stripe.com" in r.json()["url"]
