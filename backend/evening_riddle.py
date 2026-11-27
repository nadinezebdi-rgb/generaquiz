"""Énigme du soir : une petite devinette familiale écrite par Claude chaque jour, à résoudre ensemble au dîner."""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo

import resend
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from ai_client import ai_complete
from core import db, get_current_user, logger, FRONTEND_URL, JWT_SECRET, RESEND_API_KEY, SENDER_EMAIL

router = APIRouter(prefix="/enigme", tags=["enigme"])
PARIS = ZoneInfo("Europe/Paris")
_lock = asyncio.Lock()

PROMPT = """Écris UNE énigme (devinette) en français pour une famille réunie au dîner : grands-parents, parents et enfants de 8 ans.
Règles :
- 3 à 5 phrases courtes, à lire à voix haute, ton chaleureux et malicieux ;
- la réponse est un objet, un animal, un métier, un aliment ou une chose du quotidien que tout le monde connaît, d'hier ou d'aujourd'hui ;
- solvable par logique et bon sens, sans culture spécialisée, sans calcul, rien d'effrayant ni de triste ;
- un indice qui aide sans donner la réponse ;
- une courte explication qui relie chaque phrase à la réponse, et une question pour lancer la conversation entre générations.
Réponses déjà utilisées, à NE PAS reprendre : {avoid}.
Réponds uniquement avec ce JSON :
{{"titre": "...", "enigme": "...", "indice": "...", "reponse": "...", "explication": "...", "question_famille": "..."}}"""

FIELDS = ("titre", "enigme", "indice", "reponse", "explication", "question_famille")


def today() -> str:
    return datetime.now(PARIS).date().isoformat()


async def _generate(date: str) -> dict:
    avoid = [r["reponse"] async for r in db.evening_riddles.find({}, {"_id": 0, "reponse": 1}).sort("date", -1).limit(40)]
    for _ in range(3):
        raw = await ai_complete(PROMPT.format(avoid=", ".join(avoid) or "aucune"), max_tokens=800, tag="enigme")
        start = raw.find("{")
        try:
            data, _ = json.JSONDecoder().raw_decode(raw[start:]) if start >= 0 else (None, 0)
        except ValueError:
            data = None
        if data and all(isinstance(data.get(k), str) and data[k].strip() for k in FIELDS) \
                and data["reponse"].strip().lower() not in {a.lower() for a in avoid}:
            return {"date": date, **{k: data[k].strip() for k in FIELDS},
                    "created_at": datetime.now(PARIS).isoformat()}
    raise RuntimeError("énigme invalide après 3 essais")


async def get_or_create(date: str | None = None) -> dict:
    date = date or today()
    found = await db.evening_riddles.find_one({"date": date}, {"_id": 0})
    if found:
        return found
    async with _lock:
        found = await db.evening_riddles.find_one({"date": date}, {"_id": 0})
        if found:
            return found
        doc = await _generate(date)
        await db.evening_riddles.insert_one(dict(doc))
        logger.info(f"[enigme] {date} : « {doc['titre']} » ({doc['reponse']})")
        return doc


async def prepare_tonight() -> None:
    """Tâche planifiée de l'après-midi : l'énigme est prête avant le dîner."""
    try:
        await get_or_create()
    except Exception as e:
        logger.error(f"[enigme] génération impossible : {e}")


@router.get("/today")
async def riddle_today(_: dict = Depends(get_current_user)) -> dict:
    try:
        return await get_or_create()
    except Exception as e:
        logger.error(f"[enigme] génération impossible : {e}")
        raise HTTPException(status_code=503, detail="L'énigme du soir se prépare, revenez dans un instant.")


# ------------------------------------------------------------------ e-mail de 18 h (sur abonnement)
class RiddleEmailPref(BaseModel):
    enabled: bool


@router.put("/email-pref")
async def set_email_pref(body: RiddleEmailPref, user: dict = Depends(get_current_user)) -> dict:
    await db.users.update_one({"_id": user["_id"]}, {"$set": {"riddle_email_optin": body.enabled}})
    return {"riddle_email_optin": body.enabled}


def _unsub_sig(user_id: str) -> str:
    return hmac.new(JWT_SECRET.encode(), f"riddle-unsub:{user_id}".encode(), hashlib.sha256).hexdigest()[:32]


def _page(title: str, text: str) -> HTMLResponse:
    return HTMLResponse(
        f"<!doctype html><html lang='fr'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{escape(title)} — GénéraQuiz</title></head><body style='background:#FDFBF7;font-family:Arial,sans-serif;color:#1A2530;"
        f"padding:32px 16px'><div style='max-width:560px;margin:auto;background:#fff;border:2px solid #EFE9DC;border-radius:24px;padding:28px'>"
        f"{text}<p style='margin-top:28px'><a href='{FRONTEND_URL}/app/dashboard' style='background:#E07A5F;color:#fff;padding:12px 24px;"
        f"border-radius:999px;text-decoration:none;font-weight:bold'>Aller sur GénéraQuiz</a></p></div></body></html>")


