"""Cartes cadeau Famille : 2 proches pour les nouvelles cartes, 3 pour celles vendues avant."""
import io

import pytest

pypdf = pytest.importorskip("pypdf")
from gift_card_pdf import build_gift_pdf  # noqa: E402


@pytest.mark.parametrize("fields,expected", [({}, "3 proches"), ({"max_proches": 2}, "2 proches")])
def test_famille_pdf_shows_card_capacity(fields, expected):
    gift = {"code": "ABCD-EFGH-1234", "offer": "famille", "theme": "classic", **fields}
    text = pypdf.PdfReader(io.BytesIO(build_gift_pdf(gift, "https://generaquiz.fr/activer"))).pages[0].extract_text()
    assert f"1 bénéficiaire + {expected}" in text
