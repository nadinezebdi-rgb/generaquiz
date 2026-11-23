# Iteration 54: gift platform Stripe checkout, admin gift redeem, habit express quiz + habit_series badge,
# morning email habit block, new epoques categories (annees-80 / annees-2010), weekly palier >=140 filter
import os
import sys
import uuid

import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
ADMIN = {"email": "admin@generaquiz.fr", "password": os.environ.get("ADMIN_PASSWORD", "")}
HABITS = ["marche", "equilibre", "memoire", "lien", "sortie", "sommeil"]
OLD_IDS = None


def _env(key):
    for line in open("/app/backend/.env"):
        if line.startswith(key + "="):
            return line.split("=", 1)[1].strip().strip('"')


DB = MongoClient(_env("MONGO_URL"))[_env("DB_NAME")]


def _s(tok):
    s = requests.Session()
    s.headers["Authorization"] = f"Bearer {tok}"
    return s


@pytest.fixture(scope="module")
def admin():
    r = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN)
    if r.status_code != 200:
        pytest.skip("admin login failed")
    return _s(r.json()["access_token"])


CREATED_USERS = []


def _register(tag):
    email = f"test_it54_{tag}_{uuid.uuid4().hex[:6]}@example.com"
    r = requests.post(f"{BASE_URL}/api/auth/register", json={"email": email, "password": "Test1234!", "name": f"TEST {tag}"})
    assert r.status_code == 200, r.text
    s = _s(r.json()["access_token"])
    s.email = email
    CREATED_USERS.append(email)
    return s


@pytest.fixture(scope="module")
def codes(admin):
    out = []
    yield out
    for c in out:
        admin.patch(f"{BASE_URL}/api/admin/gifts/{c}/cancel")


