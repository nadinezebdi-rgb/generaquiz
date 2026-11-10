# Iteration 46: Lucette rename, tips share_url, OG share page, theme showcase, sitemap/robots, morning email tip block
import os
import re
import sys
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")

DATE = "2026-11-10"
THEMES = ["cinema", "chansons", "annees-50-60", "objets-antan", "histoire-france",
          "cuisine-terroir", "culture-40-ans", "culture-70-ans"]


# --- Categories / mascot rename
def test_categories_lucette():
    r = requests.get(f"{BASE_URL}/api/categories")
    assert r.status_code == 200
    cats = r.json()
    bv = next(c for c in cats if c["id"] == "bien-vieillir")
    assert bv["mascot_name"] == "Lucette la Pétillante"
    assert "Lucienne" not in r.text


# --- Tips API
def _check_tip(t):
    assert t["share_url"].endswith(f"/api/share/conseil/{t['date_key']}")
    assert t["share_url"].startswith("https://")
    assert t["page_url"].endswith(f"/conseils-bien-vieillir/{t['date_key']}")
    for k in ("title", "text", "action", "theme"):
        assert k in t


def test_tip_today():
    r = requests.get(f"{BASE_URL}/api/tips/today")
    assert r.status_code == 200
    d = r.json()
    assert d["tip"] is not None
    _check_tip(d["tip"])


def test_tips_recent_366():
    r = requests.get(f"{BASE_URL}/api/tips/recent?limit=366")
    assert r.status_code == 200
    lst = r.json()
    assert len(lst) >= 1
    for t in lst:
        _check_tip(t)
    assert requests.get(f"{BASE_URL}/api/tips/recent?limit=367").status_code == 422


def test_tip_by_date():
    r = requests.get(f"{BASE_URL}/api/tips/{DATE}")
    assert r.status_code == 200
    _check_tip(r.json())
    assert r.json()["date_key"] == DATE


def test_tip_bad_and_missing():
    assert requests.get(f"{BASE_URL}/api/tips/bad-date").status_code == 422
    assert requests.get(f"{BASE_URL}/api/tips/2020-01-01").status_code == 404


# --- Share OG page
def test_share_page_og():
    r = requests.get(f"{BASE_URL}/api/share/conseil/{DATE}", allow_redirects=False)
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    h = r.text
    for tag in ("og:title", "og:description", "og:image", "og:url", 'rel="canonical"'):
        assert tag in h, tag
    assert f'http-equiv="refresh" content="0;url={BASE_URL}/conseils-bien-vieillir/{DATE}"' in h
    m = re.search(r'property="og:image" content="([^"]+)"', h)
    img = m.group(1)
    assert img.startswith("https://") and img.endswith("bien-vieillir-og.jpg")
    ir = requests.get(img)
    assert ir.status_code == 200
    assert ir.headers["content-type"].startswith("image/jpeg")
    assert "Lucette" in h


def test_og_image_dimensions():
    from PIL import Image
    import io
    ir = requests.get(f"{BASE_URL}/api/static/share/bien-vieillir-og.jpg")
    im = Image.open(io.BytesIO(ir.content))
    assert im.size == (1200, 630)


def test_share_page_404():
    assert requests.get(f"{BASE_URL}/api/share/conseil/2020-01-01").status_code == 404
    assert requests.get(f"{BASE_URL}/api/share/conseil/xx").status_code == 422


# --- Showcase
@pytest.mark.parametrize("cid", THEMES)
def test_showcase(cid):
    r = requests.get(f"{BASE_URL}/api/categories/{cid}/showcase")
    assert r.status_code == 200
    d = r.json()
    assert d["category"]["id"] == cid
    assert 1 <= len(d["samples"]) <= 6
    for s in d["samples"]:
        assert s["question"] and s["answer"]
        assert "explanation" in s and "discussion_prompt" in s
    assert len(d["others"]) == 9
    assert all(o["id"] != cid for o in d["others"])
    r2 = requests.get(f"{BASE_URL}/api/categories/{cid}/showcase")
    assert r2.json()["samples"] == d["samples"]


def test_showcase_unknown():
    assert requests.get(f"{BASE_URL}/api/categories/unknown/showcase").status_code == 404


# --- sitemap / robots
def test_sitemap_robots():
    sm = requests.get(f"{BASE_URL}/sitemap.xml").text
    assert "/conseils-bien-vieillir" in sm
    for t in THEMES:
        assert f"/decouvrir/{t}" in sm, t
    rb = requests.get(f"{BASE_URL}/robots.txt").text
    for p in ("/decouvrir/", "/bien-vieillir", "/conseils-bien-vieillir"):
        assert f"Allow: {p}" in rb, p


# --- Morning email HTML (pure function, no sending)
def test_morning_email_tip_block():
    sys.path.insert(0, "/app/backend")
    from dotenv import load_dotenv
    load_dotenv("/app/backend/.env")
    from daily_email import _build_morning_email_html
    tip = {"date_key": DATE, "theme": "Sommeil", "title": "TEST <b>titre</b>", "text": "Texte", "action": "Geste"}
    html = _build_morning_email_html("Nadine", 3, "https://x/app", tip)
    assert "Lucette" in html
    assert f"conseils-bien-vieillir/{DATE}" in html
    assert "&lt;b&gt;titre" in html
    html2 = _build_morning_email_html("Nadine", 3, "https://x/app", None)
    assert "conseils-bien-vieillir" not in html2
    assert "Le conseil de Lucette" not in html2
