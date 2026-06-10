"""Pytest suite — Quiz du Jour (daily challenge).

Order-sensitive: each authenticated user can submit only once per day.
Tests are ordered to follow: anon GET → admin GET → admin submit → admin dup → new user submit → leaderboard.
"""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://caricature-saas.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@generaquiz.fr"
ADMIN_PASSWORD = "Admin2026!"


@pytest.fixture(scope="module")
def anon():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def admin_token(anon):
    r = anon.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    tok = r.json().get("access_token") or r.json().get("token")
    assert tok, f"no access_token in login resp: {r.json()}"
    return tok


@pytest.fixture(scope="module")
def admin_client(admin_token):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json", "Authorization": f"Bearer {admin_token}"})
    return s


# -------------------- Public GET /api/daily/quiz --------------------
class TestDailyQuizPublic:
    def test_anon_get_quiz_shape(self, anon):
        r = anon.get(f"{API}/daily/quiz")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["is_authenticated"] is False
        assert data["has_played"] is False
        assert "date" in data and len(data["date"]) == 10  # YYYY-MM-DD
        assert data["count"] == 5
        assert len(data["questions"]) == 5
        for q in data["questions"]:
            assert "question" in q and "options" in q and "correct_index" in q
            assert len(q["options"]) == 4
            assert 0 <= q["correct_index"] <= 3

    def test_deterministic_same_questions(self, anon):
        r1 = anon.get(f"{API}/daily/quiz").json()
        r2 = anon.get(f"{API}/daily/quiz").json()
        ids1 = [q.get("id") for q in r1["questions"]]
        ids2 = [q.get("id") for q in r2["questions"]]
        assert ids1 == ids2, f"ids differ across calls: {ids1} vs {ids2}"
        assert r1["date"] == r2["date"]


# -------------------- Auth required for submit --------------------
class TestDailySubmitAuth:
    def test_submit_without_auth_401(self, anon):
        r = anon.post(f"{API}/daily/submit", json={"score": 3, "duration_seconds": 30})
        assert r.status_code in (401, 403), r.text


# -------------------- Admin flow --------------------
class TestDailyAdminFlow:
    def test_admin_get_quiz_authenticated(self, admin_client):
        r = admin_client.get(f"{API}/daily/quiz")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["is_authenticated"] is True
        assert data["has_played"] is False  # collection vidée juste avant ce test

    def test_admin_submit_score_4(self, admin_client):
        r = admin_client.post(f"{API}/daily/submit", json={"score": 4, "duration_seconds": 42})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body == {"ok": True, "saved": True}

    def test_admin_submit_again_409(self, admin_client):
        r = admin_client.post(f"{API}/daily/submit", json={"score": 5, "duration_seconds": 20})
        assert r.status_code == 409
        assert "déjà joué" in r.json().get("detail", "").lower() or "deja" in r.json().get("detail", "").lower()

    def test_admin_has_played_now_true(self, admin_client):
        r = admin_client.get(f"{API}/daily/quiz")
        assert r.status_code == 200
        assert r.json()["has_played"] is True


# -------------------- Invalid payload --------------------
class TestDailySubmitValidation:
    @pytest.mark.parametrize("bad_score", [99, -1, 10])
    def test_invalid_score_422(self, admin_client, bad_score):
        # admin already submitted today, but Pydantic validation rejects BEFORE the dup check.
        r = admin_client.post(f"{API}/daily/submit", json={"score": bad_score, "duration_seconds": 10})
        assert r.status_code == 422, f"expected 422 got {r.status_code}: {r.text}"


# -------------------- Leaderboard --------------------
class TestDailyLeaderboard:
    def test_leaderboard_anon(self):
        # Use a brand-new session — the module-scoped `anon` accumulated cookies from login.
        s = requests.Session()
        r = s.get(f"{API}/daily/leaderboard")
        assert r.status_code == 200
        data = r.json()
        assert "top" in data and isinstance(data["top"], list)
        assert "total_players" in data
        assert data["my_rank"] is None
        assert data["my_entry"] is None

    def test_leaderboard_admin_after_submit(self, admin_client):
        r = admin_client.get(f"{API}/daily/leaderboard")
        assert r.status_code == 200
        data = r.json()
        assert data["my_rank"] == 1, f"expected admin rank 1, got {data['my_rank']}"
        assert data["my_entry"] is not None
        assert data["my_entry"]["score"] == 4

    def test_new_user_with_higher_score_takes_rank_1(self, anon):
        # Register a fresh user
        email = f"TEST_daily_{uuid.uuid4().hex[:8]}@example.com"
        password = "TestPass2026!"
        rr = anon.post(f"{API}/auth/register", json={
            "email": email, "password": password, "name": "Daily Tester"
        })
        assert rr.status_code in (200, 201), f"register failed: {rr.status_code} {rr.text}"
        # Login to get token
        lr = anon.post(f"{API}/auth/login", json={"email": email, "password": password})
        assert lr.status_code == 200, lr.text
        token = lr.json().get("access_token") or lr.json().get("token")
        assert token
        s = requests.Session()
        s.headers.update({"Content-Type": "application/json", "Authorization": f"Bearer {token}"})

        sub = s.post(f"{API}/daily/submit", json={"score": 5, "duration_seconds": 30})
        assert sub.status_code == 200, sub.text

        lb = s.get(f"{API}/daily/leaderboard").json()
        assert lb["my_rank"] == 1, f"new user should be #1, got {lb['my_rank']}"
        assert lb["my_entry"]["score"] == 5
        # Admin should now be ranked 2
        # The top list should contain at least 2 entries with new user first
        assert len(lb["top"]) >= 2
        assert lb["top"][0]["score"] == 5
        assert lb["top"][1]["score"] == 4
