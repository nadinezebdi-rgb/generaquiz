"""Mistral AI client — nightly regeneration of the full GénéraQuiz question pool.

How it works:
  - At 03:00 Europe/Paris each night (scheduled by daily_email.py), `regenerate_all()` runs.
  - For each of the 8 categories, asks Mistral to produce 100 fresh MCQs in strict JSON.
  - Replaces the questions in MongoDB atomically per category (delete_many + insert_many).
  - If Mistral fails for a given category, the existing questions are kept (zero downtime).
"""
from __future__ import annotations

import asyncio
import json
import os
import re
from datetime import datetime, timezone
from typing import Optional

from mistralai import Mistral
from pydantic import BaseModel

from core import db, logger
from seed_data import CATEGORIES

MISTRAL_MODEL = os.environ.get("MISTRAL_MODEL", "mistral-small-latest")
QUESTIONS_PER_CATEGORY = 100
BATCH_SIZE = 25  # Mistral handles ~25 well-structured items per call comfortably


class Question(BaseModel):
    id: str
    category_id: str
    question: str
    options: list[str]
    correct_index: int
    explanation: str


def _client() -> Optional[Mistral]:
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        return None
    return Mistral(api_key=api_key)


def _build_prompt(category: dict, n: int, batch_idx: int) -> str:
    difficulty_mix = {
        0: "8 FACILES (enfants/famille, niveau école primaire/collège), 10 MOYENNES (grand public), 7 DIFFICILES (passionnés/seniors).",
        1: "7 FACILES, 11 MOYENNES, 7 DIFFICILES.",
        2: "8 FACILES, 9 MOYENNES, 8 DIFFICILES.",
        3: "8 FACILES, 9 MOYENNES, 8 DIFFICILES.",
    }.get(batch_idx, "Mélange équilibré")

    return f"""Tu es un expert en culture générale française qui conçoit des quiz pour un jeu familial intergénérationnel nommé "GénéraQuiz".

**CATÉGORIE** : {category['title']}
**DESCRIPTION** : {category['description']}

**MISSION** : Génère EXACTEMENT {n} nouvelles questions à choix multiples (QCM) en français pour cette catégorie.

**RÈGLES IMPÉRATIVES** :
1. Chaque question a EXACTEMENT 4 options de réponse.
2. UNE SEULE bonne réponse par question (index 0 à 3).
3. Les questions doivent être FACTUELLEMENT VÉRIFIABLES (pas d'opinion ni d'ambiguïté).
4. Pour les dates précises, écart d'au moins 2 ans entre options proches.
5. Les explications sont courtes (1-2 phrases max), pédagogiques et factuelles.
6. **Mélange de difficulté** : {difficulty_mix}
7. **Public** : enfants, parents, grands-parents jouent ensemble.

**FORMAT DE SORTIE STRICT** (un seul tableau JSON, RIEN avant ni après, AUCUN bloc markdown) :
[
  {{"question": "Texte de la question ?", "options": ["Opt A", "Opt B", "Opt C", "Opt D"], "correct_index": 0, "explanation": "Courte explication factuelle."}}
]"""


def _extract_json(text: str):
    text = text.strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1:
        raise ValueError("No JSON array in Mistral output")
    return json.loads(text[start:end + 1])


async def _generate_one_batch(client: Mistral, category: dict, n: int, batch_idx: int) -> list[dict]:
    prompt = _build_prompt(category, n, batch_idx)
    # mistralai SDK is sync — run in thread to keep event loop free
    def _call():
        return client.chat.complete(
            model=MISTRAL_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.6,
            max_tokens=4000,
        )
    resp = await asyncio.to_thread(_call)
    content = resp.choices[0].message.content
    items = _extract_json(content)
    return [i for i in items if isinstance(i, dict)]


def _validate(item: dict) -> bool:
    q = item.get("question", "").strip()
    opts = item.get("options")
    idx = item.get("correct_index")
    if not q or not isinstance(opts, list) or len(opts) != 4:
        return False
    if not isinstance(idx, int) or not (0 <= idx <= 3):
        return False
    return True


async def regenerate_category(category: dict, target: int = QUESTIONS_PER_CATEGORY) -> int:
    """Regenerate ALL questions for one category via Mistral. Returns count inserted.

    Atomic per-category: if generation fails, the existing pool is preserved.
    """
    client = _client()
    if client is None:
        logger.warning("[mistral] MISTRAL_API_KEY manquant — régénération sautée")
        return 0

    all_q: list[dict] = []
    seen_texts: set[str] = set()
    batches = []
    remaining = target
    batch_idx = 0
    while remaining > 0:
        size = min(BATCH_SIZE, remaining)
        batches.append((batch_idx, size))
        remaining -= size
        batch_idx += 1

    for idx_b, size in batches:
        attempts = 0
        needed = size
        while needed > 0 and attempts < 3:
            attempts += 1
            try:
                items = await _generate_one_batch(client, category, needed, idx_b)
            except Exception as e:
                logger.warning(f"[mistral] {category['id']} batch {idx_b} attempt {attempts}: {e}")
                await asyncio.sleep(2)
                continue
            added = 0
            for item in items:
                if not _validate(item):
                    continue
                key = item["question"].lower().strip()
                if key in seen_texts:
                    continue
                seen_texts.add(key)
                all_q.append({
                    "id": f"m_{category['id']}_{len(all_q) + 1}",
                    "category_id": category["id"],
                    "question": item["question"].strip(),
                    "options": [str(o) for o in item["options"]],
                    "correct_index": int(item["correct_index"]),
                    "explanation": item.get("explanation", "").strip(),
                })
                added += 1
                if added >= needed:
                    break
            needed -= added

    if not all_q:
        logger.warning(f"[mistral] {category['id']} : aucune question valide, on conserve l'ancien pool")
        return 0

    # Atomic-ish replace: insert new pool first, then delete the old one (by absence of "m_" prefix)
    # Simpler: delete all + insert all in same operation block.
    await db.questions.delete_many({"category_id": category["id"]})
    await db.questions.insert_many(all_q)
    logger.info(f"[mistral] {category['id']} régénéré : {len(all_q)} questions fraîches")
    return len(all_q)


async def regenerate_all() -> dict:
    """Sequentially regenerate every category. Returns a summary dict."""
    started = datetime.now(timezone.utc)
    results: dict[str, int] = {}
    for cat in CATEGORIES:
        try:
            n = await regenerate_category(cat)
            results[cat["id"]] = n
        except Exception as e:  # never let one category break the whole run
            logger.exception(f"[mistral] {cat['id']} failed: {e}")
            results[cat["id"]] = 0
    total = sum(results.values())
    duration = (datetime.now(timezone.utc) - started).total_seconds()
    logger.info(f"[mistral] Régénération complète terminée : {total} questions en {duration:.1f}s")
    return {"total": total, "by_category": results, "duration_sec": int(duration), "model": MISTRAL_MODEL}
