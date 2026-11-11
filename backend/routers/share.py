"""Pages de partage avec aperçu riche (Open Graph) pour WhatsApp / Facebook.
Les robots lisent les balises, les humains sont redirigés vers la vraie page."""
import re
from html import escape
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Path, Query
from fastapi.responses import HTMLResponse

from core import FRONTEND_URL, db
from routers.tips import DATE_RE

router = APIRouter(prefix="/share", tags=["share"])

OG_IMAGE = f"{FRONTEND_URL}/api/static/share/bien-vieillir-og.jpg"
THEME_PAGES = {"bien-vieillir": "/bien-vieillir", "voyages-france": "/voyages-france"}


def _og_page(title: str, desc: str, page: str, image: str, og_type: str = "website") -> HTMLResponse:
    t, d, p, i = escape(title), escape(desc), escape(page), escape(image)
    return HTMLResponse(f"""<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8">
<title>{t}</title>
<meta name="description" content="{d}">
<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="GénéraQuiz">
<meta property="og:locale" content="fr_FR">
<meta property="og:title" content="{t}">
<meta property="og:description" content="{d}">
<meta property="og:url" content="{p}">
<meta property="og:image" content="{i}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<link rel="canonical" href="{p}">
<meta http-equiv="refresh" content="0;url={p}">
</head><body><p><a href="{p}">{t}</a></p>
<script>location.replace({page!r});</script></body></html>""")


def clean_name(name: str) -> str:
    return re.sub(r"[^\w\s'\-]", "", name or "", flags=re.UNICODE).strip()[:24]


@router.get("/conseil/{date_key}", response_class=HTMLResponse)
async def share_tip(date_key: str = Path(..., pattern=DATE_RE)) -> HTMLResponse:
    tip = await db.daily_tips.find_one({"date_key": date_key}, {"_id": 0})
    if not tip:
        raise HTTPException(status_code=404, detail="Conseil introuvable")
    return _og_page(
        f"{tip['title']} — le conseil de Lucette",
        f"{tip['text']} Testez vos connaissances avec le quiz Bien vieillir sur GénéraQuiz.",
        f"{FRONTEND_URL}/conseils-bien-vieillir/{date_key}", OG_IMAGE, og_type="article",
    )


@router.get("/defi/{category_id}", response_class=HTMLResponse)
async def share_challenge(category_id: str, n: str = Query("", max_length=60),
                          s: int = Query(..., ge=0, le=3)) -> HTMLResponse:
    cat = await db.categories.find_one({"id": category_id}, {"_id": 0, "title": 1})
    if not cat:
        raise HTTPException(status_code=404, detail="Thème introuvable")
    name = clean_name(n)
    params = urlencode({"defi": name, "score": s} if name else {"score": s})
    page = f"{FRONTEND_URL}{THEME_PAGES.get(category_id, f'/decouvrir/{category_id}')}?{params}#mini-quiz"
    return _og_page(
        f"{name or 'Un proche'} a fait {s}/3 au quiz {cat['title']} — à vous de jouer !",
        "3 questions, sans compte. Saurez-vous faire mieux ? Le mini-quiz de la semaine sur GénéraQuiz.",
        page, f"{FRONTEND_URL}/api/static/share/defi-{category_id}.jpg",
    )
