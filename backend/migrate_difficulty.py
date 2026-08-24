"""Migration one-shot — tag les questions existantes avec un `difficulty` 1..7.

Stratégie :
  - Pour chaque catégorie, on prend les questions verified sans `difficulty`
  - On les distribue en round-robin sur les paliers 1..7 (les 20 premières
    servent au palier 1, les 20 suivantes au palier 2, etc.)
  - Ce n'est pas une vraie évaluation de difficulté (impossible sans LLM),
    mais ça amorce le parcours immédiatement. Les nouvelles questions
    générées par `topup_paliers.py` auront, elles, la vraie difficulté LLM.

Usage :
    python migrate_difficulty.py                        # dry-run par défaut
    APPLY=1 python migrate_difficulty.py               # applique en DB
    ONLY_CATEGORY=cinema APPLY=1 python migrate_difficulty.py
"""
from __future__ import annotations

import asyncio
import os
import random
import sys
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")
sys.path.insert(0, str(ROOT_DIR))

from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

APPLY = os.environ.get("APPLY") == "1"

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]


async def migrate_category(cat_id: str, title: str) -> tuple[int, dict[int, int]]:
    qs = await db.questions.find(
        {"category_id": cat_id, "difficulty": {"$exists": False}, "quality": {"$ne": "flagged"}},
        {"_id": 0, "id": 1},
    ).to_list(2000)
    random.shuffle(qs)

    per_palier = 20
    assignments: dict[int, int] = {d: 0 for d in range(1, 8)}
    for idx, q in enumerate(qs):
        palier = (idx // per_palier) % 7 + 1
        assignments[palier] += 1
        if APPLY:
            await db.questions.update_one(
                {"id": q["id"]},
                {"$set": {"difficulty": palier}},
            )
    return len(qs), assignments


async def main():
    only = os.environ.get("ONLY_CATEGORY")
    cats = await db.categories.find({}, {"_id": 0, "id": 1, "title": 1}).to_list(50)
    if only:
        cats = [c for c in cats if c["id"] == only]

    print(f"{'[DRY-RUN]' if not APPLY else '[APPLY]'} Migration difficulty pour {len(cats)} catégorie(s)\n")
    total = 0
    for cat in cats:
        n, assignments = await migrate_category(cat["id"], cat["title"])
        total += n
        by_p = " | ".join(f"p{d}:{assignments[d]:>3}" for d in range(1, 8))
        print(f"  {cat['id']:20} → {n:>4} questions | {by_p}")

    print(f"\nTotal : {total} questions {'mises à jour' if APPLY else '(simulation)'}")


if __name__ == "__main__":
    asyncio.run(main())
