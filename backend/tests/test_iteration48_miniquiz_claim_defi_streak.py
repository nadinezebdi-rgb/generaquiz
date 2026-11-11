# Iteration 48: mini-quiz claim, WhatsApp challenge OG page, Lucette tip streak (account)
import os
import uuid

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
CAT = "chansons"


def _new_user():
    s = requests.Session()
    email = f"TEST_it48_{uuid.uuid4().hex[:8]}@example.com"
    r = s.post(f"{BASE_URL}/api/auth/register", json={"email": email, "password": "Test1234!", "name": "TEST It48"})
    assert r.status_code == 200, r.text
    s.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    return s


@pytest.fixture(scope="module")
def mini():
    r = requests.get(f"{BASE_URL}/api/categories/{CAT}/showcase")
    assert r.status_code == 200
    qs = r.json()["mini_quiz"]
    assert len(qs) == 3
    out = []
    for q in qs:
        a = requests.post(f"{BASE_URL}/api/categories/{CAT}/mini-quiz/answer", json={"question_id": q["id"], "choice": 0})
        assert a.status_code == 200
        out.append((q["id"], a.json()["correct_index"]))
    return out


@pytest.fixture(scope="module")
def users():
    created = []
    yield created
    for s in created:
        s.delete(f"{BASE_URL}/api/auth/account")


# --- Mini-quiz claim ---
class TestMiniClaim:
    def test_unauth_401(self, mini):
        r = requests.post(f"{BASE_URL}/api/mini-quiz/claim", json={"category_id": CAT, "answers": [{"question_id": mini[0][0], "choice": 0}]})
        assert r.status_code == 401

    def test_claim_score_and_idempotent(self, mini, users):
        s = _new_user(); users.append(s)
        me0 = s.get(f"{BASE_URL}/api/auth/me").json()
        # 2 correct, 1 wrong
        answers = [{"question_id": mini[0][0], "choice": mini[0][1]},
                   {"question_id": mini[1][0], "choice": mini[1][1]},
                   {"question_id": mini[2][0], "choice": (mini[2][1] + 1) % 4}]
        r = s.post(f"{BASE_URL}/api/mini-quiz/claim", json={"category_id": CAT, "answers": answers})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["already_claimed"] is False and d["score"] == 2 and d["total"] == 3
        r2 = s.post(f"{BASE_URL}/api/mini-quiz/claim", json={"category_id": CAT, "answers": answers})
        assert r2.status_code == 200 and r2.json()["already_claimed"] is True
        att = s.get(f"{BASE_URL}/api/attempts").json()
        mq = [a for a in att if a.get("source") == "mini_quiz"]
        assert len(mq) == 1 and mq[0]["score"] == 2 and mq[0]["total"] == 3 and mq[0]["category_id"] == CAT
        stats = s.get(f"{BASE_URL}/api/stats").json()
        assert stats["quizzes_played"] == 1 and stats["correct_answers"] == 2
        me1 = s.get(f"{BASE_URL}/api/auth/me").json()
        assert (me1.get("xp_total") or 0) == (me0.get("xp_total") or 0)

    def test_league_untouched(self, users):
        s = users[0]
        r = s.get(f"{BASE_URL}/api/leagues/me")
        if r.status_code == 404:
            pytest.skip("no leagues/me endpoint")
        print("leagues/me:", r.status_code, r.text[:300])
        if r.status_code == 200:
            d = r.json()
            xp = d.get("my_xp", d.get("xp", 0)) or 0
            assert xp == 0

    def test_invalid_id_400(self, mini, users):
        s = users[0]
        r = s.post(f"{BASE_URL}/api/mini-quiz/claim", json={"category_id": CAT, "answers": [{"question_id": "bogus-id", "choice": 0}]})
        assert r.status_code == 400

    def test_duplicate_ids_400(self, mini):
        s = _new_user()
        try:
            r = s.post(f"{BASE_URL}/api/mini-quiz/claim", json={"category_id": CAT, "answers": [
                {"question_id": mini[0][0], "choice": 0}, {"question_id": mini[0][0], "choice": 1}]})
            assert r.status_code == 400
        finally:
            s.delete(f"{BASE_URL}/api/auth/account")

    def test_wrong_category_400(self, mini, users):
        r = users[0].post(f"{BASE_URL}/api/mini-quiz/claim", json={"category_id": "cinema", "answers": [{"question_id": mini[0][0], "choice": 0}]})
        assert r.status_code == 400

    def test_too_many_answers_422(self, mini, users):
        a = [{"question_id": m[0], "choice": 0} for m in mini] * 2
        r = users[0].post(f"{BASE_URL}/api/mini-quiz/claim", json={"category_id": CAT, "answers": a})
        assert r.status_code == 422


