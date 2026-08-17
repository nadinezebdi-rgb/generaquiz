import { useEffect, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import { toast } from "sonner";
import { api, formatError } from "@/lib/api";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { ArrowLeft, Users, BookOpen, Sparkles, Play, Save, Loader2 } from "lucide-react";

/** EhpadNewSession — sélection du support (quiz OU prompt Livre) + résidents présents. */
export function EhpadNewSession() {
  const [kind, setKind] = useState("quiz"); // "quiz" | "prompt"
  const [categories, setCategories] = useState([]);
  const [chapters, setChapters] = useState([]);
  const [residents, setResidents] = useState([]);
  const [ref, setRef] = useState({ id: "", title: "" });
  const [selectedRes, setSelectedRes] = useState([]);
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    api.get("/categories").then((r) => setCategories(r.data)).catch(() => {});
    api.get("/livre/chapters").then((r) => setChapters(r.data)).catch(() => {});
    api.get("/ehpad/residents").then((r) => setResidents(r.data)).catch(() => {});
  }, []);

  function toggleResident(id) {
    setSelectedRes((prev) => prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]);
  }

  async function launch() {
    if (!ref.id || !ref.title) { toast.error("Choisissez un support"); return; }
    if (selectedRes.length === 0) { toast.error("Sélectionnez au moins un résident"); return; }
    setSaving(true);
    try {
      const { data } = await api.post("/ehpad/sessions", {
        kind, ref_id: ref.id, ref_title: ref.title,
        resident_ids: selectedRes, notes,
      });
      toast.success("Séance créée");
      navigate(`/app/ehpad/seance/${data.id}`);
    } catch (e) {
      toast.error(formatError(e.response?.data?.detail) || "Erreur");
    } finally { setSaving(false); }
  }

  return (
    <div className="min-h-screen paper-bg">
      <Navbar variant="app" />
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Link to="/app/ehpad" className="inline-flex items-center gap-1 text-navy/70 hover:text-navy mb-4 text-sm">
          <ArrowLeft className="w-4 h-4" /> Retour au tableau de bord
        </Link>
        <h1 className="font-display text-3xl font-extrabold text-navy mb-6">🎬 Nouvelle séance collective</h1>

        <section className="bg-white rounded-2xl border-2 border-cream-dark p-5 mb-5">
          <h2 className="font-bold text-navy mb-3">1. Quel support ?</h2>
          <div className="flex gap-2 mb-4">
            <button type="button" onClick={() => { setKind("quiz"); setRef({ id: "", title: "" }); }}
              data-testid="ehpad-kind-quiz"
              className={`px-4 py-2 rounded-full font-bold text-sm border-2 transition ${
                kind === "quiz" ? "bg-terracotta text-white border-terracotta" : "bg-white text-navy border-cream-dark"
              }`}>🎯 Quiz thématique</button>
            <button type="button" onClick={() => { setKind("prompt"); setRef({ id: "", title: "" }); }}
              data-testid="ehpad-kind-prompt"
              className={`px-4 py-2 rounded-full font-bold text-sm border-2 transition ${
                kind === "prompt" ? "bg-terracotta text-white border-terracotta" : "bg-white text-navy border-cream-dark"
              }`}>📖 Souvenir guidé</button>
          </div>
          {kind === "quiz" ? (
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-2 max-h-64 overflow-y-auto">
              {categories.map((c) => (
                <button key={c.slug} type="button"
                  onClick={() => setRef({ id: c.slug, title: c.title })}
                  data-testid={`ehpad-pick-quiz-${c.slug}`}
                  className={`text-left p-3 rounded-lg border-2 transition text-sm ${
                    ref.id === c.slug ? "border-terracotta bg-terracotta/10" : "border-cream-dark hover:border-terracotta"
                  }`}>
                  <span className="font-bold text-navy">{c.emoji} {c.title}</span>
                </button>
              ))}
            </div>
          ) : (
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {chapters.map((c) => (
                <div key={c.id}>
                  <div className="text-xs font-bold text-navy/70 mt-2">{c.emoji} {c.label}</div>
                  {[1, 2, 3, 4, 5].map((i) => (
                    <button key={i} type="button"
                      onClick={() => setRef({ id: `${c.id}_p${i}`, title: `${c.emoji} ${c.label} — prompt ${i}` })}
                      className={`w-full text-left p-2 pl-6 rounded-lg text-sm transition ${
                        ref.id === `${c.id}_p${i}` ? "bg-terracotta/10 text-terracotta font-bold" : "text-navy/70 hover:bg-cream"
                      }`}>
                      Prompt {i}
                    </button>
                  ))}
                </div>
              ))}
            </div>
          )}
          {ref.id && <p className="mt-3 text-sm text-terracotta font-bold">✓ Choisi : {ref.title}</p>}
        </section>

        <section className="bg-white rounded-2xl border-2 border-cream-dark p-5 mb-5">
          <h2 className="font-bold text-navy mb-3">2. Qui participe ?</h2>
          {residents.length === 0 ? (
            <p className="text-navy/60 text-sm">Aucun résident enregistré. <Link to="/app/ehpad" className="text-terracotta font-bold">Ajoutez-en ici →</Link></p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {residents.map((r) => (
                <button key={r.id} type="button" onClick={() => toggleResident(r.id)}
                  data-testid={`ehpad-pick-resident-${r.id}`}
                  className={`px-3 py-1.5 rounded-full text-sm font-bold border-2 transition ${
                    selectedRes.includes(r.id) ? "bg-navy text-cream border-navy" : "bg-white text-navy border-cream-dark hover:border-navy"
                  }`}>
                  {r.first_name} {r.initial}
                </button>
              ))}
            </div>
          )}
        </section>

        <section className="bg-white rounded-2xl border-2 border-cream-dark p-5 mb-5">
          <h2 className="font-bold text-navy mb-3">3. Notes (optionnel)</h2>
          <textarea value={notes} onChange={(e) => setNotes(e.target.value)}
            placeholder="Contexte de la séance, ambiance…" maxLength={1000}
            className="w-full p-3 rounded-lg border-2 border-cream-dark focus:border-terracotta outline-none min-h-[80px]" />
        </section>

        <button onClick={launch} disabled={saving} data-testid="ehpad-session-launch"
          className="inline-flex items-center gap-2 bg-terracotta text-white font-bold px-6 py-3 rounded-full hover:bg-terracotta-dark disabled:opacity-50 transition shadow-warm">
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
          Lancer la séance
        </button>
      </main>
      <Footer />
    </div>
  );
}


