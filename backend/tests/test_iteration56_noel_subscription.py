"""Iteration 56 — Super promo de Noël : récap prix, checkout abonnement Stripe, résiliation."""
import os
import uuid

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")

SUMMARY_SOLO_NOEL = ("Super promo de Noël Solo : 49 € aujourd'hui pour 12 mois, à compter de votre première connexion. "
                     "Ensuite : renouvellement automatique à 69 €/an. Vous recevrez un e-mail de rappel 30 jours avant. "
                     "Résiliable à tout moment depuis Mon compte → Abonnement, en un clic.")


@pytest.fixture(scope="module")
def user_session():
    s = requests.Session()
    email = f"test_noel_{uuid.uuid4().hex[:8]}@example.com"
    r = s.post(f"{BASE_URL}/api/auth/register", json={"email": email, "password": "TestPass123!", "name": "TEST_Noel"})
    if r.status_code not in (200, 201):
        pytest.skip(f"register failed {r.status_code} {r.text}")
    tok = r.json().get("token") or r.json().get("access_token")
    if tok:
        s.headers.update({"Authorization": f"Bearer {tok}"})
    s.email = email
    yield s
    s.delete(f"{BASE_URL}/api/auth/account", json={"password": "TestPass123!", "confirm": "SUPPRIMER"})


# Récapitulatif public
class TestSummary:
    def test_solo_noel_summary_exact(self):
        r = requests.get(f"{BASE_URL}/api/pricing/summary/solo_yearly_noel")
        assert r.status_code == 200
        d = r.json()
        assert d["amount"] == 49 and d["renew_amount"] == 69 and d["promo"] is True and d["period"] == "yearly"
        assert d["summary"] == SUMMARY_SOLO_NOEL

    def test_famille_noel_summary(self):
        d = requests.get(f"{BASE_URL}/api/pricing/summary/famille_v2_yearly_noel").json()
        assert d["amount"] == 79 and d["renew_amount"] == 99
        assert d["summary"].startswith("Super promo de Noël Famille : 79 € aujourd'hui pour 12 mois")
        assert "renouvellement automatique à 99 €/an" in d["summary"]

    @pytest.mark.parametrize("pid,amt", [("solo_monthly", "6,90 €"), ("famille_v2_monthly", "9,90 €")])
    def test_monthly_summary(self, pid, amt):
        d = requests.get(f"{BASE_URL}/api/pricing/summary/{pid}").json()
        assert d["period"] == "monthly"
        assert amt in d["summary"] and "Sans engagement" in d["summary"]

    @pytest.mark.parametrize("pid", ["heritage_yearly", "gift_solo", "nope"])
    def test_blocked_packages(self, pid):
        r = requests.get(f"{BASE_URL}/api/pricing/summary/{pid}")
        assert r.status_code == 400


# Checkout
class TestCheckout:
    def test_requires_auth(self):
        r = requests.post(f"{BASE_URL}/api/checkout/session",
                          json={"package_id": "solo_yearly_noel", "origin_url": BASE_URL, "accept_terms": True})
        assert r.status_code in (401, 403)

    def test_without_terms(self, user_session):
        r = user_session.post(f"{BASE_URL}/api/checkout/session", json={"package_id": "solo_yearly_noel", "origin_url": BASE_URL})
        assert r.status_code == 400
        assert "accepter" in r.json()["detail"]

    @pytest.mark.parametrize("pid", ["solo_yearly_noel", "famille_v2_yearly_noel", "solo_yearly", "famille_v2_yearly",
                                     "solo_monthly", "famille_v2_monthly"])
    def test_with_terms_returns_url(self, user_session, pid):
        r = user_session.post(f"{BASE_URL}/api/checkout/session",
                              json={"package_id": pid, "origin_url": BASE_URL, "accept_terms": True})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["url"].startswith("https://") and d["session_id"].startswith("cs_")
        st = user_session.get(f"{BASE_URL}/api/checkout/status/{d['session_id']}")
        assert st.status_code == 200, st.text
        assert st.json()["payment_status"] in ("unpaid", "initiated")

    def test_cancel_without_subscription(self, user_session):
        r = user_session.post(f"{BASE_URL}/api/subscription/cancel")
        assert r.status_code == 400
