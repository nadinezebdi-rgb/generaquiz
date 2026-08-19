"""Mon Livre de Vie — module de mémoire intergénérationnelle.

Refonte de l'ancien Atelier Mémoire. Structure en 10 chapitres progressifs,
3 modes de saisie (texte / audio / famille délégué), photos, permissions
familiales, questions envoyées entre membres, transcription Whisper et
export PDF téléchargeable.
"""
from __future__ import annotations

import base64
import io
import os
import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from core import db, get_current_user, logger


router = APIRouter(prefix="/livre", tags=["livre"])


# =============================================================================
# Bibliothèque des 10 chapitres avec prompts guidés
# =============================================================================
CHAPTERS: dict[str, dict] = {
    "origines": {
        "order": 1, "label": "Mes origines", "emoji": "🌱",
        "description": "Naissance, parents, grands-parents, racines familiales.",
        "prompts": [
            "Où êtes-vous né(e) et quel jour ? Que sait-on de ce jour-là ?",
            "Racontez ce que vous savez de vos parents avant votre naissance.",
            "Vos grands-parents — d'où venaient-ils, que faisaient-ils ?",
            "Y a-t-il une anecdote sur votre nom ou votre prénom ?",
            "Une histoire ou une légende familiale que l'on vous a transmise.",
        ],
    },
    "enfance": {
        "order": 2, "label": "Mon enfance", "emoji": "🧸",
        "description": "Les premières années, la maison, les jeux, les odeurs.",
        "prompts": [
            "Où avez-vous grandi ? Décrivez la maison ou l'appartement.",
            "Quel était votre jeu ou jouet préféré enfant ?",
            "Racontez une odeur ou un plat de votre enfance qui vous marque encore.",
            "Aviez-vous un(e) meilleur(e) ami(e) d'enfance ? Que faisiez-vous ensemble ?",
            "Quel est votre plus beau souvenir de Noël ou d'anniversaire enfant ?",
        ],
    },
    "ecole": {
        "order": 3, "label": "Mes années d'école", "emoji": "🎒",
        "description": "La classe, les copains, les maîtres, les leçons apprises.",
        "prompts": [
            "Racontez votre premier jour d'école — que ressentiez-vous ?",
            "Quel enseignant vous a le plus marqué et pourquoi ?",
            "Quelle matière préfériez-vous ? Laquelle détestiez-vous ?",
            "Une bêtise ou un exploit scolaire dont vous vous souvenez encore.",
            "Comment étaient les récréations de votre époque ?",
        ],
    },
    "adolescence": {
        "order": 4, "label": "Mon adolescence et ma jeunesse", "emoji": "💃",
        "description": "Les premières fois, la musique, les copains, les rêves.",
        "prompts": [
            "Quelle chanson vous rappelle instantanément vos 16 ans ?",
            "Comment vous habilliez-vous à 17 ans ?",
            "Décrivez votre premier flirt ou premier béguin.",
            "Une bande de copains dont vous étiez fier(ère) — qui en faisait partie ?",
            "Racontez une sortie ou un voyage marquant de vos 15-20 ans.",
        ],
    },
    "rencontres": {
        "order": 5, "label": "Mes rencontres et mes amours", "emoji": "❤️",
        "description": "Amour, amitié, mentor : les gens qui ont compté.",
        "prompts": [
            "Racontez comment vous avez rencontré votre grand amour.",
            "Quel(le) ami(e) vous a accompagné le plus longtemps ?",
            "Une personne qui vous a beaucoup appris — qui, comment ?",
            "Un premier baiser dont vous vous souvenez.",
            "Un mariage, une union ou une déclaration marquante à raconter ?",
        ],
    },
    "couple": {
        "order": 6, "label": "Ma vie de couple et ma famille", "emoji": "💍",
        "description": "Le foyer, les traditions, la vie à deux, les racines communes.",
        "prompts": [
            "Comment décririez-vous votre vie à deux, jour après jour ?",
            "Une tradition que vous avez inventée ou reprise en couple.",
            "Un fou rire ou une dispute mémorable qui a fini par vous rapprocher.",
            "Un lieu — maison, appartement — qui a compté pour votre famille.",
            "Quel conseil donneriez-vous à un jeune couple aujourd'hui ?",
        ],
    },
    "enfants": {
        "order": 7, "label": "Mes enfants et petits-enfants", "emoji": "👶",
        "description": "Les naissances, les premiers pas, les fous rires, les fiertés.",
        "prompts": [
            "Racontez la naissance de votre premier enfant (ou d'un enfant qui vous est cher).",
            "Un mot d'enfant qui vous fait encore sourire.",
            "Une fierté que vous éprouvez en pensant à vos enfants ou petits-enfants.",
            "Une tradition que vous aimez perpétuer avec eux.",
            "Un message que vous voudriez laisser à vos petits-enfants.",
        ],
    },
    "metier": {
        "order": 8, "label": "Ma vie professionnelle", "emoji": "💼",
        "description": "Les métiers exercés, les fiertés, les collègues.",
        "prompts": [
            "Quel a été votre tout premier travail ? Combien étiez-vous payé(e) ?",
            "Décrivez le métier qui vous a le plus rendu fier(ère).",
            "Un collègue ou patron dont vous vous souvenez, en bien ou en mal.",
            "Racontez un projet ou une réussite professionnelle qui vous rend fier(ère).",
            "Un lieu de travail que vous aimeriez revoir aujourd'hui — pourquoi ?",
        ],
    },
    "voyages": {
        "order": 9, "label": "Mes voyages et mes vacances", "emoji": "🧳",
        "description": "Les destinations, les aventures, les découvertes.",
        "prompts": [
            "Le voyage le plus lointain que vous ayez fait — racontez.",
            "Une destination qui vous a émerveillé(e). Pourquoi ?",
            "Une rencontre en voyage qui vous a marqué(e).",
            "Un plat ou une boisson découvert(e) à l'étranger.",
            "Où partiez-vous en vacances lorsque vous étiez enfant ?",
        ],
    },
    "passions": {
        "order": 10, "label": "Mes goûts, passions et petits bonheurs", "emoji": "🎵",
        "description": "Ce qui a fait battre votre cœur : sport, art, jardin, musique…",
        "prompts": [
            "Une passion qui vous a suivi(e) toute votre vie.",
            "Un livre, un film ou une chanson qui vous a bouleversé(e).",
            "Un savoir-faire que vous aimeriez transmettre.",
            "Un petit bonheur du quotidien auquel vous tenez.",
            "Une passion abandonnée — pourquoi et la reprendriez-vous ?",
        ],
    },
    "evenements": {
        "order": 11, "label": "Les événements qui ont marqué ma vie", "emoji": "🌍",
        "description": "Les grands moments, les épreuves traversées, les fiertés.",
        "prompts": [
            "Un événement historique que vous avez vécu — où étiez-vous ?",
            "Un moment difficile que vous avez surmonté — comment y êtes-vous parvenu(e) ?",
            "Une décision importante que vous ne regrettez pas.",
            "Une fierté personnelle dont vous parlez rarement.",
            "Un moment de joie profonde dont vous vous souvenez précisément.",
        ],
    },
    "transmission": {
        "order": 12, "label": "Ce que je veux transmettre", "emoji": "💌",
        "description": "Les messages, les recettes, les valeurs à laisser aux vôtres.",
        "prompts": [
            "Un message personnel à vos enfants ou petits-enfants.",
            "Une recette que vous voulez transmettre — décrivez-la.",
            "Trois valeurs qui vous ont porté(e) dans la vie.",
            "Un conseil que vous auriez aimé recevoir à 20 ans.",
            "Comment aimeriez-vous être rappelé(e) par vos proches ?",
        ],
    },
}


