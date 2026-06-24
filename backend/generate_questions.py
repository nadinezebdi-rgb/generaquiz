"""Generate 70 additional quiz questions per category using Claude Sonnet 4.5.

Run: cd /app/backend && python generate_questions.py

Output: /app/backend/data/extra_questions/{category_id}.json
        70 high-quality multiple-choice questions per category.
"""
import asyncio
import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

from emergentintegrations.llm.chat import LlmChat, UserMessage  # noqa: E402

from seed_data import CATEGORIES, QUESTIONS  # noqa: E402

OUT_DIR = ROOT_DIR / "data" / "extra_questions"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# 70 new questions per category, split in batches of ~25 to stay within model context
BATCHES_PER_CATEGORY = [25, 25, 20]   # 70 total
TARGET_PER_CATEGORY = sum(BATCHES_PER_CATEGORY)

DIFFICULTY_GUIDANCE = {
    0: "Mélange équilibré : 8 questions FACILES (enfants/famille, niveau école primaire/collège), 10 questions MOYENNES (grand public), 7 questions DIFFICILES (passionnés/seniors connaisseurs).",
    1: "Mélange équilibré : 7 questions FACILES (enfants/famille), 11 questions MOYENNES (grand public), 7 questions DIFFICILES (connaisseurs).",
    2: "Mélange équilibré : 6 questions FACILES (enfants/famille), 8 questions MOYENNES (grand public), 6 questions DIFFICILES (connaisseurs)."
}


def build_prompt(category: dict, existing_questions: list[str], n: int, difficulty: str) -> str:
    existing_sample = "\n".join(f"- {q}" for q in existing_questions[:60])
    return f"""Tu es un expert en culture générale française et un concepteur de quiz pour un jeu familial intergénérationnel nommé "GénéraQuiz".

**CATÉGORIE** : {category['title']}
**DESCRIPTION** : {category['description']}

**MISSION** : Génère EXACTEMENT {n} nouvelles questions à choix multiple (QCM) en français pour cette catégorie.

**RÈGLES IMPÉRATIVES** :
1. Chaque question a EXACTEMENT 4 options de réponse.
2. UNE SEULE bonne réponse par question (index 0 à 3).
3. Les questions doivent être FACTUELLEMENT VÉRIFIABLES (pas d'opinions ni d'ambiguïtés).
4. Évite absolument les questions piège, à interprétation, ou dont la réponse a évolué.
5. Pour les dates précises, donne 4 options bien distinctes (écart ≥ 2 ans entre options proches).
6. Les explications doivent être courtes (1-2 phrases max), pédagogiques et exactes.
7. **VARIÉTÉ DE DIFFICULTÉ** : {difficulty}
8. **PUBLIC** : enfants, parents, grands-parents jouant ensemble en famille.
9. NE PAS répéter ni paraphraser les questions existantes listées ci-dessous.

**QUESTIONS DÉJÀ EXISTANTES (à ne pas reproduire ni paraphraser)** :
{existing_sample}

**FORMAT DE SORTIE STRICT** (uniquement du JSON valide, aucun texte avant ou après, aucun bloc markdown) :
[
  {{"question": "Texte de la question ?", "options": ["Opt A", "Opt B", "Opt C", "Opt D"], "correct_index": 0, "explanation": "Courte explication factuelle."}},
  ...
]

Réponds uniquement avec le tableau JSON, rien d'autre."""


def extract_json(text: str):
    text = text.strip()
    # Remove markdown fences if present
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1:
        raise ValueError("No JSON array found in model output")
    return json.loads(text[start:end + 1])


async def generate_for_category(category: dict, existing_q_texts: list[str], previously_generated: list[dict]):
    out_path = OUT_DIR / f"{category['id']}.json"
    if out_path.exists():
        existing = json.loads(out_path.read_text())
        if len(existing) >= TARGET_PER_CATEGORY:
            print(f"[skip] {category['id']} already has {len(existing)} extra questions")
            return existing

    api_key = os.environ["EMERGENT_LLM_KEY"]
    all_generated: list[dict] = list(previously_generated)
    seen_texts = {q.lower().strip() for q in existing_q_texts}
    for q in all_generated:
        seen_texts.add(q["question"].lower().strip())

    for batch_idx, batch_size in enumerate(BATCHES_PER_CATEGORY):
        needed = batch_size
        attempts = 0
        while needed > 0 and attempts < 3:
            attempts += 1
            difficulty = DIFFICULTY_GUIDANCE[batch_idx]
            # Build prompt with already-seen questions to avoid duplicates
            seen_list = existing_q_texts + [q["question"] for q in all_generated]
            prompt = build_prompt(category, seen_list, needed, difficulty)
            chat = LlmChat(
                api_key=api_key,
                session_id=f"qgen-{category['id']}-{batch_idx}-{attempts}",
                system_message="Tu es un expert pédagogue francophone, méticuleux et factuel. Tu réponds uniquement en JSON valide."
            ).with_model("anthropic", "claude-sonnet-4-5-20250929")
            try:
                response = await chat.send_message(UserMessage(text=prompt))
                items = extract_json(response)
            except Exception as e:
                print(f"  [retry] {category['id']} batch {batch_idx} attempt {attempts}: {e}")
                await asyncio.sleep(2)
                continue

            added_this_call = 0
            for item in items:
                if not isinstance(item, dict):
                    continue
                q_text = item.get("question", "").strip()
                opts = item.get("options")
                idx = item.get("correct_index")
                expl = item.get("explanation", "").strip()
                if not q_text or not isinstance(opts, list) or len(opts) != 4:
                    continue
                if not isinstance(idx, int) or not (0 <= idx <= 3):
                    continue
                key = q_text.lower().strip()
                if key in seen_texts:
                    continue
                seen_texts.add(key)
                all_generated.append({
                    "question": q_text,
                    "options": [str(o) for o in opts],
                    "correct_index": idx,
                    "explanation": expl,
                })
                added_this_call += 1
                if added_this_call >= needed:
                    break
            needed -= added_this_call
            print(f"  [{category['id']}] batch {batch_idx + 1}/3 attempt {attempts}: +{added_this_call} (still need {needed})")

    # Cap at target and persist
    all_generated = all_generated[:TARGET_PER_CATEGORY]
    out_path.write_text(json.dumps(all_generated, ensure_ascii=False, indent=2))
    print(f"[done] {category['id']}: {len(all_generated)} extra questions written -> {out_path}")
    return all_generated


async def main():
    # Map existing question texts per category (to avoid duplicates)
    existing_by_cat: dict[str, list[str]] = {}
    for q in QUESTIONS:
        existing_by_cat.setdefault(q["category_id"], []).append(q["question"])

    only = os.environ.get("ONLY_CATEGORY")
    cats = [c for c in CATEGORIES if (not only or c["id"] == only)]

    for cat in cats:
        prev_path = OUT_DIR / f"{cat['id']}.json"
        prev = json.loads(prev_path.read_text()) if prev_path.exists() else []
        await generate_for_category(cat, existing_by_cat.get(cat["id"], []), prev)


if __name__ == "__main__":
    asyncio.run(main())
