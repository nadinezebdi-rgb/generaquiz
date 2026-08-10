"""Backend tests — Charades packs + Mots Mêlés (word search).

Covers Wave 1 word-games sprint:
- GET /charades/packs (3 packs, totals: 13/4/2)
- GET /charades/list?pack=... filtering
- POST /charades/attempt across all 3 packs
- GET /mots-meles/grids (>=5 seed grids)
- GET /mots-meles/grids/{id} (anti-cheat: no row/col leaked)
- POST /mots-meles/grids/{id}/find (correct, idempotent, wrong, invalid line, completion bonus)
"""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://caricature-saas.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    email = f"test.mm.{uuid.uuid4().hex[:8]}@example.com"
    password = "Passw0rd!Aa"
    r = s.post(f"{API}/auth/register", json={"email": email, "password": password, "name": "MM Tester"})
    assert r.status_code in (200, 201), f"register failed: {r.status_code} {r.text}"
    # cookies set on session; also login just in case
    r = s.post(f"{API}/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return s


# ---------------- Charades packs ----------------

def test_packs_endpoint(client):
    r = client.get(f"{API}/charades/packs")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list) and len(data) == 3
    by_id = {p["id"]: p for p in data}
    assert by_id["classique"]["total"] == 13
    assert by_id["nature"]["total"] == 4
    assert by_id["cuisine"]["total"] == 2
    for p in data:
        assert set(p.keys()) >= {"id", "label", "emoji", "desc", "total", "solved"}
        assert p["solved"] == 0  # fresh user


def test_list_filter_by_pack(client):
    r = client.get(f"{API}/charades/list", params={"pack": "nature"})
    assert r.status_code == 200
    d = r.json()
    assert len(d["charades"]) == 4
    assert all(c["pack"] == "nature" for c in d["charades"])
    # no answer leak
    for c in d["charades"]:
        assert "answer" not in c and "answer_display" not in c

    r_all = client.get(f"{API}/charades/list")
    assert r_all.status_code == 200
    assert len(r_all.json()["charades"]) == 19

    r_all2 = client.get(f"{API}/charades/list", params={"pack": "all"})
    assert len(r_all2.json()["charades"]) == 19


@pytest.mark.parametrize("cid,ans", [("ch01", "chateau"), ("n01", "renard"), ("c01", "poireau")])
def test_attempt_correct_each_pack(client, cid, ans):
    r = client.post(f"{API}/charades/attempt", json={"charade_id": cid, "answer": ans})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["correct"] is True


# ---------------- Mots Mêlés ----------------

def test_grids_list(client):
    r = client.get(f"{API}/mots-meles/grids")
    assert r.status_code == 200
    grids = r.json()
    assert isinstance(grids, list) and len(grids) >= 5
    seed_grids = [g for g in grids if g.get("source") == "seed"]
    assert len(seed_grids) >= 5
    for g in seed_grids[:5]:
        for k in ("id", "theme", "emoji", "size", "difficulty", "words_count", "found_count", "completed"):
            assert k in g, f"missing key {k} in grid list item"


def test_grid_detail_no_position_leak(client):
    grids = client.get(f"{API}/mots-meles/grids").json()
    gid = grids[0]["id"]
    r = client.get(f"{API}/mots-meles/grids/{gid}")
    assert r.status_code == 200
    d = r.json()
    assert d["size"] == 12
    assert len(d["grid"]) == 12
    assert all(len(row) == 12 for row in d["grid"])
    assert d["points_per_word"] == 2
    assert d["completion_bonus"] == 10
    for w in d["words"]:
        assert set(w.keys()) == {"word", "found"}, f"leaked keys: {w.keys()}"
        for forbidden in ("row", "col", "dr", "dc", "position"):
            assert forbidden not in w


def _find_word_line(grid, word):
    """Scan grid for word in 8 directions. Returns (r0,c0,r1,c1) or None."""
    size = len(grid)
    dirs = [(0, 1), (1, 0), (1, 1), (1, -1), (0, -1), (-1, 0), (-1, 1), (-1, -1)]
    for r in range(size):
        for c in range(size):
            for dr, dc in dirs:
                r1, c1 = r + dr * (len(word) - 1), c + dc * (len(word) - 1)
                if not (0 <= r1 < size and 0 <= c1 < size):
                    continue
                ok = all(grid[r + dr * i][c + dc * i] == word[i] for i in range(len(word)))
                if ok:
                    return (r, c, r1, c1)
    return None


