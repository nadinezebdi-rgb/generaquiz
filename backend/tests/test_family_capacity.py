import asyncio
import importlib
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def family(monkeypatch):
    monkeypatch.setenv("MONGO_URL", "mongodb://localhost:27017")
    monkeypatch.setenv("DB_NAME", "test_family_capacity")
    monkeypatch.setenv("JWT_SECRET", "test-only-family-capacity")
    return importlib.import_module("routers.family")


@pytest.mark.parametrize("user,tier,expected", [
    ({}, "famille_v2", 2),
    ({"plan_tier": "solo"}, "famille_v2", 2),
    ({"plan_tier": "famille_v2"}, "famille_v2", 4),
    ({"plan_tier": "famille"}, "famille_v2", 4),
    ({"plan_tier": "famille_v2", "family_max_proches": 3}, "famille_v2", 3),
    ({"plan_tier": "heritage"}, "heritage", 4),
])
def test_subscription_capacity(family, user, tier, expected):
    assert family.family_subscription_fields(user, tier) == {"family_max_proches": expected}
    assert family.family_subscription_fields(user, "solo") == {}


@pytest.mark.parametrize("user,expected", [({}, 3), ({"plan_tier": "solo"}, 3), ({"plan_tier": "famille_v2"}, 4),
                                           ({"plan_tier": "famille_v2", "family_max_proches": 2}, 3)])
def test_gift_card_capacity(family, user, expected):
    # Cartes cadeau Famille (vendues avec 3 proches).
    assert family.family_subscription_fields(user, "famille_v2", 3) == {"family_max_proches": expected}


def _cursor(rows):
    cursor = MagicMock()
    cursor.sort.return_value = cursor
    cursor.to_list = AsyncMock(side_effect=lambda limit: rows if limit is None else rows[:limit])
    return cursor


@pytest.mark.parametrize("capacity,count,allowed", [
    (3, 2, True),
    (3, 3, False),
    (None, 3, True),
    (None, 4, False),
])
def test_invitation_boundary(family, monkeypatch, capacity, count, allowed):
    owner = {"_id": "owner", "email": "owner@example.com", "name": "Owner"}
    if capacity is not None:
        owner["family_max_proches"] = capacity
    collection = SimpleNamespace(
        find=MagicMock(return_value=_cursor([{"email": f"p{i}@example.com"} for i in range(count)])),
        insert_one=AsyncMock(),
    )
    monkeypatch.setattr(family, "db", SimpleNamespace(family_proches=collection))
    monkeypatch.setattr(family, "is_family_owner", lambda user: True)
    monkeypatch.setattr(family, "_send_invite_email", AsyncMock())
    body = family.ProcheInvite(name="New", email="new@example.com")
    if allowed:
        result = asyncio.run(family.invite_proche(body, owner))
        assert result["email"] == "new@example.com"
        collection.insert_one.assert_awaited_once()
    else:
        with pytest.raises(family.HTTPException) as exc:
            asyncio.run(family.invite_proche(body, owner))
        assert exc.value.status_code == 400
        assert str(capacity or 4) in exc.value.detail
        collection.insert_one.assert_not_awaited()


def test_legacy_space_keeps_four_members_and_scores(family, monkeypatch):
    invites = [{"id": str(i), "name": f"Proche {i}", "email": f"p{i}@example.com",
                "status": "accepted", "user_id": f"user-{i}", "token": f"token-{i}"}
               for i in range(4)]
    monkeypatch.setattr(family, "db", SimpleNamespace(
        family_proches=SimpleNamespace(find=MagicMock(return_value=_cursor(invites))),
        challenges=SimpleNamespace(find=MagicMock(return_value=_cursor([]))),
    ))
    leaderboard = AsyncMock(return_value=[])
    monkeypatch.setattr(family, "_leaderboard", leaderboard)
    owner = {"_id": "owner", "name": "Owner"}
    result = asyncio.run(family._space(owner, owner, "owner"))
    assert result["max_proches"] == 4
    assert len(result["proches"]) == 4
    leaderboard.assert_awaited_once_with(["owner", "user-0", "user-1", "user-2", "user-3"])


@pytest.fixture
def checkout_modules(family, monkeypatch):
    # Aucun appel Stripe : seul l'effet des paiements sur les droits est testé.
    checkout = SimpleNamespace(
        StripeCheckout=MagicMock(), CheckoutSessionRequest=MagicMock(),
        CheckoutSessionResponse=MagicMock(), CheckoutStatusResponse=MagicMock(),
    )
    monkeypatch.setitem(sys.modules, "emergentintegrations.payments.stripe.checkout", checkout)
    payments = importlib.import_module("routers.payments")
    gifts = importlib.import_module("routers.gifts")
    monkeypatch.setattr(payments, "StripeCheckout", checkout.StripeCheckout)
    monkeypatch.setattr(gifts, "StripeCheckout", checkout.StripeCheckout, raising=False)
    return payments, gifts, checkout


@pytest.mark.parametrize("via_webhook", [False, True])
@pytest.mark.parametrize("legacy", [False, True])
def test_paid_subscription_records_capacity(checkout_modules, monkeypatch, via_webhook, legacy):
    from bson import ObjectId

    payments, _, checkout = checkout_modules
    subscriber = {"_id": ObjectId(), "plan_tier": "famille_v2" if legacy else "solo"}
    transaction = {"user_id": str(subscriber["_id"]), "package_id": "famille_v2_yearly",
                   "payment_status": "initiated", "session_id": "session-test"}
    users = SimpleNamespace(find_one=AsyncMock(return_value=subscriber), update_one=AsyncMock())
    monkeypatch.setattr(payments, "db", SimpleNamespace(
        users=users,
        payment_transactions=SimpleNamespace(
            find_one=AsyncMock(return_value=transaction), update_one=AsyncMock()),
    ))
    status = SimpleNamespace(payment_status="paid", status="complete", session_id="session-test",
                             amount_total=7900, currency="eur")
    checkout.StripeCheckout.return_value = SimpleNamespace(
        get_checkout_status=AsyncMock(return_value=status),
        handle_webhook=AsyncMock(return_value=status),
    )
    request = SimpleNamespace(base_url="http://localhost/", body=AsyncMock(return_value=b""),
                              headers={})
    if via_webhook:
        asyncio.run(payments.stripe_webhook(request))
    else:
        asyncio.run(payments.get_checkout_status("session-test", request, subscriber))
    fields = users.update_one.call_args.args[1]["$set"]
    assert fields["family_max_proches"] == (4 if legacy else 2)
    assert fields["plan_tier"] == "famille_v2"


@pytest.mark.parametrize("legacy", [False, True])
def test_gift_activation_records_capacity(checkout_modules, monkeypatch, legacy):
    from bson import ObjectId

    _, gifts, _ = checkout_modules
    user = {"_id": ObjectId(), "email": "owner@example.com",
            "plan_tier": "famille_v2" if legacy else "solo"}
    gift = {"_id": ObjectId(), "tier": "famille_v2", "offer": "famille"}
    users = SimpleNamespace(update_one=AsyncMock())
    monkeypatch.setattr(gifts, "db", SimpleNamespace(
        users=users, gift_codes=SimpleNamespace(
            find_one_and_update=AsyncMock(return_value=gift), update_one=AsyncMock()),
    ))
    monkeypatch.setattr(gifts, "is_premium_active", lambda user: False)
    asyncio.run(gifts.gift_redeem(gifts.GiftRedeem(code="GQ-ABCD-EFGH"), user))
    assert users.update_one.call_args.args[1]["$set"]["family_max_proches"] == (4 if legacy else 3)
