"""Iteration 7: premium quiz limit 20->30 + o20/o28 content rewrite."""
import os
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/") or "http://localhost:8001"
if not BASE_URL.endswith("/api"):
    BASE_URL_API = BASE_URL + "/api"
else:
    BASE_URL_API = BASE_URL

ADMIN_EMAIL = "admin@quizdantan.fr"
ADMIN_PW = "Admin2026!"


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{BASE_URL_API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PW}, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


CATEGORIES = ["annees-50-60", "chansons", "cinema", "objets-antan", "histoire-france",
              "cuisine-terroir", "culture-40-ans", "culture-70-ans"]


@pytest.mark.parametrize("cat", CATEGORIES)
def test_premium_returns_30_questions(cat, admin_headers):
    r = requests.get(f"{BASE_URL_API}/categories/{cat}/questions", headers=admin_headers, timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["is_premium"] is True
    assert len(data["questions"]) == 30, f"{cat}: expected 30 got {len(data['questions'])}"


def test_free_user_still_5_questions():
    import time
    email = f"qa.iter7.{int(time.time()*1000)}@test.fr"
    r = requests.post(f"{BASE_URL_API}/auth/register",
                      json={"email": email, "password": "Passw0rd!", "name": "Free"}, timeout=15)
    assert r.status_code == 200
    tok = r.json()["access_token"]
    r2 = requests.get(f"{BASE_URL_API}/categories/cinema/questions",
                      headers={"Authorization": f"Bearer {tok}"}, timeout=15)
    assert r2.status_code == 200
    d = r2.json()
    assert d["is_premium"] is False
    assert len(d["questions"]) == 5


def test_o20_and_o28_content(admin_headers):
    """Verify rewritten o20 (pétrin) and o28 (casse-sucre) content & correct_index."""
    # Sample multiple times to ensure we hit them (30 from 30 pool ⇒ guaranteed)
    r = requests.get(f"{BASE_URL_API}/categories/objets-antan/questions", headers=admin_headers, timeout=15)
    assert r.status_code == 200
    qs = r.json()["questions"]
    assert len(qs) == 30
    by_id = {q["id"]: q for q in qs}
    assert "o20" in by_id and "o28" in by_id
    o20 = by_id["o20"]
    assert "pétrir la pâte à pain" in o20["question"]
    assert o20["options"][o20["correct_index"]] == "Le pétrin"
    assert o20["correct_index"] == 0

    o28 = by_id["o28"]
    assert "couper le sucre" in o28["question"]
    assert o28["options"][o28["correct_index"]] == "Un casse-sucre"
    assert o28["correct_index"] == 1


def test_sample_randomness(admin_headers):
    """Mongo $sample should yield different orderings across calls."""
    orderings = []
    for _ in range(3):
        r = requests.get(f"{BASE_URL_API}/categories/cinema/questions", headers=admin_headers, timeout=15)
        orderings.append([q["id"] for q in r.json()["questions"]])
    # At least 2 of 3 should differ (sample of 30 from 30 = same set but order varies)
    assert orderings[0] != orderings[1] or orderings[1] != orderings[2]