# --- gifts: platform checkout
class TestGiftCheckout:
    @pytest.mark.parametrize("offer,amount", [("famille", 79), ("solo", 49)])
    def test_platform_checkout(self, offer, amount):
        r = requests.post(f"{BASE_URL}/api/gifts/checkout", json={
            "offer": offer, "recipient_name": "TEST_Mamie", "buyer_name": "TEST_Paul",
            "buyer_full_name": "TEST_Paul Dupont", "buyer_email": "test_it54@example.com",
            "message": "Bon anniversaire", "delivery_method": "self", "theme": "classic"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert "checkout.stripe.com" in d["url"], d
        tx = DB.payment_transactions.find_one({"session_id": d["session_id"]})
        assert tx is not None
        assert tx["stripe_mode"] == "platform"
        assert tx["amount"] == amount and tx["amount_cents"] == amount * 100
        assert tx["payment_status"] == "initiated" and tx["status"] == "open"
        assert requests.get(f"{BASE_URL}/api/gifts/order/{d['session_id']}",
                            params={"access_token": "bad"}).status_code == 404
        # set a known buyer token on our own test order to exercise _confirm_platform_order (unpaid)
        import hashlib
        tok = uuid.uuid4().hex
        DB.payment_transactions.update_one({"_id": tx["_id"]}, {"$set": {"buyer_access_hash": hashlib.sha256(tok.encode()).hexdigest()}})
        o = requests.get(f"{BASE_URL}/api/gifts/order/{d['session_id']}", params={"access_token": tok})
        assert o.status_code == 200, o.text
        assert o.json()["payment_status"] == "unpaid"
        DB.payment_transactions.update_one({"_id": tx["_id"]}, {"$set": {"status": "TEST_cancelled"}})


# --- gifts: admin code + redeem
class TestGiftRedeem:
    def test_admin_create_redeem(self, admin, codes):
        r = admin.post(f"{BASE_URL}/api/admin/gifts", json={"offer": "famille", "recipient_name": "TEST_Mamie", "buyer_name": "TEST_Paul"})
        assert r.status_code == 200, r.text
        code = r.json()["code"]
        codes.append(code)
        u = _register("redeem")
        r1 = u.post(f"{BASE_URL}/api/gifts/redeem", json={"code": code})
        assert r1.status_code == 200, r1.text
        d = r1.json()
        assert d["plan_tier"] == "famille_v2" and d["max_proches"] == 3, d
        r2 = _register("redeem2").post(f"{BASE_URL}/api/gifts/redeem", json={"code": code})
        assert r2.status_code == 409, r2.text
        me = u.get(f"{BASE_URL}/api/auth/me").json()
        me = me.get("user", me)
        assert me["plan_tier"] == "famille_v2"


# --- habit quiz
class TestHabitQuiz:
    @pytest.mark.parametrize("hid", HABITS)
    def test_quiz_no_answers(self, hid):
        r = requests.get(f"{BASE_URL}/api/bien-vieillir/habits/{hid}/quiz")
        assert r.status_code == 200, r.text
        qs = r.json()["questions"]
        assert 3 <= len(qs) <= 5, len(qs)
        for q in qs:
            assert "correct_index" not in q and "explanation" not in q
            assert set(q) == {"id", "question", "options"}

    def test_answer(self):
        q = requests.get(f"{BASE_URL}/api/bien-vieillir/habits/sommeil/quiz").json()["questions"][0]
        r = requests.post(f"{BASE_URL}/api/bien-vieillir/habits/sommeil/quiz/answer", json={"question_id": q["id"], "choice": 0})
        assert r.status_code == 200
        d = r.json()
        assert set(["correct", "correct_index", "correct_answer", "explanation"]) <= set(d)
        assert d["correct_answer"] == q["options"][d["correct_index"]]
        assert d["correct"] == (d["correct_index"] == 0)

    def test_answer_bad(self):
        assert requests.get(f"{BASE_URL}/api/bien-vieillir/habits/nope/quiz").status_code == 404
        r = requests.post(f"{BASE_URL}/api/bien-vieillir/habits/sommeil/quiz/answer", json={"question_id": "nope", "choice": 0})
        assert r.status_code == 404
        r = requests.post(f"{BASE_URL}/api/bien-vieillir/habits/sommeil/quiz/answer", json={"question_id": "x", "choice": 9})
        assert r.status_code == 422

    def test_complete_requires_auth(self):
        r = requests.post(f"{BASE_URL}/api/bien-vieillir/habits/marche/quiz/complete")
        assert r.status_code == 401, r.status_code

    def test_habit_series_badge(self):
        u = _register("habit")
        seq = ["marche", "marche", "equilibre", "memoire"]
        for i, h in enumerate(seq):
            d = u.post(f"{BASE_URL}/api/bien-vieillir/habits/{h}/quiz/complete").json()
            assert d["awarded_badges"] == [] and d["target"] == 4
        assert d["habits_played"] == 3  # repeated habit not double counted
        d = u.post(f"{BASE_URL}/api/bien-vieillir/habits/sommeil/quiz/complete").json()
        assert d["habits_played"] == 4 and d["awarded_badges"] == ["habit_series"], d
        d = u.post(f"{BASE_URL}/api/bien-vieillir/habits/lien/quiz/complete").json()
        assert d["habits_played"] == 5 and d["awarded_badges"] == []
        mine = u.get(f"{BASE_URL}/api/badges/mine").json()
        assert "habit_series" in str(mine), mine
        assert u.post(f"{BASE_URL}/api/bien-vieillir/habits/zzz/quiz/complete").status_code == 404


# --- morning email
def test_morning_email_habit_block():
    sys.path.insert(0, "/app/backend")
    from dotenv import load_dotenv
    load_dotenv("/app/backend/.env")
    import daily_email
    html = daily_email._build_morning_email_html("TEST", 3, "https://x/app")
    assert "Quiz express Bien vieillir" in html
    assert "/bien-vieillir?quiz=" in html and "#routine" in html


# --- categories
class TestCategories:
    def test_categories(self):
        cats = requests.get(f"{BASE_URL}/api/categories").json()
        cats = cats.get("categories", cats) if isinstance(cats, dict) else cats
        assert len(cats) == 12, [c["id"] for c in cats]
        by = {c["id"]: c for c in cats}
        assert by["annees-80"]["group"] == "epoques" and by["annees-80"]["sort_order"] == 2
        assert by["annees-2010"]["group"] == "epoques" and by["annees-2010"]["sort_order"] == 4
        assert by["annees-80"]["count"] == 0 and by["annees-2010"]["count"] == 0
        assert by["culture-70-ans"]["sort_order"] == 1 and by["culture-40-ans"]["sort_order"] == 3
        playable = [c for c in cats if c["count"] >= 20]
        assert len(playable) == 10, [(c["id"], c["count"]) for c in cats]

    def test_mascots_served(self):
        for cid in ("annees-80", "annees-2010"):
            r = requests.get(f"{BASE_URL}/api/static/mascots/{cid}.png")
            assert r.status_code == 200 and r.headers["content-type"].startswith("image"), cid

    def test_new_category_questions_empty(self, admin):
        r = admin.get(f"{BASE_URL}/api/categories/annees-80/questions")
        assert r.status_code in (200, 404, 409), r.text
        if r.status_code == 200:
            d = r.json()
            qs = d.get("questions", d) if isinstance(d, dict) else d
            assert len(qs) == 0


def teardown_module(module):
    for email in CREATED_USERS:
        u = DB.users.find_one({"email": email})
        if u:
            DB.habit_quiz_plays.delete_many({"user_id": str(u["_id"])})
            DB.user_badges.delete_many({"user_id": str(u["_id"])})
            DB.users.delete_one({"_id": u["_id"]})
