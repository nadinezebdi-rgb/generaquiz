"""Suivi mensuel des tarifs et performances Mistral pour Quiz d'Antan.

Ce module peut être lancé manuellement :
    python mistral_monitor.py

Il peut aussi être planifié via APScheduler depuis `cron_prefetch.py`.

# Dans cron_prefetch.py, ajouter dans start_scheduler() :
# from mistral_monitor import run_monthly_monitor
# scheduler.add_job(run_monthly_monitor, 'cron', day=1, hour=3, minute=0,
#                   id='monthly_mistral_monitor', replace_existing=True)
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import Any, TypedDict

import httpx
from mistralai import Mistral


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

BENCHMARK_PROMPT = (
    "Génère 2 questions de quiz intergénérationnel sur la cuisine française. "
    "Réponds en JSON uniquement."
)

MODELS_TO_MONITOR = [
    "mistral-small-latest",
    "mistral-large-latest",
    "mistral-medium-latest",
]

# Tarifs de référence connus au moment de génération du script — juin 2026.
# Unité : dollars US par million de tokens.
REFERENCE_PRICING: dict[str, dict[str, float]] = {
    "mistral-small-latest": {"input_price": 0.15, "output_price": 0.60},
    "mistral-large-latest": {"input_price": 0.50, "output_price": 1.50},
    "mistral-medium-latest": {"input_price": 1.50, "output_price": 7.50},
}

MISTRAL_MODELS_ENDPOINT = "https://api.mistral.ai/v1/models"
DEFAULT_TIMEOUT_SECONDS = 30.0


class BenchmarkResult(TypedDict):
    """Résultat agrégé d'un benchmark de latence."""

    model: str
    avg_ms: float | None
    min_ms: float | None
    max_ms: float | None
    success_rate: float
    timestamp: str


class PricingModel(TypedDict):
    """Tarif surveillé pour un modèle."""

    name: str
    input_price: float
    output_price: float
    changed: bool


class PricingResult(TypedDict):
    """Résultat de vérification des tarifs."""

    models: list[PricingModel]
    checked_at: str


def _utc_now_iso() -> str:
    """Retourne un timestamp UTC lisible et stable."""

    return datetime.now(UTC).isoformat(timespec="seconds")


def _get_env_int(name: str, default: int) -> int:
    """Lit un entier depuis l'environnement avec fallback sûr."""

    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        return int(raw_value)
    except ValueError:
        logger.warning("Variable %s invalide (%r), valeur par défaut utilisée : %s", name, raw_value, default)
        return default


def _get_api_key() -> str:
    """Récupère la clé API Mistral depuis l'environnement."""

    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        raise RuntimeError("MISTRAL_API_KEY est requise pour le suivi Mistral.")
    return api_key


def _extract_stream_delta(chunk: Any) -> str:
    """Extrait prudemment un fragment de texte depuis un chunk streaming Mistral."""

    try:
        delta_content = chunk.data.choices[0].delta.content
    except (AttributeError, IndexError):
        try:
            delta_content = chunk.choices[0].delta.content
        except (AttributeError, IndexError):
            return ""

    if isinstance(delta_content, str):
        return delta_content
    if isinstance(delta_content, list):
        parts: list[str] = []
        for item in delta_content:
            text = getattr(item, "text", None)
            if isinstance(text, str):
                parts.append(text)
            elif isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return "".join(parts)
    return ""


def _benchmark_latency_sync(model: str) -> float:
    """Effectue un appel Mistral synchrone et retourne la latence en millisecondes.

    La mesure cible le TTFT via streaming. Si le streaming échoue ou n'est pas
    disponible pour le SDK/modèle, on bascule sur un appel complet et on mesure
    le temps total.
    """

    client = Mistral(api_key=_get_api_key())
    messages = [{"role": "user", "content": BENCHMARK_PROMPT}]

    start = time.perf_counter()
    try:
        stream = client.chat.stream(
            model=model,
            messages=messages,
            temperature=0.2,
            max_tokens=350,
            response_format={"type": "json_object"},
        )
        for chunk in stream:
            delta = _extract_stream_delta(chunk)
            if delta:
                return (time.perf_counter() - start) * 1000

        # Si le stream termine sans token exploitable, on conserve le temps total
        # comme approximation prudente.
        return (time.perf_counter() - start) * 1000
    except Exception as stream_exc:
        logger.warning(
            "Streaming indisponible/échoué pour %s, mesure en temps total : %s",
            model,
            stream_exc,
        )

    start = time.perf_counter()
    client.chat.complete(
        model=model,
        messages=messages,
        temperature=0.2,
        max_tokens=350,
        response_format={"type": "json_object"},
    )
    return (time.perf_counter() - start) * 1000


