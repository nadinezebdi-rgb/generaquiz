"""Rappel email dimanche soir pour les utilisateurs qui n'ont pas encore
relevé le défi hebdo palier.

Cron : chaque dimanche 19:00 Paris (voir scheduler.py).
"""
from __future__ import annotations

import asyncio
import resend

from core import db, logger, RESEND_API_KEY, SENDER_EMAIL, FRONTEND_URL
from routers.palier_weekly import get_current_challenge


def _build_html(name: str, category_title: str, palier: int) -> str:
    play_url = f"{FRONTEND_URL}/app/parcours"
    return f"""<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8">
<title>Défi de la semaine — dernier appel</title></head>
<body style="margin:0;padding:0;background-color:#F4F1DE;font-family:Arial,Helvetica,sans-serif;color:#1A2530;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#F4F1DE;padding:40px 20px;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0" style="background-color:#FFFFFF;border-radius:24px;border:2px solid #E8E2C9;overflow:hidden;">
        <tr><td style="background-color:#E07A5F;padding:36px;text-align:center;">
          <div style="font-size:56px;line-height:1;">🎯</div>
          <h1 style="color:#FFFFFF;font-family:Georgia,serif;font-size:28px;margin:12px 0 0;">Dernier jour pour relever le défi&nbsp;!</h1>
        </td></tr>
        <tr><td style="padding:36px 32px;">
          <p style="font-size:18px;line-height:1.6;margin:0 0 20px;color:#1A2530;">Bonjour <strong>{name}</strong>,</p>
          <p style="font-size:16px;line-height:1.6;margin:0 0 20px;color:#334155;">
            Vous n'avez pas encore joué le <strong>Défi de la semaine</strong>.
            La semaine se termine ce soir à minuit — c'est le moment idéal pour tenter
            votre chance et marquer des points au classement.
          </p>
          <div style="background:#F4F1DE;border:2px solid #E8E2C9;border-radius:16px;padding:20px;margin:0 0 24px;text-align:center;">
            <div style="font-size:12px;text-transform:uppercase;letter-spacing:2px;color:#64748B;font-weight:bold;">Cette semaine</div>
            <div style="font-family:Georgia,serif;font-size:22px;font-weight:bold;color:#1E3A5F;margin-top:6px;">{category_title}</div>
            <div style="font-size:14px;color:#334155;margin-top:4px;">Palier {palier} · 20 questions · seuil 14/20</div>
          </div>
          <table cellpadding="0" cellspacing="0" style="margin:12px auto;"><tr>
            <td style="background-color:#E07A5F;border-radius:30px;">
              <a href="{play_url}" style="display:inline-block;padding:16px 36px;color:#FFFFFF;text-decoration:none;font-weight:bold;font-size:16px;font-family:Arial,sans-serif;">
                Relever le défi
              </a>
            </td>
          </tr></table>
          <p style="font-size:13px;line-height:1.6;color:#94A3B8;margin:24px 0 0;text-align:center;">
            Pas envie ce soir&nbsp;? Ignorez simplement ce message — il n'y a aucune obligation.
          </p>
        </td></tr>
        <tr><td style="background-color:#F4F1DE;padding:20px 32px;text-align:center;border-top:2px solid #E8E2C9;">
          <p style="font-size:12px;color:#64748B;margin:0;">© GénéraQuiz — La plateforme de jeux de mémoire pour seniors</p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body></html>"""


async def send_weekly_challenge_reminders() -> dict:
    """Rappel dimanche soir aux opted-in users qui n'ont pas participé.
    Retourne {sent, skipped, failed}."""
    if not RESEND_API_KEY:
        logger.info("[weekly-reminder] RESEND_API_KEY manquant — skip")
        return {"sent": 0, "skipped": 0, "reason": "no_resend_key"}

    challenge = await get_current_challenge()
    if not challenge:
        logger.info("[weekly-reminder] aucun défi actif — skip")
        return {"sent": 0, "reason": "no_challenge"}

    week = challenge["week"]
    # Users qui ont DÉJÀ joué cette semaine — on les exclut du rappel
    played_user_ids: set[str] = set()
    async for row in db.weekly_palier_scores.find({"week": week}, {"user_id": 1, "_id": 0}):
        played_user_ids.add(row["user_id"])

    sent = 0
    skipped = 0
    failed = 0
    cursor = db.users.find({
        "$or": [{"daily_email_optin": {"$ne": False}}, {"daily_email_optin": {"$exists": False}}],
    })
    async for user in cursor:
        if str(user["_id"]) in played_user_ids:
            skipped += 1
            continue
        if not user.get("email"):
            continue
        name = user.get("name") or user["email"].split("@")[0]
        html = _build_html(name, challenge["category_title"], challenge["palier"])
        try:
            await asyncio.to_thread(resend.Emails.send, {
                "from": SENDER_EMAIL,
                "to": [user["email"]],
                "subject": f"🎯 Dernier jour — Défi de la semaine ({challenge['category_title']})",
                "html": html,
            })
            sent += 1
        except Exception as e:
            failed += 1
            logger.warning(f"[weekly-reminder] échec {user.get('email')}: {e}")
        await asyncio.sleep(0.25)

    logger.info(f"[weekly-reminder] sent={sent} skipped={skipped} failed={failed} week={week}")
    return {"sent": sent, "skipped": skipped, "failed": failed, "week": week}
