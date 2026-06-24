"""Router FastAPI pour les invitations familiales de Quiz d'Antan."""

from __future__ import annotations

import asyncio
import logging
import secrets
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator
from postgrest.exceptions import APIError

try:  # Imports compatibles package et exécution locale.
    from quiz_antan.backend.supabase_client import get_supabase_client
except ImportError:  # pragma: no cover
    from supabase_client import get_supabase_client


logger = logging.getLogger(__name__)
router = APIRouter(tags=["family"])

# Alphabet volontairement lisible : pas de O/0 ni I/1 pour éviter les confusions.
INVITE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
INVITE_CODE_LENGTH = 6
MAX_INVITE_CODE_ATTEMPTS = 12


class CreateFamilyRequest(BaseModel):
    """Payload de création d'une famille."""

    name: str = Field(..., min_length=2, max_length=50)

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        """Nettoie le nom et refuse les valeurs composées uniquement d'espaces."""

        cleaned = value.strip()
        if len(cleaned) < 2:
            raise ValueError("Le nom de famille doit contenir au moins 2 caractères.")
        return cleaned


class JoinFamilyRequest(BaseModel):
    """Payload pour rejoindre une famille via son code d'invitation."""

    invite_code: str = Field(..., min_length=6, max_length=6)
    pseudo: str = Field(..., min_length=2, max_length=40)
    avatar: str = "default"

    @field_validator("invite_code")
    @classmethod
    def normalize_invite_code(cls, value: str) -> str:
        """Normalise le code en majuscules avant la recherche Supabase."""

        cleaned = value.strip().upper()
        if len(cleaned) != INVITE_CODE_LENGTH:
            raise ValueError("Le code d'invitation doit contenir 6 caractères.")
        return cleaned

    @field_validator("pseudo")
    @classmethod
    def pseudo_must_not_be_blank(cls, value: str) -> str:
        """Nettoie le pseudo et refuse les valeurs vides."""

        cleaned = value.strip()
        if len(cleaned) < 2:
            raise ValueError("Le pseudo doit contenir au moins 2 caractères.")
        return cleaned

    @field_validator("avatar")
    @classmethod
    def avatar_must_not_be_blank(cls, value: str) -> str:
        """Garantit une valeur d'avatar exploitable côté front."""

        cleaned = value.strip()
        return cleaned or "default"


class CreatePlayerRequest(BaseModel):
    """Payload de création directe d'un joueur dans une famille existante."""

    family_id: str = Field(..., min_length=1)
    pseudo: str = Field(..., min_length=2, max_length=40)
    avatar: str = "default"

    @field_validator("family_id", "pseudo")
    @classmethod
    def string_fields_must_not_be_blank(cls, value: str) -> str:
        """Nettoie les champs texte obligatoires."""

        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Ce champ ne peut pas être vide.")
        return cleaned

    @field_validator("avatar")
    @classmethod
    def normalize_avatar(cls, value: str) -> str:
        """Applique l'avatar par défaut si le champ est vide."""

        cleaned = value.strip()
        return cleaned or "default"


async def _run_supabase(operation: Any) -> Any:
    """Exécute un appel Supabase synchrone dans un thread non bloquant."""

    try:
        return await asyncio.to_thread(operation)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except APIError as exc:
        logger.exception("Erreur Supabase/PostgREST famille : %s", exc)
        raise HTTPException(status_code=503, detail="Service Supabase indisponible.") from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Erreur famille inattendue : %s", exc)
        raise HTTPException(status_code=503, detail="Service famille indisponible.") from exc


def _generate_invite_code() -> str:
    """Génère un code court lisible avec une source aléatoire cryptographique."""

    return "".join(secrets.choice(INVITE_ALPHABET) for _ in range(INVITE_CODE_LENGTH))


async def _find_family_by_code(invite_code: str) -> dict[str, Any] | None:
    """Recherche une famille par code d'invitation, sans tenir compte de la casse."""

    code = invite_code.strip().upper()
    supabase = get_supabase_client()
    response = await _run_supabase(
        lambda: supabase.table("families")
        .select("id,name,invite_code")
        .ilike("invite_code", code)
        .limit(1)
        .execute()
    )
    rows = response.data or []
    return rows[0] if rows else None


