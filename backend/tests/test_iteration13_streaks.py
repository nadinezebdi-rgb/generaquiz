"""Iteration 13 — Streaks (consecutive days) + morning email (Resend) tests.

Covers:
- GET /api/auth/me exposes streak_current/streak_best/streak_last_date/daily_email_optin
- POST /api/daily/submit: streak=1 on first play, +1 if yesterday, RESET to 1 if older
- PATCH /api/auth/preferences/daily-email (auth required, 401 otherwise)
- POST /api/admin/daily-email/trigger (admin-only, 403 for user; returns sent/skipped/failed/date)
- Regression: 8 categories with 100 questions each
"""
import os
import time
from datetime import datetime, timezone, timedelta

import pytest
import requests
from bson import ObjectId
from pymongo import MongoClient


BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
ADMIN_EMAIL = "admin@generaquiz.fr"
ADMIN_PASSWORD = "Admin2026!"


def _today_key() -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=1)).strftime("%Y-%m-%d")


def _yesterday_key() -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=1) - timedelta(days=1)).strftime("%Y-%m-%d")


# ---------------- fixtures ----------------
@pytest.fixture(scope="module")
def mongo():
    client = MongoClient(MONGO_URL)
    yield client[DB_NAME]
    client.close()


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    return s


def _make_user(suffix: str):
    ts = int(time.time() * 1000)
    # Server lowercases emails on register/login -- keep test email all lowercase
    email = f"test_streak_{suffix}_{ts}@example.com"
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/register", json={
        "email": email, "password": "Test1234!", "name": f"Test {suffix}",
    })
    assert r.status_code == 200, f"register failed: {r.status_code} {r.text}"
    return s, email


@pytest.fixture
def fresh_user():
    s, email = _make_user("a")
    yield s, email
    # cleanup
    try:
        s.delete(f"{BASE_URL}/api/auth/account")
    except Exception:
        pass


# ---------------- /auth/me schema ----------------
class TestAuthMeFields:
    def test_me_has_streak_and_optin_fields(self, fresh_user):
        s, _ = fresh_user
        r = s.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 200
        body = r.json()
        for field in ["streak_current", "streak_best", "streak_last_date", "daily_email_optin"]:
            assert field in body, f"missing field {field} in /auth/me"
        assert body["streak_current"] == 0
        assert body["streak_best"] == 0
        assert body["streak_last_date"] in (None, "")
        assert body["daily_email_optin"] is True


# ---------------- POST /daily/submit ----------------
class TestDailySubmitStreak:
    def test_first_submit_sets_streak_to_1(self, fresh_user):
        s, _ = fresh_user
        r = s.post(f"{BASE_URL}/api/daily/submit", json={"score": 3, "duration_seconds": 30})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["ok"] is True
        assert body["streak_current"] == 1
        assert body["streak_best"] == 1
        # /me reflects new state
        me = s.get(f"{BASE_URL}/api/auth/me").json()
        assert me["streak_current"] == 1
        assert me["streak_best"] == 1
        assert me["streak_last_date"] == _today_key()

    def test_streak_continues_when_last_played_yesterday(self, mongo):
        s, email = _make_user("yest")
        try:
            # Seed prior streak in DB (simulate played yesterday with current=4)
            mongo.users.update_one(
                {"email": email},
                {"$set": {
                    "streak_current": 4,
                    "streak_best": 4,
                    "streak_last_date": _yesterday_key(),
                }},
            )
            r = s.post(f"{BASE_URL}/api/daily/submit", json={"score": 5, "duration_seconds": 12})
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["streak_current"] == 5, f"expected 5, got {body}"
            assert body["streak_best"] == 5
        finally:
            s.delete(f"{BASE_URL}/api/auth/account")

    def test_streak_resets_when_gap_2_days(self, mongo):
        s, email = _make_user("gap")
        try:
            old_date = (datetime.now(timezone.utc) + timedelta(hours=1) - timedelta(days=5)).strftime("%Y-%m-%d")
            mongo.users.update_one(
                {"email": email},
                {"$set": {
                    "streak_current": 10,
                    "streak_best": 10,
                    "streak_last_date": old_date,
                }},
            )
            r = s.post(f"{BASE_URL}/api/daily/submit", json={"score": 2, "duration_seconds": 60})
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["streak_current"] == 1, f"expected reset to 1, got {body}"
            assert body["streak_best"] == 10, f"best should remain 10, got {body}"
        finally:
            s.delete(f"{BASE_URL}/api/auth/account")

    def test_duplicate_submit_returns_409(self, fresh_user):
        s, _ = fresh_user
        r1 = s.post(f"{BASE_URL}/api/daily/submit", json={"score": 3, "duration_seconds": 25})
        assert r1.status_code == 200
        r2 = s.post(f"{BASE_URL}/api/daily/submit", json={"score": 3, "duration_seconds": 25})
        assert r2.status_code == 409


