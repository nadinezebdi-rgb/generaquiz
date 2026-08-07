"""Sprint B: Tests for 3-tier pricing (Club/Famille/Premium × monthly/yearly)."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # fallback: read frontend/.env
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL"):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")

API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@generaquiz.fr"
ADMIN_PASSWORD = "Admin2026!"

EXPECTED = {
    "club_monthly": (4.99, "club", "monthly"),
    "club_yearly": (49.99, "club", "yearly"),
    "famille_monthly": (7.99, "famille", "monthly"),
    "famille_yearly": (79.99, "famille", "yearly"),
    "premium_monthly": (12.99, "premium", "monthly"),
    "premium_yearly": (129.99, "premium", "yearly"),
}


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_packages_list():
    r = requests.get(f"{API}/packages")
    assert r.status_code == 200
    pkgs = r.json()
    assert isinstance(pkgs, list)
    assert len(pkgs) == 6, f"expected 6 packages, got {len(pkgs)}"
    by_id = {p["id"]: p for p in pkgs}
    assert set(by_id.keys()) == set(EXPECTED.keys())
    for pid, (amount, tier, period) in EXPECTED.items():
        p = by_id[pid]
        assert p["amount"] == amount, f"{pid} amount {p['amount']} != {amount}"
        assert p["currency"] == "eur"
        assert p["tier"] == tier
        assert p["period"] == period
        assert p.get("label")
        assert p.get("description")


@pytest.mark.parametrize("package_id", list(EXPECTED.keys()))
def test_checkout_session_each_package(auth_headers, package_id):
    r = requests.post(
        f"{API}/checkout/session",
        json={"package_id": package_id, "origin_url": "https://example.com"},
        headers=auth_headers,
    )
    assert r.status_code == 200, f"{package_id}: {r.status_code} {r.text}"
    data = r.json()
    assert "url" in data and data["url"].startswith("http"), data
    assert "session_id" in data


def test_checkout_session_rejects_unknown_package(auth_headers):
    r = requests.post(
        f"{API}/checkout/session",
        json={"package_id": "club_lifetime", "origin_url": "https://example.com"},
        headers=auth_headers,
    )
    assert 400 <= r.status_code < 500, r.status_code


def test_checkout_session_requires_auth():
    r = requests.post(
        f"{API}/checkout/session",
        json={"package_id": "club_monthly", "origin_url": "https://example.com"},
    )
    assert r.status_code == 401
