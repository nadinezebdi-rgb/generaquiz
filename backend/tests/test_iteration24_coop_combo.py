"""Iteration 24 — Sprint 2 Coop Récompensé.

Tests combo multiplier ×1.5 / ×2 / ×3, combo break behaviour, best_combo
persistence, solo_correct_count, and total_xp aggregation via the coop
answer endpoint.
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@generaquiz.fr"
ADMIN_PASSWORD = "Admin2026!"


# ---------------- fixtures ----------------

@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def category_id(admin_session):
    r = admin_session.get(f"{API}/categories")
    assert r.status_code == 200
    cats = r.json()
    assert len(cats) > 0
    # Pick a category with enough questions (>= 12)
    for c in cats:
        qr = admin_session.get(f"{API}/categories/{c['id']}/questions")
        if qr.status_code == 200 and len(qr.json()) >= 12:
            return c["id"]
    return cats[0]["id"]


@pytest.fixture
def coop_challenge(admin_session, category_id):
    """Create a fresh 10-question coop challenge for each test."""
    body = {
        "team_name": "TEST_coop_combo",
        "category_id": category_id,
        "players": [
            {"name": "Alice", "role": "senior"},
            {"name": "Bob",   "role": "jeune"},
        ],
        "num_questions": 10,
    }
    r = admin_session.post(f"{API}/coop-challenges", json=body)
    assert r.status_code == 200, f"create failed: {r.status_code} {r.text}"
    token = r.json()["token"]
    # Fetch to get correct_index for each question (admin owns it, so it's
    # actually stripped in _public_view). We'll answer correctly by iterating.
    yield token


def _get_challenge(session, token):
    """Fetch challenge via mine/list to inspect stats (public view has no correct_index)."""
    r = session.get(f"{API}/coop-challenges/{token}")
    assert r.status_code == 200
    return r.json()


def _correct_index_for(session, token, idx):
    """Public view doesn't expose correct_index — brute-force by trying answers.
    We instead read directly from mongo via a probe: try each of 0..3, and on
    server response we get is_correct. But that consumes the question. Instead,
    we use the answers_log after the fact. So we need a helper that answers
    correctly on first try — impossible via public API. Trick: use the internal
    stats after answer to determine correctness."""
    raise NotImplementedError


def answer_and_expect(session, token, answer_index, help_used=False):
    r = session.post(
        f"{API}/coop-challenges/{token}/answer",
        json={"answer_index": answer_index, "help_used": help_used},
    )
    assert r.status_code == 200, f"answer failed: {r.status_code} {r.text}"
    return r.json()


def answer_correctly(session, token, help_used=False):
    """Answer the current question correctly by trying options 0..3 until we
    hit the right one. Since the endpoint advances the cursor on any answer,
    we cannot retry. Alternative: read the DB directly.

    Actually since admin owns the challenge, we can also introspect via a
    Mongo shim — but tests should use HTTP only. Solution: after creating,
    read the challenge document via mongo directly through a small helper
    that hits an internal endpoint. Not available.

    Workaround: rely on the fact that after answering we know if correct;
    if wrong, we retry with a NEW challenge. That's expensive but reliable.

    Better: use pymongo directly (backend db). Test files usually do this."""
    raise NotImplementedError("use pymongo helper in tests")


# ------- Direct Mongo helper for reading correct_index -------

@pytest.fixture(scope="module")
def mongo_db():
    from pymongo import MongoClient
    mongo_url = os.environ["MONGO_URL"]
    db_name = os.environ["DB_NAME"]
    client = MongoClient(mongo_url)
    return client[db_name]


def get_correct_at(mongo_db, token, idx):
    doc = mongo_db.coop_challenges.find_one({"token": token})
    assert doc is not None
    return doc["questions"][idx]["correct_index"]


def answer_correct(session, mongo_db, token, help_used=False, current_idx=None):
    """Fetch correct_index from Mongo, then POST answer."""
    if current_idx is None:
        doc = mongo_db.coop_challenges.find_one({"token": token})
        current_idx = doc["current_index"]
    correct = get_correct_at(mongo_db, token, current_idx)
    return answer_and_expect(session, token, correct, help_used=help_used)


def answer_wrong(session, mongo_db, token, current_idx=None):
    if current_idx is None:
        doc = mongo_db.coop_challenges.find_one({"token": token})
        current_idx = doc["current_index"]
    correct = get_correct_at(mongo_db, token, current_idx)
    wrong = (correct + 1) % 4
    return answer_and_expect(session, token, wrong, help_used=False)


# ---------------- Tests ----------------

class TestComboMultiplier:
    """Backend combo multiplier tiers."""

    def test_combo_tier_1x_for_first_two_correct(self, admin_session, mongo_db, coop_challenge):
        token = coop_challenge
        # Q1 solo correct
        r1 = answer_correct(admin_session, mongo_db, token)
        assert r1["is_correct"] is True
        assert r1["combo"] == 1
        assert r1["multiplier"] == 1.0
        assert r1["base_xp"] == 100
        assert r1["xp_earned"] == 100
        assert r1["combo_broken"] is False

        # Q2 solo correct
        r2 = answer_correct(admin_session, mongo_db, token)
        assert r2["combo"] == 2
        assert r2["multiplier"] == 1.0
        assert r2["xp_earned"] == 100

    def test_combo_tier_1_5x_at_3_correct(self, admin_session, mongo_db, coop_challenge):
        token = coop_challenge
        answer_correct(admin_session, mongo_db, token)
        answer_correct(admin_session, mongo_db, token)
        r3 = answer_correct(admin_session, mongo_db, token)
        assert r3["combo"] == 3
        assert r3["multiplier"] == 1.5
        assert r3["base_xp"] == 100
        assert r3["xp_earned"] == 150
        # combo 4 also ×1.5
        r4 = answer_correct(admin_session, mongo_db, token)
        assert r4["combo"] == 4
        assert r4["multiplier"] == 1.5
        assert r4["xp_earned"] == 150

    def test_combo_tier_2x_at_5_correct(self, admin_session, mongo_db, coop_challenge):
        token = coop_challenge
        for _ in range(4):
            answer_correct(admin_session, mongo_db, token)
        r5 = answer_correct(admin_session, mongo_db, token)
        assert r5["combo"] == 5
        assert r5["multiplier"] == 2.0
        assert r5["xp_earned"] == 200
        r6 = answer_correct(admin_session, mongo_db, token)
        assert r6["combo"] == 6
        assert r6["multiplier"] == 2.0

    def test_combo_tier_3x_at_7_correct(self, admin_session, mongo_db, coop_challenge):
        token = coop_challenge
        for _ in range(6):
            answer_correct(admin_session, mongo_db, token)
        r7 = answer_correct(admin_session, mongo_db, token)
        assert r7["combo"] == 7
        assert r7["multiplier"] == 3.0
        assert r7["base_xp"] == 100
        assert r7["xp_earned"] == 300


class TestComboBreak:
    """Combo reset on wrong or help_used."""

    def test_wrong_answer_resets_combo(self, admin_session, mongo_db, coop_challenge):
        token = coop_challenge
        # Build combo of 3
        for _ in range(3):
            r = answer_correct(admin_session, mongo_db, token)
        assert r["combo"] == 3
        # Wrong answer
        rw = answer_wrong(admin_session, mongo_db, token)
        assert rw["is_correct"] is False
        assert rw["combo"] == 0
        assert rw["multiplier"] == 1.0
        assert rw["base_xp"] == 0
        assert rw["xp_earned"] == 0
        assert rw["combo_broken"] is True

    def test_help_used_correct_resets_combo(self, admin_session, mongo_db, coop_challenge):
        token = coop_challenge
        # Build combo of 3
        for _ in range(3):
            answer_correct(admin_session, mongo_db, token)
        # Correct with help_used=True
        rh = answer_correct(admin_session, mongo_db, token, help_used=True)
        assert rh["is_correct"] is True
        assert rh["combo"] == 0
        assert rh["base_xp"] == 50
        assert rh["xp_earned"] == 50
        assert rh["combo_broken"] is True
        assert rh["multiplier"] == 1.0

    def test_combo_broken_false_when_prev_below_3(self, admin_session, mongo_db, coop_challenge):
        token = coop_challenge
        # 1 correct then wrong — prev_combo=1 → combo_broken must be False
        answer_correct(admin_session, mongo_db, token)
        rw = answer_wrong(admin_session, mongo_db, token)
        assert rw["combo"] == 0
        assert rw["combo_broken"] is False


class TestStatsPersistence:
    """best_combo and solo_correct_count tracking."""

    def test_best_combo_persists_after_break(self, admin_session, mongo_db, coop_challenge):
        token = coop_challenge
        for _ in range(5):
            r = answer_correct(admin_session, mongo_db, token)
        assert r["stats_coop"]["current_combo"] == 5
        assert r["stats_coop"]["best_combo"] == 5
        # break the combo
        rw = answer_wrong(admin_session, mongo_db, token)
        assert rw["stats_coop"]["current_combo"] == 0
        assert rw["stats_coop"]["best_combo"] == 5  # persisted

    def test_solo_correct_count_only_when_solo(self, admin_session, mongo_db, coop_challenge):
        token = coop_challenge
        # 2 solo correct
        r = answer_correct(admin_session, mongo_db, token)
        r = answer_correct(admin_session, mongo_db, token)
        assert r["stats_coop"]["solo_correct_count"] == 2
        # 1 with help (correct)
        rh = answer_correct(admin_session, mongo_db, token, help_used=True)
        assert rh["stats_coop"]["solo_correct_count"] == 2  # unchanged
        assert rh["stats_coop"]["helps_used"] == 1
        assert rh["stats_coop"]["helps_successful"] == 1
        assert rh["stats_coop"]["correct_count"] == 3
        # 1 wrong
        rw = answer_wrong(admin_session, mongo_db, token)
        assert rw["stats_coop"]["solo_correct_count"] == 2

    def test_total_xp_cumulates_with_multiplier(self, admin_session, mongo_db, coop_challenge):
        token = coop_challenge
        # 7 solo correct in a row → expected total XP:
        # 100, 100, 150, 150, 200, 200, 300 = 1200
        expected = [100, 100, 150, 150, 200, 200, 300]
        running = 0
        for exp_xp in expected:
            r = answer_correct(admin_session, mongo_db, token)
            running += exp_xp
            assert r["xp_earned"] == exp_xp
            assert r["stats_coop"]["total_xp"] == running
        assert running == 1200


class TestFullFlowRegression:
    """Regression: full 4-question challenge to make sure existing flow still
    works end-to-end after Sprint 2 changes."""

    def test_full_4q_challenge_completes(self, admin_session, mongo_db, category_id):
        body = {
            "team_name": "TEST_regression",
            "category_id": category_id,
            "players": [
                {"name": "Reg1", "role": "senior"},
                {"name": "Reg2", "role": "jeune"},
            ],
            "num_questions": 4,
        }
        r = admin_session.post(f"{API}/coop-challenges", json=body)
        assert r.status_code == 200
        token = r.json()["token"]

        # Answer all 4 correctly
        for i in range(4):
            resp = answer_correct(admin_session, mongo_db, token)
            if i < 3:
                assert resp["completed"] is False
                assert resp["next_question"] is not None
            else:
                assert resp["completed"] is True
                assert resp["next_question"] is None

        # Final state
        final = _get_challenge(admin_session, token)
        assert final["status"] == "completed"
        assert final["completed_at"] is not None
        assert final["stats_coop"]["correct_count"] == 4
        assert final["stats_coop"]["solo_correct_count"] == 4
        assert final["stats_coop"]["best_combo"] == 4
        # combo tiers: 100,100,150,150 = 500
        assert final["stats_coop"]["total_xp"] == 500

    def test_completed_challenge_rejects_more_answers(self, admin_session, mongo_db, category_id):
        body = {
            "team_name": "TEST_completed_reject",
            "category_id": category_id,
            "players": [
                {"name": "A", "role": "senior"},
                {"name": "B", "role": "jeune"},
            ],
            "num_questions": 4,
        }
        r = admin_session.post(f"{API}/coop-challenges", json=body)
        token = r.json()["token"]
        for _ in range(4):
            answer_correct(admin_session, mongo_db, token)
        # Extra answer should 400
        rr = admin_session.post(
            f"{API}/coop-challenges/{token}/answer",
            json={"answer_index": 0, "help_used": False},
        )
        assert rr.status_code == 400
