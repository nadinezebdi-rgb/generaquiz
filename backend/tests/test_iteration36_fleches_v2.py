"""Iteration 36 — Mots Fléchés v2 (non-square, Mistral generator, admin trigger)."""
import os
import time
import uuid
import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://caricature-saas.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api"

ADMIN_EMAIL = "admin@generaquiz.fr"
ADMIN_PW = "Admin2026!"


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PW})
    assert r.status_code == 200, r.text
    return s


@pytest.fixture(scope="module")
def user_session():
    s = requests.Session()
    email = f"TEST_iter36_{uuid.uuid4().hex[:8]}@example.com"
    r = s.post(f"{API}/auth/register", json={
        "email": email, "password": "Pass1234!", "name": "Iter36 Tester"
    })
    assert r.status_code in (200, 201), r.text
    return s


def test_grids_list_includes_static(user_session):
    r = user_session.get(f"{API}/mots-fleches/grids")
    assert r.status_code == 200
    grids = r.json()
    ids = {g["id"] for g in grids}
    for sid in ["mf01", "mf02", "mf03", "mf04", "mf05"]:
        assert sid in ids, f"Missing static grid {sid}"
    for g in grids:
        assert "rows" in g and "cols" in g and "source" in g
        assert g["rows"] > 0 and g["cols"] > 0
    seeds = [g for g in grids if g["source"] == "seed"]
    assert len(seeds) >= 5


def test_get_grid_no_answer_leak(user_session):
    r = user_session.get(f"{API}/mots-fleches/grids/mf01")
    assert r.status_code == 200
    grid = r.json()
    assert grid["rows"] > 0 and grid["cols"] > 0
    for row in grid["cells"]:
        for cell in row:
            if cell["type"] == "letter":
                assert "answer" not in cell, "Answer leaked in public grid"


def test_submit_static_mf01_correct(user_session):
    matrix = [
        ["", "", "", "", ""],
        ["", "R", "I", "T", "S"],
        ["", "A", "B", "H", "O"],
        ["", "W", "L", "Y", "U"],
        ["", "M", "E", "M", "R"],
    ]
    r = user_session.post(f"{API}/mots-fleches/grids/mf01/submit", json={"letters": matrix})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["correct_cells"] == 16
    assert data["total_cells"] == 16
    assert data["completed"] is True


def test_submit_bad_dimensions(user_session):
    # 3x3 payload for a 5x5 grid → 400
    r = user_session.post(f"{API}/mots-fleches/grids/mf01/submit", json={
        "letters": [["", "", ""], ["", "", ""], ["", "", ""]]
    })
    assert r.status_code == 400
    assert "Dimensions" in r.text


def test_admin_generate_forbidden_for_regular_user(user_session):
    r = user_session.post(f"{API}/mots-fleches/admin/generate")
    assert r.status_code == 403


def test_admin_generate_and_reuse(admin_session, user_session):
    # Check if a Mistral-generated grid already exists — reuse to save time
    r = user_session.get(f"{API}/mots-fleches/grids")
    assert r.status_code == 200
    grids = r.json()
    mistral_grids = [g for g in grids if g["source"] == "mistral"]

    if not mistral_grids:
        # Trigger one generation (real Mistral call ~10-20s)
        r = admin_session.post(f"{API}/mots-fleches/admin/generate", timeout=60)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "grid_id" in body and "ok" in body
        if not body["ok"]:
            pytest.skip("Mistral generation returned ok:false — skipping mistral-dependent checks")
        gid = body["grid_id"]
        assert isinstance(gid, str) and gid.startswith("mfg-")
        # Refresh list
        time.sleep(1)
        r = user_session.get(f"{API}/mots-fleches/grids")
        grids = r.json()
        mistral_grids = [g for g in grids if g["source"] == "mistral"]

    assert len(mistral_grids) > 0, "No Mistral-generated grids appeared"
    mg = mistral_grids[0]
    assert mg["rows"] > 0 and mg["cols"] > 0
    assert mg["source"] == "mistral"

    # Fetch the mistral grid detail
    r = user_session.get(f"{API}/mots-fleches/grids/{mg['id']}")
    assert r.status_code == 200
    detail = r.json()
    rows, cols = detail["rows"], detail["cols"]
    assert len(detail["cells"]) == rows
    assert all(len(row) == cols for row in detail["cells"])
    # anti-cheat
    for row in detail["cells"]:
        for cell in row:
            if cell["type"] == "letter":
                assert "answer" not in cell

    # Submit empty matrix of the correct shape
    empty = [["" for _ in range(cols)] for _ in range(rows)]
    r = user_session.post(f"{API}/mots-fleches/grids/{mg['id']}/submit", json={"letters": empty})
    assert r.status_code == 200, r.text
    sub = r.json()
    assert sub["correct_cells"] == 0
    assert sub["total_cells"] > 0
    assert sub["completed"] is False
    assert len(sub["mistakes"]) == rows
    assert all(len(row) == cols for row in sub["mistakes"])
    assert all(not v for row in sub["mistakes"] for v in row)

    # Wrong dimensions → 400
    r = user_session.post(
        f"{API}/mots-fleches/grids/{mg['id']}/submit",
        json={"letters": [["", ""], ["", ""]]},
    )
    assert r.status_code == 400
