"""Vérif manuelle A3/B : reprise, checkpoints, hiérarchie RETAG → backlog → IA.
Run: cd /app/backend && python tests/manual_qa_resume_check.py
"""
import asyncio
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).parent.parent / ".env")
from core import db  # noqa: E402
from qa_pipeline import JobCheckpoint  # noqa: E402
from routers import admin_qa  # noqa: E402

CAT = "zz-test-resume"


def iso(sec_ago):
    return (datetime.now(timezone.utc) - timedelta(seconds=sec_ago)).isoformat()


async def main():
    await db.categories.update_one({"id": CAT}, {"$set": {"id": CAT, "title": "Test", "description": "t"}}, upsert=True)
    await db.questions.delete_many({"category_id": CAT})
    await db.qa_jobs.delete_many({"category_id": CAT})
    ok = True

    # 1) reaper : heartbeat stale → queued + resume_count=1
    await db.qa_jobs.insert_one({"id": "j1", "category_id": CAT, "kind": "topup", "status": "running",
                                 "started_at": iso(600), "last_heartbeat_at": iso(400),
                                 "progress": {"done": 5}, "segment_start_done": 0, "segment_id": "s1"})
    await admin_qa._reap_dead_jobs()
    j = await db.qa_jobs.find_one({"id": "j1"})
    r = j["status"] == "queued" and j["resume_count"] == 1 and "segment_id" not in j
    print("1 reaper → reprise", "PASS" if r else f"FAIL {j}"); ok &= r

    # 2) plafond atteint → failed
    await db.qa_jobs.update_one({"id": "j1"}, {"$set": {"status": "running", "resume_count": 3,
                                                       "started_at": iso(600), "last_heartbeat_at": iso(400)}})
    await admin_qa._reap_dead_jobs()
    j = await db.qa_jobs.find_one({"id": "j1"})
    r = j["status"] == "failed" and "épuisée" in j["error"]
    print("2 plafond → failed", "PASS" if r else f"FAIL {j}"); ok &= r

    # 3) timeout sans progression → failed
    await db.qa_jobs.insert_one({"id": "j2", "category_id": CAT, "status": "running", "started_at": iso(10),
                                 "progress": {"done": 4}, "segment_start_done": 4, "resume_count": 0})
    res = await admin_qa._resume_or_fail("j2", "timeout", -2, require_progress=True)
    print("3 timeout sans progression → failed", "PASS" if res == "failed" else f"FAIL {res}"); ok &= res == "failed"

    # 4) job terminal intouchable
    await db.qa_jobs.insert_one({"id": "j3", "category_id": CAT, "status": "done", "started_at": iso(600)})
    res = await admin_qa._resume_or_fail("j3", "x", -1)
    print("4 done intouchable", "PASS" if res == "terminal" else f"FAIL {res}"); ok &= res == "terminal"

    # 5) checkpoint refusé si segment remplacé
    await db.qa_jobs.insert_one({"id": "j4", "category_id": CAT, "status": "running", "segment_id": "segA"})
    os.environ.update({"QA_JOB_ID": "j4", "QA_SEGMENT_ID": "segA"})
    cp = JobCheckpoint(db)
    a = await cp.save(done=1)
    await db.qa_jobs.update_one({"id": "j4"}, {"$set": {"segment_id": "segB"}})
    b = await cp.save(done=2)
    r = a and not b
    print("5 checkpoint superseded", "PASS" if r else f"FAIL {a} {b}"); ok &= r

    # 6) TOPUP hiérarchie : 140 vérifiées sans palier → RETAG remplit tout, 0 IA
    await db.questions.insert_many([{"id": f"zz{i}", "category_id": CAT, "question": f"Q{i}",
                                     "options": ["a", "b", "c", "d"], "correct_index": 0,
                                     "explanation": "", "quality": "verified"} for i in range(140)])
    await db.qa_jobs.insert_one({"id": "j5", "category_id": CAT, "kind": "topup", "status": "running",
                                 "segment_id": "segT", "started_at": iso(1)})
    env = {**os.environ, "ONLY_CATEGORY": CAT, "QA_JOB_ID": "j5", "QA_SEGMENT_ID": "segT"}
    t = time.time()
    p = subprocess.run([sys.executable, "topup_paliers.py"], cwd=str(Path(__file__).parent.parent),
                       env=env, capture_output=True, text=True, timeout=120)
    j = await db.qa_jobs.find_one({"id": "j5"})
    tagged = await db.questions.count_documents({"category_id": CAT, "difficulty": {"$gte": 1, "$lte": 7}})
    r = p.returncode == 0 and tagged == 140 and j["progress"]["done"] == 140 and j["progress"]["phase"] == "done" \
        and "génération IA" not in p.stdout
    print(f"6 RETAG d'abord, 0 IA ({time.time()-t:.1f}s)", "PASS" if r else f"FAIL rc={p.returncode} {j.get('progress')} {p.stdout[-500:]} {p.stderr[-500:]}")
    ok &= r

    # 7) segment remplacé → le script s'arrête (exit 3)
    await db.questions.update_many({"category_id": CAT}, {"$unset": {"difficulty": ""}})
    await db.qa_jobs.update_one({"id": "j5"}, {"$set": {"segment_id": "other"}})
    p = subprocess.run([sys.executable, "topup_paliers.py"], cwd=str(Path(__file__).parent.parent),
                       env=env, capture_output=True, text=True, timeout=120)
    print("7 orphelin s'arrête", "PASS" if p.returncode == 3 else f"FAIL rc={p.returncode}"); ok &= p.returncode == 3

    await db.questions.delete_many({"category_id": CAT})
    await db.qa_jobs.delete_many({"category_id": CAT})
    await db.categories.delete_one({"id": CAT})
    print("ALL PASS" if ok else "SOME FAIL")


asyncio.run(main())
