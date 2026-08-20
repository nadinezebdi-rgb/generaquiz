"""APScheduler central pour GénéraQuiz.

Regroupe tous les jobs cron en un seul endroit, ce qui rend `server.py` et
`daily_email.py` beaucoup plus légers et rend la matrice horaire immédiatement
lisible d'un coup d'œil.

Matrice horaire (Europe/Paris) :

  Heure     Job                                     Cadence
  ─────     ───                                     ───────
  03:00     Régénération quiz Mistral               chaque jour
  03:30     Génération grille Mots Mêlés            chaque jour
  04:00     Génération charades Mistral             chaque jour
  04:30     Génération grille Mots Fléchés          chaque jour
  09:00     E-mail « Quiz du jour »                 chaque jour
  10:00     E-mail J-7 renouvellement Premium       chaque jour
  20:00     Rappel « fin de saison » ligues         chaque dimanche
  00:05     Clôture hebdomadaire des ligues         chaque lundi

Chaque job est ajouté avec `misfire_grace_time=3600` : si l'app est redémarrée
juste sur l'horaire prévu, le job passe quand même dans l'heure suivante.
"""
from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from core import logger


_scheduler: AsyncIOScheduler | None = None


def start_scheduler() -> None:
    """Démarre APScheduler et enregistre tous les jobs.

    Idempotent : un appel supplémentaire ne relance pas un second scheduler.
    Les imports des fonctions de jobs sont locaux à cette fonction pour éviter
    les cycles d'import au chargement du module.
    """
    global _scheduler
    if _scheduler is not None:
        return

    # Imports locaux — évite tout import cycle entre server ↔ scheduler ↔ jobs.
    from daily_email import (
        send_expiration_emails,
        send_league_reminders,
        send_morning_emails,
    )
    from routers.gamification import settle_finished_week
    from mistral_client import regenerate_all as mistral_regen
    from wordsearch_mistral import generate_one_grid_from_mistral
    from charades_mistral import generate_nightly_charades
    from fleches_mistral import generate_nightly_fleches
    from topup_paliers_job import topup_all_categories_nightly

    _scheduler = AsyncIOScheduler(timezone="Europe/Paris")

    # -- Génération nocturne (03:00 → 04:30 Paris) ------------------------------
    _schedule(_scheduler, mistral_regen,             hour=3,  minute=0,  job_id="mistral_regenerate_all")
    _schedule(_scheduler, generate_one_grid_from_mistral, hour=3, minute=30, job_id="wordsearch_generate_nightly")
    _schedule(_scheduler, generate_nightly_charades, hour=4,  minute=0,  job_id="charades_generate_nightly")
    _schedule(_scheduler, generate_nightly_fleches,  hour=4,  minute=30, job_id="fleches_generate_nightly")
    _schedule(_scheduler, topup_all_categories_nightly, hour=5, minute=0, job_id="paliers_topup_nightly")

    # -- E-mails transactionnels (09:00 & 10:00 Paris) --------------------------
    _schedule(_scheduler, send_morning_emails,       hour=9,  minute=0,  job_id="daily_quiz_email")
    _schedule(_scheduler, send_expiration_emails,    hour=10, minute=0,  job_id="premium_expiration_email_j7")

    # -- Ligues (dimanche 20:00 + lundi 00:05 Paris) ----------------------------
    _schedule(_scheduler, send_league_reminders,     day_of_week="sun", hour=20, minute=0, job_id="league_reminder_sunday_20h")
    _schedule(_scheduler, settle_finished_week,      day_of_week="mon", hour=0,  minute=5, job_id="leagues_weekly_settle")

    _scheduler.start()
    logger.info(
        "[scheduler] démarré — 9 jobs actifs "
        "(quiz 03:00 · wordsearch 03:30 · charades 04:00 · fléchés 04:30 · paliers top-up 05:00 · "
        "email quotidien 09:00 · relance J-7 10:00 · rappel ligues dim 20:00 · clôture ligues lun 00:05, Europe/Paris)"
    )


def stop_scheduler() -> None:
    """Arrête APScheduler proprement (shutdown non bloquant)."""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None


def _schedule(sched: AsyncIOScheduler, func, *, job_id: str, **cron_kwargs) -> None:
    """Helper interne : ajoute un job avec les réglages par défaut GénéraQuiz.

    Réglages appliqués :
      - timezone Europe/Paris
      - `replace_existing=True` pour un rechargement idempotent
      - `misfire_grace_time=3600` (1 h) pour absorber un redémarrage tardif
    """
    sched.add_job(
        func,
        CronTrigger(timezone="Europe/Paris", **cron_kwargs),
        id=job_id,
        replace_existing=True,
        misfire_grace_time=3600,
    )
