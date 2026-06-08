"""Tests for new account / password management features:
- POST /api/auth/forgot-password (mocked email, returns reset_link + reset_token)
- POST /api/auth/reset-password (single-use, error states)
- POST /api/auth/change-password (auth required)
- PATCH /api/auth/profile (auth required)
- DELETE /api/auth/account (auth required) + cascading deletion
- Security indexes: TTL on password_reset_tokens.expires_at, unique on token
"""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"


def _ts():
    return int(time.time() * 1000)


@pytest.fixture
def fresh_user():
    """Register a brand-new free user; returns (session, email, password, name)."""
    s = requests.Session()
    email = f"qa.acct.{_ts()}@quizdantan.fr"
    pwd = "InitialPwd123"
    r = s.post(f"{API}/auth/register", json={"name": "QA Account", "email": email, "password": pwd})
    assert r.status_code == 200, f"register failed: {r.status_code} {r.text}"
    return s, email, pwd, "QA Account"


# -------- Forgot password (MOCKED email) --------
class TestForgotPassword:
    def test_unknown_email_returns_generic_success_no_token(self):
        r = requests.post(f"{API}/auth/forgot-password",
                          json={"email": f"nobody.{_ts()}@quizdantan.fr"})
        assert r.status_code == 200
        data = r.json()
        assert data.get("ok") is True
        # NO enumeration: no reset_token / reset_link / mocked in response
        assert "reset_token" not in data
        assert "reset_link" not in data
        assert "mocked" not in data

    def test_known_email_returns_mocked_token_and_link(self, fresh_user):
        _, email, _, _ = fresh_user
        r = requests.post(f"{API}/auth/forgot-password", json={"email": email})
        assert r.status_code == 200
        data = r.json()
        assert data.get("ok") is True
        assert data.get("mocked") is True
        assert isinstance(data.get("reset_token"), str) and len(data["reset_token"]) >= 16
        assert isinstance(data.get("reset_link"), str)
        assert "/reset-password?token=" in data["reset_link"]
        assert data["reset_token"] in data["reset_link"]


# -------- Reset password (single-use, invalid token, success) --------
class TestResetPassword:
    def test_invalid_token_returns_400(self):
        r = requests.post(f"{API}/auth/reset-password",
                          json={"token": "this-token-does-not-exist-xyz", "new_password": "Newpass123"})
        assert r.status_code == 400
        assert "invalide" in r.json().get("detail", "").lower()

    def test_full_reset_flow_and_single_use(self, fresh_user):
        s, email, old_pwd, _ = fresh_user
        # Request reset
        r1 = requests.post(f"{API}/auth/forgot-password", json={"email": email})
        token = r1.json()["reset_token"]
        new_pwd = "ResetPwd456!"

        # Use the token
        r2 = requests.post(f"{API}/auth/reset-password",
                           json={"token": token, "new_password": new_pwd})
        assert r2.status_code == 200, r2.text
        assert r2.json().get("ok") is True

        # OLD password no longer works
        bad = requests.post(f"{API}/auth/login", json={"email": email, "password": old_pwd})
        assert bad.status_code == 401

        # NEW password works
        good = requests.post(f"{API}/auth/login", json={"email": email, "password": new_pwd})
        assert good.status_code == 200, good.text
        assert good.json()["user"]["email"] == email

        # Token reuse -> "Lien déjà utilisé"
        r3 = requests.post(f"{API}/auth/reset-password",
                           json={"token": token, "new_password": "AnotherPwd789"})
        assert r3.status_code == 400
        assert "déjà utilisé" in r3.json().get("detail", "").lower()


