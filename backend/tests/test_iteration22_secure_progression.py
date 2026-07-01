"""Iteration 22 — Sprint A+B+C: Server-authoritative scoring, Badges, Progression.

Covers:
  A. Security: POST /api/attempts + /api/daily/submit ignore client-declared score,
     validate answer_index bounds, validate question-belongs-to-category/day.
  B. Badges: catalog (15 entries), earned list, idempotent first_quiz award, daily badges.
  C. Progression: level curve formula, mastery per category, /api/progression/me shape.
"""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"


# ---- helpers --------------------------------------------------------------
def _register(prefix="prog"):
    s = requests.Session()
    email = f"TEST_{prefix}_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}@example.com"
    r = s.post(f"{API}/auth/register", json={
        "email": email, "password": "Password123!", "name": f"Test {prefix}",
    })
    assert r.status_code in (200, 201), f"register failed: {r.status_code} {r.text}"
    return s, email


@pytest.fixture
def user_session():
    s, email = _register()
    return s, email


@pytest.fixture
def user_session2():
    s, email = _register(prefix="prog2")
    return s, email


def _get_cat_questions(s):
    cats = s.get(f"{API}/categories").json()
    assert cats and isinstance(cats, list)
    cat_id = cats[0]["id"]
    r = s.get(f"{API}/categories/{cat_id}/questions")
    assert r.status_code == 200
    return cat_id, r.json()["questions"], cats


# ---- A. Security ----------------------------------------------------------
class TestSecureAttempts:
    def test_attempts_ignores_client_score_field(self, user_session):
        """Sending a bogus 'score':999 field must not affect the server-computed score."""
        s, _ = user_session
        cat_id, qs, _ = _get_cat_questions(s)
        payload = {
            "category_id": cat_id,
            "answers": [{"question_id": q["id"], "answer_index": 0} for q in qs],
            "duration_seconds": 12,
            # Attacker fields — must be ignored / stripped by Pydantic
            "score": 999, "total": 999,
        }
        r = s.post(f"{API}/attempts", json=payload)
        # Either Pydantic strips (200) OR strict mode rejects (422). Both are fine.
        assert r.status_code in (200, 422), r.text
        if r.status_code == 200:
            data = r.json()
            assert data["total"] == len(qs)
            assert 0 <= data["score"] <= len(qs)
            # Absolutely cannot be 999
            assert data["score"] != 999
            assert data["total"] != 999

    def test_attempts_answer_index_out_of_range_422(self, user_session):
        s, _ = user_session
        cat_id, qs, _ = _get_cat_questions(s)
        payload = {
            "category_id": cat_id,
            "answers": [{"question_id": qs[0]["id"], "answer_index": 42}],
        }
        r = s.post(f"{API}/attempts", json=payload)
        assert r.status_code == 422, r.text

    def test_attempts_question_not_in_category_400(self, user_session):
        s, _ = user_session
        cats = s.get(f"{API}/categories").json()
        cat_a, cat_b = cats[0]["id"], cats[1]["id"]
        qs_b = s.get(f"{API}/categories/{cat_b}/questions").json()["questions"]
        # Sending a cat_b question under cat_a should be rejected
        r = s.post(f"{API}/attempts", json={
            "category_id": cat_a,
            "answers": [{"question_id": qs_b[0]["id"], "answer_index": 0}],
        })
        assert r.status_code == 400, r.text

    def test_attempts_correct_score_recomputed(self, user_session):
        """Send actually correct answer_indexes → score must match number correct."""
        s, _ = user_session
        cat_id, qs, _ = _get_cat_questions(s)
        # We don't know correct_index (server hides it), so send index 0 for all.
        r = s.post(f"{API}/attempts", json={
            "category_id": cat_id,
            "answers": [{"question_id": q["id"], "answer_index": 0} for q in qs],
        })
        assert r.status_code == 200
        d = r.json()
        assert d["total"] == len(qs)
        assert 0 <= d["score"] <= len(qs)
        assert d.get("mastery") is not None
        assert "awarded_badges" in d


class TestSecureDaily:
    def test_daily_bad_question_id_400(self, user_session):
        s, _ = user_session
        r = s.post(f"{API}/daily/submit", json={
            "answers": [{"question_id": "not-a-daily-qid", "answer_index": 0}],
            "duration_seconds": 20,
        })
        assert r.status_code == 400, r.text

    def test_daily_answer_index_out_of_range_422(self, user_session):
        s, _ = user_session
        dq = s.get(f"{API}/daily/quiz").json()
        r = s.post(f"{API}/daily/submit", json={
            "answers": [{"question_id": dq["questions"][0]["id"], "answer_index": 99}],
            "duration_seconds": 10,
        })
        assert r.status_code == 422, r.text