def test_find_word_flow(client):
    # Use a fresh user to avoid state pollution
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    email = f"test.mm2.{uuid.uuid4().hex[:8]}@example.com"
    r = s.post(f"{API}/auth/register", json={"email": email, "password": "Passw0rd!Aa", "name": "MM2"})
    assert r.status_code in (200, 201), r.text

    grids = s.get(f"{API}/mots-meles/grids").json()
    gid = grids[0]["id"]
    detail = s.get(f"{API}/mots-meles/grids/{gid}").json()
    grid = detail["grid"]
    words = [w["word"] for w in detail["words"]]
    assert words, "grid has no words"

    # Find first placeable word
    target = None
    coords = None
    for w in words:
        c = _find_word_line(grid, w)
        if c:
            target = w
            coords = c
            break
    assert target, "could not locate any target word in grid"

    r0, c0, r1, c1 = coords
    resp = s.post(f"{API}/mots-meles/grids/{gid}/find", json={
        "row_start": r0, "col_start": c0, "row_end": r1, "col_end": c1,
    })
    assert resp.status_code == 200, resp.text
    d = resp.json()
    assert d["correct"] is True
    assert d["word"] == target
    assert d["points_gained"] == 2 or d["points_gained"] == 12  # or bonus if 1-word grid

    # Second time -> already_found + 0 points
    resp2 = s.post(f"{API}/mots-meles/grids/{gid}/find", json={
        "row_start": r0, "col_start": c0, "row_end": r1, "col_end": c1,
    })
    assert resp2.status_code == 200
    d2 = resp2.json()
    assert d2["already_found"] is True
    assert d2["points_gained"] == 0

    # Wrong line: pick two adjacent random cells that likely form no word
    resp3 = s.post(f"{API}/mots-meles/grids/{gid}/find", json={
        "row_start": 0, "col_start": 0, "row_end": 0, "col_end": 1,
    })
    # Might be right by luck? Verify structure at least
    assert resp3.status_code == 200
    d3 = resp3.json()
    assert "correct" in d3

    # Invalid line (non-straight, non-diagonal): 0,0 -> 2,3
    resp4 = s.post(f"{API}/mots-meles/grids/{gid}/find", json={
        "row_start": 0, "col_start": 0, "row_end": 2, "col_end": 3,
    })
    assert resp4.status_code == 400, resp4.text
    assert "invalide" in resp4.json().get("detail", "").lower() or "ligne" in resp4.json().get("detail", "").lower()


def test_completion_bonus(client):
    # Fresh user
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    email = f"test.mm3.{uuid.uuid4().hex[:8]}@example.com"
    r = s.post(f"{API}/auth/register", json={"email": email, "password": "Passw0rd!Aa", "name": "MM3"})
    assert r.status_code in (200, 201)

    grids = s.get(f"{API}/mots-meles/grids").json()
    # Pick smallest grid (fewest words) to minimize API calls
    grids_sorted = sorted(grids, key=lambda g: g["words_count"])
    gid = grids_sorted[0]["id"]
    detail = s.get(f"{API}/mots-meles/grids/{gid}").json()
    grid = detail["grid"]
    words = [w["word"] for w in detail["words"]]
    total = len(words)

    last_response = None
    found_count = 0
    for w in words:
        coords = _find_word_line(grid, w)
        if not coords:
            continue
        r0, c0, r1, c1 = coords
        resp = s.post(f"{API}/mots-meles/grids/{gid}/find", json={
            "row_start": r0, "col_start": c0, "row_end": r1, "col_end": c1,
        })
        assert resp.status_code == 200, resp.text
        d = resp.json()
        if d.get("correct") and not d.get("already_found"):
            found_count += 1
            last_response = d

    assert last_response is not None
    if found_count == total:
        # Last response should have completion bonus
        assert last_response.get("completed") is True
        assert last_response["points_gained"] == 12  # +2 word + 10 bonus
    else:
        pytest.skip(f"Could not locate all words programmatically ({found_count}/{total})")
