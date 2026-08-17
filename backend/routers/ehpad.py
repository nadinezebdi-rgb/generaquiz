"""EHPAD — espace B2B animateur.

Un animateur d'EHPAD peut :
  - créer/gérer les "résidents" (fiches sans e-mail, pseudonyme + prénom + âge)
  - lancer une "séance collective" (quiz du jour ou prompt Livre) devant un groupe
  - noter les résultats / souvenirs récoltés (une entrée par résident dans la séance)
  - relire les séances passées + exporter en PDF (backlog V2)

Rôle utilisateur
----------------
On ajoute `role: "ehpad_animator"` sur le compte animateur (User existant + flag).
Un animateur voit `/app/ehpad/*` protégé.

Collections
-----------
ehpad_residents
  { id, animator_id, first_name, initial, age (optionnel), notes, active, created_at }

ehpad_sessions
  { id, animator_id, kind: "quiz" | "prompt", ref_id (category slug OU prompt_id),
    ref_title, resident_ids: [], notes, created_at }

ehpad_session_responses
  { id, session_id, resident_id, score (si quiz, 0-5), memory_text (si prompt), created_at }
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core import db, get_current_user


router = APIRouter(prefix="/ehpad", tags=["ehpad"])


def _require_animator(user: dict) -> None:
    role = user.get("role")
    if role not in ("ehpad_animator", "admin"):
        raise HTTPException(status_code=403, detail="Réservé aux comptes animateurs EHPAD")


# =============================================================================
# Admin — promotion d'un user existant en animateur EHPAD
# =============================================================================

class PromoteIn(BaseModel):
    email: str = Field(..., max_length=200)


@router.post("/admin/promote")
async def promote_to_animator(body: PromoteIn, user: dict = Depends(get_current_user)) -> dict:
    """Réservé aux admins : passe un compte en `role: ehpad_animator`.

    Un vrai flux commercial B2B devrait passer par Stripe (checkout dédié) puis
    créer le compte animateur avec ce rôle automatiquement. En attendant, on
    reste manuel : l'utilisateur B2B s'inscrit normalement puis un admin le
    promeut via cet endpoint (ou via l'admin analytics dashboard, backlog).
    """
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Réservé aux admins")
    target = await db.users.find_one({"email": body.email.strip().lower()})
    if not target:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    await db.users.update_one({"_id": target["_id"]}, {"$set": {"role": "ehpad_animator"}})
    return {"ok": True, "email": target["email"]}


# =============================================================================
# Résidents
# =============================================================================

class ResidentCreate(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=40)
    initial: str = Field("", max_length=3)     # ex "D." pour respecter la vie privée
    age: int | None = Field(None, ge=40, le=120)
    notes: str = Field("", max_length=400)


class ResidentUpdate(BaseModel):
    first_name: str | None = Field(None, min_length=1, max_length=40)
    initial: str | None = Field(None, max_length=3)
    age: int | None = Field(None, ge=40, le=120)
    notes: str | None = Field(None, max_length=400)
    active: bool | None = None


@router.get("/residents")
async def list_residents(user: dict = Depends(get_current_user)) -> list[dict]:
    _require_animator(user)
    docs = await db.ehpad_residents.find(
        {"animator_id": str(user["_id"]), "active": {"$ne": False}},
        {"_id": 0},
    ).sort("first_name", 1).to_list(200)
    return docs


@router.post("/residents")
async def create_resident(body: ResidentCreate, user: dict = Depends(get_current_user)) -> dict:
    _require_animator(user)
    doc = {
        "id": str(uuid.uuid4()),
        "animator_id": str(user["_id"]),
        "first_name": body.first_name.strip(),
        "initial": body.initial.strip(),
        "age": body.age,
        "notes": body.notes.strip(),
        "active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.ehpad_residents.insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.patch("/residents/{rid}")
async def update_resident(rid: str, body: ResidentUpdate, user: dict = Depends(get_current_user)) -> dict:
    _require_animator(user)
    updates = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}
    if not updates:
        return {"ok": True}
    r = await db.ehpad_residents.update_one(
        {"id": rid, "animator_id": str(user["_id"])},
        {"$set": updates},
    )
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Résident introuvable")
    return {"ok": True}


@router.delete("/residents/{rid}")
async def deactivate_resident(rid: str, user: dict = Depends(get_current_user)) -> dict:
    _require_animator(user)
    await db.ehpad_residents.update_one(
        {"id": rid, "animator_id": str(user["_id"])},
        {"$set": {"active": False}},
    )
    return {"ok": True}


# =============================================================================
# Séances collectives
# =============================================================================

class SessionCreate(BaseModel):
    kind: str = Field(..., pattern="^(quiz|prompt)$")
    ref_id: str = Field(..., min_length=1, max_length=80)
    ref_title: str = Field(..., min_length=1, max_length=200)
    resident_ids: list[str] = Field(..., min_length=1, max_length=30)
    notes: str = Field("", max_length=1000)


class SessionResponseIn(BaseModel):
    resident_id: str
    score: int | None = Field(None, ge=0, le=5)
    memory_text: str = Field("", max_length=2000)


@router.get("/sessions")
async def list_sessions(user: dict = Depends(get_current_user)) -> list[dict]:
    _require_animator(user)
    docs = await db.ehpad_sessions.find(
        {"animator_id": str(user["_id"])}, {"_id": 0},
    ).sort("created_at", -1).limit(100).to_list(100)
    # Enrichit avec le nombre de réponses par séance
    for d in docs:
        d["n_responses"] = await db.ehpad_session_responses.count_documents({"session_id": d["id"]})
    return docs


@router.post("/sessions")
async def create_session(body: SessionCreate, user: dict = Depends(get_current_user)) -> dict:
    _require_animator(user)
    # Sécurité : les résidents doivent appartenir à cet animateur
    valid = await db.ehpad_residents.count_documents({
        "id": {"$in": body.resident_ids},
        "animator_id": str(user["_id"]),
    })
    if valid != len(body.resident_ids):
        raise HTTPException(status_code=400, detail="Résident invalide dans la sélection")
    doc = {
        "id": str(uuid.uuid4()),
        "animator_id": str(user["_id"]),
        "kind": body.kind,
        "ref_id": body.ref_id,
        "ref_title": body.ref_title,
        "resident_ids": body.resident_ids,
        "notes": body.notes.strip(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.ehpad_sessions.insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.get("/sessions/{sid}")
async def get_session(sid: str, user: dict = Depends(get_current_user)) -> dict:
    _require_animator(user)
    s = await db.ehpad_sessions.find_one({"id": sid, "animator_id": str(user["_id"])}, {"_id": 0})
    if not s:
        raise HTTPException(status_code=404, detail="Séance introuvable")
    responses = await db.ehpad_session_responses.find({"session_id": sid}, {"_id": 0}).to_list(50)
    # attache résident details
    residents = await db.ehpad_residents.find(
        {"id": {"$in": s["resident_ids"]}, "animator_id": str(user["_id"])},
        {"_id": 0},
    ).to_list(50)
    s["residents"] = residents
    s["responses"] = responses
    return s


@router.post("/sessions/{sid}/responses")
async def add_response(sid: str, body: SessionResponseIn, user: dict = Depends(get_current_user)) -> dict:
    _require_animator(user)
    s = await db.ehpad_sessions.find_one({"id": sid, "animator_id": str(user["_id"])})
    if not s:
        raise HTTPException(status_code=404, detail="Séance introuvable")
    if body.resident_id not in s["resident_ids"]:
        raise HTTPException(status_code=400, detail="Résident non inscrit à cette séance")
    # upsert (une réponse par résident par séance)
    now = datetime.now(timezone.utc).isoformat()
    await db.ehpad_session_responses.update_one(
        {"session_id": sid, "resident_id": body.resident_id},
        {"$set": {
            "id": str(uuid.uuid4()),
            "session_id": sid,
            "resident_id": body.resident_id,
            "score": body.score,
            "memory_text": body.memory_text.strip(),
            "created_at": now,
            "updated_at": now,
        }},
        upsert=True,
    )
    return {"ok": True}


# =============================================================================
# Stats agrégées pour la homepage animateur
# =============================================================================

@router.get("/dashboard")
async def dashboard(user: dict = Depends(get_current_user)) -> dict:
    _require_animator(user)
    animator_id = str(user["_id"])
    n_residents = await db.ehpad_residents.count_documents({"animator_id": animator_id, "active": {"$ne": False}})
    n_sessions = await db.ehpad_sessions.count_documents({"animator_id": animator_id})
    n_responses = await db.ehpad_session_responses.count_documents({
        "session_id": {"$in": [d["id"] async for d in db.ehpad_sessions.find({"animator_id": animator_id}, {"id": 1})]},
    })
    recent = await db.ehpad_sessions.find(
        {"animator_id": animator_id}, {"_id": 0},
    ).sort("created_at", -1).limit(3).to_list(3)
    return {
        "n_residents": n_residents,
        "n_sessions": n_sessions,
        "n_responses": n_responses,
        "recent_sessions": recent,
    }
