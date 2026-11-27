# LOT 3: family weekly report + inactivity alert + share toggle; regression curated categories
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import requests
from bson import ObjectId
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
ADMIN = {"email": os.environ["TEST_ADMIN_EMAIL"], "password": os.environ["TEST_ADMIN_PASSWORD"]}

CREATED_USERS, CREATED_ACTIVITY = [], []


def _iso(days_ago=0):
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()


def register(prefix):
    s = requests.Session()
    email = f"test_{prefix}_{uuid.uuid4().hex[:8]}@example.com"
    r = s.post(f"{API}/auth/register", json={"email": email, "password": "Passw0rd!", "name": f"TEST_{prefix}"})
    assert r.status_code == 200, r.text
    uid = r.json()["user"]["id"]
    CREATED_USERS.append(uid)
    s.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    return s, uid, email


def make_owner(prefix):
    s, uid, email = register(prefix)
    db.users.update_one({"_id": ObjectId(uid)}, {"$set": {"plan": "premium", "plan_tier": "famille_v2",
                                                          "plan_expires_at": _iso(-30), "family_max_proches": 3}})
    return s, uid, email


def add_proche(owner_s, accept=True):
    ps, pid, pemail = register("proche")
    r = owner_s.post(f"{API}/famille/proches", json={"name": "TEST_Proche", "email": pemail})
    assert r.status_code == 200, r.text
    token = db.family_proches.find_one({"id": r.json()["id"]})["token"]
    if accept:
        a = ps.post(f"{API}/famille/invitation/{token}/accept")
        assert a.status_code == 200, a.text
    return ps, pid


def add_activity(coll, uid, days_ago, cat="cinema"):
    res = db[coll].insert_one({"user_id": uid, "category_id": cat, "created_at": _iso(days_ago), "TEST": True})
    CREATED_ACTIVITY.append((coll, res.inserted_id))


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    for coll, _id in CREATED_ACTIVITY:
        db[coll].delete_one({"_id": _id})
    for uid in CREATED_USERS:
        db.family_proches.delete_many({"owner_id": uid})
        db.credit_ledger.delete_many({"user_id": uid})
        db.users.delete_one({"_id": ObjectId(uid)})


@pytest.fixture(scope="module")
def admin():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json=ADMIN)
    if r.status_code != 200:
        pytest.skip("admin login failed")
    s.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    return s


@pytest.fixture(scope="module")
def fam():
    """Builds the scenario owners."""
    d = {}
    # A: opted in, accepted proche, no activity, share_since 5 days ago -> alert
    a_s, a_id, _ = make_owner("ownerA")
    d["a_proche_s"], d["a_proche_id"] = add_proche(a_s)
    d["a_s"], d["a_id"] = a_s, a_id
    # B: opted in, accepted proche, active today -> no alert
    b_s, b_id, _ = make_owner("ownerB")
    add_proche(b_s)
    d["b_s"], d["b_id"] = b_s, b_id
    # C: opted in, only invited proche -> not counted
    c_s, c_id, _ = make_owner("ownerC")
    add_proche(c_s, accept=False)
    d["c_s"], d["c_id"] = c_s, c_id
    # D: sharing off, accepted proche -> not counted
    dd_s, dd_id, _ = make_owner("ownerD")
    add_proche(dd_s)
    d["d_s"], d["d_id"] = dd_s, dd_id
    # E: opted in, accepted proche, last activity 4 days ago (palier_attempts) -> alert
    e_s, e_id, _ = make_owner("ownerE")
    add_proche(e_s)
    d["e_s"], d["e_id"] = e_s, e_id
    return d


