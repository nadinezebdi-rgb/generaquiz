# Iteration 50: LOT 2 "Offrir GénéraQuiz" — gift offers/promo, checkout, admin codes, PDF, redeem, family space, challenges gate
import os
import time
import uuid
from datetime import datetime, timezone, timedelta

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
ADMIN = {"email": "admin@generaquiz.fr", "password": "pF44gVBfLdushm3NZ6dN"}
DEFAULT_PROMO = {"enabled": False, "title": "Carte cadeau de Noël", "starts_on": "2026-12-01",
                 "ends_on": "2026-12-24", "famille_regular_price": 79, "famille_promo_price": 69}


def _session_with_token(tok):
    s = requests.Session()
    s.headers["Authorization"] = f"Bearer {tok}"
    return s


@pytest.fixture(scope="module")
def admin():
    r = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN)
    if r.status_code != 200:
        pytest.skip(f"admin login failed {r.status_code}")
    return _session_with_token(r.json()["access_token"])


def _register(tag):
    email = f"TEST_it50_{tag}_{uuid.uuid4().hex[:6]}@example.com"
    r = requests.post(f"{BASE_URL}/api/auth/register",
                      json={"email": email, "password": "Test1234!", "name": f"TEST {tag}"})
    assert r.status_code == 200, r.text
    s = _session_with_token(r.json()["access_token"])
    s.email = email
    return s


@pytest.fixture(scope="module")
def created_codes(admin):
    codes = []
    yield codes
    for c in codes:
        admin.patch(f"{BASE_URL}/api/admin/gifts/{c}/cancel")


def _mk_gift(admin, created_codes, offer="famille"):
    r = admin.post(f"{BASE_URL}/api/admin/gifts", json={"offer": offer, "recipient_name": "TEST_Mamie",
                                                         "buyer_name": "TEST_Paul", "message": "TEST_ bon jeu"})
    assert r.status_code == 200, r.text
    g = r.json()
    created_codes.append(g["code"])
    return g


# --- Offers + seasonal promo
class TestPromo:
    def test_offers_default(self):
        d = requests.get(f"{BASE_URL}/api/gifts/offers").json()
        prices = {o["id"]: o["price"] for o in d["offers"]}
        assert d["promo"]["active"] is False
        assert prices == {"famille": 79, "solo": 49}

    def test_promo_validation(self, admin):
        bad1 = {**DEFAULT_PROMO, "starts_on": "2026-12-30", "ends_on": "2026-12-01"}
        assert admin.put(f"{BASE_URL}/api/admin/site-settings/gift-promo", json=bad1).status_code == 400
        bad2 = {**DEFAULT_PROMO, "famille_promo_price": 79}
        assert admin.put(f"{BASE_URL}/api/admin/site-settings/gift-promo", json=bad2).status_code == 400

    def test_promo_active_then_reset(self, admin):
        today = datetime.now(timezone.utc).date()
        body = {**DEFAULT_PROMO, "enabled": True, "starts_on": (today - timedelta(days=2)).isoformat(),
                "ends_on": (today + timedelta(days=5)).isoformat()}
        try:
            r = admin.put(f"{BASE_URL}/api/admin/site-settings/gift-promo", json=body)
            assert r.status_code == 200 and r.json()["active_now"] is True
            d = requests.get(f"{BASE_URL}/api/gifts/offers").json()
            fam = next(o for o in d["offers"] if o["id"] == "famille")
            assert d["promo"]["active"] is True and fam["price"] == 69 and fam["regular_price"] == 79
        finally:
            r = admin.put(f"{BASE_URL}/api/admin/site-settings/gift-promo", json=DEFAULT_PROMO)
            assert r.status_code == 200 and r.json()["active_now"] is False

    def test_promo_non_admin_forbidden(self):
        u = _register("promo")
        assert u.get(f"{BASE_URL}/api/admin/site-settings/gift-promo").status_code == 403
        assert u.get(f"{BASE_URL}/api/admin/gifts").status_code == 403
        assert u.post(f"{BASE_URL}/api/admin/gifts", json={"offer": "solo"}).status_code == 403


