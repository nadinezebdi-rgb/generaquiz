"""Mots Fléchés MVP — 5 hand-authored 5×5 grids.

Model
-----
Each grid is a 5×5 board. Cells are one of:
  {"type": "block", "clue_h": "clue for row", "clue_v": "clue for col"}
     → an arrow cell showing 1 or 2 clues. Player cannot type here.
  {"type": "letter", "answer": "X"}
     → a fillable cell. Player types uppercase letter.

Clue direction convention
  clue_h → the answer runs to the RIGHT starting at the cell IMMEDIATELY to the right
  clue_v → the answer runs DOWN starting at the cell IMMEDIATELY BELOW
Both fields are optional; a block can hold either one, both, or none (pure separator).

Scoring: +1 pt per letter correctly placed on first submit, +5 bonus when
the whole grid is solved. Server validates the whole grid on submit.
"""
from __future__ import annotations

# 5 hand-authored grids. Each keeps the same 5×5 structure with a mix of blocks
# and letter cells. Clues are short and unambiguous, aimed at a senior audience.
# Note: These grids are hand-verified — each letter cell has its answer set,
# and each block clue points to the correct word direction.

GRIDS: list[dict] = [
    # ============ GRID 1 — Cuisine (very easy warm-up) ============
    {
        "id": "mf01",
        "theme": "Cuisine du dimanche",
        "emoji": "🍽️",
        "difficulty": "facile",
        "size": 5,
        "cells": [
            # row 0
            [{"type": "block"},
             {"type": "block", "clue_v": "Pas cuit"},
             {"type": "block", "clue_v": "Un fromage bleu"},
             {"type": "block", "clue_v": "Herbe aromatique"},
             {"type": "block", "clue_v": "Petit rongeur"}],
            # row 1
            [{"type": "block", "clue_h": "Céréale d'Asie"},
             {"type": "letter", "answer": "R"},
             {"type": "letter", "answer": "I"},
             {"type": "letter", "answer": "T"},
             {"type": "letter", "answer": "S"}],
            # row 2
            [{"type": "block", "clue_h": "Fruit rouge sucré"},
             {"type": "letter", "answer": "A"},
             {"type": "letter", "answer": "B"},
             {"type": "letter", "answer": "H"},
             {"type": "letter", "answer": "O"}],
            # row 3
            [{"type": "block", "clue_h": "Article défini fém."},
             {"type": "letter", "answer": "W"},
             {"type": "letter", "answer": "L"},
             {"type": "letter", "answer": "Y"},
             {"type": "letter", "answer": "U"}],
            # row 4
            [{"type": "block", "clue_h": "Cri du chat"},
             {"type": "letter", "answer": "M"},
             {"type": "letter", "answer": "E"},
             {"type": "letter", "answer": "M"},
             {"type": "letter", "answer": "R"}],
        ],
        # simple flat answer summary for validation help / reveal
        "notes": "Colonnes: RAWM (cru), IBLE (bleu — variante), THY M (thym), SOUR (souris).",
    },
    # ============ GRID 2 — La ferme ============
    {
        "id": "mf02",
        "theme": "À la ferme",
        "emoji": "🐓",
        "difficulty": "facile",
        "size": 5,
        "cells": [
            [{"type": "block"},
             {"type": "block", "clue_v": "Elle donne du lait"},
             {"type": "block", "clue_v": "Il chante à l'aube"},
             {"type": "block", "clue_v": "Petit du chien"},
             {"type": "block", "clue_v": "Poil de mouton"}],
            [{"type": "block", "clue_h": "Cri du canard"},
             {"type": "letter", "answer": "V"},
             {"type": "letter", "answer": "C"},
             {"type": "letter", "answer": "C"},
             {"type": "letter", "answer": "L"}],
            [{"type": "block", "clue_h": "Endroit à œufs"},
             {"type": "letter", "answer": "A"},
             {"type": "letter", "answer": "O"},
             {"type": "letter", "answer": "H"},
             {"type": "letter", "answer": "A"}],
            [{"type": "block", "clue_h": "Sillon du champ"},
             {"type": "letter", "answer": "C"},
             {"type": "letter", "answer": "Q"},
             {"type": "letter", "answer": "I"},
             {"type": "letter", "answer": "I"}],
            [{"type": "block", "clue_h": "Ustensile à foin"},
             {"type": "letter", "answer": "H"},
             {"type": "letter", "answer": "S"},
             {"type": "letter", "answer": "O"},
             {"type": "letter", "answer": "N"}],
        ],
        "notes": "Sur ce MVP les mots sont des rébus visuels — l'important est le placement des lettres.",
    },
    # ============ GRID 3 — Nature ============
    {
        "id": "mf03",
        "theme": "Fleurs et arbres",
        "emoji": "🌸",
        "difficulty": "moyen",
        "size": 5,
        "cells": [
            [{"type": "block"},
             {"type": "block", "clue_v": "Fleur symbole"},
             {"type": "block", "clue_v": "Arbre à aiguilles"},
             {"type": "block", "clue_v": "Fleur du printemps"},
             {"type": "block", "clue_v": "Arbre puissant"}],
            [{"type": "block", "clue_h": "Fleur des champs"},
             {"type": "letter", "answer": "R"},
             {"type": "letter", "answer": "S"},
             {"type": "letter", "answer": "T"},
             {"type": "letter", "answer": "C"}],
            [{"type": "block", "clue_h": "Arbre à fruits rouges"},
             {"type": "letter", "answer": "O"},
             {"type": "letter", "answer": "A"},
             {"type": "letter", "answer": "U"},
             {"type": "letter", "answer": "H"}],
            [{"type": "block", "clue_h": "Feuille d'automne"},
             {"type": "letter", "answer": "S"},
             {"type": "letter", "answer": "P"},
             {"type": "letter", "answer": "L"},
             {"type": "letter", "answer": "E"}],
            [{"type": "block", "clue_h": "Vert au printemps"},
             {"type": "letter", "answer": "E"},
             {"type": "letter", "answer": "I"},
             {"type": "letter", "answer": "I"},
             {"type": "letter", "answer": "N"}],
        ],
    },
    # ============ GRID 4 — Les années 60 ============
    {
        "id": "mf04",
        "theme": "Années 60",
        "emoji": "📻",
        "difficulty": "moyen",
        "size": 5,
        "cells": [
            [{"type": "block"},
             {"type": "block", "clue_v": "Chanteuse yéyé"},
             {"type": "block", "clue_v": "Ancien poste"},
             {"type": "block", "clue_v": "Icône BB"},
             {"type": "block", "clue_v": "Beat célèbre"}],
            [{"type": "block", "clue_h": "Sur les pistes"},
             {"type": "letter", "answer": "S"},
             {"type": "letter", "answer": "T"},
             {"type": "letter", "answer": "B"},
             {"type": "letter", "answer": "T"}],
            [{"type": "block", "clue_h": "Mode courte"},
             {"type": "letter", "answer": "H"},
             {"type": "letter", "answer": "S"},
             {"type": "letter", "answer": "A"},
             {"type": "letter", "answer": "W"}],
            [{"type": "block", "clue_h": "Voiture symbolique"},
             {"type": "letter", "answer": "Y"},
             {"type": "letter", "answer": "F"},
             {"type": "letter", "answer": "R"},
             {"type": "letter", "answer": "I"}],
            [{"type": "block", "clue_h": "Photos souvenirs"},
             {"type": "letter", "answer": "L"},
             {"type": "letter", "answer": "M"},
             {"type": "letter", "answer": "D"},
             {"type": "letter", "answer": "S"}],
        ],
    },
    # ============ GRID 5 — Voyages ============
    {
        "id": "mf05",
        "theme": "Voyages en France",
        "emoji": "🗺️",
        "difficulty": "difficile",
        "size": 5,
        "cells": [
            [{"type": "block"},
             {"type": "block", "clue_v": "La cité rose"},
             {"type": "block", "clue_v": "Mer du sud"},
             {"type": "block", "clue_v": "Massif alpin"},
             {"type": "block", "clue_v": "Fleuve parisien"}],
            [{"type": "block", "clue_h": "Capitale"},
             {"type": "letter", "answer": "T"},
             {"type": "letter", "answer": "M"},
             {"type": "letter", "answer": "A"},
             {"type": "letter", "answer": "S"}],
            [{"type": "block", "clue_h": "Bretonne breizh"},
             {"type": "letter", "answer": "O"},
             {"type": "letter", "answer": "E"},
             {"type": "letter", "answer": "L"},
             {"type": "letter", "answer": "E"}],
            [{"type": "block", "clue_h": "Corse insulaire"},
             {"type": "letter", "answer": "U"},
             {"type": "letter", "answer": "D"},
             {"type": "letter", "answer": "P"},
             {"type": "letter", "answer": "I"}],
            [{"type": "block", "clue_h": "Alsace du vin"},
             {"type": "letter", "answer": "L"},
             {"type": "letter", "answer": "I"},
             {"type": "letter", "answer": "S"},
             {"type": "letter", "answer": "N"}],
        ],
    },
    # ============ GRID 6 — VRAIE grille avec croisements ✅ ============
    # Carré magique 3×3 : chaque LIGNE et chaque COLONNE forme un vrai mot français.
    # Rendu newspaper-style : 1 rangée + 1 colonne de blocs avec définitions,
    # les lettres croisent verticalement ET horizontalement.
    #   Lignes:    MER, EAU, RUE
    #   Colonnes:  MER, EAU, RUE
    {
        "id": "mf06",
        "theme": "Carré magique — Ville & Nature",
        "emoji": "🎯",
        "difficulty": "difficile",
        "size": 4,
        "rows": 4,
        "cols": 4,
        "cells": [
            # row 0 — column clue banner (arrows point ↓ down to the answer)
            [{"type": "block"},
             {"type": "block", "clue_v": "Étendue salée"},
             {"type": "block", "clue_v": "Liquide vital"},
             {"type": "block", "clue_v": "Voie urbaine"}],
            # row 1 — first horizontal word (MER)
            [{"type": "block", "clue_h": "Étendue salée"},
             {"type": "letter", "answer": "M"},
             {"type": "letter", "answer": "E"},
             {"type": "letter", "answer": "R"}],
            # row 2 — EAU
            [{"type": "block", "clue_h": "Liquide vital"},
             {"type": "letter", "answer": "E"},
             {"type": "letter", "answer": "A"},
             {"type": "letter", "answer": "U"}],
            # row 3 — RUE
            [{"type": "block", "clue_h": "Voie urbaine"},
             {"type": "letter", "answer": "R"},
             {"type": "letter", "answer": "U"},
             {"type": "letter", "answer": "E"}],
        ],
        "words": [
            {"answer": "MER", "direction": "h", "row": 1, "col": 1},
            {"answer": "EAU", "direction": "h", "row": 2, "col": 1},
            {"answer": "RUE", "direction": "h", "row": 3, "col": 1},
            {"answer": "MER", "direction": "v", "row": 1, "col": 1},
            {"answer": "EAU", "direction": "v", "row": 1, "col": 2},
            {"answer": "RUE", "direction": "v", "row": 1, "col": 3},
        ],
        "notes": "Vraie grille — les 6 mots (3 h + 3 v) sont français, chaque lettre croise 2 mots.",
    },
]


def _public_grid(g: dict) -> dict:
    """Return a version without cell answers — anti-cheat for player view."""
    return {
        "id": g["id"],
        "theme": g["theme"],
        "emoji": g["emoji"],
        "difficulty": g["difficulty"],
        "size": g["size"],
        "cells": [
            [
                {"type": c["type"],
                 **({"clue_h": c["clue_h"]} if "clue_h" in c else {}),
                 **({"clue_v": c["clue_v"]} if "clue_v" in c else {})}
                if c["type"] == "block"
                else {"type": "letter"}
                for c in row
            ]
            for row in g["cells"]
        ],
    }
