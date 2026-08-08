"""Mots Fléchés router — hand-authored 5x5 crossword MVP.

Endpoints
---------
GET  /mots-fleches/grids                → list of {id, theme, difficulty, emoji, completed}
GET  /mots-fleches/grids/{grid_id}      → grid with cells (letters hidden)
POST /mots-fleches/grids/{grid_id}/submit → validate a full submission and score
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core import db, get_current_user
from mots_fleches_data import GRIDS, _public_grid

router = APIRouter(prefix="/mots-fleches", tags=["mots-fleches"])

POINTS_PER_LETTER = 1
COMPLETION_BONUS = 5


class SubmitIn(BaseModel):
    # 2D array of strings — same shape as the grid. Non-letter cells send "".
    letters: list[list[str]] = Field(..., min_items=1, max_items=10)


def _grid_by_id(grid_id: str) -> dict | None:
    return next((g for g in GRIDS if g["id"] == grid_id), None)


@router.get("/grids")
async def list_grids(user: dict = Depends(get_current_user)) -> list[dict]:
    user_id = str(user["_id"])
    progress = await db.fleches_progress.find(
        {"user_id": user_id}, {"_id": 0, "grid_id": 1, "completed_at": 1, "best_score": 1},
    ).to_list(50)
    pmap = {p["grid_id"]: p for p in progress}
    out = []
    for g in GRIDS:
        p = pmap.get(g["id"], {})
        out.append({
            "id": g["id"],
            "theme": g["theme"],
            "emoji": g["emoji"],
            "difficulty": g["difficulty"],
            "size": g["size"],
            "completed": bool(p.get("completed_at")),
            "best_score": int(p.get("best_score") or 0),
        })
    return out


@router.get("/grids/{grid_id}")
async def get_grid(grid_id: str, user: dict = Depends(get_current_user)) -> dict:
    grid = _grid_by_id(grid_id)
    if not grid:
        raise HTTPException(status_code=404, detail="Grille introuvable")
    return _public_grid(grid)


@router.post("/grids/{grid_id}/submit")
async def submit_grid(grid_id: str, body: SubmitIn, user: dict = Depends(get_current_user)) -> dict:
    grid = _grid_by_id(grid_id)
    if not grid:
        raise HTTPException(status_code=404, detail="Grille introuvable")

    size = grid["size"]
    if len(body.letters) != size or any(len(row) != size for row in body.letters):
        raise HTTPException(status_code=400, detail="Dimensions incorrectes")

    correct_cells = 0
    total_cells = 0
    mistakes_mask: list[list[bool]] = [[False] * size for _ in range(size)]
    for r in range(size):
        for c in range(size):
            cell = grid["cells"][r][c]
            if cell["type"] != "letter":
                continue
            total_cells += 1
            expected = cell["answer"].upper()
            given = (body.letters[r][c] or "").strip().upper()[:1]
            if given == expected:
                correct_cells += 1
            elif given:
                mistakes_mask[r][c] = True
    accuracy_pct = int(round(correct_cells / total_cells * 100)) if total_cells else 0
    is_complete = correct_cells == total_cells and total_cells > 0
    points = correct_cells * POINTS_PER_LETTER + (COMPLETION_BONUS if is_complete else 0)

    user_id = str(user["_id"])
    now = datetime.now(timezone.utc).isoformat()

    # Only award once per (user, grid) — idempotent.
    prior = await db.fleches_progress.find_one({"user_id": user_id, "grid_id": grid_id})
    best_prior = int((prior or {}).get("best_score") or 0)
    if points > best_prior:
        await db.fleches_progress.update_one(
            {"user_id": user_id, "grid_id": grid_id},
            {
                "$set": {
                    "best_score": points,
                    "last_submitted_at": now,
                    **({"completed_at": now} if is_complete and not (prior or {}).get("completed_at") else {}),
                },
                "$setOnInsert": {"user_id": user_id, "grid_id": grid_id, "started_at": now},
            },
            upsert=True,
        )
        delta = points - best_prior
        await db.users.update_one({"_id": user["_id"]}, {"$inc": {"xp_total": delta}})
        try:
            from routers.gamification import _ensure_league_membership, _week_key
            await _ensure_league_membership(user_id)
            await db.league_scores.update_one(
                {"user_id": user_id, "week_key": _week_key()},
                {"$inc": {"xp": delta}, "$setOnInsert": {
                    "user_id": user_id, "week_key": _week_key(),
                    "user_name": user.get("name") or user.get("email", "").split("@")[0],
                }},
                upsert=True,
            )
        except Exception:
            pass
    return {
        "correct_cells": correct_cells,
        "total_cells": total_cells,
        "accuracy_pct": accuracy_pct,
        "completed": is_complete,
        "points_gained": max(points - best_prior, 0),
        "best_score": max(points, best_prior),
        "mistakes": mistakes_mask,
    }