@router.get("/desinscription", response_class=HTMLResponse)
async def unsubscribe(u: str, s: str):
    if not ObjectId.is_valid(u) or not hmac.compare_digest(s, _unsub_sig(u)):
        raise HTTPException(status_code=400, detail="Lien invalide")
    await db.users.update_one({"_id": ObjectId(u)}, {"$set": {"riddle_email_optin": False}})
    return _page("Désinscription", "<h1 style='font-family:Georgia,serif;color:#1E3A5F'>C'est noté</h1>"
                 "<p style='font-size:18px'>Vous ne recevrez plus l'énigme du soir par e-mail. Vous pouvez la réactiver à tout moment dans Mon compte.</p>")


@router.get("/{date}/reponse", response_class=HTMLResponse)
async def answer_page(date: str):
    """Page publique ouverte depuis l'e-mail : la réponse n'est montrée qu'à ceux qui cliquent."""
    r = await db.evening_riddles.find_one({"date": date}, {"_id": 0})
    if not r or date > today():
        raise HTTPException(status_code=404, detail="Énigme introuvable")
    return _page("Réponse de l'énigme du soir",
                 f"<p style='color:#E07A5F;font-weight:bold;text-transform:uppercase;letter-spacing:1px;font-size:13px'>La réponse de l'énigme du soir</p>"
                 f"<h1 style='font-family:Georgia,serif;color:#7A2E3A;font-size:34px;margin:8px 0'>{escape(r['reponse'])}</h1>"
                 f"<p style='font-size:18px;line-height:1.5'>{escape(r['explication'])}</p>"
                 f"<p style='font-size:18px;background:#F4F1DE;border-radius:16px;padding:14px 18px'><strong>À vous de raconter :</strong> {escape(r['question_famille'])}</p>")


def riddle_email(user: dict, r: dict) -> tuple[str, str]:
    base = FRONTEND_URL.rstrip("/")  # /api est servi sur le même domaine
    uid = str(user["_id"])
    answer = f"{base}/api/enigme/{r['date']}/reponse"
    unsub = f"{base}/api/enigme/desinscription?u={uid}&s={_unsub_sig(uid)}"
    html = (f"<div style='font-family:Arial,sans-serif;color:#1A2530;max-width:560px;margin:auto;font-size:17px;line-height:1.55'>"
            f"<p style='color:#E07A5F;font-weight:bold;text-transform:uppercase;letter-spacing:1px;font-size:13px'>L'énigme du soir · à résoudre ensemble au dîner</p>"
            f"<h2 style='font-family:Georgia,serif;color:#1E3A5F;font-size:26px'>{escape(r['titre'])}</h2>"
            f"<p style='font-size:19px'>{escape(r['enigme'])}</p>"
            f"<p style='background:#F4F1DE;border-radius:16px;padding:12px 16px'><strong>Un indice ?</strong> {escape(r['indice'])}</p>"
            f"<p style='margin:24px 0'><a href='{answer}' style='background:#1E3A5F;color:#FDFBF7;padding:12px 24px;border-radius:999px;"
            f"text-decoration:none;font-weight:bold'>Voir la réponse</a></p>"
            f"<p style='font-size:13px;color:#1A2530'>Vous recevez cet e-mail car vous avez activé l'énigme du soir. "
            f"<a href='{unsub}' style='color:#1A2530'>Ne plus la recevoir</a></p></div>")
    return f"L'énigme du soir : {r['titre']}", html


async def send_evening_riddle_emails() -> dict:
    try:
        r = await get_or_create()
    except Exception as e:
        logger.error(f"[enigme] pas d'énigme à envoyer : {e}")
        return {"sent": 0}
    if not RESEND_API_KEY:
        logger.warning("[enigme] RESEND_API_KEY absent — envoi sauté")
        return {"sent": 0}
    sent = 0
    async for u in db.users.find({"riddle_email_optin": True, "riddle_email_sent_for": {"$ne": r["date"]}}):
        subject, html = riddle_email(u, r)
        try:
            await asyncio.to_thread(resend.Emails.send, {"from": SENDER_EMAIL, "to": [u["email"]], "subject": subject, "html": html})
            await db.users.update_one({"_id": u["_id"]}, {"$set": {"riddle_email_sent_for": r["date"]}})
            sent += 1
        except Exception as e:
            logger.warning(f"[enigme] envoi impossible à {u['email']} : {e}")
    logger.info(f"[enigme] e-mails de 18 h envoyés : {sent}")
    return {"sent": sent}
