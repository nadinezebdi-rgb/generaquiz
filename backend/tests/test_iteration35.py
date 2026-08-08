"""Iteration 35 — Charades expansion, Mots Fléchés MVP, Grid Themes IA rotation."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:3000").rstrip("/") + "/api"
ADMIN_EMAIL = "admin@generaquiz.fr"
ADMIN_PASSWORD = "Admin2026!"


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def user_session():
    """Register a fresh test user."""
    import uuid
    email = f"TEST_iter35_{uuid.uuid4().hex[:8]}@example.com"
    s = requests.Session()
    r = s.post(f"{BASE_URL}/auth/register", json={"email": email, "password": "Test2026!", "name": "Iter35"})
    assert r.status_code in (200, 201), f"register failed: {r.text}"
    return s


# ==================== Grid Themes IA rotation ====================
class TestGridThemes:
    def test_theme_families_present(self):
        import sys
        sys.path.insert(0, "/app/backend")
        from wordsearch_mistral import THEME_FAMILIES
        families = {t["family"] for t in THEME_FAMILIES}
        expected = {
            "Régions françaises", "Années 60", "Métiers d'autrefois",
            "Cuisine régionale", "Jardin & saisons", "Chansons françaises",
            "Cinéma classique", "Sport à la française", "Écrivains & poètes",
            "Vie quotidienne d'antan",
        }
        missing = expected - families
        assert not missing, f"Missing theme families: {missing}"
        assert len(THEME_FAMILIES) == 10


# ==================== Charades — Admin generate ====================
class TestCharadesAdmin:
    def test_non_admin_forbidden(self, user_session):
        r = user_session.post(f"{BASE_URL}/charades/admin/generate")
        assert r.status_code == 403, f"expected 403, got {r.status_code}: {r.text}"

    def test_admin_generate_once(self, admin_session):
        r = admin_session.post(f"{BASE_URL}/charades/admin/generate", timeout=60)
        assert r.status_code == 200, f"{r.status_code}: {r.text}"
        data = r.json()
        assert "pack" in data
        assert "attempted" in data
        assert "accepted" in data
        assert "rejected_reasons" in data
        assert isinstance(data["rejected_reasons"], list)

    def test_admin_generate_twice(self, admin_session):
        r = admin_session.post(f"{BASE_URL}/charades/admin/generate", timeout=60)
        assert r.status_code == 200
        # accepted can be 0 (all duplicates) but the endpoint must still succeed
        data = r.json()
        assert "accepted" in data


# ==================== Charades — Dynamic packs ====================
class TestCharadesPacks:
    def test_packs_include_static_and_mistral(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/charades/packs")
        assert r.status_code == 200
        packs = r.json()
        by_id = {p["id"]: p for p in packs}
        # Static must be present
        assert "classique" in by_id
        assert "nature" in by_id
        assert "cuisine" in by_id
        assert by_id["classique"]["total"] >= 13
        assert by_id["nature"]["total"] >= 4
        assert by_id["cuisine"]["total"] >= 2

    def test_mistral_charade_attempt(self, admin_session):
        # Find a mistral-generated pack
        r = admin_session.get(f"{BASE_URL}/charades/packs")
        packs = r.json()
        # Try each non-static pack
        mistral_pack = None
        for p in packs:
            if p["id"] not in {"classique", "nature", "cuisine"} and p["total"] > 0:
                mistral_pack = p["id"]
                break
        if not mistral_pack:
            # Maybe mistral generated inside classique/nature/cuisine; look at /list for source
            r2 = admin_session.get(f"{BASE_URL}/charades/list", params={"pack": "classique"})
            pytest.skip("No mistral pack available")
            return

        r = admin_session.get(f"{BASE_URL}/charades/list", params={"pack": mistral_pack})
        assert r.status_code == 200
        chars = r.json()["charades"]
        assert len(chars) > 0
        c = chars[0]
        assert "id" in c
        assert "parts" in c
        # Wrong answer
        r_wrong = admin_session.post(f"{BASE_URL}/charades/attempt",
                                     json={"charade_id": c["id"], "answer": "zzzzzz_wrong"})
        assert r_wrong.status_code == 200
        assert r_wrong.json()["correct"] is False
        assert "expected" in r_wrong.json()

        # Correct answer using expected
        expected = r_wrong.json()["expected"]
        r_ok = admin_session.post(f"{BASE_URL}/charades/attempt",
                                  json={"charade_id": c["id"], "answer": expected})
        assert r_ok.status_code == 200
        j = r_ok.json()
        # Might have already been solved on prior runs — accept either
        assert j["correct"] is True
        # Idempotent: second time no points
        r_again = admin_session.post(f"{BASE_URL}/charades/attempt",
                                     json={"charade_id": c["id"], "answer": expected})
        assert r_again.status_code == 200
        assert r_again.json()["points_gained"] == 0


# ==================== Mots Fléchés ====================
class TestMotsFleches:
    def test_list_5_grids(self, user_session):
        r = user_session.get(f"{BASE_URL}/mots-fleches/grids")
        assert r.status_code == 200
        grids = r.json()
        assert len(grids) == 5
        ids = [g["id"] for g in grids]
        assert ids == ["mf01", "mf02", "mf03", "mf04", "mf05"]
        for g in grids:
            assert g["size"] == 5
            assert g["completed"] is False
            assert g["best_score"] == 0
            assert "theme" in g and "emoji" in g and "difficulty" in g

    def test_get_grid_no_answer_leak(self, user_session):
        r = user_session.get(f"{BASE_URL}/mots-fleches/grids/mf01")
        assert r.status_code == 200
        g = r.json()
        assert len(g["cells"]) == 5
        for row in g["cells"]:
            assert len(row) == 5
            for c in row:
                assert c["type"] in ("block", "letter")
                assert "answer" not in c  # anti-cheat

    def test_submit_correct(self, user_session):
        letters = [
            ["", "", "", "", ""],
            ["", "R", "I", "T", "S"],
            ["", "A", "B", "H", "O"],
            ["", "W", "L", "Y", "U"],
            ["", "M", "E", "M", "R"],
        ]
        r = user_session.post(f"{BASE_URL}/mots-fleches/grids/mf01/submit", json={"letters": letters})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["correct_cells"] == 16
        assert d["total_cells"] == 16
        assert d["accuracy_pct"] == 100
        assert d["completed"] is True
        assert d["points_gained"] >= 16
        assert d["best_score"] >= 21
        assert len(d["mistakes"]) == 5
        assert all(len(row) == 5 for row in d["mistakes"])
        assert all(not v for row in d["mistakes"] for v in row)

    def test_submit_idempotent(self, user_session):
        letters = [
            ["", "", "", "", ""],
            ["", "R", "I", "T", "S"],
            ["", "A", "B", "H", "O"],
            ["", "W", "L", "Y", "U"],
            ["", "M", "E", "M", "R"],
        ]
        r = user_session.post(f"{BASE_URL}/mots-fleches/grids/mf01/submit", json={"letters": letters})
        assert r.status_code == 200
        assert r.json()["points_gained"] == 0

    def test_submit_partial(self, user_session):
        import uuid
        email = f"TEST_iter35b_{uuid.uuid4().hex[:8]}@example.com"
        s = requests.Session()
        s.post(f"{BASE_URL}/auth/register", json={"email": email, "password": "Test2026!", "name": "Iter35b"})
        # 8 correct + 8 wrong
        letters = [
            ["", "", "", "", ""],
            ["", "R", "I", "T", "S"],   # 4 correct
            ["", "A", "B", "H", "O"],   # 4 correct
            ["", "X", "X", "X", "X"],   # 4 wrong
            ["", "X", "X", "X", "X"],   # 4 wrong
        ]
        r = s.post(f"{BASE_URL}/mots-fleches/grids/mf01/submit", json={"letters": letters})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["correct_cells"] == 8
        assert d["completed"] is False
        # Check mistakes at wrong positions
        assert d["mistakes"][3][1] is True
        assert d["mistakes"][4][4] is True
        # Correct positions should have no mistake flag
        assert d["mistakes"][1][1] is False

    def test_submit_bad_dimensions(self, user_session):
        letters = [["", "", "", "", ""]] * 4  # 4x5 not 5x5
        r = user_session.post(f"{BASE_URL}/mots-fleches/grids/mf01/submit", json={"letters": letters})
        assert r.status_code == 400
        assert "Dimensions" in r.json().get("detail", "")

    def test_grid_not_found(self, user_session):
        r = user_session.get(f"{BASE_URL}/mots-fleches/grids/mf99")
        assert r.status_code == 404
