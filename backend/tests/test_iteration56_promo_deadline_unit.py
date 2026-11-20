"""Iteration 56 — règle serveur de fin de super promo (unitaire, sans HTTP)."""
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from fastapi import HTTPException

sys.path.insert(0, "/app/backend")
import subscription as sub  # noqa: E402

P = ZoneInfo("Europe/Paris")


def test_deadline_boundaries():
    assert sub.promo_active(datetime(2026, 12, 31, 23, 59, 58, tzinfo=P))
    assert not sub.promo_active(datetime(2027, 1, 1, 0, 0, 5, tzinfo=P))


def test_after_promo_blocks_noel_and_allows_normal(monkeypatch):
    monkeypatch.setattr(sub, "promo_active", lambda now=None: False)
    with pytest.raises(HTTPException) as e:
        sub.check_package_sellable("solo_yearly_noel")
    assert e.value.status_code == 400 and "terminée" in e.value.detail
    pkg = sub.check_package_sellable("solo_yearly")
    assert pkg["amount"] == 69
    assert sub.summary_text(pkg).startswith("Solo annuel : 69 € aujourd'hui pour 12 mois")
    assert sub.check_package_sellable("famille_v2_yearly")["amount"] == 99
    assert sub.check_package_sellable("solo_monthly")["amount"] == 6.9


def test_checkout_kwargs_promo(monkeypatch):
    captured = {}

    class FakeSession:
        @staticmethod
        def create(**kw):
            captured.update(kw)
            return {"id": "cs_x", "url": "https://x"}

    class FakeStripe:
        class checkout:
            Session = FakeSession

    monkeypatch.setattr(sub, "_stripe", lambda: FakeStripe)
    sub.create_checkout_session(sub.PACKAGES["solo_yearly_noel"], "solo_yearly_noel",
                                {"_id": "u1", "email": "t@example.com"}, "https://o")
    assert captured["mode"] == "subscription"
    items = captured["line_items"]
    assert items[0]["price_data"]["unit_amount"] == 6900 and items[0]["price_data"]["recurring"]["interval"] == "year"
    assert items[1]["price_data"]["unit_amount"] == 4900 and "recurring" not in items[1]["price_data"]
    days = (captured["subscription_data"]["trial_end"] - datetime.now().timestamp()) / 86400
    assert 364 <= days <= 367
