"""Cache Redis asynchrone pour Quiz d'Antan.

Le cache accélère la génération de quiz et limite les appels à l'API Mistral.
Si Redis est indisponible, les fonctions échouent silencieusement avec un log
et l'application continue sans cache.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import redis.asyncio as redis
from redis.asyncio import Redis
from redis.exceptions import RedisError


logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
DEFAULT_TTL_SECONDS = 86_400

_redis_client: Redis | None = None
_redis_unavailable = False


def build_cache_key(theme: str, nb_questions: int) -> str:
    """Construit la clé de cache standardisée du quiz."""

    normalized_theme = theme.strip().lower().replace(" ", "-")
    return f"quiz:{normalized_theme}:{nb_questions}"


def get_redis_client() -> Redis | None:
    """Retourne un client Redis partagé, ou None si Redis est désactivé."""

    global _redis_client

    if _redis_unavailable:
        return None
    if not REDIS_URL:
        logger.warning("REDIS_URL absent : cache Redis désactivé.")
        return None
    if _redis_client is None:
        _redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    return _redis_client


async def get_cached(key: str) -> Any | None:
    """Lit une valeur JSON depuis Redis, avec fallback gracieux."""

    global _redis_unavailable

    client = get_redis_client()
    if client is None:
        return None

    try:
        raw_value = await client.get(key)
        if raw_value is None:
            return None
        return json.loads(raw_value)
    except (RedisError, json.JSONDecodeError, TimeoutError) as exc:
        _redis_unavailable = True
        logger.warning("Cache Redis indisponible pendant la lecture de %s : %s", key, exc)
        return None


async def set_cache(key: str, data: Any, ttl: int = DEFAULT_TTL_SECONDS) -> bool:
    """Stocke une valeur sérialisée en JSON dans Redis, avec TTL en secondes."""

    global _redis_unavailable

    client = get_redis_client()
    if client is None:
        return False

    try:
        serialized = json.dumps(data, ensure_ascii=False)
        await client.set(key, serialized, ex=ttl)
        return True
    except (RedisError, TypeError, TimeoutError) as exc:
        _redis_unavailable = True
        logger.warning("Cache Redis indisponible pendant l'écriture de %s : %s", key, exc)
        return False


async def close_redis_client() -> None:
    """Ferme proprement la connexion Redis si elle a été ouverte."""

    global _redis_client

    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
