# Iteration 53 — Palier per-question validation (/answer), server-side scoring, B2 stock, C stats/mastery
import os
import uuid
import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"
CAT = "cinema"


def _load_env():
    env = {}
    with open("/app/backend/.env") as f:
        for line in f:
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.strip().split("=", 1)
                env[k] = v.strip('"')
    return env


ENV = _load_env()
mdb = MongoClient(ENV["MONGO_URL"])[ENV["DB_NAME"]]  # read-only lookups of correct answers


def _new_user():
    s = requests.Session()
    email = f"test_it53_{uuid.uuid4().hex[:8]}@example.com"
    r = s.post(f"{API}/auth/register", json={"email": email, "password": "TestPass123!", "name": "TEST_It53"})
    assert r.status_code in (200, 201), r.text
    s.headers.update({"Authorization": f"Bearer {r.json()['access_token']}"})
    return s


def _correct_pos(q):
    db_q = mdb.questions.find_one({"id": q["id"]}, {"_id": 0, "options": 1, "correct_index": 1})
    return q["options"].index(db_q["options"][db_q["correct_index"]]), db_q


@pytest.fixture(scope="module")
def user():
    s = _new_user()
    yield s
    s.delete(f"{API}/auth/account")


@pytest.fixture(scope="module")
def user2():
    s = _new_user()
    yield s
    s.delete(f"{API}/auth/account")


# --- start: no leaked answer keys, options shuffled
def test_start_no_leak(user):
    r = user.post(f"{API}/palier/categories/{CAT}/1/start")
    assert r.status_code == 200, r.text
    qs = r.json()["questions"]
    assert len(qs) == 20
    for q in qs:
        for k in ("correct_index", "explanation", "fact_check", "correct_answer"):
            assert k not in q, f"leaked {k}"
        assert set(q.keys()) <= {"id", "category_id", "question", "options", "difficulty"}
    # shuffle check: at least some questions have options order differing from DB order
    diff = 0
    for q in qs:
        dbq = mdb.questions.find_one({"id": q["id"]}, {"_id": 0, "options": 1})
        assert sorted(dbq["options"]) == sorted(q["options"])
        diff += dbq["options"] != q["options"]
    assert diff >= 5, f"only {diff}/20 shuffled"


# --- answer lock / validation / partial submit / closed run
def test_answer_lock_partial_and_closed(user):
    r = user.post(f"{API}/palier/categories/{CAT}/1/start")
    qs = r.json()["questions"]
    q0 = qs[0]
    cp, dbq = _correct_pos(q0)
    wrong = (cp + 1) % len(q0["options"])
    a1 = user.post(f"{API}/palier/categories/{CAT}/1/answer", json={"question_id": q0["id"], "answer": wrong})
    assert a1.status_code == 200, a1.text
    d1 = a1.json()
    assert d1["correct"] is False and d1["answer"] == wrong and d1["correct_index"] == cp
    assert d1["correct_answer"] == dbq["options"][dbq["correct_index"]]
    assert "explanation" in d1
    # second call with the correct answer -> identical stored result
    a2 = user.post(f"{API}/palier/categories/{CAT}/1/answer", json={"question_id": q0["id"], "answer": cp})
    assert a2.status_code == 200 and a2.json() == d1
    # invalid index / foreign question
    assert user.post(f"{API}/palier/categories/{CAT}/1/answer",
                     json={"question_id": qs[1]["id"], "answer": 9}).status_code in (400, 422)
    assert user.post(f"{API}/palier/categories/{CAT}/1/answer",
                     json={"question_id": "nope", "answer": 0}).status_code == 400
    # answer 4 more correctly (5 answered total: 1 wrong + 4 correct)
    for q in qs[1:5]:
        c, _ = _correct_pos(q)
        rr = user.post(f"{API}/palier/categories/{CAT}/1/answer", json={"question_id": q["id"], "answer": c})
        assert rr.json()["correct"] is True
    s = user.post(f"{API}/palier/categories/{CAT}/1/submit", json={})
    assert s.status_code == 200, s.text
    sd = s.json()
    assert sd["score"] == 4 and sd["passed"] is False
    assert len(sd["mistakes"]) == 16
    nulls = [m for m in sd["mistakes"] if m["your_answer"] is None]
    assert len(nulls) == 15
    for m in sd["mistakes"]:
        assert {"question_id", "question", "your_answer", "correct_answer", "explanation"} <= set(m)
    # after submit: answer 400, submit 400
    assert user.post(f"{API}/palier/categories/{CAT}/1/answer",
                     json={"question_id": qs[6]["id"], "answer": 0}).status_code == 400
    assert user.post(f"{API}/palier/categories/{CAT}/1/submit", json={}).status_code == 400


