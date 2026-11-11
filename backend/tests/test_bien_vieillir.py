"""Tests hors-ligne de la rubrique « Bien vieillir ».

Contrairement aux autres fichiers de ce dossier, ces tests ne tapent pas
l'API : ils vérifient les fonctions pures du routeur et — surtout —
l'alignement des identifiants d'habitudes entre le backend et le front.
Cet alignement est la seule chose qui, si elle se casse, corrompt
silencieusement l'historique des utilisateurs.

Exécution : pytest backend/tests/test_bien_vieillir.py
"""
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Le module n'importe `core` que pour `db` et `get_current_user` ; on ne
# sollicite ici que des fonctions pures, mais l'import de `core` exige des
# variables d'environnement. On les fournit si elles manquent.
import os

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test")
os.environ.setdefault("JWT_SECRET", "test-secret")

from routers.bien_vieillir import (  # noqa: E402
    HABIT_IDS,
    MAX_WEEKS,
    WEEK_VALID_THRESHOLD,
    compute_streak,
    sanitise_weeks,
)

FRONTEND_HABITS = Path(__file__).resolve().parents[2] / "frontend" / "src" / "content" / "routineHebdo.js"
FULL = {hid: True for hid in list(HABIT_IDS)[:WEEK_VALID_THRESHOLD]}


def test_habit_ids_match_frontend():
    """Les ids du backend et du front doivent être strictement identiques."""
    source = FRONTEND_HABITS.read_text(encoding="utf-8")
    front_ids = set(re.findall(r'^\s*id:\s*"([a-z_]+)"', source, re.MULTILINE))
    assert front_ids, "aucun id trouvé dans routineHebdo.js — le format a changé ?"
    assert front_ids == HABIT_IDS, (
        "Désalignement front/back des habitudes. "
        f"Uniquement côté front : {front_ids - HABIT_IDS}. "
        f"Uniquement côté back : {HABIT_IDS - front_ids}."
    )


def test_threshold_matches_frontend():
    source = FRONTEND_HABITS.read_text(encoding="utf-8")
    match = re.search(r"WEEK_VALID_THRESHOLD\s*=\s*(\d+)", source)
    assert match, "WEEK_VALID_THRESHOLD introuvable côté front"
    assert int(match.group(1)) == WEEK_VALID_THRESHOLD


@pytest.mark.parametrize(
    "payload",
    [
        {"pas-une-semaine": {"marche": True}},
        {"2026-W37": {"habitude-inconnue": True}},
        {"2026-W37": "pas-un-dict"},
        {"2026-W99xx": {"marche": True}},
    ],
)
def test_sanitise_drops_invalid_input(payload):
    assert sanitise_weeks(payload) == {}


def test_sanitise_keeps_valid_input():
    assert sanitise_weeks({"2026-W37": {"marche": True, "inconnu": True}}) == {"2026-W37": {"marche": True}}


def test_sanitise_ignores_false_values():
    """Une case décochée n'est pas stockée — seul `True` compte."""
    assert sanitise_weeks({"2026-W37": {"marche": False}}) == {}


def test_sanitise_caps_history():
    weeks = {f"20{y:02d}-W{w:02d}": {"marche": True} for y in range(10, 30) for w in range(1, 53)}
    capped = sanitise_weeks(weeks)
    assert len(capped) == MAX_WEEKS
    # Les semaines conservées sont les plus récentes.
    assert max(capped) == max(weeks)


def test_streak_counts_consecutive_weeks():
    assert compute_streak({"2026-W35": FULL, "2026-W36": FULL, "2026-W37": FULL}) == 3


def test_streak_resets_on_gap():
    assert compute_streak({"2026-W30": FULL, "2026-W36": FULL, "2026-W37": FULL}) == 2


def test_streak_ignores_incomplete_weeks():
    assert compute_streak({"2026-W37": {"marche": True}}) == 0


def test_streak_crosses_year_boundary():
    assert compute_streak({"2020-W53": FULL, "2021-W01": FULL}) == 2
    assert compute_streak({"2025-W52": FULL, "2026-W01": FULL}) == 2


def test_streak_empty():
    assert compute_streak({}) == 0
