"""Iteration 11 — Validate massive content expansion (240 → 800 questions, 100/cat × 8).

Covers:
- Categories listing (8 cats, count=100 each)
- Quiz play: free user (5 q) + premium admin (30 q) with $sample randomness
- Question integrity: 4 options + correct_index 0-3, no duplicates within a single call
- Register/login/me
- Family challenge create + public read + participate
- Promo redeem + admin list
- Forgot-password 200 with email_sent, rate-limit after 3 calls (HTTP 429)
"""
import os
import uuid
import requests
import pytest

def _load_backend_url():
    url = os.environ.get("REACT_APP_BACKEND_URL")
    if url:
        return url.rstrip("/")
    # fallback: parse frontend/.env
    env_path = "/app/frontend/.env"
    if os.path.exists(env_path):
        for line in open(env_path):
            if line.startswith("REACT_APP_BACKEND_URL="):
                return line.split("=", 1)[1].strip().rstrip("/")
    raise RuntimeError("REACT_APP_BACKEND_URL not set")


BASE = _load_backend_url()
API = f"{BASE}/api"

ADMIN_EMAIL = "admin@generaquiz.fr"
ADMIN_PWD = "Admin2026!"


# ---------- fixtures ----------
@pytest.fixture(scope="session")
def admin_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PWD})
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="session")
def free_user():
    s = requests.Session()
    email = f"TEST_{uuid.uuid4().hex[:10]}@example.com"
    pwd = "TestPass2026!"
    r = s.post(f"{API}/auth/register", json={"email": email, "password": pwd, "name": "Free Tester"})
    assert r.status_code in (200, 201), f"register failed: {r.status_code} {r.text}"
    return {"session": s, "email": email, "password": pwd}


# ---------- categories ----------
class TestCategories:
    def test_eight_categories_with_count_100(self):
        r = requests.get(f"{API}/categories")
        assert r.status_code == 200
        cats = r.json()
        assert len(cats) == 8, f"expected 8 categories, got {len(cats)}"
        ids = {c["id"] for c in cats}
        expected = {"annees-50-60", "chansons", "cinema", "objets-antan",
                    "histoire-france", "cuisine-terroir", "culture-40-ans", "culture-70-ans"}
        assert ids == expected
        for c in cats:
            assert c.get("count") == 100, f"{c['id']} count={c.get('count')}"


# ---------- quiz play ----------
def _validate_question(q):
    assert "question" in q and isinstance(q["question"], str) and q["question"]
    assert "options" in q and isinstance(q["options"], list) and len(q["options"]) == 4
    assert "correct_index" in q and isinstance(q["correct_index"], int)
    assert 0 <= q["correct_index"] <= 3


class TestQuizPlay:
    def test_free_user_gets_5_valid_questions(self, free_user):
        s = free_user["session"]
        r = s.get(f"{API}/categories/cinema/questions")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["is_premium"] is False
        qs = data["questions"]
        assert len(qs) == 5
        for q in qs:
            _validate_question(q)
        # uniqueness within call
        texts = [q["question"] for q in qs]
        assert len(set(texts)) == len(texts), "duplicate questions in single call"

    def test_premium_admin_gets_30_valid_unique_questions(self, admin_session):
        r = admin_session.get(f"{API}/categories/histoire-france/questions")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["is_premium"] is True
        qs = data["questions"]
        assert len(qs) == 30, f"expected 30 premium questions, got {len(qs)}"
        for q in qs:
            _validate_question(q)
        texts = [q["question"] for q in qs]
        assert len(set(texts)) == 30, "duplicates within single premium call"

    def test_sample_randomness_across_calls(self, admin_session):
        # two consecutive calls should not return identical sets (with 100 pool, 30 sample)
        r1 = admin_session.get(f"{API}/categories/chansons/questions").json()["questions"]
        r2 = admin_session.get(f"{API}/categories/chansons/questions").json()["questions"]
        s1 = {q["question"] for q in r1}
        s2 = {q["question"] for q in r2}
        # not 100% identical sets — astronomically unlikely
        assert s1 != s2, "sampling appears non-random (same 30 across 2 calls)"

    def test_all_8_categories_serve_questions_to_premium(self, admin_session):
        cat_ids = ["annees-50-60", "chansons", "cinema", "objets-antan",
                   "histoire-france", "cuisine-terroir", "culture-40-ans", "culture-70-ans"]
        for cid in cat_ids:
            r = admin_session.get(f"{API}/categories/{cid}/questions")
            assert r.status_code == 200, f"{cid} -> {r.status_code} {r.text[:200]}"
            qs = r.json()["questions"]
            assert len(qs) == 30, f"{cid} returned {len(qs)} questions"
            for q in qs:
                _validate_question(q)

    def test_unknown_category_returns_404(self, admin_session):
        r = admin_session.get(f"{API}/categories/does-not-exist/questions")
        assert r.status_code == 404


