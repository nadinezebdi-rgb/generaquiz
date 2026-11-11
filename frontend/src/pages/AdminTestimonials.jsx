import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Quote, Trash2, Eye, EyeOff, Save, Plus, BarChart3 } from "lucide-react";
import Navbar from "@/components/Navbar";
import { api, formatError } from "@/lib/api";

const EMPTY = { text: "", first_name: "", age_role: "", location: "", profile: "SENIOR", published: false };
const PROFILES = ["SENIOR", "FAMILLE", "EHPAD"];
const STAT_FIELDS = [
  { key: "players_today", label: "Joueurs aujourd'hui" },
  { key: "games_today", label: "Parties (24 h)" },
  { key: "countries_active", label: "Pays / régions actifs" },
  { key: "streak_record", label: "Record de série (jours)" },
];
const input = "w-full rounded-xl border-2 border-cream-dark px-3 py-2 text-navy focus:border-navy outline-none";
const err = (e, fb) => toast.error(formatError(e.response?.data?.detail) || fb);

function ThresholdsCard() {
  const [vals, setVals] = useState(null);
  useEffect(() => { api.get("/admin/site-settings/stats").then((r) => setVals(r.data)).catch(() => {}); }, []);
  if (!vals) return null;
  const save = () => api.put("/admin/site-settings/stats", vals).then(() => toast.success("Seuils enregistrés")).catch((e) => err(e, "Échec"));
  return (
    <section className="bg-white rounded-2xl border-2 border-cream-dark p-5 mb-8" data-testid="admin-stats-thresholds">
      <h2 className="font-display text-xl font-extrabold text-navy mb-1 flex items-center gap-2"><BarChart3 className="w-5 h-5" /> Bloc « En chiffres »</h2>
      <p className="text-sm text-navy/70 mb-4">Un compteur n&apos;apparaît qu&apos;à partir de son seuil. Le nombre de questions est toujours réel. Moins de 3 compteurs visibles : bloc masqué.</p>
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
        {STAT_FIELDS.map((f) => (
          <label key={f.key} className="text-sm font-bold text-navy">
            {f.label}
            <input type="number" min={0} value={vals[f.key]} data-testid={`threshold-${f.key}`} className={`${input} mt-1`}
              onChange={(e) => setVals({ ...vals, [f.key]: Math.max(0, Number(e.target.value) || 0) })} />
          </label>
        ))}
      </div>
      <button type="button" onClick={save} data-testid="threshold-save" className="inline-flex items-center gap-2 bg-navy text-white font-bold px-5 py-2 rounded-full hover:bg-terracotta transition-colors">
        <Save className="w-4 h-4" /> Enregistrer
      </button>
    </section>
  );
}

function TestimonialForm({ initial, onSaved, onCancel }) {
  const [f, setF] = useState(initial);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value });
  async function submit(e) {
    e.preventDefault();
    try {
      const body = { text: f.text, first_name: f.first_name, age_role: f.age_role, location: f.location, profile: f.profile, published: f.published };
      if (f.id) await api.put(`/admin/testimonials/${f.id}`, body);
      else await api.post("/admin/testimonials", body);
      toast.success("Témoignage enregistré");
      onSaved();
    } catch (e2) { err(e2, "Échec de l'enregistrement"); }
  }
  return (
    <form onSubmit={submit} className="bg-cream/60 rounded-2xl border-2 border-cream-dark p-4 grid gap-3" data-testid="testimonial-form">
      <textarea required minLength={5} maxLength={600} rows={3} placeholder="Texte du témoignage" value={f.text} onChange={set("text")} className={input} data-testid="testimonial-text" />
      <div className="grid sm:grid-cols-3 gap-3">
        <input required maxLength={40} placeholder="Prénom" value={f.first_name} onChange={set("first_name")} className={input} data-testid="testimonial-first-name" />
        <input maxLength={60} placeholder="Âge ou rôle (ex. 72 ans)" value={f.age_role} onChange={set("age_role")} className={input} data-testid="testimonial-age-role" />
        <input maxLength={80} placeholder="Lieu" value={f.location} onChange={set("location")} className={input} data-testid="testimonial-location" />
      </div>
      <div className="flex items-center gap-4 flex-wrap">
        <select value={f.profile} onChange={set("profile")} className={`${input} w-auto`} data-testid="testimonial-profile">
          {PROFILES.map((p) => <option key={p} value={p}>{p}</option>)}
        </select>
        <label className="inline-flex items-center gap-2 font-bold text-navy">
          <input type="checkbox" checked={f.published} onChange={set("published")} data-testid="testimonial-published" className="w-5 h-5" /> Publié
        </label>
        <button type="submit" className="ml-auto bg-terracotta text-white font-bold px-5 py-2 rounded-full hover:bg-terracotta-dark transition-colors" data-testid="testimonial-save">Enregistrer</button>
        {onCancel && <button type="button" onClick={onCancel} className="text-navy font-bold underline" data-testid="testimonial-cancel">Annuler</button>}
      </div>
    </form>
  );
}

