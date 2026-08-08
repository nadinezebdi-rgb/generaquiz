"""Mistral generator for Mots Fléchés — nightly.

Produces ONE new grid per night with the classic row-based structure:
  Each row = [block with clue_h] + [letters of the answer]
The number of rows is `n_words`; column count = max(word_length) + 1 (for the
clue column). No vertical intersections — trivial to generate, always solvable.

Cron: 04:30 Europe/Paris (after wordsearch @ 03:30 and charades @ 04:00).
"""
from __future__ import annotations

import asyncio
import json
import os
import random
import re
import unicodedata
from datetime import datetime, timezone

from mistralai import Mistral

from core import db, logger


MISTRAL_MODEL = os.environ.get("MISTRAL_MODEL", "mistral-small-latest")
MAX_GENERATED = 30           # keep bounded — old grids beyond this are pruned
MIN_WORDS, MAX_WORDS = 6, 8  # each grid has this many word/clue rows


THEME_ROTATION = [
    ("Cuisine française",     "🍽️"),
    ("Cinéma classique",       "🎬"),
    ("Chansons françaises",    "🎶"),
    ("Régions de France",      "🗺️"),
    ("La ferme",               "🐓"),
    ("Fleurs et arbres",       "🌸"),
    ("Métiers d'autrefois",    "👷"),
    ("Vie quotidienne d'antan", "📻"),
    ("Sport à la française",   "🏆"),
    ("Écrivains français",     "📖"),
]


def _pick_theme() -> tuple[str, str]:
    return random.choice(THEME_ROTATION)


def _normalize_answer(w: str) -> str:
    s = w.strip().upper()
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return "".join(c for c in s if "A" <= c <= "Z")


PROMPT = """Tu es un créateur de "mots fléchés" français simples, pour un public senior.

Thème imposé : « {theme} »

Génère exactement {n} paires (mot français, définition courte).
Contraintes strictes:
- Le mot est un nom commun français simple, 3 à 8 lettres, en MAJUSCULES, sans accent ni espace ni tiret
- La définition tient sur une seule ligne courte (< 60 caractères), lisible par un senior
- Aucune définition ne peut contenir le mot lui-même
- Aucune paire n'est doublée

Réponds STRICTEMENT en JSON valide :
{{
  "theme": "Un titre précis pour la grille",
  "emoji": "🎯",
  "entries": [
    {{"word": "POMME", "clue": "Un fruit rouge ou vert du verger"}},
    ...
  ]
}}
"""


def _validate_entry(entry: dict) -> tuple[bool, str]:
    w = entry.get("word", "")
    c = entry.get("clue", "")
    if not isinstance(w, str) or not isinstance(c, str):
        return False, "not strings"
    norm = _normalize_answer(w)
    if not (3 <= len(norm) <= 8):
        return False, f"length {len(norm)}"
    if not norm.isalpha():
        return False, "non-alpha"
    if norm.lower() in c.lower():
        return False, "clue contains answer"
    if not (5 <= len(c) <= 60):
        return False, "clue length"
    return True, "ok"


def _build_grid_from_entries(theme_label: str, emoji: str, entries: list[dict], theme_family: str) -> dict:
    """Turn a validated list of {word, clue} into the fléchés cell matrix."""
    words = [_normalize_answer(e["word"]) for e in entries]
    max_len = max(len(w) for w in words)
    cols = max_len + 1  # +1 clue column
    rows = len(entries)

    cells: list[list[dict]] = []
    for i, entry in enumerate(entries):
        row = [{"type": "block", "clue_h": entry["clue"]}]
        w = _normalize_answer(entry["word"])
        for k in range(max_len):
            if k < len(w):
                row.append({"type": "letter", "answer": w[k]})
            else:
                # Pad shorter words with a spacer block so the grid stays rectangular
                row.append({"type": "block"})
        cells.append(row)

    return {
        "id": f"mfg-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{random.randint(1000, 9999)}",
        "theme": theme_label,
        "emoji": emoji,
        "difficulty": random.choice(["facile", "moyen", "difficile"]),
        "size": max(rows, cols),   # legacy square hint (kept for backward compat)
        "rows": rows,
        "cols": cols,
        "cells": cells,
        "source": "mistral",
        "family": theme_family,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


async def _mistral_generate_pack() -> tuple[dict, list[dict]] | None:
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        logger.warning("[fleches-gen] MISTRAL_API_KEY manquant — sauté")
        return None
    theme_family, emoji = _pick_theme()
    n = random.randint(MIN_WORDS, MAX_WORDS)
    prompt = PROMPT.format(theme=theme_family, n=n)
    client = Mistral(api_key=api_key)
    try:
        resp = await asyncio.to_thread(
            client.chat.complete,
            model=MISTRAL_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.85,
        )
        raw = resp.choices[0].message.content
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            logger.warning("[fleches-gen] no JSON in Mistral response: %s", raw[:200])
            return None
        payload = json.loads(match.group(0))
        if not isinstance(payload.get("entries"), list):
            return None
        # Validate and dedupe
        clean = []
        seen: set[str] = set()
        for e in payload["entries"]:
            ok, _ = _validate_entry(e)
            if not ok:
                continue
            norm = _normalize_answer(e["word"])
            if norm in seen:
                continue
            seen.add(norm)
            clean.append({"word": norm, "clue": e["clue"].strip()})
        if len(clean) < MIN_WORDS:
            logger.warning("[fleches-gen] too few valid entries after QA: %d", len(clean))
            return None
        return ({"theme": payload.get("theme") or theme_family, "emoji": payload.get("emoji") or emoji,
                 "family": theme_family}, clean)
    except Exception as e:
        logger.warning(f"[fleches-gen] Mistral error: {e}")
        return None


async def generate_nightly_fleches() -> str | None:
    """Nightly job: build ONE new fléchés grid via Mistral and persist it.

    Returns the grid id on success, None on failure. Prunes to MAX_GENERATED.
    """
    result = await _mistral_generate_pack()
    if not result:
        return None
    meta, entries = result
    grid = _build_grid_from_entries(meta["theme"], meta["emoji"], entries, meta["family"])
    await db.fleches_generated.insert_one(grid)
    logger.info(f"[fleches-gen] added grid {grid['id']} — {grid['theme']} ({grid['rows']}x{grid['cols']})")

    count = await db.fleches_generated.count_documents({})
    if count > MAX_GENERATED:
        oldest = await db.fleches_generated.find({}, {"_id": 1}).sort("created_at", 1).limit(count - MAX_GENERATED).to_list(count)
        if oldest:
            await db.fleches_generated.delete_many({"_id": {"$in": [d["_id"] for d in oldest]}})
    return grid["id"]
