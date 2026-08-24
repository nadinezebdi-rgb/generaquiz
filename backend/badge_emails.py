"""Email de félicitations pour le badge Grand Maître (palier 7 dans ≥ 3 catégories).

Isolé dans son propre module car ce n'est pas un email transactionnel programmé
(comme les emails de daily/expiration/ligue) mais un envoi événementiel déclenché
depuis `badges.check_after_palier` au moment où le badge tombe.
"""
from __future__ import annotations

import asyncio
import resend

from core import logger, RESEND_API_KEY, SENDER_EMAIL, FRONTEND_URL


def _build_html(name: str, categories_count: int) -> str:
    return f"""<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8">
<title>Grand Maître — félicitations</title></head>
<body style="margin:0;padding:0;background-color:#F4F1DE;font-family:Arial,Helvetica,sans-serif;color:#1A2530;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#F4F1DE;padding:40px 20px;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0" style="background-color:#FFFFFF;border-radius:24px;border:2px solid #E8E2C9;overflow:hidden;">
        <tr><td style="background-color:#1E3A5F;padding:36px;text-align:center;">
          <div style="font-size:64px;line-height:1;margin-bottom:8px;">👑</div>
          <h1 style="color:#F2CC8F;font-family:Georgia,serif;font-size:32px;margin:8px 0 0;">Grand Maître !</h1>
        </td></tr>
        <tr><td style="padding:40px 32px;">
          <p style="font-size:18px;line-height:1.6;margin:0 0 20px;color:#1A2530;">
            Bonjour <strong>{name}</strong>,
          </p>
          <p style="font-size:16px;line-height:1.6;margin:0 0 20px;color:#334155;">
            Vous venez de décrocher le badge le plus prestigieux de GénéraQuiz :
            <strong>Grand Maître</strong>. Vous avez validé le palier <strong>Expert</strong>
            (7/7) dans <strong>{categories_count} catégorie{'s' if categories_count > 1 else ''}</strong> — un exploit rare qui témoigne d'une véritable
            culture générale.
          </p>
          <p style="font-size:16px;line-height:1.6;margin:0 0 24px;color:#334155;">
            Vos trophées sont visibles sur votre profil, aux côtés des autres badges
            que vous avez collectionnés le long du parcours.
          </p>
          <table cellpadding="0" cellspacing="0" style="margin:12px auto;"><tr>
            <td style="background-color:#E07A5F;border-radius:30px;">
              <a href="{FRONTEND_URL}/app/account" style="display:inline-block;padding:16px 36px;color:#FFFFFF;text-decoration:none;font-weight:bold;font-size:16px;font-family:Arial,sans-serif;">
                Voir mes trophées
              </a>
            </td>
          </tr></table>
          <p style="font-size:14px;line-height:1.6;color:#64748B;margin:32px 0 0;text-align:center;font-style:italic;">
            Merci d'être un pilier de la communauté. À vous les paliers Expert des
            catégories qu'il vous reste !
          </p>
        </td></tr>
        <tr><td style="background-color:#F4F1DE;padding:20px 32px;text-align:center;border-top:2px solid #E8E2C9;">
          <p style="font-size:12px;color:#64748B;margin:0;">© GénéraQuiz — La plateforme de jeux de mémoire pour seniors</p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body></html>"""


async def send_grand_maitre_email(user: dict, categories_count: int) -> bool:
    """Envoi asynchrone (thread pool car resend SDK est synchrone).

    Never raises — un échec d'email ne doit pas empêcher l'attribution du badge.
    """
    if not RESEND_API_KEY:
        logger.info(f"[badge-email] Resend non configuré → skip envoi Grand Maître à {user.get('email')}")
        return False
    name = user.get("name") or (user.get("email") or "").split("@")[0]
    email = user.get("email")
    if not email:
        return False
    html = _build_html(name, categories_count)
    try:
        await asyncio.to_thread(resend.Emails.send, {
            "from": SENDER_EMAIL,
            "to": [email],
            "subject": "👑 Félicitations — Vous êtes Grand Maître GénéraQuiz !",
            "html": html,
        })
        logger.info(f"[badge-email] Grand Maître envoyé à {email}")
        return True
    except Exception as e:
        logger.warning(f"[badge-email] échec envoi Grand Maître à {email}: {e}")
        return False
