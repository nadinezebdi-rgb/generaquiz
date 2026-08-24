import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { History, Search, Loader2, User, Package, Clock } from "lucide-react";
import { api, formatError } from "@/lib/api";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";

/**
 * AdminAudit — journal des actions administrateur (superadmin only côté back-end).
 * Lecture seule. Utile pour retracer :
 *   - Changement de rôle (user.role_change)
 *   - QA bulk approve/delete/flag, delete, rerun (qa.*)
 *   - Codes promo create/toggle/delete (promo.*)
 */
export default function AdminAudit() {
  const [events, setEvents] = useState([]);
  const [total, setTotal] = useState(0);
  const [actions, setActions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");
  const [action, setAction] = useState("");

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ limit: "200" });
      if (q) params.set("q", q);
      if (action) params.set("action", action);
      const { data } = await api.get(`/admin/audit?${params.toString()}`);
      setEvents(data.events || []);
      setTotal(data.total || 0);
    } catch (e) {
      toast.error(formatError(e?.response?.data?.detail) || "Impossible de charger l'audit");
    } finally {
      setLoading(false);
    }
  }, [q, action]);

  useEffect(() => {
    api.get("/admin/audit/actions").then((r) => setActions(r.data || [])).catch(() => {});
  }, []);
  useEffect(() => { refresh(); }, [refresh]);

  return (
    <div className="min-h-screen bg-cream text-navy">
      <Navbar />
      <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8" data-testid="admin-audit-page">
        <header className="mb-6">
          <span className="inline-flex items-center gap-2 bg-terracotta text-white font-bold px-3 py-1 rounded-full text-xs uppercase tracking-wider mb-3">
            <History className="w-3.5 h-3.5" /> Super-admin · Journal d&apos;audit
          </span>
          <h1 className="font-display text-4xl font-extrabold">Journal des actions administrateur</h1>
          <p className="text-navy/70 mt-2">
            {total} événement{total > 1 ? "s" : ""} enregistré{total > 1 ? "s" : ""} · lecture seule.
          </p>
        </header>

        <div className="bg-white border-2 border-cream-dark rounded-2xl p-4 mb-4 flex flex-wrap items-center gap-3" data-testid="admin-audit-filters">
          <div className="flex items-center gap-2 flex-1 min-w-[220px] border-2 border-cream-dark rounded-full px-3">
            <Search className="w-4 h-4 text-navy/40" />
            <input
              type="search"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Rechercher email admin, cible, action"
              className="flex-1 py-2 outline-none bg-transparent"
              data-testid="admin-audit-search"
            />
          </div>
          <select
            value={action}
            onChange={(e) => setAction(e.target.value)}
            data-testid="admin-audit-action-filter"
            className="border-2 border-cream-dark rounded-full px-4 py-2 bg-white outline-none"
          >
            <option value="">Toutes les actions</option>
            {actions.map((a) => <option key={a} value={a}>{a}</option>)}
          </select>
        </div>

        {loading ? (
          <div className="text-center py-10 text-navy/60 inline-flex items-center gap-2">
            <Loader2 className="w-5 h-5 animate-spin" /> Chargement…
          </div>
        ) : events.length === 0 ? (
          <div className="bg-white border-2 border-cream-dark rounded-2xl p-10 text-center text-navy/60" data-testid="admin-audit-empty">
            Aucun événement pour ces filtres.
          </div>
        ) : (
          <ul className="space-y-3" data-testid="admin-audit-list">
            {events.map((e, i) => <AuditRow key={i} event={e} />)}
          </ul>
        )}
      </main>
      <Footer />
    </div>
  );
}

function AuditRow({ event }) {
  const date = event.created_at ? new Date(event.created_at) : null;
  const actionColor = event.action?.startsWith("user.")
    ? "bg-terracotta text-white"
    : event.action?.startsWith("qa.")
      ? "bg-navy text-cream"
      : event.action?.startsWith("promo.")
        ? "bg-mustard text-navy"
        : "bg-bordeaux text-white";

  return (
    <li className="bg-white border-2 border-cream-dark rounded-2xl p-4" data-testid="admin-audit-row">
      <div className="flex flex-wrap items-start gap-3">
        <span className={`inline-flex items-center gap-1 font-mono text-[11px] font-bold uppercase tracking-widest px-2.5 py-1 rounded-full ${actionColor}`}>
          {event.action}
        </span>
        <div className="text-xs text-navy/50 inline-flex items-center gap-1">
          <Clock className="w-3 h-3" />
          {date ? date.toLocaleString("fr-FR") : "—"}
        </div>
      </div>
      <div className="mt-2 grid md:grid-cols-2 gap-3 text-sm">
        <div>
          <div className="inline-flex items-center gap-1 text-xs uppercase tracking-widest text-navy/50 font-bold mb-1">
            <User className="w-3 h-3" /> Admin
          </div>
          <div className="font-bold text-navy">{event.admin_email || "(inconnu)"}</div>
          {event.admin_role && <div className="text-xs text-navy/50">rôle : {event.admin_role}</div>}
        </div>
        <div>
          <div className="inline-flex items-center gap-1 text-xs uppercase tracking-widest text-navy/50 font-bold mb-1">
            <Package className="w-3 h-3" /> Cible
          </div>
          <div className="text-navy">
            {event.target_label || event.target_id || <span className="italic text-navy/40">—</span>}
          </div>
          {event.target_type && <div className="text-xs text-navy/50">type : {event.target_type}</div>}
        </div>
      </div>
      {(event.before || event.after) && (
        <div className="mt-3 grid md:grid-cols-2 gap-3 text-xs">
          {event.before && (
            <div className="bg-cream rounded-lg p-2 border border-cream-dark">
              <div className="text-navy/50 font-bold uppercase tracking-widest text-[10px] mb-1">Avant</div>
              <pre className="whitespace-pre-wrap break-words font-mono text-navy/80">{JSON.stringify(event.before, null, 2)}</pre>
            </div>
          )}
          {event.after && (
            <div className="bg-[#3D9970]/10 rounded-lg p-2 border border-[#3D9970]/30">
              <div className="text-[#2A7350] font-bold uppercase tracking-widest text-[10px] mb-1">Après</div>
              <pre className="whitespace-pre-wrap break-words font-mono text-navy/80">{JSON.stringify(event.after, null, 2)}</pre>
            </div>
          )}
        </div>
      )}
      {event.meta && Object.keys(event.meta).length > 0 && (
        <details className="mt-3">
          <summary className="text-xs font-bold text-navy/60 cursor-pointer hover:text-navy">Détails techniques</summary>
          <pre className="mt-2 text-xs font-mono bg-navy text-cream/80 p-3 rounded-lg overflow-x-auto">{JSON.stringify(event.meta, null, 2)}</pre>
        </details>
      )}
    </li>
  );
}
