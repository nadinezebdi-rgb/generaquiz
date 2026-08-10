"""Iteration 37 — Mots Fléchés v3: mf06 magic-square grid + arrow markers.

Covers:
- GET /api/mots-fleches/grids includes mf06 (rows:4, cols:4, difficulté:difficile)
- GET /api/mots-fleches/grids/mf06: 4x4 with block row 0 (clue_v banner), block col 0 (clue_h),
  9 letter cells at rows 1-3 cols 1-3 without 'answer' field (anti-cheat).
- POST submit correct MER/EAU/RUE matrix → correct_cells:9, total_cells:9, completed:true,
  points_gained:14 on first, 0 on second (idempotent).
- Mental crossword check: cols 1..3 spell MER, EAU, RUE from letters.
- Regression: mf01..mf05 still present.
"""
from __future__ import annotations

import os
import uuid
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@generaquiz.fr"
ADMIN_PASSWORD = "Admin2026!"


@pytest.fixture(scope="module")
def user_session():
    """Register a fresh user to isolate progress (avoids best_score leftovers)."""
    s = requests.Session()
    email = f"TEST_iter37_{uuid.uuid4().hex[:8]}@example.com"
    r = s.post(f"{API}/auth/register", json={
        "email": email, "password": "Passw0rd!", "name": "Iter37 Tester",
    })
    assert r.status_code in (200, 201), f"register: {r.status_code} {r.text}"
    # Some auth flows require explicit login after register
    if "access_token" not in r.text and "session" not in s.cookies.get_dict():
        lr = s.post(f"{API}/auth/login", json={"email": email, "password": "Passw0rd!"})
        assert lr.status_code == 200, f"login: {lr.status_code} {lr.text}"
    return s


# -------- list grids --------
def test_grids_list_contains_mf06(user_session):
    r = user_session.get(f"{API}/mots-fleches/grids")
    assert r.status_code == 200, r.text
    grids = r.json()
    ids = [g["id"] for g in grids]
    # regression: 5 static
    for sid in ["mf01", "mf02", "mf03", "mf04", "mf05"]:
        assert sid in ids, f"missing static grid {sid}"
    assert "mf06" in ids, f"mf06 missing from grids list: {ids}"
    mf06 = next(g for g in grids if g["id"] == "mf06")
    assert mf06["rows"] == 4
    assert mf06["cols"] == 4
    assert mf06["difficulty"] == "difficile"
    assert "magique" in mf06["theme"].lower() or "carré" in mf06["theme"].lower()


# -------- get mf06 --------
def test_get_mf06_structure_and_anticheat(user_session):
    r = user_session.get(f"{API}/mots-fleches/grids/mf06")
    assert r.status_code == 200, r.text
    g = r.json()
    assert g["rows"] == 4 and g["cols"] == 4
    cells = g["cells"]
    assert len(cells) == 4 and all(len(row) == 4 for row in cells)

    # Row 0 should be all blocks; positions (0,1..3) should have clue_v banner
    for c in cells[0]:
        assert c["type"] == "block"
    for j in (1, 2, 3):
        assert "clue_v" in cells[0][j], f"row0 col{j} missing clue_v: {cells[0][j]}"

    # Column 0 rows 1..3 blocks with clue_h
    for i in (1, 2, 3):
        assert cells[i][0]["type"] == "block"
        assert "clue_h" in cells[i][0], f"row{i} col0 missing clue_h: {cells[i][0]}"

    # 9 letter cells at rows 1..3 cols 1..3, no 'answer' leak
    letter_count = 0
    for i in (1, 2, 3):
        for j in (1, 2, 3):
            c = cells[i][j]
            assert c["type"] == "letter", f"cell ({i},{j}) not letter: {c}"
            assert "answer" not in c, f"answer leak at ({i},{j}): {c}"
            letter_count += 1
    assert letter_count == 9


# -------- submit correct --------
def _correct_matrix():
    return [
        ["", "", "", ""],
        ["", "M", "E", "R"],
        ["", "E", "A", "U"],
        ["", "R", "U", "E"],
    ]


def test_submit_mf06_correct_then_idempotent(user_session):
    payload = {"letters": _correct_matrix()}
    r1 = user_session.post(f"{API}/mots-fleches/grids/mf06/submit", json=payload)
    assert r1.status_code == 200, r1.text
    d1 = r1.json()
    assert d1["correct_cells"] == 9
    assert d1["total_cells"] == 9
    assert d1["completed"] is True
    assert d1["points_gained"] == 14, f"expected 14 (9 letters + 5 bonus), got {d1['points_gained']}"
    assert d1["best_score"] == 14

    # Idempotent: 2nd correct submit awards 0 new points
    r2 = user_session.post(f"{API}/mots-fleches/grids/mf06/submit", json=payload)
    assert r2.status_code == 200, r2.text
    d2 = r2.json()
    assert d2["correct_cells"] == 9
    assert d2["completed"] is True
    assert d2["points_gained"] == 0, f"expected 0 on repeat, got {d2['points_gained']}"
    assert d2["best_score"] == 14


# -------- crossword check: columns spell real words --------
def test_mf06_columns_spell_real_words():
    """Read the private data directly to prove col1=MER, col2=EAU, col3=RUE."""
    import sys, importlib
    sys.path.insert(0, "/app/backend")
    m = importlib.import_module("mots_fleches_data")
    mf06 = next(g for g in m.GRIDS if g["id"] == "mf06")
    cells = mf06["cells"]
    col1 = "".join(cells[i][1]["answer"] for i in (1, 2, 3))
    col2 = "".join(cells[i][2]["answer"] for i in (1, 2, 3))
    col3 = "".join(cells[i][3]["answer"] for i in (1, 2, 3))
    assert col1 == "MER", f"col1={col1}"
    assert col2 == "EAU", f"col2={col2}"
    assert col3 == "RUE", f"col3={col3}"
    # rows also
    row1 = "".join(cells[1][j]["answer"] for j in (1, 2, 3))
    row2 = "".join(cells[2][j]["answer"] for j in (1, 2, 3))
    row3 = "".join(cells[3][j]["answer"] for j in (1, 2, 3))
    assert row1 == "MER"
    assert row2 == "EAU"
    assert row3 == "RUE"


# -------- regression: bad dimensions --------
def test_submit_mf06_bad_dimensions(user_session):
    bad = {"letters": [["", "", "", ""]] * 3}  # 3x4 instead of 4x4
    r = user_session.post(f"{API}/mots-fleches/grids/mf06/submit", json=bad)
    assert r.status_code == 400