class TestShareToggle:
    def test_owner_enable(self, fam):
        for k in ("a_s", "b_s", "c_s", "e_s"):
            r = fam[k].put(f"{API}/famille/partage", json={"enabled": True})
            assert r.status_code == 200 and r.json() == {"share_progress": True}
        u = db.users.find_one({"_id": ObjectId(fam["a_id"])})
        assert u["family_share_progress"] is True and u.get("family_share_since")

    def test_get_famille_share_progress(self, fam):
        r = fam["a_s"].get(f"{API}/famille")
        assert r.json()["role"] == "owner" and r.json()["share_progress"] is True
        r = fam["a_proche_s"].get(f"{API}/famille")
        assert r.json()["role"] == "proche" and r.json()["share_progress"] is True
        r = fam["d_s"].get(f"{API}/famille")
        assert r.json()["share_progress"] is False

    def test_proche_forbidden(self, fam):
        r = fam["a_proche_s"].put(f"{API}/famille/partage", json={"enabled": True})
        assert r.status_code == 403

    def test_non_owner_forbidden(self):
        s, _, _ = register("free")
        assert s.put(f"{API}/famille/partage", json={"enabled": True}).status_code == 403

    def test_invalid_body(self, fam):
        assert fam["a_s"].put(f"{API}/famille/partage", json={}).status_code == 422

    def test_disable_then_reenable_keeps_since(self, fam):
        r = fam["d_s"].put(f"{API}/famille/partage", json={"enabled": False})
        assert r.status_code == 200 and r.json()["share_progress"] is False
        assert db.users.find_one({"_id": ObjectId(fam["d_id"])})["family_share_progress"] is False


class TestReports:
    def test_admin_only(self, fam):
        for kind in ("hebdo", "inactivite"):
            assert fam["a_s"].post(f"{API}/famille/admin/rapports/{kind}").status_code == 403
        assert requests.post(f"{API}/famille/admin/rapports/hebdo").status_code in (401, 403)

    def test_unknown_kind(self, admin):
        assert admin.post(f"{API}/famille/admin/rapports/foo").status_code == 404

    def test_setup_activity(self, fam):
        db.users.update_one({"_id": ObjectId(fam["a_id"])}, {"$set": {"family_share_since": _iso(5)}})
        db.users.update_one({"_id": ObjectId(fam["e_id"])}, {"$set": {"family_share_since": _iso(10)}})
        add_activity("attempts", fam["b_id"], 0, "cinema")
        add_activity("daily_attempts", fam["b_id"], 1, None)
        add_activity("palier_attempts", fam["b_id"], 2, "annees-80")
        add_activity("palier_attempts", fam["e_id"], 4, "cinema")

    def test_weekly(self, admin, fam):
        r = admin.post(f"{API}/famille/admin/rapports/hebdo")
        assert r.status_code == 200, r.text
        data = r.json()
        # A, B, E counted; C (invited only) & D (off) excluded
        sharing_with_accepted = 0
        for u in db.users.find({"family_share_progress": True}):
            if db.family_proches.count_documents({"owner_id": str(u["_id"]), "status": "accepted"}):
                sharing_with_accepted += 1
        assert data["owners"] == sharing_with_accepted
        assert data["owners"] >= 3

    def test_inactivity_first_call(self, admin, fam):
        r = admin.post(f"{API}/famille/admin/rapports/inactivite")
        assert r.status_code == 200, r.text
        assert r.json()["alerted"] >= 2
        a = db.users.find_one({"_id": ObjectId(fam["a_id"])})
        e = db.users.find_one({"_id": ObjectId(fam["e_id"])})
        b = db.users.find_one({"_id": ObjectId(fam["b_id"])})
        c = db.users.find_one({"_id": ObjectId(fam["c_id"])})
        assert a.get("family_inactivity_alert_for") == a["family_share_since"]
        assert e.get("family_inactivity_alert_for")
        assert not b.get("family_inactivity_alert_for")
        assert not c.get("family_inactivity_alert_for")
        fam["e_marker"] = e["family_inactivity_alert_for"]

    def test_inactivity_second_call_no_realert(self, admin, fam):
        r = admin.post(f"{API}/famille/admin/rapports/inactivite")
        assert r.status_code == 200
        assert r.json()["alerted"] == 0
        assert db.users.find_one({"_id": ObjectId(fam["e_id"])})["family_inactivity_alert_for"] == fam["e_marker"]


class TestCurated:
    @pytest.mark.parametrize("cid", ["bien-vieillir", "annees-80", "annees-2010"])
    def test_palier_start(self, cid):
        s, _, _ = register("palier")
        r = s.post(f"{API}/palier/categories/{cid}/1/start")
        assert r.status_code == 200, r.text
        assert len(r.json()["questions"]) == 20

    def test_categories_counts(self):
        cats = requests.get(f"{API}/categories").json()
        cats = cats if isinstance(cats, list) else cats.get("categories", [])
        by = {c["id"]: c for c in cats}
        for cid in ("bien-vieillir", "annees-80", "annees-2010"):
            assert cid in by, cid
            print(cid, {k: v for k, v in by[cid].items() if "count" in k or "question" in k})
