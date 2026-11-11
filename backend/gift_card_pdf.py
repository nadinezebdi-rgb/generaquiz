"""Carte cadeau GénéraQuiz imprimable (PDF A4 paysage, reportlab + qrcode)."""
import io
import random

import qrcode
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfgen import canvas

NAVY = HexColor("#142A47")
NAVY_2 = HexColor("#1E3A5F")
GOLD = HexColor("#F2CC8F")
GOLD_DARK = HexColor("#E5B96A")
CREAM = HexColor("#F4F1DE")
WHITE = HexColor("#FFFFFF")

OFFER_TEXT = {
    "famille": {
        "title": "Offre Famille",
        "tagline": "1 bénéficiaire + 4 proches pour partager une année de jeux",
        "lines": [
            "Le bénéficiaire : tout GénéraQuiz pendant 1 an, Livre de Vie et son PDF compris",
            "4 proches invités : quiz et défis du groupe familial, toute l'année",
            "Classement familial et résultats partagés pour tous",
        ],
    },
    "solo": {
        "title": "Offre Solo",
        "tagline": "Une année complète de jeux et de souvenirs",
        "lines": [
            "Quiz illimités dans toutes les catégories",
            "Progression, badges et séries",
            "Livre de Vie et son PDF à télécharger",
        ],
    },
}


def _qr_image(url: str) -> ImageReader:
    img = qrcode.make(url, box_size=10, border=1)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return ImageReader(buf)


def _stars(c: canvas.Canvas, w: float, h: float, seed: str) -> None:
    rnd = random.Random(seed)
    c.setFillColor(GOLD)
    for _ in range(70):
        x, y, r = rnd.uniform(20, w - 20), rnd.uniform(20, h - 20), rnd.uniform(0.6, 1.8)
        c.setFillAlpha(rnd.uniform(0.25, 0.7))
        c.circle(x, y, r, stroke=0, fill=1)
    c.setFillAlpha(1)


def build_gift_pdf(gift: dict, activate_url: str) -> bytes:
    w, h = landscape(A4)
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(w, h))
    c.setTitle(f"Carte cadeau GénéraQuiz — {gift['code']}")
    noel = gift.get("theme") == "noel"
    offer = OFFER_TEXT[gift["offer"]]

    c.setFillColor(NAVY)
    c.rect(0, 0, w, h, stroke=0, fill=1)
    if noel:
        _stars(c, w, h, gift["code"])
    c.setStrokeColor(GOLD)
    c.setLineWidth(3)
    c.roundRect(22, 22, w - 44, h - 44, 18, stroke=1, fill=0)
    c.setLineWidth(0.8)
    c.roundRect(32, 32, w - 64, h - 64, 14, stroke=1, fill=0)

    left = 70
    c.setFillColor(GOLD)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(left, h - 80, "GÉNÉRAQUIZ  ·  LE JEU QUI RAPPROCHE LES GÉNÉRATIONS")
    c.setFont("Times-Bold", 42)
    c.drawString(left, h - 135, "Carte cadeau de Noël" if noel else "Carte cadeau")
    c.setFillColor(WHITE)
    c.setFont("Times-Bold", 26)
    c.drawString(left, h - 172, offer["title"] + " — 1 an")
    c.setFillColor(CREAM)
    c.setFont("Helvetica", 13)
    c.drawString(left, h - 194, offer["tagline"])

    y = h - 240
    c.setFont("Helvetica-Bold", 15)
    c.setFillColor(GOLD)
    c.drawString(left, y, f"Pour {gift.get('recipient_name') or 'vous'}")
    if gift.get("buyer_name"):
        c.setFillColor(CREAM)
        c.setFont("Helvetica", 12)
        c.drawString(left, y - 20, f"De la part de {gift['buyer_name']}")
    y -= 44
    if gift.get("message"):
        c.setFont("Times-Italic", 14)
        c.setFillColor(WHITE)
        for line in simpleSplit(f"« {gift['message']} »", "Times-Italic", 14, 440)[:4]:
            c.drawString(left, y, line)
            y -= 18
        y -= 8

    c.setFont("Helvetica", 11)
    c.setFillColor(CREAM)
    for line in offer["lines"]:
        c.setFillColor(GOLD)
        c.circle(left + 4, y + 4, 2.6, stroke=0, fill=1)
        c.setFillColor(CREAM)
        c.drawString(left + 14, y, line)
        y -= 17

    # Code + QR (colonne droite)
    rx, box_w = w - 300, 230
    c.setFillColor(GOLD)
    c.roundRect(rx, h - 210, box_w, 74, 12, stroke=0, fill=1)
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(rx + box_w / 2, h - 156, "VOTRE CODE CADEAU")
    c.setFont("Courier-Bold", 24)
    c.drawCentredString(rx + box_w / 2, h - 192, gift["code"])

    qr_size = 150
    c.setFillColor(WHITE)
    c.roundRect(rx + (box_w - qr_size) / 2 - 8, h - 400, qr_size + 16, qr_size + 16, 10, stroke=0, fill=1)
    c.drawImage(_qr_image(activate_url), rx + (box_w - qr_size) / 2, h - 392, qr_size, qr_size)
    c.setFillColor(CREAM)
    c.setFont("Helvetica", 10)
    c.drawCentredString(rx + box_w / 2, h - 418, "Scannez pour activer le cadeau")

    c.setFillColor(GOLD)
    c.setFont("Times-Italic", 17)
    c.drawCentredString(rx + box_w / 2, h - 455, "Offrez des moments à partager")

    c.setFillColor(GOLD_DARK)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(left, 118, "Comment l'activer ?")
    c.setFillColor(CREAM)
    c.setFont("Helvetica", 11)
    site = activate_url.split("?")[0].replace("https://", "").replace("http://", "")
    c.drawString(left, 99, f"1. Rendez-vous sur {site}")
    c.drawString(left, 83, "2. Saisissez le code   3. Créez votre compte ou connectez-vous")
    c.setFont("Helvetica-Oblique", 10)
    c.drawString(left, 62, "L'année offerte commence le jour de l'activation. Code à usage unique.")

    c.showPage()
    c.save()
    return buf.getvalue()
