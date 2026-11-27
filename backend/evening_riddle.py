"""Énigme du soir : une petite devinette familiale écrite par Claude chaque jour, à résoudre ensemble au dîner."""
from __future__ import annotations

import asyncio
import json
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException

from ai_client import ai_complete
from core import db, get_current_user, logger

router = APIRouter(prefix="/enigme", tags=["enigme"])
PARIS = ZoneInfo("Europe/Paris")
_lock = asyncio.Lock()

PROMPT = """Écris UNE énigme (devinette) en français pour une famille réunie au dîner : grands-parents, parents et enfants de 8 ans.
Règles :
- 3 à 5 phrases courtes, à lire à voix haute, ton chaleureux et malicieux ;
- la réponse est un objet, un animal, un métier, un aliment ou une chose du quotidien que tout le monde connaît, d'hier ou d'aujourd'hui ;
- solvable par logique et bon sens, sans culture spécialisée, sans calcul, rien d'effrayant ni de triste ;
- un indice qui aide sans donner la réponse ;
- une courte explication qui relie chaque phrase à la réponse, et une question pour lancer la conversation entre générations.
Réponses déjà utilisées, à NE PAS reprendre : {avoid}.
Réponds uniquement avec ce JSON :
{{"titre": "...", "enigme": "...", "indice": "...", "reponse": "...", "explication": "...", "question_famille": "..."}}"""

FIELDS = ("titre", "enigme", "indice", "reponse", "explication", "question_famille")


def today() -> str:
    return datetime.now(PARIS).date().isoformat()


async def _generate(date: str) -> dict:
    avoid = [r["reponse"] async for r in db.evening_riddles.find({}, {"_id": 0, "reponse": 1}).sort("date", -1).limit(40)]
    for _ in range(3):
        raw = await ai_complete(PROMPT.format(avoid=", ".join(avoid) or "aucune"), max_tokens=800, tag="enigme")
        start = raw.find("{")
        try:
            data, _ = json.JSONDecoder().raw_decode(raw[start:]) if start >= 0 else (None, 0)
        except ValueError:
            data = None
        if data and all(isinstance(data.get(k), str) and data[k].strip() for k in FIELDS) \
                and data["reponse"].strip().lower() not in {a.lower() for a in avoid}:
            return {"date": date, **{k: data[k].strip() for k in FIELDS},
                    "created_at": datetime.now(PARIS).isoformat()}
    raise RuntimeError("énigme invalide après 3 essais")


async def get_or_create(date: str | None = None) -> dict:
    date = date or today()
    found = await db.evening_riddles.find_one({"date": date}, {"_id": 0})
    if found:
        return found
    async with _lock:
        found = await db.evening_riddles.find_one({"date": date}, {"_id": 0})
        if found:
            return found
        doc = await _generate(date)
        await db.evening_riddles.insert_one(dict(doc))
        logger.info(f"[enigme] {date} : « {doc['titre']} » ({doc['reponse']})")
        return doc


async def prepare_tonight() -> None:
    """Tâche planifiée de l'après-midi : l'énigme est prête avant le dîner."""
    try:
        await get_or_create()
    except Exception as e:
        logger.error(f"[enigme] génération impossible : {e}")


@router.get("/today")
async def riddle_today(_: dict = Depends(get_current_user)) -> dict:
    try:
        return await get_or_create()
    except Exception as e:
        logger.error(f"[enigme] génération impossible : {e}")
        raise HTTPException(status_code=503, detail="L'énigme du soir se prépare, revenez dans un instant.")
