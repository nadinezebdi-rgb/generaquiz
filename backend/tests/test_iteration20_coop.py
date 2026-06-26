"""Iteration 20 — Cooperative Challenges (Défi Famille Coop) + birth_year on register.

Tests:
- POST /api/coop-challenges (create, validation, same role error, unknown category)
- GET /api/coop-challenges/{token} (auth, ownership, no answer leakage, alternating roles)
- POST /api/coop-challenges/{token}/answer (xp scoring, completion, idempotency)
- GET /api/coop-challenges/mine/list (listing + total_questions)
- Register with birth_year → age_group (senior/jeune/libre/null)
- PATCH /api/auth/profile birth_year update
"""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"


# ---------- Fixtures ----------
@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _register(s, suffix="", birth_year=None):
    email = f"TEST_coop_{suffix}_{uuid.uuid4().hex[:6]}@example.com"
    body = {"email": email, "password": "Coop2026!", "name": f"Coop {suffix}"}
    if birth_year is not None:
        body["birth_year"] = birth_year
    r = s.post(f"{API}/auth/register", json=body)
    assert r.status_code == 200, f"register failed: {r.status_code} {r.text}"
    data = r.json()
    return data, email


@pytest.fixture(scope="module")
def user_a(session):
    # fresh isolated session for user A (cookies stored)
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    data, email = _register(s, "A")
    return {"session": s, "email": email, "user": data.get("user")}


@pytest.fixture(scope="module")
def user_b(session):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    data, email = _register(s, "B")
    return {"session": s, "email": email, "user": data.get("user")}


@pytest.fixture(scope="module")
def category_id(user_a):
    r = user_a["session"].get(f"{API}/categories")
    assert r.status_code == 200
    cats = r.json()
    assert len(cats) >= 1
    return cats[0]["id"]


# ---------- birth_year + age_group ----------
class TestBirthYear:
    def test_register_senior(self):
        s = requests.Session(); s.headers.update({"Content-Type": "application/json"})
        _, _ = _register(s, "senior", birth_year=1955)
        me = s.get(f"{API}/auth/me").json()
        assert me["birth_year"] == 1955
        assert me["age_group"] == "senior"

    def test_register_jeune(self):
        s = requests.Session(); s.headers.update({"Content-Type": "application/json"})
        _, _ = _register(s, "jeune", birth_year=2010)
        me = s.get(f"{API}/auth/me").json()
        assert me["birth_year"] == 2010
        assert me["age_group"] == "jeune"

    def test_register_libre(self):
        s = requests.Session(); s.headers.update({"Content-Type": "application/json"})
        _, _ = _register(s, "libre", birth_year=1985)
        me = s.get(f"{API}/auth/me").json()
        assert me["birth_year"] == 1985
        assert me["age_group"] == "libre"

    def test_register_no_birth_year(self):
        s = requests.Session(); s.headers.update({"Content-Type": "application/json"})
        _, _ = _register(s, "noby")
        me = s.get(f"{API}/auth/me").json()
        assert me.get("birth_year") is None
        assert me.get("age_group") is None

    def test_patch_profile_birth_year(self):
        s = requests.Session(); s.headers.update({"Content-Type": "application/json"})
        _, _ = _register(s, "patch")
        me = s.get(f"{API}/auth/me").json()
        assert me.get("birth_year") is None
        r = s.patch(f"{API}/auth/profile", json={"name": me["name"], "birth_year": 1960})
        assert r.status_code == 200, r.text
        me2 = s.get(f"{API}/auth/me").json()
        assert me2["birth_year"] == 1960
        assert me2["age_group"] == "senior"


# ---------- Coop Challenge creation ----------
class TestCoopCreate:
    def test_create_ok(self, user_a, category_id):
        s = user_a["session"]
        body = {
            "team_name": "TEST_Aventuriers",
            "category_id": category_id,
            "num_questions": 4,
            "players": [
                {"name": "Mamie", "role": "senior"},
                {"name": "Lou", "role": "jeune"},
            ],
        }
        r = s.post(f"{API}/coop-challenges", json=body)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "token" in data and isinstance(data["token"], str)
        assert data["total"] == 4
        assert data["team_name"] == "TEST_Aventuriers"

    def test_same_role_returns_400(self, user_a, category_id):
        s = user_a["session"]
        body = {
            "team_name": "TEST_Same",
            "category_id": category_id,
            "num_questions": 4,
            "players": [
                {"name": "A", "role": "senior"},
                {"name": "B", "role": "senior"},
            ],
        }
        r = s.post(f"{API}/coop-challenges", json=body)
        assert r.status_code == 400, r.text

    def test_unknown_category_404(self, user_a):
        s = user_a["session"]
        body = {
            "team_name": "TEST_Unk",
            "category_id": "does-not-exist-xyz",
            "num_questions": 4,
            "players": [
                {"name": "A", "role": "senior"},
                {"name": "B", "role": "jeune"},
            ],
        }
        r = s.post(f"{API}/coop-challenges", json=body)
        assert r.status_code == 404, r.text

    def test_unauth_create_returns_401(self, category_id):
        s = requests.Session(); s.headers.update({"Content-Type": "application/json"})
        body = {
            "team_name": "X", "category_id": category_id, "num_questions": 4,
            "players": [{"name": "A", "role": "senior"}, {"name": "B", "role": "jeune"}],
        }
        r = s.post(f"{API}/coop-challenges", json=body)
        assert r.status_code == 401