# --- Checkout
class TestCheckout:
    def test_gift_checkout_ok_and_order_unpaid(self):
        r = requests.post(f"{BASE_URL}/api/gifts/checkout", json={
            "offer": "famille", "recipient_name": "TEST_Mamie", "buyer_name": "TEST_Paul",
            "buyer_email": "test_buyer@example.com", "message": "Joyeux", "origin_url": BASE_URL})
        assert r.status_code == 200, r.text
        d = r.json()
        assert "stripe.com" in d["url"] and d["session_id"]
        o = requests.get(f"{BASE_URL}/api/gifts/order/{d['session_id']}")
        assert o.status_code == 200, o.text
        assert o.json()["payment_status"] != "paid" and "gift" not in o.json()

    def test_gift_checkout_blank_names(self):
        r = requests.post(f"{BASE_URL}/api/gifts/checkout", json={
            "offer": "solo", "recipient_name": "  ", "buyer_name": "TEST_Paul",
            "buyer_email": "test_buyer@example.com", "origin_url": BASE_URL})
        assert r.status_code == 422

    def test_order_unknown(self):
        assert requests.get(f"{BASE_URL}/api/gifts/order/cs_test_unknown").status_code == 404

    def test_regular_checkout_rejects_gift(self):
        u = _register("chk")
        r = u.post(f"{BASE_URL}/api/checkout/session", json={"package_id": "gift_famille", "origin_url": BASE_URL})
        assert r.status_code == 400
        r2 = u.post(f"{BASE_URL}/api/checkout/session", json={"package_id": "solo_yearly", "origin_url": BASE_URL})
        assert r2.status_code == 200 and "url" in r2.json()


# --- Admin codes + PDF + lookup + cancel
class TestAdminCodes:
    def test_create_pdf_lookup_cancel(self, admin, created_codes):
        g = _mk_gift(admin, created_codes, "solo")
        code = g["code"]
        assert len(code) == 12 and code.startswith("GQ-") and code[7] == "-"
        k = g["pdf_url"].split("k=")[1]
        p = requests.get(f"{BASE_URL}/api/gifts/{code}/carte.pdf", params={"k": k})
        assert p.status_code == 200 and p.headers["content-type"].startswith("application/pdf")
        assert p.content[:4] == b"%PDF"
        assert requests.get(f"{BASE_URL}/api/gifts/{code}/carte.pdf", params={"k": "wrong"}).status_code == 404
        lk = requests.get(f"{BASE_URL}/api/gifts/code/{code.replace('-', '').lower()}")
        assert lk.status_code == 200 and lk.json()["code"] == code and lk.json()["offer"] == "solo"
        assert "pdf_key" not in lk.json()
        c = admin.patch(f"{BASE_URL}/api/admin/gifts/{code}/cancel")
        assert c.status_code == 200 and c.json()["status"] == "cancelled"
        assert admin.patch(f"{BASE_URL}/api/admin/gifts/{code}/cancel").status_code == 400
        assert requests.get(f"{BASE_URL}/api/gifts/code/{code}").status_code == 404

    def test_admin_list(self, admin):
        d = admin.get(f"{BASE_URL}/api/admin/gifts").json()
        assert isinstance(d["gifts"], list) and set(d["stats"]) >= {"sold", "revenue", "redeemed", "pending"}


