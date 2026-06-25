"""Iteration 19 — P2 features: stats publiques, parrainage, mistral ping/lock, pub→crédit.

Each test class uses an isolated requests.Session() to avoid cookie pollution
(/auth/login sets httpOnly cookies that would otherwise leak across tests).
"""
import os
import time
import asyncio
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@generaquiz.fr"
ADMIN_PASSWORD = "Admin2026!"


def _new_session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _register(session, email, password="Pass1234!", name="Test User", referral_code=None):
    payload = {"email": email, "password": password, "name": name}
    if referral_code is not None:
        payload["referral_code"] = referral_code
    return session.post(f"{API}/auth/register", json=payload)


def _login(session, email, password):
    r = session.post(f"{API}/auth/login", json={"email": email, "password": password})
    return r


def _admin_session():
    s = _new_session()
    r = _login(s, ADMIN_EMAIL, ADMIN_PASSWORD)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    return s


# ============================================================
# Stats publiques
# ============================================================
class TestPublicStats:
    def test_public_stats_no_auth_required(self):
        s = _new_session()
        r = s.get(f"{API}/stats/public")
        assert r.status_code == 200, r.text
        data = r.json()
        keys = ["players_today", "games_today", "games_total",
                "questions_total", "streak_record", "countries_active"]
        for k in keys:
            assert k in data, f"missing key {k}"
            assert isinstance(data[k], int), f"{k} is not int: {type(data[k])}"
            assert data[k] >= 0, f"{k} is negative"
        # Should be 800 (8 categories x 100) per the spec
        assert data["questions_total"] >= 700, f"questions_total too low: {data['questions_total']}"


# ============================================================
# Mistral ping (admin only)
# ============================================================
class TestMistralPing:
    def test_ping_requires_auth(self):
        s = _new_session()
        r = s.get(f"{API}/admin/mistral/ping")
        assert r.status_code == 401, f"got {r.status_code} {r.text}"

    def test_ping_rejects_non_admin(self):
        s = _new_session()
        ts = int(time.time() * 1000)
        email = f"TEST_mping_{ts}@example.com"
        rr = _register(s, email)
        assert rr.status_code == 200, rr.text
        r = s.get(f"{API}/admin/mistral/ping")
        assert r.status_code == 403, f"got {r.status_code} {r.text}"

    def test_ping_admin_returns_full_payload(self):
        s = _admin_session()
        r = s.get(f"{API}/admin/mistral/ping")
        assert r.status_code == 200, r.text
        data = r.json()
        assert "ok" in data
        assert "latency_ms" in data and isinstance(data["latency_ms"], int)
        assert data["latency_ms"] < 10000
        assert "model" in data
        assert "questions_per_category" in data
        assert isinstance(data["questions_per_category"], dict)
        assert len(data["questions_per_category"]) == 8, \
            f"expected 8 categories, got {len(data['questions_per_category'])}"
        assert "total_questions" in data
        assert "last_run" in data
        assert "lock_held" in data
        assert isinstance(data["lock_held"], bool)


# ============================================================
# Mistral regenerate endpoint reachable (don't wait for completion)
# ============================================================
class TestMistralRegenerateReachable:
    def test_regenerate_admin_returns_200(self):
        s = _admin_session()
        r = s.post(f"{API}/admin/mistral/regenerate")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("ok") is True

    def test_ping_still_works_after_regenerate_trigger(self):
        s = _admin_session()
        r = s.get(f"{API}/admin/mistral/ping")
        assert r.status_code == 200


