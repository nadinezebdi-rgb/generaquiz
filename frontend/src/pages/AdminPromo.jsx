import { useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { motion } from "framer-motion";
import { api } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import Navbar from "@/components/Navbar";
import { Ticket, Plus, Copy, Check, Power, Trash2, Loader2, Shield, Infinity as Inf } from "lucide-react";

const DURATION_OPTIONS = [
  { value: 7, label: "7 jours" },
  { value: 30, label: "30 jours (1 mois)" },
  { value: 90, label: "3 mois" },
  { value: 365, label: "1 an" },
  { value: 36500, label: "Illimité (à vie)" },
];

export default function AdminPromo() {
  const { user, loading } = useAuth();
  const [promos, setPromos] = useState([]);
  const [fetching, setFetching] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ code: "", duration_days: 36500, max_uses: "", label: "" });
  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState("");
  const [copied, setCopied] = useState("");

  const fetchPromos = async () => {
    try {
      const { data } = await api.get("/admin/promo");
      setPromos(data);
    } catch (e) {
      setErr(e.response?.data?.detail || "Erreur");
    } finally {
      setFetching(false);
    }
  };

  useEffect(() => {
    if (user && user.role === "admin") fetchPromos();
    else if (user) setFetching(false);
  }, [user]);

  if (loading) return <div className="min-h-screen paper-bg flex items-center justify-center text-navy text-xl">Chargement...</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (user.role !== "admin") {
    return (
      <div className="min-h-screen paper-bg">
        <Navbar variant="app" />
        <main className="max-w-2xl mx-auto px-4 py-16 text-center">
          <Shield className="w-16 h-16 text-bordeaux mx-auto mb-4" />
          <h1 className="font-display text-3xl font-extrabold text-navy mb-3">Accès refusé</h1>
          <p className="text-navy/70 mb-6">Cette page est réservée aux administrateurs.</p>
          <Link to="/app/dashboard" className="bg-navy text-white font-bold px-6 py-3 rounded-full">Tableau de bord</Link>
        </main>
      </div>
    );
  }

  const submit = async (e) => {
    e.preventDefault();
    setErr(""); setSubmitting(true);
    try {
      const payload = {
        code: form.code.trim() || null,
        duration_days: Number(form.duration_days),
        max_uses: form.max_uses ? Number(form.max_uses) : null,
        label: form.label.trim() || null,
      };
      await api.post("/admin/promo", payload);
      setForm({ code: "", duration_days: 36500, max_uses: "", label: "" });
      setShowForm(false);
      await fetchPromos();
    } catch (e2) {
      setErr(e2.response?.data?.detail || "Erreur");
    } finally {
      setSubmitting(false);
    }
  };

  const copyCode = async (code) => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(code);
      setTimeout(() => setCopied(""), 1500);
    } catch {}
  };

  const toggle = async (id) => {
    try {
      await api.patch(`/admin/promo/${id}`);
      await fetchPromos();
    } catch (e) { setErr(e.response?.data?.detail || "Erreur"); }
  };

  const remove = async (id) => {
    if (!window.confirm("Supprimer définitivement ce code ?")) return;
    try {
      await api.delete(`/admin/promo/${id}`);
      await fetchPromos();
    } catch (e) { setErr(e.response?.data?.detail || "Erreur"); }
  };

  return (
    <div className="min-h-screen paper-bg">
      <Navbar variant="app" />

      <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4 mb-8">
          <div>
            <div className="inline-flex items-center gap-2 bg-bordeaux text-cream font-bold px-3 py-1 rounded-full text-sm mb-3">
              <Shield className="w-4 h-4" /> Administration
            </div>
            <h1 className="font-display text-4xl md:text-5xl font-extrabold text-navy mb-2">
              Codes promo
            </h1>
            <p className="text-lg text-navy/70 max-w-2xl">
              Créez des codes pour offrir un accès Premium gratuit (durée limitée ou illimitée).
            </p>
          </div>
          <button
            onClick={() => setShowForm((v) => !v)}
            data-testid="admin-promo-new"
            className="inline-flex items-center gap-2 bg-terracotta hover:bg-terracotta-dark text-white font-bold px-6 py-4 rounded-full shadow-warm transition"
          >
            <Plus className="w-5 h-5" /> {showForm ? "Annuler" : "Nouveau code"}
          </button>
        </div>

        {err && (
          <div className="bg-[#D9534F]/10 border-2 border-[#D9534F]/40 rounded-xl p-4 text-navy font-medium mb-6" data-testid="admin-promo-error">
            {err}
          </div>
        )}

        {showForm && (
          <motion.form
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            onSubmit={submit}
            className="bg-white border-4 border-navy rounded-[28px] p-6 md:p-8 mb-8"
            data-testid="admin-promo-form"
          >
            <div className="grid md:grid-cols-2 gap-5">
              <div>
                <label className="block font-bold text-navy mb-2">Code (optionnel)</label>
                <input
                  data-testid="admin-promo-code"
                  type="text"
                  maxLength={40}
                  placeholder="Laissez vide pour génération auto"
                  value={form.code}
                  onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })}
                  className="w-full p-4 text-lg rounded-2xl border-2 border-cream-dark focus:border-navy bg-white min-h-[56px] uppercase font-mono"
                />
              </div>
              <div>
                <label className="block font-bold text-navy mb-2">Libellé interne</label>
                <input
                  data-testid="admin-promo-label"
                  type="text"
                  maxLength={120}
                  placeholder="Ex : Promo presse, Cadeau famille..."
                  value={form.label}
                  onChange={(e) => setForm({ ...form, label: e.target.value })}
                  className="w-full p-4 text-lg rounded-2xl border-2 border-cream-dark focus:border-navy bg-white min-h-[56px]"
                />
              </div>
              <div>
                <label className="block font-bold text-navy mb-2">Durée d'accès Premium</label>
                <select
                  data-testid="admin-promo-duration"
                  value={form.duration_days}
                  onChange={(e) => setForm({ ...form, duration_days: e.target.value })}
                  className="w-full p-4 text-lg rounded-2xl border-2 border-cream-dark focus:border-navy bg-white min-h-[56px]"
                >
                  {DURATION_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block font-bold text-navy mb-2">
                  Utilisations max <span className="text-navy/50 font-normal">(vide = illimité)</span>
                </label>
                <input
                  data-testid="admin-promo-max-uses"
                  type="number"
                  min={1}
                  max={100000}
                  placeholder="Ex : 100"
                  value={form.max_uses}
                  onChange={(e) => setForm({ ...form, max_uses: e.target.value })}
                  className="w-full p-4 text-lg rounded-2xl border-2 border-cream-dark focus:border-navy bg-white min-h-[56px]"
                />
              </div>
            </div>
            <button
              type="submit"
              data-testid="admin-promo-submit"
              disabled={submitting}
              className="mt-6 inline-flex items-center gap-2 bg-terracotta hover:bg-terracotta-dark text-white font-bold px-6 py-3 rounded-full shadow-warm disabled:opacity-60"
            >
              {submitting ? <Loader2 className="w-5 h-5 animate-spin" /> : <Ticket className="w-5 h-5" />}
              Créer le code
            </button>
          </motion.form>
        )}

        {/* List */}
        {fetching ? (
          <div className="text-navy/60 text-lg">Chargement...</div>
        ) : promos.length === 0 ? (
          <div className="bg-white border-2 border-cream-dark rounded-[28px] p-10 text-center" data-testid="admin-promo-empty">
            <Ticket className="w-14 h-14 mx-auto text-terracotta/60 mb-4" />
            <h3 className="font-display text-2xl font-bold text-navy mb-2">Aucun code créé</h3>
            <p className="text-navy/70">Créez votre premier code promo ci-dessus.</p>
          </div>
        ) : (
          <div className="bg-white border-2 border-cream-dark rounded-[28px] overflow-hidden">
            <table className="w-full">
              <thead className="bg-cream">
                <tr className="text-left text-sm font-bold uppercase tracking-wider text-navy/70">
                  <th className="px-5 py-4">Code</th>
                  <th className="px-5 py-4">Durée</th>
                  <th className="px-5 py-4">Utilisations</th>
                  <th className="px-5 py-4">Statut</th>
                  <th className="px-5 py-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {promos.map((p) => (
                  <tr key={p.id} className="border-t-2 border-cream" data-testid={`admin-promo-row-${p.code}`}>
                    <td className="px-5 py-4">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => copyCode(p.code)}
                          data-testid={`admin-promo-copy-${p.code}`}
                          className="inline-flex items-center gap-2 bg-cream hover:bg-mustard transition px-3 py-1.5 rounded-lg font-mono font-bold text-navy text-base"
                          title="Copier"
                        >
                          {p.code} {copied === p.code ? <Check className="w-4 h-4 text-[#3D9970]" /> : <Copy className="w-4 h-4 text-navy/50" />}
                        </button>
                      </div>
                      {p.label && <div className="text-xs text-navy/60 mt-1">{p.label}</div>}
                    </td>
                    <td className="px-5 py-4 text-navy">
                      {p.is_lifetime ? (
                        <span className="inline-flex items-center gap-1 font-bold text-bordeaux">
                          <Inf className="w-4 h-4" /> À vie
                        </span>
                      ) : (
                        `${p.duration_days} j`
                      )}
                    </td>
                    <td className="px-5 py-4 text-navy">
                      <span className="font-bold">{p.used_count}</span>
                      <span className="text-navy/50"> / {p.max_uses ?? "∞"}</span>
                    </td>
                    <td className="px-5 py-4">
                      {p.active ? (
                        <span className="inline-block bg-[#3D9970]/15 text-[#26653C] text-xs font-bold px-2 py-1 rounded-full">Actif</span>
                      ) : (
                        <span className="inline-block bg-[#D9534F]/15 text-bordeaux text-xs font-bold px-2 py-1 rounded-full">Désactivé</span>
                      )}
                    </td>
                    <td className="px-5 py-4 text-right">
                      <button
                        onClick={() => toggle(p.id)}
                        data-testid={`admin-promo-toggle-${p.code}`}
                        className="inline-flex items-center gap-1 text-navy/70 hover:text-terracotta font-medium text-sm mr-3"
                        title={p.active ? "Désactiver" : "Réactiver"}
                      >
                        <Power className="w-4 h-4" /> {p.active ? "Désactiver" : "Activer"}
                      </button>
                      <button
                        onClick={() => remove(p.id)}
                        data-testid={`admin-promo-delete-${p.code}`}
                        className="inline-flex items-center gap-1 text-bordeaux hover:text-[#D9534F] font-medium text-sm"
                        title="Supprimer"
                      >
                        <Trash2 className="w-4 h-4" /> Supprimer
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  );
}
