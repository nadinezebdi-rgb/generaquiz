# Iteration 58 — quiz sessions anti-cheat, free daily limit by answered questions,
# client_ip / XFF spoofing, atomic reset-password token, regressions (pricing, contact).
import os
import uuid
import secrets
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor

import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"
ADMIN_EMAIL = os.environ["TEST_ADMIN_EMAIL"]
ADMIN_PASSWORD = os.environ["TEST_ADMIN_PASSWORD"]
TEST_PW = "Tst_" + uuid.uuid4().hex[:10]

_mongo = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
CREATED = []  # sessions for cleanup


def clear_rl():
    _mongo.rate_limits.delete_many({})


def register(prefix="free"):
    clear_rl()
    s = requests.Session()
    email = f"test_{prefix}_{uuid.uuid4().hex[:8]}@example.com"
    r = s.post(f"{API}/auth/register", json={"email": email, "password": TEST_PW, "name": f"TEST_{prefix}"})
    assert r.status_code == 200, r.text
    CREATED.append(s)
    return s, email


@pytest.fixture(scope="module")
def admin():
    clear_rl()
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    if r.status_code != 200:
        pytest.skip(f"admin login failed {r.status_code}")
    return s


@pytest.fixture(scope="module")
def category_id(admin):
    cats = [c for c in admin.get(f"{API}/categories").json() if c.get("count", 0) >= 10]
    assert cats
    return cats[0]["id"]


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    for s in CREATED:
        try:
            s.delete(f"{API}/auth/account")
        except Exception:
            pass
    clear_rl()


def correct_of(qid, shown_options=None):
    """Index de la bonne réponse dans l'ordre affiché (les options sont mélangées par partie côté serveur)."""
    doc = _mongo.questions.find_one({"id": qid})
    if shown_options is None:
        return doc["correct_index"]
    return shown_options.index(doc["options"][doc["correct_index"]])


# ---- Anti-cheat session flow ----
class TestQuizSession:
    def test_get_returns_session(self, admin, category_id):
        d = admin.get(f"{API}/categories/{category_id}/questions").json()
        assert isinstance(d.get("session_id"), str) and d["questions"]
        assert all("correct_index" not in q for q in d["questions"])

    def test_answer_requires_session(self, admin, category_id):
        d = admin.get(f"{API}/categories/{category_id}/questions").json()
        r = admin.post(f"{API}/categories/{category_id}/answer", json={"question_id": d["questions"][0]["id"], "choice": 0})
        assert r.status_code == 422
        r = admin.post(f"{API}/categories/{category_id}/answer",
                       json={"session_id": str(uuid.uuid4()), "question_id": d["questions"][0]["id"], "choice": 0})
        assert r.status_code == 400

    def test_first_choice_only_and_score_from_stored(self, admin, category_id):
        d = admin.get(f"{API}/categories/{category_id}/questions").json()
        sid, q = d["session_id"], d["questions"][0]
        ci = correct_of(q["id"], q["options"])
        wrong = (ci + 1) % len(q["options"])
        r1 = admin.post(f"{API}/categories/{category_id}/answer", json={"session_id": sid, "question_id": q["id"], "choice": wrong})
        assert r1.status_code == 200 and r1.json()["correct"] is False
        r2 = admin.post(f"{API}/categories/{category_id}/answer", json={"session_id": sid, "question_id": q["id"], "choice": ci})
        assert r2.status_code == 200 and r2.json()["correct"] is False  # first choice kept
        # client claims correct index -> ignored
        s = admin.post(f"{API}/attempts", json={"category_id": category_id, "session_id": sid,
                                                "answers": [{"question_id": q["id"], "answer_index": ci}]})
        assert s.status_code == 200, s.text
        assert s.json()["score"] == 0 and s.json()["total"] == 1
        # second save -> 409
        s2 = admin.post(f"{API}/attempts", json={"category_id": category_id, "session_id": sid,
                                                 "answers": [{"question_id": q["id"], "answer_index": ci}]})
        assert s2.status_code == 409 and "déjà enregistré" in s2.json()["detail"]
        # answer on consumed session -> 409
        r3 = admin.post(f"{API}/categories/{category_id}/answer", json={"session_id": sid, "question_id": q["id"], "choice": ci})
        assert r3.status_code == 409

    def test_attempt_without_or_unknown_session_400(self, admin, category_id):
        d = admin.get(f"{API}/categories/{category_id}/questions").json()
        qid = d["questions"][0]["id"]
        r = admin.post(f"{API}/attempts", json={"category_id": category_id, "answers": [{"question_id": qid, "answer_index": 0}]})
        assert r.status_code == 400
        r = admin.post(f"{API}/attempts", json={"category_id": category_id, "session_id": "nope",
                                                "answers": [{"question_id": qid, "answer_index": 0}]})
        assert r.status_code == 400

    def test_attempt_unanswered_question_400(self, admin, category_id):
        d = admin.get(f"{API}/categories/{category_id}/questions").json()
        r = admin.post(f"{API}/attempts", json={"category_id": category_id, "session_id": d["session_id"],
                                                "answers": [{"question_id": d["questions"][0]["id"], "answer_index": 0}]})
        assert r.status_code == 400

    def test_expired_session_400(self, admin, category_id):
        d = admin.get(f"{API}/categories/{category_id}/questions").json()
        sid, q = d["session_id"], d["questions"][0]
        admin.post(f"{API}/categories/{category_id}/answer", json={"session_id": sid, "question_id": q["id"], "choice": 0})
        _mongo.quiz_sessions.update_one({"id": sid}, {"$set": {"created_at": (datetime.now(timezone.utc) - timedelta(hours=7)).isoformat()}})
        r = admin.post(f"{API}/attempts", json={"category_id": category_id, "session_id": sid,
                                                "answers": [{"question_id": q["id"], "answer_index": 0}]})
        assert r.status_code == 400 and "expirée" in r.json()["detail"]

    def test_other_user_session_rejected(self, admin, category_id):
        d = admin.get(f"{API}/categories/{category_id}/questions").json()
        s, _ = register("other")
        r = s.post(f"{API}/categories/{category_id}/answer",
                   json={"session_id": d["session_id"], "question_id": d["questions"][0]["id"], "choice": 0})
        assert r.status_code == 400

    def test_concurrent_double_save_only_one(self, admin, category_id):
        d = admin.get(f"{API}/categories/{category_id}/questions").json()
        sid, q = d["session_id"], d["questions"][0]
        admin.post(f"{API}/categories/{category_id}/answer", json={"session_id": sid, "question_id": q["id"], "choice": 0})
        body = {"category_id": category_id, "session_id": sid, "answers": [{"question_id": q["id"], "answer_index": 0}]}
        with ThreadPoolExecutor(4) as ex:
            codes = sorted(ex.map(lambda _: admin.post(f"{API}/attempts", json=body).status_code, range(4)))
        assert codes.count(200) == 1 and codes.count(409) == 3, codes