# ---------------- PATCH /auth/preferences/daily-email ----------------
class TestDailyEmailPreference:
    def test_unauthenticated_returns_401(self):
        r = requests.patch(
            f"{BASE_URL}/api/auth/preferences/daily-email",
            json={"daily_email_optin": False},
        )
        assert r.status_code == 401

    def test_toggle_off_then_on(self, fresh_user):
        s, _ = fresh_user
        # Off
        r = s.patch(f"{BASE_URL}/api/auth/preferences/daily-email",
                    json={"daily_email_optin": False})
        assert r.status_code == 200, r.text
        assert r.json()["daily_email_optin"] is False
        # Verify via /me
        me = s.get(f"{BASE_URL}/api/auth/me").json()
        assert me["daily_email_optin"] is False
        # Back on
        r = s.patch(f"{BASE_URL}/api/auth/preferences/daily-email",
                    json={"daily_email_optin": True})
        assert r.status_code == 200
        assert r.json()["daily_email_optin"] is True


# ---------------- /admin/daily-email/trigger ----------------
class TestAdminDailyEmailTrigger:
    def test_user_gets_403(self, fresh_user):
        s, _ = fresh_user
        r = s.post(f"{BASE_URL}/api/admin/daily-email/trigger")
        assert r.status_code == 403

    def test_admin_returns_summary(self, admin_session, mongo):
        # Ensure admin has played today => skipped >= 1
        admin = mongo.users.find_one({"email": ADMIN_EMAIL})
        today = _today_key()
        mongo.daily_attempts.delete_many({"user_id": str(admin["_id"]), "date_key": today})
        mongo.daily_attempts.insert_one({
            "user_id": str(admin["_id"]),
            "user_name": admin.get("name", "Admin"),
            "date_key": today,
            "score": 5,
            "total": 5,
            "duration_seconds": 10,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        # Make sure admin is opt-in
        mongo.users.update_one({"_id": admin["_id"]},
                               {"$set": {"daily_email_optin": True}})

        r = admin_session.post(f"{BASE_URL}/api/admin/daily-email/trigger")
        assert r.status_code == 200, r.text
        body = r.json()
        for key in ["sent", "skipped", "failed", "date"]:
            assert key in body, f"missing {key} in trigger response"
        assert body["date"] == today
        assert body["skipped"] >= 1, f"expected skipped>=1 since admin played today, got {body}"


# ---------------- Regression: categories ----------------
class TestRegressionCategories:
    def test_eight_categories_returned(self):
        r = requests.get(f"{BASE_URL}/api/categories")
        assert r.status_code == 200
        cats = r.json()
        assert isinstance(cats, list)
        assert len(cats) == 8, f"expected 8 categories, got {len(cats)}"

    def test_each_category_has_100_questions(self, mongo):
        cats = mongo.categories.find({}, {"_id": 0, "id": 1, "name": 1})
        deficits = []
        for c in cats:
            cnt = mongo.questions.count_documents({"category_id": c["id"]})
            if cnt < 100:
                deficits.append((c.get("name", c["id"]), cnt))
        assert not deficits, f"categories under 100 questions: {deficits}"
