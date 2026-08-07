"""Admin analytics — business & product KPIs.

Read-only aggregates over existing collections. No new collection needed.
All endpoints require role='admin'.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends

from core import db, get_admin_user


router = APIRouter(prefix="/admin/analytics", tags=["admin-analytics"])


def _iso_day(offset: int = 0) -> str:
    """Return YYYY-MM-DD for today - offset days (UTC)."""
    return (datetime.now(timezone.utc) - timedelta(days=offset)).strftime("%Y-%m-%d")


def _iso_since(days: int) -> str:
    """Return ISO cutoff for created_at >= now - days."""
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


@router.get("/overview")
async def overview(_: dict = Depends(get_admin_user)) -> dict:
    """Headline KPIs surfaced at the top of the dashboard."""
    now = datetime.now(timezone.utc)
    since_30 = _iso_since(30)
    since_1 = _iso_since(1)

    total_users = await db.users.count_documents({})
    new_users_30d = await db.users.count_documents({"created_at": {"$gte": since_30}})
    new_users_24h = await db.users.count_documents({"created_at": {"$gte": since_1}})

    # MAU / DAU: users who submitted at least one attempt in the window.
    dau_users = await db.attempts.distinct("user_id", {"created_at": {"$gte": since_1}})
    dau_daily = await db.daily_attempts.distinct(
        "user_id", {"date_key": _iso_day()}
    )
    dau = len(set(dau_users) | set(dau_daily))

    mau_users = await db.attempts.distinct("user_id", {"created_at": {"$gte": since_30}})
    mau_daily = await db.daily_attempts.distinct(
        "user_id", {"date_key": {"$gte": _iso_day(offset=30)}}
    )
    mau = len(set(mau_users) | set(mau_daily))

    # Paid subscribers = users with non-null plan_tier.
    paid_users = await db.users.count_documents({"plan_tier": {"$in": ["club", "famille", "premium"]}})
    conv_rate = round((paid_users / total_users * 100), 1) if total_users else 0.0

    # MRR estimate — sum of amounts on active plan_tier users (monthly-equivalent).
    monthly_by_tier = {"club": 4.99, "famille": 7.99, "premium": 12.99}
    mrr = 0.0
    for tier, monthly in monthly_by_tier.items():
        n = await db.users.count_documents({"plan_tier": tier})
        mrr += n * monthly

    # Revenue MTD (from payment_transactions marked paid this calendar month)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
    rev_agg = await db.payment_transactions.aggregate([
        {"$match": {"payment_status": "paid", "updated_at": {"$gte": month_start}}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}, "n": {"$sum": 1}}},
    ]).to_list(1)
    revenue_mtd = float(rev_agg[0]["total"]) if rev_agg else 0.0
    transactions_mtd = int(rev_agg[0]["n"]) if rev_agg else 0

    return {
        "generated_at": now.isoformat(),
        "users": {
            "total": total_users,
            "new_30d": new_users_30d,
            "new_24h": new_users_24h,
            "paid": paid_users,
            "conversion_pct": conv_rate,
        },
        "engagement": {
            "dau": dau,
            "mau": mau,
            "dau_mau_pct": round((dau / mau * 100), 1) if mau else 0.0,
        },
        "revenue": {
            "mrr_estimate_eur": round(mrr, 2),
            "revenue_mtd_eur": round(revenue_mtd, 2),
            "transactions_mtd": transactions_mtd,
            "arpu_paid_eur": round(mrr / paid_users, 2) if paid_users else 0.0,
        },
    }


@router.get("/signups")
async def signups_timeseries(days: int = 30, _: dict = Depends(get_admin_user)) -> list[dict]:
    """Daily new-signup count for the last <days> days (default 30)."""
    days = max(1, min(days, 180))
    since = _iso_since(days)
    docs = await db.users.find(
        {"created_at": {"$gte": since}},
        {"_id": 0, "created_at": 1},
    ).to_list(20000)
    buckets: dict[str, int] = {}
    for d in docs:
        ca = d.get("created_at", "")
        key = ca[:10] if len(ca) >= 10 else ""
        if key:
            buckets[key] = buckets.get(key, 0) + 1
    # Fill missing days
    out = []
    for i in range(days - 1, -1, -1):
        k = _iso_day(offset=i)
        out.append({"date": k, "count": buckets.get(k, 0)})
    return out


@router.get("/revenue")
async def revenue_timeseries(days: int = 30, _: dict = Depends(get_admin_user)) -> list[dict]:
    """Daily paid revenue in EUR for the last <days> days."""
    days = max(1, min(days, 180))
    since = _iso_since(days)
    docs = await db.payment_transactions.find(
        {"payment_status": "paid", "updated_at": {"$gte": since}},
        {"_id": 0, "amount": 1, "updated_at": 1},
    ).to_list(20000)
    buckets: dict[str, float] = {}
    for d in docs:
        upd = d.get("updated_at") or ""
        key = upd[:10] if isinstance(upd, str) and len(upd) >= 10 else ""
        if key:
            buckets[key] = buckets.get(key, 0.0) + float(d.get("amount") or 0)
    out = []
    for i in range(days - 1, -1, -1):
        k = _iso_day(offset=i)
        out.append({"date": k, "amount": round(buckets.get(k, 0.0), 2)})
    return out


@router.get("/categories")
async def top_categories(_: dict = Depends(get_admin_user)) -> list[dict]:
    """Top categories by played volume (attempts count) with avg accuracy."""
    pipeline = [
        {"$group": {
            "_id": "$category_id",
            "attempts": {"$sum": 1},
            "correct": {"$sum": "$score"},
            "total": {"$sum": "$total"},
        }},
        {"$sort": {"attempts": -1}},
        {"$limit": 20},
    ]
    rows = await db.attempts.aggregate(pipeline).to_list(20)
    # Fetch category titles
    cats = {c["id"]: c["title"] async for c in db.categories.find({}, {"id": 1, "title": 1})}
    return [
        {
            "category_id": r["_id"],
            "title": cats.get(r["_id"], r["_id"]),
            "attempts": int(r["attempts"]),
            "correct": int(r["correct"]),
            "total": int(r["total"]),
            "accuracy_pct": round((r["correct"] / r["total"] * 100), 1) if r["total"] else 0.0,
        }
        for r in rows
    ]


@router.get("/atelier")
async def atelier_kpis(_: dict = Depends(get_admin_user)) -> dict:
    """Atelier Mémoire adoption metrics."""
    total_entries = await db.atelier_entries.count_documents({})
    total_sessions = len(await db.atelier_entries.distinct("session_id"))
    unique_users = len(await db.atelier_entries.distinct("user_id"))

    # Sessions per theme
    pipe = [
        {"$group": {"_id": {"session": "$session_id", "theme": "$theme"}}},
        {"$group": {"_id": "$_id.theme", "sessions": {"$sum": 1}}},
        {"$sort": {"sessions": -1}},
    ]
    by_theme = await db.atelier_entries.aggregate(pipe).to_list(20)
    return {
        "total_entries": total_entries,
        "total_sessions": total_sessions,
        "unique_users": unique_users,
        "avg_entries_per_session": round(total_entries / total_sessions, 1) if total_sessions else 0.0,
        "by_theme": [{"theme": r["_id"], "sessions": int(r["sessions"])} for r in by_theme],
    }
