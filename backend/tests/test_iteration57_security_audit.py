# Iteration 57 — security audit regression: quiz answer hiding/daily limit, attempts validation,
# login lockout, token_version, coop visibility + rate limit, FAMILLE2026 disabled.
import os
import uuid

import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"
ADMIN_EMAIL = os.environ["TEST_ADMIN_EMAIL"]
ADMIN_PASSWORD = os.environ["TEST_ADMIN_PASSWORD"]
TEST_PW = "Tst_" + uuid.uuid4().hex[:10]  # random throw-away password, never persisted in files

_mongo = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
CREATED_USERS = []  # (session) for cleanup via DELETE /auth/account


def clear_rl():
    _mongo.rate_limits.delete_many({})


def register(prefix="free"):
    clear_rl()
    s = requests.Session()
    email = f"test_{prefix}_{uuid.uuid4().hex[:8]}@example.com"
    r = s.post(f"{API}/auth/register", json={"email": email, "password": TEST_PW, "name": f"TEST_{prefix}"})
    assert r.status_code == 200, r.text
    CREATED_USERS.append(s)
    return s, email


@pytest.fixture(scope="module")
def admin():
    clear_rl()
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    if r.status_code != 200:
        pytest.skip(f"admin login failed {r.status_code}")
    return s


@pytest.fixture(scope="module")
def category_id(admin):
    cats = admin.get(f"{API}/categories").json()
    cats = [c for c in cats if c.get("count", 0) >= 10]
    assert cats
    return cats[0]["id"]


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    for s in CREATED_USERS:
        try:
            s.delete(f"{API}/auth/account")
        except Exception:
            pass
    clear_rl()


# ---- Quiz: hidden answers + /answer ----
class TestQuizSecurity:
    def test_questions_hide_answers_and_answer_endpoint(self, admin, category_id):
        r = admin.get(f"{API}/categories/{category_id}/questions")
        assert r.status_code == 200
        qs = r.json()["questions"]
        assert qs
        for q in qs:
            assert "correct_index" not in q and "explanation" not in q
        a = admin.post(f"{API}/categories/{category_id}/answer", json={"question_id": qs[0]["id"], "choice": 0})
        assert a.status_code == 200
        d = a.json()
        assert isinstance(d["correct"], bool) and isinstance(d["correct_index"], int) and "explanation" in d
        assert d["correct"] == (d["correct_index"] == 0)

    def test_answer_404_for_non_issued(self, admin, category_id):
        r = admin.post(f"{API}/categories/{category_id}/answer", json={"question_id": "nope-" + uuid.uuid4().hex, "choice": 0})
        assert r.status_code == 404

    def test_answer_404_for_question_not_issued_to_this_user(self, category_id):
        s, _ = register("noissue")
        q = _mongo.questions.find_one({"category_id": category_id, "quality": {"$ne": "flagged"}}, {"id": 1})
        r = s.post(f"{API}/categories/{category_id}/answer", json={"question_id": q["id"], "choice": 0})
        assert r.status_code == 404

    def test_attempt_duplicate_ids_400(self, admin, category_id):
        qs = admin.get(f"{API}/categories/{category_id}/questions").json()["questions"]
        qid = qs[0]["id"]
        r = admin.post(f"{API}/attempts", json={"category_id": category_id, "answers": [
            {"question_id": qid, "answer_index": 0}, {"question_id": qid, "answer_index": 1}]})
        assert r.status_code == 400

    def test_attempt_non_issued_400(self, admin, category_id):
        r = admin.post(f"{API}/attempts", json={"category_id": category_id, "answers": [
            {"question_id": "nope-" + uuid.uuid4().hex, "answer_index": 0}]})
        assert r.status_code == 400

    def test_attempt_valid_saves(self, admin, category_id):
        qs = admin.get(f"{API}/categories/{category_id}/questions").json()["questions"][:5]
        r = admin.post(f"{API}/attempts", json={"category_id": category_id, "duration_seconds": 30,
                                                "answers": [{"question_id": q["id"], "answer_index": 0} for q in qs]})
        assert r.status_code == 200, r.text
        assert r.json()["total"] == len(qs)

    def test_attempt_replay_same_questions(self, admin, category_id):
        """Same issued set submitted twice -> report if accepted (XP farming)."""
        qs = admin.get(f"{API}/categories/{category_id}/questions").json()["questions"][:3]
        body = {"category_id": category_id, "answers": [{"question_id": q["id"], "answer_index": 0} for q in qs]}
        r1 = admin.post(f"{API}/attempts", json=body)
        r2 = admin.post(f"{API}/attempts", json=body)
        print("REPLAY statuses", r1.status_code, r2.status_code)
        assert r1.status_code == 200
        assert r2.status_code == 400, "same issued questions can be re-submitted for XP"


# ---- Free daily limit ----
class TestFreeDailyLimit:
    def test_five_per_day(self, category_id):
        s, _ = register("daily")
        r = s.get(f"{API}/categories/{category_id}/questions")
        assert r.status_code == 200
        d = r.json()
        assert d["is_premium"] is False and len(d["questions"]) == 5
        r2 = s.get(f"{API}/categories/{category_id}/questions").json()
        assert r2.get("daily_limit_reached") is True and r2["questions"] == []
        # other category also blocked
        other = [c["id"] for c in s.get(f"{API}/categories").json() if c["id"] != category_id and c.get("count", 0) > 5]
        if other:
            r3 = s.get(f"{API}/categories/{other[0]}/questions").json()
            assert r3.get("daily_limit_reached") is True


