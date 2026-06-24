"""Service métier pour scores, classements et badges de Quiz d'Antan."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Literal

try:  # Imports compatibles exécution package et lancement local depuis backend/.
    from quiz_antan.backend.supabase_client import get_supabase_client
except ImportError:  # pragma: no cover
    from supabase_client import get_supabase_client


Period = Literal["week", "month", "alltime"]
Difficulty = Literal["facile", "moyen", "difficile"]

DIFFICULTY_WEIGHTS: dict[str, float] = {
    "facile": 1.0,
    "moyen": 1.5,
    "difficile": 2.0,
}


SessionData = dict[str, Any]


def _utc_now_iso() -> str:
    """Retourne un horodatage UTC compatible Supabase/PostgREST."""

    return datetime.now(UTC).isoformat()


def _period_start(period: Period) -> str | None:
    """Convertit une période métier en borne temporelle ISO."""

    now = datetime.now(UTC)
    if period == "week":
        return (now - timedelta(days=7)).isoformat()
    if period == "month":
        return (now - timedelta(days=30)).isoformat()
    return None


def _round_score(value: float) -> float:
    """Arrondit le score à deux décimales de façon stable."""

    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _normalize_period(period: str) -> Period:
    """Valide une période de classement."""

    if period not in {"week", "month", "alltime"}:
        raise ValueError("La période doit être 'week', 'month' ou 'alltime'.")
    return period  # type: ignore[return-value]


def _difficulty_from_question(question: dict[str, Any]) -> str | None:
    """Extrait la difficulté d'une question si elle existe."""

    difficulty = question.get("difficulty")
    return difficulty if isinstance(difficulty, str) else None


def _question_lookup(questions: list[dict[str, Any]] | None) -> dict[str, dict[str, Any]]:
    """Indexe les questions par identifiant pour compléter les réponses."""

    lookup: dict[str, dict[str, Any]] = {}
    for question in questions or []:
        question_id = question.get("id") or question.get("question_id")
        if question_id is not None:
            lookup[str(question_id)] = question
    return lookup


