import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { api, formatError } from "@/lib/api";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { Users, Building2, ClipboardList, Plus, Trash2, Play, Sparkles, ArrowRight } from "lucide-react";

/**
 * EhpadDashboard — accueil animateur EHPAD.
 *
 * Onglets : Résidents · Séances · Nouvelle séance.
 * Reste léger : le vrai poste de travail sera étendu en V2.
 */
export default function EhpadDashboard() {
  const [tab, setTab] = useState("dashboard");
  const [dash, setDash] = useState(null);
  const [residents, setResidents] = useState([]);
  const [sessions, setSessions] = useState([]);
  const navigate = useNavigate();

  useEffect(() => { refresh(); }, []);

  async function refresh() {
    try {
      const [d, r, s] = await Promise.all([
        api.get("/ehpad/dashboard"),
        api.get("/ehpad/residents"),
        api.get("/ehpad/sessions"),
      ]);
      setDash(d.data); setResidents(r.data); setSessions(s.data);
    } catch (e) {
      const status = e.response?.status;
      if (status === 403) {
        toast.error("Réservé aux comptes animateurs EHPAD");
        navigate("/app/dashboard");
      } else {
        toast.error(formatError(e.response?.data?.detail) || "Erreur de chargement");
      }
    }
  }

  return (
    <div className="min-h-screen paper-bg">
      <Navbar variant="app" />
      <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <header className="mb-8">
          <span className="inline-flex items-center gap-2 bg-navy text-cream font-bold px-3 py-1 rounded-full text-xs uppercase tracking-wider mb-3">
            <Building2 className="w-3.5 h-3.5" /> Espace animateur EHPAD
          </span>
          <h1 className="font-display text-4xl md:text-5xl font-extrabold text-navy" data-testid="ehpad-title">
            🏥 Bienvenue, <span className="text-terracotta italic">animateur</span>
          </h1>
          <p className="text-navy/70 mt-2 max-w-2xl">
            Gérez vos résidents, animez des séances collectives (quiz ou souvenirs), et gardez trace des moments partagés.
          </p>
        </header>

        {dash && (
          <div className="grid grid-cols-3 gap-4 mb-8">
            <StatCard label="Résidents actifs" value={dash.n_residents} icon={Users} testid="ehpad-stat-residents" />
            <StatCard label="Séances animées" value={dash.n_sessions} icon={ClipboardList} testid="ehpad-stat-sessions" />
            <StatCard label="Souvenirs récoltés" value={dash.n_responses} icon={Sparkles} testid="ehpad-stat-responses" />
          </div>
        )}

        <div className="mb-6 flex gap-2 border-b-2 border-cream-dark">
          <TabBtn active={tab === "dashboard"} onClick={() => setTab("dashboard")} testid="ehpad-tab-dashboard">📊 Vue d&apos;ensemble</TabBtn>
          <TabBtn active={tab === "residents"} onClick={() => setTab("residents")} testid="ehpad-tab-residents">👥 Résidents ({residents.length})</TabBtn>
          <TabBtn active={tab === "sessions"} onClick={() => setTab("sessions")} testid="ehpad-tab-sessions">📋 Séances</TabBtn>
        </div>

        {tab === "dashboard" && <DashboardTab dash={dash} onCreate={() => navigate("/app/ehpad/nouvelle-seance")} />}
        {tab === "residents" && <ResidentsTab residents={residents} onChange={refresh} />}
        {tab === "sessions" && <SessionsTab sessions={sessions} onCreate={() => navigate("/app/ehpad/nouvelle-seance")} />}
      </main>
      <Footer />
    </div>
  );
}

function TabBtn({ active, onClick, children, testid }) {
  return (
    <button type="button" onClick={onClick} data-testid={testid}
      className={`inline-flex items-center gap-2 px-4 py-2 font-bold text-sm border-b-4 -mb-0.5 transition ${
        active ? "border-terracotta text-terracotta" : "border-transparent text-navy/60 hover:text-navy"
      }`}>{children}</button>
  );
}

function StatCard({ label, value, icon: Icon, testid }) {
  return (
    <div className="bg-white rounded-2xl border-2 border-cream-dark p-5 shadow-warm" data-testid={testid}>
      <Icon className="w-6 h-6 text-terracotta mb-2" />
      <div className="text-3xl font-extrabold text-navy">{value}</div>
      <div className="text-sm text-navy/60">{label}</div>
    </div>
  );
}