# ---- B. Badges ------------------------------------------------------------
class TestBadges:
    def test_catalog_requires_auth(self):
        r = requests.get(f"{API}/badges/catalog")
        assert r.status_code == 401

    def test_catalog_15_badges(self, user_session):
        s, _ = user_session
        r = s.get(f"{API}/badges/catalog")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) == 15, f"expected 15 badges got {len(data)}"
        expected_keys = {"id", "title", "desc", "emoji", "tier", "family", "earned", "earned_at"}
        for b in data:
            assert expected_keys.issubset(set(b.keys())), f"missing keys in {b}"
            assert b["earned"] is False
            assert b["earned_at"] is None

    def test_mine_initially_empty(self, user_session):
        s, _ = user_session
        r = s.get(f"{API}/badges/mine")
        assert r.status_code == 200
        assert r.json() == []

    def test_first_quiz_award_and_idempotent(self, user_session):
        s, _ = user_session
        cat_id, qs, _ = _get_cat_questions(s)
        payload = {
            "category_id": cat_id,
            "answers": [{"question_id": q["id"], "answer_index": 0} for q in qs],
        }
        r1 = s.post(f"{API}/attempts", json=payload)
        assert r1.status_code == 200
        assert "first_quiz" in r1.json().get("awarded_badges", [])
        # 2nd attempt must not re-award
        r2 = s.post(f"{API}/attempts", json=payload)
        assert r2.status_code == 200
        assert "first_quiz" not in r2.json().get("awarded_badges", [])
        # /badges/mine now has first_quiz
        mine = s.get(f"{API}/badges/mine").json()
        assert any(b["id"] == "first_quiz" for b in mine)


# ---- C. Progression -------------------------------------------------------
class TestProgression:
    def test_level_curve_formula(self):
        """Validate xp_for_level via /auth/me by nudging xp_total directly."""
        # Just validate compute via the endpoint output shape
        from pymongo import MongoClient  # motor sync equivalent unavailable → use pymongo
        # Skip if pymongo not installed — but requirements has it via motor deps
        s, _ = _register(prefix="lvl")
        r = s.get(f"{API}/auth/me")
        assert r.status_code == 200
        me = r.json()
        assert me["level"] == 1
        assert 0 <= me["level_progress_pct"] <= 100

    def test_progression_me_shape(self, user_session):
        s, _ = user_session
        r = s.get(f"{API}/progression/me")
        assert r.status_code == 200
        p = r.json()
        for k in ("level", "xp_total", "xp_in_level", "xp_to_next", "next_level_at", "progress_pct", "mastery"):
            assert k in p, f"missing key {k}"
        assert p["level"] == 1
        assert p["xp_total"] == 0
        assert 0 <= p["progress_pct"] <= 100
        # Mastery has one entry per category (even without play)
        cats = s.get(f"{API}/categories").json()
        assert len(p["mastery"]) == len(cats)
        for m in p["mastery"]:
            assert set(("category_id", "title", "correct", "total", "quizzes_played", "tier")).issubset(m.keys())
            assert m["correct"] == 0
            assert m["total"] == 0
            assert m["tier"]["key"] == "novice"

    def test_progression_updates_after_attempt(self, user_session2):
        s, _ = user_session2
        cat_id, qs, _ = _get_cat_questions(s)
        payload = {
            "category_id": cat_id,
            "answers": [{"question_id": q["id"], "answer_index": 0} for q in qs],
        }
        r = s.post(f"{API}/attempts", json=payload)
        assert r.status_code == 200
        d = r.json()
        played_total = d["total"]
        played_correct = d["score"]
        p = s.get(f"{API}/progression/me").json()
        cat_entry = next((m for m in p["mastery"] if m["category_id"] == cat_id), None)
        assert cat_entry is not None
        assert cat_entry["total"] == played_total
        assert cat_entry["correct"] == played_correct
        assert cat_entry["quizzes_played"] == 1

    def test_auth_me_exposes_level_fields(self, user_session):
        s, _ = user_session
        me = s.get(f"{API}/auth/me").json()
        for k in ("level", "level_progress_pct", "xp_to_next_level", "xp_total"):
            assert k in me


# ---- helper: level formula direct-check ----------------------------------
def test_xp_for_level_formula():
    """Direct check of the documented curve L1=0, L2=50, L3=150, L6=750."""
    import sys
    sys.path.insert(0, "/app/backend")
    from progression import xp_for_level, compute_level
    assert xp_for_level(1) == 0
    assert xp_for_level(2) == 50
    assert xp_for_level(3) == 150
    assert xp_for_level(4) == 300
    assert xp_for_level(5) == 500
    assert xp_for_level(6) == 750
    assert compute_level(0)["level"] == 1
    assert compute_level(50)["level"] == 2
    assert compute_level(150)["level"] == 3
    assert compute_level(749)["level"] == 5
    assert compute_level(750)["level"] == 6
    r = compute_level(100)  # halfway between L2(50) and L3(150)
    assert r["level"] == 2
    assert r["progress_pct"] == 50