async def _ensure_pseudo_available(family_id: str, pseudo: str) -> None:
    """Empêche deux membres d'une même famille d'utiliser le même pseudo."""

    supabase = get_supabase_client()
    response = await _run_supabase(
        lambda: supabase.table("players")
        .select("id")
        .eq("family_id", family_id)
        .ilike("pseudo", pseudo.strip())
        .limit(1)
        .execute()
    )
    if response.data:
        raise HTTPException(status_code=409, detail="Ce pseudo est déjà pris dans cette famille.")


async def _create_player(family_id: str, pseudo: str, avatar: str = "default") -> dict[str, Any]:
    """Insère un joueur après contrôle d'unicité du pseudo familial."""

    await _ensure_pseudo_available(family_id=family_id, pseudo=pseudo)
    supabase = get_supabase_client()
    response = await _run_supabase(
        lambda: supabase.table("players")
        .insert({"family_id": family_id, "pseudo": pseudo.strip(), "avatar": avatar or "default"})
        .execute()
    )
    rows = response.data or []
    if not rows:
        raise HTTPException(status_code=503, detail="Impossible de créer le joueur.")
    return rows[0]


@router.post("/create")
async def create_family(payload: CreateFamilyRequest) -> dict[str, str]:
    """Crée une famille et retourne son code d'invitation partageable."""

    supabase = get_supabase_client()

    for _ in range(MAX_INVITE_CODE_ATTEMPTS):
        invite_code = _generate_invite_code()
        existing_family = await _find_family_by_code(invite_code)
        if existing_family is not None:
            continue

        response = await _run_supabase(
            lambda: supabase.table("families")
            .insert({"name": payload.name, "invite_code": invite_code})
            .execute()
        )
        rows = response.data or []
        if not rows:
            raise HTTPException(status_code=503, detail="Impossible de créer la famille.")

        family = rows[0]
        return {"family_id": family["id"], "name": family["name"], "invite_code": family["invite_code"]}

    raise HTTPException(status_code=503, detail="Impossible de générer un code d'invitation unique.")


@router.post("/join")
async def join_family(payload: JoinFamilyRequest) -> dict[str, str]:
    """Ajoute un joueur à une famille à partir d'un code d'invitation."""

    family = await _find_family_by_code(payload.invite_code)
    if family is None:
        raise HTTPException(status_code=404, detail="Code d'invitation inexistant.")

    player = await _create_player(family_id=family["id"], pseudo=payload.pseudo, avatar=payload.avatar)
    return {
        "player_id": player["id"],
        "pseudo": player["pseudo"],
        "family_id": family["id"],
        "family_name": family["name"],
    }


@router.get("/{family_id}")
async def read_family(family_id: str) -> dict[str, Any]:
    """Retourne les informations d'une famille et la liste de ses joueurs."""

    supabase = get_supabase_client()
    family_response = await _run_supabase(
        lambda: supabase.table("families")
        .select("id,name,invite_code")
        .eq("id", family_id)
        .limit(1)
        .execute()
    )
    family_rows = family_response.data or []
    if not family_rows:
        raise HTTPException(status_code=404, detail="Famille introuvable.")

    players_response = await _run_supabase(
        lambda: supabase.table("players")
        .select("id,pseudo,avatar,created_at")
        .eq("family_id", family_id)
        .order("created_at", desc=False)
        .execute()
    )
    family = family_rows[0]
    return {
        "family_id": family["id"],
        "name": family["name"],
        "invite_code": family["invite_code"],
        "players": players_response.data or [],
    }


@router.get("/by-code/{invite_code}")
async def read_family_by_code(invite_code: str) -> dict[str, Any]:
    """Valide un code d'invitation et retourne un résumé de la famille."""

    family = await _find_family_by_code(invite_code)
    if family is None:
        raise HTTPException(status_code=404, detail="Code d'invitation inexistant.")

    supabase = get_supabase_client()
    players_response = await _run_supabase(
        lambda: supabase.table("players")
        .select("id", count="exact")
        .eq("family_id", family["id"])
        .execute()
    )
    nb_players = players_response.count if players_response.count is not None else len(players_response.data or [])

    return {"family_id": family["id"], "name": family["name"], "nb_players": nb_players}
