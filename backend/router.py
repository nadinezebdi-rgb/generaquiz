"""Router FastAPI pour les quiz générés par Mistral.

À inclure dans l'application principale avec :
    app.include_router(router)
"""

from __future__ import annotations

import logging
import random
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from cache import build_cache_key, get_cached, set_cache
from mistral_client import generate_questions
from prompts import THEME_CATALOG, ThemeMetadata


logger = logging.getLogger(__name__)
router = APIRouter(tags=["quiz"])

Difficulty = Literal["facile", "moyen", "difficile"]
Category = Literal["nostalgie", "moderne", "intemporel", "culture"]
Era = Literal["1950-1980", "1980-2000", "2000-2020", "intemporel"]
TargetDifficulty = Literal["facile", "moyen", "difficile", "mixte"]
ThemeEra = Literal["1950-1980", "1980-2000", "2000-2020", "intemporel", "mixte"]


class QuizQuestion(BaseModel):
    """Question validée retournée par l'API."""

    question: str = Field(..., min_length=3)
    choices: list[str] = Field(..., min_length=4, max_length=4)
    answer: str = Field(..., min_length=1)
    difficulty: Difficulty
    category: Category
    era: Era

    @field_validator("choices")
    @classmethod
    def choices_must_be_distinct(cls, choices: list[str]) -> list[str]:
        """Vérifie que les quatre choix sont distincts."""

        if len(set(choices)) != 4:
            raise ValueError("Les choix doivent être distincts.")
        return choices

    @field_validator("answer")
    @classmethod
    def answer_must_not_be_empty(cls, answer: str) -> str:
        """Vérifie que la réponse n'est pas vide."""

        if not answer.strip():
            raise ValueError("La réponse ne peut pas être vide.")
        return answer

    def model_post_init(self, __context: object) -> None:
        """Vérifie que la réponse correspond à un choix proposé."""

        if self.answer not in self.choices:
            raise ValueError("La réponse doit être l'un des choix proposés.")


class QuizResponse(BaseModel):
    """Réponse de génération de quiz."""

    theme: str
    nb: int
    source: Literal["cache", "mistral"]
    questions: list[QuizQuestion]


class ThemeResponse(BaseModel):
    """Thème disponible avec métadonnées."""

    key: str
    label: str
    description: str
    category: Category
    era: ThemeEra
    target_difficulty: TargetDifficulty


class ThemesResponse(BaseModel):
    """Liste des thèmes disponibles."""

    themes: list[ThemeResponse]


def _normalize_generated_questions(raw_questions: object) -> list[QuizQuestion]:
    """Convertit une liste brute en modèles Pydantic validés."""

    if not isinstance(raw_questions, list):
        raise ValueError("La source ne contient pas une liste de questions.")
    return [QuizQuestion.model_validate(question) for question in raw_questions]


async def _generate_or_get_from_cache(theme: str, nb: int) -> QuizResponse:
    """Sert un quiz depuis le cache ou le génère via Mistral."""

    cache_key = build_cache_key(theme=theme, nb_questions=nb)
    cached_questions = await get_cached(cache_key)

    if cached_questions is not None:
        try:
            questions = _normalize_generated_questions(cached_questions)
            return QuizResponse(theme=theme, nb=nb, source="cache", questions=questions)
        except ValueError as exc:
            logger.warning("Cache invalide pour %s, régénération Mistral : %s", cache_key, exc)

    try:
        generated_questions = await generate_questions(theme=theme, nb=nb)
    except Exception as exc:
        logger.exception("Impossible de générer le quiz '%s' via Mistral : %s", theme, exc)
        raise HTTPException(
            status_code=503,
            detail="Service de génération indisponible : Mistral et cache ne permettent pas de servir ce quiz.",
        ) from exc

    questions = _normalize_generated_questions(generated_questions)
    await set_cache(cache_key, [question.model_dump() for question in questions])
    return QuizResponse(theme=theme, nb=nb, source="mistral", questions=questions)


@router.get("/api/quiz/generate", response_model=QuizResponse)
async def generate_quiz(
    theme: str = Query(..., min_length=2, max_length=100, description="Thème du quiz à générer."),
    nb: int = Query(5, ge=1, le=20, description="Nombre de questions souhaitées."),
) -> QuizResponse:
    """Génère un quiz sur un thème donné ou le sert depuis Redis."""

    return await _generate_or_get_from_cache(theme=theme.strip(), nb=nb)


@router.get("/api/quiz/themes", response_model=ThemesResponse)
async def list_themes() -> ThemesResponse:
    """Retourne les thèmes disponibles avec leurs métadonnées."""

    themes = [ThemeResponse.model_validate(theme) for theme in THEME_CATALOG]
    return ThemesResponse(themes=themes)


@router.get("/api/quiz/random", response_model=QuizResponse)
async def random_quiz(
    nb: int = Query(5, ge=1, le=20, description="Nombre de questions souhaitées."),
) -> QuizResponse:
    """Choisit un thème aléatoire et génère un quiz intergénérationnel."""

    # Priorité aux thèmes qui mélangent naturellement plusieurs générations.
    mixed_themes: list[ThemeMetadata] = [
        theme for theme in THEME_CATALOG if theme["era"] in {"mixte", "intemporel"}
    ]
    selected_theme = random.choice(mixed_themes or THEME_CATALOG)
    return await _generate_or_get_from_cache(theme=selected_theme["key"], nb=nb)
