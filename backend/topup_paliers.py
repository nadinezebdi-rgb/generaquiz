"""Top-up des paliers — assure 20 questions par difficulté (1..7) et par catégorie.

Cible : 140 questions par catégorie = 7 paliers × 20 questions.
Chaque palier correspond à un niveau de difficulté progressif :
    1 = très facile     2 = facile      3 = accessible
    4 = intermédiaire   5 = confirmé    6 = difficile     7 = expert

Le script :
  1. Pour chaque catégorie, compte les questions verified par palier
  2. Si < 20 dans un palier, génère (Mistral/Sonnet) puis fact-check (Opus) jusqu'à atteindre 20
  3. N'écrase JAMAIS une question existante — insère uniquement des nouvelles

Usage :
    python topup_paliers.py                        # toutes catégories, tous paliers
    ONLY_CATEGORY=cinema python topup_paliers.py   # une catégorie
    TARGET_PER_PALIER=20 python topup_paliers.py   # override cible (défaut 20)
    MAX_ATTEMPTS=3 python topup_paliers.py         # max fact-check retries (défaut 3)

Rapport écrit dans /tmp/topup_report_{category}.json et affiché sur stdout.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")
sys.path.insert(0, str(ROOT_DIR))

# On réutilise les briques du script de fact-check pour rester DRY et garantir
# que les nouvelles questions passent EXACTEMENT le même pipeline qualité.
from audit_and_regen_questions import (  # noqa: E402
    fact_check_question, CONFIDENCE_THRESHOLD, FACT_CHECK_MODEL, GEN_MODEL,
)
from emergentintegrations.llm.chat import LlmChat, UserMessage  # noqa: E402
from motor.motor_asyncio import AsyncIOMotorClient              # noqa: E402

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
EMERGENT_LLM_KEY = os.environ["EMERGENT_LLM_KEY"]

TARGET_PER_PALIER = int(os.environ.get("TARGET_PER_PALIER", "20"))
MAX_ATTEMPTS = int(os.environ.get("MAX_ATTEMPTS", "3"))

DIFFICULTY_HINTS = {
    1: "Très facile — grand public, niveau école primaire, culture générale immédiate.",
    2: "Facile — évoque des souvenirs partagés par tous, formulation directe.",
    3: "Accessible — nécessite un peu de réflexion mais reste populaire.",
    4: "Intermédiaire — vraie question de culture, on distingue les amateurs.",
    5: "Confirmé — détails plus fins, dates précises, noms secondaires.",
    6: "Difficile — questions pointues, connaissances de passionné.",
    7: "Expert — anecdotes rares, chiffres précis, seul un érudit répond.",
}

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]


async def generate_for_difficulty(category: dict, difficulty: int, avoid_texts: list[str]) -> dict[str, Any] | None:
    """Génère UNE question au niveau de difficulté demandé."""
    hint = DIFFICULTY_HINTS[difficulty]
    avoid = "\n".join(f"- {t}" for t in avoid_texts[-40:])
    prompt = f"""Catégorie : {category['title']}
Description : {category.get('description', '')}

NIVEAU DE DIFFICULTÉ demandé : {difficulty}/7
Consigne : {hint}

Génère UNE question à choix multiple (4 options, 1 seule correcte), factuellement irréprochable, adaptée à ce niveau.

Ne reproduis PAS les questions suivantes (ni leur paraphrase) :
{avoid}

