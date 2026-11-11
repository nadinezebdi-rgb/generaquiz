"""Témoignages de la page d'accueil, pilotés depuis l'admin (collection `testimonials`)."""
import uuid
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core import db, get_admin_user, record_audit

router = APIRouter(tags=["testimonials"])

PUBLIC = {"_id": 0, "id": 1, "text": 1, "first_name": 1, "age_role": 1, "location": 1, "profile": 1}


class TestimonialIn(BaseModel):
    text: str = Field(..., min_length=5, max_length=600)
    first_name: str = Field(..., min_length=1, max_length=40)
    age_role: str = Field("", max_length=60)
    location: str = Field("", max_length=80)
    profile: Literal["SENIOR", "FAMILLE", "EHPAD"]
    published: bool = False


@router.get("/testimonials")
async def public_testimonials() -> list[dict]:
    return await db.testimonials.find({"published": True}, PUBLIC).sort("created_at", -1).to_list(12)


@router.get("/admin/testimonials")
async def admin_list(admin: dict = Depends(get_admin_user)) -> list[dict]:
    return await db.testimonials.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)


@router.post("/admin/testimonials")
async def admin_create(body: TestimonialIn, admin: dict = Depends(get_admin_user)) -> dict:
    doc = {**body.model_dump(), "id": uuid.uuid4().hex, "created_at": datetime.now(timezone.utc).isoformat()}
    await db.testimonials.insert_one(doc)
    await record_audit(admin, action="testimonial.create", target_type="testimonial", target_id=doc["id"])
    doc.pop("_id", None)
    return doc


@router.put("/admin/testimonials/{tid}")
async def admin_update(tid: str, body: TestimonialIn, admin: dict = Depends(get_admin_user)) -> dict:
    r = await db.testimonials.update_one({"id": tid}, {"$set": body.model_dump()})
    if not r.matched_count:
        raise HTTPException(status_code=404, detail="Témoignage introuvable")
    await record_audit(admin, action="testimonial.update", target_type="testimonial", target_id=tid,
                       meta={"published": body.published})
    return await db.testimonials.find_one({"id": tid}, {"_id": 0})


@router.delete("/admin/testimonials/{tid}")
async def admin_delete(tid: str, admin: dict = Depends(get_admin_user)) -> dict:
    r = await db.testimonials.delete_one({"id": tid})
    if not r.deleted_count:
        raise HTTPException(status_code=404, detail="Témoignage introuvable")
    await record_audit(admin, action="testimonial.delete", target_type="testimonial", target_id=tid)
    return {"ok": True}
