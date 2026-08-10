"""Backend tests for PATCH /api/auth/profile email update feature (iteration 39)."""
import os
import time
import requests
import pytest

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
ADMIN_EMAIL = "admin@generaquiz.fr"
ADMIN_PASSWORD = "Admin2026!"
NEW_EMAIL = "admin-new@generaquiz.fr"
OCCUPIED_EMAIL = f"occupied_{int(time.time())}@example.com"


def _login(email, password):
    s = requests.Session()
    r = s.post(f"{BASE}/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"login failed {r.status_code} {r.text}"
    return s, r.json()


@pytest.fixture(scope="module")
def admin_session():
    s, _ = _login(ADMIN_EMAIL, ADMIN_PASSWORD)
    yield s
    # Teardown: ensure admin email restored
    try:
        # Try relog with new email in case previous test left it changed
        s2 = requests.Session()
        r = s2.post(f"{BASE}/auth/login", json={"email": NEW_EMAIL, "password": ADMIN_PASSWORD})
        if r.status_code == 200:
            s2.patch(f"{BASE}/auth/profile", json={"name": "Admin", "email": ADMIN_EMAIL})
    except Exception:
        pass


def test_login_and_me(admin_session):
    r = admin_session.get(f"{BASE}/auth/me")
    assert r.status_code == 200
    assert r.json()["email"] == ADMIN_EMAIL


def test_update_name_only_no_email_leak(admin_session):
    me = admin_session.get(f"{BASE}/auth/me").json()
    orig_name = me["name"]
    orig_xp = me.get("xp_total", 0)
    r = admin_session.patch(f"{BASE}/auth/profile", json={"name": orig_name})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["email"] == ADMIN_EMAIL
    assert data["name"] == orig_name
    assert data.get("xp_total", 0) == orig_xp


def test_invalid_email_returns_422(admin_session):
    r = admin_session.patch(f"{BASE}/auth/profile", json={"name": "Admin", "email": "foobar"})
    assert r.status_code == 422, f"expected 422 got {r.status_code}: {r.text}"


def test_uniqueness_409(admin_session):
    # Register a second user
    reg = requests.post(f"{BASE}/auth/register", json={
        "email": OCCUPIED_EMAIL, "password": "Passw0rd!", "name": "Occupied"
    })
    assert reg.status_code == 200, reg.text
    # Try to update admin email to occupied
    r = admin_session.patch(f"{BASE}/auth/profile", json={"name": "Admin", "email": OCCUPIED_EMAIL})
    assert r.status_code == 409, f"expected 409 got {r.status_code}: {r.text}"
    detail = r.json().get("detail", "")
    assert "déjà utilisée" in detail or "deja utilisee" in detail.lower(), detail


def test_case_insensitive_same_account_allowed(admin_session):
    r = admin_session.patch(f"{BASE}/auth/profile", json={"name": "Admin", "email": ADMIN_EMAIL.upper()})
    assert r.status_code == 200, r.text
    # Verify stored lowercase
    me = admin_session.get(f"{BASE}/auth/me").json()
    assert me["email"] == ADMIN_EMAIL


def test_full_email_update_and_revert():
    # Fresh session for admin
    s, _ = _login(ADMIN_EMAIL, ADMIN_PASSWORD)
    # Update to new email
    r = s.patch(f"{BASE}/auth/profile", json={"name": "Admin", "email": NEW_EMAIL})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["email"] == NEW_EMAIL

    # Verify via /me on same session
    me = s.get(f"{BASE}/auth/me").json()
    assert me["email"] == NEW_EMAIL

    # Verify login with new email works
    s2, payload = _login(NEW_EMAIL, ADMIN_PASSWORD)
    assert payload["user"]["email"] == NEW_EMAIL

    # Verify old email login fails
    r_old = requests.post(f"{BASE}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r_old.status_code == 401

    # Revert
    r_rev = s2.patch(f"{BASE}/auth/profile", json={"name": "Admin", "email": ADMIN_EMAIL})
    assert r_rev.status_code == 200
    assert r_rev.json()["email"] == ADMIN_EMAIL

    # Verify login with original email works again
    s3, payload3 = _login(ADMIN_EMAIL, ADMIN_PASSWORD)
    assert payload3["user"]["email"] == ADMIN_EMAIL
