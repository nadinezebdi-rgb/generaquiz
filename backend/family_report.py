"""Rapport du dimanche aux proches + alerte d'inactivité (3 jours), si le bénéficiaire a activé le partage."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from html import escape

import resend
from bson import ObjectId

from core import db, logger, FRONTEND_URL, RESEND_API_KEY, SENDER_EMAIL
from routers.family import is_family_owner

INACTIVITY_DAYS = 3
ACTIVITY_COLLECTIONS = ("attempts", "daily_attempts", "palier_attempts")


async def _recipients(owner_id: str) -> list[dict]:
    ids = [p["user_id"] async for p in db.family_proches.find(
        {"owner_id": owner_id, "status": "accepted", "user_id": {"$ne": None}}, {"user_id": 1})]
    if not ids:
        return []
    return await db.users.find({"_id": {"$in": [ObjectId(i) for i in ids]}, "family_owner_id": owner_id},
                               {"email": 1, "name": 1}).to_list(10)


async def _activity(user_id: str, since: str | None = None) -> list[dict]:
    q = {"user_id": user_id, **({"created_at": {"$gte": since}} if since else {})}
    rows = []
    for coll in ACTIVITY_COLLECTIONS:
        rows += await db[coll].find(q, {"_id": 0, "created_at": 1, "category_id": 1}) \
            .sort("created_at", -1).to_list(None if since else 1)
    return rows


async def last_activity(user_id: str) -> str | None:
    rows = await _activity(user_id)
    return max((r["created_at"] for r in rows), default=None)


async def _topic_idea(category_ids: list[str]) -> str:
    base = {"discussion_prompt": {"$nin": [None, ""]}, "quality": {"$ne": "flagged"}}
    for match in ([{**base, "category_id": {"$in": category_ids}}] if category_ids else []) + [base]:
        docs = await db.questions.aggregate([{"$match": match}, {"$sample": {"size": 1}},
                                             {"$project": {"_id": 0, "discussion_prompt": 1}}]).to_list(1)
        if docs:
            return docs[0]["discussion_prompt"]
    return "Quel est votre plus beau souvenir de vacances ?"


def _html(title: str, body: str, topic: str) -> str:
    return (f"<div style='font-family:Arial,sans-serif;color:#1A2530;max-width:560px;margin:auto'>"
            f"<h2 style='font-family:Georgia,serif;color:#1E3A5F'>{title}</h2>{body}"
            f"<div style='background:#F4F1DE;border-radius:16px;padding:16px 20px;margin:20px 0'>"
            f"<p style='margin:0 0 6px;font-weight:bold;color:#E07A5F'>Une idée pour votre prochain appel</p>"
            f"<p style='margin:0;font-size:17px'>« {escape(topic)} »</p></div>"
            f"<p><a href='{FRONTEND_URL}/app/famille' style='background:#E07A5F;color:#fff;padding:12px 24px;"
            f"border-radius:999px;text-decoration:none;font-weight:bold'>Voir l'espace famille</a></p>"
            f"<p style='font-size:12px;color:#64748B'>Vous recevez cet e-mail car le partage est activé dans l'espace famille.</p></div>")


async def _send(to: str, subject: str, html: str) -> bool:
    if not RESEND_API_KEY:
        logger.warning("RESEND_API_KEY absent — rapport famille non envoyé")
        return False
    try:
        await asyncio.to_thread(resend.Emails.send, {"from": SENDER_EMAIL, "to": [to], "subject": subject, "html": html})
        return True
    except Exception as e:
        logger.warning(f"[family-report] échec pour {to}: {e}")
        return False


async def _sharing_owners():
    async for owner in db.users.find({"family_share_progress": True}):
        if not is_family_owner(owner):
            continue
        recipients = await _recipients(str(owner["_id"]))
        if recipients:
            yield owner, recipients


async def _achievements(owner_id: str, since: str) -> str:
    from badges import BADGES
    titles = {b["id"]: b["title"] for b in BADGES}
    passed = await db.palier_attempts.find(
        {"user_id": owner_id, "created_at": {"$gte": since}, "score": {"$gte": 14}, "legacy": {"$ne": True}},
        {"_id": 0, "category_id": 1, "palier": 1}).to_list(200)
    best: dict[str, int] = {}
    for p in passed:
        best[p["category_id"]] = max(best.get(p["category_id"], 0), int(p["palier"]))
    cats = {c["id"]: c["title"] async for c in db.categories.find({"id": {"$in": list(best)}}, {"_id": 0, "id": 1, "title": 1})}
    badges = [titles.get(b["badge_id"], b["badge_id"]) async for b in db.user_badges.find(
        {"user_id": owner_id, "earned_at": {"$gte": since}}, {"_id": 0, "badge_id": 1})]
    items = [f"🏔️ Palier {n} réussi en <strong>{escape(cats.get(c, c))}</strong>" for c, n in best.items()]
    items += [f"🏅 Badge « <strong>{escape(t)}</strong> » gagné" for t in badges]
    if not items:
        return ""
    lis = "".join(f"<li style='margin:4px 0'>{i}</li>" for i in items)
    return (f"<p style='margin:16px 0 4px;font-weight:bold;color:#1E3A5F'>De quoi le féliciter :</p>"
            f"<ul style='padding-left:20px;margin:0'>{lis}</ul>")


async def build_weekly_report(owner: dict) -> dict:
    owner_id = str(owner["_id"])
    since = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    rows = await _activity(owner_id, since)
    days = len({r["created_at"][:10] for r in rows})
    cats = list({r["category_id"] for r in rows if r.get("category_id")})
    name = escape(owner.get("name") or "Votre proche")
    if days:
        body = (f"<p>Cette semaine, {name} a joué <strong>{days} jour{'s' if days > 1 else ''} sur 7</strong> "
                f"({len(rows)} partie{'s' if len(rows) > 1 else ''}).</p>")
    else:
        body = f"<p>{name} n'a pas joué cette semaine. Un petit appel lui fera sûrement plaisir.</p>"
    body += await _achievements(owner_id, since)
    topic = await _topic_idea(cats)
    return {"days": days, "games": len(rows), "topic": topic,
            "subject": f"La semaine de {owner.get('name') or 'votre proche'} sur GénéraQuiz",
            "html": _html(f"La semaine de {name}", body, topic)}


async def send_weekly_family_reports() -> dict:
    sent = owners = 0
    async for owner, recipients in _sharing_owners():
        owners += 1
        report = await build_weekly_report(owner)
        for r in recipients:
            sent += await _send(r["email"], report["subject"], report["html"])
    logger.info(f"[family-report] rapports du dimanche : {sent} e-mail(s) pour {owners} bénéficiaire(s)")
    return {"owners": owners, "sent": sent}


async def send_inactivity_alerts() -> dict:
    sent = alerted = 0
    now = datetime.now(timezone.utc)
    async for owner, recipients in _sharing_owners():
        last = await last_activity(str(owner["_id"])) or owner.get("family_share_since")
        if not last or now - datetime.fromisoformat(last) < timedelta(days=INACTIVITY_DAYS):
            continue
        if owner.get("family_inactivity_alert_for") == last:
            continue  # une seule alerte par période d'absence
        name = escape(owner.get("name") or "Votre proche")
        days = (now - datetime.fromisoformat(last)).days
        topic = await _topic_idea([])
        html = _html(f"{name} n'a pas joué depuis {days} jours",
                     f"<p>Rien d'inquiétant sans doute, mais c'est l'occasion de prendre des nouvelles.</p>", topic)
        ok = 0
        for r in recipients:
            ok += await _send(r["email"], f"Des nouvelles de {owner.get('name') or 'votre proche'} ?", html)
        sent += ok
        if not ok:
            continue  # réessai au prochain passage
        await db.users.update_one({"_id": owner["_id"]}, {"$set": {"family_inactivity_alert_for": last}})
        alerted += 1
    logger.info(f"[family-report] alertes d'inactivité : {sent} e-mail(s) pour {alerted} bénéficiaire(s)")
    return {"alerted": alerted, "sent": sent}