function DashboardTab({ dash, onCreate }) {
  return (
    <div className="space-y-6">
      <div className="bg-gradient-to-br from-terracotta/10 to-mustard/20 rounded-2xl border-2 border-terracotta/40 p-6 flex items-start gap-4">
        <div className="bg-terracotta text-white rounded-2xl p-3"><Play className="w-8 h-8" /></div>
        <div className="flex-1">
          <h3 className="font-display text-xl font-extrabold text-navy mb-1">Lancer une séance collective</h3>
          <p className="text-navy/70 mb-3">Choisissez un quiz thématique ou un prompt du Livre de Vie, sélectionnez les résidents présents, et notez leurs réponses au fur et à mesure.</p>
          <button onClick={onCreate} data-testid="ehpad-new-session-cta"
            className="inline-flex items-center gap-2 bg-terracotta text-white font-bold px-5 py-2.5 rounded-full hover:bg-terracotta-dark transition shadow-warm">
            <Plus className="w-4 h-4" /> Nouvelle séance
          </button>
        </div>
      </div>
      {dash?.recent_sessions?.length > 0 && (
        <div className="bg-white rounded-2xl border-2 border-cream-dark p-5">
          <h3 className="font-display text-lg font-bold text-navy mb-3">Dernières séances</h3>
          <ul className="space-y-2">
            {dash.recent_sessions.map((s) => (
              <li key={s.id} className="flex items-center justify-between text-sm bg-cream rounded-lg p-3 border border-cream-dark">
                <div>
                  <div className="font-bold text-navy">{s.ref_title}</div>
                  <div className="text-xs text-navy/60">{new Date(s.created_at).toLocaleDateString("fr-FR")} · {s.kind === "quiz" ? "Quiz" : "Souvenir"}</div>
                </div>
                <Link to={`/app/ehpad/seance/${s.id}`} className="text-terracotta font-bold text-sm hover:underline">Ouvrir →</Link>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function ResidentsTab({ residents, onChange }) {
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({ first_name: "", initial: "", age: "", notes: "" });
  const [saving, setSaving] = useState(false);

  async function add() {
    if (!form.first_name.trim()) return;
    setSaving(true);
    try {
      await api.post("/ehpad/residents", {
        first_name: form.first_name.trim(),
        initial: form.initial.trim(),
        age: form.age ? parseInt(form.age, 10) : null,
        notes: form.notes.trim(),
      });
      toast.success("Résident ajouté");
      setForm({ first_name: "", initial: "", age: "", notes: "" });
      setShowAdd(false);
      onChange();
    } catch (e) { toast.error(formatError(e.response?.data?.detail) || "Erreur"); }
    finally { setSaving(false); }
  }

  async function remove(id) {
    if (!window.confirm("Retirer ce résident de la liste ?")) return;
    try {
      await api.delete(`/ehpad/residents/${id}`);
      toast.success("Résident retiré");
      onChange();
    } catch (e) { toast.error("Erreur"); }
  }

  return (
    <div className="space-y-4">
      <button onClick={() => setShowAdd(!showAdd)} data-testid="ehpad-add-resident-toggle"
        className="inline-flex items-center gap-2 bg-navy text-cream font-bold px-4 py-2 rounded-full hover:bg-navy-dark transition">
        <Plus className="w-4 h-4" /> Ajouter un résident
      </button>
      {showAdd && (
        <div className="bg-white rounded-2xl border-2 border-cream-dark p-5 space-y-3" data-testid="ehpad-add-resident-form">
          <div className="grid md:grid-cols-3 gap-3">
            <input value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })}
              placeholder="Prénom" maxLength={40}
              className="p-3 rounded-lg border-2 border-cream-dark focus:border-terracotta outline-none" data-testid="ehpad-resident-first-name" />
            <input value={form.initial} onChange={(e) => setForm({ ...form, initial: e.target.value })}
              placeholder="Initiale (ex. M.)" maxLength={3}
              className="p-3 rounded-lg border-2 border-cream-dark focus:border-terracotta outline-none" />
            <input value={form.age} onChange={(e) => setForm({ ...form, age: e.target.value })}
              placeholder="Âge (optionnel)" type="number" min="40" max="120"
              className="p-3 rounded-lg border-2 border-cream-dark focus:border-terracotta outline-none" />
          </div>
          <textarea value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })}
            placeholder="Notes (préférences, souvenirs marquants…)" maxLength={400}
            className="w-full p-3 rounded-lg border-2 border-cream-dark focus:border-terracotta outline-none min-h-[80px]" />
          <button onClick={add} disabled={saving} data-testid="ehpad-resident-save"
            className="inline-flex items-center gap-2 bg-terracotta text-white font-bold px-4 py-2 rounded-full hover:bg-terracotta-dark disabled:opacity-50 transition">
            Enregistrer
          </button>
        </div>
      )}
      {residents.length === 0 ? (
        <p className="text-navy/60 text-sm">Aucun résident enregistré pour l&apos;instant.</p>
      ) : (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
          {residents.map((r) => (
            <div key={r.id} className="bg-white rounded-xl border-2 border-cream-dark p-4 flex items-start justify-between" data-testid={`ehpad-resident-${r.id}`}>
              <div>
                <div className="font-bold text-navy">{r.first_name} {r.initial}</div>
                {r.age && <div className="text-xs text-navy/60">{r.age} ans</div>}
                {r.notes && <p className="text-sm text-navy/70 mt-1">{r.notes}</p>}
              </div>
              <button onClick={() => remove(r.id)} className="text-bordeaux p-1 hover:bg-bordeaux/10 rounded transition">
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function SessionsTab({ sessions, onCreate }) {
  if (sessions.length === 0) {
    return (
      <div className="bg-white rounded-2xl border-2 border-dashed border-cream-dark p-10 text-center">
        <ClipboardList className="w-12 h-12 text-navy/30 mx-auto mb-3" />
        <p className="text-navy/60 mb-4">Aucune séance encore animée.</p>
        <button onClick={onCreate} className="bg-terracotta text-white font-bold px-5 py-2 rounded-full inline-flex items-center gap-2">
          <Plus className="w-4 h-4" /> Créer ma première séance
        </button>
      </div>
    );
  }
  return (
    <ul className="space-y-2">
      {sessions.map((s) => (
        <li key={s.id} className="bg-white rounded-xl border-2 border-cream-dark p-4 flex items-center justify-between">
          <div>
            <div className="font-bold text-navy">{s.ref_title}</div>
            <div className="text-xs text-navy/60">
              {new Date(s.created_at).toLocaleDateString("fr-FR")} · {s.kind === "quiz" ? "Quiz" : "Souvenir"} · {s.resident_ids.length} résident(s) · {s.n_responses} réponse(s)
            </div>
          </div>
          <Link to={`/app/ehpad/seance/${s.id}`} data-testid={`ehpad-session-open-${s.id}`}
            className="inline-flex items-center gap-1 text-terracotta font-bold text-sm hover:underline">
            Ouvrir <ArrowRight className="w-4 h-4" />
          </Link>
        </li>
      ))}
    </ul>
  );
}
