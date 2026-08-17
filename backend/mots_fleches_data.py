"""Mots Fléchés — 6 vraies grilles 4×4 croisées (carrés magiques 3×3).

Model
-----
Grille 4×4 : la première ligne et la première colonne sont des "blocks" avec
définitions (▶ pour un mot horizontal, ▼ pour un mot vertical). La zone
jouable est un carré 3×3 où chaque ligne ET chaque colonne forme un vrai mot
français. Grâce à la symétrie (matrice symétrique), les indices "row" et
"col" produisent les MÊMES 3 mots.

Pour éviter la redondance visuelle (afficher deux fois exactement la même
définition), chaque mot dispose de DEUX définitions différentes : une pour
la direction horizontale (clue_h) et une pour la verticale (clue_v). Le mot
à trouver reste identique mais la formulation change — c'est plus riche
pédagogiquement.

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
                clues_h: tuple[str, str, str],
                clues_v: tuple[str, str, str],
                notes: str | None = None) -> dict:
    """Construit une grille 4×4 à partir d'un carré magique 3×3 symétrique.

    Contrainte de validation (assert au load) : la matrice doit être symétrique,
    donc si on écrit les 3 mots en lignes, les colonnes formeront les mêmes
    mots. Les deux tuples de clues (horizontal + vertical) doivent avoir 3
    éléments chacun.
    """
    assert len(w1) == len(w2) == len(w3) == 3, f"{gid}: mots doivent faire 3 lettres"
    assert len(clues_h) == 3 and len(clues_v) == 3, f"{gid}: clues_h/clues_v doivent avoir 3 items"
    matrix = [list(w1), list(w2), list(w3)]
    for i in range(3):
        for j in range(3):
            assert matrix[i][j] == matrix[j][i], f"{gid}: non symétrique en ({i},{j})"
    words = [w1, w2, w3]

    cells = [
        # row 0 — bandeau de définitions verticales (▼) — clues verticaux
        [
            {"type": "block"},
            {"type": "block", "clue_v": clues_v[0]},
            {"type": "block", "clue_v": clues_v[1]},
            {"type": "block", "clue_v": clues_v[2]},
        ],
    ]
    for i in range(3):
        # col 0 de chaque ligne — clue horizontal
        row = [{"type": "block", "clue_h": clues_h[i]}]
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
        clues_h=(
            "Récipient à café au lait",
            "N'hésite pas (verbe, 3e p. sg.)",
            "Article défini pluriel",
        ),
        clues_v=(
            "Il contient chocolat chaud ou soupe",
            "Prend un risque (verbe)",
            "Précède un nom au pluriel",
        ),
        notes="Carré magique : BOL/OSE/LES en lignes ET en colonnes (2 définitions par mot).",
    ),

    # ============ mf02 — À la ferme ============
    # OIE / IRA / EAU  (symétrique)
    _magic_grid(
        gid="mf02",
        theme="À la ferme",
        emoji="🐓",
        difficulty="facile",
        w1="OIE", w2="IRA", w3="EAU",
        clues_h=(
            "Volaille grise à long cou",
            "Verbe aller au futur (3e p. sg.)",
            "Liquide vital (H₂O)",
        ),
        clues_v=(
            "Elle fait \"couac\" en s'envolant",
            "Il partira bientôt (verbe aller)",
            "Sans elle, pas de vie",
        ),
        notes="Carré magique : OIE/IRA/EAU (2 définitions par mot).",
    ),

    # ============ mf03 — Nature & vigne ============
    # ROC / OSE / CEP  (symétrique)
    _magic_grid(
        gid="mf03",
        theme="Nature & vigne",
        emoji="🍇",
        difficulty="moyen",
        w1="ROC", w2="OSE", w3="CEP",
        clues_h=(
            "Grosse pierre solide",
            "Prend le risque (verbe, 3e p. sg.)",
            "Pied de vigne",
        ),
        clues_v=(
            "Bloc de granit ou de calcaire",
            "N'a pas froid aux yeux (verbe)",
            "Souche qui donne le raisin",
        ),
        notes="Carré magique : ROC/OSE/CEP (2 définitions par mot).",
    ),

    # ============ mf04 — Petits mots courants ============
    # ILE / LES / EST  (symétrique)
    _magic_grid(
        gid="mf04",
        theme="Petits mots courants",
        emoji="📚",
        difficulty="moyen",
        w1="ILE", w2="LES", w3="EST",
        clues_h=(
            "Terre entourée d'eau",
            "Article défini pluriel",
            "Point cardinal du soleil levant",
        ),
        clues_v=(
            "La Corse en est une",
            "Précède un nom au pluriel",
            "Verbe être (3e p. sg.)",
        ),
        notes="Carré magique : ILE/LES/EST (2 définitions par mot).",
    ),

    # ============ mf05 — Objets du quotidien ============
    # SAC / AIL / CLE  (symétrique)
    _magic_grid(
        gid="mf05",
        theme="Objets du quotidien",
        emoji="🔑",
        difficulty="difficile",
        w1="SAC", w2="AIL", w3="CLE",
        clues_h=(
            "Contient les courses",
            "Bulbe qui parfume l'aïoli",
            "Ouvre la porte",
        ),
        clues_v=(
            "On le porte à l'épaule",
            "Ingrédient de l'aïoli et du pesto",
            "Elle tourne dans la serrure",
        ),
        notes="Carré magique : SAC/AIL/CLE (2 définitions par mot).",
    ),

    # ============ mf06 — Ville & Nature (grille historique) ============
    # MER / EAU / RUE  (déjà en prod, on la garde)
    _magic_grid(
        gid="mf06",
        theme="Ville & Nature",
        emoji="🎯",
        difficulty="difficile",
        w1="MER", w2="EAU", w3="RUE",
        clues_h=(
            "Étendue salée",
            "Liquide vital",
            "Voie urbaine",
        ),
        clues_v=(
            "Elle borde les plages",
            "Elle coule du robinet",
            "On la traverse en ville",
        ),
        notes="Carré magique : MER/EAU/RUE (2 définitions par mot).",
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
