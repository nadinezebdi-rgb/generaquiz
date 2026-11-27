# Iteration 59 — email verification at sign-up, profile email change re-verification,
# reset-password verifies email, social pre-registration takeover protection, Énigme du soir.
import os
import sys
import uuid
import asyncio
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import pytest
import requests
from bson import ObjectId
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"
ADMIN_EMAIL = os.environ["TEST_ADMIN_EMAIL"]
ADMIN_PASSWORD = os.environ["TEST_ADMIN_PASSWORD"]
TEST_PW = "Tst_" + uuid.uuid4().hex[:10]
_mongo = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
CREATED_IDS = []


def clear_rl():
    _mongo.rate_limits.delete_many({"key": {"$regex": "^(register|login|verify-mail)"}})


def register(prefix):
    clear_rl()
    s = requests.Session()
    email = f"test_{prefix}_{uuid.uuid4().hex[:8]}@example.com"
    r = s.post(f"{API}/auth/register", json={"email": email, "password": TEST_PW, "name": f"TEST_{prefix}"})
    assert r.status_code == 200, r.text
    uid = r.json()["user"]["id"]
    CREATED_IDS.append(uid)
    return s, email, uid, r.json()


def plant_verify_token(uid, email, expired=False):
    tok = secrets.token_urlsafe(32)
    _mongo.email_verify_tokens.insert_one({
        "token_hash": hashlib.sha256(tok.encode()).hexdigest(), "user_id": uid, "email": email,
        "expires_at": datetime.now(timezone.utc) + (timedelta(hours=-1) if expired else timedelta(hours=48)),
        "used": False})
    return tok


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    for uid in CREATED_IDS:
        _mongo.users.delete_one({"_id": ObjectId(uid)})
        _mongo.email_verify_tokens.delete_many({"user_id": uid})
        _mongo.password_reset_tokens.delete_many({"user_id": uid})
        _mongo.credit_ledger.delete_many({"user_id": uid})
        _mongo.rate_limits.delete_many({"key": f"verify-mail:{uid}"})


# --- Registration creates unverified user + hashed token
def test_register_unverified_and_hashed_token():
    s, email, uid, data = register("reg")
    assert data["user"]["email_verified"] is False
    assert s.get(f"{API}/auth/me").json()["email_verified"] is False
    rec = _mongo.email_verify_tokens.find_one({"user_id": uid})
    assert rec and len(rec["token_hash"]) == 64 and "token" not in rec
    assert rec["email"] == email and rec["used"] is False
    u = _mongo.users.find_one({"_id": ObjectId(uid)})
    assert u["password_hash"].startswith("$2b$")


# --- Verify email: valid / reuse / invalid / expired / old address
def test_verify_email_flow():
    s, email, uid, _ = register("ver")
    tok = plant_verify_token(uid, email)
    r = requests.post(f"{API}/auth/verify-email", json={"token": tok})
    assert r.status_code == 200 and r.json()["ok"] is True
    assert s.get(f"{API}/auth/me").json()["email_verified"] is True
    r2 = requests.post(f"{API}/auth/verify-email", json={"token": tok})
    assert r2.status_code == 400
    r3 = requests.post(f"{API}/auth/verify-email", json={"token": "x" * 40})
    assert r3.status_code == 400
    exp = plant_verify_token(uid, email, expired=True)
    assert requests.post(f"{API}/auth/verify-email", json={"token": exp}).status_code == 400
    assert requests.post(f"{API}/auth/verify-email", json={"token": "short"}).status_code == 422


# --- Resend: already verified short-circuit, 3/h limit
def test_resend_limit():
    s, email, uid, _ = register("rsd")
    codes = [s.post(f"{API}/auth/resend-verification").status_code for _ in range(4)]
    assert all(c in (200, 502) for c in codes[:3]), codes  # 502 = envoi refusé par Resend (adresse de test)
    assert codes[3] == 429, codes
    assert requests.post(f"{API}/auth/resend-verification").status_code == 401


def test_resend_already_verified():
    clear_rl()
    s = requests.Session()
    assert s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}).status_code == 200
    r = s.post(f"{API}/auth/resend-verification")
    assert r.status_code == 200 and r.json().get("already_verified") is True