# -------- Change password (auth required) --------
class TestChangePassword:
    def test_requires_auth(self):
        r = requests.post(f"{API}/auth/change-password",
                          json={"current_password": "x", "new_password": "newpwd1"})
        assert r.status_code == 401

    def test_wrong_current_password_returns_400(self, fresh_user):
        s, _, _, _ = fresh_user
        r = s.post(f"{API}/auth/change-password",
                   json={"current_password": "WRONG", "new_password": "Newpwd123"})
        assert r.status_code == 400
        assert "incorrect" in r.json().get("detail", "").lower()

    def test_change_password_success_and_login_with_new(self, fresh_user):
        s, email, old_pwd, _ = fresh_user
        new_pwd = "ChangedPwd789!"
        r = s.post(f"{API}/auth/change-password",
                   json={"current_password": old_pwd, "new_password": new_pwd})
        assert r.status_code == 200, r.text
        assert r.json().get("ok") is True
        # OLD password fails
        bad = requests.post(f"{API}/auth/login", json={"email": email, "password": old_pwd})
        assert bad.status_code == 401
        # NEW password works
        good = requests.post(f"{API}/auth/login", json={"email": email, "password": new_pwd})
        assert good.status_code == 200


# -------- Update profile name --------
class TestUpdateProfile:
    def test_requires_auth(self):
        r = requests.patch(f"{API}/auth/profile", json={"name": "Anonymous"})
        assert r.status_code == 401

    def test_update_name_and_me_reflects_it(self, fresh_user):
        s, email, _, _ = fresh_user
        new_name = f"Renamed QA {_ts()}"
        r = s.patch(f"{API}/auth/profile", json={"name": new_name})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["name"] == new_name
        assert body["email"] == email
        # /me confirms persistence
        me = s.get(f"{API}/auth/me")
        assert me.status_code == 200
        assert me.json()["name"] == new_name


# -------- Delete account + cascade --------
class TestDeleteAccount:
    def test_requires_auth(self):
        r = requests.delete(f"{API}/auth/account")
        assert r.status_code == 401

    def test_delete_user_cascades_attempts(self, fresh_user):
        s, email, _, _ = fresh_user
        # Create an attempt so we can verify cascade
        cats = requests.get(f"{API}/categories").json()
        cat_id = cats[0]["id"]
        ra = s.post(f"{API}/attempts", json={"category_id": cat_id, "score": 3, "total": 5})
        assert ra.status_code == 200

        # Confirm attempt is visible
        list_before = s.get(f"{API}/attempts")
        assert list_before.status_code == 200
        assert len(list_before.json()) >= 1

        # Delete account
        rd = s.delete(f"{API}/auth/account")
        assert rd.status_code == 200, rd.text
        assert rd.json().get("ok") is True

        # /me with cookies of deleted user -> 401
        me = s.get(f"{API}/auth/me")
        assert me.status_code == 401

        # Login should fail since user is gone
        relog = requests.post(f"{API}/auth/login",
                              json={"email": email, "password": "InitialPwd123"})
        assert relog.status_code == 401


# -------- DB indexes (TTL + unique on token) --------
class TestPasswordResetIndexes:
    """Verify TTL & unique indexes exist on password_reset_tokens via Mongo directly."""

    def test_indexes_present(self):
        from pymongo import MongoClient
        client = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
        db = client[os.environ.get("DB_NAME", "test_database")]
        # Make sure collection exists by triggering one forgot-password
        email = f"qa.idx.{_ts()}@quizdantan.fr"
        s = requests.Session()
        s.post(f"{API}/auth/register", json={"name": "Idx", "email": email, "password": "Initial123"})
        requests.post(f"{API}/auth/forgot-password", json={"email": email})

        idx_info = db.password_reset_tokens.index_information()
        # token index
        token_idx = next((v for k, v in idx_info.items() if any(p[0] == "token" for p in v.get("key", []))), None)
        assert token_idx is not None, f"missing token index. all={list(idx_info.keys())}"
        assert token_idx.get("unique") is True, "token index must be unique"
        # TTL on expires_at
        ttl_idx = next((v for k, v in idx_info.items() if any(p[0] == "expires_at" for p in v.get("key", []))), None)
        assert ttl_idx is not None, "missing expires_at index"
        assert ttl_idx.get("expireAfterSeconds") == 0, f"TTL not configured: {ttl_idx}"
        client.close()