# Mapping migration : anciens chapitres → nouveaux chapitres (idempotent)
_LEGACY_CHAPTER_MAP = {
    "famille": "enfants",       # anciennes entrées "famille" → nouveau chapitre "enfants"
    "epreuves": "transmission", # "épreuves & fiertés" → "transmission" (confirmé par l'utilisateur)
}


async def _migrate_legacy_chapters() -> None:
    """Migre en douceur les entrées portant un ancien chapter_id vers le nouveau.

    Idempotent : appelée au démarrage du module, aucune duplication.
    Aucune donnée n'est supprimée, seul le chapter_id est réécrit.
    """
    for old, new in _LEGACY_CHAPTER_MAP.items():
        try:
            r = await db.livre_entries.update_many(
                {"chapter_id": old},
                {"$set": {"chapter_id": new}},
            )
            if r.modified_count:
                logger.info(f"[livre-migration] {old}→{new}: {r.modified_count} entrées migrées")
        except Exception as e:
            logger.warning(f"[livre-migration] échec {old}→{new}: {e}")



def _chapter_by_id(cid: str) -> dict | None:
    return CHAPTERS.get(cid)


def _prompt_by_id(chapter: dict, chapter_id: str, prompt_id: str) -> str | None:
    for i, p in enumerate(chapter["prompts"]):
        if prompt_id == f"{chapter_id}_p{i+1}":
            return p
    return None


# =============================================================================
# Schemas — entrées
# =============================================================================

class PhotoIn(BaseModel):
    b64: str = Field(..., max_length=2_500_000)     # ~1.8 Mo image après base64
    caption: str = Field("", max_length=200)
    who: str = Field("", max_length=100)
    where: str = Field("", max_length=100)
    when: str = Field("", max_length=50)


class EntryCreate(BaseModel):
    chapter_id: str
    prompt_id: str
    mode: str = Field("text", pattern="^(text|audio|delegated)$")
    text: str = Field("", max_length=8000)
    audio_b64: str | None = Field(None, max_length=2_500_000)  # ~1.8 Mo (env. 60 s audio)
    photos: list[PhotoIn] = Field(default_factory=list, max_length=3)
    delegated_author_name: str = Field("", max_length=60)  # nom saisi si mode=delegated
    visibility: str = Field("private", pattern="^(private|family)$")


# =============================================================================
# Endpoints — chapitres & prompts
# =============================================================================

@router.get("/chapters")
async def list_chapters(user: dict = Depends(get_current_user)) -> list[dict]:
    """Retourne les 10 chapitres avec compteur d'entrées de l'utilisateur."""
    user_id = str(user["_id"])
    entries = await db.livre_entries.aggregate([
        {"$match": {"user_id": user_id}},
        {"$group": {"_id": "$chapter_id", "count": {"$sum": 1}}},
    ]).to_list(50)
    counts = {e["_id"]: e["count"] for e in entries}
    out = []
    for cid, c in sorted(CHAPTERS.items(), key=lambda kv: kv[1]["order"]):
        out.append({
            "id": cid,
            "order": c["order"],
            "label": c["label"],
            "emoji": c["emoji"],
            "description": c["description"],
            "n_prompts": len(c["prompts"]),
            "n_written": counts.get(cid, 0),
        })
    return out


@router.get("/chapters/{chapter_id}")
async def get_chapter(chapter_id: str, user: dict = Depends(get_current_user)) -> dict:
    ch = _chapter_by_id(chapter_id)
    if not ch:
        raise HTTPException(status_code=404, detail="Chapitre introuvable")
    user_id = str(user["_id"])
    # Charge les entrées existantes pour ce chapitre
    docs = await db.livre_entries.find(
        {"user_id": user_id, "chapter_id": chapter_id},
        {"_id": 0},
    ).sort("created_at", 1).to_list(200)
    return {
        "id": chapter_id,
        "label": ch["label"],
        "emoji": ch["emoji"],
        "description": ch["description"],
        "prompts": [
            {"id": f"{chapter_id}_p{i+1}", "text": p}
            for i, p in enumerate(ch["prompts"])
        ],
        "entries": docs,
    }


