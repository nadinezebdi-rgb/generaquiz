"""Conseil du jour « Bien vieillir » — écrit par Claude Sonnet chaque nuit,
relu par Claude Opus (exactitude + prudence santé), stocké dans `daily_tips`."""
from __future__ import annotations

import asyncio
import json
import os
import random
import re
import time
import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from emergentintegrations.llm.chat import LlmChat, UserMessage

from audit_and_regen_questions import FACT_CHECK_MODEL, GEN_MODEL
from core import db, logger

PARIS_TZ = ZoneInfo("Europe/Paris")
THEMES = ["alimentation", "activité physique", "sommeil", "mémoire", "lien social", "prévention", "moral & bien-être"]
MAX_ATTEMPTS = 3
_gen_lock = asyncio.Lock()
_RETRY_COOLDOWN_SEC = 30 * 60
_last_attempt: dict[str, float] = {}

WRITER_SYSTEM = """Tu es Lucette la Pétillante, mascotte du thème « Bien vieillir » de GénéraQuiz, un jeu familial pour seniors français.
Tu écris UN conseil du jour court, chaleureux et pratique, fondé sur les recommandations reconnues en France (Santé publique France, PNNS, HAS, OMS).
Règles : aucun médicament, aucun dosage, aucun diagnostic, aucune promesse de guérison, aucune marque. Vouvoiement. Ton bienveillant, jamais culpabilisant."""

REVIEW_SYSTEM = """Tu es médecin gériatre et relecteur exigeant. Tu vérifies qu'un conseil santé grand public destiné à des seniors est exact, prudent et conforme aux recommandations françaises/OMS.
Refuse tout conseil inexact, risqué, culpabilisant, contenant un médicament, un dosage ou un chiffre douteux.
Réponds UNIQUEMENT en JSON : {"ok": true|false, "raison": "1 phrase"}"""


QUIZ_REVIEW_SYSTEM = """Tu es médecin gériatre et vérificateur de quiz. Tu contrôles une question à choix multiples grand public liée à un conseil santé pour seniors.
Vérifie : la bonne réponse est exacte et sans ambiguïté, les 3 autres sont clairement fausses, l'explication est juste et prudente.
Réponds UNIQUEMENT en JSON : {"ok": true|false, "raison": "1 phrase"}"""


def today_key() -> str:
    return datetime.now(PARIS_TZ).strftime("%Y-%m-%d")


def _theme_for(date_key: str) -> str:
    return THEMES[datetime.strptime(date_key, "%Y-%m-%d").toordinal() % len(THEMES)]


def _parse_json(raw) -> dict | None:
    text = (raw if isinstance(raw, str) else str(raw)).strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


async def _ask(model: tuple[str, str], system: str, prompt: str) -> dict | None:
    chat = LlmChat(
        api_key=os.environ["EMERGENT_LLM_KEY"],
        session_id=f"tip-{uuid.uuid4().hex[:10]}",
        system_message=system,
    ).with_model(*model)
    try:
        return _parse_json(await chat.send_message(UserMessage(text=prompt)))
    except Exception as e:
        logger.warning(f"[daily-tip] appel {model[1]} échoué : {e}")
        return None


async def _write_and_review(theme: str, avoid: list[str]) -> dict | None:
    avoid_txt = "\n".join(f"- {t}" for t in avoid) or "(aucun)"
    prompt = f"""Thème du jour : {theme}

Ne reprends PAS ces conseils récents (ni leur idée) :
{avoid_txt}

Format JSON STRICT, rien d'autre :
{{"titre": "6 à 9 mots, accrocheur", "conseil": "2 à 3 phrases concrètes (max 320 caractères)", "astuce": "1 geste simple à faire aujourd'hui (max 120 caractères)"}}"""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        tip = await _ask(GEN_MODEL, WRITER_SYSTEM, prompt)
        if not tip or not all(isinstance(tip.get(k), str) and tip[k].strip() for k in ("titre", "conseil", "astuce")):
            continue
        review = await _ask(FACT_CHECK_MODEL, REVIEW_SYSTEM,
                            f"Titre : {tip['titre']}\nConseil : {tip['conseil']}\nAstuce : {tip['astuce']}")
        if review and review.get("ok") is True:
            return {"title": tip["titre"].strip(), "text": tip["conseil"].strip(),
                    "action": tip["astuce"].strip(), "review": review.get("raison", "")}
        logger.info(f"[daily-tip] tentative {attempt} refusée : {(review or {}).get('raison')}")
    return None


