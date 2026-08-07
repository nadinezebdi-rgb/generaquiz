"""Sprint 3 backend tests: Atelier Mémoire, Mascot Affection, EHPAD landing."""
import os
import uuid
import time
import pytest
import requests

def _load_backend_url():
    v = os.environ.get("REACT_APP_BACKEND_URL")
    if v:
        return v.rstrip("/")
    # Load from /app/frontend/.env
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                return line.split("=", 1)[1].strip().rstrip("/")
    raise RuntimeError("REACT_APP_BACKEND_URL not found")

BASE_URL = _load_backend_url()
ADMIN_EMAIL = "admin@generaquiz.fr"
ADMIN_PASSWORD = "Admin2026!"


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, r.text
    return s


@pytest.fixture(scope="module")
def fresh_session():
    """Register a fresh account for first-time badge testing."""
    s = requests.Session()
    email = f"TEST_atelier_{uuid.uuid4().hex[:8]}@test.fr"
    r = s.post(f"{BASE_URL}/api/auth/register", json={
        "email": email, "password": "TestPass2026!", "name": "Test Atelier",
    })
    assert r.status_code in (200, 201), r.text
    return s, email


# ---------- Atelier ----------
class TestAtelier:
    def test_themes_public(self):
        r = requests.get(f"{BASE_URL}/api/atelier/themes")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 5
        ids = {t["id"] for t in data}
        assert ids == {"annees-60", "annees-70", "annees-80", "enfance", "famille"}
        for t in data:
            assert t["prompt_count"] == 5
            assert "label" in t and "emoji" in t and "description" in t

    def test_theme_detail_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/atelier/themes/annees-60")
        assert r.status_code in (401, 403)

    def test_theme_detail_authed(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/atelier/themes/annees-60")
        assert r.status_code == 200
        data = r.json()
        assert len(data["prompts"]) == 5
        ids = [p["id"] for p in data["prompts"]]
        assert ids == [f"annees-60_p{i}" for i in range(1, 6)]

    def test_submit_and_badge_first_time(self, fresh_session):
        s, _ = fresh_session
        payload = {"theme": "annees-60", "answers": [
            {"prompt_id": "annees-60_p1", "answer": "Un souvenir de test"}
        ]}
        r = s.post(f"{BASE_URL}/api/atelier/sessions", json=payload)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["ok"] is True
        assert data["saved"] == 1
        assert data["xp_gained"] == 25
        badge_ids = [b["id"] for b in data["awarded_badges"]]
        assert "premier_atelier" in badge_ids

        # Second submission — badge NOT re-awarded
        r2 = s.post(f"{BASE_URL}/api/atelier/sessions", json=payload)
        assert r2.status_code == 200
        badge_ids2 = [b["id"] for b in r2.json()["awarded_badges"]]
        assert "premier_atelier" not in badge_ids2

    def test_submit_rejects_bad_theme(self, admin_session):
        r = admin_session.post(f"{BASE_URL}/api/atelier/sessions", json={
            "theme": "unknown", "answers": [{"prompt_id": "unknown_p1", "answer": "x"}]
        })
        assert r.status_code == 400

    def test_submit_rejects_bad_prompt(self, admin_session):
        r = admin_session.post(f"{BASE_URL}/api/atelier/sessions", json={
            "theme": "annees-60", "answers": [{"prompt_id": "annees-60_pZ", "answer": "x"}]
        })
        assert r.status_code == 400

    def test_entries_grouped_recent_first(self, fresh_session):
        s, _ = fresh_session
        r = s.get(f"{BASE_URL}/api/atelier/entries")
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 1
        first = data[0]
        assert "session_id" in first and "theme_label" in first
        assert first["entries"][0].get("prompt_text")


# ---------- Progression / Affection ----------
class TestProgression:
    def test_affection_field_present(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/progression/me")
        assert r.status_code == 200
        data = r.json()
        assert "mastery" in data
        assert len(data["mastery"]) > 0
        for m in data["mastery"]:
            assert "affection" in m
            aff = m["affection"]
            assert set(aff.keys()) >= {"level", "label", "next_level_at"}
            assert aff["level"] in (0, 1, 2, 3)

    def test_affection_thresholds_logic(self, admin_session):
        # Just validate schema — actual value depends on user data.
        r = admin_session.get(f"{BASE_URL}/api/progression/me")
        for m in r.json()["mastery"]:
            total = m["total"]
            level = m["affection"]["level"]
            if total >= 500:
                assert level == 3
            elif total >= 100:
                assert level == 2
            elif total >= 20:
                assert level == 1
            else:
                assert level == 0


# ---------- Mascot Skins ----------
class TestMascotSkins:
    @pytest.mark.parametrize("slug", ["chansons", "cinema", "cuisine-terroir"])
    @pytest.mark.parametrize("skin", [1, 2, 3])
    def test_skin_files_served(self, slug, skin):
        url = f"{BASE_URL}/api/static/mascots/{slug}_skin{skin}.png"
        r = requests.head(url, allow_redirects=True)
        # Try GET if HEAD not allowed
        if r.status_code >= 400:
            r = requests.get(url)
        assert r.status_code == 200, f"{url} → {r.status_code}"


# ---------- EHPAD landing (public backend? actually it's a frontend route, no API needed) ----------
# Skipped — /ehpad is a frontend-only page.


# ---------- No regression ----------
class TestRegression:
    def test_progression_still_has_level(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/progression/me")
        assert r.status_code == 200
        d = r.json()
        assert "level" in d and "xp_total" in d

    def test_daily_endpoint_still_works(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/daily/today")
        assert r.status_code in (200, 401, 403)  # just not 500

    def test_pricing_still_works(self):
        r = requests.get(f"{BASE_URL}/api/packages")
        assert r.status_code == 200
