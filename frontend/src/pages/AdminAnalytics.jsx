import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid,
  ResponsiveContainer,
} from "recharts";
import { api, formatError } from "@/lib/api";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import {
  Users, TrendingUp, Euro, Activity, BookOpen, Loader2, RefreshCw,
} from "lucide-react";

/**
 * /app/admin/analytics — Admin-only KPI dashboard.
 *
 * Read-only. Data comes from GET /api/admin/analytics/{overview|signups|revenue|categories|atelier}.
 * Every panel guards against empty/missing data so a fresh install still renders.
 */

function Kpi({ label, value, sub, icon: Icon, tone = "navy", testid }) {
  const tones = {
    navy: "bg-navy text-cream",
    terracotta: "bg-terracotta text-white",
    mustard: "bg-mustard text-navy",
    bordeaux: "bg-bordeaux text-cream",
  };
  return (
    <div data-testid={testid} className={`rounded-[20px] p-4 md:p-5 ${tones[tone]}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-bold uppercase tracking-wider opacity-80">{label}</span>
        <Icon className="w-4 h-4 opacity-70" />
      </div>
      <div className="font-display text-3xl font-extrabold leading-none">{value}</div>
      {sub && <div className="text-xs opacity-75 mt-1">{sub}</div>}
    </div>
  );
}

export default function AdminAnalytics() {
  const [overview, setOverview] = useState(null);
  const [signups, setSignups] = useState([]);
  const [revenue, setRevenue] = useState([]);
  const [cats, setCats] = useState([]);
  const [atelier, setAtelier] = useState(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState(null);

  async function load() {
    setLoading(true);
    setErr(null);
    try {
      const [ov, su, rv, ct, at] = await Promise.all([
        api.get("/admin/analytics/overview"),
        api.get("/admin/analytics/signups?days=30"),
        api.get("/admin/analytics/revenue?days=30"),
        api.get("/admin/analytics/categories"),
        api.get("/admin/analytics/atelier"),
      ]);
      setOverview(ov.data);
      setSignups(su.data);
      setRevenue(rv.data);
      setCats(ct.data);
      setAtelier(at.data);
    } catch (e) {
      setErr(formatError(e.response?.data?.detail) || "Chargement impossible");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  if (loading) {
    return (
      <div className="min-h-screen paper-bg">
        <Navbar variant="app" />
        <div className="max-w-7xl mx-auto px-4 py-16 flex justify-center">
          <Loader2 className="w-8 h-8 animate-spin text-terracotta" />
        </div>
      </div>
    );
  }

  if (err) {
    return (
      <div className="min-h-screen paper-bg">
        <Navbar variant="app" />
        <div className="max-w-3xl mx-auto px-4 py-16 text-center">
          <div className="bg-white border-2 border-cream-dark rounded-[24px] p-8" data-testid="admin-analytics-error">
            <div className="text-navy/80 mb-3">{err}</div>
            <button
              type="button"
              onClick={load}
              className="inline-flex items-center gap-2 bg-terracotta text-white font-bold px-4 py-2 rounded-full"
            >
              <RefreshCw className="w-4 h-4" /> Réessayer
            </button>
          </div>
        </div>
      </div>
    );
  }

  const u = overview.users;
  const e = overview.engagement;
  const r = overview.revenue;

  return (
    <div className="min-h-screen paper-bg">
      <Navbar variant="app" />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <div className="flex items-start justify-between mb-6 gap-3 flex-wrap">
          <div>
            <h1 className="font-display text-4xl font-extrabold text-navy" data-testid="admin-analytics-title">
              Tableau de bord <span className="text-terracotta italic">business</span>
            </h1>
            <p className="text-navy/60 text-sm">
              Généré à {new Date(overview.generated_at).toLocaleTimeString("fr-FR")}
            </p>
          </div>
          <button
            type="button"
            onClick={load}
            data-testid="admin-analytics-refresh"
            className="inline-flex items-center gap-2 bg-white border-2 border-cream-dark text-navy hover:border-terracotta font-bold px-4 py-2 rounded-full transition"
          >
            <RefreshCw className="w-4 h-4" /> Rafraîchir
          </button>
        </div>

        {/* --- KPI cards --- */}
        <section className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6" data-testid="admin-kpi-grid">
          <Kpi
            testid="admin-kpi-users"
            label="Utilisateurs" value={u.total.toLocaleString("fr-FR")}
            sub={`+${u.new_30d} sur 30 j`} icon={Users} tone="navy"
          />
          <Kpi
            testid="admin-kpi-paid"
            label="Abonnés payants" value={u.paid.toLocaleString("fr-FR")}
            sub={`${u.conversion_pct}% de conversion`} icon={TrendingUp} tone="terracotta"
          />
          <Kpi
            testid="admin-kpi-mrr"
            label="MRR estimé" value={`${r.mrr_estimate_eur} €`}
            sub={`ARPU ${r.arpu_paid_eur} €`} icon={Euro} tone="mustard"
          />
          <Kpi
            testid="admin-kpi-dau"
            label="DAU / MAU" value={`${e.dau} / ${e.mau}`}
            sub={`Stickiness ${e.dau_mau_pct}%`} icon={Activity} tone="bordeaux"
          />
        </section>

        {/* --- Charts row --- */}
        <section className="grid lg:grid-cols-2 gap-4 mb-6">
          <div className="bg-white border-2 border-cream-dark rounded-[24px] p-5" data-testid="admin-chart-signups">
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-display text-xl font-extrabold text-navy">Nouveaux inscrits (30 j)</h2>
              <span className="text-xs text-navy/60">
                Total : {signups.reduce((s, d) => s + d.count, 0)}
              </span>
            </div>
            <div className="h-64">
              <ResponsiveContainer>
                <LineChart data={signups}>
                  <CartesianGrid stroke="#E8DFC7" strokeDasharray="4 4" />
                  <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#1F2A44" }} tickFormatter={(d) => d.slice(5)} />
                  <YAxis tick={{ fontSize: 11, fill: "#1F2A44" }} allowDecimals={false} />
                  <Tooltip contentStyle={{ borderRadius: 12, border: "2px solid #E8DFC7" }} />
                  <Line type="monotone" dataKey="count" stroke="#C25E3D" strokeWidth={2.5} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="bg-white border-2 border-cream-dark rounded-[24px] p-5" data-testid="admin-chart-revenue">
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-display text-xl font-extrabold text-navy">Recettes journalières (30 j)</h2>
              <span className="text-xs text-navy/60">
                Total : {revenue.reduce((s, d) => s + d.amount, 0).toFixed(2)} €
              </span>
            </div>
            <div className="h-64">
              <ResponsiveContainer>
                <BarChart data={revenue}>
                  <CartesianGrid stroke="#E8DFC7" strokeDasharray="4 4" />
                  <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#1F2A44" }} tickFormatter={(d) => d.slice(5)} />
                  <YAxis tick={{ fontSize: 11, fill: "#1F2A44" }} />
                  <Tooltip contentStyle={{ borderRadius: 12, border: "2px solid #E8DFC7" }} formatter={(v) => [`${v} €`, "Recettes"]} />
                  <Bar dataKey="amount" fill="#1F2A44" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </section>

        {/* --- Categories + atelier --- */}
        <section className="grid lg:grid-cols-2 gap-4">
          <div className="bg-white border-2 border-cream-dark rounded-[24px] p-5" data-testid="admin-table-categories">
            <h2 className="font-display text-xl font-extrabold text-navy mb-3">Top catégories jouées</h2>
            {cats.length === 0 ? (
              <div className="text-navy/60 text-sm">Aucune donnée pour le moment.</div>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-navy/60 uppercase tracking-wider">
                    <th className="py-2">Catégorie</th>
                    <th className="text-right">Quiz</th>
                    <th className="text-right">Précision</th>
                  </tr>
                </thead>
                <tbody>
                  {cats.map((c) => (
                    <tr key={c.category_id} className="border-t border-cream-dark" data-testid={`admin-cat-row-${c.category_id}`}>
                      <td className="py-2 font-bold text-navy">{c.title}</td>
                      <td className="text-right">{c.attempts}</td>
                      <td className="text-right">
                        <span className={c.accuracy_pct >= 70 ? "text-[#2A7350] font-bold" : "text-navy"}>
                          {c.accuracy_pct}%
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          <div className="bg-white border-2 border-cream-dark rounded-[24px] p-5" data-testid="admin-atelier-kpis">
            <div className="flex items-center gap-2 mb-3">
              <BookOpen className="w-5 h-5 text-terracotta" />
              <h2 className="font-display text-xl font-extrabold text-navy">Atelier Mémoire</h2>
            </div>
            <div className="grid grid-cols-2 gap-3 mb-4">
              <div className="bg-cream rounded-2xl p-3">
                <div className="text-xs text-navy/60 uppercase font-bold">Sessions</div>
                <div className="font-display text-2xl font-extrabold text-navy">{atelier.total_sessions}</div>
              </div>
              <div className="bg-cream rounded-2xl p-3">
                <div className="text-xs text-navy/60 uppercase font-bold">Souvenirs</div>
                <div className="font-display text-2xl font-extrabold text-navy">{atelier.total_entries}</div>
              </div>
              <div className="bg-cream rounded-2xl p-3">
                <div className="text-xs text-navy/60 uppercase font-bold">Utilisateurs</div>
                <div className="font-display text-2xl font-extrabold text-navy">{atelier.unique_users}</div>
              </div>
              <div className="bg-cream rounded-2xl p-3">
                <div className="text-xs text-navy/60 uppercase font-bold">Moy / session</div>
                <div className="font-display text-2xl font-extrabold text-navy">{atelier.avg_entries_per_session}</div>
              </div>
            </div>
            {atelier.by_theme?.length > 0 && (
              <div>
                <div className="text-xs text-navy/60 uppercase font-bold mb-2">Par thème</div>
                <div className="space-y-1">
                  {atelier.by_theme.map((t) => (
                    <div key={t.theme} className="flex items-center justify-between text-sm">
                      <span className="text-navy">{t.theme}</span>
                      <span className="font-bold text-terracotta">{t.sessions}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </section>
      </main>
      <Footer />
    </div>
  );
}
