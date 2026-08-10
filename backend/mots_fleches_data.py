"""Mots Fléchés — 6 vraies grilles 4×4 croisées (carrés magiques 3×3).

Model
-----
Grille 4×4 : la première ligne et la première colonne sont des "blocks" avec
définitions (▶ pour un mot horizontal, ▼ pour un mot vertical). La zone
jouable est un carré 3×3 où chaque ligne ET chaque colonne forme un vrai mot
français. Grâce à la symétrie (matrice symétrique), les indices "row" et
"col" sont identiques 3 par 3 — chaque définition est donc reprise 2 fois
(une fois horizontale, une fois verticale), ce qui est cohérent visuellement.

Cellules
--------
  {"type": "block", "clue_h": "..." , "clue_v": "..."}
     → case définition. Le joueur ne peut pas y écrire.
  {"type": "letter", "answer": "X"}
     → case à remplir. Le joueur tape une lettre A-Z.

Conventions clue
  clue_h → réponse à DROITE, commence à la case immédiatement à droite
  clue_v → réponse EN BAS, commence à la case immédiatement en dessous

Scoring : +1 pt par lettre correcte + 5 pts bonus si toute la grille est juste.
"""
from __future__ import annotations


def _magic_grid(gid: str, theme: str, emoji: str, difficulty: str,
                w1: str, w2: str, w3: str,
                clue1: str, clue2: str, clue3: str,
                notes: str | None = None) -> dict:
    """Construit une grille 4×4 à partir d'un carré magique 3×3 symétrique.

    Contrainte de validation (assert au load) : la matrice doit être symétrique,
    donc w1[i] == wi[0], w1[j] == wj[0], w2[k] == w3[1] etc. Autrement dit, si
    on écrit les 3 mots en lignes, les colonnes formeront les mêmes 3 mots.
    """
    assert len(w1) == len(w2) == len(w3) == 3, f"{gid}: mots doivent faire 3 lettres"
    matrix = [list(w1), list(w2), list(w3)]
    # Symétrie: matrix[i][j] == matrix[j][i]
    for i in range(3):
        for j in range(3):
            assert matrix[i][j] == matrix[j][i], f"{gid}: non symétrique en ({i},{j})"
    words = [w1, w2, w3]
    clues = [clue1, clue2, clue3]

    cells = [
        # row 0 — bandeau de définitions verticales (▼)
        [
            {"type": "block"},
            {"type": "block", "clue_v": clues[0]},
            {"type": "block", "clue_v": clues[1]},
            {"type": "block", "clue_v": clues[2]},
        ],
    ]
    for i in range(3):
        row = [{"type": "block", "clue_h": clues[i]}]
        for j in range(3):
            row.append({"type": "letter", "answer": matrix[i][j]})
        cells.append(row)

    grid = {
        "id": gid,
        "theme": theme,
        "emoji": emoji,
        "difficulty": difficulty,
        "size": 4,
        "rows": 4,
        "cols": 4,
        "cells": cells,
        "words": [
            *[{"answer": w, "direction": "h", "row": i + 1, "col": 1} for i, w in enumerate(words)],
            *[{"answer": w, "direction": "v", "row": 1, "col": j + 1} for j, w in enumerate(words)],
        ],
    }
    if notes:
        grid["notes"] = notes
    return grid


GRIDS: list[dict] = [
    # ============ mf01 — Petit-déjeuner ============
    # BOL / OSE / LES  (symétrique)
    _magic_grid(
        gid="mf01",
        theme="Petit-déjeuner",
        emoji="🥐",
        difficulty="facile",
        w1="BOL", w2="OSE", w3="LES",
        clue1="Récipient à café au lait",
        clue2="N'hésite pas (verbe, 3e p. sg.)",
        clue3="Article défini pluriel",
        notes="Carré magique : BOL/OSE/LES en lignes ET en colonnes.",
    ),

    # ============ mf02 — À la ferme ============
    # OIE / IRA / EAU  (symétrique)
    _magic_grid(
        gid="mf02",
        theme="À la ferme",
        emoji="🐓",
        difficulty="facile",
        w1="OIE", w2="IRA", w3="EAU",
        clue1="Volaille grise à long cou",
        clue2="Verbe aller au futur (3e p. sg.)",
        clue3="Liquide vital (H₂O)",
        notes="Carré magique : OIE/IRA/EAU en lignes ET en colonnes.",
    ),

    # ============ mf03 — Nature & vigne ============
    # ROC / OSE / CEP  (symétrique)
    _magic_grid(
        gid="mf03",
        theme="Nature & vigne",
        emoji="🍇",
        difficulty="moyen",
        w1="ROC", w2="OSE", w3="CEP",
        clue1="Grosse pierre solide",
        clue2="Prend le risque (verbe, 3e p. sg.)",
        clue3="Pied de vigne",
        notes="Carré magique : ROC/OSE/CEP en lignes ET en colonnes.",
    ),

    # ============ mf04 — Petits mots courants ============
    # ILE / LES / EST  (symétrique)
    _magic_grid(
        gid="mf04",
        theme="Petits mots courants",
        emoji="📚",
        difficulty="moyen",
        w1="ILE", w2="LES", w3="EST",
        clue1="Terre entourée d'eau",
        clue2="Article défini pluriel",
        clue3="Point cardinal du soleil levant",
        notes="Carré magique : ILE/LES/EST en lignes ET en colonnes.",
    ),

    # ============ mf05 — Objets du quotidien ============
    # SAC / AIL / CLE  (symétrique)
    _magic_grid(
        gid="mf05",
        theme="Objets du quotidien",
        emoji="🔑",
        difficulty="difficile",
        w1="SAC", w2="AIL", w3="CLE",
        clue1="Contient les courses",
        clue2="Bulbe qui parfume l'aïoli",
        clue3="Ouvre la porte",
        notes="Carré magique : SAC/AIL/CLE en lignes ET en colonnes.",
    ),

    # ============ mf06 — Ville & Nature (grille historique) ============
    # MER / EAU / RUE  (déjà en prod, on la garde)
    _magic_grid(
        gid="mf06",
        theme="Ville & Nature",
        emoji="🎯",
        difficulty="difficile",
        w1="MER", w2="EAU", w3="RUE",
        clue1="Étendue salée",
        clue2="Liquide vital",
        clue3="Voie urbaine",
        notes="Carré magique : MER/EAU/RUE en lignes ET en colonnes.",
    ),
]


def _public_grid(g: dict) -> dict:
    """Retourne la grille sans les réponses (anti-triche pour la vue joueur)."""
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
