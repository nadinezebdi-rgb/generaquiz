"""Mistral generator for Mots Mêlés grids — nightly.

Once a night, ask Mistral to produce ONE fresh themed word-search:
  { "theme": "...", "emoji": "🍎", "words": ["POMME", "POIRE", ...] }

Then we lay them out in a grid using `wordsearch_data.build_grid` (deterministic
placement, retries). If Mistral fails or returns garbage, the previous grids
stay untouched — zero downtime.

The seed grids (5) are inserted at startup if the collection is empty.
"""
from __future__ import annotations

import asyncio
import json
import os
import random
import re
from datetime import datetime, timezone

from mistralai import Mistral

from core import db, logger
from wordsearch_data import build_grid, build_all_seed_grids


MISTRAL_MODEL = os.environ.get("MISTRAL_MODEL", "mistral-small-latest")
MAX_GRIDS = 40   # keep the collection bounded — old grids beyond this get pruned


# Rotating theme families — the nightly prompt draws from ONE at random so grids
# always surprise players. Add / remove categories to shape the content library.
THEME_FAMILIES: list[dict] = [
    {"family": "Régions françaises",
     "hint": "Choisis une région (Bretagne, Provence, Alsace, Corse, Auvergne...) et sors 10 mots emblématiques"},
    {"family": "Années 60",
     "hint": "Icones des années 60 en France (musique, mode, tv, personnalités, marques)"},
    {"family": "Métiers d'autrefois",
     "hint": "Métiers du XXᵉ siècle qui ont quasi disparu (rémouleur, allumeur de réverbère, télégraphiste...)"},
    {"family": "Cuisine régionale",
     "hint": "Une région ou une famille de plats (bistrot, pâtisserie, plats du dimanche...)"},
    {"family": "Jardin & saisons",
     "hint": "Faune, flore, outils, activités par saison"},
    {"family": "Chansons françaises",
     "hint": "Chanteurs, chansons, comédies musicales des 50-90's"},
    {"family": "Cinéma classique",
     "hint": "Acteurs, films, réalisateurs français d'avant 2000"},
    {"family": "Sport à la française",
     "hint": "Tour de France, Roland-Garros, coupe du monde, disciplines emblématiques"},
    {"family": "Écrivains & poètes",
     "hint": "Grands auteurs français du XIXᵉ et XXᵉ, œuvres célèbres"},
    {"family": "Vie quotidienne d'antan",
     "hint": "Objets du quotidien des années 50-70 (transistor, marmite en fonte, TSF, Solex...)"},
]


def _pick_theme_family() -> dict:
    return random.choice(THEME_FAMILIES)


PROMPT_TEMPLATE = """Tu es un créateur de jeux "mots mêlés" en français, pour un public senior français.

Thème IMPOSÉ : « {family} »
Précision : {hint}

Génère un sous-thème précis (ex : « La Bretagne » pour « Régions françaises ») et 10 mots français associés.
Contraintes :
- Sous-thème court et évocateur pour un senior français
- Mots en MAJUSCULES, sans espace, sans tiret, sans accent, 3 à 9 lettres MAX
- Aucun mot en doublon
- Exactement 10 mots

Réponds STRICTEMENT en JSON valide, sans aucun texte avant ou après :
{{"theme": "Sous-thème précis", "emoji": "🎯 un seul emoji", "words": ["MOT1", ..., "MOT10"]}}
"""


async def _mistral_generate_theme() -> dict | None:
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        logger.warning("[wordsearch] MISTRAL_API_KEY manquant — génération sautée")
        return None
    family = _pick_theme_family()
    prompt = PROMPT_TEMPLATE.format(family=family["family"], hint=family["hint"])
    client = Mistral(api_key=api_key)
    try:
        resp = await asyncio.to_thread(
            client.chat.complete,
            model=MISTRAL_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.9,
        )
        raw = resp.choices[0].message.content
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            logger.warning("[wordsearch] pas de JSON dans la réponse Mistral: %s", raw[:200])
            return None
        payload = json.loads(match.group(0))
        if not payload.get("theme") or not isinstance(payload.get("words"), list):
            return None
        payload["family"] = family["family"]
        return payload
    except Exception as e:
        logger.warning(f"[wordsearch] Mistral error: {e}")
        return None


async def seed_grids_if_empty() -> None:
    """Insert 5 seed grids if the collection is empty."""
    count = await db.wordsearch_grids.count_documents({})
    if count > 0:
        return
    grids = build_all_seed_grids()
    if grids:
        await db.wordsearch_grids.insert_many(grids)
        logger.info(f"[wordsearch] seeded {len(grids)} grids")


async def generate_one_grid_from_mistral() -> str | None:
    """Nightly job: generate a single new grid via Mistral. Returns grid id on success."""
    payload = await _mistral_generate_theme()
    if not payload:
        return None
    grid = build_grid(
        theme=payload["theme"],
        emoji=payload.get("emoji", "🧩"),
        raw_words=payload["words"],
        size=12,
        difficulty=random.choice(["facile", "moyen", "difficile"]),
        source="mistral",
    )
    if not grid:
        logger.warning(f"[wordsearch] failed to place words for theme={payload['theme']!r}")
        return None
    grid["family"] = payload.get("family")
    await db.wordsearch_grids.insert_one(grid)
    logger.info(f"[wordsearch] added grid {grid['id']} — {grid.get('family')}: {grid['theme']}")

    # Prune to MAX_GRIDS: keep the most recent
    count = await db.wordsearch_grids.count_documents({})
    if count > MAX_GRIDS:
        to_drop = count - MAX_GRIDS
        oldest = await db.wordsearch_grids.find({}, {"_id": 1}).sort("created_at", 1).limit(to_drop).to_list(to_drop)
        if oldest:
            await db.wordsearch_grids.delete_many({"_id": {"$in": [d["_id"] for d in oldest]}})
    return grid["id"]
