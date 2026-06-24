"""Pré-génération nocturne des quiz Quiz d'Antan.

Ce script peut être lancé directement :
    python cron_prefetch.py

Il peut aussi être importé par l'application principale afin d'activer la tâche
APScheduler qui pré-génère les questions tous les jours à 2h du matin.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from cache import build_cache_key, close_redis_client, set_cache
from mistral_client import generate_questions
from prompts import THEME_CATALOG


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

PREFETCH_NB_QUESTIONS = 10
PREFETCH_TTL_SECONDS = 86_400


async def prefetch_all_themes(nb: int = PREFETCH_NB_QUESTIONS) -> dict[str, Any]:
    """Génère et met en cache tous les thèmes disponibles."""

    total = len(THEME_CATALOG)
    successes = 0
    failures: list[dict[str, str]] = []

    logger.info("Début de pré-génération de %s thèmes, %s questions par thème.", total, nb)

    for index, theme_metadata in enumerate(THEME_CATALOG, start=1):
        theme = theme_metadata["key"]
        cache_key = build_cache_key(theme=theme, nb_questions=nb)
        logger.info("[%s/%s] Génération du thème : %s", index, total, theme)

        try:
            questions = await generate_questions(theme=theme, nb=nb)
            saved = await set_cache(cache_key, questions, ttl=PREFETCH_TTL_SECONDS)
            if saved:
                logger.info("[%s/%s] Thème mis en cache : %s", index, total, cache_key)
            else:
                logger.warning(
                    "[%s/%s] Génération réussie mais cache Redis indisponible : %s",
                    index,
                    total,
                    theme,
                )
            successes += 1
        except Exception as exc:
            logger.exception("[%s/%s] Erreur sur le thème '%s' : %s", index, total, theme, exc)
            failures.append({"theme": theme, "error": str(exc)})

    summary: dict[str, Any] = {
        "total": total,
        "successes": successes,
        "failures_count": len(failures),
        "failures": failures,
    }
    logger.info("Pré-génération terminée : %s", summary)
    return summary


def create_scheduler() -> AsyncIOScheduler:
    """Crée un scheduler APScheduler configuré pour 2h du matin."""

    scheduler = AsyncIOScheduler(timezone="Europe/Paris")
    scheduler.add_job(
        prefetch_all_themes,
        trigger=CronTrigger(hour=2, minute=0, timezone="Europe/Paris"),
        id="quiz_antan_prefetch_nightly",
        name="Pré-génération nocturne Quiz d'Antan",
        replace_existing=True,
        kwargs={"nb": PREFETCH_NB_QUESTIONS},
        max_instances=1,
        coalesce=True,
    )
    return scheduler


def start_scheduler() -> AsyncIOScheduler:
    """Démarre le scheduler et retourne l'instance active."""

    scheduler = create_scheduler()
    scheduler.start()
    logger.info("APScheduler démarré : pré-génération quotidienne à 2h00 Europe/Paris.")
    return scheduler


async def _main() -> None:
    """Point d'entrée asynchrone pour le lancement standalone."""

    try:
        await prefetch_all_themes(nb=PREFETCH_NB_QUESTIONS)
    finally:
        await close_redis_client()


if __name__ == "__main__":
    asyncio.run(_main())
