"""Rapport du matin (07:30 Paris) envoyé aux admins : ce que les tâches de
la nuit ont rempli, repris ou raté + stock par thème + conseil du jour."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from html import escape

import resend

from core import ADMIN_EMAIL, FRONTEND_URL, RESEND_API_KEY, SENDER_EMAIL, db, logger
from daily_tips import today_key

TARGET = 140
STATUS_LABEL = {"done": "✅ Terminé", "failed": "❌ Échec", "running": "⏳ En cours",
                "queued": "🕒 En file", "cancelled": "⛔ Annulé"}


async def _recipients() -> list[str]:
    emails = {u["email"].lower() async for u in db.users.find(
        {"role": {"$in": ["admin", "superadmin"]}}, {"_id": 0, "email": 1})}
    if ADMIN_EMAIL:
        emails.add(ADMIN_EMAIL.lower())
    return sorted(emails)


async def build_report() -> dict:
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    jobs = await db.qa_jobs.find(
        {"started_at": {"$gte": since.isoformat()}}, {"_id": 0}
    ).sort("started_at", 1).to_list(200)
    rows = []
    for j in jobs:
        p = j.get("progress") or {}
        rows.append({
            "category": j.get("category_title") or j.get("category_id"),
            "kind": j.get("kind", "topup"),
            "status": j.get("status"),
            "resumes": int(j.get("resume_count") or 0),
            "done": int(p.get("done") or 0),
            "total": int(p.get("total") or 0),
            "retagged": int(p.get("retagged") or 0),
            "backlog": int(p.get("backlog_verified") or 0),
            "generated": int(p.get("generated") or 0),
            "note": j.get("error") or j.get("last_interruption") or "",
        })
    stock = []
    async for c in db.categories.find({}, {"_id": 0, "id": 1, "title": 1}):
        n = await db.questions.count_documents({"category_id": c["id"], "quality": {"$ne": "flagged"},
                                                "difficulty": {"$gte": 1, "$lte": 7}})
        stock.append({"title": c["title"], "playable": n})
    regen = await db.app_state.find_one({"key": "mistral_regen"}, {"_id": 0}) or {}
    tip = await db.daily_tips.find_one({"date_key": today_key()}, {"_id": 0, "title": 1, "theme": 1})
    return {
        "jobs": rows,
        "filled": sum(r["done"] for r in rows),
        "resumed": sum(1 for r in rows if r["resumes"] > 0),
        "failed": sum(1 for r in rows if r["status"] == "failed"),
        "stock": stock,
        "complete": sum(1 for s in stock if s["playable"] >= TARGET),
        "regen": {"status": regen.get("status"), "finished_at": regen.get("finished_at"),
                  "total": (regen.get("last_summary") or {}).get("total")},
        "tip": tip,
    }


def _td(v, bold=False) -> str:
    style = "padding:6px 8px;border-bottom:1px solid #E8E2C9;font-size:13px;"
    return f'<td style="{style}{"font-weight:700;" if bold else ""}">{v}</td>'


def render_html(r: dict) -> str:
    job_rows = "".join(
        "<tr>" + _td(escape(j["category"]), True) + _td(j["kind"]) + _td(STATUS_LABEL.get(j["status"], j["status"]))
        + _td(f'{j["done"]}/{j["total"]}' if j["total"] else "—")
        + _td(f'{j["retagged"]} · {j["backlog"]} · {j["generated"]}')
        + _td(f'{j["resumes"]}' if j["resumes"] else "—")
        + _td(escape(j["note"][:120])) + "</tr>"
        for j in r["jobs"]
    ) or f'<tr>{_td("Aucune tâche lancée ces dernières 24 h.")}</tr>'
    stock_rows = "".join(
        "<tr>" + _td(escape(s["title"]), True)
        + _td(f'{"✅" if s["playable"] >= TARGET else "🟧"} {s["playable"]} / {TARGET}') + "</tr>"
        for s in r["stock"]
    )
    tip = r["tip"]
    tip_line = (f'✅ « {escape(tip["title"])} » ({escape(tip["theme"])})' if tip
                else "⚠️ Aucun conseil validé pour aujourd'hui (le dernier conseil reste affiché).")
    regen = r["regen"]
    th = 'style="text-align:left;padding:6px 8px;font-size:11px;color:#1E3A5F99;text-transform:uppercase"'
    return f"""<div style="font-family:Georgia,serif;background:#F4F1DE;padding:24px;color:#1E3A5F">
