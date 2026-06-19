"""Iteration 15 — Gamification: credits, leagues, challenge, streak-saver, social auth 503s."""
import os
import time
import requests
import pytest
from pymongo import MongoClient
from bson import ObjectId

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://caricature-saas.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

# Direct DB access for state-setup (forcing credits=0 etc.)
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")
_mongo = MongoClient(MONGO_URL)
_db = _mongo[DB_NAME]

ADMIN_EMAIL = "admin@generaquiz.fr"
ADMIN_PASSWORD = "Admin2026!"


def _register_unique():
    ts = int(time.time() * 1000)
    email = f"test_iter15_{ts}@example.com"
    s = requests.Session()
    r = s.post(f"{API}/auth/register", json={"email": email, "password": "Pass2026!", "name": "Test User"})
    assert r.status_code == 200, f"register failed: {r.status_code} {r.text}"
    return s, email, r.json()


def _login_admin():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    return s, r.json()


# --- Register & welcome bonus ---
class TestRegisterWelcomeBonus:
    def test_register_gives_5_credits(self):
        s, email, body = _register_unique()
        assert body["user"]["credits"] == 5
        me = s.get(f"{API}/auth/me").json()
        assert me["credits"] == 5
        # Ledger has welcome_bonus
        bal = s.get(f"{API}/gamification/credits/balance").json()
        reasons = [e["reason"] for e in bal["recent"]]
        assert "welcome_bonus" in reasons


# --- Admin backfill ---
class TestAdminBackfill:
    def test_admin_credits_ge_5(self):
        s, body = _login_admin()
        assert body["user"]["credits"] >= 5


# --- Credits balance ---
class TestCreditsBalance:
    def test_balance_shape(self):
        s, _, _ = _register_unique()
        r = s.get(f"{API}/gamification/credits/balance")
        assert r.status_code == 200
        data = r.json()
        assert "credits" in data and isinstance(data["credits"], int)
        assert "recent" in data and isinstance(data["recent"], list)


# --- Spend ---
class TestCreditsSpend:
    def test_spend_hint_5050_ok(self):
        s, _, _ = _register_unique()
        r = s.post(f"{API}/gamification/credits/spend", json={"amount": 2, "reason": "hint_5050"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["credits"] == 3
        bal = s.get(f"{API}/gamification/credits/balance").json()
        assert bal["recent"][0]["reason"] == "hint_5050"
        assert bal["recent"][0]["delta"] == -2

    def test_spend_bad_amount(self):
        s, _, _ = _register_unique()
        r = s.post(f"{API}/gamification/credits/spend", json={"amount": 5, "reason": "hint_5050"})
        assert r.status_code == 400
        assert "50/50" in r.json()["detail"] or "coûte" in r.json()["detail"]

    def test_spend_invalid_reason(self):
        s, _, _ = _register_unique()
        r = s.post(f"{API}/gamification/credits/spend", json={"amount": 2, "reason": "foo"})
        assert r.status_code == 400
        assert "Raison invalide" in r.json()["detail"]

    def test_spend_insufficient(self):
        s, email, _ = _register_unique()
        # Force credits=0
        _db.users.update_one({"email": email}, {"$set": {"credits": 0}})
        r = s.post(f"{API}/gamification/credits/spend", json={"amount": 2, "reason": "hint_5050"})
        assert r.status_code == 400
        assert "insuffisants" in r.json()["detail"].lower()


# --- Earn ad with daily cap ---
class TestEarnAd:
    def test_earn_ad_5_then_429(self):
        s, email, _ = _register_unique()
        # Clear any earlier ad rewards for cleanliness
        user_id = str(_db.users.find_one({"email": email})["_id"])
        _db.credit_ledger.delete_many({"user_id": user_id, "reason": "ad_reward"})

        for i in range(5):
            r = s.post(f"{API}/gamification/credits/earn-ad", json={})
            assert r.status_code == 200, f"call {i} failed: {r.text}"
            assert r.json()["earned"] == 1
        # 6th
        r = s.post(f"{API}/gamification/credits/earn-ad", json={})
        assert r.status_code == 429
        assert "Limite quotidienne" in r.json()["detail"]


# --- Streak saver ---
class TestStreakSaver:
    def test_no_streak_returns_400(self):
        s, _, _ = _register_unique()
        r = s.post(f"{API}/gamification/streak-saver")
        assert r.status_code == 400
        assert "Aucune série" in r.json()["detail"]


# --- Challenge submit ---
class TestChallengeSubmit:
    def test_challenge_xp_and_credit(self):
        s, _, _ = _register_unique()
        r = s.post(f"{API}/gamification/challenge/submit", json={
            "category_id": "cinema", "score": 4, "total": 5, "duration_seconds": 42
        })
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["xp_gained"] == 54  # 50 + 4
        assert d["credits_gained"] == 1


# --- Leagues ---
class TestLeaguesCurrent:
    def test_league_default_bronze(self):
        s, _, _ = _register_unique()
        # Submit a challenge first to ensure membership has been created via lazy enrollment as well,
        # but the endpoint itself does lazy enrollment too.
        r = s.get(f"{API}/gamification/leagues/current")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["tier"] == "bronze"
        assert d["cohort_id"]
        assert "-W" in d["week_key"]
        assert d["seconds_until_close"] > 0
        assert "leaderboard" in d
        assert d["my_rank"] is not None
        assert "my_xp" in d
        assert "week_ends_at" in d


# --- Social auth: missing env -> 503 ---
class TestSocialAuth:
    def test_apple_not_configured(self):
        r = requests.post(f"{API}/auth/apple", json={"id_token": "x" * 40})
        # Apple/Google env vars MUST be absent in this preview env
        assert r.status_code == 503, f"expected 503, got {r.status_code}: {r.text}"
        assert "Apple" in r.json()["detail"]

    def test_google_not_configured(self):
        r = requests.post(f"{API}/auth/google", json={"id_token": "x" * 40})
        assert r.status_code == 503, f"expected 503, got {r.status_code}: {r.text}"
        assert "Google" in r.json()["detail"]

    def test_apple_id_token_too_short(self):
        r = requests.post(f"{API}/auth/apple", json={"id_token": "short"})
        assert r.status_code == 422


# --- Static legal pages ---
class TestLegalPages:
    @pytest.mark.parametrize("path", ["/cgu", "/cgv", "/confidentialite"])
    def test_legal_page_200(self, path):
        r = requests.get(f"{BASE_URL}{path}")
        assert r.status_code == 200