# ---------- Coop Challenge GET ----------
class TestCoopGet:
    @pytest.fixture(scope="class")
    def created(self, user_a, category_id):
        s = user_a["session"]
        body = {
            "team_name": "TEST_Get",
            "category_id": category_id,
            "num_questions": 4,
            "players": [
                {"name": "Mamie", "role": "senior"},
                {"name": "Lou", "role": "jeune"},
            ],
        }
        r = s.post(f"{API}/coop-challenges", json=body)
        return r.json()

    def test_get_owner_ok_and_no_leakage(self, user_a, created):
        s = user_a["session"]
        r = s.get(f"{API}/coop-challenges/{created['token']}")
        assert r.status_code == 200
        data = r.json()
        assert data["team_name"] == "TEST_Get"
        assert len(data["questions"]) == 4
        # Alternating roles: Q0 -> player1.role (senior), Q1 -> player2.role (jeune)
        assert data["questions"][0]["assigned_to"] == "senior"
        assert data["questions"][1]["assigned_to"] == "jeune"
        assert data["questions"][2]["assigned_to"] == "senior"
        assert data["questions"][3]["assigned_to"] == "jeune"
        # No correct_index / explanation leakage
        for q in data["questions"]:
            assert "correct_index" not in q
            assert "explanation" not in q
            assert set(q.keys()) >= {"id", "question", "options", "assigned_to"}

    def test_get_non_owner_returns_403(self, user_b, created):
        r = user_b["session"].get(f"{API}/coop-challenges/{created['token']}")
        assert r.status_code == 403

    def test_get_unknown_token_404(self, user_a):
        r = user_a["session"].get(f"{API}/coop-challenges/notatoken123")
        assert r.status_code == 404


# ---------- Coop Answer flow + completion + idempotency ----------
class TestCoopAnswerFlow:
    def test_full_flow_scoring_and_completion(self, user_a, category_id):
        s = user_a["session"]
        body = {
            "team_name": "TEST_Flow",
            "category_id": category_id,
            "num_questions": 4,
            "players": [
                {"name": "Mamie", "role": "senior"},
                {"name": "Lou", "role": "jeune"},
            ],
        }
        cr = s.post(f"{API}/coop-challenges", json=body)
        assert cr.status_code == 200
        token = cr.json()["token"]

        # Need server-side correct_index; fetch via mongo not available — use exhaustive trick:
        # Try answer 0 with help_used = (True, False, False, False), inspect XP earned.
        # We can verify XP=100 (solo correct) or XP=50 (help correct) or XP=0 (wrong).
        xp_seen = []
        helps_used_pattern = [False, True, False, True]  # mix
        for i in range(4):
            r = s.post(f"{API}/coop-challenges/{token}/answer",
                       json={"answer_index": 0, "help_used": helps_used_pattern[i]})
            assert r.status_code == 200, r.text
            d = r.json()
            xp_seen.append(d["xp_earned"])
            # XP must be one of (0, 50, 100)
            assert d["xp_earned"] in (0, 50, 100)
            if d["xp_earned"] == 100:
                assert d["is_correct"] is True and helps_used_pattern[i] is False
            if d["xp_earned"] == 50:
                assert d["is_correct"] is True and helps_used_pattern[i] is True
            if d["xp_earned"] == 0:
                assert d["is_correct"] is False
            # next_question semantics
            if i < 3:
                assert d["completed"] is False
                assert d["next_question"] is not None
                assert "correct_index" not in d["next_question"]
            else:
                assert d["completed"] is True
                assert d["next_question"] is None

        # Final stats coherence
        get = s.get(f"{API}/coop-challenges/{token}").json()
        stats = get["stats_coop"]
        assert stats["total_xp"] == sum(xp_seen)
        assert stats["correct_count"] == sum(1 for x in xp_seen if x > 0)
        assert stats["helps_used"] == sum(1 for u in helps_used_pattern if u)
        assert get["status"] == "completed"

        # Idempotency — answer after completion returns 400
        r2 = s.post(f"{API}/coop-challenges/{token}/answer",
                    json={"answer_index": 0, "help_used": False})
        assert r2.status_code == 400
        assert "terminé" in r2.json().get("detail", "").lower() or "termin" in r2.json().get("detail", "").lower()


# ---------- Listing ----------
class TestCoopList:
    def test_mine_list_sorted_and_no_answers(self, user_a, category_id):
        s = user_a["session"]
        # Create two challenges close in time
        for i in range(2):
            s.post(f"{API}/coop-challenges", json={
                "team_name": f"TEST_List_{i}",
                "category_id": category_id,
                "num_questions": 4,
                "players": [
                    {"name": "A", "role": "senior"},
                    {"name": "B", "role": "jeune"},
                ],
            })
            time.sleep(0.05)
        r = s.get(f"{API}/coop-challenges/mine/list")
        assert r.status_code == 200, r.text
        rows = r.json()
        assert isinstance(rows, list) and len(rows) >= 2
        # total_questions injected
        assert all("total_questions" in row for row in rows)
        # No correct_index / explanation in questions
        for row in rows:
            for q in row.get("questions", []):
                assert "correct_index" not in q
                assert "explanation" not in q
        # Sorted by created_at desc
        created = [row.get("created_at") for row in rows if row.get("created_at")]
        assert created == sorted(created, reverse=True)
