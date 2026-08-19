"""Backend tests for Admin QA Regen Batch + Search feature (iteration 42)."""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
ADMIN_EMAIL = "admin@generaquiz.fr"
ADMIN_PASS = "pF44gVBfLdushm3NZ6dN"


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS})
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def user_session():
    s = requests.Session()
    email = f"testuser_qa_{int(time.time())}@example.com"
    r = s.post(f"{BASE_URL}/api/auth/register", json={
        "email": email, "password": "TestPass123!", "name": "QA Tester"
    })
    if r.status_code not in (200, 201):
        pytest.skip(f"cannot register test user: {r.status_code} {r.text}")
    return s


# ---------- Search on /admin/qa/questions ----------
class TestQASearch:
    def test_search_piaf_in_chansons(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/qa/questions", params={
            "category_id": "chansons", "quality": "all", "q": "Piaf", "limit": 50
        })
        assert r.status_code == 200
        data = r.json()
        assert "total" in data and "questions" in data
        # Every returned question should have 'piaf' somewhere (case-insensitive)
        for q in data["questions"]:
            fc = q.get("fact_check") or {}
            parts = [q.get("question") or "", " ".join(q.get("options") or []),
                     fc.get("comment") or "", fc.get("correction") or ""]
            haystack = " ".join(parts).lower()
            assert "piaf" in haystack, f"Question {q.get('id')} does not contain 'piaf'"

    def test_search_case_insensitive(self, admin_session):
        r1 = admin_session.get(f"{BASE_URL}/api/admin/qa/questions",
                               params={"category_id": "chansons", "quality": "all", "q": "piaf"})
        r2 = admin_session.get(f"{BASE_URL}/api/admin/qa/questions",
                               params={"category_id": "chansons", "quality": "all", "q": "PIAF"})
        assert r1.status_code == 200 and r2.status_code == 200
        assert r1.json()["total"] == r2.json()["total"]

    def test_search_empty_q(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/qa/questions",
                              params={"category_id": "chansons", "quality": "all"})
        assert r.status_code == 200
        assert r.json()["total"] >= 0


# ---------- Rerun endpoint ----------
class TestRerunJob:
    def test_non_admin_forbidden(self, user_session):
        r = user_session.post(f"{BASE_URL}/api/admin/qa/rerun/cinema")
        assert r.status_code == 403

    def test_unknown_category_404(self, admin_session):
        r = admin_session.post(f"{BASE_URL}/api/admin/qa/rerun/does-not-exist-xyz")
        assert r.status_code == 404

    def test_rerun_creates_running_job_and_conflict(self, admin_session):
        # Use a small category. Start job.
        cat = "cinema"
        # If there's already a running job, wait/skip conflict test appropriately
        r = admin_session.post(f"{BASE_URL}/api/admin/qa/rerun/{cat}")
        if r.status_code == 409:
            pytest.skip("A job is already running from a previous test session")
        assert r.status_code == 200, f"expected 200, got {r.status_code} {r.text}"
        body = r.json()
        assert body.get("ok") is True
        job = body["job"]
        assert job["status"] == "running"
        assert job["category_id"] == cat
        assert job.get("started_at")
        assert job.get("started_by") == ADMIN_EMAIL
        job_id = job["id"]

        # Verify job present in list
        rl = admin_session.get(f"{BASE_URL}/api/admin/qa/jobs", params={"limit": 10})
        assert rl.status_code == 200
        jobs = rl.json()
        assert isinstance(jobs, list)
        assert any(j["id"] == job_id for j in jobs)

        # Immediately relaunch → 409
        r2 = admin_session.post(f"{BASE_URL}/api/admin/qa/rerun/{cat}")
        assert r2.status_code == 409
        detail = r2.json().get("detail", "")
        assert "déjà en cours" in detail.lower() or "deja en cours" in detail.lower()


# ---------- Jobs listing ----------
class TestQAJobs:
    def test_jobs_list_sorted_desc(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/qa/jobs", params={"limit": 10})
        assert r.status_code == 200
        jobs = r.json()
        assert isinstance(jobs, list)
        if len(jobs) >= 2:
            # Verify sort desc by started_at
            starts = [j.get("started_at", "") for j in jobs]
            assert starts == sorted(starts, reverse=True)
        # each job has expected keys
        for j in jobs:
            assert "id" in j and "status" in j and "category_id" in j
            assert "_id" not in j  # ObjectId excluded

    def test_jobs_non_admin_forbidden(self, user_session):
        r = user_session.get(f"{BASE_URL}/api/admin/qa/jobs")
        assert r.status_code == 403


# ---------- Regression: existing admin QA actions ----------
class TestQARegression:
    def test_summary(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/qa/summary")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) > 0
        for c in data:
            assert {"category_id", "total", "verified", "flagged"}.issubset(c)

    def test_quality_filter_still_works(self, admin_session):
        for q in ("flagged", "verified", "unchecked", "all"):
            r = admin_session.get(f"{BASE_URL}/api/admin/qa/questions",
                                  params={"category_id": "chansons", "quality": q, "limit": 5})
            assert r.status_code == 200, f"quality={q} failed"
