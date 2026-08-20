import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";
import { api, formatError, BACKEND_URL } from "@/lib/api";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import {
  Lock, Unlock, Check, Trophy, ChevronRight, ChevronLeft, ArrowLeft, Sparkles,
  Loader2, X, RotateCcw, Award,
} from "lucide-react";

/**
 * Parcours — page à paliers d'une catégorie (7 × 20 = 140 questions).
 * 3 états :
 *   - overview  : les 7 paliers, débloqués/verrouillés + best_score
 *   - playing   : quiz de 20 questions du palier choisi
 *   - result    : score, badge "réussi/échec", CTA rejouer / palier suivant
 */
export default function Parcours() {
  const { categoryId } = useParams();
  const navigate = useNavigate();
  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [mode, setMode] = useState("overview"); // overview | playing | result
  const [playState, setPlayState] = useState(null); // {palier, questions, answers, idx}
  const [result, setResult] = useState(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get(`/palier/categories/${categoryId}`);
      setOverview(data);
    } catch (e) {
      toast.error(formatError(e.response?.data?.detail) || "Impossible de charger le parcours");
    } finally {
      setLoading(false);
    }
  }, [categoryId]);

  useEffect(() => { refresh(); }, [refresh]);

  async function startPalier(n) {
    try {
      const { data } = await api.post(`/palier/categories/${categoryId}/${n}/start`);
      setPlayState({
        palier: n,
        label: data.label,
        pass_threshold: data.pass_threshold,
        questions: data.questions,
        answers: {},
        idx: 0,
      });
      setResult(null);
      setMode("playing");
    } catch (e) {
      const status = e.response?.status;
      if (status === 409) {
        toast.error("Stock de questions insuffisant pour ce palier. Un admin doit lancer un top-up.");
      } else if (status === 403) {
        toast.error("Palier précédent non validé.");
      } else {
        toast.error(formatError(e.response?.data?.detail) || "Impossible de démarrer");
      }
    }
  }

  async function submitPalier() {
    if (!playState) return;
    const { palier, questions, answers } = playState;
    const payload = {
      answers: questions.map((q) => ({
        question_id: q.id,
        answer_index: answers[q.id] ?? -1,
      })),
    };
    try {
      const { data } = await api.post(`/palier/categories/${categoryId}/${palier}/submit`, payload);
      setResult(data);
      setMode("result");
      await refresh();
    } catch (e) {
      toast.error(formatError(e.response?.data?.detail) || "Impossible de soumettre");
    }
  }

  function returnToOverview() {
    setPlayState(null);
    setResult(null);
    setMode("overview");
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-cream text-navy">
        <Navbar />
        <div className="max-w-6xl mx-auto p-8 text-center">
          <Loader2 className="w-8 h-8 animate-spin mx-auto text-terracotta" />
        </div>
      </div>
    );
  }
  if (!overview) return null;

  return (
    <div className="min-h-screen bg-cream text-navy" data-testid={`parcours-page-${categoryId}`}>
      <Navbar />
      <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <AnimatePresence mode="wait">
          {mode === "overview" && (
            <motion.div key="overview" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              <OverviewView overview={overview} onStart={startPalier} navigate={navigate} />
            </motion.div>
          )}
          {mode === "playing" && playState && (
            <motion.div key="playing" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              <PlayView
                state={playState}
                setState={setPlayState}
                onSubmit={submitPalier}
                onAbandon={returnToOverview}
              />
            </motion.div>
          )}
          {mode === "result" && result && playState && (
            <motion.div key="result" initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }}>
              <ResultView
                result={result}
                palier={playState.palier}
                label={playState.label}
                onRetry={() => startPalier(playState.palier)}
                onNext={() => startPalier(playState.palier + 1)}
                onBackToOverview={returnToOverview}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </main>
      <Footer />
    </div>
  );
}

