# Iteration 44: Bien vieillir category + QA rebalance refactor + daily quiz persistence
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
ADMIN = {"email": "admin@generaquiz.fr", "password": "pF44gVBfLdushm3NZ6dN"}


@pytest.fixture(scope="module")
def admin():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json=ADMIN)
    if r.status_code != 200:
        pytest.skip(f"admin login failed {r.status_code}")
    tok = r.json().get("access_token") or r.json().get("token")
    if tok:
        s.headers["Authorization"] = f"Bearer {tok}"
    return s


# --- Categories ---
class TestCategories:
    def test_categories_include_bien_vieillir(self):
        r = requests.get(f"{BASE_URL}/api/categories")
        assert r.status_code == 200
        cats = r.json()
        assert len(cats) == 10
        bv = next(c for c in cats if c["id"] == "bien-vieillir")
        assert bv["title"] == "Bien vieillir"
        assert bv["mascot_name"] == "Lucette la Pétillante"
        assert bv["mascot_image"] == "/api/static/mascots/bien-vieillir.png"
        assert "_id" not in bv

    def test_mascot_served(self):
        r = requests.get(f"{BASE_URL}/api/static/mascots/bien-vieillir.png")
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("image/")
        assert len(r.content) > 1000

    def test_questions_bien_vieillir(self, admin):
        r = admin.get(f"{BASE_URL}/api/categories/bien-vieillir/questions")
        assert r.status_code == 200
        data = r.json()
        qs = data["questions"] if isinstance(data, dict) else data
        assert len(qs) >= 1
        for q in qs:
            assert q["category_id"] == "bien-vieillir"
            assert len(q["options"]) == 4
            assert "_id" not in q


# --- Palier mode with low stock ---
class TestPalier:
    def test_overview(self, admin):
        r = admin.get(f"{BASE_URL}/api/palier/categories/bien-vieillir")
        assert r.status_code == 200
        p = r.json()["paliers"]
        assert len(p) == 7
        assert p[0]["unlocked"] is True
        assert all(x["stock_available"] >= 3 for x in p)

    def test_start_low_stock_no_crash(self, admin):
        r = admin.post(f"{BASE_URL}/api/palier/categories/bien-vieillir/1/start")
        # 3 questions/palier in preview -> 409 'Stock insuffisant' (not 500)
        assert r.status_code in (200, 409), r.text
        if r.status_code == 409:
            assert "Stock insuffisant" in r.json()["detail"]

    def test_start_locked_palier(self, admin):
        r = admin.post(f"{BASE_URL}/api/palier/categories/bien-vieillir/2/start")
        assert r.status_code == 403


# --- Livre memory map ---
class TestLivre:
    def test_memory_trigger(self, admin):
        r = admin.get(f"{BASE_URL}/api/livre/memory-trigger/bien-vieillir")
        assert r.status_code == 200
        d = r.json()
        assert d["has_trigger"] is True
        assert d["chapter_id"] == "transmission"
        assert d["prompt_hint"]


# --- Admin QA ---
class TestAdminQA:
    def test_rebalance_category(self, admin):
        r = admin.post(f"{BASE_URL}/api/admin/qa/rebalance/bien-vieillir")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["ok"] is True
        for k in ("tagged", "still_missing_slots", "distribution_after"):
            assert k in d
        assert d["category_title"] == "Bien vieillir"

    def test_rebalance_unknown(self, admin):
        r = admin.post(f"{BASE_URL}/api/admin/qa/rebalance/nope-xyz")
        assert r.status_code == 404

    def test_rebalance_all(self, admin):
        r = admin.post(f"{BASE_URL}/api/admin/qa/rebalance-all")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["ok"] is True
        assert len(d["categories"]) == 10
        for c in d["categories"]:
            for k in ("tagged", "still_missing_slots", "distribution_after"):
                assert k in c

    def test_rebalance_requires_admin(self):
        r = requests.post(f"{BASE_URL}/api/admin/qa/rebalance-all")
        assert r.status_code in (401, 403)

    def test_queue(self, admin):
        r = admin.get(f"{BASE_URL}/api/admin/qa/queue")
        assert r.status_code == 200, r.text

    def test_jobs(self, admin):
        r = admin.get(f"{BASE_URL}/api/admin/qa/jobs")
        assert r.status_code == 200, r.text

    def test_summary(self, admin):
        r = admin.get(f"{BASE_URL}/api/admin/qa/summary")
        assert r.status_code == 200, r.text


# --- Daily quiz persisted ---
class TestDaily:
    def test_daily_stable(self):
        a = requests.get(f"{BASE_URL}/api/daily/quiz").json()
        b = requests.get(f"{BASE_URL}/api/daily/quiz").json()
        assert a["count"] == 5
        assert [q["id"] for q in a["questions"]] == [q["id"] for q in b["questions"]]
        assert all("_id" not in q for q in a["questions"])

    def test_daily_submit_scoring(self):
        import uuid
        s = requests.Session()
        email = f"test_bv_{uuid.uuid4().hex[:8]}@example.com"
        r = s.post(f"{BASE_URL}/api/auth/register",
                   json={"email": email, "password": "TestPass123!", "name": "TEST_daily"})
        assert r.status_code in (200, 201), r.text
        s.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
        try:
            quiz = s.get(f"{BASE_URL}/api/daily/quiz").json()
            qs = quiz["questions"]
            answers = [{"question_id": q["id"], "answer_index": q["correct_index"]} for q in qs[:3]]
            answers += [{"question_id": q["id"], "answer_index": (q["correct_index"] + 1) % 4} for q in qs[3:]]
            r = s.post(f"{BASE_URL}/api/daily/submit", json={"answers": answers, "duration_seconds": 30})
            assert r.status_code == 200, r.text
            d = r.json()
            assert d["score"] == 3
            assert d["total"] == 5
            r2 = s.post(f"{BASE_URL}/api/daily/submit", json={"answers": answers})
            assert r2.status_code == 409
        finally:
            s.delete(f"{BASE_URL}/api/auth/account")

    def test_daily_submit_foreign_question(self, admin):
        r = admin.post(f"{BASE_URL}/api/daily/submit",
                       json={"answers": [{"question_id": "not-today", "answer_index": 0}]})
        assert r.status_code in (400, 409)