Format JSON STRICT, rien d'autre :
{{"question": "...", "options": ["A", "B", "C", "D"], "correct_index": 0, "explanation": "..."}}"""
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"topup-{category['id']}-{difficulty}-{time.time()}",
        system_message="Tu es expert culture française pour seniors. Tes questions sont irréprochables factuellement.",
    ).with_model(*GEN_MODEL)
    try:
        raw = await chat.send_message(UserMessage(text=prompt))
    except Exception as e:
        print(f"    [gen d={difficulty}] error: {e}")
        return None
    text = raw.strip() if isinstance(raw, str) else str(raw)
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    if not (isinstance(d.get("options"), list) and len(d["options"]) == 4):
        return None
    idx = d.get("correct_index")
    if not isinstance(idx, int) or not (0 <= idx <= 3):
        return None
    return {
        "question": d["question"].strip(),
        "options": [str(o) for o in d["options"]],
        "correct_index": idx,
        "explanation": (d.get("explanation") or "").strip(),
    }


async def topup_category(category: dict) -> dict:
    cat_id = category["id"]
    print(f"\n=== Top-up: {cat_id} ({category['title']}) ===")

    # Comptage actuel par palier — on ne compte QUE les questions verified
    # (les flagged ne sont pas jouables donc ne comptent pas dans les 20).
    counts_per_palier: dict[int, int] = {d: 0 for d in range(1, 8)}
    existing_texts: list[str] = []
    async for q in db.questions.find(
        {"category_id": cat_id, "quality": {"$ne": "flagged"}},
        {"_id": 0, "difficulty": 1, "question": 1},
    ):
        d = q.get("difficulty")
        if isinstance(d, int) and 1 <= d <= 7:
            counts_per_palier[d] = counts_per_palier.get(d, 0) + 1
        existing_texts.append(q["question"])

    print(f"  Palier   | current | target | missing")
    for d in range(1, 8):
        cur = counts_per_palier[d]
        missing = max(0, TARGET_PER_PALIER - cur)
        print(f"    {d}      | {cur:>7} | {TARGET_PER_PALIER:>6} | {missing:>7}")

    report = {"category_id": cat_id, "generated": {}, "failed": {}}

    for difficulty in range(1, 8):
        missing = max(0, TARGET_PER_PALIER - counts_per_palier[difficulty])
        if missing == 0:
            continue
        print(f"\n  → Palier {difficulty} : génération de {missing} questions")
        generated = 0
        failed = 0
        for i in range(missing):
            success = False
            for attempt in range(MAX_ATTEMPTS):
                new_q = await generate_for_difficulty(category, difficulty, existing_texts)
                if not new_q:
                    continue
                check = await fact_check_question({**new_q, "id": f"topup-tmp-{i}"})
                if check["verdict"] == "correct" and check["confidence"] >= CONFIDENCE_THRESHOLD:
                    doc = {
                        "id": f"topup_{cat_id}_d{difficulty}_{int(time.time()*1000)}_{i}",
                        "category_id": cat_id,
                        "difficulty": difficulty,
                        "question": new_q["question"],
                        "options": new_q["options"],
                        "correct_index": new_q["correct_index"],
                        "explanation": new_q["explanation"],
                        "quality": "verified",
                        "fact_check": {
                            "verdict": check["verdict"],
                            "confidence": check["confidence"],
                            "comment": check["comment"],
                            "correction": None,
                            "checked_at": time.time(),
                            "checker_model": FACT_CHECK_MODEL[1],
                            "generated_by": GEN_MODEL[1],
                            "topup": True,
                        },
                    }
                    await db.questions.insert_one(doc)
                    existing_texts.append(new_q["question"])
                    generated += 1
                    success = True
                    print(f"    [{i+1}/{missing}] ✅ (confidence {check['confidence']}, tentative {attempt+1})")
                    break
                else:
                    print(f"    [{i+1}/{missing}] ⚠ refus factcheck ({check['verdict']}/{check['confidence']}) tentative {attempt+1}")
            if not success:
                failed += 1
                print(f"    [{i+1}/{missing}] ❌ abandon après {MAX_ATTEMPTS} tentatives")
        report["generated"][difficulty] = generated
        report["failed"][difficulty] = failed

    out = Path(f"/tmp/topup_report_{cat_id}.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\n  Rapport : {out}")
    return report


async def main():
    only = os.environ.get("ONLY_CATEGORY")
    cats = await db.categories.find({}, {"_id": 0}).to_list(50)
    if only:
        cats = [c for c in cats if c["id"] == only]
    if not cats:
        print(f"Aucune catégorie trouvée (only={only})")
        return

    all_reports = []
    for cat in cats:
        rep = await topup_category(cat)
        all_reports.append(rep)

    total_gen = sum(sum(r["generated"].values()) for r in all_reports)
    total_fail = sum(sum(r["failed"].values()) for r in all_reports)
    print(f"\n\n===== SYNTHÈSE ({len(cats)} catégorie(s)) =====")
    print(f"  Questions générées : {total_gen}")
    print(f"  Échecs             : {total_fail}")


if __name__ == "__main__":
    asyncio.run(main())
