"""Router FastAPI pour les classements persistants de Quiz d'Antan."""

from __future__ import annotations

import logging
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from postgrest.exceptions import APIError

try:  # Imports compatibles package et exécution locale.
    from quiz_antan.backend.leaderboard_service import (
        get_family_leaderboard,
        get_global_leaderboard,
        get_player_badges,
        get_theme_champions,
        submit_score,
    )
except ImportError:  # pragma: no cover
    from leaderboard_service import (
        get_family_leaderboard,
        get_global_leaderboard,
        get_player_badges,
        get_theme_champions,
        submit_score,
    )


logger = logging.getLogger(__name__)
router = APIRouter(tags=["leaderboard"])

Difficulty = Literal["facile", "moyen", "difficile"]
Period = Literal["week", "month", "alltime"]


class AnswerSubmit(BaseModel):
    """Réponse envoyée par le front à la fin d'une partie."""

    question_id: str = Field(..., min_length=1, description="Identifiant de la question.")
    chosen: str = Field(..., min_length=1, description="Réponse choisie par le joueur.")
    correct: bool = Field(..., description="Indique si la réponse est correcte.")
    difficulty: Difficulty = Field(..., description="Difficulté de la question.")
    time_taken_seconds: float | None = Field(
        default=None,
        ge=0,
        description="Temps de réponse en secondes, utilisé pour le bonus temps.",
    )
    time_bonus: int | None = Field(
        default=None,
        ge=0,
        description="Bonus temps optionnel précalculé par question.",
    )

    @field_validator("chosen")
    @classmethod
    def chosen_must_not_be_blank(cls, value: str) -> str:
        """Empêche les réponses vides ou composées d'espaces."""

        cleaned = value.strip()
        if not cleaned:
            raise ValueError("La réponse choisie ne peut pas être vide.")
        return cleaned


class ScoreSubmitRequest(BaseModel):
    """Payload de soumission d'un score de fin de session."""

    session_token: str = Field(..., min_length=8, max_length=512)
    player_id: str = Field(..., min_length=1)
    family_id: str = Field(..., min_length=1)
    theme: str = Field(..., min_length=1, max_length=100)
    answers: list[AnswerSubmit] = Field(..., min_length=1, max_length=50)

    @field_validator("session_token", "player_id", "family_id", "theme")
    @classmethod
    def string_fields_must_not_be_blank(cls, value: str) -> str:
        """Nettoie les chaînes critiques et refuse les valeurs vides."""

        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Ce champ ne peut pas être vide.")
        return cleaned


class ScoreSubmitResponse(BaseModel):
    """Réponse renvoyée après soumission d'un score."""

    score: float
    rank: int | None = None
    badges_earned: list[str]


class BadgeResponse(BaseModel):
    """Badge attribué à un joueur."""

    id: str
    player_id: str
    family_id: str | None = None
    type: str
    context: dict[str, Any] = Field(default_factory=dict)
    awarded_at: str | None = None


async def _handle_supabase_call(coro: Any) -> Any:
    """Centralise la conversion des erreurs Supabase en HTTPException."""

    try:
        return await coro
    except ValueError as exc:
        message = str(exc)
        status_code = 409 if "déjà été soumise" in message else 400
        raise HTTPException(status_code=status_code, detail=message) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except APIError as exc:
        logger.exception("Erreur Supabase/PostgREST : %s", exc)
        raise HTTPException(status_code=503, detail="Service Supabase indisponible.") from exc
    except Exception as exc:
        logger.exception("Erreur leaderboard inattendue : %s", exc)
        raise HTTPException(status_code=503, detail="Service leaderboard indisponible.") from exc


@router.post("/submit", response_model=ScoreSubmitResponse)
async def submit_leaderboard_score(payload: ScoreSubmitRequest) -> ScoreSubmitResponse:
    """Soumet le score de fin de session et retourne score, rang et badges."""

    result = await _handle_supabase_call(
        submit_score(
            session_token=payload.session_token,
            player_id=payload.player_id,
            family_id=payload.family_id,
            theme=payload.theme,
            answers=[answer.model_dump() for answer in payload.answers],
            questions=[answer.model_dump() for answer in payload.answers],
        )
    )
    return ScoreSubmitResponse.model_validate(result)


@router.get("/family/{family_id}")
async def read_family_leaderboard(
    family_id: str,
    period: Period = Query("week", description="Période : week, month ou alltime."),
) -> list[dict[str, Any]]:
    """Retourne le classement des joueurs d'une famille."""

    leaderboard = await _handle_supabase_call(get_family_leaderboard(family_id=family_id, period=period))
    if not leaderboard:
        raise HTTPException(status_code=404, detail="Aucun classement trouvé pour cette famille.")
    return leaderboard


@router.get("/global")
async def read_global_leaderboard(
    period: Period = Query("week", description="Période : week, month ou alltime."),
    limit: int = Query(10, ge=1, le=100, description="Nombre maximal de familles retournées."),
) -> list[dict[str, Any]]:
    """Retourne le classement global des familles."""

    leaderboard = await _handle_supabase_call(get_global_leaderboard(period=period, limit=limit))
    if not leaderboard:
        raise HTTPException(status_code=404, detail="Aucun classement global trouvé.")
    return leaderboard


@router.get("/themes")
async def read_theme_champions() -> list[dict[str, Any]]:
    """Retourne les champions par thème."""

    champions = await _handle_supabase_call(get_theme_champions())
    if not champions:
        raise HTTPException(status_code=404, detail="Aucun champion par thème trouvé.")
    return champions


@router.get("/player/{player_id}/badges", response_model=list[BadgeResponse])
async def read_player_badges(player_id: str) -> list[BadgeResponse]:
    """Retourne les badges obtenus par un joueur."""

    badges = await _handle_supabase_call(get_player_badges(player_id=player_id))
    if not badges:
        raise HTTPException(status_code=404, detail="Aucun badge trouvé pour ce joueur.")
    return [BadgeResponse.model_validate(badge) for badge in badges]
