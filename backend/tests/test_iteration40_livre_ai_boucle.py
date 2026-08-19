"""Backend tests for iteration 40: Landing/HowItWorks + 12 chapters + Livre progression + Rewrite AI + Quiz->Livre bridge."""
import os
import re
import time
import requests
import pytest
from dotenv import dotenv_values

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL")
            or dotenv_values("/app/frontend/.env").get("REACT_APP_BACKEND_URL")
            or "").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL not configured"
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@generaquiz.fr"
ADMIN_PASSWORD = "Admin2026!"

EXPECTED_ORDER = [
    "origines", "enfance", "ecole", "adolescence", "rencontres", "couple",
    "enfants", "metier", "voyages", "passions", "evenements", "transmission",
]


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{API}/auth/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    data = r.json()
    tok = data.get("access_token") or data.get("token")
    assert tok, f"no token in login response: {data}"
    return tok


@pytest.fixture(scope="module")
def headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ============== Phase 2 — 12 chapitres ==============
def test_chapters_returns_12_in_order(headers):
    r = requests.get(f"{API}/livre/chapters", headers=headers, timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    assert isinstance(data, list)
    assert len(data) == 12, f"expected 12 chapters, got {len(data)}"
    ids = [c["id"] for c in data]
    assert ids == EXPECTED_ORDER, f"order mismatch: {ids}"


def test_no_legacy_chapter_ids(headers):
    """Assert no chapter returned uses legacy IDs (famille / epreuves)."""
    r = requests.get(f"{API}/livre/chapters", headers=headers, timeout=15)
    ids = {c["id"] for c in r.json()}
    assert "famille" not in ids
    assert "epreuves" not in ids


# ============== Phase 2 — progression ==============
def test_progression_endpoint(headers):
    r = requests.get(f"{API}/livre/progression", headers=headers, timeout=15)
    assert r.status_code == 200, r.text
    d = r.json()
    for k in ["total_entries", "total_photos", "chapters_started",
              "chapters_completed", "chapters_total", "estimated_pages",
              "progression_percent"]:
        assert k in d, f"missing key {k}: {d}"
    assert d["chapters_total"] == 12


# ============== Helper : create a base entry for AI rewrite ==============
@pytest.fixture(scope="module")
def sample_entry(headers):
    """Create a text entry we can safely rewrite in the AI tests."""
    body = {
        "chapter_id": "enfance",
        "prompt_id": "enfance_p1",
        "mode": "text",
        "text": "Marie était ma voisine d'enfance. On jouait ensemble dans la cour de la maison bleue.",
        "visibility": "private",
    }
    r = requests.post(f"{API}/livre/entries", headers=headers, json=body, timeout=15)
    assert r.status_code == 200, r.text
    entry = r.json()["entry"]
    yield entry
    # No cleanup endpoint — leave entry (marked TEST-ish via text content)


# ============== Phase 3 — Rewrite AI ==============
def test_rewrite_too_short(headers, sample_entry):
    body = {"entry_id": sample_entry["id"], "tone": "natural"}
    # create a super short entry to test 400
    short = requests.post(f"{API}/livre/entries", headers=headers, json={
        "chapter_id": "enfance", "prompt_id": "enfance_p1", "mode": "text",
        "text": "trop court", "visibility": "private",
    }, timeout=15)
    assert short.status_code == 200
    sid = short.json()["entry"]["id"]
    r = requests.post(f"{API}/livre/entries/{sid}/rewrite", headers=headers,
                      json={"entry_id": sid, "tone": "natural"}, timeout=30)
    assert r.status_code == 400, r.text


def test_rewrite_ai_no_hallucination(headers, sample_entry):
    """Guardrail: rewriting a text mentioning only 'Marie' must NOT add other first names."""
    r = requests.post(f"{API}/livre/entries/{sample_entry['id']}/rewrite",
                      headers=headers,
                      json={"entry_id": sample_entry["id"], "tone": "natural"},
                      timeout=90)
    assert r.status_code == 200, f"rewrite failed: {r.status_code} {r.text}"
    data = r.json()
    assert "rewritten" in data and data["rewritten"], data
    rewritten = data["rewritten"]
    # Guardrail check: no other first name (very loose heuristic: known common French names)
    forbidden = ["Pierre", "Jean", "Paul", "Louis", "Sophie", "Julie", "Anne", "Claire", "Lucie", "Camille"]
    lower = rewritten
    leaked = [n for n in forbidden if re.search(rf"\b{n}\b", lower)]
    assert not leaked, f"Rewrite hallucinated names: {leaked} in: {rewritten}"


def test_accept_rewrite_persists_and_archives_original(headers, sample_entry):
    entry_id = sample_entry["id"]
    # Fetch current text
    lst = requests.get(f"{API}/livre/entries", headers=headers, timeout=15).json()
    original_text = None
    for c in lst["chapters"]:
        for e in c["entries"]:
            if e["id"] == entry_id:
                original_text = e["text"]
    assert original_text
    new_text = original_text + " (édité manuellement)"
    r = requests.post(f"{API}/livre/entries/{entry_id}/accept-rewrite",
                      headers=headers, json={"text": new_text}, timeout=15)
    assert r.status_code == 200, r.text

    # Verify persistence
    lst2 = requests.get(f"{API}/livre/entries", headers=headers, timeout=15).json()
    found = None
    for c in lst2["chapters"]:
        for e in c["entries"]:
            if e["id"] == entry_id:
                found = e
    assert found and found["text"] == new_text
    assert found.get("original_text") == original_text, "original_text not archived"


# ============== Phase 4 — Boucle Quiz→Livre ==============
@pytest.mark.parametrize("category_slug,expected_chapter", [
    ("chansons", "passions"),
    ("cinema", "passions"),
    ("voyages-france", "voyages"),
    ("histoire-france", "evenements"),
    ("annees-50-60", "adolescence"),
    ("objets-antan", "enfance"),
])
def test_from_quiz_creates_entry_in_correct_chapter(headers, category_slug, expected_chapter):
    body = {
        "quiz_question_id": f"testq-{category_slug}-{int(time.time())}",
        "category_slug": category_slug,
        "question_text": "Question test",
        "memory_text": f"Souvenir de test pour {category_slug}",
    }
    r = requests.post(f"{API}/livre/from-quiz", headers=headers, json=body, timeout=15)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["chapter_id"] == expected_chapter, f"{category_slug} → {d['chapter_id']} (expected {expected_chapter})"
    assert d["entry"]["source"] == "quiz"
    assert d["entry"]["quiz_category_slug"] == category_slug