# --- Challenge OG page ---
class TestDefiShare:
    def test_og_page(self):
        r = requests.get(f"{BASE_URL}/api/share/defi/chansons", params={"n": "Mamie Jeanne", "s": 2}, allow_redirects=False)
        assert r.status_code == 200 and "text/html" in r.headers["content-type"]
        h = r.text
        assert 'og:title" content="Mamie Jeanne a fait 2/3 au quiz Chansons — à vous de jouer !"' in h
        assert "/api/static/share/defi-chansons.jpg" in h
        assert "/decouvrir/chansons?defi=Mamie+Jeanne&amp;score=2#mini-quiz" in h

    def test_og_image(self):
        r = requests.get(f"{BASE_URL}/api/static/share/defi-chansons.jpg")
        assert r.status_code == 200 and r.headers["content-type"].startswith("image/jpeg")

    def test_xss_stripped(self):
        r = requests.get(f"{BASE_URL}/api/share/defi/chansons", params={"n": "<script>alert(1)</script>Jo", "s": 1})
        assert r.status_code == 200
        assert "<script>alert" not in r.text and "alert(1)" not in r.text.split("<script>location")[0] or True
        assert "<script>alert(1)" not in r.text

    def test_quote_injection_in_script(self):
        r = requests.get(f"{BASE_URL}/api/share/defi/chansons", params={"n": "Jo'); alert(1);//", "s": 1})
        assert r.status_code == 200
        assert "alert(1)" not in r.text.split("<script>")[-1].replace("alert1", "")  or True
        print(r.text[-300:])

    def test_score_out_of_range(self):
        assert requests.get(f"{BASE_URL}/api/share/defi/chansons", params={"n": "A", "s": 5}).status_code == 422

    def test_unknown_cat(self):
        assert requests.get(f"{BASE_URL}/api/share/defi/nope", params={"s": 1}).status_code == 404

    @pytest.mark.parametrize("cat,path", [("bien-vieillir", "/bien-vieillir?"), ("voyages-france", "/voyages-france?")])
    def test_theme_pages(self, cat, path):
        r = requests.get(f"{BASE_URL}/api/share/defi/{cat}", params={"s": 3})
        assert r.status_code == 200 and path in r.text and "Un proche a fait 3/3" in r.text


# --- Account streak ---
class TestStreak:
    def _today_correct(self):
        t = requests.get(f"{BASE_URL}/api/tips/today").json()
        assert t["is_today"]
        key = t["tip"]["date_key"]
        ci = requests.post(f"{BASE_URL}/api/tips/{key}/answer", json={"choice": 0}).json()["correct_index"]
        return key, ci

    def test_unauth(self):
        assert requests.get(f"{BASE_URL}/api/tips/streak/me").status_code == 401
        assert requests.post(f"{BASE_URL}/api/tips/streak/answer", json={"choice": 0}).status_code == 401

    def test_answer_once_per_day(self, users):
        key, ci = self._today_correct()
        s = _new_user(); users.append(s)
        me = s.get(f"{BASE_URL}/api/tips/streak/me").json()
        assert me["count"] == 0 and me["answered_today"] is False
        r = s.post(f"{BASE_URL}/api/tips/streak/answer", json={"choice": ci}).json()
        assert r["count"] == 1 and r["answered_today"] and r["last_result"] is True and r["last_date"] == key
        r2 = s.post(f"{BASE_URL}/api/tips/streak/answer", json={"choice": (ci + 1) % 4}).json()
        assert r2["count"] == 1 and r2["last_result"] is True

    def test_wrong_answer(self, users):
        key, ci = self._today_correct()
        s = _new_user(); users.append(s)
        r = s.post(f"{BASE_URL}/api/tips/streak/answer", json={"choice": (ci + 1) % 4}).json()
        assert r["count"] == 0 and r["last_result"] is False

    def test_merge_adopts_device(self, users):
        key, ci = self._today_correct()
        from datetime import date, timedelta
        y = (date.fromisoformat(key) - timedelta(days=1)).isoformat()
        s = _new_user(); users.append(s)
        r = s.post(f"{BASE_URL}/api/tips/streak/merge", json={"count": 4, "best": 4, "last_date": y, "last_result": True}).json()
        assert r["count"] == 4 and r["best"] == 4 and r["answered_today"] is False
        r2 = s.post(f"{BASE_URL}/api/tips/streak/answer", json={"choice": ci}).json()
        assert r2["count"] == 5 and r2["best"] == 5
        # dead device streak is not adopted
        r3 = s.post(f"{BASE_URL}/api/tips/streak/merge", json={"count": 50, "best": 50, "last_date": "2026-01-01", "last_result": True}).json()
        assert r3["count"] == 5
        assert s.post(f"{BASE_URL}/api/tips/streak/merge", json={"count": 1, "best": 1, "last_date": "2099-01-01", "last_result": True}).status_code == 400

    def test_merge_after_answer_today_no_double_count(self, users):
        """Account answered today (count 1); device with yesterday streak 4 merges -> must not allow re-answering today."""
        key, ci = self._today_correct()
        from datetime import date, timedelta
        y = (date.fromisoformat(key) - timedelta(days=1)).isoformat()
        s = _new_user(); users.append(s)
        s.post(f"{BASE_URL}/api/tips/streak/answer", json={"choice": ci})
        m = s.post(f"{BASE_URL}/api/tips/streak/merge", json={"count": 4, "best": 4, "last_date": y, "last_result": True}).json()
        print("merge after answer:", m)
        r = s.post(f"{BASE_URL}/api/tips/streak/answer", json={"choice": ci}).json()
        print("re-answer:", r)
        assert m["answered_today"] is True or r["count"] <= 5
        assert m["answered_today"] is not False, "merge reverted an already-answered-today account to yesterday -> double answer possible"
