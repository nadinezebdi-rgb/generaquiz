"""Mots Mêlés — word search puzzle backend logic.

Data model in Mongo (collection `wordsearch_grids`):
{
  "_id": ObjectId,
  "id": str,                # slug e.g. "cuisine-francaise-01"
  "theme": str,             # "Cuisine française"
  "emoji": str,
  "size": int,              # 10, 12, 14
  "grid": list[list[str]],  # size × size uppercase letters
  "words": [
    {"word": "FROMAGE", "row": 3, "col": 2, "dr": 0, "dc": 1}
    # dr/dc: -1|0|1 direction vector (excludes 0,0)
  ],
  "difficulty": "facile" | "moyen" | "difficile",
  "created_at": iso,
  "source": "seed" | "mistral"
}

Player state in `wordsearch_progress`:
{ user_id, grid_id, found_words: [str], completed_at, awarded_points }
"""
from __future__ import annotations

import random
import string
import unicodedata
import uuid
from datetime import datetime, timezone

# Directions: 8-way (right, down, diag, and their opposites)
DIRECTIONS: list[tuple[int, int]] = [
    (0, 1),   # right
    (1, 0),   # down
    (1, 1),   # down-right
    (1, -1),  # down-left
    (0, -1),  # left  (reverse — makes it harder)
    (-1, 0),  # up
    (-1, 1),  # up-right
    (-1, -1), # up-left
]

FRENCH_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _normalize_word(w: str) -> str:
    """Uppercase, strip accents, keep only A-Z (grid-ready)."""
    s = w.strip().upper()
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return "".join(c for c in s if c in FRENCH_LETTERS)


def place_words(size: int, words: list[str], max_attempts: int = 400) -> tuple[list[list[str]], list[dict]] | None:
    """Try to place all `words` in a `size × size` grid.

    Returns (grid, placements) on success, None if any word cannot be placed.
    Each placement is {word, row, col, dr, dc}.
    """
    if any(len(w) > size for w in words):
        return None

    grid: list[list[str | None]] = [[None] * size for _ in range(size)]
    placements: list[dict] = []

    # Longest words first to maximise placement success
    for word in sorted(words, key=len, reverse=True):
        placed = False
        for _ in range(max_attempts):
            dr, dc = random.choice(DIRECTIONS)
            # bounds for starting cell so the whole word fits
            row_lo = 0 if dr >= 0 else len(word) - 1
            row_hi = size - len(word) if dr > 0 else size - 1
            if dr < 0:
                row_hi = size - 1
            col_lo = 0 if dc >= 0 else len(word) - 1
            col_hi = size - len(word) if dc > 0 else size - 1
            if dc < 0:
                col_hi = size - 1

            r0 = random.randint(row_lo, row_hi)
            c0 = random.randint(col_lo, col_hi)

            # verify each cell is free or already matches
            ok = True
            for i, letter in enumerate(word):
                r, c = r0 + dr * i, c0 + dc * i
                if r < 0 or c < 0 or r >= size or c >= size:
                    ok = False
                    break
                cell = grid[r][c]
                if cell is not None and cell != letter:
                    ok = False
                    break
            if not ok:
                continue

            # commit
            for i, letter in enumerate(word):
                r, c = r0 + dr * i, c0 + dc * i
                grid[r][c] = letter
            placements.append({"word": word, "row": r0, "col": c0, "dr": dr, "dc": dc})
            placed = True
            break

        if not placed:
            return None  # try again with fewer / different words

    # Fill remaining cells with random letters
    final_grid = [
        [cell if cell is not None else random.choice(FRENCH_LETTERS) for cell in row]
        for row in grid
    ]
    return final_grid, placements


def build_grid(theme: str, emoji: str, raw_words: list[str], size: int = 12,
               difficulty: str = "moyen", source: str = "seed") -> dict | None:
    """Normalize words, place them, return the full grid doc (unsaved).

    Retries placement up to 5 times before giving up.
    """
    words = [w for w in {_normalize_word(w) for w in raw_words} if len(w) >= 3]
    if not words:
        return None
    # Cap words: too many crowd the grid
    words = sorted(words, key=len, reverse=True)[:12]

    for _ in range(5):
        result = place_words(size, words)
        if result:
            grid, placements = result
            return {
                "id": f"{_normalize_word(theme).lower()}-{uuid.uuid4().hex[:6]}",
                "theme": theme,
                "emoji": emoji,
                "size": size,
                "grid": grid,
                "words": placements,
                "difficulty": difficulty,
                "source": source,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
    return None


# ---------------------------------------------------------------------------
# Seed grids — 5 hand-authored themes, generated deterministically for testing.
# The nightly Mistral job will add more grids over time.
# ---------------------------------------------------------------------------
SEED_THEMES: list[dict] = [
    {"theme": "Cuisine française", "emoji": "🍽️", "words":
        ["POMME", "POIRE", "FROMAGE", "TARTE", "SUCRE", "PAIN", "SEL", "BEURRE",
         "OIGNON", "SAUCE", "SOUPE", "GATEAU"]},
    {"theme": "Chansons françaises", "emoji": "🎶", "words":
        ["PIAF", "AZNAVOUR", "BREL", "BARBARA", "TRENET", "MONTAND", "FERRE",
         "SARDOU", "MOUSTAKI", "BECAUD"]},
    {"theme": "Cinéma français", "emoji": "🎬", "words":
        ["BELMONDO", "DELON", "GABIN", "SIGNORET", "MONTAND", "DEPARDIEU",
         "MOREAU", "BARDOT", "TAUTOU", "AUTEUIL"]},
    {"theme": "La ferme", "emoji": "🐓", "words":
        ["POULE", "VACHE", "COCHON", "MOUTON", "CANARD", "CHEVAL", "CHIEN",
         "CHAT", "OIE", "LAPIN", "ANE", "COQ"]},
    {"theme": "Les fleurs", "emoji": "🌸", "words":
        ["ROSE", "TULIPE", "LILAS", "MUGUET", "VIOLETTE", "IRIS", "LYS",
         "PIVOINE", "ORCHIDEE", "JASMIN", "OEILLET", "DAHLIA"]},
]


def build_all_seed_grids() -> list[dict]:
    """Build one grid per seed theme. Deterministic random seed for reproducibility."""
    random.seed(42)
    grids = []
    for theme in SEED_THEMES:
        g = build_grid(theme["theme"], theme["emoji"], theme["words"], size=12, source="seed")
        if g:
            grids.append(g)
    return grids