# ---- Free daily limit counts answered questions ----
class TestFreeLimit:
    def test_refetch_does_not_consume(self, category_id):
        s, _ = register("free")
        for _ in range(3):  # StrictMode double fetch / refresh
            d = s.get(f"{API}/categories/{category_id}/questions").json()
            assert not d.get("daily_limit_reached") and len(d["questions"]) == 5
        sid = d["session_id"]
        for q in d["questions"]:
            r = s.post(f"{API}/categories/{category_id}/answer", json={"session_id": sid, "question_id": q["id"], "choice": 0})
            assert r.status_code == 200
        sv = s.post(f"{API}/attempts", json={"category_id": category_id, "session_id": sid,
                                             "answers": [{"question_id": q["id"], "answer_index": 0} for q in d["questions"]]})
        assert sv.status_code == 200
        d2 = s.get(f"{API}/categories/{category_id}/questions").json()
        assert d2.get("daily_limit_reached") is True and d2["questions"] == []

    def test_answer_new_question_after_limit_403(self, category_id):
        s, _ = register("free2")
        a = s.get(f"{API}/categories/{category_id}/questions").json()
        b = s.get(f"{API}/categories/{category_id}/questions").json()  # second open session
        for q in a["questions"]:
            assert s.post(f"{API}/categories/{category_id}/answer", json={"session_id": a["session_id"], "question_id": q["id"], "choice": 0}).status_code == 200
        r = s.post(f"{API}/categories/{category_id}/answer", json={"session_id": b["session_id"], "question_id": b["questions"][0]["id"], "choice": 0})
        assert r.status_code == 403
        # re-answer an already answered question still OK
        r = s.post(f"{API}/categories/{category_id}/answer", json={"session_id": a["session_id"], "question_id": a["questions"][0]["id"], "choice": 1})
        assert r.status_code == 200

    def test_partial_answers_reduce_next_limit(self, category_id):
        s, _ = register("free3")
        a = s.get(f"{API}/categories/{category_id}/questions").json()
        for q in a["questions"][:2]:
            s.post(f"{API}/categories/{category_id}/answer", json={"session_id": a["session_id"], "question_id": q["id"], "choice": 0})
        b = s.get(f"{API}/categories/{category_id}/questions").json()
        assert len(b["questions"]) == 3


# ---- client_ip ----
class TestClientIp:
    def test_spoofed_xff_ignored(self):
        clear_rl()
        egress = requests.get("https://ifconfig.me/ip", timeout=10).text.strip()
        requests.post(f"{API}/auth/login", headers={"X-Forwarded-For": "9.9.9.9, 8.8.8.8"},
                      json={"email": f"test_xff_{uuid.uuid4().hex[:6]}@example.com", "password": "wrongpass1"})
        keys = [d["key"] for d in _mongo.rate_limits.find({"key": {"$regex": "^login:"}})]
        assert f"login:{egress}" in keys, keys
        assert not any("9.9.9.9" in k or "8.8.8.8" in k for k in keys)
        clear_rl()


# ---- reset-password atomic ----
class TestResetToken:
    def test_reset_token_concurrent_single_use(self):
        s, email = register("reset")
        user = _mongo.users.find_one({"email": email})
        token = secrets.token_urlsafe(32)
        _mongo.password_reset_tokens.insert_one({"token": token, "user_id": str(user["_id"]), "email": email,
                                                 "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
                                                 "used": False, "created_at": datetime.now(timezone.utc), "test": True})
        with ThreadPoolExecutor(5) as ex:
            codes = list(ex.map(lambda i: requests.post(f"{API}/auth/reset-password",
                                                        json={"token": token, "new_password": TEST_PW + str(i)}).status_code, range(5)))
        assert codes.count(200) == 1 and codes.count(400) == 4, codes
        _mongo.password_reset_tokens.delete_one({"token": token})
        # re-login session for cleanup
        clear_rl()
        for i in range(5):
            if s.post(f"{API}/auth/login", json={"email": email, "password": TEST_PW + str(i)}).status_code == 200:
                break


# ---- regressions ----
class TestRegression:
    def test_pricing_and_contact(self, admin):
        r = admin.get(f"{API}/packages")
        assert r.status_code == 200
        clear_rl()
        c = requests.post(f"{API}/contact", json={"name": "TEST_contact", "email": "test_contact@example.com",
                                                   "subject": "TEST", "message": "TEST message iteration 58, merci."})
        assert c.status_code in (200, 201, 422), c.text
        print("contact", c.status_code, c.text[:200])
