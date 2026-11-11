# Iteration 51: retest of iteration_50 fixes — lifetime redeem, cancelled PDF 404, checkout origin, owner accept 409, new code format, challenge gate
import os
import uuid

import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
ADMIN = {"email": "admin@generaquiz.fr", "password": "pF44gVBfLdushm3NZ6dN"}


def _env(key):
    for line in open("/app/backend/.env"):
        if line.startswith(key + "="):
            return line.split("=", 1)[1].strip().strip('"')


DB = MongoClient(_env("MONGO_URL"))[_env("DB_NAME")]


def _s(tok):
    s = requests.Session()
    s.headers["Authorization"] = f"Bearer {tok}"
    return s


@pytest.fixture(scope="module")
def admin():
    r = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN)
    if r.status_code != 200:
        pytest.skip("admin login failed")
    return _s(r.json()["access_token"])


def _register(tag):
    email = f"test_it51_{tag}_{uuid.uuid4().hex[:6]}@example.com"
    r = requests.post(f"{BASE_URL}/api/auth/register", json={"email": email, "password": "Test1234!", "name": f"TEST {tag}"})
    assert r.status_code == 200, r.text
    s = _s(r.json()["access_token"])
    s.email = email
    return s


@pytest.fixture(scope="module")
def codes(admin):
    out = []
    yield out
    for c in out:
        admin.patch(f"{BASE_URL}/api/admin/gifts/{c}/cancel")


def _mk(admin, codes, offer="famille"):
    r = admin.post(f"{BASE_URL}/api/admin/gifts", json={"offer": offer, "recipient_name": "TEST_Mamie", "buyer_name": "TEST_Paul"})
    assert r.status_code == 200, r.text
    codes.append(r.json()["code"])
    return r.json()


# --- new codes never start with GQ in first block
def test_new_code_format(admin, codes):
    for _ in range(8):
        c = _mk(admin, codes, "solo")["code"]
        assert c.startswith("GQ-") and len(c) == 12
        assert not c[3:5] == "GQ", c


# --- cancelled code PDF -> 404
def test_cancelled_pdf_404(admin, codes):
    g = _mk(admin, codes, "solo")
    k = g["pdf_url"].split("k=")[1]
    assert requests.get(f"{BASE_URL}/api/gifts/{g['code']}/carte.pdf", params={"k": k}).status_code == 200
    assert admin.patch(f"{BASE_URL}/api/admin/gifts/{g['code']}/cancel").status_code == 200
    assert requests.get(f"{BASE_URL}/api/gifts/{g['code']}/carte.pdf", params={"k": k}).status_code == 404


# --- checkout ignores origin_url, optional
def test_checkout_origin_ignored():
    body = {"offer": "solo", "recipient_name": "TEST_Mamie", "buyer_name": "TEST_Paul", "buyer_email": "test_it51@example.com"}
    r = requests.post(f"{BASE_URL}/api/gifts/checkout", json=body)
    assert r.status_code == 200, r.text
    r2 = requests.post(f"{BASE_URL}/api/gifts/checkout", json={**body, "origin_url": "https://evil.example.com"})
    assert r2.status_code == 200
    sid = r2.json()["session_id"]
    import stripe  # noqa
    key = _env("STRIPE_API_KEY")
    if not key or key == "sk_test_emergent":
        # emergent proxy: can't fetch session; check DB tx exists at least
        assert DB.payment_transactions.find_one({"session_id": sid}) is not None
        return
    stripe.api_key = key
    sess = stripe.checkout.Session.retrieve(sid)
    assert "evil.example.com" not in sess.success_url and sess.success_url.startswith(_env("FRONTEND_URL"))


# --- lifetime premium user keeps lifetime after redeem
def test_lifetime_redeem_keeps_lifetime(admin, codes):
    u = _register("life")
    me = u.get(f"{BASE_URL}/api/auth/me").json()
    me = me.get("user", me)
    DB.users.update_one({"email": u.email.lower()}, {"$set": {"plan": "premium", "plan_tier": "solo", "plan_expires_at": None}})
    g = _mk(admin, codes, "famille")
    r = u.post(f"{BASE_URL}/api/gifts/redeem", json={"code": g["code"]})
    assert r.status_code == 200, r.text
    assert r.json()["plan_expires_at"] is None
    assert r.json()["plan_tier"] == "famille_v2"
    me = u.get(f"{BASE_URL}/api/auth/me").json()
    me = me.get("user", me)
    assert me["plan"] == "premium" and me.get("plan_expires_at") is None


# --- famille owner cannot accept another family's invite; proche creates challenge, outsider 402
def test_owner_accept_409_and_challenge_gate(admin, codes):
    o1, o2, proche, outsider = _register("o1"), _register("o2"), _register("pr"), _register("out")
    for o in (o1, o2):
        assert o.post(f"{BASE_URL}/api/gifts/redeem", json={"code": _mk(admin, codes, "famille")["code"]}).status_code == 200
    inv = o1.post(f"{BASE_URL}/api/famille/proches", json={"name": "TEST_x", "email": o2.email}).json()
    tok = inv["link"].rsplit("/", 1)[1]
    r = o2.post(f"{BASE_URL}/api/famille/invitation/{tok}/accept")
    assert r.status_code == 409, r.text
    assert o2.get(f"{BASE_URL}/api/famille").json()["role"] == "owner"
    assert proche.post(f"{BASE_URL}/api/famille/invitation/{tok}/accept").status_code == 200
    cat = requests.get(f"{BASE_URL}/api/categories").json()[0]["id"]
    assert proche.post(f"{BASE_URL}/api/challenges", json={"category_id": cat}).status_code == 200
    assert outsider.post(f"{BASE_URL}/api/challenges", json={"category_id": cat}).status_code == 402


def test_promo_disabled():
    d = requests.get(f"{BASE_URL}/api/gifts/offers").json()
    assert d["promo"]["active"] is False
    assert {o["id"]: o["price"] for o in d["offers"]} == {"famille": 79, "solo": 49}