# --- client-supplied answers in submit body are ignored
def test_submit_ignores_client_answers(user):
    qs = user.post(f"{API}/palier/categories/{CAT}/1/start").json()["questions"]
    fake = [{"question_id": q["id"], "answer_index": _correct_pos(q)[0]} for q in qs]
    sd = user.post(f"{API}/palier/categories/{CAT}/1/submit", json={"answers": fake}).json()
    assert sd["score"] == 0 and len(sd["mistakes"]) == 20


# --- replay after failure returns same question set
def test_replay_same_set_and_pass_unlocks(user):
    first = user.post(f"{API}/palier/categories/{CAT}/1/start").json()["questions"]
    ids1 = [q["id"] for q in first]
    for q in first:
        c, _ = _correct_pos(q)
        user.post(f"{API}/palier/categories/{CAT}/1/answer", json={"question_id": q["id"], "answer": c})
    sd = user.post(f"{API}/palier/categories/{CAT}/1/submit", json={}).json()
    assert sd["score"] == 20 and sd["passed"] and sd["next_palier_unlocked"] and sd["next_palier"] == 2
    assert sd["mistakes"] == []
    ov = user.get(f"{API}/palier/categories/{CAT}").json()
    p1 = ov["paliers"][0]
    assert p1["completed"] and p1["best_score"] == 20 and p1["attempts"] == 3
    assert ov["paliers"][1]["unlocked"] is True
    lb = user.get(f"{API}/palier/leaderboard/{CAT}?limit=1000").json()
    assert any(e["is_current_user"] for e in lb["entries"]) or lb["me_out_of_top"]
    assert user.post(f"{API}/palier/categories/{CAT}/2/start").status_code == 200
    assert user.post(f"{API}/palier/categories/{CAT}/3/start").status_code == 403
    assert len(set(ids1)) == 20


def test_replay_same_questions_after_fail(user2):
    a = [q["id"] for q in user2.post(f"{API}/palier/categories/{CAT}/1/start").json()["questions"]]
    user2.post(f"{API}/palier/categories/{CAT}/1/submit", json={})
    b = [q["id"] for q in user2.post(f"{API}/palier/categories/{CAT}/1/start").json()["questions"]]
    assert a == b


# --- C: stats + mastery combine classic + palier
def test_stats_and_mastery_combined():
    s = _new_user()
    try:
        qr = s.get(f"{API}/categories/{CAT}/questions").json()["questions"]
        answers = [{"question_id": q["id"], "answer_index": q["correct_index"]} for q in qr[:10]]
        att = s.post(f"{API}/attempts", json={"category_id": CAT, "answers": answers})
        assert att.status_code == 200, att.text
        classic_score = len(answers)
        qs = s.post(f"{API}/palier/categories/{CAT}/1/start").json()["questions"]
        for q in qs[:15]:
            s.post(f"{API}/palier/categories/{CAT}/1/answer", json={"question_id": q["id"], "answer": _correct_pos(q)[0]})
        sub = s.post(f"{API}/palier/categories/{CAT}/1/submit", json={}).json()
        assert sub["score"] == 15
        st = s.get(f"{API}/stats").json()
        assert st["quizzes_played"] == 2
        assert st["correct_answers"] == classic_score + 15
        assert st["total_answers"] == classic_score + 20
        pr = s.get(f"{API}/progression/me").json()
        m = next(x for x in pr["mastery"] if x["category_id"] == CAT)
        assert m["correct"] == classic_score + 15 and m["total"] == classic_score + 20 and m["quizzes_played"] == 2
    finally:
        s.delete(f"{API}/auth/account")


# --- B2: stock < 20 in overview
def test_stock_overview(user):
    ct = user.get(f"{API}/palier/categories/cuisine-terroir").json()["paliers"]
    assert ct[0]["stock_available"] == 19 and ct[1]["stock_available"] == 19
    bv = user.get(f"{API}/palier/categories/bien-vieillir").json()["paliers"]
    assert bv[0]["stock_available"] < 20
    assert user.post(f"{API}/palier/categories/cuisine-terroir/1/start").status_code == 409