# =============================================================================
# Endpoints — création / lecture entrée
# =============================================================================

@router.post("/entries")
async def create_entry(body: EntryCreate, user: dict = Depends(get_current_user)) -> dict:
    ch = _chapter_by_id(body.chapter_id)
    if not ch:
        raise HTTPException(status_code=400, detail="Chapitre inconnu")
    prompt_text = _prompt_by_id(ch, body.chapter_id, body.prompt_id)
    if not prompt_text:
        raise HTTPException(status_code=400, detail="Prompt inconnu")
    if body.mode == "text" and not body.text.strip():
        raise HTTPException(status_code=400, detail="Texte vide")
    if body.mode == "audio" and not body.audio_b64:
        raise HTTPException(status_code=400, detail="Enregistrement audio manquant")

    user_id = str(user["_id"])
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "chapter_id": body.chapter_id,
        "prompt_id": body.prompt_id,
        "prompt_text": prompt_text,
        "mode": body.mode,
        "text": body.text.strip(),
        "audio_b64": body.audio_b64,
        "photos": [p.model_dump() for p in body.photos],
        "author_user_id": user_id,
        "delegated_author_name": body.delegated_author_name.strip() if body.mode == "delegated" else "",
        "visibility": body.visibility,
        "created_at": now,
        "updated_at": now,
    }
    await db.livre_entries.insert_one(doc)

    # Progression douce : +10 XP par souvenir (pas de score, juste une reconnaissance)
    XP_ENTRY = 10
    await db.users.update_one({"_id": user["_id"]}, {"$inc": {"xp_total": XP_ENTRY}})

    # Renvoie sans le _id de Mongo
    doc.pop("_id", None)
    return {"ok": True, "entry": doc, "xp_gained": XP_ENTRY}


@router.get("/entries")
async def list_entries(user: dict = Depends(get_current_user)) -> dict:
    """Vue Livre : tous les souvenirs regroupés par chapitre, ordre chronologique."""
    user_id = str(user["_id"])
    docs = await db.livre_entries.find(
        {"user_id": user_id}, {"_id": 0},
    ).sort("created_at", 1).to_list(2000)

    grouped: dict[str, list] = {}
    for d in docs:
        grouped.setdefault(d["chapter_id"], []).append(d)

    chapters_out = []
    for cid, c in sorted(CHAPTERS.items(), key=lambda kv: kv[1]["order"]):
        entries = grouped.get(cid, [])
        chapters_out.append({
            "id": cid, "order": c["order"], "label": c["label"], "emoji": c["emoji"],
            "n_written": len(entries),
            "entries": entries,
        })
    total_entries = len(docs)
    total_prompts = sum(len(c["prompts"]) for c in CHAPTERS.values())
    return {
        "total_entries": total_entries,
        "total_prompts": total_prompts,
        "progress_pct": int(round(total_entries / total_prompts * 100)) if total_prompts else 0,
        "chapters": chapters_out,
    }


# =============================================================================
# Souvenir du jour — un prompt aléatoire chaque jour pour le dashboard
# =============================================================================

@router.get("/souvenir-du-jour")
async def souvenir_du_jour(user: dict = Depends(get_current_user)) -> dict:
    """Prompt aléatoire déterministe basé sur la date + user_id (stable dans la journée)."""
    import hashlib
    user_id = str(user["_id"])
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    seed = int(hashlib.sha256(f"{user_id}:{today}".encode()).hexdigest(), 16)
    # Pick chapitre + prompt déterministe
    chapter_ids = sorted(CHAPTERS.keys(), key=lambda k: CHAPTERS[k]["order"])
    cid = chapter_ids[seed % len(chapter_ids)]
    ch = CHAPTERS[cid]
    idx = (seed >> 5) % len(ch["prompts"])
    return {
        "chapter_id": cid,
        "chapter_label": ch["label"],
        "chapter_emoji": ch["emoji"],
        "prompt_id": f"{cid}_p{idx+1}",
        "prompt_text": ch["prompts"][idx],
    }


# =============================================================================
# Progression — statistiques agrégées pour le widget Dashboard "Livre en construction"
# =============================================================================

# Constante utilisée pour estimer le nombre de pages du futur livre imprimé.
# ~180 mots par page A5 en interligne confortable ; +1 page par photo (mise en pleine page).
_WORDS_PER_PAGE = 180
_PAGES_PER_PHOTO = 1
_FRONT_MATTER_PAGES = 6   # titre + sommaire + intro + fin


