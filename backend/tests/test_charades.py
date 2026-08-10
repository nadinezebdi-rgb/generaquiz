"""Backend tests for the Charades game (Sprint 'Jeux de Mots — Étape 0 + 1')."""
import os
import time
import uuid
import requests
import pytest

def _load_backend_url():
    v = os.environ.get("REACT_APP_BACKEND_URL")
    if v:
        return v.rstrip("/")
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    return line.split("=", 1)[1].strip().rstrip("/")
    except Exception:
        pass
    raise RuntimeError("REACT_APP_BACKEND_URL not set")

BASE_URL = _load_backend_url()
API = f"{BASE_URL}/api"

# Known correct answers (per review request), used only in tests
ANSWERS = {
    "ch01": "chateau", "ch02": "bonjour", "ch03": "poulet", "ch04": "vinaigre",
    "ch05": "souris",  "ch06": "lapin",   "ch07": "chaton",  "ch08": "marmite",
    "ch09": "chapeau", "ch10": "bonbon",  "ch11": "sapin",   "ch12": "orange",
    "ch13": "carotte",
}

ADMIN_EMAIL = "admin@generaquiz.fr"
ADMIN_PWD = "Admin2026!"


def _login(email, pwd):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": email, "password": pwd}, timeout=15)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return s


def _register_fresh():
    s = requests.Session()
    email = f"test.charades.{uuid.uuid4().hex[:10]}@example.com"
    pwd = "Testpass123!"
    r = s.post(f"{API}/auth/register",
               json={"email": email, "password": pwd, "name": "Charades Tester"},
               timeout=15)
    assert r.status_code in (200, 201), f"register failed: {r.status_code} {r.text}"
    return s, email


@pytest.fixture(scope="module")
def admin_session():
    return _login(ADMIN_EMAIL, ADMIN_PWD)


# ---------- Auth / List ---------- #
def test_list_requires_auth():
    r = requests.get(f"{API}/charades/list", timeout=15)
    assert r.status_code in (401, 403)


def test_list_shape_no_answer_leak(admin_session):
    r = admin_session.get(f"{API}/charades/list", timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert set(data.keys()) >= {"charades", "solved_ids", "points_per_correct"}
    assert data["points_per_correct"] == 5
    assert len(data["charades"]) == 13
    for c in data["charades"]:
        assert set(c.keys()) == {"id", "parts", "hint"}, f"unexpected keys: {c.keys()}"
        assert "answer" not in c and "answer_display" not in c
        assert isinstance(c["parts"], list) and len(c["parts"]) == 3


# ---------- Attempts on fresh user ---------- #
def test_fresh_user_correct_attempt_awards_5_xp():
    s, _ = _register_fresh()
    # xp_total before
    me0 = s.get(f"{API}/auth/me", timeout=15).json()
    xp0 = int(me0.get("xp_total") or 0)

    r = s.post(f"{API}/charades/attempt",
               json={"charade_id": "ch01", "answer": "château"},
               timeout=15)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["correct"] is True
    assert d["already_solved"] is False
    assert d["expected"] == "Château"
    assert d["points_gained"] == 5
    assert d["awarded_badges"] == []

    me1 = s.get(f"{API}/auth/me", timeout=15).json()
    assert int(me1.get("xp_total") or 0) == xp0 + 5


def test_wrong_answer_no_points():
    s, _ = _register_fresh()
    r = s.post(f"{API}/charades/attempt",
               json={"charade_id": "ch01", "answer": "maison"},
               timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert d["correct"] is False
    assert d["points_gained"] == 0
    assert d["expected"] == "Château"  # beautiful spelling revealed


@pytest.mark.parametrize("variant", ["CHATEAU", "château", "CHÂTEAU", "  chateau  ", "Chat-eau!"])
def test_normalized_variants_accepted(variant):
    s, _ = _register_fresh()
    r = s.post(f"{API}/charades/attempt",
               json={"charade_id": "ch01", "answer": variant},
               timeout=15)
    assert r.status_code == 200, r.text
    assert r.json()["correct"] is True, f"variant '{variant}' rejected"


def test_idempotent_no_double_scoring():
    s, _ = _register_fresh()
    r1 = s.post(f"{API}/charades/attempt",
                json={"charade_id": "ch02", "answer": "bonjour"}, timeout=15).json()
    assert r1["correct"] and r1["points_gained"] == 5 and r1["already_solved"] is False

    xp_mid = int(s.get(f"{API}/auth/me").json().get("xp_total") or 0)

    r2 = s.post(f"{API}/charades/attempt",
                json={"charade_id": "ch02", "answer": "bonjour"}, timeout=15).json()
    assert r2["correct"] is True
    assert r2["already_solved"] is True
    assert r2["points_gained"] == 0

    xp_end = int(s.get(f"{API}/auth/me").json().get("xp_total") or 0)
    assert xp_end == xp_mid, "xp changed on second solve"


def test_unknown_charade_id_404():
    s, _ = _register_fresh()
    r = s.post(f"{API}/charades/attempt",
               json={"charade_id": "ch99", "answer": "whatever"}, timeout=15)
    assert r.status_code == 404


# ---------- Badge at 10 solved ---------- #
def test_badge_amateur_mots_awarded_once_at_10():
    s, _ = _register_fresh()
    ordered = [f"ch{str(i).zfill(2)}" for i in range(1, 12)]  # 11 solves
    badges_seen = []
    for i, cid in enumerate(ordered, start=1):
        r = s.post(f"{API}/charades/attempt",
                   json={"charade_id": cid, "answer": ANSWERS[cid]}, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["correct"] is True, f"charade {cid} not accepted"
        if i == 10:
            ids = [b["id"] for b in d["awarded_badges"]]
            assert "amateur_mots" in ids, f"badge missing at 10th solve: {d}"
            b = next(b for b in d["awarded_badges"] if b["id"] == "amateur_mots")
            assert b["title"] == "Amateur de mots"
        else:
            assert d["awarded_badges"] == [], f"unexpected badge at solve #{i}: {d}"
        badges_seen.append(d["awarded_badges"])

    # 11th solve should NOT re-award
    assert badges_seen[10] == []


# ---------- Progress ---------- #
def test_progress_endpoint():
    s, _ = _register_fresh()
    # 1 wrong + 1 correct
    s.post(f"{API}/charades/attempt", json={"charade_id": "ch01", "answer": "nope"}, timeout=15)
    s.post(f"{API}/charades/attempt", json={"charade_id": "ch01", "answer": "chateau"}, timeout=15)
    r = s.get(f"{API}/charades/progress", timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert d["total_charades"] == 13
    assert d["solved_count"] == 1
    assert "ch01" in d["solved_ids"]
    assert d["attempts_total"] == 2
    assert d["attempts_correct"] == 1
    assert d["accuracy_pct"] == 50.0
