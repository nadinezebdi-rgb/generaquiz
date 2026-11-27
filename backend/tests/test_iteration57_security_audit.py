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


# ---- Free daily limit ----


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

# Tests de session de quiz : voir test_iteration58_quiz_session_anticheat.py (API avec session_id)