@router.get("/progression")
async def livre_progression(user: dict = Depends(get_current_user)) -> dict:
    """Agrégats du Livre de Vie pour le widget Dashboard.

    Retourne : souvenirs racontés, photos ajoutées, chapitres au moins entamés,
    chapitres complétés (tous les prompts remplis), estimation du nombre de
    pages, et progression 0-100.
    """
    user_id = str(user["_id"])
    entries = await db.livre_entries.find(
        {"user_id": user_id}, {"chapter_id": 1, "prompt_id": 1, "text": 1, "photos": 1},
    ).to_list(2000)

    total_entries = len(entries)
    total_photos = sum(len(e.get("photos") or []) for e in entries)
    total_words = sum(len((e.get("text") or "").split()) for e in entries)

    # Chapitres entamés / complétés
    by_chapter: dict[str, set] = {}
    for e in entries:
        by_chapter.setdefault(e["chapter_id"], set()).add(e.get("prompt_id"))
    chapters_started = len(by_chapter)
    chapters_completed = sum(
        1 for cid, prompt_ids in by_chapter.items()
        if _chapter_by_id(cid) and len(prompt_ids) >= len(_chapter_by_id(cid)["prompts"])  # type: ignore
    )

    # Estimation de pages
    est_pages = _FRONT_MATTER_PAGES + max(1, total_words // _WORDS_PER_PAGE) + total_photos * _PAGES_PER_PHOTO

    # Progression globale : moyenne (prompts remplis) / (prompts totaux)
    total_prompts = sum(len(c["prompts"]) for c in CHAPTERS.values())
    filled_prompts = sum(len(pids) for pids in by_chapter.values())
    percent = min(100, round((filled_prompts / total_prompts) * 100)) if total_prompts else 0

    return {
        "total_entries": total_entries,
        "total_photos": total_photos,
        "total_words": total_words,
        "chapters_started": chapters_started,
        "chapters_completed": chapters_completed,
        "chapters_total": len(CHAPTERS),
        "estimated_pages": est_pages,
        "progression_percent": percent,
    }



# =============================================================================
# Boucle Quiz → Livre : "Cette question vous rappelle un souvenir ?"
# =============================================================================
# Mapping catégorie de quiz → chapitre du Livre où classer automatiquement le
# souvenir. Toute catégorie non listée retombe sur "passions" (fourre-tout).
_CATEGORY_TO_CHAPTER: dict[str, str] = {
    "chansons": "passions",
    "cinema": "passions",
    "culture-70-ans": "passions",
    "culture-40-ans": "passions",
    "cuisine-terroir": "passions",
    "voyages-france": "voyages",
    "histoire-france": "evenements",
    "annees-50-60": "adolescence",
    "objets-antan": "enfance",
}


class QuizMemoryBody(BaseModel):
    quiz_question_id: str = Field(..., min_length=1, max_length=100)
    category_slug: str = Field(..., min_length=1, max_length=80)
    question_text: str = Field(..., min_length=1, max_length=500)
    memory_text: str = Field(..., min_length=1, max_length=4000)


@router.post("/from-quiz")
async def livre_from_quiz(body: QuizMemoryBody, user: dict = Depends(get_current_user)) -> dict:
    """Crée une entrée dans le Livre de Vie à partir d'un souvenir déclenché
    par une question de quiz. Le chapitre est déduit automatiquement de la
    catégorie de quiz via `_CATEGORY_TO_CHAPTER`.
    """
    chapter_id = _CATEGORY_TO_CHAPTER.get(body.category_slug, "passions")
    ch = _chapter_by_id(chapter_id)
    if not ch:
        raise HTTPException(status_code=500, detail="Chapitre invalide")

    now = datetime.now(timezone.utc).isoformat()
    entry = {
        "id": str(uuid.uuid4()),
        "user_id": str(user["_id"]),
        "chapter_id": chapter_id,
        "prompt_id": f"quiz_{body.quiz_question_id}",
        "prompt_text": body.question_text.strip(),
        "mode": "text",
        "text": body.memory_text.strip(),
        "audio_b64": None,
        "photos": [],
        "author_user_id": str(user["_id"]),
        "delegated_author_name": None,
        "visibility": "family",
        "source": "quiz",                       # trace : d'où vient ce souvenir
        "quiz_question_id": body.quiz_question_id,
        "quiz_category_slug": body.category_slug,
        "created_at": now,
        "updated_at": now,
    }
    await db.livre_entries.insert_one(entry)
    entry.pop("_id", None)
    return {"ok": True, "entry": entry, "chapter_id": chapter_id, "chapter_label": ch["label"]}



# =============================================================================
# Famille — Questions posées entre proches
# =============================================================================

class FamilyQuestionCreate(BaseModel):
    to_email: str = Field(..., max_length=200)
    question: str = Field(..., min_length=5, max_length=300)


@router.post("/family/questions")
async def send_family_question(body: FamilyQuestionCreate, user: dict = Depends(get_current_user)) -> dict:
    """Un(e) petit-enfant envoie une question à un grand-parent (par e-mail)."""
    from_user_id = str(user["_id"])
    to = await db.users.find_one({"email": body.to_email.strip().lower()})
    if not to:
        raise HTTPException(status_code=404, detail="Aucun compte trouvé avec cet e-mail")
    if str(to["_id"]) == from_user_id:
        raise HTTPException(status_code=400, detail="Vous ne pouvez pas vous envoyer une question à vous-même")
    doc = {
        "id": str(uuid.uuid4()),
        "from_user_id": from_user_id,
        "from_user_name": user.get("name") or user.get("email", "").split("@")[0],
        "to_user_id": str(to["_id"]),
        "question": body.question.strip(),
        "response_entry_id": None,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "answered_at": None,
    }
    await db.family_questions.insert_one(doc)
    doc.pop("_id", None)
    return {"ok": True, "question": doc}


@router.get("/family/questions/inbox")
async def inbox(user: dict = Depends(get_current_user)) -> list[dict]:
    """Questions reçues (à répondre)."""
    user_id = str(user["_id"])
    docs = await db.family_questions.find(
        {"to_user_id": user_id}, {"_id": 0},
    ).sort("created_at", -1).to_list(100)
    return docs


@router.get("/family/questions/sent")
async def sent(user: dict = Depends(get_current_user)) -> list[dict]:
    """Questions envoyées (pour suivre les réponses)."""
    user_id = str(user["_id"])
    docs = await db.family_questions.find(
        {"from_user_id": user_id}, {"_id": 0},
    ).sort("created_at", -1).to_list(100)
    return docs


class AnswerQuestion(BaseModel):
    question_id: str
    entry_id: str


@router.post("/family/questions/answer")
async def answer_question(body: AnswerQuestion, user: dict = Depends(get_current_user)) -> dict:
    """Lie une entrée déjà créée à une question de famille (marque comme answered)."""
    user_id = str(user["_id"])
    q = await db.family_questions.find_one({"id": body.question_id, "to_user_id": user_id})
    if not q:
        raise HTTPException(status_code=404, detail="Question introuvable")
    entry = await db.livre_entries.find_one({"id": body.entry_id, "user_id": user_id})
    if not entry:
        raise HTTPException(status_code=404, detail="Souvenir introuvable")
    await db.family_questions.update_one(
        {"id": body.question_id},
        {"$set": {
            "response_entry_id": body.entry_id,
            "status": "answered",
            "answered_at": datetime.now(timezone.utc).isoformat(),
        }},
    )
    return {"ok": True}


# =============================================================================
# Famille — Membres & permissions (invitations, ébauche pour V1)
# =============================================================================

class FamilyInvite(BaseModel):
    invitee_email: str = Field(..., max_length=200)
    permission: str = Field("view", pattern="^(view|comment|contribute|manage)$")


@router.post("/family/invite")
async def invite_member(body: FamilyInvite, user: dict = Depends(get_current_user)) -> dict:
    """Crée une invitation famille avec un jeton unique.

    L'e-mail est optionnellement envoyé via Resend (non bloquant).
    """
    owner_id = str(user["_id"])
    invitee = body.invitee_email.strip().lower()
    # Vérifie qu'aucune invitation active n'existe déjà
    existing = await db.family_members.find_one({
        "owner_id": owner_id, "invitee_email": invitee, "status": {"$in": ["invited", "accepted"]},
    })
    if existing:
        raise HTTPException(status_code=400, detail="Cette personne est déjà invitée")
    token = secrets.token_urlsafe(24)
    doc = {
        "id": str(uuid.uuid4()),
        "owner_id": owner_id,
        "invitee_email": invitee,
        "invitee_user_id": None,
        "permission": body.permission,
        "status": "invited",
        "token": token,
        "invited_at": datetime.now(timezone.utc).isoformat(),
        "accepted_at": None,
    }
    await db.family_members.insert_one(doc)
    doc.pop("_id", None)
    return {"ok": True, "invite": doc}


@router.get("/family/members")
async def my_family(user: dict = Depends(get_current_user)) -> list[dict]:
    owner_id = str(user["_id"])
    docs = await db.family_members.find(
        {"owner_id": owner_id, "status": {"$in": ["invited", "accepted"]}},
        {"_id": 0, "token": 0},
    ).sort("invited_at", -1).to_list(100)
    return docs


@router.delete("/family/members/{member_id}")
async def revoke_member(member_id: str, user: dict = Depends(get_current_user)) -> dict:
    owner_id = str(user["_id"])
    r = await db.family_members.update_one(
        {"id": member_id, "owner_id": owner_id},
        {"$set": {"status": "revoked"}},
    )
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Membre introuvable")
    return {"ok": True}


# =============================================================================
# Whisper — transcription automatique d'un enregistrement audio base64
# =============================================================================

class TranscribeIn(BaseModel):
    audio_b64: str = Field(..., max_length=3_500_000)


@router.post("/transcribe")
async def transcribe(body: TranscribeIn, user: dict = Depends(get_current_user)) -> dict:
    """Transcrit un audio base64 (webm/mp3/wav) en français via OpenAI Whisper.

    Utilise l'EMERGENT_LLM_KEY : coût facturé au user Emergent, aucun compte
    OpenAI direct requis. Le fichier est encapsulé en BytesIO et passé au SDK.
    """
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="Service de transcription indisponible")
    try:
        from emergentintegrations.llm.openai import OpenAISpeechToText
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Module STT absent : {e}")
    try:
        raw = base64.b64decode(body.audio_b64)
    except Exception:
        raise HTTPException(status_code=400, detail="Audio base64 invalide")
    if len(raw) > 5_000_000:
        raise HTTPException(status_code=400, detail="Audio trop lourd (max ~5 Mo)")

    # BytesIO doit avoir un attribut `name` avec une extension supportée sinon
    # l'API OpenAI refuse.
    audio_file = io.BytesIO(raw)
    audio_file.name = "souvenir.webm"

    stt = OpenAISpeechToText(api_key=api_key)
    try:
        resp = await stt.transcribe(
            file=audio_file,
            model="whisper-1",
            response_format="json",
            language="fr",
            temperature=0.0,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Transcription impossible : {e}")
    transcript = getattr(resp, "text", "") or ""
    return {"transcript": transcript.strip()}


# =============================================================================
# PDF — export téléchargeable du Livre de Vie
# =============================================================================

@router.get("/export/pdf")
async def export_pdf(user: dict = Depends(get_current_user)) -> StreamingResponse:
    """Génère un PDF simple mais chaleureux du Livre de Vie de l'utilisateur.

    Structure : couverture (nom + tagline + date) → sommaire des chapitres →
    pour chaque chapitre : bandeau titre + toutes les entrées (texte ou
    transcription si audio) avec date. Les photos et audios sont exclus (V2).
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib.colors import HexColor
    from reportlab.lib.enums import TA_CENTER
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image as RLImage,
    )

    user_id = str(user["_id"])
    docs = await db.livre_entries.find({"user_id": user_id}, {"_id": 0}).sort("created_at", 1).to_list(2000)
    if not docs:
        raise HTTPException(status_code=400, detail="Votre Livre est encore vide")

    grouped: dict[str, list] = {}
    for d in docs:
        grouped.setdefault(d["chapter_id"], []).append(d)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        rightMargin=2.2 * cm, leftMargin=2.2 * cm,
        topMargin=2.4 * cm, bottomMargin=2 * cm,
        title=f"Mon Livre de Vie - {user.get('name', '')}",
        author=user.get("name") or user.get("email", ""),
    )
    styles = getSampleStyleSheet()
    navy = HexColor("#1E3A5F")
    terracotta = HexColor("#E07A5F")
    styles.add(ParagraphStyle("CoverTitle", parent=styles["Title"], fontSize=42, leading=48, alignment=TA_CENTER, textColor=terracotta, spaceAfter=20))
    styles.add(ParagraphStyle("CoverSub", parent=styles["Normal"], fontSize=16, leading=22, alignment=TA_CENTER, textColor=navy, spaceAfter=12))
    styles.add(ParagraphStyle("ChapterTitle", parent=styles["Heading1"], fontSize=24, leading=28, textColor=terracotta, spaceBefore=6, spaceAfter=14))
    styles.add(ParagraphStyle("PromptQ", parent=styles["Italic"], fontSize=12, leading=16, textColor=navy, spaceAfter=6))
    styles.add(ParagraphStyle("EntryTxt", parent=styles["Normal"], fontSize=11, leading=17, spaceAfter=14))

    story: list = []
    # === Couverture ===
    story.append(Spacer(1, 6 * cm))
    story.append(Paragraph("Mon Livre de Vie", styles["CoverTitle"]))
    story.append(Paragraph(f"— {user.get('name') or user.get('email','').split('@')[0]} —", styles["CoverSub"]))
    story.append(Spacer(1, 2 * cm))
    story.append(Paragraph("<i>Mes souvenirs. Mon histoire.<br/>Pour ceux que j&apos;aime.</i>", styles["CoverSub"]))
    story.append(Spacer(1, 3 * cm))
    story.append(Paragraph(datetime.now().strftime("%B %Y").capitalize(), styles["CoverSub"]))
    story.append(PageBreak())

    # === Chapitres ===
    for cid, c in sorted(CHAPTERS.items(), key=lambda kv: kv[1]["order"]):
        entries = grouped.get(cid, [])
        if not entries:
            continue

        # Couverture de chapitre en pleine page (si générée)
        cover_path = COVERS_DIR / f"{cid}.png"
        if cover_path.exists() and cover_path.stat().st_size > 5000:
            story.append(Spacer(1, 2 * cm))
            try:
                img = RLImage(str(cover_path), width=12 * cm, height=12 * cm, kind="proportional", hAlign="CENTER")
                story.append(img)
            except Exception:
                pass
            story.append(Spacer(1, 1 * cm))

        story.append(Paragraph(f"{c['emoji']} {c['label']}", styles["ChapterTitle"]))
        story.append(Paragraph(f"<i>{c['description']}</i>", styles["PromptQ"]))
        story.append(Spacer(1, 0.5 * cm))

        for e in entries:
            story.append(Paragraph(e.get("prompt_text", ""), styles["PromptQ"]))
            txt = (e.get("text") or "").replace("\n", "<br/>")
            if not txt and e.get("mode") == "audio":
                txt = "<i>(souvenir enregistré en audio, non transcrit)</i>"
            when = e.get("created_at", "")[:10]
            author = ""
            if e.get("mode") == "delegated" and e.get("delegated_author_name"):
                author = f' <font color="#722F37">— raconté par {e["delegated_author_name"]}</font>'
            story.append(Paragraph(f'{txt}<br/><font size="8" color="#888">{when}{author}</font>', styles["EntryTxt"]))

            # Photos du souvenir (jusqu'à 3, ~6×6 cm chacune)
            photos = e.get("photos") or []
            if photos:
                photo_flowables = []
                for ph in photos[:3]:
                    try:
                        img_bytes = base64.b64decode(ph.get("b64", ""))
                        img_io = io.BytesIO(img_bytes)
                        rl_img = RLImage(img_io, width=5.5 * cm, height=5.5 * cm, kind="proportional")
                        photo_flowables.append(rl_img)
                    except Exception:
                        continue
                if photo_flowables:
                    from reportlab.platypus import Table, TableStyle
                    tbl = Table([photo_flowables], colWidths=[6 * cm] * len(photo_flowables))
                    tbl.setStyle(TableStyle([
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 4),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ]))
                    story.append(tbl)
                    # Légendes des photos si présentes
                    captions = [ph.get("caption", "") for ph in photos[:3]]
                    if any(captions):
                        cap_txt = " · ".join(c for c in captions if c) or ""
                        if cap_txt:
                            story.append(Paragraph(f'<font size="8" color="#666"><i>{cap_txt}</i></font>', styles["EntryTxt"]))
                    story.append(Spacer(1, 0.4 * cm))

        story.append(PageBreak())

    doc.build(story)
    buf.seek(0)
    filename = f"livre-de-vie-{datetime.now().strftime('%Y%m%d')}.pdf"
    return StreamingResponse(
        buf, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# =============================================================================
# Quiz Memory Triggers — mapping catégorie de quiz → chapitre du Livre
# =============================================================================

# Association manuelle : quelle catégorie de quiz "invite" à raconter quel
# chapitre du Livre ? Utilisé côté front en fin de quiz pour proposer un CTA
# doux "Vous avez un souvenir à raconter à ce sujet ?".
QUIZ_MEMORY_MAP: dict[str, dict] = {
    "annees-50-60":     {"chapter_id": "adolescence", "prompt_hint": "Quelle chanson vous rappelle vos 20 ans ?"},
    "annees-70":        {"chapter_id": "adolescence", "prompt_hint": "Quelle mode ou musique des années 70 vous représentait ?"},
    "annees-80":        {"chapter_id": "metier",      "prompt_hint": "Racontez votre premier travail ou votre bureau des années 80."},
    "chansons":         {"chapter_id": "adolescence", "prompt_hint": "Quelle chanson vous fait fondre à chaque écoute ?"},
    "cinema":           {"chapter_id": "passions",    "prompt_hint": "Un film qui vous a bouleversé — racontez."},
    "cuisine":          {"chapter_id": "enfance",     "prompt_hint": "Une odeur ou un plat de votre enfance ?"},
    "sport":            {"chapter_id": "passions",    "prompt_hint": "Un moment de sport dont vous êtes fier(ère) ?"},
    "geographie":       {"chapter_id": "voyages",     "prompt_hint": "Une destination qui vous a émerveillé(e) ?"},
    "voyages-france":   {"chapter_id": "voyages",     "prompt_hint": "Où passiez-vous vos vacances quand vous étiez jeune ?"},
    "histoire":         {"chapter_id": "evenements", "prompt_hint": "Un événement historique que vous avez vécu — racontez."},
    "litterature":      {"chapter_id": "passions",    "prompt_hint": "Un livre qui vous a marqué(e) ?"},
    "sciences":         {"chapter_id": "ecole",       "prompt_hint": "Une matière ou expérience qui vous a fasciné(e) à l'école ?"},
    "personnages":      {"chapter_id": "rencontres",  "prompt_hint": "Une personnalité que vous auriez aimé rencontrer ?"},
}


@router.get("/memory-trigger/{category_slug}")
async def memory_trigger(category_slug: str, user: dict = Depends(get_current_user)) -> dict:
    """Renvoie le chapitre + prompt-hint associé à une catégorie de quiz.
    Le front l'affiche en fin de quiz comme CTA doux vers le Livre.
    """
    mapping = QUIZ_MEMORY_MAP.get(category_slug)
    if not mapping:
        return {"has_trigger": False}
    ch = CHAPTERS.get(mapping["chapter_id"])
    if not ch:
        return {"has_trigger": False}
    return {
        "has_trigger": True,
        "chapter_id": mapping["chapter_id"],
        "chapter_label": ch["label"],
        "chapter_emoji": ch["emoji"],
        "prompt_hint": mapping["prompt_hint"],
    }


# =============================================================================
# Couvertures illustrées — expose les URLs statiques par chapitre
# =============================================================================

COVERS_DIR = Path(__file__).parent.parent / "static" / "livre_covers"


@router.get("/covers")
async def list_covers() -> dict:
    """Retourne pour chaque chapitre l'URL de sa couverture (si générée)."""
    out = {}
    for cid in CHAPTERS.keys():
        path = COVERS_DIR / f"{cid}.png"
        if path.exists() and path.stat().st_size > 5000:
            out[cid] = f"/api/static/livre_covers/{cid}.png"
    return out


# =============================================================================
# Coop Atelier — session partagée grand-parent ↔ petit-enfant
# =============================================================================
# Le propriétaire du Livre (grand-parent connecté) ouvre une session coop
# pour un chapitre donné. Il obtient un code d'invitation à 6 caractères et
# un lien partageable. Le petit-enfant rejoint sans compte, saisit son nom,
# et peut alors ajouter des souvenirs qui s'ajoutent au Livre du grand-parent
# (attribution automatique en mode "delegated"). Sync via polling léger.


class CoopCreate(BaseModel):
    chapter_id: str


class CoopJoin(BaseModel):
    code: str = Field(..., min_length=6, max_length=8)
    guest_name: str = Field(..., min_length=1, max_length=60)


class CoopHeartbeat(BaseModel):
    guest_name: str = Field(..., min_length=1, max_length=60)


class CoopEntry(BaseModel):
    prompt_id: str
    guest_name: str = Field(..., min_length=1, max_length=60)
    text: str = Field(..., min_length=1, max_length=8000)


def _gen_invite_code() -> str:
    """6 caractères non ambigus (pas de 0/O/I/1)."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(6))


async def _find_session(code: str) -> dict | None:
    return await db.livre_coop_sessions.find_one({"invite_code": code.upper()})


@router.post("/coop/create")
async def coop_create(body: CoopCreate, user: dict = Depends(get_current_user)) -> dict:
    """Crée une session coop pour un chapitre. Réutilise le code existant si actif."""
    ch = _chapter_by_id(body.chapter_id)
    if not ch:
        raise HTTPException(status_code=400, detail="Chapitre inconnu")
    owner_id = str(user["_id"])
    now = datetime.now(timezone.utc)
    # Réutilise une session active existante pour ce chapitre (idempotent)
    existing = await db.livre_coop_sessions.find_one({
        "owner_user_id": owner_id,
        "chapter_id": body.chapter_id,
        "status": "active",
    })
    if existing:
        existing.pop("_id", None)
        return {"ok": True, "session": existing, "reused": True}

    # Génère un code unique (retry si collision improbable)
    for _ in range(5):
        code = _gen_invite_code()
        if not await db.livre_coop_sessions.find_one({"invite_code": code}):
            break
    else:
        raise HTTPException(status_code=500, detail="Impossible de générer un code")

    owner_name = user.get("name") or user.get("email", "").split("@")[0]
    doc = {
        "id": str(uuid.uuid4()),
        "owner_user_id": owner_id,
        "owner_name": owner_name,
        "chapter_id": body.chapter_id,
        "chapter_label": ch["label"],
        "chapter_emoji": ch["emoji"],
        "invite_code": code,
        "status": "active",
        "participants": [
            {"name": owner_name, "is_owner": True, "joined_at": now.isoformat(), "last_seen": now.isoformat()},
        ],
        "created_at": now.isoformat(),
    }
    await db.livre_coop_sessions.insert_one(doc)
    doc.pop("_id", None)
    return {"ok": True, "session": doc, "reused": False}


@router.get("/coop/mine")
async def coop_mine(user: dict = Depends(get_current_user)) -> list[dict]:
    """Liste des sessions coop actives du propriétaire connecté."""
    owner_id = str(user["_id"])
    docs = await db.livre_coop_sessions.find(
        {"owner_user_id": owner_id, "status": "active"}, {"_id": 0},
    ).sort("created_at", -1).to_list(50)
    return docs


@router.post("/coop/{code}/close")
async def coop_close(code: str, user: dict = Depends(get_current_user)) -> dict:
    """Le propriétaire ferme la session coop."""
    owner_id = str(user["_id"])
    r = await db.livre_coop_sessions.update_one(
        {"invite_code": code.upper(), "owner_user_id": owner_id, "status": "active"},
        {"$set": {"status": "closed", "closed_at": datetime.now(timezone.utc).isoformat()}},
    )
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Session introuvable")
    return {"ok": True}


@router.post("/coop/join")
async def coop_join(body: CoopJoin) -> dict:
    """Un invité rejoint via le code. Ajoute son nom aux participants."""
    sess = await _find_session(body.code)
    if not sess or sess.get("status") != "active":
        raise HTTPException(status_code=404, detail="Session introuvable ou fermée")
    guest = body.guest_name.strip()
    now = datetime.now(timezone.utc).isoformat()
    # Ajoute le participant s'il n'est pas déjà présent (case-insensitive)
    participants = sess.get("participants", [])
    known = any(p["name"].lower() == guest.lower() for p in participants)
    if not known:
        await db.livre_coop_sessions.update_one(
            {"_id": sess["_id"]},
            {"$push": {"participants": {
                "name": guest, "is_owner": False, "joined_at": now, "last_seen": now,
            }}},
        )
    else:
        await db.livre_coop_sessions.update_one(
            {"_id": sess["_id"], "participants.name": {"$regex": f"^{guest}$", "$options": "i"}},
            {"$set": {"participants.$.last_seen": now}},
        )
    sess = await _find_session(body.code)
    sess.pop("_id", None)
    return {"ok": True, "session": sess}


@router.get("/coop/{code}/state")
async def coop_state(code: str) -> dict:
    """État courant : chapitre, prompts, souvenirs et participants.

    Endpoint public (pas d'auth) pour permettre au petit-enfant de suivre en
    temps réel sans compte. Ne renvoie que les entrées du chapitre concerné.
    """
    sess = await _find_session(code)
    if not sess:
        raise HTTPException(status_code=404, detail="Session introuvable")
    if sess.get("status") != "active":
        raise HTTPException(status_code=410, detail="Session fermée")
    ch = _chapter_by_id(sess["chapter_id"])
    if not ch:
        raise HTTPException(status_code=500, detail="Chapitre invalide")
    entries = await db.livre_entries.find(
        {"user_id": sess["owner_user_id"], "chapter_id": sess["chapter_id"]},
        {"_id": 0, "audio_b64": 0},  # allège la payload : pas de blob audio en polling
    ).sort("created_at", 1).to_list(500)
    return {
        "session_id": sess["id"],
        "owner_name": sess["owner_name"],
        "chapter": {
            "id": sess["chapter_id"],
            "label": ch["label"],
            "emoji": ch["emoji"],
            "description": ch["description"],
            "prompts": [{"id": f"{sess['chapter_id']}_p{i+1}", "text": p} for i, p in enumerate(ch["prompts"])],
        },
        "entries": entries,
        "participants": sess.get("participants", []),
    }


@router.post("/coop/{code}/heartbeat")
async def coop_heartbeat(code: str, body: CoopHeartbeat) -> dict:
    """Met à jour last_seen pour un participant (garde la présence à jour)."""
    sess = await _find_session(code)
    if not sess or sess.get("status") != "active":
        raise HTTPException(status_code=404, detail="Session introuvable")
    now = datetime.now(timezone.utc).isoformat()
    await db.livre_coop_sessions.update_one(
        {"_id": sess["_id"], "participants.name": {"$regex": f"^{body.guest_name.strip()}$", "$options": "i"}},
        {"$set": {"participants.$.last_seen": now}},
    )
    return {"ok": True}


@router.post("/coop/{code}/entry")
async def coop_entry(code: str, body: CoopEntry) -> dict:
    """L'invité (petit-enfant) écrit un souvenir. Crée une entrée `delegated`
    dans le Livre du propriétaire, attribuée au prénom de l'invité.
    """
    sess = await _find_session(code)
    if not sess or sess.get("status") != "active":
        raise HTTPException(status_code=404, detail="Session introuvable ou fermée")
    chapter_id = sess["chapter_id"]
    ch = _chapter_by_id(chapter_id)
    if not ch:
        raise HTTPException(status_code=500, detail="Chapitre invalide")
    prompt_text = _prompt_by_id(ch, chapter_id, body.prompt_id)
    if not prompt_text:
        raise HTTPException(status_code=400, detail="Prompt inconnu")
    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Texte vide")

    now = datetime.now(timezone.utc).isoformat()
    entry = {
        "id": str(uuid.uuid4()),
        "user_id": sess["owner_user_id"],           # rattaché au Livre du grand-parent
        "chapter_id": chapter_id,
        "prompt_id": body.prompt_id,
        "prompt_text": prompt_text,
        "mode": "delegated",
        "text": text,
        "audio_b64": None,
        "photos": [],
        "author_user_id": None,                     # pas de compte pour l'invité
        "delegated_author_name": body.guest_name.strip(),
        "visibility": "family",
        "coop_session_code": sess["invite_code"],   # trace : d'où vient ce souvenir
        "created_at": now,
        "updated_at": now,
    }
    await db.livre_entries.insert_one(entry)
    entry.pop("_id", None)
    # Update last_seen de l'invité
    await db.livre_coop_sessions.update_one(
        {"_id": sess["_id"], "participants.name": {"$regex": f"^{body.guest_name.strip()}$", "$options": "i"}},
        {"$set": {"participants.$.last_seen": now}},
    )
    return {"ok": True, "entry": entry}
