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


# -------- Défi Famille (Challenges) --------
class TestChallenges:
    def test_create_requires_auth(self):
        r = requests.post(f"{API}/challenges", json={"category_id": "chansons", "num_questions": 4})
        assert r.status_code == 401

    def test_create_free_user_gets_402(self, free_user_session):
        r = free_user_session.post(f"{API}/challenges", json={"category_id": "chansons", "num_questions": 4})
        assert r.status_code == 402, f"expected 402, got {r.status_code} {r.text}"
        assert "Premium" in r.json().get("detail", "")

    def test_create_admin_premium(self, admin_session):
        r = admin_session.post(f"{API}/challenges", json={"category_id": "chansons", "num_questions": 4})
        assert r.status_code == 200, f"{r.status_code} {r.text}"
        body = r.json()
        assert "token" in body and len(body["token"]) >= 6
        assert body["total"] == 4  # chansons pool has 4 questions
        assert body["category"]["id"] == "chansons"
        # save for downstream tests
        pytest.shared_token = body["token"]

    def test_create_invalid_category(self, admin_session):
        r = admin_session.post(f"{API}/challenges", json={"category_id": "does-not-exist", "num_questions": 3})
        assert r.status_code == 404

    def test_create_num_questions_validation(self, admin_session):
        # below min
        r = admin_session.post(f"{API}/challenges", json={"category_id": "chansons", "num_questions": 1})
        assert r.status_code == 422
        # above max
        r = admin_session.post(f"{API}/challenges", json={"category_id": "chansons", "num_questions": 50})
        assert r.status_code == 422

    def test_get_public_no_auth_hides_correct_index(self):
        token = getattr(pytest, "shared_token", None)
        assert token, "create test must run first"
        # PUBLIC endpoint - use bare requests (no session/cookies)
        r = requests.get(f"{API}/challenges/{token}")
        assert r.status_code == 200
        body = r.json()
        assert body["token"] == token
        assert body["category_id"] == "chansons"
        assert body["creator_name"]
        assert body["total"] == 4
        assert isinstance(body["questions"], list)
        # Anti-cheat: NO correct_index in any question
        for q in body["questions"]:
            assert "correct_index" not in q, f"LEAK: correct_index present in question {q.get('id')}"
            assert "explanation" not in q, f"LEAK: explanation present in question {q.get('id')}"
            assert "id" in q and "question" in q and "options" in q
            assert len(q["options"]) == 4
        # category meta
        assert body.get("category_title")
        assert body.get("category_mascot_image")

    def test_get_unknown_token_404(self):
        r = requests.get(f"{API}/challenges/nonexistent_token_xyz")
        assert r.status_code == 404

    def test_participate_public_no_auth(self):
        token = getattr(pytest, "shared_token", None)
        assert token
        # fetch question count
        meta = requests.get(f"{API}/challenges/{token}").json()
        n = meta["total"]
        # All zeros guess
        payload = {"name": "Mamie Test", "answers": [0] * n, "duration_seconds": 42}
        r = requests.post(f"{API}/challenges/{token}/participate", json=payload)
        assert r.status_code == 200, f"{r.status_code} {r.text}"
        body = r.json()
        assert body["total"] == n
        assert 0 <= body["score"] <= n
        assert isinstance(body["detail"], list) and len(body["detail"]) == n
        for d in body["detail"]:
            assert "question_id" in d
            assert "chosen" in d
            assert "correct_index" in d  # detail must include for review
            assert "is_correct" in d
        assert isinstance(body["leaderboard"], list)
        assert any(p["name"] == "Mamie Test" for p in body["leaderboard"])

    def test_participate_wrong_answers_length_400(self):
        token = getattr(pytest, "shared_token", None)
        r = requests.post(f"{API}/challenges/{token}/participate",
                          json={"name": "Bad", "answers": [0, 1], "duration_seconds": 5})
        assert r.status_code == 400

    def test_participate_unknown_token_404(self):
        r = requests.post(f"{API}/challenges/nope_token/participate",
                          json={"name": "X", "answers": [0, 0, 0, 0]})
        assert r.status_code == 404

    def test_participate_perfect_score(self, admin_session):
        # Create a fresh challenge as admin then play it with the correct answers
        r = admin_session.post(f"{API}/challenges", json={"category_id": "cinema", "num_questions": 4})
        assert r.status_code == 200
        token = r.json()["token"]
        # Get correct answers from admin (premium) via authenticated endpoint /challenges/mine OR by reading questions
        # Strategy: admin can read seed answers via /categories/{id}/questions
        # But challenge questions are randomly chosen subset; we must map by id
        all_qs = admin_session.get(f"{API}/categories/cinema/questions").json()["questions"]
        by_id = {q["id"]: q["correct_index"] for q in all_qs}
        public = requests.get(f"{API}/challenges/{token}").json()
        correct = [by_id[q["id"]] for q in public["questions"]]
        rp = requests.post(f"{API}/challenges/{token}/participate",
                           json={"name": "Champion", "answers": correct, "duration_seconds": 30})
        assert rp.status_code == 200
        body = rp.json()
        assert body["score"] == body["total"]
        # leaderboard top entry is Champion (best score, lowest time)
        top = body["leaderboard"][0]
        assert top["name"] == "Champion"
        assert top["score"] == body["total"]

    def test_list_mine_requires_auth(self):
        r = requests.get(f"{API}/challenges/mine")
        assert r.status_code == 401

    def test_list_mine_returns_creator_challenges(self, admin_session):
        r = admin_session.get(f"{API}/challenges/mine")
        assert r.status_code == 200
        rows = r.json()
        assert isinstance(rows, list)
        assert len(rows) >= 1
        # sorted desc by created_at
        if len(rows) >= 2:
            assert rows[0]["created_at"] >= rows[1]["created_at"]
        # correct_index must NOT appear in any question
        for ch in rows:
            assert "total_questions" in ch
            assert isinstance(ch.get("participants", []), list)
            for q in ch.get("questions", []):
                assert "correct_index" not in q
                assert "explanation" not in q