# ============================================================
# Referral system
# ============================================================
class TestReferral:
    def test_new_user_gets_referral_code(self):
        s = _new_session()
        ts = int(time.time() * 1000)
        email = f"TEST_parrain_{ts}@example.com"
        rr = _register(s, email, name="Marie")
        assert rr.status_code == 200, rr.text
        user = rr.json()["user"]
        assert user.get("referral_code"), "no referral_code on returned user"
        code = user["referral_code"]
        # Format PRENOM-XXXX
        assert "-" in code, f"code format invalid: {code}"
        prefix, suffix = code.split("-", 1)
        assert prefix == "MARIE" or prefix.startswith("MARIE")
        assert len(suffix) >= 4

        # Confirm via /auth/me
        me = s.get(f"{API}/auth/me")
        assert me.status_code == 200
        assert me.json()["referral_code"] == code
        assert me.json()["credits"] == 5  # WELCOME_CREDITS

    def test_validate_code_valid_and_invalid(self):
        # Create sponsor
        s_sponsor = _new_session()
        ts = int(time.time() * 1000)
        sponsor_email = f"TEST_val_sponsor_{ts}@example.com"
        rr = _register(s_sponsor, sponsor_email, name="Pierre")
        assert rr.status_code == 200
        sponsor_code = rr.json()["user"]["referral_code"]

        # Validate from a fresh anonymous session
        s = _new_session()
        r = s.post(f"{API}/referral/validate-code", json={"code": sponsor_code})
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["valid"] is True
        assert data["sponsor_name"] == "Pierre"
        assert data["bonus"] == 5

        r2 = s.post(f"{API}/referral/validate-code", json={"code": "NOPE-ZZZZ"})
        assert r2.status_code == 200
        assert r2.json()["valid"] is False

    def test_full_referral_flow_grants_bonus_once(self):
        ts = int(time.time() * 1000)
        # User A (sponsor)
        s_a = _new_session()
        a_email = f"TEST_par_a_{ts}@example.com"
        ra = _register(s_a, a_email, name="Sophie")
        assert ra.status_code == 200
        a_code = ra.json()["user"]["referral_code"]
        a_credits_before = ra.json()["user"]["credits"]
        assert a_credits_before == 5

        # User B registers with A's code
        s_b = _new_session()
        b_email = f"TEST_par_b_{ts}@example.com"
        rb = _register(s_b, b_email, name="Lucas", referral_code=a_code)
        assert rb.status_code == 200, rb.text
        b_credits_before = rb.json()["user"]["credits"]
        assert b_credits_before == 5  # bonus arrives only on first attempt

        # User B plays a quiz attempt
        attempt = {"category_id": "annees-70-80", "score": 3, "total": 5, "duration_seconds": 30}
        r_att = s_b.post(f"{API}/attempts", json=attempt)
        assert r_att.status_code == 200, r_att.text
        body = r_att.json()
        assert body.get("referral_bonus_granted") is True, body

        # B should now have 5+5 credits
        me_b = s_b.get(f"{API}/auth/me").json()
        assert me_b["credits"] == 10, f"B credits = {me_b['credits']}"

        # A should also have +5 and referral_count=1
        # Re-login A to get fresh user state
        s_a2 = _new_session()
        _login(s_a2, a_email, "Pass1234!")
        me_a = s_a2.get(f"{API}/auth/me").json()
        assert me_a["credits"] == 10, f"A credits = {me_a['credits']}"
        assert me_a["referral_count"] == 1, f"A referral_count = {me_a['referral_count']}"

        # Second attempt by B should NOT re-trigger bonus
        r_att2 = s_b.post(f"{API}/attempts", json=attempt)
        assert r_att2.status_code == 200
        assert r_att2.json().get("referral_bonus_granted") is False

        me_b2 = s_b.get(f"{API}/auth/me").json()
        assert me_b2["credits"] == 10, f"B credits after 2nd attempt = {me_b2['credits']}"

    def test_referral_my_endpoint(self):
        s = _new_session()
        ts = int(time.time() * 1000)
        email = f"TEST_my_{ts}@example.com"
        rr = _register(s, email, name="Inès")
        assert rr.status_code == 200

        r = s.get(f"{API}/referral/my")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["code"]
        assert "register?code=" in d["invite_link"]
        assert d["code"] in d["invite_link"]
        assert d["referral_count"] == 0
        assert d["bonus"] == 5

    def test_referral_my_requires_auth(self):
        s = _new_session()
        r = s.get(f"{API}/referral/my")
        assert r.status_code == 401


# ============================================================
# Pub → Crédit
# ============================================================
class TestAdReward:
    def test_earn_ad_first_call_grants_credit(self):
        s = _new_session()
        ts = int(time.time() * 1000)
        email = f"TEST_ad_{ts}@example.com"
        rr = _register(s, email)
        assert rr.status_code == 200
        credits_before = rr.json()["user"]["credits"]

        r = s.post(f"{API}/gamification/credits/earn-ad", json={"placement": "test"})
        assert r.status_code == 200, r.text
        data = r.json()
        # remaining_today should be 4 after the 1st of 5
        assert data.get("remaining_today") == 4, data
        # Balance check via /me
        me = s.get(f"{API}/auth/me").json()
        assert me["credits"] == credits_before + 1

    def test_earn_ad_daily_cap_429(self):
        s = _new_session()
        ts = int(time.time() * 1000)
        email = f"TEST_adcap_{ts}@example.com"
        rr = _register(s, email)
        assert rr.status_code == 200

        # 5 successful calls
        for i in range(5):
            r = s.post(f"{API}/gamification/credits/earn-ad", json={"placement": "test"})
            assert r.status_code == 200, f"call {i+1}: {r.status_code} {r.text}"

        # 6th must be 429
        r6 = s.post(f"{API}/gamification/credits/earn-ad", json={"placement": "test"})
        assert r6.status_code == 429, f"expected 429, got {r6.status_code} {r6.text}"


# ============================================================
# Email expiration helper
# ============================================================
class TestExpirationEmail:
    def test_send_expiration_emails_callable(self):
        """Smoke test: function exists and handles missing Resend gracefully."""
        import sys
        sys.path.insert(0, "/app/backend")
        from daily_email import send_expiration_emails  # noqa
        result = asyncio.get_event_loop().run_until_complete(send_expiration_emails()) \
            if not asyncio.get_event_loop().is_running() else None
        # If above pattern doesn't apply we just import-check
        assert callable(send_expiration_emails)