// -----------------------------------------------------------------------------
// OVERVIEW
// -----------------------------------------------------------------------------
function OverviewView({ overview, onStart, navigate }) {
  const { category, paliers, pass_threshold, palier_size } = overview;
  const completed = paliers.filter((p) => p.completed).length;
  return (
    <>
      <button
        type="button"
        onClick={() => navigate("/app/dashboard")}
        className="inline-flex items-center gap-1 text-sm font-bold text-navy/60 hover:text-navy mb-4"
        data-testid="parcours-back"
      >
        <ArrowLeft className="w-4 h-4" /> Retour au tableau de bord
      </button>

      <header className="mb-8 flex flex-col sm:flex-row items-start gap-4">
        <div className="w-24 h-24 rounded-2xl overflow-hidden bg-white border-2 border-cream-dark shrink-0">
          {category.mascot_image && (
            <img src={`${BACKEND_URL}${category.mascot_image}`} alt={category.mascot_name} className="w-full h-full object-cover" />
          )}
        </div>
        <div className="flex-1">
          <span className="inline-flex items-center gap-1 bg-terracotta text-white text-xs font-bold uppercase tracking-widest px-3 py-1 rounded-full mb-2">
            <Sparkles className="w-3 h-3" /> Parcours
          </span>
          <h1 className="font-display text-3xl sm:text-4xl font-extrabold">{category.title}</h1>
          <p className="text-navy/70 mt-1">
            7 paliers de {palier_size} questions · seuil de réussite {pass_threshold}/{palier_size}
          </p>
          <p className="text-sm text-navy/50 mt-1">
            <Trophy className="w-3.5 h-3.5 inline mr-1 text-mustard-dark" />
            {completed} palier{completed > 1 ? "s" : ""} sur {paliers.length} validé{completed > 1 ? "s" : ""}
          </p>
        </div>
      </header>

      <div className="grid gap-3">
        {paliers.map((p, i) => <PalierRow key={p.palier} palier={p} onStart={onStart} lastInList={i === paliers.length - 1} />)}
      </div>
    </>
  );
}

function PalierRow({ palier, onStart }) {
  const { palier: n, label, unlocked, completed, best_score, target_size, pass_threshold, stock_available, attempts } = palier;
  const stockOk = stock_available >= target_size;
  const stockBadgeColor = stockOk ? "text-[#2A7350] bg-[#3D9970]/15" : "text-terracotta bg-terracotta/15";
  return (
    <div
      data-testid={`parcours-palier-row-${n}`}
      className={`bg-white rounded-2xl border-2 p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center gap-4 transition ${
        completed ? "border-[#3D9970] shadow-sm"
        : unlocked ? "border-terracotta hover:shadow-warm"
        : "border-cream-dark opacity-60"
      }`}
    >
      <div className={`w-14 h-14 rounded-full flex items-center justify-center shrink-0 font-display text-2xl font-extrabold ${
        completed ? "bg-[#3D9970] text-white" : unlocked ? "bg-terracotta text-white" : "bg-cream-dark text-navy/40"
      }`}>
        {completed ? <Check className="w-6 h-6" strokeWidth={3} /> : n}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <h3 className="font-display text-lg font-extrabold">Palier {n} · {label}</h3>
          {completed && <span className="inline-flex items-center gap-1 bg-[#3D9970] text-white text-[10px] uppercase font-bold px-2 py-0.5 rounded-full">Validé</span>}
          {!unlocked && <span className="inline-flex items-center gap-1 bg-cream-dark text-navy/50 text-[10px] uppercase font-bold px-2 py-0.5 rounded-full">
            <Lock className="w-3 h-3" /> Verrouillé
          </span>}
        </div>
        <p className="text-sm text-navy/60 mt-1">
          {target_size} questions · seuil {pass_threshold}/{target_size}
          {best_score > 0 && ` · meilleur score : ${best_score}/${target_size}`}
          {attempts > 0 && ` · ${attempts} tentative${attempts > 1 ? "s" : ""}`}
        </p>
        {!stockOk && (
          <span className={`inline-flex items-center gap-1 mt-2 text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${stockBadgeColor}`}>
            ⚠ stock {stock_available}/{target_size}
          </span>
        )}
      </div>
      <div className="shrink-0">
        {unlocked ? (
          <button
            type="button"
            onClick={() => onStart(n)}
            disabled={!stockOk}
            data-testid={`parcours-start-${n}`}
            className={`inline-flex items-center gap-2 font-bold px-5 py-3 rounded-full transition min-w-[140px] justify-center ${
              completed
                ? "bg-navy text-cream hover:bg-navy-dark"
                : "bg-terracotta text-white hover:bg-terracotta-dark shadow-warm"
            } disabled:opacity-40 disabled:cursor-not-allowed`}
          >
            {completed ? <><RotateCcw className="w-4 h-4" /> Refaire</>
                       : <><Unlock className="w-4 h-4" /> Commencer</>}
          </button>
        ) : (
          <span className="inline-flex items-center gap-2 bg-cream-dark text-navy/40 font-bold px-5 py-3 rounded-full min-w-[140px] justify-center">
            <Lock className="w-4 h-4" /> Verrouillé
          </span>
        )}
      </div>
    </div>
  );
}

