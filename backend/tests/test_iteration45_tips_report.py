# Iteration 45: daily tip (public), morning report endpoint auth, QA summary, SEO assets
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
ADMIN = {"email": "admin@generaquiz.fr", "password": "pF44gVBfLdushm3NZ6dN"}


def _login(payload):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json=payload)
    if r.status_code != 200:
        return None
    tok = r.json().get("access_token") or r.json().get("token")
    if tok:
        s.headers["Authorization"] = f"Bearer {tok}"
    return s


@pytest.fixture(scope="module")
def admin():
    s = _login(ADMIN)
    if not s:
        pytest.skip("admin login failed")
    return s


@pytest.fixture(scope="module")
def free_user():
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    pwd = "TestPass123!"
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/register", json={"email": email, "password": pwd, "name": "TEST_Free"})
    if r.status_code not in (200, 201):
        pytest.skip(f"register failed {r.status_code} {r.text[:200]}")
    tok = r.json().get("access_token") or r.json().get("token")
    if tok:
        s.headers["Authorization"] = f"Bearer {tok}"
    yield s
    d = s.delete(f"{BASE_URL}/api/auth/account", json={"password": pwd, "confirm": "SUPPRIMER"})
    print("cleanup delete account", d.status_code, d.text[:200])


# --- Public tips ---
class TestTips:
    def test_today_public(self):
        r = requests.get(f"{BASE_URL}/api/tips/today")
        assert r.status_code == 200
        d = r.json()
        assert d["is_today"] is True
        tip = d["tip"]
        for k in ("date_key", "theme", "title", "text", "action"):
            assert isinstance(tip[k], str) and tip[k].strip()
        assert "_id" not in tip and "review" not in tip and "writer_model" not in tip

    def test_recent_limit(self):
        r = requests.get(f"{BASE_URL}/api/tips/recent?limit=3")
        assert r.status_code == 200
        lst = r.json()
        assert isinstance(lst, list) and 1 <= len(lst) <= 3
        assert all("_id" not in t for t in lst)
        keys = [t["date_key"] for t in lst]
        assert keys == sorted(keys, reverse=True)

    def test_recent_limit_validation(self):
        assert requests.get(f"{BASE_URL}/api/tips/recent?limit=0").status_code == 422
        assert requests.get(f"{BASE_URL}/api/tips/recent?limit=31").status_code == 422


# --- Morning report auth ---
class TestMorningReportAuth:
    def test_anonymous_rejected(self):
        r = requests.post(f"{BASE_URL}/api/admin/qa/morning-report/send")
        assert r.status_code in (401, 403)

    def test_free_user_rejected(self, free_user):
        r = free_user.post(f"{BASE_URL}/api/admin/qa/morning-report/send")
        assert r.status_code == 403

    def test_free_user_sees_tip(self, free_user):
        r = free_user.get(f"{BASE_URL}/api/tips/today")
        assert r.status_code == 200 and r.json()["tip"]["title"]


# --- QA summary for fill banner ---
class TestQASummary:
    def test_summary_has_bien_vieillir(self, admin):
        r = admin.get(f"{BASE_URL}/api/admin/qa/summary")
        assert r.status_code == 200
        d = r.json()
        rows = d if isinstance(d, list) else d.get("categories") or d.get("summary")
        bv = next(c for c in rows if c["category_id"] == "bien-vieillir")
        print("bien-vieillir summary", bv)
        assert "missing_for_full_parcours" in bv
        assert bv["category_title"]


# --- SEO ---
class TestSEO:
    def test_sitemap(self):
        r = requests.get(f"{BASE_URL}/sitemap.xml")
        assert r.status_code == 200
        assert "https://generaquiz.fr/bien-vieillir" in r.text

    def test_regression_categories(self):
        r = requests.get(f"{BASE_URL}/api/categories")
        assert r.status_code == 200
        assert any(c["id"] == "bien-vieillir" for c in r.json())
