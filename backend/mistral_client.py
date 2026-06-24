"""Client Mistral pour générer des questions de quiz.

Ce module appelle réellement l'API Mistral via le SDK `mistralai` v1+.
Les variables sensibles sont lues depuis l'environnement.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any, Literal, TypedDict

from mistralai import Mistral

from prompts import SYSTEM_PROMPT, build_user_prompt


logger = logging.getLogger(__name__)

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
MISTRAL_MODEL = os.getenv("MISTRAL_MODEL", "mistral-small-latest")
MISTRAL_TIMEOUT_SECONDS = float(os.getenv("MISTRAL_TIMEOUT_SECONDS", "30"))
MAX_TIMEOUT_RETRIES = 2

Difficulty = Literal["facile", "moyen", "difficile"]
Category = Literal["nostalgie", "moderne", "intemporel", "culture"]
Era = Literal["1950-1980", "1980-2000", "2000-2020", "intemporel"]


class QuestionDict(TypedDict):
    """Structure attendue pour une question générée."""

    question: str
    choices: list[str]
    answer: str
    difficulty: Difficulty
    category: Category
    era: Era


def _get_mistral_client() -> Mistral:
    """Instancie le client Mistral à partir de la clé API d'environnement."""

    if not MISTRAL_API_KEY:
        raise RuntimeError("MISTRAL_API_KEY est manquante dans l'environnement.")
    return Mistral(api_key=MISTRAL_API_KEY)


def _extract_content(response: Any) -> str:
    """Extrait le contenu texte d'une réponse chat Mistral."""

    try:
        content = response.choices[0].message.content
    except (AttributeError, IndexError) as exc:
        raise ValueError("Réponse Mistral invalide : contenu introuvable.") from exc

    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        # Certains SDK peuvent retourner des blocs typés ; on concatène le texte.
        parts: list[str] = []
        for item in content:
            text = getattr(item, "text", None)
            if isinstance(text, str):
                parts.append(text)
            elif isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return "".join(parts).strip()
    raise ValueError("Réponse Mistral invalide : format de contenu non supporté.")


def _strip_json_fences(raw_content: str) -> str:
    """Nettoie prudemment d'éventuelles balises Markdown malgré la consigne JSON."""

    content = raw_content.strip()
    if content.startswith("```json"):
        content = content.removeprefix("```json").strip()
    if content.startswith("```"):
        content = content.removeprefix("```").strip()
    if content.endswith("```"):
        content = content.removesuffix("```").strip()
    return content


def _validate_questions(data: Any) -> list[QuestionDict]:
    """Valide minimalement le JSON retourné par Mistral."""

    if not isinstance(data, list):
        raise ValueError("Le JSON retourné par Mistral doit être un tableau.")

    valid_difficulties = {"facile", "moyen", "difficile"}
    valid_categories = {"nostalgie", "moderne", "intemporel", "culture"}
    valid_eras = {"1950-1980", "1980-2000", "2000-2020", "intemporel"}
    questions: list[QuestionDict] = []

    for index, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"Question #{index + 1} invalide : objet attendu.")

        question = item.get("question")
        choices = item.get("choices")
        answer = item.get("answer")
        difficulty = item.get("difficulty")
        category = item.get("category")
        era = item.get("era")

        if not isinstance(question, str) or not question.strip():
            raise ValueError(f"Question #{index + 1} invalide : texte manquant.")
        if not isinstance(choices, list) or len(choices) != 4:
            raise ValueError(f"Question #{index + 1} invalide : 4 choix requis.")
        if not all(isinstance(choice, str) and choice.strip() for choice in choices):
            raise ValueError(f"Question #{index + 1} invalide : choix vides interdits.")
        if len(set(choices)) != 4:
            raise ValueError(f"Question #{index + 1} invalide : choix dupliqués.")
        if answer not in choices:
            raise ValueError(f"Question #{index + 1} invalide : réponse absente des choix.")
        if difficulty not in valid_difficulties:
            raise ValueError(f"Question #{index + 1} invalide : difficulté inconnue.")
        if category not in valid_categories:
            raise ValueError(f"Question #{index + 1} invalide : catégorie inconnue.")
        if era not in valid_eras:
            raise ValueError(f"Question #{index + 1} invalide : époque inconnue.")

        questions.append(
            {
                "question": question.strip(),
                "choices": [choice.strip() for choice in choices],
                "answer": str(answer).strip(),
                "difficulty": difficulty,
                "category": category,
                "era": era,
            }
        )

    return questions


async def _call_mistral(theme: str, nb: int) -> list[QuestionDict]:
    """Exécute un appel Mistral dans un thread pour préserver l'API async FastAPI."""

    def sync_call() -> list[QuestionDict]:
        client = _get_mistral_client()
        response = client.chat.complete(
            model=MISTRAL_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(theme=theme, nb=nb)},
            ],
            temperature=0.85,
            response_format={"type": "json_object"},
        )
        raw_content = _extract_content(response)
        parsed = json.loads(_strip_json_fences(raw_content))

        # Avec response_format=json_object, certains modèles enveloppent le tableau.
        if isinstance(parsed, dict):
            for key in ("questions", "data", "items"):
                if key in parsed:
                    parsed = parsed[key]
                    break
        return _validate_questions(parsed)

    return await asyncio.wait_for(asyncio.to_thread(sync_call), timeout=MISTRAL_TIMEOUT_SECONDS)


async def generate_questions(theme: str, nb: int = 5) -> list[QuestionDict]:
    """Génère `nb` questions via Mistral et retourne une liste de dictionnaires.

    Deux nouvelles tentatives sont effectuées en cas de timeout. Les autres
    erreurs sont journalisées puis remontées au routeur FastAPI.
    """

    if nb < 1 or nb > 20:
        raise ValueError("Le nombre de questions doit être compris entre 1 et 20.")
    cleaned_theme = theme.strip()
    if not cleaned_theme:
        raise ValueError("Le thème ne peut pas être vide.")

    total_attempts = MAX_TIMEOUT_RETRIES + 1
    for attempt in range(1, total_attempts + 1):
        try:
            return await _call_mistral(theme=cleaned_theme, nb=nb)
        except (asyncio.TimeoutError, TimeoutError) as exc:
            logger.warning(
                "Timeout Mistral pour le thème '%s' tentative %s/%s : %s",
                cleaned_theme,
                attempt,
                total_attempts,
                exc,
            )
            if attempt >= total_attempts:
                logger.error("Échec Mistral après retries timeout pour '%s'.", cleaned_theme)
                raise
            await asyncio.sleep(0.5 * attempt)
        except Exception as exc:
            logger.exception("Erreur Mistral pour le thème '%s' : %s", cleaned_theme, exc)
            raise

    raise RuntimeError("Échec inattendu de génération Mistral.")