/** EhpadSessionView — saisie des réponses par résident. */
export function EhpadSessionView() {
  const { sessionId } = useParams();
  const [session, setSession] = useState(null);
  const [dirty, setDirty] = useState({});

  useEffect(() => { load(); }, [sessionId]);

  async function load() {
    try {
      const { data } = await api.get(`/ehpad/sessions/${sessionId}`);
      setSession(data);
    } catch (e) { toast.error("Séance introuvable"); }
  }

  function existingResponse(residentId) {
    return session?.responses?.find((r) => r.resident_id === residentId);
  }

  async function saveResponse(residentId, patch) {
    const current = existingResponse(residentId) || {};
    const merged = { ...current, ...patch };
    try {
      await api.post(`/ehpad/sessions/${sessionId}/responses`, {
        resident_id: residentId,
        score: session.kind === "quiz" ? (merged.score ?? null) : null,
        memory_text: session.kind === "prompt" ? (merged.memory_text || "") : "",
      });
      setDirty((prev) => ({ ...prev, [residentId]: false }));
      toast.success("Réponse enregistrée", { duration: 1500 });
      load();
    } catch (e) { toast.error("Erreur"); }
  }

  if (!session) return null;

  return (
    <div className="min-h-screen paper-bg">
      <Navbar variant="app" />
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Link to="/app/ehpad" className="inline-flex items-center gap-1 text-navy/70 hover:text-navy mb-4 text-sm">
          <ArrowLeft className="w-4 h-4" /> Retour
        </Link>
        <header className="mb-6">
          <span className="inline-flex items-center gap-2 bg-bordeaux text-cream font-bold px-3 py-1 rounded-full text-xs uppercase tracking-wider mb-2">
            {session.kind === "quiz" ? "🎯 Séance Quiz" : "📖 Séance Souvenir"}
          </span>
          <h1 className="font-display text-3xl font-extrabold text-navy" data-testid="ehpad-session-title">{session.ref_title}</h1>
          <p className="text-navy/70 text-sm mt-1">
            {new Date(session.created_at).toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" })} · {session.residents.length} résident(s)
          </p>
        </header>

        <div className="space-y-4">
          {session.residents.map((r) => {
            const resp = existingResponse(r.id);
            return (
              <div key={r.id} className="bg-white rounded-2xl border-2 border-cream-dark p-5" data-testid={`ehpad-response-${r.id}`}>
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <div className="font-display text-lg font-bold text-navy">{r.first_name} {r.initial}</div>
                    {r.age && <div className="text-xs text-navy/60">{r.age} ans</div>}
                  </div>
                  {resp && <span className="text-xs bg-mustard/30 text-navy px-2 py-1 rounded-full font-bold">✓ enregistrée</span>}
                </div>
                {session.kind === "quiz" ? (
                  <div className="flex gap-1" data-testid={`ehpad-score-picker-${r.id}`}>
                    {[0, 1, 2, 3, 4, 5].map((s) => (
                      <button key={s} type="button" onClick={() => saveResponse(r.id, { score: s })}
                        className={`flex-1 py-2 rounded-lg font-bold border-2 transition ${
                          resp?.score === s ? "bg-terracotta text-white border-terracotta" : "bg-white text-navy border-cream-dark hover:border-terracotta"
                        }`}>
                        {s}/5
                      </button>
                    ))}
                  </div>
                ) : (
                  <div>
                    <textarea defaultValue={resp?.memory_text || ""} onChange={() => setDirty((p) => ({ ...p, [r.id]: true }))}
                      onBlur={(e) => saveResponse(r.id, { memory_text: e.target.value })}
                      placeholder="Notez le souvenir raconté par ce résident…"
                      maxLength={2000}
                      className="w-full p-3 rounded-lg border-2 border-cream-dark focus:border-terracotta outline-none min-h-[100px]" />
                    {dirty[r.id] && <div className="text-xs text-navy/60 mt-1">Cliquez ailleurs pour enregistrer automatiquement</div>}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </main>
      <Footer />
    </div>
  );
}
