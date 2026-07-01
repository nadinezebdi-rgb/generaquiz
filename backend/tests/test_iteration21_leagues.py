"""Sprint 1 — Ligues + Streak Saver + Email reminder."""
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import pytest
import requests
from bson import ObjectId

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
ADMIN_EMAIL = "admin@generaquiz.fr"
ADMIN_PASS = "Admin2026!"
PARIS = ZoneInfo("Europe/Paris")


# ---------- fixtures ----------
@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    return sess


@pytest.fixture(scope="module")
def admin(s):
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS})
    assert r.status_code == 200, r.text
    return s


@pytest.fixture(scope="module")
def fresh_user():
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    email = f"TEST_lg_{int(datetime.now().timestamp())}@example.com"
    pw = "Passw0rd!"
    r = sess.post(f"{BASE_URL}/api/auth/register", json={
        "email": email, "password": pw, "name": "TEST League", "birth_year": 1990,
    })
    assert r.status_code in (200, 201), r.text
    return sess, email


# ---------- LEAGUES endpoint ----------
class TestLeaguesCurrent:
    def test_requires_auth(self):
        anon = requests.Session()
        r = anon.get(f"{BASE_URL}/api/gamification/leagues/current")
        assert r.status_code in (401, 403)

    def test_admin_can_fetch(self, admin):
        r = admin.get(f"{BASE_URL}/api/gamification/leagues/current")
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ("tier", "tier_label", "tier_index", "next_tier", "previous_tier",
                  "cohort_id", "week_key", "week_ends_at", "seconds_until_close",
                  "promote_top", "relegate_bottom", "cohort_size", "max_cohort_size",
                  "my_rank", "my_xp", "leaderboard"):
            assert k in d, f"missing key {k}"
        assert d["tier"] in ("bronze", "argent", "or", "diamant")
        assert d["promote_top"] == 5
        assert d["relegate_bottom"] == 3
        assert d["max_cohort_size"] == 30
        assert isinstance(d["leaderboard"], list)
        assert d["seconds_until_close"] >= 0

    def test_lazy_enrollment_new_user(self, fresh_user):
        sess, _ = fresh_user
        r = sess.get(f"{BASE_URL}/api/gamification/leagues/current")
        assert r.status_code == 200
        d = r.json()
        assert d["my_xp"] == 0
        assert d["my_rank"] is not None
        # leaderboard must contain at least myself with is_me=true
        me = [r for r in d["leaderboard"] if r.get("is_me")]
        assert len(me) == 1
        assert me[0]["xp"] == 0


# ---------- ATTEMPTS feeds league_scores ----------
class TestAttemptsFeedXP:
    def test_attempt_adds_xp_to_league(self, fresh_user):
        sess, _ = fresh_user
        before = sess.get(f"{BASE_URL}/api/gamification/leagues/current").json()
        x0 = before["my_xp"]
        # POST an attempt (XP_PER_CORRECT_CATEGORY=1 → +5)
        r = sess.post(f"{BASE_URL}/api/attempts", json={
            "category_id": "histoire", "score": 5, "total": 5, "duration_seconds": 60,
        })
        assert r.status_code == 200, r.text
        after = sess.get(f"{BASE_URL}/api/gamification/leagues/current").json()
        assert after["my_xp"] == x0 + 5, f"my_xp before={x0} after={after['my_xp']}"


