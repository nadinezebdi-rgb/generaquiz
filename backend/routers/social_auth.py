"""Apple Sign-In and Google Sign-In token verification — server-side.

The mobile client (iOS/Android) obtains a signed id_token from Apple or Google and
posts it here. The backend:
  1. Fetches the provider's public JWKS (cached in memory, 24h TTL).
  2. Verifies the JWT signature + critical claims (iss / aud / exp / azp where applicable).
  3. Upserts the user (matched by `apple_sub` / `google_sub`), grants WELCOME_CREDITS on first login.
  4. Returns our own JWT access token + refresh, same as /api/auth/login.

Environment variables required (backend/.env):
  APPLE_SERVICES_ID         e.g. com.generaquiz.app.services
  APPLE_BUNDLE_ID           e.g. com.generaquiz.app           (alternative aud accepted)
  GOOGLE_WEB_CLIENT_ID      OAuth client ID of type "Web application"
  GOOGLE_IOS_CLIENT_ID      (optional) OAuth client ID of type iOS, accepted as aud too
  GOOGLE_ANDROID_CLIENT_ID  (optional) OAuth client ID of type Android, accepted as aud too

If env vars are missing, the corresponding endpoint returns 503 "non configuré" instead
of failing silently or accepting unverified tokens.
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Optional

import httpx
import jwt
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

from core import (
    db, logger, WELCOME_CREDITS,
    user_to_public, create_access_token, create_refresh_token, set_auth_cookies,
)

router = APIRouter(prefix="/auth", tags=["auth-social"])

APPLE_JWKS_URL = "https://appleid.apple.com/auth/keys"
APPLE_ISSUER = "https://appleid.apple.com"
GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_ISSUERS = {"https://accounts.google.com", "accounts.google.com"}

JWKS_CACHE_TTL_SECONDS = 24 * 3600
EXPIRATION_LEEWAY = 300  # 5 minutes — symmetric tolerance

# In-memory JWKS cache: {url: (fetched_at_epoch, {kid: jwk_dict})}
_jwks_cache: dict[str, tuple[float, dict[str, dict]]] = {}


# ---------------------------------------------------------------------------
# JWKS helpers
# ---------------------------------------------------------------------------
async def _fetch_jwks(url: str) -> dict[str, dict]:
    """Returns {kid: jwk_dict}. Cached in memory."""
    now = time.time()
    cached = _jwks_cache.get(url)
    if cached and (now - cached[0] < JWKS_CACHE_TTL_SECONDS):
        return cached[1]
    async with httpx.AsyncClient(timeout=8.0) as client:
        r = await client.get(url)
        r.raise_for_status()
        data = r.json()
    keys = {k["kid"]: k for k in data.get("keys", [])}
    _jwks_cache[url] = (now, keys)
    return keys


def _get_signing_key(jwks: dict[str, dict], kid: str):
    jwk = jwks.get(kid)
    if not jwk:
        raise HTTPException(status_code=401, detail="Clé de signature inconnue")
    return jwt.algorithms.RSAAlgorithm.from_jwk(jwk)


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------
class SocialAuthRequest(BaseModel):
    id_token: str = Field(..., min_length=20, max_length=4096)
    name: Optional[str] = Field(None, max_length=80)


# ---------------------------------------------------------------------------
# User upsert helper (shared by Apple and Google)
# ---------------------------------------------------------------------------
async def _upsert_social_user(
    *,
    provider: str,
    sub: str,
    email: Optional[str],
    name_from_token: Optional[str],
    name_from_request: Optional[str],
) -> dict:
    provider_field = "apple_sub" if provider == "apple" else "google_sub"
    existing = await db.users.find_one({provider_field: sub})
    if existing:
        return existing

    # Existing email match? Link the social identity to that account.
    if email:
        by_email = await db.users.find_one({"email": email.lower()})
        if by_email:
            await db.users.update_one(
                {"_id": by_email["_id"]},
                {"$set": {provider_field: sub}},
            )
            by_email[provider_field] = sub
            return by_email

    # Brand-new account — create + grant welcome credits
    display_name = (name_from_request or name_from_token or (email.split("@")[0] if email else "Joueur")).strip()[:80]
    doc = {
        "email": (email or f"{sub}@apple.local" if provider == "apple" else f"{sub}@google.local").lower(),
        "password_hash": None,         # social-only, no password
        "name": display_name,
        "role": "user",
        "plan": "free",
        "plan_expires_at": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "credits": WELCOME_CREDITS,
        "xp_total": 0,
        "auth_provider": provider,
        provider_field: sub,
    }
    result = await db.users.insert_one(doc)
    doc["_id"] = result.inserted_id
    await db.credit_ledger.insert_one({
        "user_id": str(result.inserted_id),
        "delta": WELCOME_CREDITS,
        "balance_after": WELCOME_CREDITS,
        "reason": f"welcome_bonus_{provider}",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    logger.info(f"[social-auth] nouveau compte {provider} créé : {doc['email']}")
    return doc


def _issue_session(response: Response, user: dict) -> dict:
    access = create_access_token(str(user["_id"]), user["email"])
    refresh = create_refresh_token(str(user["_id"]))
    set_auth_cookies(response, access, refresh)
    return {"user": user_to_public(user), "access_token": access}


# ---------------------------------------------------------------------------
# Apple Sign-In
# ---------------------------------------------------------------------------
@router.post("/apple")
async def auth_apple(body: SocialAuthRequest, response: Response):
    services_id = os.environ.get("APPLE_SERVICES_ID")
    bundle_id = os.environ.get("APPLE_BUNDLE_ID")
    audience = [a for a in (services_id, bundle_id) if a]
    if not audience:
        raise HTTPException(status_code=503, detail="Apple Sign-In non configuré côté serveur.")

    try:
        unverified_header = jwt.get_unverified_header(body.id_token)
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=400, detail="Format de jeton invalide")
    kid = unverified_header.get("kid")
    if not kid:
        raise HTTPException(status_code=400, detail="Jeton sans identifiant de clé")

    try:
        jwks = await _fetch_jwks(APPLE_JWKS_URL)
    except Exception as e:
        logger.warning(f"[apple] JWKS fetch failed: {e}")
        raise HTTPException(status_code=503, detail="Impossible de joindre Apple pour vérifier")
    signing_key = _get_signing_key(jwks, kid)

    try:
        payload = jwt.decode(
            body.id_token,
            signing_key,
            algorithms=["RS256"],
            issuer=APPLE_ISSUER,
            audience=audience,
            leeway=EXPIRATION_LEEWAY,
            options={"require": ["iss", "aud", "exp", "sub"]},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Jeton expiré")
    except jwt.InvalidIssuerError:
        raise HTTPException(status_code=401, detail="Émetteur invalide")
    except jwt.InvalidAudienceError:
        raise HTTPException(status_code=401, detail="Audience invalide")
    except jwt.InvalidTokenError as e:
        logger.warning(f"[apple] verification failed: {e}")
        raise HTTPException(status_code=401, detail="Jeton invalide")

    sub = payload.get("sub")
    email = payload.get("email")
    user = await _upsert_social_user(
        provider="apple",
        sub=sub,
        email=email,
        name_from_token=None,  # Apple only provides name in the initial JSON-encoded `user` field
        name_from_request=body.name,
    )
    return _issue_session(response, user)


# ---------------------------------------------------------------------------
# Google Sign-In
# ---------------------------------------------------------------------------
@router.post("/google")
async def auth_google(body: SocialAuthRequest, response: Response):
    web_id = os.environ.get("GOOGLE_WEB_CLIENT_ID")
    ios_id = os.environ.get("GOOGLE_IOS_CLIENT_ID")
    android_id = os.environ.get("GOOGLE_ANDROID_CLIENT_ID")
    audience = [a for a in (web_id, ios_id, android_id) if a]
    if not audience:
        raise HTTPException(status_code=503, detail="Google Sign-In non configuré côté serveur.")

    try:
        unverified_header = jwt.get_unverified_header(body.id_token)
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=400, detail="Format de jeton invalide")
    kid = unverified_header.get("kid")
    if not kid:
        raise HTTPException(status_code=400, detail="Jeton sans identifiant de clé")

    try:
        jwks = await _fetch_jwks(GOOGLE_JWKS_URL)
    except Exception as e:
        logger.warning(f"[google] JWKS fetch failed: {e}")
        raise HTTPException(status_code=503, detail="Impossible de joindre Google pour vérifier")
    signing_key = _get_signing_key(jwks, kid)

    try:
        payload = jwt.decode(
            body.id_token,
            signing_key,
            algorithms=["RS256"],
            audience=audience,
            leeway=EXPIRATION_LEEWAY,
            options={"require": ["iss", "aud", "exp", "sub"]},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Jeton expiré")
    except jwt.InvalidAudienceError:
        raise HTTPException(status_code=401, detail="Audience invalide")
    except jwt.InvalidTokenError as e:
        logger.warning(f"[google] verification failed: {e}")
        raise HTTPException(status_code=401, detail="Jeton invalide")

    if payload.get("iss") not in GOOGLE_ISSUERS:
        raise HTTPException(status_code=401, detail="Émetteur invalide")

    # `azp` strict check: if the token has an `azp`, it must be one of our configured client IDs
    azp = payload.get("azp")
    if azp and azp not in audience:
        raise HTTPException(status_code=401, detail="Partie autorisée invalide")

    if payload.get("email") and not payload.get("email_verified", False):
        raise HTTPException(status_code=401, detail="Email Google non vérifié")

    sub = payload.get("sub")
    email = payload.get("email")
    user = await _upsert_social_user(
        provider="google",
        sub=sub,
        email=email,
        name_from_token=payload.get("name"),
        name_from_request=body.name,
    )
    return _issue_session(response, user)
