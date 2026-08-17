"""Mon Livre de Vie — module de mémoire intergénérationnelle.

Refonte de l'ancien Atelier Mémoire. Structure en 10 chapitres progressifs,
3 modes de saisie (texte / audio / famille délégué), photos, permissions
familiales et questions envoyées entre membres.

Data model
----------
livre_entries (nouvelle collection, remplace progressivement atelier_entries)
  {
    id, user_id,
    chapter_id: "enfance" | "ecole" | …,
    prompt_id: str,
    prompt_text: str,          # dénormalisé pour évolution future des prompts
    mode: "text" | "audio" | "delegated",
    text: str,                 # transcription si audio, texte si écrit
    audio_b64: str | None,     # base64 mp3/webm, jusqu'à ~1 Mo (MVP)
    photos: [{b64, caption, who, where, when}],
    author_user_id: str,       # peut différer de user_id si "raconté avec la famille"
    visibility: "private" | "family",
    created_at, updated_at
  }

family_members (partage du Livre de Vie)
  {
    id, owner_id, invitee_email, invitee_user_id | None,
    permission: "view" | "comment" | "contribute" | "manage",
    status: "invited" | "accepted" | "revoked",
    invited_at, accepted_at | None, token: str
  }

family_questions (question posée par un proche)
  {
    id, from_user_id, to_user_id, question: str,
    response_entry_id: str | None,
    status: "pending" | "answered",
    created_at, answered_at | None
  }
"""
from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core import db, get_current_user


router = APIRouter(prefix="/livre", tags=["livre"])


# =============================================================================
# Bibliothèque des 10 chapitres avec prompts guidés
# =============================================================================
CHAPTERS: dict[str, dict] = {
    "enfance": {
        "order": 1, "label": "Mon enfance", "emoji": "🍼",
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
        "order": 2, "label": "L'école & les études", "emoji": "🎒",
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
        "order": 3, "label": "L'adolescence", "emoji": "🎵",
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
        "order": 4, "label": "Les grandes rencontres", "emoji": "💑",
        "description": "Amour, amitié, mentor : les gens qui ont compté.",
        "prompts": [
            "Racontez comment vous avez rencontré votre grand amour.",
            "Quel(le) ami(e) vous a accompagné le plus longtemps ?",
            "Une personne qui vous a beaucoup appris — qui, comment ?",
            "Un premier baiser dont vous vous souvenez.",
            "Un mariage, une union ou une déclaration marquante à raconter ?",
        ],
    },
    "metier": {
        "order": 5, "label": "Ma vie professionnelle", "emoji": "👷",
        "description": "Les métiers exercés, les fiertés, les collègues.",
        "prompts": [
            "Quel a été votre tout premier travail ? Combien étiez-vous payé(e) ?",
            "Décrivez le métier qui vous a le plus rendu fier(ère).",
            "Un collègue ou patron dont vous vous souvenez, en bien ou en mal.",
            "Racontez un projet ou une réussite professionnelle qui vous rend fier(ère).",
            "Un lieu de travail que vous aimeriez revoir aujourd'hui — pourquoi ?",
        ],
    },
    "famille": {
        "order": 6, "label": "Ma famille", "emoji": "👨‍👩‍👧‍👦",
        "description": "Enfants, parents, grands-parents, cousinades.",
        "prompts": [
            "Racontez la naissance de votre premier enfant (ou d'un enfant qui vous est cher).",
            "Une tradition familiale à laquelle vous tenez.",
            "Un souvenir avec vos parents que vous voulez transmettre.",
            "Une réunion de famille marquante.",
            "Un message que vous voudriez laisser à vos petits-enfants.",
        ],
    },
    "voyages": {
        "order": 7, "label": "Mes voyages", "emoji": "✈️",
        "description": "Les destinations, les aventures, les découvertes.",
        "prompts": [
            "Le voyage le plus lointain que vous ayez fait — racontez.",
            "Une destination qui vous a émerveillé(e). Pourquoi ?",
            "Une rencontre en voyage qui vous a marqué(e).",
            "Un plat ou une boisson découvert(e) à l'étranger.",
            "Une petite aventure ou galère de voyage dont vous riez encore.",
        ],
    },
    "passions": {
        "order": 8, "label": "Mes passions", "emoji": "🎨",
        "description": "Ce qui a fait battre votre cœur : sport, art, jardin, musique…",
        "prompts": [
            "Une passion qui vous a suivi(e) toute votre vie.",
            "Un livre ou un film qui vous a bouleversé(e).",
            "Un savoir-faire que vous aimeriez transmettre.",
            "Un moment où vous vous êtes surpassé(e) dans votre passion.",
            "Une passion abandonnée — pourquoi et la reprendriez-vous ?",
        ],
    },
    "epreuves": {
        "order": 9, "label": "Mes épreuves & mes fiertés", "emoji": "🌱",
        "description": "Les combats traversés, les leçons de vie.",
        "prompts": [
            "Un moment difficile que vous avez surmonté — comment y êtes-vous parvenu(e) ?",
            "Une décision importante que vous ne regrettez pas.",
            "Une leçon de vie que vous voudriez partager avec les jeunes.",
            "Une fierté personnelle dont vous parlez rarement.",
            "Ce qui vous rend heureux(se) aujourd'hui, malgré tout.",
        ],
    },
    "transmission": {
        "order": 10, "label": "Ce que je transmets", "emoji": "💌",
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
    seed = int(hashlib.md5(f"{user_id}:{today}".encode()).hexdigest(), 16)
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
