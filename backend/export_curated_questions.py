"""Exporte les questions d'une catégorie (vérifiées + écartées) vers data/curated_questions/ pour la prod.

Usage : python export_curated_questions.py bien-vieillir annees-80 annees-2010
"""
import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")
OUT = ROOT / "data" / "curated_questions"


async def main(cats):
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    OUT.mkdir(parents=True, exist_ok=True)
    for cat in cats:
        docs = await db.questions.find(
            {"category_id": cat, "quality": {"$in": ["verified", "flagged"]}}, {"_id": 0}
        ).to_list(5000)
        (OUT / f"{cat}.json").write_text(json.dumps(docs, ensure_ascii=False, indent=1), encoding="utf-8")
        print(cat, len(docs), "dont vérifiées :", sum(d["quality"] == "verified" for d in docs))


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
