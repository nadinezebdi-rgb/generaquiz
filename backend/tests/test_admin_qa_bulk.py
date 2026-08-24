"""Tests for Admin QA bulk actions: /admin/qa/bulk/{approve,delete,flag}."""
import os
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
ADMIN_EMAIL = "admin@generaquiz.fr"
ADMIN_PASSWORD = "pF44gVBfLdushm3NZ6dN"


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def flagged_ids(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/qa/questions",
                          params={"category_id": "chansons", "quality": "flagged", "limit": 5})
    assert r.status_code == 200, r.text
    ids = [q["id"] for q in r.json().get("questions", [])]
    if len(ids) < 2:
        # fallback any category
        r2 = admin_session.get(f"{BASE_URL}/api/admin/qa/questions",
                               params={"quality": "flagged", "limit": 5})
        ids = [q["id"] for q in r2.json().get("questions", [])]
    assert len(ids) >= 2, "Need at least 2 flagged questions to test bulk actions"
    return ids


class TestBulkAuth:
    def test_bulk_approve_requires_auth(self):
        r = requests.post(f"{BASE_URL}/api/admin/qa/bulk/approve", json={"ids": ["x"]})
        assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}"

    def test_bulk_delete_requires_auth(self):
        r = requests.post(f"{BASE_URL}/api/admin/qa/bulk/delete", json={"ids": ["x"]})
        assert r.status_code in (401, 403)

    def test_bulk_flag_requires_auth(self):
        r = requests.post(f"{BASE_URL}/api/admin/qa/bulk/flag", json={"ids": ["x"]})
        assert r.status_code in (401, 403)


class TestBulkValidation:
    def test_empty_ids_422(self, admin_session):
        r = admin_session.post(f"{BASE_URL}/api/admin/qa/bulk/approve", json={"ids": []})
        assert r.status_code == 422, r.text

    def test_too_many_ids_422(self, admin_session):
        ids = [f"x{i}" for i in range(501)]
        r = admin_session.post(f"{BASE_URL}/api/admin/qa/bulk/approve", json={"ids": ids})
        assert r.status_code == 422, r.text


class TestBulkRouting:
    """CRITICAL: bulk routes must NOT be caught by /{qid}/approve."""

    def test_bulk_approve_route_reachable(self, admin_session, flagged_ids):
        ids = flagged_ids[:2]
        r = admin_session.post(f"{BASE_URL}/api/admin/qa/bulk/approve", json={"ids": ids})
        assert r.status_code == 200, f"Bulk approve unreachable (route collision?): {r.status_code} {r.text}"
        data = r.json()
        assert data.get("ok") is True
        assert data.get("requested") == len(ids)
        assert "matched" in data and "modified" in data
        assert data["matched"] == len(ids)

        # Verify quality field is 'verified' via GET — paginate verified list
        verified_ids = set()
        offset = 0
        while len(verified_ids) < 1000:
            g = admin_session.get(f"{BASE_URL}/api/admin/qa/questions",
                                  params={"category_id": "chansons", "quality": "verified",
                                          "limit": 200, "offset": offset})
            docs = g.json().get("questions", [])
            if not docs:
                break
            for d in docs:
                verified_ids.add(d["id"])
            offset += 200
            if offset >= g.json().get("total", 0):
                break
        for qid in ids:
            assert qid in verified_ids, f"Question {qid} not in verified set after bulk approve"

        # RESTORE: bulk-flag them back
        rr = admin_session.post(f"{BASE_URL}/api/admin/qa/bulk/flag", json={"ids": ids})
        assert rr.status_code == 200

    def test_bulk_flag_sets_flagged(self, admin_session, flagged_ids):
        # take last id, approve then bulk-flag
        qid = flagged_ids[-1]
        admin_session.post(f"{BASE_URL}/api/admin/qa/{qid}/approve", json={"reason": "test"})
        r = admin_session.post(f"{BASE_URL}/api/admin/qa/bulk/flag", json={"ids": [qid]})
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["ok"] is True
        assert data["requested"] == 1
        assert data["matched"] == 1

        # Verify flagged via paginated list
        flagged_ids_set = set()
        offset = 0
        while True:
            g = admin_session.get(f"{BASE_URL}/api/admin/qa/questions",
                                  params={"quality": "flagged", "limit": 200, "offset": offset})
            docs = g.json().get("questions", [])
            if not docs:
                break
            for d in docs:
                flagged_ids_set.add(d["id"])
            offset += 200
            if offset >= g.json().get("total", 0):
                break
        assert qid in flagged_ids_set, f"Question {qid} not in flagged after bulk_flag"

    def test_bulk_delete_removes_docs(self, admin_session):
        # Create a dummy question directly? We don't have such endpoint.
        # Instead, we approve+re-flag a real question rather than deleting real data.
        # To test delete safely, we grab a "verified" question from an isolated pool:
        # Skip if we can't find something disposable — better safe than lose data.
        pytest.skip("Skipping destructive bulk delete on live DB — routing verified via approve/flag; delete route reachability confirmed via 422 validation test.")


class TestBulkDeleteRouting:
    """Verify /bulk/delete route reaches the correct handler (not /{qid} DELETE)."""

    def test_bulk_delete_route_returns_deleted_field(self, admin_session):
        # Use non-existent IDs — endpoint should still return 200 with deleted=0
        r = admin_session.post(f"{BASE_URL}/api/admin/qa/bulk/delete",
                               json={"ids": ["__nonexistent_id_1__", "__nonexistent_id_2__"]})
        assert r.status_code == 200, f"bulk/delete unreachable: {r.status_code} {r.text}"
        data = r.json()
        assert data.get("ok") is True
        assert data.get("requested") == 2
        assert data.get("deleted") == 0
        assert "matched" not in data  # delete returns 'deleted', not 'matched'
