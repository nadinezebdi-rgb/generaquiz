"""Application FastAPI principale pour Quiz d'Antan.

Variables d'environnement utilisées :
- MISTRAL_API_KEY : utilisée par le client Mistral dans le backend, non lue ici.
- REDIS_URL : utilisée par ``backend/cache.py`` pour créer le client Redis.
- ALLOWED_ORIGINS : liste des origines CORS autorisées, séparées par des virgules.
- APP_ENV : ``development`` ou ``production`` ; vaut ``development`` par défaut.
"""

from __future__ import annotations

import logging
import os
import sys
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import uvicorn
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from redis.exceptions import RedisError

# Compatibilité avec la structure existante : certains modules backend utilisent
# encore des imports absolus courts comme ``from cache import ...``.
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_PARENT_DIR = CURRENT_DIR.parent
BACKEND_DIR = CURRENT_DIR / "backend"

for path in (PROJECT_PARENT_DIR, BACKEND_DIR):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from quiz_antan.backend.cache import close_redis_client, get_redis_client  # noqa: E402
from quiz_antan.backend.cron_prefetch import start_scheduler  # noqa: E402
from quiz_antan.backend.router import router as quiz_router  # noqa: E402
from quiz_antan.backend.leaderboard_router import router as leaderboard_router  # noqa: E402
from quiz_antan.backend.family_router import router as family_router  # noqa: E402

try:
    from quiz_antan.backend.cron_prefetch import stop_scheduler as imported_stop_scheduler  # type: ignore[attr-defined] # noqa: E402
except ImportError:  # pragma: no cover - fallback si la fonction n'existe pas encore.
    imported_stop_scheduler = None


APP_ENV = os.getenv("APP_ENV", "development").lower()
APP_VERSION = "1.0.0"

logging.basicConfig(
    level=logging.INFO if APP_ENV == "development" else logging.WARNING,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


def _get_allowed_origins() -> list[str]:
    """Retourne les origines CORS autorisées depuis ALLOWED_ORIGINS."""

    raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
    return [origin.strip() for origin in raw_origins.split(",") if origin.strip()]


async def _redis_ping() -> bool:
    """Vérifie réellement que Redis répond à un PING."""

    client = get_redis_client()
    if client is None:
        return False

    try:
        response: Any = await client.ping()
        return bool(response)
    except (RedisError, TimeoutError, OSError) as exc:
        logger.warning("Redis ne répond pas au ping : %s", exc)
        return False


async def _stop_scheduler(scheduler: AsyncIOScheduler | None) -> None:
    """Arrête APScheduler proprement avec fallback local si besoin."""

    if imported_stop_scheduler is not None:
        result = imported_stop_scheduler()
        if hasattr(result, "__await__"):
            await result
        return

    if scheduler is not None and scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler arrêté.")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Cycle de vie applicatif : Redis au démarrage, nettoyage à l'arrêt."""

    scheduler: AsyncIOScheduler | None = None
    logger.info("Démarrage de Quiz d'Antan API en mode %s.", APP_ENV)

    try:
        redis_available = await _redis_ping()
        app.state.redis_available = redis_available
        logger.info("Redis initialisé : %s", "disponible" if redis_available else "indisponible")

        scheduler = start_scheduler()
        app.state.scheduler = scheduler
        yield
    finally:
        await _stop_scheduler(scheduler)
        await close_redis_client()
        logger.info("Arrêt complet de Quiz d'Antan API.")


app = FastAPI(
    title="Quiz d'Antan API",
    description="API intergénérationnelle de génération de quiz avec Mistral, Redis et APScheduler.",
    version=APP_VERSION,
    lifespan=lifespan,
)

# TrustedHostMiddleware volontairement désactivé : trop restrictif en développement.

app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next: Any) -> Response:
    """Log simple des requêtes : méthode, chemin, statut et durée."""

    started_at = time.perf_counter()
    status_code = 500

    try:
        response: Response = await call_next(request)
        status_code = response.status_code
        return response
    except Exception:
        logger.exception("Erreur non gérée pendant %s %s", request.method, request.url.path)
        raise
    finally:
        duration_ms = (time.perf_counter() - started_at) * 1000
        logger.info(
            "%s %s -> %s en %.2f ms",
            request.method,
            request.url.path,
            status_code,
            duration_ms,
        )


@app.get("/", tags=["system"])
async def root() -> dict[str, str]:
    """Route racine de contrôle rapide."""

    return {"status": "ok", "app": "Quiz d'Antan API", "version": APP_VERSION}


@app.get("/health", tags=["system"])
async def health() -> JSONResponse:
    """Retourne l'état de santé de l'API et de Redis."""

    redis_available = await _redis_ping()
    app.state.redis_available = redis_available
    return JSONResponse(content={"status": "healthy", "redis": redis_available})


app.include_router(quiz_router, prefix="/api/quiz", tags=["quiz"])
app.include_router(leaderboard_router, prefix="/api/leaderboard", tags=["leaderboard"])
app.include_router(family_router, prefix="/api/family", tags=["family"])


if __name__ == "__main__":
    uvicorn.run(
        "quiz_antan.main:app",
        host="0.0.0.0",
        port=8000,
        reload=APP_ENV == "development",
    )