def _valid_quiz(q: dict | None) -> bool:
    return bool(
        q and isinstance(q.get("question"), str) and q["question"].strip()
        and isinstance(q.get("options"), list) and len(q["options"]) == 4
        and all(isinstance(o, str) and o.strip() for o in q["options"])
        and len({o.strip().lower() for o in q["options"]}) == 4
        and isinstance(q.get("bonne_reponse"), int) and 0 <= q["bonne_reponse"] <= 3
        and isinstance(q.get("explication"), str) and q["explication"].strip()
    )


async def write_tip_quiz(tip: dict) -> dict | None:
    """Une question QCM liée au conseil, écrite par Sonnet, vérifiée par Opus.
    Les options sont mélangées (l'IA met souvent la bonne en premier)."""
    prompt = f"""Conseil du jour :
Titre : {tip['title']}
Conseil : {tip['text']}
Geste : {tip['action']}

Écris UNE question de quiz simple qui teste ce que le lecteur vient d'apprendre dans ce conseil. 4 propositions courtes, une seule correcte.
Format JSON STRICT, rien d'autre :
{{"question": "max 140 caractères", "options": ["...", "...", "...", "..."], "bonne_reponse": 0, "explication": "1 phrase, max 200 caractères"}}"""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        q = await _ask(GEN_MODEL, WRITER_SYSTEM, prompt)
        if not _valid_quiz(q):
            continue
        good = q["options"][q["bonne_reponse"]]
        listing = "\n".join(f"- {o}{' (BONNE RÉPONSE)' if o == good else ''}" for o in q["options"])
        review = await _ask(FACT_CHECK_MODEL, QUIZ_REVIEW_SYSTEM,
                            f"Question : {q['question']}\nPropositions :\n{listing}\nExplication : {q['explication']}")
        if review and review.get("ok") is True:
            options = [o.strip() for o in q["options"]]
            random.shuffle(options)
            return {"question": q["question"].strip(), "options": options,
                    "correct_index": options.index(good.strip()), "explanation": q["explication"].strip()}
        logger.info(f"[daily-tip] quiz tentative {attempt} refusée : {(review or {}).get('raison')}")
    return None


async def backfill_tip_quizzes(limit: int = 30) -> int:
    """Ajoute une question aux conseils récents qui n'en ont pas encore."""
    added = 0
    async for tip in db.daily_tips.find(
        {"quiz": {"$exists": False}, "quiz_attempts": {"$not": {"$gte": 2}}}, {"_id": 0}
    ).sort("date_key", -1).limit(limit):
        quiz = await write_tip_quiz(tip)
        if not quiz:
            await db.daily_tips.update_one({"date_key": tip["date_key"]}, {"$inc": {"quiz_attempts": 1}})
        else:
            await db.daily_tips.update_one({"date_key": tip["date_key"], "quiz": {"$exists": False}},
                                           {"$set": {"quiz": quiz}})
            added += 1
    if added:
        logger.info(f"[daily-tip] {added} question(s) ajoutée(s) aux conseils existants")
    return added


async def generate_daily_tip(date_key: str | None = None) -> dict:
    """Idempotent : ne génère que si aucun conseil n'existe pour ce jour.
    Après un échec, nouvel essai au plus toutes les 30 min (pas de rafale IA)."""
    date_key = date_key or today_key()
    async with _gen_lock:
        existing = await db.daily_tips.find_one({"date_key": date_key}, {"_id": 0})
        if existing:
            return {"status": "exists", "date_key": date_key}
        if time.time() - _last_attempt.get(date_key, 0) < _RETRY_COOLDOWN_SEC:
            return {"status": "cooldown", "date_key": date_key}
        _last_attempt[date_key] = time.time()
        recent = await db.daily_tips.find({}, {"_id": 0, "title": 1}).sort("date_key", -1).to_list(30)
        theme = _theme_for(date_key)
        tip = await _write_and_review(theme, [r["title"] for r in recent])
        if not tip:
            logger.warning(f"[daily-tip] {date_key} : aucun conseil validé après {MAX_ATTEMPTS} tentatives")
            return {"status": "failed", "date_key": date_key}
        quiz = await write_tip_quiz(tip)
        if quiz:
            tip["quiz"] = quiz
        await db.daily_tips.update_one(
            {"date_key": date_key},
            {"$setOnInsert": {"date_key": date_key, "theme": theme, **tip,
                              "writer_model": GEN_MODEL[1], "reviewer_model": FACT_CHECK_MODEL[1],
                              "created_at": datetime.now(timezone.utc).isoformat()}},
            upsert=True,
        )
        logger.info(f"[daily-tip] {date_key} ({theme}) : « {tip['title']} »")
        return {"status": "created", "date_key": date_key}


async def daily_tip_job() -> None:
    """Cron 02:30 : conseil du jour + rattrapage des questions manquantes."""
    await generate_daily_tip()
    await backfill_tip_quizzes()
