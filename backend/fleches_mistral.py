"""Mistral generator for Mots Fléchés — nightly.

Approche v4 (2026-02) : bank de carrés magiques 3×3 pré-vérifiés + Mistral pour
générer des définitions fraîches. Cela garantit une grille avec de vrais
croisements verticaux ET horizontaux (contrairement à l'ancien mode row-based
qui n'avait qu'un mot par ligne).

Bank
----
Chaque entrée est un triplet (w1, w2, w3) qui forme une matrice symétrique 3×3
(matrix[i][j] == matrix[j][i]). Chaque ligne ET chaque colonne du carré est
donc un vrai mot français. La bank est vérifiée à la main. Elle exclut les
6 triplets déjà utilisés par les grilles seed (mf01-mf06).

Cron: 04:30 Europe/Paris (après wordsearch @ 03:30 et charades @ 04:00).
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


MISTRAL_MODEL = os.environ.get("MISTRAL_MODEL", "mistral-small-latest")
MAX_GENERATED = 30

# =============================================================================
# Bank de carrés magiques 3×3 (mots français courants, matrice symétrique)
# =============================================================================
# Chaque entrée: (triplet w1/w2/w3, thème/emoji, clues par défaut)
# Les 3 clues sont associées 1-to-1 aux mots (w1_clue, w2_clue, w3_clue).
# Les triplets déjà utilisés dans les seeds (mf01..mf06) sont EXCLUS.
MAGIC_BANK: list[dict] = [
    {
        "words": ("AIL", "ILE", "LES"),
        "theme": "Jardin & vocabulaire", "emoji": "🌿",
        "clues": ("Bulbe qui parfume l'aïoli", "Terre entourée d'eau", "Article défini pluriel"),
    },
    {
        "words": ("ART", "RUE", "TES"),
        "theme": "Petits mots courants", "emoji": "📖",
        "clues": ("Peinture, sculpture… tout ça", "Voie urbaine", "Possessif pluriel (à toi)"),
    },
    {
        "words": ("BOL", "OIE", "LES"),
        "theme": "Cuisine & basse-cour", "emoji": "🥣",
        "clues": ("Récipient rond pour le café", "Volaille grise à long cou", "Article défini pluriel"),
    },
    {
        "words": ("COL", "OSE", "LES"),
        "theme": "Vêtements & petits mots", "emoji": "👔",
        "clues": ("Partie haute de la chemise", "N'hésite pas (verbe)", "Article défini pluriel"),
    },
    {
        "words": ("DES", "EAU", "SUD"),
        "theme": "Petits mots & géographie", "emoji": "🧭",
        "clues": ("Article partitif pluriel", "Liquide vital (H₂O)", "Point cardinal opposé au nord"),
    },
    {
        "words": ("CES", "EAU", "SUD"),
        "theme": "Petits mots & géographie", "emoji": "🌊",
        "clues": ("Démonstratif pluriel (ceux-ci)", "Liquide vital (H₂O)", "Point cardinal chaud"),
    },
    {
        "words": ("FIN", "ILE", "NEZ"),
        "theme": "Corps & vocabulaire", "emoji": "👃",
        "clues": ("Le mot du dernier chapitre", "Terre entourée d'eau", "Il sent bon ou mauvais"),
    },
    {
        "words": ("VIN", "IRE", "NEZ"),
        "theme": "Cave & humeur", "emoji": "🍷",
        "clues": ("Boisson fermentée du raisin", "Colère (littéraire)", "Organe de l'odorat"),
    },
    {
        "words": ("CLE", "LES", "EST"),
        "theme": "Petits mots courants", "emoji": "🔑",
        "clues": ("Elle ouvre la porte", "Article défini pluriel", "Point cardinal du soleil levant"),
    },
    {
        "words": ("AME", "MET", "ETE"),
        "theme": "Sentiments & saisons", "emoji": "☀️",
        "clues": ("Elle habite en nous", "Verbe mettre (3ᵉ p. sg.)", "Saison des vacances"),
    },
    {
        "words": ("ANE", "NUL", "ELU"),
        "theme": "Vocabulaire & politique", "emoji": "🗳️",
        "clues": ("Animal têtu à longues oreilles", "Zéro pointé, sans valeur", "Personne choisie par un vote"),
    },
    {
        "words": ("FEE", "EST", "ETE"),
        "theme": "Contes & saisons", "emoji": "🧚",
        "clues": ("Elle a une baguette magique", "Point cardinal du levant", "Saison la plus chaude"),
    },
    {
        "words": ("DON", "OSE", "NEZ"),
        "theme": "Générosité & humeur", "emoji": "🎁",
        "clues": ("Cadeau ou talent", "Prend le risque (verbe)", "Organe entre les yeux et la bouche"),
    },
    {
        "words": ("ETE", "TES", "EST"),
        "theme": "Saisons & petits mots", "emoji": "🌞",
        "clues": ("Saison des cigales", "Possessif (à toi, pluriel)", "Point cardinal du levant"),
    },
    {
        "words": ("ARC", "RUE", "CEP"),
        "theme": "Vignes & voûtes", "emoji": "🍇",
        "clues": ("Il tire des flèches", "Voie urbaine", "Pied de vigne"),
    },
]


def _pick_triple() -> dict:
    return random.choice(MAGIC_BANK)


# =============================================================================
# Mistral : reformulation des définitions (optionnel)
# =============================================================================

PROMPT_RECLUE = """Tu es un rédacteur de définitions de mots croisés, pour un public senior français.

