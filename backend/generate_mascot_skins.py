"""Generate mascot skin variants (Sprint 3 — Mascot Affection).

For each of the 8 categories we generate 3 "affection" skin variants using the
same base mascot but with a visual reward twist:

  - level 1 (apprenti) : "friendly wave" — same character, adds a small props
  - level 2 (confirmé) : "in action" — dynamic pose, engaged with theme
  - level 3 (maître)   : "hero" — golden accents, aura, celebratory

Output: /app/backend/static/mascots/<slug>_skin{1|2|3}.png
Run once: `cd /app/backend && python generate_mascot_skins.py`
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

# (slug, base description, [skin1_extra, skin2_extra, skin3_extra])
BASE_PALETTE = (
    "Bright cartoon palette of terracotta orange (#E07A5F), navy blue (#1E3A5F), "
    "mustard yellow (#F2CC8F), cream (#F4F1DE), and bordeaux (#722F37). "
    "Big expressive cartoon eyes, exaggerated friendly features. "
    "Solid cream background (#F4F1DE), centered character, square framing, "
    "no text, no watermark, soft shadow under character."
)

MASCOTS = [
    ("annees-50-60",
     "A modern colorful cartoon caricature portrait of a happy French man in his 60s, 1950s style, pomade slicked-back hair, thin moustache",
     [
         "wearing a blue polo shirt and white pants, giving a friendly small wave",
         "in action tuning a vintage rotary television set with rabbit-ear antennas, sparkles around it, tongue slightly out concentrating",
         "in a golden yellow spotlight, wearing a golden crown, radiant celebratory smile, glowing golden aura",
     ]),
    ("chansons",
     "A modern colorful cartoon caricature portrait of a joyful elegant French chanteuse, woman in her 60s with curly red hair like Édith Piaf, red lipstick, long black evening gown",
     [
         "holding a vintage chrome microphone lowered, gently waving hello, mouth in a small confident smile",
         "in dynamic singing pose, arms wide, mouth open belting a note, musical notes floating around, spotlight beam",
         "on a grand golden theatre stage, standing under a golden spotlight aura, holding a golden microphone, confetti falling, celebratory pose",
     ]),
    ("cinema",
     "A modern colorful cartoon caricature portrait of a French cinema projectionist man in his 60s, big moustache, red usher hat and bow tie, navy blue uniform",
     [
         "holding a small film reel, one hand raised in a friendly wave",
         "in the projection booth, operating a vintage film projector with beam of light coming out, film strips floating around",
         "standing on a red carpet holding a golden film reel trophy, golden aura, popcorn confetti flying, celebratory smile",
     ]),
    ("objets-antan",
     "A modern colorful cartoon caricature portrait of a sweet French grandma in her 70s, white hair in a bun, round glasses, floral blue and terracotta dress with white apron",
     [
         "holding a vintage rotary telephone receiver near her ear, giving a small welcoming wave",
         "actively winding up a mechanical alarm clock, surrounded by floating vintage objects: iron, kettle, transistor radio",
         "in a golden armchair, surrounded by warm golden aura, holding a golden treasure box overflowing with vintage trinkets, radiant proud smile",
     ]),
    ("histoire-france",
     "A modern colorful cartoon caricature portrait of a stately French history professor man in his 60s, white moustache, navy blue military kepi cap with gold trim, navy blue jacket with brass buttons",
     [
         "holding a rolled scroll, small French flag behind him, one hand raised in a friendly salute",
         "in front of a large historical map, actively pointing to a location with a wooden stick, papers flying around him",
         "on a marble pedestal, wearing a golden ceremonial sash, holding a golden scepter, French flag behind him unfurling, radiant golden aura, celebratory pose",
     ]),
    ("cuisine-terroir",
     "A modern colorful cartoon caricature portrait of a jolly French chef man in his 60s, big curly moustache, plump cheeks, tall white chef hat (toque), white double-breasted chef jacket with red kerchief",
     [
         "holding a wooden spoon lowered, giving a friendly small wave with the other hand, warm smile",
         "in action stirring a large steaming pot of bouillabaisse, tossing herbs in the air, ingredients flying around",
         "standing on a golden restaurant kitchen podium with a golden chef hat, holding a golden Michelin star, golden aura, celebratory triumphant smile, sparkles",
     ]),
    ("culture-40-ans",
     "A modern colorful cartoon caricature portrait of a stylish smiling French woman in her early 40s, shoulder-length brown wavy hair with subtle highlights, fashionable round glasses, denim jacket over a striped top",
     [
         "holding a smartphone in one hand and a vinyl record in the other, casual friendly wave",
         "actively DJing, headphones on, hands on a turntable, musical notes and floppy disks flying around, energetic pose",
         "on a golden neon-lit stage with 90s icons floating (Game Boy, cassette tape, floppy disk) all gold-plated, wearing a golden headset, radiant golden aura, celebratory pose",
     ]),
    ("culture-70-ans",
     "A modern colorful cartoon caricature portrait of a wise distinguished French man in his early 70s, neatly trimmed grey beard, round reading glasses on his nose, tweed jacket with elbow patches over a sweater vest",
     [
         "holding an open hardback book and a pipe (not lit), small friendly wave with the other hand",
         "in his study surrounded by floating books, a globe spinning, telescope pointed to the ceiling, actively reading with intense curiosity",
         "on a marble library platform with golden books floating around him, wearing a golden scholarly medal, radiant golden aura, celebratory wise smile",
     ]),
]

SKIN_SUFFIX = ["_skin1", "_skin2", "_skin3"]  # 0 = base image already exists


async def generate_variant(slug: str, base_desc: str, variant_desc: str, suffix: str):
    out_path = OUT_DIR / f"{slug}{suffix}.png"
    if out_path.exists() and out_path.stat().st_size > 5000:
        print(f"[skip] {slug}{suffix} already exists")
        return
    prompt = f"{base_desc}, {variant_desc}. {BASE_PALETTE}"
    api_key = os.environ["EMERGENT_LLM_KEY"]
    chat = LlmChat(
        api_key=api_key,
        session_id=f"mascot-skin-{slug}{suffix}",
        system_message="You are a master cartoon illustrator generating warm modern caricature mascot skins.",
    )
    chat.with_model("gemini", "gemini-3.1-flash-image-preview").with_params(modalities=["image", "text"])
    msg = UserMessage(text=prompt)
    text, images = await chat.send_message_multimodal_response(msg)
    print(f"[{slug}{suffix}] text: {(text or '')[:60]}")
    if not images:
        print(f"[{slug}{suffix}] NO IMAGE")
        return
    data = base64.b64decode(images[0]["data"])
    out_path.write_bytes(data)
    print(f"[{slug}{suffix}] saved {len(data)} bytes -> {out_path.name}")


async def main():
    for slug, base_desc, variants in MASCOTS:
        for i, v in enumerate(variants):
            suffix = SKIN_SUFFIX[i]
            try:
                await generate_variant(slug, base_desc, v, suffix)
            except Exception as e:
                print(f"[{slug}{suffix}] ERROR: {e}")


if __name__ == "__main__":
    asyncio.run(main())