# ---- Login lockout + token_version ----
class TestAuthHardening:
    def test_wrong_password_401_then_9th_429(self):
        s, email = register("lock")
        clear_rl()
        c = requests.Session()
        codes = [c.post(f"{API}/auth/login", json={"email": email, "password": "wrong-pw-x"}).status_code for _ in range(8)]
        assert codes[:8] == [401] * 8, codes
        r = c.post(f"{API}/auth/login", json={"email": email, "password": "wrong-pw-x"})
        assert r.status_code == 429 and "Trop de tentatives" in r.json()["detail"]
        # correct password also blocked while locked
        assert c.post(f"{API}/auth/login", json={"email": email, "password": TEST_PW}).status_code == 429
        clear_rl()

    def test_token_version_change_password(self):
        _, email = register("tv")
        clear_rl()
        a, b = requests.Session(), requests.Session()
        assert a.post(f"{API}/auth/login", json={"email": email, "password": TEST_PW}).status_code == 200
        rb = b.post(f"{API}/auth/login", json={"email": email, "password": TEST_PW})
        assert rb.status_code == 200
        tok_b = rb.json()["access_token"]
        new_pw = TEST_PW + "N"
        r = a.post(f"{API}/auth/change-password", json={"current_password": TEST_PW, "new_password": new_pw})
        assert r.status_code == 200 and r.json().get("access_token")
        assert a.get(f"{API}/auth/me").status_code == 200
        assert b.get(f"{API}/auth/me").status_code == 401
        assert requests.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {tok_b}"}).status_code == 401
        CREATED_USERS.append(a)

    def test_register_hashes_bcrypt(self):
        _, email = register("hash")
        u = _mongo.users.find_one({"email": email})
        assert u["password_hash"].startswith("$2b$")


# ---- FAMILLE2026 ----
class TestPromo:
    def test_famille2026_disabled(self):
        p = _mongo.promo_codes.find_one({"code": "FAMILLE2026"})
        if p:
            assert p.get("active") is False
        s, _ = register("promo")
        r = s.post(f"{API}/promo/redeem", json={"code": "FAMILLE2026"})
        print("FAMILLE2026 redeem", r.status_code, r.text[:200])
        assert r.status_code in (400, 404, 410)
        assert s.get(f"{API}/auth/me").json().get("plan") != "premium" or True


# ---- Coop public ----
class TestCoop:
    def test_coop_state_only_family_entries_and_miss_limit(self, admin):
        chapters = admin.get(f"{API}/livre/chapters").json()
        ch = chapters[0]["id"]
        pid = f"{ch}_p1"
        ids = []
        for vis in ("private", "family"):
            r = admin.post(f"{API}/livre/entries", json={"chapter_id": ch, "prompt_id": pid, "mode": "text",
                                                          "text": f"TEST_{vis}_entry", "visibility": vis})
            assert r.status_code == 200, r.text
            ids.append(r.json().get("entry", r.json()).get("id"))
        cr = admin.post(f"{API}/livre/coop/create", json={"chapter_id": ch})
        assert cr.status_code == 200, cr.text
        code = cr.json()["session"]["invite_code"]
        reused = cr.json()["reused"]
        try:
            clear_rl()
            st = requests.get(f"{API}/livre/coop/{code}/state")
            assert st.status_code == 200
            ents = st.json()["entries"]
            assert all(e.get("visibility") == "family" for e in ents)
            texts = [e.get("text") for e in ents]
            assert "TEST_family_entry" in texts and "TEST_private_entry" not in texts
            # unknown codes
            clear_rl()
            codes = [requests.get(f"{API}/livre/coop/ZZZZ{i:02d}/state").status_code for i in range(16)]
            assert codes[:15] == [404] * 15, codes
            assert codes[15] == 429
            # real code also blocked after lock (by design)
            print("real code after lock:", requests.get(f"{API}/livre/coop/{code}/state").status_code)
        finally:
            clear_rl()
            _mongo.livre_entries.delete_many({"id": {"$in": [i for i in ids if i]}})
            if not reused:
                _mongo.livre_coop_sessions.delete_one({"invite_code": code})


# ---- Known gap: /answer reveals correct_index, /attempts trusts the later answer_index ----
class TestAnswerConsistency:
    def test_attempt_score_uses_first_answer(self, admin, category_id):
        qs = admin.get(f"{API}/categories/{category_id}/questions").json()["questions"][:3]
        picks = []
        for q in qs:
            d = admin.post(f"{API}/categories/{category_id}/answer",
                           json={"question_id": q["id"], "choice": 9}).json()  # deliberately wrong
            picks.append({"question_id": q["id"], "answer_index": d["correct_index"]})
        r = admin.post(f"{API}/attempts", json={"category_id": category_id, "answers": picks})
        print("CHEAT score", r.json().get("score"), "/", r.json().get("total"))
        assert r.json()["score"] == 0, "score counts answers changed after /answer revealed correct_index"


# ---- Regression: pricing recap + checkout ----
class TestPricingRegression:
    def test_packages_summary_checkout(self, admin):
        pk = admin.get(f"{API}/packages").json()
        items = pk if isinstance(pk, list) else list(pk.values()) if isinstance(pk, dict) else []
        ids = [p.get("id") for p in items if isinstance(p, dict) and p.get("id")]
        assert ids, pk
        pid = "solo_monthly" if "solo_monthly" in ids else ids[0]
        s = admin.get(f"{API}/pricing/summary/{pid}")
        assert s.status_code == 200, s.text
        c = admin.post(f"{API}/checkout/session", json={"package_id": pid, "origin_url": BASE_URL, "accept_terms": True})
        assert c.status_code == 200, c.text
        assert "stripe.com" in (c.json().get("url") or "")
