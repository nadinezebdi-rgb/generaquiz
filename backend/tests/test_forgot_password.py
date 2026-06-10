"""Tests for password reset flow using real Resend integration (iteration 9)."""
import os
import time
import subprocess
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://caricature-saas.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

FORBIDDEN_FIELDS = {"reset_token", "reset_link", "mocked"}


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# --- Forgot Password: response structure / no enumeration / no token leak ---
class TestForgotPasswordSecurity:
    def test_unknown_email_returns_generic_no_leak(self, session):
        r = session.post(f"{API}/auth/forgot-password", json={"email": "test_unknown_xyz_99999@example.com"})
        assert r.status_code == 200
        data = r.json()
        assert data.get("ok") is True
        assert "Si ce compte existe" in data.get("message", "")
        # No token leak
        for f in FORBIDDEN_FIELDS:
            assert f not in data, f"Forbidden field '{f}' leaked in response for unknown email"
        # For unknown emails, email_sent should NOT be present (early return)
        # but if it is, it must not be true
        assert data.get("email_sent") in (None, False)

    def test_admin_email_returns_generic_with_email_sent_false(self, session):
        # admin@quizdantan.fr exists in DB but Resend test mode rejects it
        r = session.post(f"{API}/auth/forgot-password", json={"email": "admin@quizdantan.fr"})
        assert r.status_code == 200
        data = r.json()
        assert "Si ce compte existe" in data.get("message", "")
        for f in FORBIDDEN_FIELDS:
            assert f not in data, f"Forbidden field '{f}' leaked"
        # email_sent should be present and False (Resend test mode rejects non-owner)
        assert "email_sent" in data
        assert data["email_sent"] is False

    def test_invalid_email_format_rejected(self, session):
        r = session.post(f"{API}/auth/forgot-password", json={"email": "not-an-email"})
        assert r.status_code in (400, 422)


# --- End-to-end: register fresh -> forgot -> reset -> login ---
class TestResetPasswordE2E:
    def test_full_reset_flow(self, session):
        ts = int(time.time())
        email = f"TEST_reset_{ts}@example.com"
        pwd_old = "Original123!"
        pwd_new = "BrandNew456!"

        # Register
        reg = session.post(f"{API}/auth/register", json={
            "email": email, "password": pwd_old, "name": "Reset Test"
        })
        assert reg.status_code == 200, f"Register failed: {reg.status_code} {reg.text}"

        # Logout to clear cookies
        session.post(f"{API}/auth/logout")
        session.cookies.clear()

        # Forgot password
        fp = session.post(f"{API}/auth/forgot-password", json={"email": email})
        assert fp.status_code == 200
        data = fp.json()
        for f in FORBIDDEN_FIELDS:
            assert f not in data
        assert "email_sent" in data

        # Pull token from backend logs (recommended path in Resend test mode)
        time.sleep(1)
        email_lc = email.lower()
        log = ""
        for path in ("/var/log/supervisor/backend.out.log", "/var/log/supervisor/backend.err.log"):
            try:
                log += subprocess.check_output(
                    ["tail", "-n", "500", path], stderr=subprocess.STDOUT
                ).decode("utf-8", errors="ignore")
            except Exception:
                pass

        # Extract token from the [RESET] line for our specific email
        token = None
        for line in log.splitlines():
            if "[RESET]" in line and email_lc in line and "reset-password?token=" in line:
                token = line.split("reset-password?token=", 1)[1].strip()
                break
        assert token, f"Could not find reset token in backend logs for {email}"

        # Reset password
        rp = session.post(f"{API}/auth/reset-password", json={
            "token": token, "new_password": pwd_new
        })
        assert rp.status_code == 200, f"Reset failed: {rp.status_code} {rp.text}"

        # Old password should fail
        bad = session.post(f"{API}/auth/login", json={"email": email, "password": pwd_old})
        assert bad.status_code == 401

        # New password should succeed
        good = session.post(f"{API}/auth/login", json={"email": email, "password": pwd_new})
        assert good.status_code == 200, f"Login with new pwd failed: {good.text}"

        # Token cannot be reused
        again = session.post(f"{API}/auth/reset-password", json={
            "token": token, "new_password": "Another789!"
        })
        assert again.status_code == 400

    def test_invalid_token_rejected(self, session):
        r = session.post(f"{API}/auth/reset-password", json={
            "token": "ZZinvalidtokenXX1234", "new_password": "Whatever123!"
        })
        assert r.status_code == 400