# ---------- COOP feeds league_scores ----------
class TestCoopFeedXP:
    def test_coop_answer_grants_league_xp(self, fresh_user):
        sess, _ = fresh_user
        # Get categories then create a coop challenge
        cats = sess.get(f"{BASE_URL}/api/categories").json()
        if not cats:
            pytest.skip("no categories")
        cat_id = cats[0]["id"] if isinstance(cats[0], dict) else cats[0]
        r = sess.post(f"{BASE_URL}/api/coop-challenges", json={
            "category_id": cat_id, "num_questions": 4, "team_name": "TEST_LG_Coop",
            "players": [{"name": "P1", "role": "senior"}, {"name": "P2", "role": "jeune"}],
        })
        if r.status_code != 200:
            pytest.skip(f"coop create failed: {r.status_code} {r.text}")
        token = r.json()["token"]
        # Get questions
        view = sess.get(f"{BASE_URL}/api/coop-challenges/{token}").json()
        q = view["questions"][0]
        before = sess.get(f"{BASE_URL}/api/gamification/leagues/current").json()
        x0 = before["my_xp"]
        # Find correct_index by reading the coop_challenges doc directly
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient
        async def _correct():
            c = AsyncIOMotorClient(os.environ["MONGO_URL"])
            doc = await c[os.environ["DB_NAME"]].coop_challenges.find_one({"token": token})
            c.close()
            return doc["questions"][0].get("correct_index", 0) if doc else 0
        correct_idx = asyncio.run(_correct())
        rr = sess.post(f"{BASE_URL}/api/coop-challenges/{token}/answer",
                       json={"question_id": q.get("id") or q.get("question_id"), "answer_index": correct_idx})
        assert rr.status_code == 200 and rr.json().get("is_correct"), rr.text
        after = sess.get(f"{BASE_URL}/api/gamification/leagues/current").json()
        assert after["my_xp"] > x0, f"my_xp before={x0} after={after['my_xp']}"


# ---------- STREAK SAVER ----------
class TestStreakSaver:
    def test_no_streak_returns_400(self, fresh_user):
        sess, _ = fresh_user
        r = sess.post(f"{BASE_URL}/api/gamification/streak-saver")
        assert r.status_code == 400
        assert "série" in r.json().get("detail", "").lower() or "serie" in r.json().get("detail", "").lower()

    def test_requires_auth(self):
        anon = requests.Session()
        r = anon.post(f"{BASE_URL}/api/gamification/streak-saver")
        assert r.status_code in (401, 403)

    def test_eligible_save_succeeds(self):
        """Setup user in DB with streak=3 + last_date=day_before, then call endpoint."""
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient
        mongo_url = os.environ["MONGO_URL"]
        db_name = os.environ["DB_NAME"]

        sess = requests.Session()
        sess.headers.update({"Content-Type": "application/json"})
        email = f"TEST_ss_{int(datetime.now().timestamp())}@example.com"
        rr = sess.post(f"{BASE_URL}/api/auth/register", json={
            "email": email, "password": "Passw0rd!", "name": "TEST SS", "birth_year": 1990,
        })
        assert rr.status_code in (200, 201)

        now_paris = datetime.now(PARIS)
        day_before = (now_paris - timedelta(days=2)).strftime("%Y-%m-%d")
        yesterday = (now_paris - timedelta(days=1)).strftime("%Y-%m-%d")

        async def _patch(creds):
            client = AsyncIOMotorClient(mongo_url)
            db = client[db_name]
            await db.users.update_one(
                {"email": email.lower()},
                {"$set": {"streak_current": 3, "streak_last_date": day_before, "credits": creds}},
            )
            client.close()

        asyncio.run(_patch(50))

        r = sess.post(f"{BASE_URL}/api/gamification/streak-saver")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["streak_last_date"] == yesterday
        assert d["credits"] == 40  # 50 - 10

        # Now try again — should now fail because last_date is yesterday, not day_before
        r2 = sess.post(f"{BASE_URL}/api/gamification/streak-saver")
        assert r2.status_code == 400

        # Insufficient credits scenario
        asyncio.run(_patch(2))
        r3 = sess.post(f"{BASE_URL}/api/gamification/streak-saver")
        assert r3.status_code in (400, 402)


# ---------- EMAIL REMINDER ----------
class TestLeagueReminder:
    def test_send_league_reminders_callable(self):
        import asyncio, sys
        sys.path.insert(0, "/app/backend")
        from daily_email import send_league_reminders
        res = asyncio.run(send_league_reminders())
        assert isinstance(res, dict)
        assert "sent" in res

    def test_scheduler_has_5_jobs(self):
        """Grep daily_email.py for 5 expected scheduler jobs."""
        with open("/app/backend/daily_email.py") as f:
            src = f.read()
        for jid in ("daily_quiz_email", "leagues_weekly_settle",
                    "mistral_regenerate_all", "premium_expiration_email_j7",
                    "league_reminder_sunday_20h"):
            assert jid in src, f"missing scheduler job id {jid}"
