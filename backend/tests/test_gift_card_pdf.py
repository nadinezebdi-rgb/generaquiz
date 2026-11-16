from gift_card_pdf import build_gift_pdf


def test_christmas_gift_pdf_has_personal_details_and_no_demo_code():
    gift = {
        "code": "GQ-ABC23456-DEF23456-GHK23456-JKM23456",
        "offer": "famille",
        "theme": "noel",
        "recipient_name": "Mamie Jeanne",
        "buyer_name": "Léa et Tom",
        "message": "Joyeux Noël, on va jouer ensemble !",
    }

    pdf = build_gift_pdf(gift, "https://generaquiz.fr/activer?code=" + gift["code"])

    assert pdf.startswith(b"%PDF")
    assert b"CARTE CADEAU" in pdf
    assert b"generaquiz.fr" in pdf
    assert gift["code"].encode() in pdf
    assert b"000000" not in pdf