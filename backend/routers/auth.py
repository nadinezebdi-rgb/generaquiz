"""Auth router: register/login/logout/me/forgot/reset/change-password/profile/account.
Includes Resend email sending and IP-based rate limiting on /forgot-password."""
import asyncio
import secrets
from datetime import datetime, timezone, timedelta

import resend
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pymongo.errors import DuplicateKeyError

from core import (
    db, logger, FRONTEND_URL, RESEND_API_KEY, SENDER_EMAIL, WELCOME_CREDITS,
    hash_password, verify_password, create_access_token, create_refresh_token,
    set_auth_cookies, clear_auth_cookies, user_to_public, get_current_user, rate_limit,
    RegisterRequest, LoginRequest, ForgotPasswordRequest, ResetPasswordRequest,
    ChangePasswordRequest, UpdateProfileRequest, DailyEmailPrefRequest,
)
from routers.referral import generate_referral_code_for, find_user_by_code

router = APIRouter(prefix="/auth", tags=["auth"])


def _infer_country_code(request: Request) -> str:
    """Best-effort country code from Accept-Language. Defaults to FR.

    Accept-Language examples: 'fr-FR,fr;q=0.9' → FR, 'en-GB' → GB.
    Used only for the "Pays/régions actifs" public counter — never gates features.
    """
    lang = (request.headers.get("accept-language") or "fr").lower()
    first = lang.split(",")[0].strip()
    if "-" in first:
        return first.split("-")[1].upper()[:2]
    # bare 'fr' → assume FR; bare 'en' → GB as a neutral default
    return "FR" if first.startswith("fr") else first.upper()[:2] or "FR"


