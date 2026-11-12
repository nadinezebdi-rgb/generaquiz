# Iteration 52: category rename + universes (group/sort_order) — read-only regression checks
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
ADMIN = {"email": "admin@generaquiz.fr", "password": "pF44gVBfLdushm3NZ6dN"}

EXPECTED = {
    "annees-50-60": ("Années 50-60", "nostalgie", 2, 137),
    "chansons": ("Chansons d'antan", "nostalgie", 3, 126),
    "cinema": ("Cinéma", "intemporels", 1, 142),
    "objets-antan": ("Objets d'antan", "nostalgie", 1, 138),
    "histoire-france": ("Histoire de France", "intemporels", 2, 105),
    "cuisine-terroir": ("Cuisine & Terroir", "intemporels", 3, 138),
    "culture-40-ans": ("Années 90-2000", "epoques", 2, 93),
    "culture-70-ans": ("Années 60-70", "epoques", 1, 96),
    "voyages-france": ("Voyages & régions de France", "intemporels", 4, 129),
    "bien-vieillir": ("Bien vieillir", "intemporels", 5, 21),
}


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json=ADMIN)
    if r.status_code != 200:
        pytest.skip(f"admin login failed {r.status_code}")
    tok = r.json().get("token") or r.json().get("access_token")
    if tok:
        s.headers.update({"Authorization": f"Bearer {tok}"})
    return s


@pytest.fixture(scope="module")
def cats():
    r = requests.get(f"{BASE_URL}/api/categories")
    assert r.status_code == 200
    return r.json()


# Categories endpoint: ids, titles, group, sort_order, counts
class TestCategories:
    def test_ten_categories_no_soon(self, cats):
        ids = {c["id"] for c in cats}
        assert ids == set(EXPECTED.keys())
        assert all(not c.get("soon") for c in cats)
        assert not any(c["id"].startswith("soon") for c in cats)

    def test_titles_groups_sort(self, cats):
        for c in cats:
            title, group, so, _ = EXPECTED[c["id"]]
            assert c["title"] == title, c["id"]
            assert c["group"] == group, c["id"]
            assert c["sort_order"] == so, c["id"]
            assert "_id" not in c

    def test_counts(self, cats):
        got = {c["id"]: c.get("count") for c in cats}
        print("counts:", got)
        for cid, (_, _, _, n) in EXPECTED.items():
            assert got[cid] == n, f"{cid}: {got[cid]} != {n}"

    def test_other_fields_present(self, cats):
        for c in cats:
            for k in ("description", "mascot_image", "mascot_name"):
                assert k in c, f"{c['id']} missing {k}"

    def test_no_old_titles(self, cats):
        txt = str(cats)
        assert "Génération 40" not in txt and "Génération 70" not in txt


# Paliers / progression / leaderboards still keyed on unchanged ids
class TestPaliers:
    @pytest.mark.parametrize("cid", list(EXPECTED.keys()))
    def test_overview_7_paliers(self, session, cid):
        r = session.get(f"{BASE_URL}/api/palier/categories/{cid}")
        assert r.status_code == 200
        d = r.json()
        assert len(d["paliers"]) == 7
        assert d["category"]["title"] == EXPECTED[cid][0]

    def test_admin_cinema_progress_intact(self, session):
        r = session.get(f"{BASE_URL}/api/palier/categories/cinema")
        p = r.json()["paliers"]
        done = [x for x in p if x["completed"]]
        print("cinema completed:", [(x["palier"], x["best_score"]) for x in done])
        assert len(done) >= 1

    def test_leaderboard_cinema(self, session):
        r = session.get(f"{BASE_URL}/api/palier/leaderboard/cinema")
        assert r.status_code == 200
        d = r.json()
        print("leaderboard:", d)
        assert isinstance(d.get("entries"), list)
        assert len(d["entries"]) >= 1

    @pytest.mark.parametrize("cid", ["culture-40-ans", "chansons"])
    def test_leaderboard_renamed(self, session, cid):
        r = session.get(f"{BASE_URL}/api/palier/leaderboard/{cid}")
        assert r.status_code == 200

    @pytest.mark.parametrize("cid", ["culture-40-ans", "chansons"])
    def test_questions_endpoint(self, session, cid):
        r = session.get(f"{BASE_URL}/api/categories/{cid}/questions")
        assert r.status_code == 200, r.text[:200]

    def test_weekly(self, session):
        r = session.get(f"{BASE_URL}/api/palier/weekly")
        print("weekly", r.status_code, r.text[:300])
        assert r.status_code in (200, 404)
        assert "Génération" not in r.text
        h = session.get(f"{BASE_URL}/api/palier/weekly/history")
        print("history", h.status_code, h.text[:300])
        assert "Génération" not in h.text
