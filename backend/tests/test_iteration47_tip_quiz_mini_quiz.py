# Iteration 47: tip quiz (daily tips QCM) + weekly mini-quiz on theme showcases
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
DATE = "2026-11-10"


@pytest.fixture(scope="module")
def s():
    return requests.Session()


def _check_public_quiz(tip):
    assert "quiz" in tip, f"no quiz on {tip.get('date_key')}"
    q = tip["quiz"]
    assert isinstance(q["question"], str) and q["question"]
    assert isinstance(q["options"], list) and len(q["options"]) == 4
    assert "correct_index" not in q and "explanation" not in q
    for k in ("correct_index", "explanation", "review", "quiz_attempts", "writer_model"):
        assert k not in tip


# --- Tip quiz exposure ---
class TestTipQuizPublic:
    def test_today(self, s):
        r = s.get(f"{BASE_URL}/api/tips/today")
        assert r.status_code == 200
        _check_public_quiz(r.json()["tip"])

    def test_recent(self, s):
        r = s.get(f"{BASE_URL}/api/tips/recent?limit=366")
        assert r.status_code == 200
        data = r.json()
        assert any(t["date_key"] == DATE for t in data)
        for t in data:
            if "quiz" in t:
                _check_public_quiz(t)

    def test_by_date(self, s):
        r = s.get(f"{BASE_URL}/api/tips/{DATE}")
        assert r.status_code == 200
        assert r.json()["theme"] == "sommeil"
        _check_public_quiz(r.json())


# --- Tip answer ---
class TestTipAnswer:
    def test_all_choices_consistent(self, s):
        results = [s.post(f"{BASE_URL}/api/tips/{DATE}/answer", json={"choice": i}) for i in range(4)]
        assert all(r.status_code == 200 for r in results)
        data = [r.json() for r in results]
        ci = data[0]["correct_index"]
        assert isinstance(ci, int) and 0 <= ci <= 3
        assert all(d["correct_index"] == ci for d in data)
        assert sum(d["correct"] for d in data) == 1
        assert data[ci]["correct"] is True
        assert data[0]["explanation"]

    @pytest.mark.parametrize("payload", [{"choice": 7}, {"choice": -1}, {}, {"choice": "a"}])
    def test_invalid_choice(self, s, payload):
        r = s.post(f"{BASE_URL}/api/tips/{DATE}/answer", json=payload)
        assert r.status_code == 422

    def test_unknown_date(self, s):
        r = s.post(f"{BASE_URL}/api/tips/2001-01-01/answer", json={"choice": 0})
        assert r.status_code == 404

    def test_bad_date_format(self, s):
        r = s.post(f"{BASE_URL}/api/tips/abc/answer", json={"choice": 0})
        assert r.status_code in (404, 422)


# --- Mini-quiz showcase ---
CATS = ["cinema", "voyages-france", "bien-vieillir"]


class TestMiniQuiz:
    @pytest.mark.parametrize("cat", CATS)
    def test_showcase_mini_quiz(self, s, cat):
        r = s.get(f"{BASE_URL}/api/categories/{cat}/showcase")
        assert r.status_code == 200
        d = r.json()
        mq = d["mini_quiz"]
        assert isinstance(mq, list)
        print(cat, "mini_quiz len", len(mq), "samples", len(d["samples"]), "count", d["category"]["count"])
        if cat != "bien-vieillir":
            assert len(mq) == 3
        sample_qs = {x["question"] for x in d["samples"]}
        for q in mq:
            assert set(q.keys()) == {"id", "question", "options"}
            assert q["question"] not in sample_qs
            assert len(q["options"]) >= 2
        assert len({q["id"] for q in mq}) == len(mq)
        r2 = s.get(f"{BASE_URL}/api/categories/{cat}/showcase").json()
        assert [q["id"] for q in r2["mini_quiz"]] == [q["id"] for q in mq]

    def test_answer_correct_flow(self, s):
        mq = s.get(f"{BASE_URL}/api/categories/cinema/showcase").json()["mini_quiz"]
        for q in mq:
            r = s.post(f"{BASE_URL}/api/categories/cinema/mini-quiz/answer", json={"question_id": q["id"], "choice": 0})
            assert r.status_code == 200
            d = r.json()
            assert isinstance(d["correct"], bool)
            assert 0 <= d["correct_index"] < len(q["options"])
            assert d["correct"] == (d["correct_index"] == 0)
            assert "explanation" in d
            r2 = s.post(f"{BASE_URL}/api/categories/cinema/mini-quiz/answer",
                        json={"question_id": q["id"], "choice": d["correct_index"]})
            assert r2.json()["correct"] is True

    def test_cross_category_404(self, s):
        mq = s.get(f"{BASE_URL}/api/categories/cinema/showcase").json()["mini_quiz"]
        r = s.post(f"{BASE_URL}/api/categories/voyages-france/mini-quiz/answer",
                   json={"question_id": mq[0]["id"], "choice": 0})
        assert r.status_code == 404

    def test_unknown_question_404(self, s):
        r = s.post(f"{BASE_URL}/api/categories/cinema/mini-quiz/answer",
                   json={"question_id": "nope-xyz", "choice": 0})
        assert r.status_code == 404

    def test_invalid_choice_422(self, s):
        mq = s.get(f"{BASE_URL}/api/categories/cinema/showcase").json()["mini_quiz"]
        r = s.post(f"{BASE_URL}/api/categories/cinema/mini-quiz/answer",
                   json={"question_id": mq[0]["id"], "choice": 9})
        assert r.status_code == 422

    def test_unknown_category_showcase_404(self, s):
        assert s.get(f"{BASE_URL}/api/categories/zz-nope/showcase").status_code == 404