def _build_reset_email_html(reset_link: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="UTF-8"><title>Réinitialiser votre mot de passe</title></head>
<body style="margin:0;padding:0;background-color:#F4F1DE;font-family:Arial,Helvetica,sans-serif;color:#1A2530;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#F4F1DE;padding:40px 20px;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0" style="background-color:#FFFFFF;border-radius:24px;border:2px solid #E8E2C9;overflow:hidden;">
        <tr><td style="background-color:#1E3A5F;padding:30px;text-align:center;">
          <div style="display:inline-block;background-color:#E07A5F;width:48px;height:48px;border-radius:50%;line-height:48px;color:#FFFFFF;font-size:24px;font-weight:bold;">Q</div>
          <h1 style="color:#F2CC8F;font-family:Georgia,serif;font-size:28px;margin:14px 0 0;">GénéraQuiz</h1>
        </td></tr>
        <tr><td style="padding:40px 32px;">
          <h2 style="font-family:Georgia,serif;font-size:24px;color:#1A2530;margin:0 0 16px;">Réinitialisation de votre mot de passe</h2>
          <p style="font-size:16px;line-height:1.6;color:#334155;margin:0 0 20px;">Bonjour,</p>
          <p style="font-size:16px;line-height:1.6;color:#334155;margin:0 0 20px;">Vous avez demandé à réinitialiser le mot de passe de votre compte <strong>GénéraQuiz</strong>. Cliquez sur le bouton ci-dessous pour choisir un nouveau mot de passe :</p>
          <table cellpadding="0" cellspacing="0" style="margin:28px auto;"><tr><td style="background-color:#E07A5F;border-radius:30px;">
            <a href="{reset_link}" style="display:inline-block;padding:16px 36px;color:#FFFFFF;text-decoration:none;font-weight:bold;font-size:16px;font-family:Arial,sans-serif;">Réinitialiser mon mot de passe</a>
          </td></tr></table>
          <p style="font-size:14px;line-height:1.6;color:#64748B;margin:20px 0 8px;">Ou copiez-collez ce lien dans votre navigateur :</p>
          <p style="font-size:13px;line-height:1.4;color:#1E3A5F;word-break:break-all;background-color:#F4F1DE;padding:12px;border-radius:8px;margin:0 0 24px;font-family:monospace;">{reset_link}</p>
          <p style="font-size:14px;line-height:1.6;color:#64748B;margin:20px 0;">Ce lien est valable <strong>1 heure</strong>.</p>
          <p style="font-size:14px;line-height:1.6;color:#64748B;margin:20px 0 0;">Si vous n'avez pas demandé cette réinitialisation, ignorez simplement cet email — votre mot de passe reste inchangé.</p>
        </td></tr>
        <tr><td style="background-color:#F4F1DE;padding:20px 32px;text-align:center;border-top:2px solid #E8E2C9;">
          <p style="font-size:12px;color:#64748B;margin:0;">© GénéraQuiz — La plateforme de jeux de mémoire pour seniors</p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body></html>"""


async def _send_reset_email(to_email: str, reset_link: str) -> bool:
    if not RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not set — email not sent")
        return False
    # Détection du mode test/sandbox Resend : si l'expéditeur est encore
    # onboarding@resend.dev, seul l'email propriétaire du compte Resend pourra
    # recevoir le message. On log un avertissement explicite pour aider au debug.
    if "onboarding@resend.dev" in SENDER_EMAIL:
        logger.warning(
            "Resend en mode sandbox (SENDER_EMAIL=onboarding@resend.dev) — "
            "seul l'email propriétaire du compte Resend recevra le mail. "
            "Vérifier le domaine generaquiz.fr sur resend.com/domains."
        )
    params = {"from": SENDER_EMAIL, "to": [to_email],
              "subject": "Réinitialisation de votre mot de passe — GénéraQuiz",
              "html": _build_reset_email_html(reset_link)}
    try:
        result = await asyncio.to_thread(resend.Emails.send, params)
        eid = result.get("id") if isinstance(result, dict) else result
        logger.info(f"Reset email sent to {to_email} — id={eid}")
        return True
    except Exception as e:
        msg = str(e)
        if "testing" in msg.lower() or "verify a domain" in msg.lower():
            logger.error(f"Reset email non envoyé à {to_email} — Resend en mode test : domaine SENDER_EMAIL non vérifié (resend.com/domains)")
        else:
            logger.error(f"Failed to send reset email to {to_email}: {e}")
        return False


@router.post("/register")
async def register(body: RegisterRequest, request: Request, response: Response):
    email = body.email.lower().strip()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Cet email est déjà utilisé")

    # Validate optional referral code (silently ignore if invalid to avoid blocking signup)
    referred_by_user_id = None
    if body.referral_code:
        sponsor = await find_user_by_code(body.referral_code)
        if sponsor:
            referred_by_user_id = str(sponsor["_id"])

    # Generate this new user's own referral code (so they can invite immediately).
    # Retry on the extremely unlikely DuplicateKeyError race between two concurrent
    # signups generating the same suffix.
    own_code = await generate_referral_code_for(body.name, email)

    doc = {"email": email, "password_hash": hash_password(body.password),
           "name": body.name.strip(), "role": "user", "plan": "free",
           "plan_expires_at": None, "created_at": datetime.now(timezone.utc).isoformat(),
           "credits": WELCOME_CREDITS, "xp_total": 0, "auth_provider": "email",
           "referral_code": own_code,
           "referred_by_user_id": referred_by_user_id,
           "referral_count": 0,
           "country_code": _infer_country_code(request)}
    try:
        result = await db.users.insert_one(doc)
    except DuplicateKeyError:
        # Race on referral_code unique index — regenerate once and retry
        doc["referral_code"] = await generate_referral_code_for(body.name, email)
        result = await db.users.insert_one(doc)
    doc["_id"] = result.inserted_id
    # Welcome bonus ledger entry (audit trail)
    await db.credit_ledger.insert_one({
        "user_id": str(result.inserted_id),
        "delta": WELCOME_CREDITS,
        "balance_after": WELCOME_CREDITS,
        "reason": "welcome_bonus",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    access = create_access_token(str(result.inserted_id), email)
    refresh = create_refresh_token(str(result.inserted_id))
    set_auth_cookies(response, access, refresh)
    return {"user": user_to_public(doc), "access_token": access}


@router.post("/login")
async def login(body: LoginRequest, response: Response):
    email = body.email.lower().strip()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
    access = create_access_token(str(user["_id"]), email)
    refresh = create_refresh_token(str(user["_id"]))
    set_auth_cookies(response, access, refresh)
    return {"user": user_to_public(user), "access_token": access}


@router.post("/logout")
async def logout(response: Response):
    clear_auth_cookies(response)
    return {"ok": True}


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return user_to_public(user)


# Rate limit: max 3 calls / 15 min per IP to prevent flood/enumeration scans
@router.post("/forgot-password", dependencies=[Depends(rate_limit("forgot-pw", max_calls=3, window_seconds=900))])
async def forgot_password(body: ForgotPasswordRequest):
    email = body.email.lower().strip()
    user = await db.users.find_one({"email": email})
    generic = {"ok": True, "message": "Si ce compte existe, un email de réinitialisation a été envoyé.", "email_sent": False}
    if not user:
        return generic
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    await db.password_reset_tokens.insert_one({"token": token, "user_id": str(user["_id"]),
                                                "email": email, "expires_at": expires_at,
                                                "used": False, "created_at": datetime.now(timezone.utc)})
    reset_link = f"{FRONTEND_URL}/reset-password?token={token}"
    logger.info(f"[RESET] {email} -> {reset_link}")
    sent = await _send_reset_email(email, reset_link)
    generic["email_sent"] = sent
    return generic


@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest):
    record = await db.password_reset_tokens.find_one({"token": body.token})
    if not record:
        raise HTTPException(status_code=400, detail="Lien invalide ou expiré")
    if record.get("used"):
        raise HTTPException(status_code=400, detail="Lien déjà utilisé")
    expires = record.get("expires_at")
    if isinstance(expires, datetime):
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires < datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="Lien expiré")
    await db.users.update_one({"_id": ObjectId(record["user_id"])},
                              {"$set": {"password_hash": hash_password(body.new_password)}})
    await db.password_reset_tokens.update_one({"_id": record["_id"]},
                                              {"$set": {"used": True, "used_at": datetime.now(timezone.utc)}})
    return {"ok": True, "message": "Mot de passe réinitialisé. Vous pouvez vous connecter."}


@router.post("/change-password")
async def change_password(body: ChangePasswordRequest, user: dict = Depends(get_current_user)):
    if not verify_password(body.current_password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Mot de passe actuel incorrect")
    await db.users.update_one({"_id": ObjectId(str(user["_id"]))},
                              {"$set": {"password_hash": hash_password(body.new_password)}})
    return {"ok": True, "message": "Mot de passe mis à jour"}


@router.patch("/profile")
async def update_profile(body: UpdateProfileRequest, user: dict = Depends(get_current_user)):
    await db.users.update_one({"_id": ObjectId(str(user["_id"]))},
                              {"$set": {"name": body.name.strip()}})
    fresh = await db.users.find_one({"_id": ObjectId(str(user["_id"]))})
    return user_to_public(fresh)


@router.patch("/preferences/daily-email")
async def toggle_daily_email(body: DailyEmailPrefRequest, user: dict = Depends(get_current_user)):
    """Opt-in / opt-out of the morning Quiz du Jour email reminder."""
    await db.users.update_one(
        {"_id": ObjectId(str(user["_id"]))},
        {"$set": {"daily_email_optin": body.daily_email_optin}},
    )
    fresh = await db.users.find_one({"_id": ObjectId(str(user["_id"]))})
    return user_to_public(fresh)


@router.delete("/account")
async def delete_account(user: dict = Depends(get_current_user), response: Response = None):
    user_id = str(user["_id"])
    await db.users.delete_one({"_id": ObjectId(user_id)})
    await db.attempts.delete_many({"user_id": user_id})
    await db.challenges.delete_many({"creator_user_id": user_id})
    if response is not None:
        clear_auth_cookies(response)
    return {"ok": True}
