"""Pages de partage avec aperçu riche (Open Graph) pour WhatsApp / Facebook.
Les robots lisent les balises, les humains sont redirigés vers la page du conseil."""
from html import escape

from fastapi import APIRouter, HTTPException, Path
from fastapi.responses import HTMLResponse

from core import FRONTEND_URL, db
from routers.tips import DATE_RE

router = APIRouter(prefix="/share", tags=["share"])

OG_IMAGE = f"{FRONTEND_URL}/api/static/share/bien-vieillir-og.jpg"


@router.get("/conseil/{date_key}", response_class=HTMLResponse)
async def share_tip(date_key: str = Path(..., pattern=DATE_RE)) -> HTMLResponse:
    tip = await db.daily_tips.find_one({"date_key": date_key}, {"_id": 0})
    if not tip:
        raise HTTPException(status_code=404, detail="Conseil introuvable")
    page = f"{FRONTEND_URL}/conseils-bien-vieillir/{date_key}"
    title = escape(f"{tip['title']} — le conseil de Lucette")
    desc = escape(f"{tip['text']} Testez vos connaissances avec le quiz Bien vieillir sur GénéraQuiz.")
    html = f"""<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="GénéraQuiz">
<meta property="og:locale" content="fr_FR">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{escape(page)}">
<meta property="og:image" content="{escape(OG_IMAGE)}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<link rel="canonical" href="{escape(page)}">
<meta http-equiv="refresh" content="0;url={escape(page)}">
</head><body><p><a href="{escape(page)}">{title}</a></p>
<script>location.replace({page!r});</script></body></html>"""
    return HTMLResponse(html)
