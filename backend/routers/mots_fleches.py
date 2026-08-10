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

from core import db, get_current_user, get_admin_user
from mots_fleches_data import GRIDS, _public_grid

router = APIRouter(prefix="/mots-fleches", tags=["mots-fleches"])

POINTS_PER_LETTER = 1
COMPLETION_BONUS = 5


class SubmitIn(BaseModel):
    # 2D array of strings — same shape as the grid. Non-letter cells send "".
    letters: list[list[str]] = Field(..., min_items=1, max_items=15)


async def _grid_by_id(grid_id: str) -> dict | None:
    """Static grids first, then Mistral-generated collection."""
    static = next((g for g in GRIDS if g["id"] == grid_id), None)
    if static:
        return static
    return await db.fleches_generated.find_one({"id": grid_id}, {"_id": 0})


def _rows_cols(g: dict) -> tuple[int, int]:
    rows = g.get("rows") or g.get("size") or len(g["cells"])
    cols = g.get("cols") or g.get("size") or (len(g["cells"][0]) if g["cells"] else 0)
    return int(rows), int(cols)


@router.get("/grids")
async def list_grids(user: dict = Depends(get_current_user)) -> list[dict]:
    user_id = str(user["_id"])
    progress = await db.fleches_progress.find(
        {"user_id": user_id}, {"_id": 0, "grid_id": 1, "completed_at": 1, "best_score": 1},
    ).to_list(200)
    pmap = {p["grid_id"]: p for p in progress}
    all_grids: list[dict] = list(GRIDS)
    generated = await db.fleches_generated.find({}, {"_id": 0}).sort("created_at", -1).to_list(60)
    all_grids.extend(generated)
    out = []
    for g in all_grids:
        p = pmap.get(g["id"], {})
        rows, cols = _rows_cols(g)
        out.append({
            "id": g["id"],
            "theme": g["theme"],
            "emoji": g["emoji"],
            "difficulty": g.get("difficulty", "moyen"),
            "size": g.get("size", max(rows, cols)),
            "rows": rows,
            "cols": cols,
            "source": g.get("source", "seed"),
            "completed": bool(p.get("completed_at")),
            "best_score": int(p.get("best_score") or 0),
        })
    return out


@router.get("/grids/{grid_id}")
async def get_grid(grid_id: str, user: dict = Depends(get_current_user)) -> dict:
    grid = await _grid_by_id(grid_id)
    if not grid:
        raise HTTPException(status_code=404, detail="Grille introuvable")
    payload = _public_grid(grid)
    rows, cols = _rows_cols(grid)
    payload["rows"] = rows
    payload["cols"] = cols
    return payload


@router.post("/grids/{grid_id}/check")
async def check_grid(grid_id: str, body: SubmitIn, user: dict = Depends(get_current_user)) -> dict:
    """Validation en direct sans effet de bord : renvoie les erreurs case par
    case sans toucher au score ni à la progression. Idéal pour un retour
    visuel pendant la saisie (mode "Vérifier au fur et à mesure").
    """
    grid = await _grid_by_id(grid_id)
    if not grid:
        raise HTTPException(status_code=404, detail="Grille introuvable")

    rows, cols = _rows_cols(grid)
    if len(body.letters) != rows or any(len(row) != cols for row in body.letters):
        raise HTTPException(status_code=400, detail="Dimensions incorrectes")

    correct_cells = 0
    total_cells = 0
    mistakes_mask: list[list[bool]] = [[False] * cols for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
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
    return {
        "correct_cells": correct_cells,
        "total_cells": total_cells,
        "accuracy_pct": accuracy_pct,
        "mistakes": mistakes_mask,
    }


@router.post("/grids/{grid_id}/submit")
async def submit_grid(grid_id: str, body: SubmitIn, user: dict = Depends(get_current_user)) -> dict:
    grid = await _grid_by_id(grid_id)
    if not grid:
        raise HTTPException(status_code=404, detail="Grille introuvable")

    rows, cols = _rows_cols(grid)
    if len(body.letters) != rows or any(len(row) != cols for row in body.letters):
        raise HTTPException(status_code=400, detail="Dimensions incorrectes")

    correct_cells = 0
    total_cells = 0
    mistakes_mask: list[list[bool]] = [[False] * cols for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
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


@router.post("/admin/generate")
async def admin_generate(_: dict = Depends(get_admin_user)) -> dict:
    """Manually trigger the Mistral fléchés generator. Returns the new grid id or null."""
    from fleches_mistral import generate_nightly_fleches
    gid = await generate_nightly_fleches()
    return {"grid_id": gid, "ok": bool(gid)}
