"""One-time mascot generation script using Gemini Nano Banana via Emergent universal key.

Run: cd /app/backend && python generate_mascots.py
"""
import asyncio
import base64
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

from emergentintegrations.llm.chat import LlmChat, UserMessage

OUT_DIR = ROOT_DIR / "static" / "mascots"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Modern colorful cartoon caricature style mascots (one per category)
MASCOTS = [
    ("annees-50-60",
     "A modern colorful cartoon caricature portrait of a happy French man in his 60s wearing a 1950s style outfit: pomade slicked-back hair, thin moustache, blue polo shirt, white pants, sitting next to a vintage wooden television set with rabbit-ear antennas. Bright cheerful palette of terracotta orange, navy blue, cream and mustard yellow. Round friendly face, big expressive eyes, exaggerated cartoon features. Solid cream background (#F4F1DE), centered character, square framing, no text, no watermark, soft shadow under character."),
    ("chansons",
     "A modern colorful cartoon caricature portrait of a joyful elegant French chanteuse, woman in her 60s with curly red hair like Édith Piaf, red lipstick, long black evening gown, holding a vintage chrome microphone, mouth open singing. Bright palette terracotta, deep bordeaux red, cream and mustard. Big expressive cartoon eyes, exaggerated features. Solid cream background (#F4F1DE), centered character, square framing, no text."),
    ("cinema",
     "A modern colorful cartoon caricature portrait of a French cinema projectionist man in his 60s, big moustache, wearing a red usher hat and bow tie, holding a vintage film reel, beret cocked sideways. Style is bright cartoon with navy blue uniform, terracotta accents, mustard yellow film reel. Big friendly eyes, exaggerated features. Solid cream background (#F4F1DE), centered character, square framing, no text."),
    ("objets-antan",
     "A modern colorful cartoon caricature portrait of a sweet French grandma in her 70s, white hair in a bun, round glasses, floral blue and terracotta dress with white apron, holding a vintage rotary telephone receiver to her ear. Warm friendly smile, rosy cheeks, big expressive cartoon eyes. Bright cheerful palette: terracotta, mustard, cream, navy accents. Solid cream background (#F4F1DE), centered, square framing, no text."),
    ("histoire-france",
     "A modern colorful cartoon caricature portrait of a stately French history professor man in his 60s, white moustache, wearing a navy blue military kepi cap with gold trim, a navy blue jacket with brass buttons, holding a rolled scroll. Behind him a small French flag. Bright cartoon palette: navy blue uniform, terracotta scroll, mustard accents, cream skin. Big friendly cartoon eyes. Solid cream background (#F4F1DE), centered, square framing, no text."),
    ("cuisine-terroir",
     "A modern colorful cartoon caricature portrait of a jolly French chef man in his 60s, big curly moustache, plump cheeks, tall white chef hat (toque), white double-breasted chef jacket with red kerchief, holding a wooden spoon and a steaming pot of soup. Round happy face, big expressive eyes. Bright cartoon palette: terracotta apron, mustard pot, cream and navy accents. Solid cream background (#F4F1DE), centered, square framing, no text."),
]


async def generate_one(slug: str, prompt: str):
    out_path = OUT_DIR / f"{slug}.png"
    if out_path.exists() and out_path.stat().st_size > 5000:
        print(f"[skip] {slug} already exists")
        return
    api_key = os.environ["EMERGENT_LLM_KEY"]
    chat = LlmChat(
        api_key=api_key,
        session_id=f"mascot-{slug}",
        system_message="You are a master cartoon illustrator generating warm modern caricature mascots.",
    )
    chat.with_model("gemini", "gemini-3.1-flash-image-preview").with_params(modalities=["image", "text"])
    msg = UserMessage(text=prompt)
    text, images = await chat.send_message_multimodal_response(msg)
    print(f"[{slug}] text response: {(text or '')[:60]}")
    if not images:
        print(f"[{slug}] no image generated")
        return
    img = images[0]
    data = base64.b64decode(img["data"])
    out_path.write_bytes(data)
    print(f"[{slug}] saved -> {out_path} ({len(data)} bytes)")


async def main():
    for slug, prompt in MASCOTS:
        try:
            await generate_one(slug, prompt)
        except Exception as e:
            print(f"[{slug}] ERROR: {e}")


if __name__ == "__main__":
    asyncio.run(main())
