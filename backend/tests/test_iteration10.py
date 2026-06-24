"""Iteration 10 — refactor regression + rate-limit on /api/auth/forgot-password.

Covers:
- Auth: register/login/me/logout/forgot/reset/change-password/profile/account
- Quiz: categories, questions, attempts, stats
- Payments: packages
- Challenges: admin create, mine, public get, participate
- Promo: admin CRUD + redeem
- Static mascots
- Rate-limit (3 calls / 15 min) on forgot-password and isolation
"""
import os
import time
import uuid
import pytest
import requests

def _load_frontend_env():
    p = "/app/frontend/.env"
    if os.path.exists(p):
        for line in open(p):
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.strip().split("=", 1)
                os.environ.setdefault(k, v)

_load_frontend_env()
BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
ADMIN_EMAIL = "admin@quizdantan.fr"
ADMIN_PWD = "Admin2026!"


@pytest.fixture(scope="module")
def s():
    return requests.Session()


@pytest.fixture(scope="module")
def admin_session():
    sess = requests.Session()
    r = sess.post(f"{BASE}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PWD})
    assert r.status_code == 200, r.text
    sess.headers.update({"Authorization": f"Bearer {r.json()['access_token']}"})
    return sess


@pytest.fixture(scope="module")
def fresh_user():
    sess = requests.Session()
    email = f"TEST_{uuid.uuid4().hex[:10]}@example.com"
    pwd = "Pwd12345!"
    r = sess.post(f"{BASE}/api/auth/register", json={"email": email, "password": pwd, "name": "Tester"})
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    sess.headers.update({"Authorization": f"Bearer {token}"})
    return {"sess": sess, "email": email, "password": pwd, "id": r.json()["user"]["id"]}


# -------- root --------
def test_api_root(s):
    r = s.get(f"{BASE}/api/")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# -------- auth router --------
def test_auth_me(admin_session):
    r = admin_session.get(f"{BASE}/api/auth/me")
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == ADMIN_EMAIL
    assert body["role"] == "admin"


def test_auth_login_wrong_pwd(s):
    r = s.post(f"{BASE}/api/auth/login", json={"email": ADMIN_EMAIL, "password": "wrong"})
    assert r.status_code == 401


def test_auth_logout(fresh_user):
    sess = requests.Session()
    r = sess.post(f"{BASE}/api/auth/login",
                  json={"email": fresh_user["email"], "password": fresh_user["password"]})
    assert r.status_code == 200
    r2 = sess.post(f"{BASE}/api/auth/logout")
    assert r2.status_code == 200


def test_auth_profile_patch(fresh_user):
    r = fresh_user["sess"].patch(f"{BASE}/api/auth/profile", json={"name": "RenamedTester"})
    assert r.status_code == 200
    assert r.json()["name"] == "RenamedTester"
    # verify via /me
    r2 = fresh_user["sess"].get(f"{BASE}/api/auth/me")
    assert r2.json()["name"] == "RenamedTester"


def test_auth_change_password(fresh_user):
    new = "NewPwd99!"
    r = fresh_user["sess"].post(f"{BASE}/api/auth/change-password",
                                json={"current_password": fresh_user["password"], "new_password": new})
    assert r.status_code == 200
    # login with new password
    sess2 = requests.Session()
    r2 = sess2.post(f"{BASE}/api/auth/login", json={"email": fresh_user["email"], "password": new})
    assert r2.status_code == 200
    fresh_user["password"] = new


# -------- quiz router --------
def test_quiz_categories(s):
    r = s.get(f"{BASE}/api/categories")
    assert r.status_code == 200
    cats = r.json()
    assert len(cats) == 8, f"expected 8 categories, got {len(cats)}"


def test_quiz_questions_free_user(fresh_user):
    # free user gets limited questions on premium categories (but should still work for at least one)
    r = fresh_user["sess"].get(f"{BASE}/api/categories")
    assert r.status_code == 200
    cat_id = r.json()[0]["id"]
    r2 = fresh_user["sess"].get(f"{BASE}/api/categories/{cat_id}/questions")
    assert r2.status_code == 200
    data = r2.json()
    assert isinstance(data, dict) and "questions" in data


def test_quiz_questions_premium(admin_session):
    cats = admin_session.get(f"{BASE}/api/categories").json()
    r = admin_session.get(f"{BASE}/api/categories/{cats[0]['id']}/questions")
    assert r.status_code == 200
    qs = r.json().get("questions", [])
    assert len(qs) > 0


def test_quiz_attempts_and_stats(fresh_user):
    cats = fresh_user["sess"].get(f"{BASE}/api/categories").json()
    payload = {"category_id": cats[0]["id"], "score": 4, "total": 5, "duration_seconds": 60}
    r = fresh_user["sess"].post(f"{BASE}/api/attempts", json=payload)
    assert r.status_code == 200, r.text
    r2 = fresh_user["sess"].get(f"{BASE}/api/stats")
    assert r2.status_code == 200
    stats = r2.json()
    assert stats.get("quizzes_played", 0) >= 1


# -------- payments router --------
def test_payments_packages(s):
    r = s.get(f"{BASE}/api/packages")
    assert r.status_code == 200
    pkgs = r.json()
    # Should be dict or list with premium_monthly + premium_yearly
    raw = pkgs if isinstance(pkgs, dict) else {p.get("id"): p for p in pkgs}
    assert "premium_monthly" in raw or any("monthly" in str(k) for k in raw)


# -------- challenges router --------
def test_challenges_admin_create_and_mine(admin_session):
    cats = admin_session.get(f"{BASE}/api/categories").json()
    r = admin_session.post(f"{BASE}/api/challenges",
                            json={"category_id": cats[0]["id"], "num_questions": 5})
    assert r.status_code == 200, r.text
    token = r.json()["token"]
    # mine
    r2 = admin_session.get(f"{BASE}/api/challenges/mine")
    assert r2.status_code == 200
    assert any(c["token"] == token for c in r2.json())
    # public get
    r3 = requests.get(f"{BASE}/api/challenges/{token}")
    assert r3.status_code == 200
    pub = r3.json()
    assert "questions" in pub
    # participate
    answers = [0] * len(pub["questions"])
    r4 = requests.post(f"{BASE}/api/challenges/{token}/participate",
                       json={"name": "TestGuest", "answers": answers, "duration_seconds": 90})
    assert r4.status_code == 200, r4.text


# -------- promo router --------
def test_promo_admin_list_contains_seeded(admin_session):
    r = admin_session.get(f"{BASE}/api/admin/promo")
    assert r.status_code == 200
    codes = [p["code"] for p in r.json()]
    assert "FAMILLE2026" in codes
    assert "DECOUVERTE30" in codes


def test_promo_admin_crud(admin_session):
    new_code = f"TEST_{uuid.uuid4().hex[:6].upper()}"
    r = admin_session.post(f"{BASE}/api/admin/promo",
                            json={"code": new_code, "duration_days": 7, "max_uses": 5,
                                  "label": "Test code"})
    assert r.status_code == 200, r.text
    promo_id = r.json().get("id") or r.json().get("_id")
    # delete
    if promo_id:
        rd = admin_session.delete(f"{BASE}/api/admin/promo/{promo_id}")
        assert rd.status_code in (200, 204)


def test_promo_redeem(fresh_user):
    r = fresh_user["sess"].post(f"{BASE}/api/promo/redeem", json={"code": "FAMILLE2026"})
    assert r.status_code == 200, r.text
    # verify plan upgraded
    me = fresh_user["sess"].get(f"{BASE}/api/auth/me").json()
    assert me["plan"] == "premium"


# -------- static mascots --------
def test_static_mascots():
    cats_ids = ["cinema", "chansons", "histoire-france", "objets-antan",
                "cuisine-terroir", "annees-50-60", "culture-40-ans", "culture-70-ans"]
    for cid in cats_ids:
        r = requests.get(f"{BASE}/api/static/mascots/{cid}.png")
        assert r.status_code == 200, f"mascot {cid} missing"
        assert r.headers.get("content-type", "").startswith("image/")


# -------- rate-limit on /api/auth/forgot-password --------
# Note: rate-limit is process-local in-memory, so requires fresh backend or unused budget.
# We restart backend at the start of this test class to clear buckets.
class TestRateLimit:
    @classmethod
    def setup_class(cls):
        # Clear the rate-limit buckets by restarting backend
        os.system("sudo supervisorctl restart backend > /dev/null 2>&1")
        # wait for backend ready
        for _ in range(30):
            try:
                r = requests.get(f"{BASE}/api/", timeout=2)
                if r.status_code == 200:
                    break
            except Exception:
                pass
            time.sleep(1)

    def test_forgot_pw_first_3_ok_then_429(self):
        email = f"unknown_{uuid.uuid4().hex[:6]}@example.com"
        statuses = []
        for _ in range(3):
            r = requests.post(f"{BASE}/api/auth/forgot-password", json={"email": email})
            statuses.append(r.status_code)
        assert statuses == [200, 200, 200], f"first 3 should be 200, got {statuses}"
        # 4th must be 429
        r4 = requests.post(f"{BASE}/api/auth/forgot-password", json={"email": email})
        assert r4.status_code == 429, f"4th call must be 429, got {r4.status_code} {r4.text}"
        # Retry-After header
        assert r4.headers.get("Retry-After"), "Retry-After header missing"
        # Message in French
        body = r4.json()
        detail = body.get("detail", "")
        assert "Trop de tentatives" in detail, f"unexpected detail: {detail}"

    def test_rate_limit_isolation_login_unaffected(self):
        # login and register should NOT be rate-limited even after forgot-pw is exhausted
        # (the previous test left forgot-pw at 4+ calls from this IP)
        r = requests.post(f"{BASE}/api/auth/login",
                           json={"email": ADMIN_EMAIL, "password": ADMIN_PWD})
        assert r.status_code == 200, "login must not be affected by forgot-pw rate-limit"
        # register also unaffected
        r2 = requests.post(f"{BASE}/api/auth/register",
                            json={"email": f"TEST_iso_{uuid.uuid4().hex[:6]}@example.com",
                                  "password": "Pwd12345!", "name": "Iso"})
        assert r2.status_code == 200, "register must not be affected by forgot-pw rate-limit"


# -------- account deletion (last, since it deletes the fresh_user) --------
def test_zz_delete_account(fresh_user):
    # use a fresh dedicated user so we don't break other tests order
    sess = requests.Session()
    email = f"TEST_del_{uuid.uuid4().hex[:8]}@example.com"
    sess.post(f"{BASE}/api/auth/register",
              json={"email": email, "password": "Pwd12345!", "name": "ToDelete"})
    r = sess.post(f"{BASE}/api/auth/login", json={"email": email, "password": "Pwd12345!"})
    sess.headers.update({"Authorization": f"Bearer {r.json()['access_token']}"})
    rd = sess.delete(f"{BASE}/api/auth/account")
    assert rd.status_code == 200
    # /me must now 401
    rm = sess.get(f"{BASE}/api/auth/me")
    assert rm.status_code == 401
