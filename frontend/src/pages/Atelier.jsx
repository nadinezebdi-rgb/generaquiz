import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";
import { api, formatError } from "@/lib/api";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import {
  BookOpen, ArrowRight, ArrowLeft, Feather, Loader2,
  Sparkles, CheckCircle2, ChevronRight, History,
} from "lucide-react";

/**
 * Atelier Mémoire — 2-step flow.
 *   1. Pick a theme card (decade / childhood / family).
 *   2. Answer 5 open-ended prompts in sequence. Save all at once at the end.
 *
 * No score, no time limit — the goal is to trigger memories.
 */

export default function Atelier() {
  const navigate = useNavigate();
  const [themes, setThemes] = useState([]);
  const [selected, setSelected] = useState(null);  // theme object with prompts
  const [answers, setAnswers] = useState({});      // {prompt_id: text}
  const [step, setStep] = useState(0);             // 0..4 prompt index, 5 = review
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(null);          // {xp_gained, awarded_badges}

  useEffect(() => {
    api.get("/atelier/themes").then((r) => setThemes(r.data)).catch(() => {});
  }, []);

  async function chooseTheme(t) {
    setLoading(true);
    try {
      const { data } = await api.get(`/atelier/themes/${t.id}`);
      setSelected(data);
      setStep(0);
      setAnswers({});
      setDone(null);
    } catch (e) {
      toast.error(formatError(e.response?.data?.detail) || "Impossible de charger l'atelier");
    } finally {
      setLoading(false);
    }
  }

  async function submitSession() {
    if (!selected) return;
    setSubmitting(true);
    try {
      const payload = {
        theme: selected.id,
        answers: Object.entries(answers)
          .filter(([, v]) => v && v.trim())
          .map(([prompt_id, answer]) => ({ prompt_id, answer: answer.trim() })),
      };
      if (payload.answers.length === 0) {
        toast.error("Répondez à au moins un souvenir avant de sauvegarder.");
        setSubmitting(false);
        return;
      }
      const { data } = await api.post("/atelier/sessions", payload);
      setDone(data);
    } catch (e) {
      toast.error(formatError(e.response?.data?.detail) || "Impossible de sauvegarder");
    } finally {
      setSubmitting(false);
    }
  }

  // ---------- Selection view ----------
  if (!selected) {
    return (
      <div className="min-h-screen paper-bg">
        <Navbar variant="app" />
        <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
          <div className="text-center max-w-2xl mx-auto mb-10">
            <span className="inline-flex items-center gap-2 bg-bordeaux text-cream font-bold px-4 py-1.5 rounded-full text-xs uppercase tracking-wider mb-4">
              <Feather className="w-3.5 h-3.5" /> Nouveau — Atelier Mémoire
            </span>
            <h1 className="font-display text-4xl sm:text-5xl font-extrabold text-navy mb-3" data-testid="atelier-title">
              Écrivez vos souvenirs, <span className="text-terracotta italic">un par un.</span>
            </h1>
            <p className="text-navy/70 text-lg">
              Cinq questions ouvertes par thème. Pas de score, pas de chrono — juste vous et votre mémoire.
              Vos souvenirs sont sauvegardés dans votre carnet privé.
            </p>
            <div className="mt-5">
              <Link
                to="/app/atelier/mes-souvenirs"
                data-testid="atelier-view-entries"
                className="inline-flex items-center gap-2 text-navy underline decoration-terracotta decoration-2 underline-offset-4 hover:text-terracotta transition text-sm font-bold"
              >
                <History className="w-4 h-4" /> Voir mes souvenirs déjà écrits
              </Link>
            </div>
          </div>

          <div className="grid md:grid-cols-3 gap-4">
            {themes.map((t, i) => (
              <motion.button
                type="button"
                key={t.id}
                onClick={() => chooseTheme(t)}
                disabled={loading}
                data-testid={`atelier-theme-${t.id}`}
                initial={{ opacity: 0, y: 14 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }}
                whileHover={{ y: -4 }}
                className="bg-white border-2 border-cream-dark rounded-[24px] p-5 text-left hover:border-terracotta transition disabled:opacity-50"
              >
                <div className="text-4xl mb-2">{t.emoji}</div>
                <div className="font-display text-xl font-extrabold text-navy mb-1">{t.label}</div>
                <div className="text-sm text-navy/70 mb-3">{t.description}</div>
                <div className="flex items-center justify-between text-xs text-navy/60">
                  <span>{t.prompt_count} questions</span>
                  <span className="inline-flex items-center gap-1 text-terracotta font-bold">
                    Commencer <ArrowRight className="w-4 h-4" />
                  </span>
                </div>
              </motion.button>
            ))}
          </div>

          <div className="mt-10 bg-cream border-2 border-cream-dark rounded-2xl p-4 md:p-6 flex items-start gap-3">
            <Sparkles className="w-5 h-5 text-terracotta shrink-0 mt-0.5" />
            <div className="text-sm text-navy/80">
              <strong className="text-navy">Astuce famille :</strong> lisez à voix haute chaque question à
              votre parent, tapez sa réponse. Vous obtenez un carnet de mémoires que la famille peut
              conserver. Chaque atelier terminé rapporte <strong>+25 points</strong>.
            </div>
          </div>
        </main>
        <Footer />
      </div>
    );
  }

  // ---------- Completion view ----------
  if (done) {
    return (
      <div className="min-h-screen paper-bg">
        <Navbar variant="app" />
        <main className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 py-16 text-center">
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-white border-2 border-cream-dark rounded-[32px] p-8 md:p-10"
            data-testid="atelier-done"
          >
            <div className="w-16 h-16 mx-auto rounded-full bg-[#3D9970]/15 flex items-center justify-center mb-4">
              <CheckCircle2 className="w-8 h-8 text-[#3D9970]" />
            </div>
            <h2 className="font-display text-3xl font-extrabold text-navy mb-2">
              Bravo, atelier terminé !
            </h2>
            <p className="text-navy/70 mb-6">
              {done.saved} souvenir(s) sauvegardé(s) · +{done.xp_gained} points
            </p>
            {done.awarded_badges?.length > 0 && (
              <div className="mb-6" data-testid="atelier-badges-awarded">
                <div className="text-sm font-bold text-terracotta uppercase tracking-wider mb-3">
                  Badge{done.awarded_badges.length > 1 ? "s" : ""} débloqué{done.awarded_badges.length > 1 ? "s" : ""}
                </div>
                <div className="flex justify-center gap-3 flex-wrap">
                  {done.awarded_badges.map((b) => (
                    <div key={b.id} className="bg-cream border-2 border-terracotta rounded-2xl p-3 min-w-[140px]">
                      <div className="text-3xl mb-1">{b.emoji}</div>
                      <div className="font-bold text-navy text-sm">{b.title}</div>
                      <div className="text-xs text-navy/60">{b.desc}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
            <div className="flex gap-3 justify-center flex-wrap">
              <button
                type="button"
                onClick={() => { setSelected(null); setDone(null); }}
                data-testid="atelier-cta-new"
                className="inline-flex items-center gap-2 bg-terracotta hover:bg-terracotta-dark text-white font-bold px-5 py-3 rounded-full transition"
              >
                <BookOpen className="w-4 h-4" /> Autre atelier
              </button>
              <button
                type="button"
                onClick={() => navigate("/app/atelier/mes-souvenirs")}
                data-testid="atelier-cta-view"
                className="inline-flex items-center gap-2 bg-white border-2 border-navy text-navy hover:bg-navy hover:text-cream font-bold px-5 py-3 rounded-full transition"
              >
                Voir mon carnet
              </button>
            </div>
          </motion.div>
        </main>
        <Footer />
      </div>
    );
  }

  // ---------- Prompt-by-prompt view ----------
  const prompt = selected.prompts[step];
  const isLast = step >= selected.prompts.length - 1;
  const answered = Object.keys(answers).filter((k) => answers[k]?.trim()).length;
  const answerText = answers[prompt?.id] || "";

  return (
    <div className="min-h-screen paper-bg">
      <Navbar variant="app" />
      <main className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <div className="flex items-center justify-between mb-3">
          <button
            type="button"
            onClick={() => setSelected(null)}
            data-testid="atelier-back"
            className="inline-flex items-center gap-1 text-navy/70 hover:text-navy font-bold text-sm"
          >
            <ArrowLeft className="w-4 h-4" /> Changer de thème
          </button>
          <div className="text-sm text-navy/60" data-testid="atelier-progress">
            Question {step + 1} / {selected.prompts.length}
          </div>
        </div>

        <div className="h-2 bg-cream-dark rounded-full overflow-hidden mb-6">
          <div
            className="h-full bg-terracotta transition-all"
            style={{ width: `${((step + 1) / selected.prompts.length) * 100}%` }}
          />
        </div>

        <div className="bg-white border-2 border-cream-dark rounded-[28px] p-6 md:p-8">
          <div className="flex items-center gap-3 mb-4">
            <span className="text-3xl">{selected.emoji}</span>
            <div>
              <div className="text-xs uppercase tracking-wider text-terracotta font-bold">{selected.label}</div>
              <div className="text-xs text-navy/60">Prenez le temps qu&apos;il faut.</div>
            </div>
          </div>
          <AnimatePresence mode="wait">
            <motion.div
              key={prompt.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.3 }}
            >
              <h2 className="font-display text-2xl md:text-3xl font-extrabold text-navy mb-5" data-testid="atelier-prompt">
                {prompt.text}
              </h2>
              <textarea
                value={answerText}
                onChange={(e) => setAnswers((a) => ({ ...a, [prompt.id]: e.target.value }))}
                placeholder="Racontez librement…"
                maxLength={1500}
                data-testid="atelier-answer-input"
                className="w-full min-h-[180px] border-2 border-cream-dark rounded-2xl p-4 focus:outline-none focus:border-terracotta transition text-navy"
              />
              <div className="text-right text-xs text-navy/50 mt-1">
                {answerText.length} / 1500
              </div>
            </motion.div>
          </AnimatePresence>

          <div className="mt-6 flex items-center justify-between gap-3 flex-wrap">
            <button
              type="button"
              onClick={() => setStep((s) => Math.max(0, s - 1))}
              disabled={step === 0}
              data-testid="atelier-prev"
              className="inline-flex items-center gap-1 text-navy/70 hover:text-navy font-bold text-sm disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <ArrowLeft className="w-4 h-4" /> Précédent
            </button>
            {isLast ? (
              <button
                type="button"
                onClick={submitSession}
                disabled={submitting}
                data-testid="atelier-submit"
                className="inline-flex items-center gap-2 bg-terracotta hover:bg-terracotta-dark text-white font-bold px-6 py-3 rounded-full shadow-warm transition disabled:opacity-60"
              >
                {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
                Sauvegarder mes souvenirs ({answered})
              </button>
            ) : (
              <button
                type="button"
                onClick={() => setStep((s) => Math.min(selected.prompts.length - 1, s + 1))}
                data-testid="atelier-next"
                className="inline-flex items-center gap-2 bg-navy hover:bg-navy-dark text-cream font-bold px-5 py-3 rounded-full transition"
              >
                Suivant <ChevronRight className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
