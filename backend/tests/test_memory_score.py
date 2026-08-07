"""Sprint C — Score Mémoire 5 axes tests."""
import os
import time
import uuid
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # Fallback: read frontend .env
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")

API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@generaquiz.fr"
ADMIN_PW = "Admin2026!"

EXPECTED_KEYS = ["culture", "regularite", "attention", "rapidite", "memoire"]


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PW})
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def fresh_user_session():
    s = requests.Session()
    email = f"TEST_memscore_{uuid.uuid4().hex[:10]}@example.com"
    r = s.post(
        f"{API}/auth/register",
        json={"email": email, "password": "TestPass2026!", "name": "MemScore Tester"},
    )
    assert r.status_code in (200, 201), f"Register failed: {r.status_code} {r.text}"
    return s, email


def _validate_payload_shape(payload):
    assert "axes" in payload and isinstance(payload["axes"], list)
    assert "overall" in payload and isinstance(payload["overall"], int)
    assert "computed_at" in payload and isinstance(payload["computed_at"], str)
    assert 0 <= payload["overall"] <= 100
    axes = payload["axes"]
    assert len(axes) == 5, f"Expected 5 axes, got {len(axes)}"
    keys = [a["key"] for a in axes]
    assert keys == EXPECTED_KEYS, f"Axes order mismatch: {keys}"
    for a in axes:
        assert set(["key", "label", "hint", "value", "detail"]).issubset(a.keys())
        assert isinstance(a["value"], int)
        assert 0 <= a["value"] <= 100, f"axis {a['key']} value out of range: {a['value']}"
        assert isinstance(a["detail"], dict)


def test_unauthenticated_returns_401_or_403():
    r = requests.get(f"{API}/progression/memory-score")
    assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}"


def test_admin_memory_score_shape(admin_session):
    r = admin_session.get(f"{API}/progression/memory-score")
    assert r.status_code == 200, r.text
    _validate_payload_shape(r.json())


def test_fresh_user_cold_start(fresh_user_session):
    s, _ = fresh_user_session
    r = s.get(f"{API}/progression/memory-score")
    assert r.status_code == 200, r.text
    payload = r.json()
    _validate_payload_shape(payload)
    # New user - all axes should be 0
    for a in payload["axes"]:
        assert a["value"] == 0, f"Fresh user axis {a['key']} value={a['value']} (expected 0)"
    assert payload["overall"] == 0


def test_fresh_user_after_one_attempt(fresh_user_session):
    s, _ = fresh_user_session

    # Get a category and a question set
    cats = s.get(f"{API}/categories")
    assert cats.status_code == 200, cats.text
    cat_list = cats.json()
    assert len(cat_list) > 0
    cat_id = cat_list[0]["id"]

    q_resp = s.get(f"{API}/categories/{cat_id}/questions")
    assert q_resp.status_code == 200, q_resp.text
    questions = q_resp.json()
    # Handle both shapes: list vs { questions: [...] }
    if isinstance(questions, dict) and "questions" in questions:
        questions = questions["questions"]
    assert len(questions) > 0, "No questions returned"

    # Build attempt payload with answers (server-authoritative)
    answers = [{"question_id": q["id"], "answer_index": 0} for q in questions[:5]]
    payload = {
        "category_id": cat_id,
        "duration_seconds": 45,
        "answers": answers,
    }
    r = s.post(f"{API}/attempts", json=payload)
    assert r.status_code in (200, 201), f"Attempt submit failed: {r.status_code} {r.text}"

    # Now fetch score
    r = s.get(f"{API}/progression/memory-score")
    assert r.status_code == 200
    payload = r.json()
    _validate_payload_shape(payload)

    culture = next(a for a in payload["axes"] if a["key"] == "culture")
    assert culture["detail"].get("attempts", 0) >= 1, f"culture.detail={culture['detail']}"
    assert culture["value"] >= 0
    # cold_start flag should be True since attempts < 3
    assert culture["detail"].get("cold_start") is True, f"Expected cold_start flag true when attempts<3, detail={culture['detail']}"


def test_progression_me_still_works(admin_session):
    """Regression: /progression/me must still return level/mastery."""
    r = admin_session.get(f"{API}/progression/me")
    assert r.status_code == 200, r.text
    data = r.json()
    assert "level" in data
    assert "mastery" in data
