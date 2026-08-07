"""Atelier Mémoire — guided reminiscence workshop (Sprint D+).

Non-quiz activity: the user picks a "décennie" (thème) and gets 5 open-ended
prompts. Answers are stored verbatim in `atelier_entries`. No scoring — the
goal is to trigger and preserve memories, not to grade them.

Data model (atelier_entries):
  {
    user_id: str,
    session_id: str,          # groups the 5 prompts of one workshop
    theme: str,               # "annees-60" | "annees-70" | "annees-80" | "enfance" | "famille"
    prompt_id: str,           # canonical prompt id (see THEMES)
    prompt_text: str,         # denormalised for future portability
    answer: str,              # user's response, up to 1500 chars
    created_at: iso,
  }
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core import db, get_current_user
from badges import award_badge, BADGE_INDEX

router = APIRouter(prefix="/atelier", tags=["atelier"])


# ---------------------------------------------------------------------------
# Themed prompt library — 5 open-ended prompts per theme
# ---------------------------------------------------------------------------
THEMES: dict[str, dict] = {
    "annees-60": {
        "label": "Les années 60",
        "emoji": "📻",
        "description": "Le poste de radio, les 45 tours, les vacances en 2CV.",
        "prompts": [
            "Décrivez la première chanson qui vous fait penser à vos 20 ans.",
            "Quel plat votre mère (ou grand-mère) préparait le dimanche ?",
            "Racontez un dimanche en famille : où alliez-vous, avec qui ?",
            "Quel objet des années 60 aimeriez-vous retrouver aujourd'hui ?",
            "Décrivez la première fois que vous êtes parti(e) en vacances.",
        ],
    },
    "annees-70": {
        "label": "Les années 70",
        "emoji": "🕺",
        "description": "Le tourne-disque, les pattes d'éph, les samedi soir télé.",
        "prompts": [
            "Quelle émission de télévision regardiez-vous le samedi soir ?",
            "Décrivez votre premier salaire ou premier travail.",
            "Quel groupe ou chanteur écoutiez-vous le plus en 1975 ?",
            "Racontez un souvenir d'un été particulier des années 70.",
            "Quelle mode vestimentaire vous représentait à cette époque ?",
        ],
    },
    "annees-80": {
        "label": "Les années 80",
        "emoji": "📺",
        "description": "La cassette VHS, le Minitel, le walkman.",
        "prompts": [
            "Quel film avez-vous vu au cinéma dont vous vous souvenez ?",
            "Décrivez votre voiture (ou celle de vos parents) dans les années 80.",
            "Quel objet technologique vous a le plus impressionné ?",
            "Racontez un anniversaire mémorable de cette décennie.",
            "Quel voisin ou ami vous a particulièrement marqué à cette époque ?",
        ],
    },
    "enfance": {
        "label": "Souvenirs d'enfance",
        "emoji": "🎈",
        "description": "L'école, la maison de vos grands-parents, les jeux dehors.",
        "prompts": [
            "Décrivez votre chambre d'enfant : les couleurs, les objets, l'odeur.",
            "Quel jeu inventiez-vous avec vos frères, sœurs ou voisins ?",
            "Racontez une bêtise dont vous vous souvenez avec le sourire.",
            "Quel adulte de votre enfance vous a le plus marqué et pourquoi ?",
            "Décrivez le goûter préféré de votre enfance.",
        ],
    },
    "famille": {
        "label": "En famille",
        "emoji": "👵",
        "description": "Les repas, les fêtes, les traditions transmises.",
        "prompts": [
            "Quelle tradition familiale aimeriez-vous transmettre à vos petits-enfants ?",
            "Décrivez le repas de Noël (ou Pâques) le plus mémorable.",
            "Quel proverbe ou expression tenez-vous de vos parents ?",
            "Racontez comment vous avez rencontré votre conjoint(e) ou meilleur(e) ami(e).",
            "Quelle histoire de famille aimeriez-vous que personne n'oublie ?",
        ],
    },
}


# ---------------------------------------------------------------------------
# Pydantic payloads
# ---------------------------------------------------------------------------
class AtelierAnswerIn(BaseModel):
    prompt_id: str
    answer: str = Field(..., min_length=1, max_length=1500)


class AtelierSessionSubmit(BaseModel):
    theme: str
    answers: list[AtelierAnswerIn]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@router.get("/themes")
async def list_themes() -> list[dict]:
    """Publicly-viewable catalog: card metadata + prompt count. Prompts hidden until start."""
    return [
        {
            "id": tid,
            "label": t["label"],
            "emoji": t["emoji"],
            "description": t["description"],
            "prompt_count": len(t["prompts"]),
        }
        for tid, t in THEMES.items()
    ]


@router.get("/themes/{theme_id}")
async def get_theme(theme_id: str, user: dict = Depends(get_current_user)) -> dict:
    """Full theme with prompts (auth required — the workshop is a benefit)."""
    theme = THEMES.get(theme_id)
    if not theme:
        raise HTTPException(status_code=404, detail="Thème introuvable")
    return {
        "id": theme_id,
        "label": theme["label"],
        "emoji": theme["emoji"],
        "description": theme["description"],
        "prompts": [
            {"id": f"{theme_id}_p{i+1}", "text": p}
            for i, p in enumerate(theme["prompts"])
        ],
    }


@router.post("/sessions")
async def submit_session(body: AtelierSessionSubmit, user: dict = Depends(get_current_user)) -> dict:
    """Save a completed workshop session.

    Reward:
      - +25 XP (regularité)
      - "Premier atelier" badge on the first ever completed session.
    """
    theme = THEMES.get(body.theme)
    if not theme:
        raise HTTPException(status_code=400, detail="Thème invalide")
    if not body.answers:
        raise HTTPException(status_code=400, detail="Aucune réponse fournie")

    # Build lookup id → text so we denormalise the prompt (future-proof)
    prompt_lookup = {
        f"{body.theme}_p{i+1}": p for i, p in enumerate(theme["prompts"])
    }
    session_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    user_id = str(user["_id"])

    docs: list[dict[str, Any]] = []
    for a in body.answers:
        text = prompt_lookup.get(a.prompt_id)
        if not text:
            raise HTTPException(status_code=400, detail=f"Prompt inconnu: {a.prompt_id}")
        docs.append({
            "user_id": user_id,
            "session_id": session_id,
            "theme": body.theme,
            "prompt_id": a.prompt_id,
            "prompt_text": text,
            "answer": a.answer.strip(),
            "created_at": now,
        })
    if docs:
        await db.atelier_entries.insert_many(docs)

    # XP reward — feeds into leagues + level curve like a normal quiz.
    XP_ATELIER = 25
    await db.users.update_one(
        {"_id": user["_id"]},
        {"$inc": {"xp_total": XP_ATELIER}},
    )
    try:
        from routers.gamification import _ensure_league_membership, _week_key
        await _ensure_league_membership(user_id)
        await db.league_scores.update_one(
            {"user_id": user_id, "week_key": _week_key()},
            {"$inc": {"xp": XP_ATELIER}, "$setOnInsert": {
                "user_id": user_id, "week_key": _week_key(),
                "user_name": user.get("name") or user.get("email", "").split("@")[0],
            }},
            upsert=True,
        )
    except Exception:
        pass

    # First-ever atelier badge — award once. Also award atelier_5 milestone.
    awarded: list[dict] = []
    sessions_done = await db.atelier_entries.distinct("session_id", {"user_id": user_id})
    if await award_badge(user_id, "premier_atelier"):
        awarded.append(BADGE_INDEX["premier_atelier"])
    if len(sessions_done) >= 5 and await award_badge(user_id, "atelier_5"):
        awarded.append(BADGE_INDEX["atelier_5"])
    return {
        "ok": True,
        "session_id": session_id,
        "saved": len(docs),
        "xp_gained": XP_ATELIER,
        "awarded_badges": awarded,
    }


@router.get("/entries")
async def my_entries(user: dict = Depends(get_current_user)) -> list[dict]:
    """Return the user's saved atelier entries grouped by session (most recent first)."""
    user_id = str(user["_id"])
    docs = await db.atelier_entries.find(
        {"user_id": user_id}, {"_id": 0},
    ).sort("created_at", -1).to_list(500)

    # Group by session_id
    sessions: dict[str, dict[str, Any]] = {}
    for d in docs:
        sid = d["session_id"]
        if sid not in sessions:
            sessions[sid] = {
                "session_id": sid,
                "theme": d["theme"],
                "theme_label": THEMES.get(d["theme"], {}).get("label", d["theme"]),
                "theme_emoji": THEMES.get(d["theme"], {}).get("emoji", "📝"),
                "created_at": d["created_at"],
                "entries": [],
            }
        sessions[sid]["entries"].append({
            "prompt_id": d["prompt_id"],
            "prompt_text": d["prompt_text"],
            "answer": d["answer"],
        })
    # Sort by created_at desc
    return sorted(sessions.values(), key=lambda s: s["created_at"], reverse=True)
