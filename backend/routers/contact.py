"""Formulaire « Nous écrire » : message transmis à l'adresse de contact + accusé de réception."""
import asyncio
from datetime import datetime, timezone
from html import escape

import resend
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

from core import db, logger, CONTACT_EMAIL, RESEND_API_KEY, SENDER_EMAIL, rate_limit

router = APIRouter(prefix="/contact", tags=["contact"])

SUBJECTS = {"question": "Une question", "abonnement": "Mon abonnement", "cadeau": "Un cadeau",
            "ehpad": "Établissement / EHPAD", "idee": "Une idée ou un souci", "autre": "Autre"}


class ContactIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    subject: str = "question"
    message: str = Field(min_length=10, max_length=4000)
    website: str = ""  # piège à robots, doit rester vide


def _send(params: dict) -> None:
    resend.Emails.send({"from": SENDER_EMAIL, **params})


@router.post("", dependencies=[Depends(rate_limit("contact", 5, 3600))])
async def send_contact(body: ContactIn) -> dict:
    if body.website:
        return {"ok": True}
    if not RESEND_API_KEY:
        raise HTTPException(status_code=503, detail="L'envoi de messages est momentanément indisponible.")
    subject = SUBJECTS.get(body.subject, SUBJECTS["autre"])
    name, msg = escape(body.name.strip()), escape(body.message.strip()).replace("\n", "<br>")
    await db.contact_messages.insert_one({"name": body.name.strip(), "email": body.email, "subject": body.subject,
                                          "message": body.message.strip(),
                                          "created_at": datetime.now(timezone.utc).isoformat()})
    try:
        await asyncio.to_thread(_send, {
            "to": [CONTACT_EMAIL], "reply_to": body.email, "subject": f"[Contact] {subject} — {body.name.strip()}",
            "html": f"<p><strong>{name}</strong> ({escape(body.email)}) — {escape(subject)}</p><p>{msg}</p>"
                    f"<p style='color:#64748B;font-size:12px'>Répondez directement à cet e-mail pour lui écrire.</p>"})
    except Exception as e:
        logger.error(f"[contact] envoi impossible : {e}")
        raise HTTPException(status_code=502, detail="Votre message n'a pas pu être envoyé. Réessayez dans un instant.")
    try:
        await asyncio.to_thread(_send, {
            "to": [body.email], "subject": "Nous avons bien reçu votre message",
            "html": f"<div style='font-family:Arial,sans-serif;color:#1A2530;max-width:560px'>"
                    f"<p>Bonjour {name},</p><p>Nous avons bien reçu votre message et vous répondrons très vite.</p>"
                    f"<p style='background:#F4F1DE;border-radius:12px;padding:12px 16px'>{msg}</p>"
                    f"<p>À bientôt,<br>L'équipe GénéraQuiz</p></div>"})
    except Exception as e:
        logger.warning(f"[contact] accusé de réception non envoyé à {body.email} : {e}")
    return {"ok": True}