// -----------------------------------------------------------------------------
// PLAY VIEW
// -----------------------------------------------------------------------------
function PlayView({ state, setState, onSubmit, onAbandon }) {
  const { palier, label, pass_threshold, questions, answers, idx } = state;
  const q = questions[idx];
  const answered = Object.keys(answers).length;
  const total = questions.length;
  const allAnswered = answered === total;

  function selectAnswer(qid, i) {
    setState((s) => ({ ...s, answers: { ...s.answers, [qid]: i } }));
  }
  function next() { if (idx < total - 1) setState((s) => ({ ...s, idx: s.idx + 1 })); }
  function prev() { if (idx > 0) setState((s) => ({ ...s, idx: s.idx - 1 })); }

  const chosen = answers[q.id];

  return (
    <div data-testid="parcours-play">
      <div className="flex items-center justify-between mb-4">
        <button
          type="button"
          onClick={() => { if (window.confirm("Abandonner le palier ? Vos réponses seront perdues.")) onAbandon(); }}
          data-testid="parcours-abandon"
          className="inline-flex items-center gap-1 text-sm font-bold text-navy/60 hover:text-navy"
        >
          <X className="w-4 h-4" /> Quitter
        </button>
        <div className="text-sm font-bold text-navy/70">
          Palier {palier} · {label}
        </div>
      </div>

      {/* Progress */}
      <div className="mb-6">
        <div className="flex items-center justify-between text-xs text-navy/60 mb-1">
          <span>Question {idx + 1} / {total}</span>
          <span>{answered}/{total} répondues · seuil {pass_threshold}/{total}</span>
        </div>
        <div className="w-full h-2 rounded-full bg-cream-dark overflow-hidden">
          <div className="h-full bg-terracotta transition-all" style={{ width: `${((idx + 1) / total) * 100}%` }} />
        </div>
      </div>

      <motion.div
        key={q.id}
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        className="bg-white rounded-3xl border-2 border-cream-dark p-6 sm:p-8 mb-4"
        data-testid="parcours-question"
      >
        <h2 className="font-display text-2xl font-extrabold text-navy mb-6">{q.question}</h2>
        <div className="grid gap-3">
          {q.options.map((opt, i) => {
            const selected = chosen === i;
            return (
              <button
                key={i}
                type="button"
                onClick={() => selectAnswer(q.id, i)}
                data-testid={`parcours-option-${i}`}
                className={`text-left flex items-center gap-3 p-4 rounded-2xl border-2 font-bold transition ${
                  selected
                    ? "border-terracotta bg-terracotta/10 text-navy"
                    : "border-cream-dark bg-white hover:border-navy/40 text-navy/80"
                }`}
              >
                <span className={`w-8 h-8 rounded-full flex items-center justify-center text-sm shrink-0 ${
                  selected ? "bg-terracotta text-white" : "bg-cream text-navy/60"
                }`}>
                  {String.fromCharCode(65 + i)}
                </span>
                <span className="flex-1">{opt}</span>
              </button>
            );
          })}
        </div>
      </motion.div>

      <div className="flex items-center justify-between gap-3">
        <button
          type="button"
          onClick={prev}
          disabled={idx === 0}
          data-testid="parcours-prev"
          className="inline-flex items-center gap-1 bg-white border-2 border-cream-dark text-navy font-bold px-4 py-3 rounded-full hover:border-navy/40 disabled:opacity-40 transition"
        >
          <ChevronLeft className="w-5 h-5" /> Précédente
        </button>
        {idx < total - 1 ? (
          <button
            type="button"
            onClick={next}
            data-testid="parcours-next"
            className="inline-flex items-center gap-1 bg-navy text-cream font-bold px-5 py-3 rounded-full hover:bg-navy-dark transition"
          >
            Suivante <ChevronRight className="w-5 h-5" />
          </button>
        ) : (
          <button
            type="button"
            onClick={onSubmit}
            disabled={!allAnswered}
            data-testid="parcours-submit"
            className="inline-flex items-center gap-2 bg-terracotta text-white font-bold px-6 py-3 rounded-full hover:bg-terracotta-dark shadow-warm disabled:opacity-50 transition"
          >
            <Check className="w-5 h-5" /> Valider mes réponses ({answered}/{total})
          </button>
        )}
      </div>
    </div>
  );
}