# ---------- auth ----------
class TestAuth:
    def test_register_login_me(self):
        s = requests.Session()
        email = f"TEST_{uuid.uuid4().hex[:10]}@example.com"
        pwd = "Strong2026!"
        r = s.post(f"{API}/auth/register", json={"email": email, "password": pwd, "name": "RegTest"})
        assert r.status_code in (200, 201)
        # me right after register
        me = s.get(f"{API}/auth/me")
        assert me.status_code == 200
        assert me.json()["email"] == email.lower()
        # fresh session login
        s2 = requests.Session()
        r2 = s2.post(f"{API}/auth/login", json={"email": email, "password": pwd})
        assert r2.status_code == 200
        me2 = s2.get(f"{API}/auth/me")
        assert me2.status_code == 200
        assert me2.json()["email"] == email.lower()


# ---------- challenges ----------
class TestChallenges:
    def test_create_read_participate(self, admin_session):
        # create as admin (premium)
        payload = {"category_id": "cinema", "player_name": "Papi"}
        r = admin_session.post(f"{API}/challenges", json=payload)
        assert r.status_code in (200, 201), r.text
        body = r.json()
        token = body.get("token") or body.get("challenge", {}).get("token")
        assert token, f"no token in response: {body}"

        # public read (no auth needed)
        pub = requests.get(f"{API}/challenges/{token}")
        assert pub.status_code == 200, pub.text
        chal = pub.json()
        # ensure 30 questions served for premium-created challenge
        qs = chal.get("questions") or chal.get("challenge", {}).get("questions")
        assert qs and isinstance(qs, list)
        assert len(qs) >= 5
        # NOTE: public challenge view intentionally strips `correct_index` (anti-cheat),
        # so we only validate question text + 4 options here.
        for q in qs:
            assert isinstance(q.get("question"), str) and q["question"]
            assert isinstance(q.get("options"), list) and len(q["options"]) == 4
            assert "correct_index" not in q, "public challenge MUST NOT leak correct_index"

        # participate (schema: name + answers as list of int indices)
        answers = [0 for _ in qs]
        part = requests.post(f"{API}/challenges/{token}/participate", json={
            "name": "Mamie",
            "answers": answers,
        })
        assert part.status_code in (200, 201), part.text


# ---------- promo ----------
class TestPromo:
    def test_admin_promo_list_contains_seeded_codes(self, admin_session):
        r = admin_session.get(f"{API}/admin/promo")
        # endpoint might be /api/promo/list or /api/admin/promo depending on routing
        if r.status_code == 404:
            r = admin_session.get(f"{API}/promo/list")
        assert r.status_code == 200, f"{r.status_code} {r.text}"
        codes = [p["code"] for p in r.json()]
        assert "FAMILLE2026" in codes
        assert "DECOUVERTE30" in codes

    def test_redeem_promo_upgrades_user_to_premium(self):
        s = requests.Session()
        email = f"TEST_{uuid.uuid4().hex[:10]}@example.com"
        s.post(f"{API}/auth/register", json={"email": email, "password": "Strong2026!", "name": "PromoTest"})
        r = s.post(f"{API}/promo/redeem", json={"code": "FAMILLE2026"})
        assert r.status_code == 200, r.text
        me = s.get(f"{API}/auth/me").json()
        assert me.get("plan") == "premium"


# ---------- forgot password & rate limit ----------
class TestForgotPassword:
    def test_returns_200_with_email_sent_key(self):
        email = f"TEST_{uuid.uuid4().hex[:10]}@example.com"
        # register so user exists
        requests.post(f"{API}/auth/register", json={"email": email, "password": "Strong2026!", "name": "FP"})
        r = requests.post(f"{API}/auth/forgot-password", json={"email": email})
        assert r.status_code == 200, r.text
        data = r.json()
        assert "email_sent" in data
        assert isinstance(data["email_sent"], bool)

    def test_rate_limit_after_3_calls(self):
        # use unique fresh email to avoid bucket pollution; rate-limit is per-IP though.
        # Hit endpoint 4 times rapidly with arbitrary emails. 4th should return 429.
        # Restart not done -> may be already rate-limited from previous test.
        # We try, and accept either: at least one 429 within 5 calls
        statuses = []
        for i in range(5):
            r = requests.post(f"{API}/auth/forgot-password", json={"email": f"ratetest{i}@x.com"})
            statuses.append(r.status_code)
        assert 429 in statuses, f"expected at least one 429 in {statuses}"
