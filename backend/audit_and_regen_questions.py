"""Pipeline de qualité IA pour les questions de quiz — audit + fact-check + régénération.

Étapes (par catégorie) :
    1. LOAD des questions existantes en DB pour la catégorie
    2. FACT-CHECK de chaque question via Claude Opus 4.8 :
       - Est-ce que la réponse déclarée est vraiment correcte ?
       - Est-ce que les 3 autres options sont clairement fausses ?
       - Est-ce que la formulation est ambiguë ?
       Résultat: JSON {verdict, confidence, comment, correction?}
    3. Marque les questions "verified" / "flagged" en DB :
       - verified : confidence >= 85 ET verdict == "correct"
       - flagged  : sinon (exclues automatiquement du tirage côté quiz.py)
    4. REGEN : pour chaque question flagged, génère un remplaçant via Claude
       Sonnet 4.6 avec un prompt plus strict, puis re-passe par le fact-check.
       Insère uniquement si le remplaçant est verified.

Usage :
    python audit_and_regen_questions.py                 # toutes catégories
    ONLY_CATEGORY=chansons python audit_and_regen_questions.py  # une catégorie
    LIMIT=20 python audit_and_regen_questions.py       # 20 questions max/cat
    DRY_RUN=1 python audit_and_regen_questions.py      # sans écrire en DB

Résumé écrit dans /tmp/qa_report_{category}.json.
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

from emergentintegrations.llm.chat import LlmChat, UserMessage  # noqa: E402
from motor.motor_asyncio import AsyncIOMotorClient              # noqa: E402

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
EMERGENT_LLM_KEY = os.environ["EMERGENT_LLM_KEY"]

FACT_CHECK_MODEL = ("anthropic", "claude-opus-4-8")
GEN_MODEL = ("anthropic", "claude-sonnet-4-6")

CONFIDENCE_THRESHOLD = 85   # en dessous → flagged
DRY_RUN = os.environ.get("DRY_RUN") == "1"

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]


# ============================================================================
# 1. FACT-CHECK — Claude Opus 4.8
# ============================================================================

FACT_CHECK_SYSTEM = """Tu es un vérificateur factuel expert de culture générale francophone. Tu es méticuleux, prudent et intransigeant sur l'exactitude.

Pour chaque question de quiz qu'on te soumet, tu dois :
1. Vérifier si la réponse marquée "correct" est vraiment la bonne réponse factuellement.
2. Vérifier si les 3 autres options sont clairement fausses (pas ambiguës).
3. Détecter les erreurs classiques : dates approximatives, artistes confondus, œuvres attribuées à tort, chiffres inventés.
4. Détecter les questions à interprétation, opinions déguisées en faits, ou questions dont la réponse a changé (ex : "actuel président", "dernier film").

Réponds UNIQUEMENT en JSON valide, sans markdown, sans texte avant ou après :

{"verdict": "correct" | "doubtful" | "wrong", "confidence": 0-100, "comment": "1 phrase max justifiant le verdict", "correction": "réponse exacte si différente, sinon null"}

Règles :
- "correct" + confidence >= 90 : tu es certain que la question et sa réponse sont exactes.
- "doubtful" : ambigu, imprécis, ou tu n'es pas sûr à 100%.
- "wrong" : la réponse marquée correcte est fausse.
- confidence < 90 → le score doit refléter ta VRAIE certitude, pas un score de politesse."""


async def fact_check_question(q: dict[str, Any]) -> dict[str, Any]:
    """Retourne {verdict, confidence, comment, correction} pour une question."""
    correct_answer = q["options"][q["correct_index"]]
    prompt = f"""QUESTION : {q['question']}

OPTIONS :
  A. {q['options'][0]}
  B. {q['options'][1]}
  C. {q['options'][2]}
  D. {q['options'][3]}

RÉPONSE MARQUÉE COMME CORRECTE : {chr(65 + q['correct_index'])}. {correct_answer}

EXPLICATION FOURNIE : {q.get('explanation', '(aucune)')}

Vérifie et réponds en JSON."""
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"fc-{q['id']}",
        system_message=FACT_CHECK_SYSTEM,
    ).with_model(*FACT_CHECK_MODEL)

    try:
        raw = await chat.send_message(UserMessage(text=prompt))
    except Exception as e:
        return {"verdict": "error", "confidence": 0, "comment": str(e)[:120], "correction": None}

    text = raw.strip() if isinstance(raw, str) else str(raw)
    # Enlève d'éventuels blocs markdown
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return {"verdict": "error", "confidence": 0, "comment": "JSON absent", "correction": None}
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError as e:
        return {"verdict": "error", "confidence": 0, "comment": f"JSON invalide: {e}", "correction": None}

    return {
        "verdict": data.get("verdict", "error"),
        "confidence": int(data.get("confidence", 0) or 0),
        "comment": (data.get("comment") or "")[:300],
        "correction": data.get("correction"),
    }


# ============================================================================
# 2. RÉGÉNÉRATION — Claude Sonnet 4.6 avec prompt strict
# ============================================================================

GEN_SYSTEM = """Tu es un concepteur de quiz français, historien-vérificateur avant tout. Chaque question que tu produis doit être un fait établi, sourçable dans Wikipédia français ou une encyclopédie classique.