<div style="max-width:720px;margin:auto;background:#fff;border-radius:18px;padding:24px;border:2px solid #E8E2C9">
<h1 style="margin:0 0 4px;font-size:22px">☀️ Rapport du matin — GénéraQuiz</h1>
<p style="margin:0 0 18px;color:#1E3A5F99">{datetime.now(timezone.utc).strftime("%d/%m/%Y")} · tâches des dernières 24 h</p>
<table style="width:100%;margin-bottom:18px"><tr>
<td style="background:#E07A5F15;border-radius:12px;padding:12px;text-align:center"><b style="font-size:22px">{r["filled"]}</b><br><span style="font-size:12px">questions ajoutées</span></td>
<td style="background:#F2CC8F40;border-radius:12px;padding:12px;text-align:center"><b style="font-size:22px">{r["resumed"]}</b><br><span style="font-size:12px">tâche(s) reprise(s)</span></td>
<td style="background:#722F3715;border-radius:12px;padding:12px;text-align:center"><b style="font-size:22px">{r["failed"]}</b><br><span style="font-size:12px">échec(s)</span></td>
<td style="background:#3D997015;border-radius:12px;padding:12px;text-align:center"><b style="font-size:22px">{r["complete"]}/{len(r["stock"])}</b><br><span style="font-size:12px">thèmes complets</span></td>
</tr></table>
<h2 style="font-size:16px">Tâches de remplissage</h2>
<table style="width:100%;border-collapse:collapse"><tr><th {th}>Thème</th><th {th}>Type</th><th {th}>Statut</th><th {th}>Progression</th><th {th}>Retag · Stock · IA</th><th {th}>Reprises</th><th {th}>Note</th></tr>{job_rows}</table>
<h2 style="font-size:16px;margin-top:20px">Stock jouable par thème</h2>
<table style="width:100%;border-collapse:collapse">{stock_rows}</table>
<h2 style="font-size:16px;margin-top:20px">Autres tâches de la nuit</h2>
<p style="font-size:13px;margin:4px 0">Régénération Mistral : <b>{escape(str(regen.get("status") or "—"))}</b> · {regen.get("total") or 0} question(s) · fin {escape(str(regen.get("finished_at") or "—"))[:16]}</p>
<p style="font-size:13px;margin:4px 0">Conseil du jour de Lucienne : {tip_line}</p>
<p style="margin-top:20px"><a href="{FRONTEND_URL}/app/admin/qa" style="background:#E07A5F;color:#fff;padding:10px 18px;border-radius:999px;text-decoration:none;font-weight:700">Ouvrir l'admin QA</a></p>
</div></div>"""


async def send_admin_morning_report() -> dict:
    if not RESEND_API_KEY:
        logger.info("[morning-report] RESEND_API_KEY manquant — envoi sauté")
        return {"sent": 0, "reason": "no_resend_key"}
    report = await build_report()
    html = render_html(report)
    subject = (f"☀️ Rapport du matin : {report['filled']} ajoutée(s), "
               f"{report['resumed']} reprise(s), {report['failed']} échec(s)")
    sent, recipients = 0, await _recipients()
    for email in recipients:
        try:
            await asyncio.to_thread(resend.Emails.send, {
                "from": SENDER_EMAIL, "to": [email], "subject": subject, "html": html,
            })
            sent += 1
        except Exception as e:
            logger.warning(f"[morning-report] échec pour {email}: {e}")
    logger.info(f"[morning-report] envoyé à {sent}/{len(recipients)} admin(s)")
    return {"sent": sent, "recipients": recipients, "subject": subject,
            "summary": {k: report[k] for k in ("filled", "resumed", "failed", "complete")}}