# --- Profile email change requires current password, resets verification
def test_profile_email_change():
    s, email, uid, _ = register("pro")
    old_tok = plant_verify_token(uid, email)
    new_email = f"test_pro2_{uuid.uuid4().hex[:8]}@example.com"
    r = s.patch(f"{API}/auth/profile", json={"name": "TEST_pro", "email": new_email})
    assert r.status_code == 403, r.text
    r = s.patch(f"{API}/auth/profile", json={"name": "TEST_pro", "email": new_email, "current_password": "wrongpass1"})
    assert r.status_code == 403
    # name-only update still works without password
    assert s.patch(f"{API}/auth/profile", json={"name": "TEST_pro_n"}).status_code == 200
    # mark verified, then change email -> must become unverified
    _mongo.users.update_one({"_id": ObjectId(uid)}, {"$set": {"email_verified": True}})
    r = s.patch(f"{API}/auth/profile", json={"name": "TEST_pro", "email": new_email, "current_password": TEST_PW})
    assert r.status_code == 200, r.text
    assert r.json()["email"] == new_email and r.json()["email_verified"] is False
    assert _mongo.email_verify_tokens.find_one({"user_id": uid, "email": new_email})
    # token issued for old address no longer verifies
    r = requests.post(f"{API}/auth/verify-email", json={"token": old_tok})
    assert r.status_code == 400
    assert s.get(f"{API}/auth/me").json()["email_verified"] is False


def test_profile_email_change_social_only_400():
    s, email, uid, _ = register("soc")
    _mongo.users.update_one({"_id": ObjectId(uid)}, {"$set": {"password_hash": None}})
    r = s.patch(f"{API}/auth/profile", json={"name": "TEST_soc", "email": f"x_{uuid.uuid4().hex[:6]}@example.com",
                                              "current_password": "whatever12"})
    assert r.status_code == 400, r.text


# --- Reset password sets email_verified true
def test_reset_password_verifies_email():
    s, email, uid, _ = register("rst")
    tok = secrets.token_urlsafe(32)
    _mongo.password_reset_tokens.insert_one({"token": tok, "user_id": uid, "email": email, "used": False,
                                             "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
                                             "created_at": datetime.now(timezone.utc)})
    r = requests.post(f"{API}/auth/reset-password", json={"token": tok, "new_password": TEST_PW + "x"})
    assert r.status_code == 200, r.text
    u = _mongo.users.find_one({"_id": ObjectId(uid)})
    assert u["email_verified"] is True and u.get("token_version", 0) == 1
    assert s.get(f"{API}/auth/me").status_code == 401  # old session revoked


# --- Social takeover protection via direct call
def test_social_upsert_unverified_and_verified():
    s1, e1, uid1, _ = register("sun")
    s2, e2, uid2, _ = register("sve")
    _mongo.users.update_one({"_id": ObjectId(uid2)}, {"$set": {"email_verified": True}})
    pw2 = _mongo.users.find_one({"_id": ObjectId(uid2)})["password_hash"]
    sys.path.insert(0, "/app/backend")
    from dotenv import load_dotenv
    load_dotenv("/app/backend/.env")

    async def run():
        from routers.social_auth import _upsert_social_user
        a = await _upsert_social_user(provider="google", sub="TEST_sub_" + uid1, email=e1.upper(),
                                      name_from_token=None, name_from_request=None)
        b = await _upsert_social_user(provider="apple", sub="TEST_sub_" + uid2, email=e2,
                                      name_from_token=None, name_from_request=None)
        return a, b

    a, b = asyncio.run(run())
    assert str(a["_id"]) == uid1 and str(b["_id"]) == uid2
    u1 = _mongo.users.find_one({"_id": ObjectId(uid1)})
    assert u1["password_hash"] is None and u1["token_version"] == 1 and u1["email_verified"] is True
    assert u1["google_sub"] == "TEST_sub_" + uid1
    assert s1.get(f"{API}/auth/me").status_code == 401  # attacker session revoked
    r = requests.post(f"{API}/auth/login", json={"email": e1, "password": TEST_PW})
    assert r.status_code == 401  # attacker password no longer works
    u2 = _mongo.users.find_one({"_id": ObjectId(uid2)})
    assert u2["password_hash"] == pw2 and u2["apple_sub"] == "TEST_sub_" + uid2
    assert u2.get("token_version", 0) == 0
    assert s2.get(f"{API}/auth/me").status_code == 200


# --- Énigme du soir
def test_enigme_today():
    assert requests.get(f"{API}/enigme/today").status_code == 401
    s, *_ = register("eni")
    r = s.get(f"{API}/enigme/today", timeout=90)
    assert r.status_code == 200, r.text
    d = r.json()
    for k in ("date", "titre", "enigme", "indice", "reponse", "explication", "question_famille"):
        assert isinstance(d.get(k), str) and d[k].strip(), k
    assert "_id" not in d
    d2 = s.get(f"{API}/enigme/today", timeout=90).json()
    assert d2 == d
    assert _mongo.evening_riddles.count_documents({"date": d["date"]}) == 1


# --- Regression: admin login + categories
def test_regression_login_categories():
    clear_rl()
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200 and r.json()["user"]["email_verified"] is True
    assert "access_token" in s.cookies.get_dict()
    cats = s.get(f"{API}/categories").json()
    assert isinstance(cats, list) and len(cats) > 0
    cid = next(c["id"] for c in cats if c.get("count", 0) >= 5)
    q = s.get(f"{API}/categories/{cid}/questions")
    assert q.status_code == 200, q.text
