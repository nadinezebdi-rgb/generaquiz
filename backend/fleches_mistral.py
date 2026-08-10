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
MAGIC_BANK_3: list[dict] = [
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


# =============================================================================
# Bank de carrés magiques 4×4 (16 cases jouables, générée par un solver exhaustif
# puis triée à la main sur un pool de ~290 mots français ultra-courants)
# =============================================================================
MAGIC_BANK_4: list[dict] = [
    {
        "words": ("CERF", "EPEE", "REVE", "FEES"),
        "theme": "Contes de fées", "emoji": "🧚",
        "clues": (
            "Cervidé aux bois majestueux",
            "Arme du chevalier",
            "Ce que fait dormir la belle au bois",
            "Créatures magiques à baguette",
        ),
    },
    {
        "words": ("JOLI", "OEIL", "LIRE", "ILES"),
        "theme": "Douceurs du regard", "emoji": "📖",
        "clues": (
            "Agréable à regarder",
            "Organe de la vue",
            "Parcourir un livre",
            "Terres entourées d'eau",
        ),
    },
    {
        "words": ("AMIS", "MIDI", "IDEE", "SIEN"),
        "theme": "Repas entre amis", "emoji": "🍽️",
        "clues": (
            "Personnes chères et fidèles",
            "Heure du déjeuner",
            "Pensée ou petit projet",
            "Possessif (à lui, elle)",
        ),
    },
    {
        "words": ("BAIN", "AIDE", "IDEE", "NEES"),
        "theme": "Vie de famille", "emoji": "🛁",
        "clues": (
            "Moment dans la baignoire",
            "Coup de main donné",
            "Petite trouvaille",
            "Venues au monde (féminin pluriel)",
        ),
    },
    {
        "words": ("ANSE", "NOEL", "SERA", "ELAN"),
        "theme": "Fêtes de fin d'année", "emoji": "🎄",
        "clues": (
            "Poignée d'une tasse",
            "Fête du 25 décembre",
            "Verbe être au futur (3ᵉ p. sg.)",
            "Grand cervidé du Nord",
        ),
    },
    {
        "words": ("VRAI", "REND", "ANSE", "IDEE"),
        "theme": "Réflexions", "emoji": "💡",
        "clues": (
            "Contraire de faux",
            "Verbe rendre (3ᵉ p. sg.)",
            "Poignée d'un panier",
            "Petite trouvaille de l'esprit",
        ),
    },
    {
        "words": ("ETAT", "TOUR", "AUTO", "TROU"),
        "theme": "Sur la route", "emoji": "🚗",
        "clues": (
            "Pays ou condition",
            "Édifice de la dame de fer",
            "Voiture familière",
            "Cavité dans le sol",
        ),
    },
    {
        "words": ("NAIF", "AIDE", "IDEE", "FEES"),
        "theme": "Contes d'enfance", "emoji": "🧸",
        "clues": (
            "Innocent, trop confiant",
            "Coup de main généreux",
            "Petite trouvaille de l'esprit",
            "Créatures magiques ailées",
        ),
    },
    {
        "words": ("SEPT", "ETUI", "PURE", "TIEN"),
        "theme": "Petits mots précis", "emoji": "🔢",
        "clues": (
            "Nombre des jours de la semaine",
            "Petite boîte pour lunettes",
            "Sans mélange, cristalline",
            "Possessif (à toi)",
        ),
    },
    {
        "words": ("PORC", "OEIL", "RIRE", "CLES"),
        "theme": "Instants du quotidien", "emoji": "😄",
        "clues": (
            "Cochon de la ferme",
            "Organe qui voit",
            "Ce que fait une bonne blague",
            "Elles ouvrent les portes",
        ),
    },
    {
        "words": ("GAIN", "AIDE", "IDEE", "NEES"),
        "theme": "Idée gagnante", "emoji": "🏆",
        "clues": (
            "Bénéfice ou victoire",
            "Coup de main précieux",
            "Éclair de génie",
            "Venues au monde",
        ),
    },
    {
        "words": ("HERO", "ETUI", "RUSE", "OIES"),
        "theme": "Récits de bravoure", "emoji": "🦸",
        "clues": (
            "Personnage courageux",
            "Petite boîte allongée",
            "Astuce ingénieuse",
            "Volailles blanches à long cou",
        ),
    },
    {
        "words": ("VERS", "ETUI", "RUSE", "SIEN"),
        "theme": "Poésie & logique", "emoji": "✒️",
        "clues": (
            "Une ligne de poème",
            "Contenant pour un stylo",
            "Astuce pour arriver à ses fins",
            "Possessif (à lui, à elle)",
        ),
    },
    {
        "words": ("PROF", "RIRE", "ORME", "FEES"),
        "theme": "École enchantée", "emoji": "🎓",
        "clues": (
            "Enseignant familier",
            "Éclat de bonne humeur",
            "Grand arbre à écorce épaisse",
            "Créatures magiques ailées",
        ),
    },
    {
        "words": ("GROS", "ROSE", "OSER", "SERA"),
        "theme": "Jardin & avenir", "emoji": "🌹",
        "clues": (
            "Contraire de mince",
            "Fleur reine du jardin",
            "Prendre le risque",
            "Verbe être au futur",
        ),
    },
]

# Backwards-compat alias for external callers (aucun autre module n'y touche mais on garde).
MAGIC_BANK = MAGIC_BANK_3


def _pick_puzzle() -> tuple[dict, int]:
    """Retourne (entry, size). 60 % des nuits = 4×4 (plus riche), 40 % = 3×3."""
    if random.random() < 0.6:
        return random.choice(MAGIC_BANK_4), 4
    return random.choice(MAGIC_BANK_3), 3


# =============================================================================
# Mistral : reformulation des définitions (optionnel)
# =============================================================================

PROMPT_RECLUE = """Tu es un rédacteur de définitions de mots croisés, pour un public senior français.

Voici {n} mots français : {word_list}.

Pour chaque mot, écris DEUX définitions courtes DIFFÉRENTES (< 50 caractères chacune), claires et évocatrices pour un senior, sans citer le mot lui-même. Les deux définitions doivent définir le MÊME mot mais avec deux formulations distinctes (angles différents : sens propre / sens figuré, usage familier / soutenu, sensoriel / factuel, etc.).

- La première définition sera affichée à côté du mot en HORIZONTAL.
- La seconde sera affichée à côté du mot en VERTICAL.
Aucune définition ne doit être identique à une autre dans la grille.

Réponds STRICTEMENT en JSON valide :
{{
  "clues_h": [{example_list}],
  "clues_v": [{example_list_v}]
}}
"""


async def _mistral_reclue(words: tuple[str, ...]) -> tuple[list[str], list[str]] | None:
    """Demande à Mistral 2n définitions fraîches (n horizontales + n verticales) pour n mots.

    Chaque mot reçoit DEUX formulations distinctes — une pour la lecture
    horizontale, une pour la verticale — afin d'éviter le doublon visuel
    inhérent aux carrés magiques symétriques.
    """
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        return None
    client = Mistral(api_key=api_key)
    n = len(words)
    word_list = ", ".join(words)
    example_list = ", ".join([f'"définition H de {w}"' for w in words])
    example_list_v = ", ".join([f'"définition V de {w}"' for w in words])
    prompt = PROMPT_RECLUE.format(n=n, word_list=word_list, example_list=example_list, example_list_v=example_list_v)
    try:
        resp = await asyncio.to_thread(
            client.chat.complete,
            model=MISTRAL_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
        )
        raw = resp.choices[0].message.content
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            return None
        data = json.loads(match.group(0))
        clues_h = data.get("clues_h", [])
        clues_v = data.get("clues_v", [])
        if not (isinstance(clues_h, list) and isinstance(clues_v, list)):
            return None
        if len(clues_h) != n or len(clues_v) != n:
            return None
        # Validation : longueur, pas de contamination, unicité (H_i != V_i)
        for i, word in enumerate(words):
            for arr in (clues_h, clues_v):
                if not isinstance(arr[i], str):
                    return None
                c = arr[i].strip()
                if len(c) < 5 or len(c) > 60:
                    return None
                if word.lower() in c.lower():
                    return None
                arr[i] = c
            if clues_h[i].lower() == clues_v[i].lower():
                # Refuse si Mistral a produit deux fois la même définition
                return None
        return clues_h, clues_v
    except Exception as e:
        logger.warning(f"[fleches-gen] Mistral reclue error: {e}")
        return None


# =============================================================================
# Construction du document grille
# =============================================================================

def _build_magic_grid(theme_label: str, emoji: str, words: tuple[str, ...],
                      clues_h: list[str], clues_v: list[str], theme_family: str) -> dict:
    """Construit une grille (N+1)×(N+1) (N×N jouable) à partir d'un tuple symétrique.

    N=3 → grille 4×4 avec 9 cases jouables.
    N=4 → grille 5×5 avec 16 cases jouables.

    clues_h : définitions affichées à côté des mots horizontaux (colonne 0).
    clues_v : définitions affichées au-dessus des mots verticaux (ligne 0).
    Elles décrivent les mêmes mots mais avec des formulations différentes.
    """
    n = len(words)
    assert n in (3, 4), "seul 3 ou 4 mots supportés"
    assert len(clues_h) == n and len(clues_v) == n, "clues_h/clues_v doivent avoir n items"
    matrix = [list(w) for w in words]

    # Row 0 = bandeau de définitions verticales (▼)
    cells = [[{"type": "block"}] + [{"type": "block", "clue_v": clues_v[k]} for k in range(n)]]
    for i in range(n):
        row = [{"type": "block", "clue_h": clues_h[i]}]
        for j in range(n):
            row.append({"type": "letter", "answer": matrix[i][j]})
        cells.append(row)

    return {
        "id": f"mfg-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{random.randint(1000, 9999)}",
        "theme": theme_label,
        "emoji": emoji,
        "difficulty": "difficile",  # les croisements rendent chaque erreur pénalisante
        "size": n + 1,
        "rows": n + 1,
        "cols": n + 1,
        "cells": cells,
        "words": [
            *[{"answer": w, "direction": "h", "row": i + 1, "col": 1} for i, w in enumerate(words)],
            *[{"answer": w, "direction": "v", "row": 1, "col": j + 1} for j, w in enumerate(words)],
        ],
        "source": "mistral",
        "family": theme_family,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "notes": f"Carré magique {'/'.join(words)} — {2 * n} mots croisés (H + V), 2 définitions distinctes par mot.",
    }


def _fallback_clues_v(clues_h: list[str]) -> list[str]:
    """Si Mistral échoue et que la bank ne fournit qu'un jeu de clues, on
    dérive un jeu vertical minimaliste en préfixant "↓ " et en variant la
    ponctuation. Fallback rare, uniquement quand l'API Mistral est indisponible.
    """
    return [f"↓ {c}" for c in clues_h]


async def generate_nightly_fleches() -> str | None:
    """Job nocturne : construit UNE nouvelle grille carré magique (3×3 ou 4×4).

    Étapes :
    1. Choisit une entrée dans MAGIC_BANK_3 (40 %) ou MAGIC_BANK_4 (60 %)
    2. Demande à Mistral 2N définitions fraîches (N horizontales + N verticales,
       chacune différente pour le même mot)
    3. Fallback : si Mistral échoue, réutilise les clues du bank pour H et
       une variante minimale pour V (dernier recours)
    4. Persiste la grille et purge les anciennes au-delà de MAX_GENERATED

    Retourne l'id de la grille ou None si aucune écriture DB n'a eu lieu.
    """
    entry, size = _pick_puzzle()
    words = entry["words"]
    default_clues = list(entry["clues"])

    fresh = await _mistral_reclue(words)
    if fresh is not None:
        clues_h, clues_v = fresh
        source_clues = "mistral"
    else:
        clues_h = default_clues
        clues_v = _fallback_clues_v(default_clues)
        source_clues = "default+fallback"

    grid = _build_magic_grid(
        theme_label=entry["theme"],
        emoji=entry["emoji"],
        words=words,
        clues_h=clues_h,
        clues_v=clues_v,
        theme_family=entry["theme"],
    )
    await db.fleches_generated.insert_one(grid)
    logger.info(
        f"[fleches-gen] added magic grid {grid['id']} — {grid['theme']} "
        f"({'/'.join(words)}, {size}×{size}) source_clues={source_clues}"
    )

    count = await db.fleches_generated.count_documents({})
    if count > MAX_GENERATED:
        oldest = await db.fleches_generated.find({}, {"_id": 1}).sort("created_at", 1).limit(count - MAX_GENERATED).to_list(count)
        if oldest:
            await db.fleches_generated.delete_many({"_id": {"$in": [d["_id"] for d in oldest]}})
    return grid["id"]