// -----------------------------------------------------------------------------
// RESULT VIEW
// -----------------------------------------------------------------------------
function ResultView({ result, palier, label, onRetry, onNext, onBackToOverview }) {
  const { score, total, passed, best_score, next_palier_unlocked, next_palier } = result;
  const pct = Math.round((score / total) * 100);
  return (
    <div className="text-center max-w-2xl mx-auto" data-testid="parcours-result">
      <div className={`w-24 h-24 rounded-full flex items-center justify-center mx-auto mb-6 ${
        passed ? "bg-[#3D9970] text-white" : "bg-terracotta text-white"
      }`}>
        {passed ? <Award className="w-12 h-12" /> : <RotateCcw className="w-12 h-12" />}
      </div>
      <h1 className="font-display text-4xl font-extrabold mb-2">
        {passed ? "Palier validé !" : "Pas encore, ne lâchez pas !"}
      </h1>
      <p className="text-navy/70 mb-6">
        Palier {palier} · {label}
      </p>
      <div className="bg-white border-2 border-cream-dark rounded-3xl p-8 mb-6">
        <div className="font-display text-6xl font-extrabold text-bordeaux mb-1" data-testid="parcours-result-score">
          {score} / {total}
        </div>
        <div className="text-navy/60">{pct}%</div>
        {best_score > score && (
          <div className="mt-3 text-sm text-navy/60">
            Meilleur score : <strong>{best_score}/{total}</strong>
          </div>
        )}
      </div>

      {passed ? (
        <div className="bg-[#3D9970]/10 border-2 border-[#3D9970]/40 rounded-2xl p-4 mb-6">
          <p className="text-navy font-bold">
            <Sparkles className="w-4 h-4 inline mr-1 text-[#2A7350]" />
            {next_palier_unlocked
              ? `Bravo, le palier ${next_palier} est débloqué !`
              : "Vous avez terminé le parcours de cette catégorie ! 🎉"}
          </p>
        </div>
      ) : (
        <div className="bg-terracotta/10 border-2 border-terracotta/40 rounded-2xl p-4 mb-6">
          <p className="text-navy">
            Il vous fallait <strong>{result?.pass_threshold ?? 14}/{total}</strong> pour valider le palier.
            Rejouez le même palier avec les mêmes questions pour améliorer votre score.
          </p>
        </div>
      )}

      <div className="flex flex-col sm:flex-row gap-3 justify-center">
        <button
          type="button"
          onClick={onRetry}
          data-testid="parcours-result-retry"
          className="inline-flex items-center justify-center gap-2 bg-white border-2 border-navy text-navy font-bold px-5 py-3 rounded-full hover:bg-navy hover:text-cream transition"
        >
          <RotateCcw className="w-4 h-4" /> {passed ? "Rejouer ce palier" : "Réessayer"}
        </button>
        {next_palier_unlocked && (
          <button
            type="button"
            onClick={onNext}
            data-testid="parcours-result-next"
            className="inline-flex items-center justify-center gap-2 bg-terracotta text-white font-bold px-5 py-3 rounded-full hover:bg-terracotta-dark shadow-warm transition"
          >
            Palier {next_palier} <ChevronRight className="w-4 h-4" />
          </button>
        )}
        <button
          type="button"
          onClick={onBackToOverview}
          data-testid="parcours-result-overview"
          className="inline-flex items-center justify-center gap-2 bg-cream border-2 border-cream-dark text-navy font-bold px-5 py-3 rounded-full hover:border-navy/40 transition"
        >
          Vue d&apos;ensemble
        </button>
      </div>
    </div>
  );
}
