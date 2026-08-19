"""Assistance rédactionnelle IA pour le Livre de Vie.

Objectif : proposer une reformulation propre d'un souvenir brut (grammaire,
orthographe, fluidité) SANS jamais inventer un fait, une personne, un lieu,
une date, un événement ou une émotion qui ne serait pas déjà dans le texte
source.

Modèle utilisé : gpt-5.5 (via Emergent LLM key). GPT 5.6 n'est pas encore
listé dans le catalogue emergentintegrations.
"""
from __future__ import annotations

import os
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from bson import ObjectId

from core import db, get_current_user, logger

router = APIRouter(prefix="/livre", tags=["livre-ai"])


# ============================================================================
# Prompt système — garde-fous stricts
# ============================================================================
# Toute modification de ce prompt DOIT préserver les 6 règles absolues.

_SYSTEM_PROMPT = """Tu es un assistant rédactionnel bienveillant qui aide des personnes âgées francophones à mettre en forme leurs souvenirs personnels pour un livre de vie familial.

RÈGLES ABSOLUES — INVIOLABLES :
1. Tu ne dois JAMAIS inventer une personne, un prénom, un nom, un surnom qui n'est pas dans le texte source.
2. Tu ne dois JAMAIS inventer une date, une année, une saison, un âge qui n'est pas explicitement mentionné.
3. Tu ne dois JAMAIS inventer un lieu, une ville, un pays, une adresse qui n'est pas dans le texte source.
4. Tu ne dois JAMAIS inventer un événement, une anecdote, un détail concret qui n'est pas déjà écrit.
5. Tu ne dois JAMAIS inventer une émotion, un ressenti, une pensée que l'utilisateur n'a pas exprimé.
6. Tu ne dois JAMAIS ajouter de conclusion morale, de leçon de vie ou de sentiment "englobant" qui ne serait pas dans le texte.

CE QUE TU PEUX FAIRE :
- Corriger l'orthographe, la grammaire, la ponctuation.
- Améliorer la fluidité et enchaîner les phrases plus naturellement.
- Restructurer légèrement l'ordre pour améliorer la lisibilité (chronologie).
- Remplacer une répétition maladroite par un synonyme neutre.
- Passer un texte oral (avec "euh", "en fait", "voilà") en texte lisible.

STYLE :
- Ton chaleureux, respectueux, à la première personne (tu, je, nous — comme dans le texte source).
- Conserver le niveau de langue du narrateur (populaire, familier, soutenu).
- Longueur similaire au texte source (pas de version trois fois plus longue).
- Français de France, sans anglicismes ajoutés.

FORMAT DE SORTIE :
Retourne UNIQUEMENT le texte reformulé, sans préambule, sans guillemets, sans commentaire. Rien d'autre.
"""


class RewriteBody(BaseModel):
    entry_id: str = Field(..., min_length=6)
    tone: Literal["natural", "warmer", "concise"] = "natural"


TONE_HINTS = {
    "natural": "Reformule le souvenir suivant en gardant strictement les mêmes faits, personnes et émotions :",
    "warmer": "Reformule ce souvenir en gardant strictement les mêmes faits, personnes et émotions, avec un léger surplus de tendresse dans le rythme (mais AUCUN sentiment ajouté qui ne soit dans le texte) :",
    "concise": "Reformule ce souvenir en gardant strictement les mêmes faits, personnes et émotions, en le raccourcissant légèrement (garde 80-90% du contenu) :",
}