export default function AdminTestimonials() {
  const [items, setItems] = useState([]);
  const [editing, setEditing] = useState(null);
  const load = () => api.get("/admin/testimonials").then((r) => setItems(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);

  const togglePublish = (t) => api.put(`/admin/testimonials/${t.id}`, { ...t, published: !t.published }).then(load).catch((e) => err(e, "Échec"));
  const remove = (t) => window.confirm("Supprimer ce témoignage ?") && api.delete(`/admin/testimonials/${t.id}`).then(load).catch((e) => err(e, "Échec"));
  const published = items.filter((t) => t.published).length;

  return (
    <div className="min-h-screen paper-bg">
      <Navbar />
      <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8" data-testid="admin-testimonials-page">
        <h1 className="font-display text-4xl font-extrabold text-navy mb-2">Accueil : preuves sociales</h1>
        <p className="text-navy/70 mb-8">Témoignages publiés : <b data-testid="testimonials-published-count">{published}</b>. Section masquée s&apos;il n&apos;y en a aucun ; la mention « Déjà adopté… » n&apos;apparaît qu&apos;à partir de 3.</p>
        <ThresholdsCard />
        <section>
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-display text-xl font-extrabold text-navy flex items-center gap-2"><Quote className="w-5 h-5" /> Témoignages</h2>
            {editing === null && (
              <button type="button" onClick={() => setEditing(EMPTY)} data-testid="testimonial-new" className="inline-flex items-center gap-2 bg-navy text-white font-bold px-4 py-2 rounded-full hover:bg-terracotta transition-colors">
                <Plus className="w-4 h-4" /> Nouveau
              </button>
            )}
          </div>
          {editing && <div className="mb-4"><TestimonialForm initial={editing} onSaved={() => { setEditing(null); load(); }} onCancel={() => setEditing(null)} /></div>}
          <ul className="grid gap-3">
            {items.map((t) => (
              <li key={t.id} className="bg-white rounded-2xl border-2 border-cream-dark p-4 flex gap-4 items-start" data-testid={`testimonial-row-${t.id}`}>
                <div className="flex-1 min-w-0">
                  <p className="text-navy mb-1">« {t.text} »</p>
                  <p className="text-sm text-navy/60">{[t.first_name, t.age_role, t.location].filter(Boolean).join(" · ")} · <b>{t.profile}</b></p>
                </div>
                <button type="button" onClick={() => togglePublish(t)} title={t.published ? "Dépublier" : "Publier"} data-testid={`testimonial-toggle-${t.id}`}
                  className={`inline-flex items-center gap-1 text-sm font-bold px-3 py-1.5 rounded-full ${t.published ? "bg-emerald-100 text-emerald-700" : "bg-cream text-navy/60"}`}>
                  {t.published ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />} {t.published ? "Publié" : "Brouillon"}
                </button>
                <button type="button" onClick={() => setEditing(t)} className="text-sm font-bold text-navy underline" data-testid={`testimonial-edit-${t.id}`}>Modifier</button>
                <button type="button" onClick={() => remove(t)} aria-label="Supprimer" data-testid={`testimonial-delete-${t.id}`} className="text-bordeaux"><Trash2 className="w-4 h-4" /></button>
              </li>
            ))}
            {!items.length && <li className="text-navy/60" data-testid="testimonials-empty">Aucun témoignage pour l&apos;instant.</li>}
          </ul>
        </section>
      </main>
    </div>
  );
}
