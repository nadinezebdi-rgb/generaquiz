"""Génère les couvertures illustrées des 10 chapitres du Livre de Vie.

Aquarelles douces et chaleureuses, palette maison (terracotta / navy / mustard /
cream / bordeaux). Style intergénérationnel, tendre, sans texte, orientation
carrée, prêt à être affiché en tête de chapitre dans l'app.

Sortie : /app/backend/static/livre_covers/<chapter_id>.png
Run once : `cd /app/backend && python generate_livre_covers.py`
"""
import asyncio
import base64
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

from emergentintegrations.llm.chat import LlmChat, UserMessage  # noqa: E402

OUT_DIR = ROOT_DIR / "static" / "livre_covers"
OUT_DIR.mkdir(parents=True, exist_ok=True)

PALETTE = (
    "Watercolor illustration, soft and warm. Palette limited to terracotta orange (#E07A5F), "
    "navy blue (#1E3A5F), mustard yellow (#F2CC8F), cream (#F4F1DE), bordeaux (#722F37). "
    "Gentle intergenerational feel, tender atmosphere. Centered subject, square framing, "
    "cream paper texture background. No text, no watermark, no faces close-up."
)

COVERS = [
    ("enfance",
     "A child's toy pram, a plush teddy bear and colored wooden blocks on a soft rug"),
    ("ecole",
     "An open vintage school notebook, an inkwell, a wooden ruler and a small red apple on a wooden desk"),
    ("adolescence",
     "A vintage transistor radio, headphones with a cassette tape and a rose flower"),
    ("rencontres",
     "Two hands gently holding a small folded love letter next to a bouquet of wildflowers"),
    ("metier",
     "Vintage tools of many trades stacked: a leather-bound ledger, a fountain pen, a set of keys and small round glasses"),
    ("famille",
     "A round dinner table set for a family meal: soup tureen, warm bread, three cloth napkins tied with ribbon"),
    ("voyages",
     "An old leather suitcase covered with travel stickers, a compass, a folded map and a straw hat"),
    ("passions",
     "A vinyl record, watercolor paints and brushes, a chess piece, and a small potted plant clustered together"),
    ("epreuves",
     "A young oak tree growing from a crack in an old stone, gentle sunrise light and morning dew"),
    ("transmission",
     "A hand-written recipe card, a wax-sealed envelope tied with twine, and a small burning candle"),
]


async def generate_cover(chapter_id: str, subject: str) -> None:
    out = OUT_DIR / f"{chapter_id}.png"
    if out.exists() and out.stat().st_size > 5000:
        print(f"[skip] {chapter_id} déjà généré")
        return
    prompt = f"{subject}. {PALETTE}"
    api_key = os.environ["EMERGENT_LLM_KEY"]
    chat = LlmChat(
        api_key=api_key,
        session_id=f"livre-cover-{chapter_id}",
        system_message="You are a watercolor illustrator drawing warm intergenerational chapter covers.",
    )
    chat.with_model("gemini", "gemini-3.1-flash-image-preview").with_params(modalities=["image", "text"])
    msg = UserMessage(text=prompt)
    _, images = await chat.send_message_multimodal_response(msg)
    if not images:
        print(f"[{chapter_id}] AUCUNE IMAGE")
        return
    data = base64.b64decode(images[0]["data"])
    out.write_bytes(data)
    print(f"[{chapter_id}] {len(data)} octets → {out.name}")


async def main():
    for cid, subject in COVERS:
        try:
            await generate_cover(cid, subject)
        except Exception as e:
            print(f"[{cid}] ERROR: {e}")


if __name__ == "__main__":
    asyncio.run(main())