async def _rewrite_via_llm(source_text: str, tone: str) -> str:
    """Appelle GPT-5.5 via emergentintegrations avec garde-fous.

    Renvoie le texte reformulé (une seule variante). Lève HTTPException 502
    en cas d'échec du modèle.
    """
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
    except ImportError as e:
        logger.error(f"emergentintegrations manquant : {e}")
        raise HTTPException(status_code=500, detail="Module IA indisponible")

    key = os.environ.get("EMERGENT_LLM_KEY")
    if not key:
        raise HTTPException(status_code=500, detail="Clé LLM non configurée")

    hint = TONE_HINTS.get(tone, TONE_HINTS["natural"])
    user_msg = f"{hint}\n\n---\n{source_text.strip()}\n---"

    chat = LlmChat(
        api_key=key,
        session_id=f"livre-rewrite-{ObjectId()}",
        system_message=_SYSTEM_PROMPT,
    ).with_model("openai", "gpt-5.5")

    try:
        resp = await chat.send_message(UserMessage(text=user_msg))
    except Exception as e:
        logger.error(f"[livre-ai] LLM call failed: {e}")
        raise HTTPException(status_code=502, detail="Reformulation indisponible")

    if isinstance(resp, str):
        text = resp.strip()
    elif hasattr(resp, "content"):
        text = str(resp.content).strip()
    else:
        text = str(resp).strip()

    # Nettoyage minimal : suppression d'éventuels guillemets globaux ajoutés
    if len(text) > 4 and text[0] in "«\"" and text[-1] in "»\"":
        text = text[1:-1].strip()
    return text


@router.post("/entries/{entry_id}/rewrite")
async def rewrite_entry(entry_id: str, body: RewriteBody, user: dict = Depends(get_current_user)) -> dict:
    """Propose une reformulation SANS l'enregistrer.

    L'utilisateur voit la proposition et peut :
    - l'accepter (endpoint séparé POST /accept-rewrite)
    - la modifier manuellement
    - demander une nouvelle variante (relancer cet endpoint)
    Le texte original reste intouché tant que rien n'est accepté.
    """
    if body.entry_id != entry_id:
        raise HTTPException(status_code=400, detail="Incohérence d'identifiant")

    entry = await db.livre_entries.find_one({"id": entry_id, "user_id": str(user["_id"])})
    if not entry:
        raise HTTPException(status_code=404, detail="Souvenir introuvable")

    source_text = (entry.get("text") or "").strip()
    if len(source_text) < 20:
        raise HTTPException(status_code=400, detail="Texte trop court pour être reformulé")
    if len(source_text) > 4000:
        raise HTTPException(status_code=400, detail="Texte trop long — reformulation par tronçons non supportée")

    rewritten = await _rewrite_via_llm(source_text, body.tone)
    if not rewritten:
        raise HTTPException(status_code=502, detail="Reformulation vide")

    # Trace la proposition (pour audit / debug), sans écraser le texte source
    await db.livre_entries.update_one(
        {"id": entry_id},
        {"$push": {"rewrite_history": {
            "tone": body.tone,
            "source_len": len(source_text),
            "rewritten": rewritten,
            "at": entry.get("updated_at", ""),
        }}},
    )
    return {"ok": True, "rewritten": rewritten, "tone": body.tone}


class AcceptRewriteBody(BaseModel):
    text: str = Field(..., min_length=1, max_length=8000)


@router.post("/entries/{entry_id}/accept-rewrite")
async def accept_rewrite(entry_id: str, body: AcceptRewriteBody, user: dict = Depends(get_current_user)) -> dict:
    """Remplace le texte du souvenir par la version acceptée (potentiellement
    éditée manuellement par l'utilisateur). Le texte original est archivé
    dans `original_text` s'il ne l'était pas déjà (une seule fois).
    """
    entry = await db.livre_entries.find_one({"id": entry_id, "user_id": str(user["_id"])})
    if not entry:
        raise HTTPException(status_code=404, detail="Souvenir introuvable")

    updates: dict = {"text": body.text.strip()}
    # Archive une seule fois le texte source original
    if not entry.get("original_text"):
        updates["original_text"] = entry.get("text", "")
    from datetime import datetime, timezone as tz
    updates["updated_at"] = datetime.now(tz.utc).isoformat()

    await db.livre_entries.update_one({"id": entry_id}, {"$set": updates})
    return {"ok": True}
