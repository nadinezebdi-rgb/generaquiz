"""Rubrique « Bien vieillir » — catalogue d'habitudes et synchronisation de la routine.

Le front persiste la routine hebdomadaire en localStorage (voir
`frontend/src/hooks/useWeeklyRoutine.js`) : la rubrique est publique et doit
rester utilisable sans compte. Ce routeur ajoute une synchronisation
*optionnelle* pour les utilisateurs connectés, afin que la routine suive d'un
appareil à l'autre.

Le format accepté par PUT /routine est exactement celui produit par
`exportPayload()` côté front :

    {
      "version": 1,
      "weeks": {"2026-W37": {"marche": true, "memoire": true}},
      "updatedAt": "2026-09-09T10:00:00.000Z"
    }

Collection Mongo : `bien_vieillir_routines`, un document par utilisateur, clé
`user_id`.

ATTENTION — les identifiants d'habitudes sont persistés tels quels. Ne jamais
renommer un `id` existant : cela effacerait silencieusement l'historique des
utilisateurs. Pour retirer une habitude, la marquer `retired`.
La liste ci-dessous doit rester alignée avec
`frontend/src/content/routineHebdo.js` (test : backend/tests/test_bien_vieillir.py).
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core import db, get_current_user

router = APIRouter(prefix="/bien-vieillir", tags=["bien-vieillir"])

ROUTINE_VERSION = 1

# Nombre d'habitudes à cocher pour qu'une semaine compte dans la série.
WEEK_VALID_THRESHOLD = 4

# Bornes défensives : une routine hebdomadaire n'a aucune raison de dépasser
# 10 ans d'historique. Évite qu'un client bogué ou malveillant fasse grossir un
# document Mongo sans limite.
MAX_WEEKS = 520

WEEK_KEY_RE = re.compile(r"^\d{4}-W\d{2}$")

HABITS: list[dict[str, str]] = [
    {"id": "marche", "emoji": "🚶", "label": "Bouger 30 minutes, 5 jours"},
    {"id": "equilibre", "emoji": "🤸", "label": "Deux séances d'équilibre ou de renforcement"},
    {"id": "memoire", "emoji": "🧠", "label": "Trois séances de stimulation cognitive"},
    {"id": "lien", "emoji": "💬", "label": "Trois vraies conversations"},
    {"id": "sortie", "emoji": "🌤️", "label": "Sortir de chez soi cinq jours"},
    {"id": "sommeil", "emoji": "🌙", "label": "Des horaires de sommeil réguliers"},
]

HABIT_IDS = {h["id"] for h in HABITS}


class RoutinePayload(BaseModel):
    version: int = Field(default=ROUTINE_VERSION)
    weeks: dict[str, dict[str, bool]] = Field(default_factory=dict)
    updatedAt: str | None = None


def sanitise_weeks(weeks: dict[str, Any]) -> dict[str, dict[str, bool]]:
    """Ne conserve que des clés de semaine ISO valides et des habitudes connues.

    Toute donnée non reconnue est écartée silencieusement plutôt que rejetée :
    un client d'une version antérieure ou postérieure ne doit pas voir sa
    synchronisation échouer en bloc à cause d'une seule clé inattendue.
    """
    clean: dict[str, dict[str, bool]] = {}
    for week, checks in (weeks or {}).items():
        if not isinstance(week, str) or not WEEK_KEY_RE.match(week):
            continue
        if not isinstance(checks, dict):
            continue
        kept = {hid: True for hid in HABIT_IDS if checks.get(hid) is True}
        if kept:
            clean[week] = kept
    if len(clean) > MAX_WEEKS:
        # On garde les semaines les plus récentes (les clés ISO se trient
        # lexicographiquement dans l'ordre chronologique).
        for week in sorted(clean)[:-MAX_WEEKS]:
            del clean[week]
    return clean


def compute_streak(weeks: dict[str, dict[str, bool]]) -> int:
    """Semaines validées consécutives, en repartant de la plus récente validée.

    Contrairement au calcul du front (qui connaît la date du jour), on ne
    tolère pas ici de « semaine en cours » : cette valeur est indicative et
    l'affichage fait foi côté client.
    """
    valid = sorted(w for w, checks in weeks.items() if len(checks) >= WEEK_VALID_THRESHOLD)
    if not valid:
        return 0
    streak = 1
    for previous, current in zip(valid, valid[1:]):
        if _is_consecutive(previous, current):
            streak += 1
        else:
            streak = 1
    return streak


def _is_consecutive(previous: str, current: str) -> bool:
    """True si `current` est la semaine ISO qui suit immédiatement `previous`."""
    py, pw = int(previous[:4]), int(previous[6:])
    cy, cw = int(current[:4]), int(current[6:])
    if py == cy:
        return cw == pw + 1
    # Bascule d'année : la semaine 1 suit la 52e ou la 53e selon les années.
    return cy == py + 1 and cw == 1 and pw >= 52


@router.get("/habits")
async def list_habits() -> dict[str, Any]:
    """Catalogue public des habitudes — sert de contrat au front et aux tests."""
    return {
        "version": ROUTINE_VERSION,
        "weekValidThreshold": WEEK_VALID_THRESHOLD,
        "habits": HABITS,
    }


@router.get("/routine")
async def get_routine(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    """Routine synchronisée de l'utilisateur connecté (vide s'il n'a rien poussé)."""
    doc = await db.bien_vieillir_routines.find_one({"user_id": user["id"]})
    if not doc:
        return {"version": ROUTINE_VERSION, "weeks": {}, "updatedAt": None, "streak": 0}
    weeks = sanitise_weeks(doc.get("weeks", {}))
    return {
        "version": ROUTINE_VERSION,
        "weeks": weeks,
        "updatedAt": doc.get("updated_at"),
        "streak": compute_streak(weeks),
    }


@router.put("/routine")
async def put_routine(
    payload: RoutinePayload,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Fusionne la routine locale avec celle du serveur.

    Fusion et non remplacement : deux appareils utilisés en parallèle ne doivent
    pas s'effacer mutuellement. Une case cochée l'emporte toujours sur une case
    absente — décocher se propage donc uniquement sur l'appareil courant, ce qui
    est le compromis le moins destructeur.
    """
    if payload.version != ROUTINE_VERSION:
        raise HTTPException(
            status_code=400,
            detail=f"Version de routine non supportée : {payload.version}",
        )

    incoming = sanitise_weeks(payload.weeks)
    existing_doc = await db.bien_vieillir_routines.find_one({"user_id": user["id"]})
    merged = sanitise_weeks(existing_doc.get("weeks", {})) if existing_doc else {}

    for week, checks in incoming.items():
        merged.setdefault(week, {}).update(checks)
    merged = sanitise_weeks(merged)

    now = datetime.now(timezone.utc).isoformat()
    await db.bien_vieillir_routines.update_one(
        {"user_id": user["id"]},
        {"$set": {"user_id": user["id"], "weeks": merged, "updated_at": now}},
        upsert=True,
    )
    return {
        "version": ROUTINE_VERSION,
        "weeks": merged,
        "updatedAt": now,
        "streak": compute_streak(merged),
    }