def _calculate_scores(
    answers: list[dict[str, Any]],
    questions: list[dict[str, Any]] | None = None,
) -> tuple[int, int, float, int, float]:
    """Calcule score brut, total, difficulté moyenne, bonus temps et score pondéré."""

    total_questions = len(answers)
    if total_questions <= 0:
        raise ValueError("Impossible de soumettre un score sans réponse.")

    questions_by_id = _question_lookup(questions)
    raw_score = sum(1 for answer in answers if bool(answer.get("correct")))
    difficulty_values: list[float] = []
    time_bonus = 0

    for answer in answers:
        question_id = answer.get("question_id")
        source_question = questions_by_id.get(str(question_id), {}) if question_id is not None else {}
        difficulty = answer.get("difficulty") or _difficulty_from_question(source_question) or "facile"
        difficulty_values.append(DIFFICULTY_WEIGHTS.get(str(difficulty).lower(), 1.0))

        # Le bonus temps peut être fourni explicitement par question. En fallback,
        # on récompense légèrement les bonnes réponses rapides sans jamais pénaliser.
        explicit_bonus = answer.get("time_bonus")
        if isinstance(explicit_bonus, (int, float)):
            time_bonus += max(0, int(explicit_bonus))
            continue

        time_taken = answer.get("time_taken_seconds")
        if bool(answer.get("correct")) and isinstance(time_taken, (int, float)):
            time_bonus += max(0, min(10, int(10 - float(time_taken) // 3)))

    difficulty_avg = sum(difficulty_values) / len(difficulty_values)
    weighted_score = (raw_score / total_questions) * 100 * difficulty_avg + time_bonus
    return raw_score, total_questions, _round_score(difficulty_avg), int(time_bonus), _round_score(weighted_score)


async def _to_thread(callable_obj: Any) -> Any:
    """Exécute une requête Supabase synchrone hors boucle événementielle."""

    return await asyncio.to_thread(callable_obj)


def _response_data(response: Any) -> Any:
    """Récupère le champ data d'une réponse supabase-py."""

    return getattr(response, "data", None)


async def _get_rank_in_family(family_id: str, player_id: str) -> int | None:
    """Retourne le rang actuel d'un joueur dans sa famille."""

    supabase = get_supabase_client()

    def sync_query() -> Any:
        return (
            supabase.table("v_player_leaderboard")
            .select("player_id,rank_in_family")
            .eq("family_id", family_id)
            .eq("player_id", player_id)
            .maybe_single()
            .execute()
        )

    data = _response_data(await _to_thread(sync_query))
    if isinstance(data, dict):
        rank = data.get("rank_in_family")
        return int(rank) if rank is not None else None
    return None


async def submit_score(
    session_token: str,
    player_id: str,
    family_id: str,
    theme: str,
    answers: list[dict[str, Any]],
    questions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Soumet le score final d'une session et attribue les badges éventuels."""

    supabase = get_supabase_client()

    def find_completed_session() -> Any:
        return (
            supabase.table("quiz_sessions")
            .select("id,completed_at")
            .eq("session_token", session_token)
            .not_.is_("completed_at", "null")
            .limit(1)
            .execute()
        )

    already_completed = _response_data(await _to_thread(find_completed_session)) or []
    if already_completed:
        raise ValueError("Cette session a déjà été soumise.")

    raw_score, total_questions, difficulty_avg, time_bonus, weighted_score = _calculate_scores(
        answers=answers,
        questions=questions,
    )
    completed_at = _utc_now_iso()

    session_payload = {
        "session_token": session_token,
        "player_id": player_id,
        "family_id": family_id,
        "theme": theme,
        "nb_questions": total_questions,
        "completed_at": completed_at,
    }

    def upsert_session() -> Any:
        return (
            supabase.table("quiz_sessions")
            .upsert(session_payload, on_conflict="session_token")
            .execute()
        )

    session_rows = _response_data(await _to_thread(upsert_session)) or []
    if not session_rows:
        raise RuntimeError("Impossible d'enregistrer la session Supabase.")
    session_id = session_rows[0]["id"]

    score_payload = {
        "session_id": session_id,
        "player_id": player_id,
        "family_id": family_id,
        "raw_score": raw_score,
        "total_questions": total_questions,
        "weighted_score": weighted_score,
        "difficulty_avg": difficulty_avg,
        "time_bonus": time_bonus,
        "theme": theme,
    }

    def insert_score() -> Any:
        return supabase.table("scores").insert(score_payload).execute()

    await _to_thread(insert_score)

    session_data: SessionData = {
        "session_id": session_id,
        "player_id": player_id,
        "family_id": family_id,
        "theme": theme,
        "raw_score": raw_score,
        "total_questions": total_questions,
        "weighted_score": weighted_score,
        "difficulty_avg": difficulty_avg,
        "time_bonus": time_bonus,
        "completed_at": completed_at,
    }
    badges_earned = await check_and_award_badges(player_id, family_id, session_data)
    rank_in_family = await _get_rank_in_family(family_id=family_id, player_id=player_id)

    return {"score": weighted_score, "rank": rank_in_family, "badges_earned": badges_earned}


async def get_family_leaderboard(family_id: str, period: str = "week") -> list[dict[str, Any]]:
    """Retourne le classement des joueurs d'une famille."""

    normalized_period = _normalize_period(period)
    supabase = get_supabase_client()

    if normalized_period == "alltime":
        def sync_query() -> Any:
            return (
                supabase.table("v_player_leaderboard")
                .select("*")
                .eq("family_id", family_id)
                .order("rank_in_family")
                .execute()
            )
    else:
        start = _period_start(normalized_period)

        def sync_query() -> Any:
            return (
                supabase.table("scores")
                .select("player_id,players!inner(pseudo,avatar),weighted_score,created_at")
                .eq("family_id", family_id)
                .gte("created_at", start)
                .order("weighted_score", desc=True)
                .execute()
            )

    data = _response_data(await _to_thread(sync_query)) or []
    if normalized_period == "alltime":
        return list(data)

    totals: dict[str, dict[str, Any]] = {}
    for row in data:
        current = totals.setdefault(
            row["player_id"],
            {
                "player_id": row["player_id"],
                "pseudo": (row.get("players") or {}).get("pseudo"),
                "avatar": (row.get("players") or {}).get("avatar"),
                "family_id": family_id,
                "total_score": 0.0,
                "nb_sessions": 0,
                "best_score": 0.0,
                "last_played_at": None,
            },
        )
        score = float(row.get("weighted_score") or 0)
        current["total_score"] = _round_score(float(current["total_score"]) + score)
        current["nb_sessions"] += 1
        current["best_score"] = max(float(current["best_score"]), score)
        played_at = row.get("created_at")
        if played_at and (current["last_played_at"] is None or played_at > current["last_played_at"]):
            current["last_played_at"] = played_at

    ranked = sorted(totals.values(), key=lambda item: item["total_score"], reverse=True)
    for index, row in enumerate(ranked, start=1):
        row["rank_in_family"] = index
    return ranked


async def get_global_leaderboard(period: str = "week", limit: int = 10) -> list[dict[str, Any]]:
    """Retourne le classement global des familles."""

    normalized_period = _normalize_period(period)
    safe_limit = max(1, min(int(limit), 100))
    supabase = get_supabase_client()

    if normalized_period == "alltime":
        def sync_query() -> Any:
            return (
                supabase.table("v_family_leaderboard")
                .select("*")
                .order("total_score", desc=True)
                .limit(safe_limit)
                .execute()
            )
    else:
        start = _period_start(normalized_period)

        def sync_query() -> Any:
            return (
                supabase.table("scores")
                .select("family_id,families!inner(name),theme,weighted_score,created_at")
                .gte("created_at", start)
                .order("weighted_score", desc=True)
                .execute()
            )

    data = _response_data(await _to_thread(sync_query)) or []
    if normalized_period == "alltime":
        return list(data)

    totals: dict[str, dict[str, Any]] = {}
    theme_totals: dict[str, dict[str, float]] = {}
    for row in data:
        family_id = row["family_id"]
        current = totals.setdefault(
            family_id,
            {
                "family_id": family_id,
                "family_name": (row.get("families") or {}).get("name"),
                "total_score": 0.0,
                "nb_sessions": 0,
                "last_played_at": None,
            },
        )
        score = float(row.get("weighted_score") or 0)
        current["total_score"] = _round_score(float(current["total_score"]) + score)
        current["nb_sessions"] += 1
        played_at = row.get("created_at")
        if played_at and (current["last_played_at"] is None or played_at > current["last_played_at"]):
            current["last_played_at"] = played_at
        theme = row.get("theme") or "inconnu"
        theme_totals.setdefault(family_id, {})[theme] = theme_totals.setdefault(family_id, {}).get(theme, 0.0) + score

    ranked = sorted(totals.values(), key=lambda item: item["total_score"], reverse=True)[:safe_limit]
    for index, row in enumerate(ranked, start=1):
        row["rank"] = index
        family_themes = theme_totals.get(row["family_id"], {})
        row["best_theme"] = max(family_themes, key=family_themes.get) if family_themes else None
    return ranked


async def get_theme_champions() -> list[dict[str, Any]]:
    """Retourne les champions globaux par thème."""

    supabase = get_supabase_client()

    def sync_query() -> Any:
        return supabase.table("v_theme_champions").select("*").order("theme").execute()

    data = _response_data(await _to_thread(sync_query)) or []
    return list(data)


async def _insert_badge_once(
    player_id: str,
    family_id: str,
    badge_type: str,
    context: dict[str, Any] | None = None,
) -> bool:
    """Insère un badge sans doublon, puis indique s'il est nouveau."""

    supabase = get_supabase_client()
    badge_context = context or {}

    def existing_badge() -> Any:
        query = (
            supabase.table("badges")
            .select("id")
            .eq("player_id", player_id)
            .eq("type", badge_type)
        )
        if badge_context.get("theme") is not None:
            query = query.eq("context->>theme", str(badge_context["theme"]))
        return query.limit(1).execute()

    existing = _response_data(await _to_thread(existing_badge)) or []
    if existing:
        return False

    payload = {
        "player_id": player_id,
        "family_id": family_id,
        "type": badge_type,
        "context": badge_context,
    }

    def insert_badge() -> Any:
        return supabase.table("badges").insert(payload).execute()

    try:
        await _to_thread(insert_badge)
        return True
    except Exception:
        # L'index unique Supabase reste la source de vérité en cas de course.
        return False


async def check_and_award_badges(
    player_id: str,
    family_id: str,
    session_data: SessionData,
) -> list[str]:
    """Attribue les badges automatiques gagnés par une session."""

    supabase = get_supabase_client()
    earned: list[str] = []

    def count_player_scores() -> Any:
        return (
            supabase.table("scores")
            .select("id", count="exact")
            .eq("player_id", player_id)
            .execute()
        )

    count_response = await _to_thread(count_player_scores)
    if getattr(count_response, "count", 0) == 1:
        if await _insert_badge_once(player_id, family_id, "first_game"):
            earned.append("first_game")

    if session_data["raw_score"] == session_data["total_questions"]:
        if await _insert_badge_once(
            player_id,
            family_id,
            "perfect_score",
            {"theme": session_data["theme"], "session_id": session_data["session_id"]},
        ):
            earned.append("perfect_score")

    since = (datetime.now(UTC) - timedelta(days=3)).isoformat()

    def count_recent_sessions() -> Any:
        return (
            supabase.table("quiz_sessions")
            .select("id", count="exact")
            .eq("player_id", player_id)
            .not_.is_("completed_at", "null")
            .gte("completed_at", since)
            .execute()
        )

    recent_sessions_response = await _to_thread(count_recent_sessions)
    if getattr(recent_sessions_response, "count", 0) >= 3:
        if await _insert_badge_once(player_id, family_id, "streak_3"):
            earned.append("streak_3")

    def best_theme_score_in_family() -> Any:
        return (
            supabase.table("scores")
            .select("player_id,weighted_score")
            .eq("family_id", family_id)
            .eq("theme", session_data["theme"])
            .order("weighted_score", desc=True)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

    best_rows = _response_data(await _to_thread(best_theme_score_in_family)) or []
    if best_rows and best_rows[0].get("player_id") == player_id:
        if await _insert_badge_once(
            player_id,
            family_id,
            "theme_champion",
            {"theme": session_data["theme"]},
        ):
            earned.append("theme_champion")

    return earned


async def get_player_badges(player_id: str) -> list[dict[str, Any]]:
    """Retourne les badges attribués à un joueur."""

    supabase = get_supabase_client()

    def sync_query() -> Any:
        return (
            supabase.table("badges")
            .select("*")
            .eq("player_id", player_id)
            .order("awarded_at", desc=True)
            .execute()
        )

    data = _response_data(await _to_thread(sync_query)) or []
    return list(data)
