# Iteration 49: LOT 1 homepage — admin testimonials CRUD, public stats thresholds, catalogue count
import os
import uuid

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
ADMIN = {"email": "admin@generaquiz.fr", "password": "pF44gVBfLdushm3NZ6dN"}
DEFAULTS = {"players_today": 20, "games_today": 50, "countries_active": 3, "streak_record": 7}
PUBLIC_KEYS = {"id", "text", "first_name", "age_role", "location", "profile"}


@pytest.fixture(scope="module")
def admin():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json=ADMIN)
    if r.status_code != 200:
        pytest.skip(f"admin login failed {r.status_code}")
    tok = r.json().get("access_token")
    if tok:
        s.headers["Authorization"] = f"Bearer {tok}"
    return s


@pytest.fixture(scope="module")
def user():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/register", json={
        "email": f"TEST_it49_{uuid.uuid4().hex[:8]}@example.com", "password": "Test1234!", "name": "TEST It49"})
    assert r.status_code == 200, r.text
    s.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    return s


@pytest.fixture(scope="module")
def created(admin):
    ids = []
    yield ids
    for tid in ids:
        admin.delete(f"{BASE_URL}/api/admin/testimonials/{tid}")


def _body(**kw):
    b = {"text": "TEST_ super jeu pour ma mère", "first_name": "TEST_Jo", "age_role": "72 ans",
         "location": "Lyon", "profile": "SENIOR", "published": False}
    b.update(kw)
    return b


# --- Auth guards
class TestGuards:
    def test_anon_admin_testimonials(self):
        assert requests.get(f"{BASE_URL}/api/admin/testimonials").status_code in (401, 403)
        assert requests.post(f"{BASE_URL}/api/admin/testimonials", json=_body()).status_code in (401, 403)

    def test_user_forbidden(self, user):
        assert user.get(f"{BASE_URL}/api/admin/testimonials").status_code in (401, 403)
        assert user.get(f"{BASE_URL}/api/admin/site-settings/stats").status_code in (401, 403)
        assert user.put(f"{BASE_URL}/api/admin/site-settings/stats", json=DEFAULTS).status_code in (401, 403)

    def test_anon_settings(self):
        assert requests.get(f"{BASE_URL}/api/admin/site-settings/stats").status_code in (401, 403)


# --- Validation
class TestValidation:
    def test_bad_profile(self, admin):
        assert admin.post(f"{BASE_URL}/api/admin/testimonials", json=_body(profile="OTHER")).status_code == 422

    def test_short_text(self, admin):
        assert admin.post(f"{BASE_URL}/api/admin/testimonials", json=_body(text="abc")).status_code == 422

    def test_negative_threshold(self, admin):
        r = admin.put(f"{BASE_URL}/api/admin/site-settings/stats", json={**DEFAULTS, "games_today": -1})
        assert r.status_code == 422


# --- CRUD + public projection
class TestCrud:
    def test_flow(self, admin, created):
        r = admin.post(f"{BASE_URL}/api/admin/testimonials", json=_body())
        assert r.status_code == 200, r.text
        t = r.json()
        created.append(t["id"])
        assert t["published"] is False and "_id" not in t
        # draft not public
        pub = requests.get(f"{BASE_URL}/api/testimonials").json()
        assert t["id"] not in [p["id"] for p in pub]
        # publish
        r = admin.put(f"{BASE_URL}/api/admin/testimonials/{t['id']}", json=_body(published=True, profile="EHPAD"))
        assert r.status_code == 200 and r.json()["published"] is True and r.json()["profile"] == "EHPAD"
        pub = requests.get(f"{BASE_URL}/api/testimonials").json()
        mine = [p for p in pub if p["id"] == t["id"]]
        assert len(mine) == 1
        assert set(mine[0].keys()) == PUBLIC_KEYS
        assert mine[0]["profile"] == "EHPAD"
        # admin list includes it
        lst = admin.get(f"{BASE_URL}/api/admin/testimonials").json()
        assert any(x["id"] == t["id"] and x["published"] for x in lst)
        # delete
        assert admin.delete(f"{BASE_URL}/api/admin/testimonials/{t['id']}").status_code == 200
        created.remove(t["id"])
        assert t["id"] not in [p["id"] for p in requests.get(f"{BASE_URL}/api/testimonials").json()]
        assert admin.delete(f"{BASE_URL}/api/admin/testimonials/{t['id']}").status_code == 404

    def test_update_404(self, admin):
        assert admin.put(f"{BASE_URL}/api/admin/testimonials/nope", json=_body()).status_code == 404


# --- Stats thresholds
class TestStats:
    def test_public_shape(self):
        d = requests.get(f"{BASE_URL}/api/stats/public").json()
        assert d["livre_chapters"] == 12
        assert isinstance(d["questions_total"], int) and d["questions_total"] > 0
        assert isinstance(d["visible"], list)

    def test_thresholds_zero_then_restore(self, admin):
        try:
            r = admin.put(f"{BASE_URL}/api/admin/site-settings/stats", json={k: 0 for k in DEFAULTS})
            assert r.status_code == 200
            assert admin.get(f"{BASE_URL}/api/admin/site-settings/stats").json() == {k: 0 for k in DEFAULTS}
            d = requests.get(f"{BASE_URL}/api/stats/public").json()
            keys = ["players_today", "games_today", "questions_total", "streak_record", "countries_active"]
            expected = [k for k in keys if d[k] > 0]
            assert sorted(d["visible"]) == sorted(expected)
        finally:
            r = admin.put(f"{BASE_URL}/api/admin/site-settings/stats", json=DEFAULTS)
            assert r.status_code == 200
        assert admin.get(f"{BASE_URL}/api/admin/site-settings/stats").json() == DEFAULTS
        d = requests.get(f"{BASE_URL}/api/stats/public").json()
        for k, th in DEFAULTS.items():
            assert (k in d["visible"]) == (d[k] >= th)