async def benchmark_latency(model: str, nb_runs: int = 3) -> BenchmarkResult:
    """Mesure la latence Mistral pour un modèle donné.

    Chaque run envoie un appel réel avec un prompt court et fixe. En cas de
    timeout, une nouvelle tentative unique est effectuée. Les autres erreurs
    sont journalisées et le run est compté en échec.
    """

    if nb_runs < 1:
        raise ValueError("nb_runs doit être supérieur ou égal à 1.")

    timeout_seconds = float(os.getenv("MISTRAL_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS)))
    latencies_ms: list[float] = []
    successes = 0

    logger.info("Benchmark Mistral démarré pour %s (%s runs).", model, nb_runs)

    for run_index in range(1, nb_runs + 1):
        for attempt in range(1, 3):
            try:
                latency_ms = await asyncio.wait_for(
                    asyncio.to_thread(_benchmark_latency_sync, model),
                    timeout=timeout_seconds,
                )
                latencies_ms.append(latency_ms)
                successes += 1
                logger.info(
                    "Benchmark %s run %s/%s réussi : %.0f ms.",
                    model,
                    run_index,
                    nb_runs,
                    latency_ms,
                )
                break
            except (asyncio.TimeoutError, TimeoutError) as exc:
                logger.warning(
                    "Timeout benchmark %s run %s/%s tentative %s/2 : %s",
                    model,
                    run_index,
                    nb_runs,
                    attempt,
                    exc,
                )
                if attempt >= 2:
                    logger.error("Benchmark %s run %s échoué après retry timeout.", model, run_index)
            except Exception as exc:
                logger.exception(
                    "Erreur benchmark %s run %s/%s : %s",
                    model,
                    run_index,
                    nb_runs,
                    exc,
                )
                break

    return {
        "model": model,
        "avg_ms": round(mean(latencies_ms), 2) if latencies_ms else None,
        "min_ms": round(min(latencies_ms), 2) if latencies_ms else None,
        "max_ms": round(max(latencies_ms), 2) if latencies_ms else None,
        "success_rate": round(successes / nb_runs, 4),
        "timestamp": _utc_now_iso(),
    }


def _extract_remote_pricing(models_payload: Any) -> dict[str, dict[str, float]]:
    """Tente d'extraire les tarifs depuis la réponse `/v1/models`.

    L'API peut ne pas exposer de pricing. Cette fonction accepte plusieurs
    formes possibles afin de rester robuste sans imposer de dépendance au format
    exact : `pricing`, `price`, `input_price`, `output_price`, ou prix par token.
    """

    if not isinstance(models_payload, dict):
        return {}

    items = models_payload.get("data") or models_payload.get("models") or []
    if not isinstance(items, list):
        return {}

    remote_prices: dict[str, dict[str, float]] = {}

    for item in items:
        if not isinstance(item, dict):
            continue

        model_name = item.get("id") or item.get("name") or item.get("model")
        if not isinstance(model_name, str) or model_name not in REFERENCE_PRICING:
            continue

        pricing = item.get("pricing") or item.get("price") or item.get("prices") or item
        if not isinstance(pricing, dict):
            continue

        input_price = (
            pricing.get("input_price")
            or pricing.get("input")
            or pricing.get("prompt")
            or pricing.get("prompt_price")
            or pricing.get("input_cost_per_million_tokens")
        )
        output_price = (
            pricing.get("output_price")
            or pricing.get("output")
            or pricing.get("completion")
            or pricing.get("completion_price")
            or pricing.get("output_cost_per_million_tokens")
        )

        # Si l'endpoint expose un prix par token, conversion en prix / million.
        input_per_token = pricing.get("input_cost_per_token") or pricing.get("prompt_cost_per_token")
        output_per_token = pricing.get("output_cost_per_token") or pricing.get("completion_cost_per_token")
        if input_price is None and input_per_token is not None:
            input_price = float(input_per_token) * 1_000_000
        if output_price is None and output_per_token is not None:
            output_price = float(output_per_token) * 1_000_000

        try:
            if input_price is not None and output_price is not None:
                remote_prices[model_name] = {
                    "input_price": float(input_price),
                    "output_price": float(output_price),
                }
        except (TypeError, ValueError):
            logger.warning("Pricing distant non exploitable pour %s : %s", model_name, pricing)

    return remote_prices


async def check_pricing() -> PricingResult:
    """Vérifie les tarifs Mistral actuels et les compare aux références stockées."""

    api_key = _get_api_key()
    checked_at = _utc_now_iso()
    remote_prices: dict[str, dict[str, float]] = {}

    logger.info("Vérification des tarifs Mistral via %s.", MISTRAL_MODELS_ENDPOINT)

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(
                MISTRAL_MODELS_ENDPOINT,
                headers={"Authorization": f"Bearer {api_key}"},
            )
            response.raise_for_status()
            remote_prices = _extract_remote_pricing(response.json())
    except Exception as exc:
        logger.warning("Impossible de récupérer/interpréter les tarifs distants : %s", exc)

    if not remote_prices:
        logger.warning(
            "L'endpoint Mistral ne retourne pas de pricing exploitable ; tarifs stockés conservés."
        )

    models: list[PricingModel] = []
    for model_name, reference in REFERENCE_PRICING.items():
        current = remote_prices.get(model_name, reference)
        changed = (
            round(float(current["input_price"]), 6) != round(float(reference["input_price"]), 6)
            or round(float(current["output_price"]), 6) != round(float(reference["output_price"]), 6)
        )
        models.append(
            {
                "name": model_name,
                "input_price": float(current["input_price"]),
                "output_price": float(current["output_price"]),
                "changed": changed,
            }
        )

    return {"models": models, "checked_at": checked_at}


def estimate_monthly_cost(nb_quiz: int, cache_ratio: int = 30) -> dict[str, dict[str, float | int]]:
    """Estime le coût mensuel brut et avec cache pour chaque modèle surveillé.

    Hypothèse simple et conservatrice : `MONITOR_TOKENS_PER_QUIZ` représente le
    total de tokens par quiz, réparti à parts égales entre entrée et sortie.
    Le cache réduit le nombre de quiz réellement générés côté API.
    """

    if nb_quiz < 0:
        raise ValueError("nb_quiz ne peut pas être négatif.")
    if cache_ratio < 0 or cache_ratio > 100:
        raise ValueError("cache_ratio doit être compris entre 0 et 100.")

    tokens_per_quiz = _get_env_int("MONITOR_TOKENS_PER_QUIZ", 800)
    input_tokens_per_quiz = tokens_per_quiz / 2
    output_tokens_per_quiz = tokens_per_quiz / 2
    effective_quiz = nb_quiz * (1 - cache_ratio / 100)

    estimates: dict[str, dict[str, float | int]] = {}
    for model_name, pricing in REFERENCE_PRICING.items():
        input_cost = (nb_quiz * input_tokens_per_quiz / 1_000_000) * pricing["input_price"]
        output_cost = (nb_quiz * output_tokens_per_quiz / 1_000_000) * pricing["output_price"]
        gross_cost = input_cost + output_cost
        cached_cost = gross_cost * (1 - cache_ratio / 100)

        estimates[model_name] = {
            "monthly_quiz": nb_quiz,
            "cache_ratio": cache_ratio,
            "effective_api_quiz": round(effective_quiz, 2),
            "tokens_per_quiz": tokens_per_quiz,
            "gross_cost_usd": round(gross_cost, 4),
            "cached_cost_usd": round(cached_cost, 4),
        }

    return estimates


def _format_ms(value: float | None) -> str:
    """Formate une latence optionnelle."""

    return "N/A" if value is None else f"{value:.0f} ms"


def _choose_recommended_model(
    benchmark_results: list[BenchmarkResult],
    cost_estimates: dict[str, dict[str, float | int]],
) -> str:
    """Détermine automatiquement un modèle recommandé pour Quiz d'Antan."""

    usable_results = [result for result in benchmark_results if result["avg_ms"] is not None]
    if not usable_results:
        return (
            "Aucun benchmark exploitable. Par défaut, utiliser `mistral-small-latest` "
            "pour limiter le coût jusqu'au prochain rapport."
        )

    # Score simple : privilégier coût bas, succès élevé et latence faible.
    best_model = "mistral-small-latest"
    best_score = float("inf")
    for result in usable_results:
        model_name = result["model"]
        avg_ms = float(result["avg_ms"] or 0)
        success_rate = max(float(result["success_rate"]), 0.01)
        monthly_cost = float(cost_estimates.get(model_name, {}).get("cached_cost_usd", 0.0))
        score = (monthly_cost * 1000 + avg_ms / 100) / success_rate
        if score < best_score:
            best_model = model_name
            best_score = score

    if best_model == "mistral-small-latest":
        return (
            "Recommandation : `mistral-small-latest` reste le meilleur choix par défaut "
            "pour un quiz à grande échelle, car il minimise le coût tout en offrant une "
            "latence généralement suffisante pour générer des questions courtes."
        )
    if best_model == "mistral-large-latest":
        return (
            "Recommandation : `mistral-large-latest` ressort du benchmark. À réserver aux "
            "modes premium ou aux questions nécessitant une qualité maximale, car son coût "
            "reste supérieur à `mistral-small-latest`."
        )
    return (
        "Recommandation : `mistral-medium-latest` ressort du benchmark. Vérifier toutefois "
        "le rapport coût/qualité sur vos vrais retours utilisateurs avant de le généraliser."
    )


def generate_report(
    benchmark_results: list[BenchmarkResult],
    pricing: PricingResult,
    cost_estimates: dict[str, dict[str, float | int]],
) -> str:
    """Génère et sauvegarde le rapport Markdown mensuel."""

    report_date = datetime.now(UTC)
    month_key = report_date.strftime("%Y-%m")
    reports_dir = Path("reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / f"mistral_report_{month_key}.md"

    benchmark_lines = [
        "| Modèle | Latence moyenne | Min | Max | Taux de succès | Mesuré le |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for result in benchmark_results:
        benchmark_lines.append(
            "| {model} | {avg} | {min_} | {max_} | {success:.0%} | {timestamp} |".format(
                model=result["model"],
                avg=_format_ms(result["avg_ms"]),
                min_=_format_ms(result["min_ms"]),
                max_=_format_ms(result["max_ms"]),
                success=float(result["success_rate"]),
                timestamp=result["timestamp"],
            )
        )

    pricing_lines = [
        "| Modèle | Input ($/M tokens) | Output ($/M tokens) | Statut |",
        "|---|---:|---:|---|",
    ]
    for model_pricing in pricing["models"]:
        status = "⚠ CHANGEMENT DÉTECTÉ" if model_pricing["changed"] else "OK"
        pricing_lines.append(
            "| {name} | ${input_price:.4f} | ${output_price:.4f} | {status} |".format(
                name=model_pricing["name"],
                input_price=model_pricing["input_price"],
                output_price=model_pricing["output_price"],
                status=status,
            )
        )

    cost_lines = [
        "| Modèle | Quiz/mois | Tokens/quiz | Cache | Quiz API estimés | Coût brut | Coût avec cache |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for model_name, estimate in cost_estimates.items():
        cost_lines.append(
            "| {model} | {monthly_quiz} | {tokens_per_quiz} | {cache_ratio}% | {effective_api_quiz} | ${gross:.4f} | ${cached:.4f} |".format(
                model=model_name,
                monthly_quiz=int(estimate["monthly_quiz"]),
                tokens_per_quiz=int(estimate["tokens_per_quiz"]),
                cache_ratio=int(estimate["cache_ratio"]),
                effective_api_quiz=estimate["effective_api_quiz"],
                gross=float(estimate["gross_cost_usd"]),
                cached=float(estimate["cached_cost_usd"]),
            )
        )

    recommendation = _choose_recommended_model(benchmark_results, cost_estimates)

    report_content = "\n".join(
        [
            f"# Rapport mensuel Mistral — Quiz d'Antan — {month_key}",
            "",
            f"Date du rapport : {report_date.isoformat(timespec='seconds')}",
            f"Tarifs vérifiés le : {pricing['checked_at']}",
            "",
            "## 1. Benchmark de latence",
            "",
            *benchmark_lines,
            "",
            "## 2. Tarifs actuels",
            "",
            *pricing_lines,
            "",
            "## 3. Coûts mensuels estimés",
            "",
            *cost_lines,
            "",
            "## 4. Recommandation automatique",
            "",
            recommendation,
            "",
            "## 5. Configuration utilisée",
            "",
            f"- `MONITOR_MONTHLY_QUIZ` : {next(iter(cost_estimates.values()))['monthly_quiz'] if cost_estimates else 'N/A'}",
            f"- `MONITOR_CACHE_RATIO` : {next(iter(cost_estimates.values()))['cache_ratio'] if cost_estimates else 'N/A'}%",
            f"- `MONITOR_TOKENS_PER_QUIZ` : {next(iter(cost_estimates.values()))['tokens_per_quiz'] if cost_estimates else 'N/A'}",
            f"- Modèles suivis : {', '.join(MODELS_TO_MONITOR)}",
            "",
        ]
    )

    report_path.write_text(report_content, encoding="utf-8")
    logger.info("Rapport Mistral sauvegardé : %s", report_path)
    return report_content


async def send_notification(report_content: str) -> None:
    """Envoie le rapport vers un webhook Slack/Discord si configuré."""

    webhook_url = os.getenv("MONITOR_WEBHOOK_URL")
    if not webhook_url:
        logger.info("Notification désactivée : MONITOR_WEBHOOK_URL absente.")
        return

    summary = report_content[:2000]
    payload = {"text": "Rapport Mistral mensuel — Quiz d'Antan\n" + summary}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(webhook_url, json=payload)
            response.raise_for_status()
        logger.info("Notification Mistral envoyée avec succès.")
    except Exception as exc:
        logger.exception("Échec d'envoi de la notification Mistral : %s", exc)


async def run_monthly_monitor() -> None:
    """Orchestre le suivi mensuel complet Mistral."""

    start_time = time.perf_counter()
    logger.info("Démarrage du suivi mensuel Mistral — Quiz d'Antan.")

    benchmark_runs = _get_env_int("MONITOR_BENCHMARK_RUNS", 3)
    monthly_quiz = _get_env_int("MONITOR_MONTHLY_QUIZ", 10_000)
    cache_ratio = _get_env_int("MONITOR_CACHE_RATIO", 30)

    logger.info("Étape 1/5 — Benchmark de latence des modèles Mistral.")
    benchmark_results: list[BenchmarkResult] = []
    for model in MODELS_TO_MONITOR:
        benchmark_results.append(await benchmark_latency(model=model, nb_runs=benchmark_runs))

    logger.info("Étape 2/5 — Vérification des tarifs Mistral.")
    pricing = await check_pricing()

    logger.info("Étape 3/5 — Calcul des coûts mensuels estimés.")
    cost_estimates = estimate_monthly_cost(nb_quiz=monthly_quiz, cache_ratio=cache_ratio)

    logger.info("Étape 4/5 — Génération du rapport Markdown.")
    report_content = generate_report(
        benchmark_results=benchmark_results,
        pricing=pricing,
        cost_estimates=cost_estimates,
    )

    logger.info("Étape 5/5 — Notification optionnelle.")
    await send_notification(report_content)

    elapsed_seconds = time.perf_counter() - start_time
    logger.info("Suivi mensuel Mistral terminé en %.2f secondes.", elapsed_seconds)


if __name__ == "__main__":
    asyncio.run(run_monthly_monitor())
