"""Job nocturne — auto-seed via queue manager.

Appelé chaque nuit à 05:00 Paris (après le régen Mistral à 03:00 et les jeux
annexes à 03:30/04:00/04:30) depuis `scheduler.py`.

Délègue à `auto_seed_understocked_categories()` qui :
  - détecte toutes les catégories avec < 140 questions jouables
  - lance un top-up pour chacune via le queue manager (max 2 en parallèle)
  - est 100 % idempotent (le 409 anti-doublon empêche les doublons avec un
    éventuel top-up admin manuel encore en cours)
  - donne une visibilité dashboard complète (jobs DB, progress bar, etc.)

L'ancienne implémentation lançait des subprocess Mistral+Opus en série sans
passer par le queue → risque de pic mémoire quand plusieurs jobs se
chevauchaient avec un run admin manuel. Ce refactor élimine ce risque.
"""
from __future__ import annotations

import logging

logger = logging.getLogger("quizdantan")


async def topup_all_categories_nightly() -> None:
    """Auto-seed nocturne — respecte la queue manager (2 jobs max en parallèle).

    Log un bilan structuré pour tracer ce qui a été lancé/queued/skippé.
    Ne bloque pas : les subprocess Mistral+Opus tournent en arrière-plan et
    seront pilotés par `_run_qa_subprocess` avec timeout + reap.
    """
    from routers.admin_qa import auto_seed_understocked_categories
    try:
        summary = await auto_seed_understocked_categories()
    except Exception as e:
        logger.exception(f"[paliers-topup-nightly] exception : {type(e).__name__}: {e}")
        return

    if summary["launched"] == 0 and summary["queued"] == 0:
        if summary["already_running"]:
            logger.info(
                f"[paliers-topup-nightly] {summary['already_running']} job(s) admin déjà "
                f"en cours — rien de plus à lancer"
            )
        else:
            logger.info(
                f"[paliers-topup-nightly] rien à faire, "
                f"{summary['skipped_complete']} catégorie(s) déjà complète(s) à 140/140"
            )
        return

    logger.info(
        f"[paliers-topup-nightly] auto-seed déclenché : "
        f"{summary['launched']} lancé(s), "
        f"{summary['queued']} en file, "
        f"{summary['already_running']} déjà en cours, "
        f"{summary['skipped_complete']} déjà complet(s)"
    )
    # Détail par catégorie (débug utile pour reconstituer une nuit)
    for c in summary["categories"]:
        logger.info(
            f"[paliers-topup-nightly]   · {c['category_id']}: "
            f"{c['playable']}/140 → {c['status']}"
        )
