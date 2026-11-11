# Prep data for iteration 51 UI tests: TEST_ users + admin gift codes (prints JSON)
import json
import os
import uuid

import requests
from pymongo import MongoClient

B = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
DB = MongoClient("mongodb://localhost:27017")["test_database"]
adm = requests.post(f"{B}/api/auth/login", json={"email": "admin@generaquiz.fr", "password": "pF44gVBfLdushm3NZ6dN"}).json()
H = {"Authorization": f"Bearer {adm['access_token']}"}


def reg(tag):
    e = f"test_it51ui_{tag}_{uuid.uuid4().hex[:6]}@example.com"
    r = requests.post(f"{B}/api/auth/register", json={"email": e, "password": "Test1234!", "name": f"TEST {tag}"})
    return {"email": e, "password": "Test1234!", "token": r.json()["access_token"]}


def code(offer):
    return requests.post(f"{B}/api/admin/gifts", headers=H, json={"offer": offer, "recipient_name": "TEST_Mamie",
                                                                  "buyer_name": "TEST_Paul"}).json()["code"]


out = {k: reg(k) for k in ["owner", "proche", "nofam", "act", "life", "acct", "solo"]}
for k in ["c_type", "c_life", "c_acct", "c_paste", "c_noprefix"]:
    out[k] = code("famille")
requests.post(f"{B}/api/gifts/redeem", headers={"Authorization": f"Bearer {out['owner']['token']}"}, json={"code": code("famille")})
requests.post(f"{B}/api/gifts/redeem", headers={"Authorization": f"Bearer {out['solo']['token']}"}, json={"code": code("solo")})
inv = requests.post(f"{B}/api/famille/proches", headers={"Authorization": f"Bearer {out['owner']['token']}"},
                    json={"name": "TEST_Proche", "email": out["proche"]["email"]}).json()
requests.post(f"{B}/api/famille/invitation/{inv['link'].rsplit('/', 1)[1]}/accept",
              headers={"Authorization": f"Bearer {out['proche']['token']}"})
DB.users.update_one({"email": out["life"]["email"]}, {"$set": {"plan": "premium", "plan_tier": "solo", "plan_expires_at": None}})
print(json.dumps(out))
