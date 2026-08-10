"""Mots Mêlés router — word search puzzle.

Endpoints
---------
GET  /mots-meles/grids                → list of {id, theme, emoji, size, difficulty,
                                                  words_count, found_count, completed}
GET  /mots-meles/grids/{grid_id}      → full grid with cells + list of TARGET words
                                        (but NOT their positions — anti-cheat)
POST /mots-meles/grids/{grid_id}/find → user claims a word is at (r0,c0)-(r1,c1);
                                        backend validates positions and awards points

Scoring: +2 pts per word found on the first correct claim. +10 bonus once ALL
words of a grid are found. Weekly league gets the same delta.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core import db, get_current_user
from wordsearch_data import _normalize_word

router = APIRouter(prefix="/mots-meles", tags=["mots-meles"])

POINTS_PER_WORD = 2
COMPLETION_BONUS = 10


class FindIn(BaseModel):
    row_start: int = Field(..., ge=0, lt=30)
    col_start: int = Field(..., ge=0, lt=30)
    row_end: int = Field(..., ge=0, lt=30)
    col_end: int = Field(..., ge=0, lt=30)


async def _user_progress(user_id: str, grid_id: str) -> dict:
    doc = await db.wordsearch_progress.find_one(
        {"user_id": user_id, "grid_id": grid_id}, {"_id": 0}
    )
    return doc or {"user_id": user_id, "grid_id": grid_id, "found_words": []}


@router.get("/grids")
async def list_grids(user: dict = Depends(get_current_user)) -> list[dict]:
    """All available grids with the user's per-grid progress."""
    user_id = str(user["_id"])
    grids = await db.wordsearch_grids.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    progress_docs = await db.wordsearch_progress.find(
        {"user_id": user_id}, {"_id": 0, "grid_id": 1, "found_words": 1, "completed_at": 1},
    ).to_list(200)
    progress_map = {p["grid_id"]: p for p in progress_docs}
    out = []
    for g in grids:
        p = progress_map.get(g["id"], {})
        words_count = len(g.get("words", []))
        found_count = len(p.get("found_words") or [])
        out.append({
            "id": g["id"],
            "theme": g["theme"],
            "emoji": g["emoji"],
            "size": g["size"],
            "difficulty": g.get("difficulty", "moyen"),
            "source": g.get("source", "seed"),
            "created_at": g.get("created_at"),
            "words_count": words_count,
            "found_count": found_count,
            "completed": found_count >= words_count and words_count > 0,
        })
    return out


@router.get("/grids/{grid_id}")
async def get_grid(grid_id: str, user: dict = Depends(get_current_user)) -> dict:
    """Full grid + word list. Word POSITIONS are NEVER sent — anti-cheat."""
    grid = await db.wordsearch_grids.find_one({"id": grid_id}, {"_id": 0})
    if not grid:
        raise HTTPException(status_code=404, detail="Grille introuvable")
    user_id = str(user["_id"])
    prog = await _user_progress(user_id, grid_id)
    found = set(prog.get("found_words") or [])
    return {
        "id": grid["id"],
        "theme": grid["theme"],
        "emoji": grid["emoji"],
        "size": grid["size"],
        "grid": grid["grid"],
        "difficulty": grid.get("difficulty", "moyen"),
        # Only send words + whether they've been found — never their coordinates
        "words": [
            {"word": w["word"], "found": w["word"] in found}
            for w in grid.get("words", [])
        ],
        "points_per_word": POINTS_PER_WORD,
        "completion_bonus": COMPLETION_BONUS,
    }


def _line_word(grid: list[list[str]], r0: int, c0: int, r1: int, c1: int) -> str | None:
    """Return the word formed by the straight line from (r0,c0) to (r1,c1).

    Line must be strictly horizontal, vertical or diagonal (45°). Returns None
    if the line is invalid or off-grid.
    """
    size = len(grid)
    dr = 0 if r0 == r1 else (1 if r1 > r0 else -1)
    dc = 0 if c0 == c1 else (1 if c1 > c0 else -1)
    if dr == 0 and dc == 0:
        return None
    steps_r = abs(r1 - r0)
    steps_c = abs(c1 - c0)
    if steps_r != 0 and steps_c != 0 and steps_r != steps_c:
        return None
    length = max(steps_r, steps_c) + 1
    letters = []
    for i in range(length):
        r, c = r0 + dr * i, c0 + dc * i
        if r < 0 or c < 0 or r >= size or c >= size:
            return None
        letters.append(grid[r][c])
    return "".join(letters)


@router.post("/grids/{grid_id}/find")
async def find_word(grid_id: str, body: FindIn, user: dict = Depends(get_current_user)) -> dict:
    """Validate a claim that a word sits on line (row_start,col_start) → (row_end,col_end).

    Idempotent: re-finding an already-found word yields no new points.
    """
    grid_doc = await db.wordsearch_grids.find_one({"id": grid_id}, {"_id": 0})
    if not grid_doc:
        raise HTTPException(status_code=404, detail="Grille introuvable")

    size = grid_doc["size"]
    grid = grid_doc["grid"]
    if any(v < 0 or v >= size for v in (body.row_start, body.col_start, body.row_end, body.col_end)):
        raise HTTPException(status_code=400, detail="Coordonnées hors grille")

    line = _line_word(grid, body.row_start, body.col_start, body.row_end, body.col_end)
    if not line:
        raise HTTPException(status_code=400, detail="Ligne invalide (doit être droite ou diagonale)")

    reversed_line = line[::-1]
    target_words = {w["word"] for w in grid_doc.get("words", [])}
    matched = None
    for candidate in (line, reversed_line):
        if candidate in target_words:
            matched = candidate
            break

    user_id = str(user["_id"])
    prog = await _user_progress(user_id, grid_id)
    already_found = set(prog.get("found_words") or [])

    if not matched:
        return {"correct": False, "word": None, "already_found": False, "points_gained": 0}

    if matched in already_found:
        return {"correct": True, "word": matched, "already_found": True, "points_gained": 0,
                "found_count": len(already_found), "total_words": len(target_words)}

    # New word! Persist + award.
    new_found = sorted(already_found | {matched})
    total_words = len(target_words)
    is_complete = len(new_found) >= total_words
    points = POINTS_PER_WORD + (COMPLETION_BONUS if is_complete else 0)
    now = datetime.now(timezone.utc).isoformat()

    await db.wordsearch_progress.update_one(
        {"user_id": user_id, "grid_id": grid_id},
        {
            "$set": {
                "found_words": new_found,
                "updated_at": now,
                **({"completed_at": now} if is_complete else {}),
            },
            "$setOnInsert": {"user_id": user_id, "grid_id": grid_id, "started_at": now},
        },
        upsert=True,
    )
    await db.users.update_one({"_id": user["_id"]}, {"$inc": {"xp_total": points}})
    try:
        from routers.gamification import _ensure_league_membership, _week_key
        await _ensure_league_membership(user_id)
        await db.league_scores.update_one(
            {"user_id": user_id, "week_key": _week_key()},
            {"$inc": {"xp": points}, "$setOnInsert": {
                "user_id": user_id, "week_key": _week_key(),
                "user_name": user.get("name") or user.get("email", "").split("@")[0],
            }},
            upsert=True,
        )
    except Exception:
        pass

    return {
        "correct": True,
        "word": matched,
        "already_found": False,
        "points_gained": points,
        "found_count": len(new_found),
        "total_words": total_words,
        "completed": is_complete,
    }
