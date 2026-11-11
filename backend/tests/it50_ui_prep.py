# Prep data for iteration 50 UI tests: TEST_ users + admin gift codes
import json
import os
import uuid

import requests

B = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
adm = requests.post(f"{B}/api/auth/login", json={"email": "admin@generaquiz.fr", "password": "pF44gVBfLdushm3NZ6dN"}).json()
H = {"Authorization": f"Bearer {adm['access_token']}"}


def reg(tag):
    e = f"test_it50ui_{tag}_{uuid.uuid4().hex[:6]}@example.com"
    r = requests.post(f"{B}/api/auth/register", json={"email": e, "password": "Test1234!", "name": f"TEST {tag}"})
    return {"email": e, "password": "Test1234!", "token": r.json()["access_token"]}


def code(offer):
    return requests.post(f"{B}/api/admin/gifts", headers=H, json={"offer": offer, "recipient_name": "TEST_Mamie",
                                                                  "buyer_name": "TEST_Paul", "message": "TEST_ Bon jeu !"}).json()["code"]


out = {"activator": reg("act"), "owner": reg("owner"), "proche": reg("proche"), "nofam": reg("nofam"),
       "code_famille": code("famille"), "code_owner": code("famille"), "code_used": code("solo")}
# owner redeems a famille code; code_used redeemed by nofam? no -> by owner so nofam stays free
requests.post(f"{B}/api/gifts/redeem", headers={"Authorization": f"Bearer {out['owner']['token']}"},
              json={"code": out["code_owner"]})
requests.post(f"{B}/api/gifts/redeem", headers={"Authorization": f"Bearer {out['owner']['token']}"},
              json={"code": out["code_used"]})
inv = requests.post(f"{B}/api/famille/proches", headers={"Authorization": f"Bearer {out['owner']['token']}"},
                    json={"name": "TEST_Proche", "email": out["proche"]["email"]}).json()
out["invite_token"] = inv["link"].rsplit("/", 1)[1]
print(json.dumps(out))