# --- Redeem + family space + challenges gate
class TestRedeemFamily:
    def test_full_flow(self, admin, created_codes):
        owner = _register("owner")
        g = _mk_gift(admin, created_codes, "famille")
        # unauth redeem
        assert requests.post(f"{BASE_URL}/api/gifts/redeem", json={"code": g["code"]}).status_code in (401, 403)
        r = owner.post(f"{BASE_URL}/api/gifts/redeem", json={"code": g["code"].lower()})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["plan_tier"] == "famille_v2"
        exp = datetime.fromisoformat(d["plan_expires_at"])
        assert abs((exp - datetime.now(timezone.utc)).days - 365) <= 1
        assert owner.post(f"{BASE_URL}/api/gifts/redeem", json={"code": g["code"]}).status_code == 409
        assert owner.post(f"{BASE_URL}/api/gifts/redeem", json={"code": "GQ-ZZZZ-ZZZZ"}).status_code == 404
        me = owner.get(f"{BASE_URL}/api/auth/me").json()
        me = me.get("user", me)
        assert me["plan"] == "premium"
        # extend with solo code (tier stays famille_v2, expiry +365 from current)
        g2 = _mk_gift(admin, created_codes, "solo")
        r2 = owner.post(f"{BASE_URL}/api/gifts/redeem", json={"code": g2["code"]})
        assert r2.status_code == 200
        assert r2.json()["plan_tier"] == "famille_v2"
        exp2 = datetime.fromisoformat(r2.json()["plan_expires_at"])
        assert abs((exp2 - exp).days - 365) <= 1

        # family space
        sp = owner.get(f"{BASE_URL}/api/famille").json()
        assert sp["role"] == "owner" and sp["max_proches"] == 4
        assert owner.post(f"{BASE_URL}/api/famille/proches",
                          json={"name": "Me", "email": owner.email}).status_code == 400
        invites = []
        for i in range(4):
            r = owner.post(f"{BASE_URL}/api/famille/proches",
                           json={"name": f"TEST_P{i}", "email": f"test_it50_p{i}_{uuid.uuid4().hex[:4]}@example.com"})
            assert r.status_code == 200, r.text
            invites.append(r.json())
        assert owner.post(f"{BASE_URL}/api/famille/proches",
                          json={"name": "dup", "email": invites[0]["email"]}).status_code == 400
        assert owner.post(f"{BASE_URL}/api/famille/proches",
                          json={"name": "5th", "email": "test_it50_fifth@example.com"}).status_code == 400

        token = invites[0]["link"].rsplit("/", 1)[1]
        info = requests.get(f"{BASE_URL}/api/famille/invitation/{token}")
        assert info.status_code == 200 and info.json()["owner_name"] == "TEST owner"

        proche = _register("proche")
        outsider = _register("outsider")
        assert outsider.post(f"{BASE_URL}/api/famille/proches",
                             json={"name": "x", "email": "test_it50_x@example.com"}).status_code == 402
        cat = requests.get(f"{BASE_URL}/api/categories").json()[0]["id"]
        assert outsider.post(f"{BASE_URL}/api/challenges", json={"category_id": cat}).status_code == 402
        assert proche.post(f"{BASE_URL}/api/challenges", json={"category_id": cat}).status_code == 402

        acc = proche.post(f"{BASE_URL}/api/famille/invitation/{token}/accept")
        assert acc.status_code == 200, acc.text
        # someone else can't reuse it
        assert outsider.post(f"{BASE_URL}/api/famille/invitation/{token}/accept").status_code == 409
        psp = proche.get(f"{BASE_URL}/api/famille").json()
        assert psp["role"] == "proche" and psp["owner_name"] == "TEST owner"
        assert "leaderboard" in psp and "challenges" in psp
        assert len(psp["leaderboard"]) == 2
        assert all("email" not in p and "link" not in p for p in psp["proches"])
        ch = proche.post(f"{BASE_URL}/api/challenges", json={"category_id": cat})
        assert ch.status_code == 200, ch.text
        osp = owner.get(f"{BASE_URL}/api/famille").json()
        assert any(c["token"] == ch.json()["token"] for c in osp["challenges"])

        # owner removes proche -> access lost
        assert owner.delete(f"{BASE_URL}/api/famille/proches/{invites[0]['id']}").status_code == 200
        assert proche.get(f"{BASE_URL}/api/famille").json()["role"] == "none"
        assert proche.post(f"{BASE_URL}/api/challenges", json={"category_id": cat}).status_code == 402
        assert requests.get(f"{BASE_URL}/api/famille/invitation/{token}").status_code == 404

        # second proche joins then leaves
        tok2 = invites[1]["link"].rsplit("/", 1)[1]
        assert outsider.post(f"{BASE_URL}/api/famille/invitation/{tok2}/accept").status_code == 200
        assert outsider.get(f"{BASE_URL}/api/famille").json()["role"] == "proche"
        assert outsider.post(f"{BASE_URL}/api/famille/quitter").status_code == 200
        assert outsider.get(f"{BASE_URL}/api/famille").json()["role"] == "none"
        assert outsider.post(f"{BASE_URL}/api/famille/quitter").status_code == 400
        # slot freed after removal + leave -> can invite again
        r = owner.post(f"{BASE_URL}/api/famille/proches",
                       json={"name": "TEST_P5", "email": "test_it50_p5@example.com"})
        assert r.status_code == 200