RÈGLES INVIOLABLES :
1. Aucune date approximative. Si tu n'es pas certain d'une année précise, choisis une AUTRE question.
2. Aucun artiste, auteur, ou personnage inventé.
3. Une seule bonne réponse absolument, les 3 distracteurs doivent être clairement faux.
4. Aucune question sur "l'actualité", "le dernier", "l'actuel" — les faits doivent être stables dans le temps.
5. Aucune question à interprétation ("Quel est le meilleur film...", "Qui est le plus grand...").
6. Explication courte (1-2 phrases) contenant l'année ou la source pour aider la vérification."""


async def generate_replacement(category: dict, avoid_texts: list[str]) -> dict[str, Any] | None:
    """Génère UNE question de remplacement pour la catégorie donnée."""
    avoid_sample = "\n".join(f"- {t}" for t in avoid_texts[:40])
    prompt = f"""Catégorie : {category['title']}
Description : {category.get('description', '')}

Génère UNE question à choix multiple (4 options, 1 correcte), factuellement irréprochable.

Ne reproduis PAS les questions suivantes (ni leur paraphrase) :
{avoid_sample}

Format JSON strict, rien d'autre :
{{"question": "...", "options": ["A", "B", "C", "D"], "correct_index": 0, "explanation": "..."}}"""
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"gen-{category['id']}-{time.time()}",
        system_message=GEN_SYSTEM,
    ).with_model(*GEN_MODEL)

    try:
        raw = await chat.send_message(UserMessage(text=prompt))
    except Exception as e:
        print(f"    [gen] error: {e}")
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


# ============================================================================
# 3. PIPELINE PRINCIPAL
# ============================================================================

async def audit_category(category: dict, limit: int | None = None) -> dict:
    cat_id = category["id"]
    print(f"\n=== Catégorie: {cat_id} ({category['title']}) ===")

    query = {"category_id": cat_id}
    if limit:
        questions = await db.questions.find(query).limit(limit).to_list(limit)
    else:
        questions = await db.questions.find(query).to_list(500)
    print(f"  {len(questions)} questions à auditer")

    report = {"category_id": cat_id, "total": len(questions), "verified": 0, "flagged": 0, "regenerated": 0, "regen_failed": 0, "flagged_details": []}
    good_texts: list[str] = []

    for i, q in enumerate(questions, 1):
        result = await fact_check_question(q)
        verdict = result["verdict"]
        conf = result["confidence"]
        is_ok = verdict == "correct" and conf >= CONFIDENCE_THRESHOLD

        status_label = "OK ✓" if is_ok else f"⚠ {verdict}/{conf}"
        print(f"  [{i}/{len(questions)}] {status_label} — {q['question'][:60]}")

        # Mise à jour du statut en DB
        update = {
            "quality": "verified" if is_ok else "flagged",
            "fact_check": {
                "verdict": verdict,
                "confidence": conf,
                "comment": result["comment"],
                "correction": result["correction"],
                "checked_at": time.time(),
                "checker_model": FACT_CHECK_MODEL[1],
            },
        }
        if not DRY_RUN:
            await db.questions.update_one({"id": q["id"]}, {"$set": update})

        if is_ok:
            report["verified"] += 1
            good_texts.append(q["question"])
        else:
            report["flagged"] += 1
            report["flagged_details"].append({
                "id": q["id"],
                "question": q["question"],
                "correct_marked": q["options"][q["correct_index"]],
                "verdict": verdict,
                "confidence": conf,
                "comment": result["comment"],
                "correction": result["correction"],
            })

            # Génération d'un remplaçant + fact-check du remplaçant
            new_q = await generate_replacement(category, good_texts + [q["question"]])
            if not new_q:
                report["regen_failed"] += 1
                continue

            check = await fact_check_question({**new_q, "id": f"tmp-{i}"})
            if check["verdict"] == "correct" and check["confidence"] >= CONFIDENCE_THRESHOLD:
                new_doc = {
                    "id": f"gen_{cat_id}_{int(time.time()*1000)}_{i}",
                    "category_id": cat_id,
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
                    },
                }
                if not DRY_RUN:
                    await db.questions.insert_one(new_doc)
                report["regenerated"] += 1
                good_texts.append(new_q["question"])
                print(f"    → ✅ regen OK (confidence {check['confidence']})")
            else:
                report["regen_failed"] += 1
                print(f"    → ❌ regen refusé ({check['verdict']}/{check['confidence']})")

    out = Path(f"/tmp/qa_report_{cat_id}.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\n  Rapport : {out}")
    print(f"  Verified: {report['verified']} · Flagged: {report['flagged']} · Regénérées: {report['regenerated']} · Échec regen: {report['regen_failed']}")
    return report


async def main():
    only = os.environ.get("ONLY_CATEGORY")
    limit_env = os.environ.get("LIMIT")
    limit = int(limit_env) if limit_env else None

    cats = await db.categories.find({}, {"_id": 0}).to_list(50)
    if only:
        cats = [c for c in cats if c["id"] == only]
    if not cats:
        print(f"Aucune catégorie trouvée (only={only})")
        return

    all_reports = []
    for cat in cats:
        rep = await audit_category(cat, limit=limit)
        all_reports.append(rep)

    total = sum(r["total"] for r in all_reports)
    verified = sum(r["verified"] for r in all_reports)
    flagged = sum(r["flagged"] for r in all_reports)
    regen = sum(r["regenerated"] for r in all_reports)
    print(f"\n\n===== SYNTHÈSE ({len(cats)} catégorie(s)) =====")
    print(f"  Total audités : {total}")
    print(f"  Verified      : {verified} ({verified*100//max(total,1)}%)")
    print(f"  Flagged       : {flagged}")
    print(f"  Regénérées OK : {regen}")


if __name__ == "__main__":
    asyncio.run(main())