Voici trois mots français : {w1}, {w2}, {w3}.

Pour chaque mot, écris UNE définition courte (< 50 caractères), claire et évocatrice pour un senior, sans citer le mot lui-même. Une définition par mot, dans le même ordre.

Réponds STRICTEMENT en JSON valide :
{{
  "clues": ["définition de {w1}", "définition de {w2}", "définition de {w3}"]
}}
"""


async def _mistral_reclue(w1: str, w2: str, w3: str) -> list[str] | None:
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        return None
    client = Mistral(api_key=api_key)
    prompt = PROMPT_RECLUE.format(w1=w1, w2=w2, w3=w3)
    try:
        resp = await asyncio.to_thread(
            client.chat.complete,
            model=MISTRAL_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        raw = resp.choices[0].message.content
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            return None
        data = json.loads(match.group(0))
        clues = data.get("clues", [])
        if not isinstance(clues, list) or len(clues) != 3:
            return None
        # Validation : longueur, pas de contamination
        for i, (word, clue) in enumerate(zip([w1, w2, w3], clues)):
            if not isinstance(clue, str):
                return None
            c = clue.strip()
            if len(c) < 5 or len(c) > 60:
                return None
            if word.lower() in c.lower():
                return None
            clues[i] = c
        return clues
    except Exception as e:
        logger.warning(f"[fleches-gen] Mistral reclue error: {e}")
        return None


# =============================================================================
# Construction du document grille
# =============================================================================

def _build_magic_grid(theme_label: str, emoji: str, words: tuple[str, str, str],
                      clues: list[str], theme_family: str) -> dict:
    """Construit une grille 4×4 (3×3 jouable) à partir d'un triplet symétrique."""
    w1, w2, w3 = words
    matrix = [list(w1), list(w2), list(w3)]

    cells = [
        [
            {"type": "block"},
            {"type": "block", "clue_v": clues[0]},
            {"type": "block", "clue_v": clues[1]},
            {"type": "block", "clue_v": clues[2]},
        ],
    ]
    for i in range(3):
        row = [{"type": "block", "clue_h": clues[i]}]
        for j in range(3):
            row.append({"type": "letter", "answer": matrix[i][j]})
        cells.append(row)

    return {
        "id": f"mfg-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{random.randint(1000, 9999)}",
        "theme": theme_label,
        "emoji": emoji,
        "difficulty": "difficile",  # les croisements rendent chaque erreur pénalisante
        "size": 4,
        "rows": 4,
        "cols": 4,
        "cells": cells,
        "words": [
            {"answer": w1, "direction": "h", "row": 1, "col": 1},
            {"answer": w2, "direction": "h", "row": 2, "col": 1},
            {"answer": w3, "direction": "h", "row": 3, "col": 1},
            {"answer": w1, "direction": "v", "row": 1, "col": 1},
            {"answer": w2, "direction": "v", "row": 1, "col": 2},
            {"answer": w3, "direction": "v", "row": 1, "col": 3},
        ],
        "source": "mistral",
        "family": theme_family,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "notes": f"Carré magique {w1}/{w2}/{w3} — 6 mots croisés, chaque lettre en croise 2.",
    }


async def generate_nightly_fleches() -> str | None:
    """Job nocturne : construit UNE nouvelle grille carré magique 3×3.

    Étapes :
    1. Choisit un triplet du bank (garanti symétrique)
    2. Demande à Mistral 3 définitions fraîches (sinon utilise les défauts)
    3. Persiste la grille et purge les anciennes au-delà de MAX_GENERATED

    Retourne l'id de la grille ou None si aucune écriture DB n'a eu lieu.
    """
    triple = _pick_triple()
    w1, w2, w3 = triple["words"]
    default_clues = list(triple["clues"])

    fresh = await _mistral_reclue(w1, w2, w3)
    clues = fresh if fresh else default_clues

    grid = _build_magic_grid(
        theme_label=triple["theme"],
        emoji=triple["emoji"],
        words=triple["words"],
        clues=clues,
        theme_family=triple["theme"],
    )
    await db.fleches_generated.insert_one(grid)
    logger.info(
        f"[fleches-gen] added magic grid {grid['id']} — {grid['theme']} "
        f"({w1}/{w2}/{w3}) source_clues={'mistral' if fresh else 'default'}"
    )

    count = await db.fleches_generated.count_documents({})
    if count > MAX_GENERATED:
        oldest = await db.fleches_generated.find({}, {"_id": 1}).sort("created_at", 1).limit(count - MAX_GENERATED).to_list(count)
        if oldest:
            await db.fleches_generated.delete_many({"_id": {"$in": [d["_id"] for d in oldest]}})
    return grid["id"]
