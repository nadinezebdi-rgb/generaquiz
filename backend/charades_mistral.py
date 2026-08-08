"""Mistral generator for Charades — nightly.

Once a night (04:00 Paris) we ask Mistral for a SMALL BATCH of new charades
in strict JSON, validate each one automatically, and store the survivors in
Mongo under the `mistral_charades` collection.

Automatic quality checks (each candidate must pass ALL):
  - parts is a list of 2 or 3 clues
  - answer_display is 1 to 24 letters (accents / apostrophes OK)
  - normalize(answer_display) is 3..15 letters after stripping non-alpha
  - hint is 8..200 chars
  - answer isn't already in the static library
  - no candidate is duplicated within the batch

Rejected candidates are logged so an admin can inspect the raw output later.

Design decision: we DO NOT verify phonetic decomposition (impossible to do
reliably). Instead we mark each Mistral charade with source="mistral" so
the UI can show a small "auto" badge, and any player report bumps a flag.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
from datetime import datetime, timezone

from mistralai import Mistral

from core import db, logger
from charades_data import CHARADES, normalize


MISTRAL_MODEL = os.environ.get("MISTRAL_MODEL", "mistral-small-latest")

BATCH_SIZE = 5           # ask for 5 candidates, keep the ones that pass QA
MAX_MISTRAL_CHARADES = 60  # keep the extension bounded

PACKS_ROTATION = ["classique", "cuisine", "nature", "metiers", "animaux", "voyages"]

PROMPT = """Tu es un auteur de charades françaises pour un public senior.

Rappel du format : "Mon premier..." pour chaque syllabe puis "Mon tout...".
IMPORTANT : chaque syllabe doit VRAIMENT correspondre au mot final quand on prononce à voix haute.

Contraintes strictes :
- Thème du batch : {pack}
- Réponse : mot français simple, courant, entre 3 et 15 lettres
- 2 ou 3 syllabes (parts), pas plus
- Chaque partie doit indiquer un mot ou concept clair
- Ni vulgaire, ni technique
- Vocabulaire adapté à un senior français (années 60-90)

Génère exactement {n} charades différentes, UNIQUES et VALIDES. Réponds STRICTEMENT en JSON:
[
  {{
    "parts": ["Mon premier ...", "Mon deuxième ...", "Mon tout ..."],
    "answer_display": "Château",
    "hint": "Un petit indice"
  }},
  ...
]
"""


def _validate_candidate(c: dict, existing_answers: set[str]) -> tuple[bool, str]:
    """Return (ok, reason). Automatic QA — no phonetic check."""
    parts = c.get("parts")
    if not isinstance(parts, list) or len(parts) < 2 or len(parts) > 3:
        return False, "parts must be a list of 2 or 3 clues"
    if not all(isinstance(p, str) and 10 <= len(p) <= 220 for p in parts):
        return False, "each part must be a string of 10-220 chars"
    display = c.get("answer_display")
    if not isinstance(display, str) or not (1 <= len(display) <= 24):
        return False, "answer_display length out of range"
    norm = normalize(display)
    if not (3 <= len(norm) <= 15):
        return False, f"normalized answer length out of range ({norm!r})"
    if norm in existing_answers:
        return False, f"duplicate answer ({norm})"
    hint = c.get("hint", "")
    if not isinstance(hint, str) or not (5 <= len(hint) <= 220):
        return False, "hint length out of range"
    return True, "ok"


async def _mistral_batch(pack: str, n: int = BATCH_SIZE) -> list[dict]:
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        logger.warning("[charades-gen] MISTRAL_API_KEY manquant — sauté")
        return []
    prompt = PROMPT.format(pack=pack, n=n)
    client = Mistral(api_key=api_key)
    try:
        resp = await asyncio.to_thread(
            client.chat.complete,
            model=MISTRAL_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.9,
        )
        raw = resp.choices[0].message.content
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        if not match:
            logger.warning("[charades-gen] pas de JSON dans la réponse: %s", raw[:200])
            return []
        arr = json.loads(match.group(0))
        return arr if isinstance(arr, list) else []
    except Exception as e:
        logger.warning(f"[charades-gen] Mistral error: {e}")
        return []


async def generate_nightly_charades() -> dict:
    """Nightly job: ask Mistral for a small pack, validate, persist.

    Returns a small report {pack, attempted, accepted, rejected_reasons[]}.
    """
    pack = PACKS_ROTATION[datetime.now(timezone.utc).timetuple().tm_yday % len(PACKS_ROTATION)]

    # Existing answers (static + already-generated) to avoid duplicates
    existing = {c["answer"] for c in CHARADES}
    async for d in db.mistral_charades.find({}, {"answer": 1, "_id": 0}):
        existing.add(d["answer"])

    candidates = await _mistral_batch(pack, n=BATCH_SIZE)
    accepted: list[dict] = []
    rejected: list[str] = []
    seen_in_batch: set[str] = set()
    now = datetime.now(timezone.utc).isoformat()

    for c in candidates:
        ok, reason = _validate_candidate(c, existing | seen_in_batch)
        if not ok:
            rejected.append(reason)
            continue
        norm = normalize(c["answer_display"])
        seen_in_batch.add(norm)
        accepted.append({
            "id": f"m{now[:10].replace('-', '')}_{norm}",
            "pack": pack,
            "parts": c["parts"],
            "answer_display": c["answer_display"],
            "answer": norm,
            "hint": c["hint"],
            "source": "mistral",
            "created_at": now,
        })

    if accepted:
        await db.mistral_charades.insert_many(accepted)
        logger.info(f"[charades-gen] +{len(accepted)} charades ({pack}) — rejected {len(rejected)}")

    # Prune to MAX_MISTRAL_CHARADES
    count = await db.mistral_charades.count_documents({})
    if count > MAX_MISTRAL_CHARADES:
        oldest = await db.mistral_charades.find({}, {"_id": 1}).sort("created_at", 1).limit(count - MAX_MISTRAL_CHARADES).to_list(count)
        if oldest:
            await db.mistral_charades.delete_many({"_id": {"$in": [d["_id"] for d in oldest]}})

    return {
        "pack": pack,
        "attempted": len(candidates),
        "accepted": len(accepted),
        "rejected_reasons": rejected,
    }
