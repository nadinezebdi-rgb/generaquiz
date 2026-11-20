import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { Check, ChevronLeft, ChevronRight, Loader2, X } from "lucide-react";
import { api, formatError } from "@/lib/api";

function optionClass(state) {
  if (state === "correct") return "border-[#3D9970] bg-[#3D9970]/10 text-navy";
  if (state === "wrong") return "border-[#D9534F] bg-[#D9534F]/10 text-navy";
  if (state === "selected") return "border-terracotta bg-terracotta/10 text-navy";
  if (state === "dim") return "border-cream-dark bg-white text-navy/50";
  return "border-cream-dark bg-white hover:border-navy/40 text-navy/80";
}

function OptionButton({ label, text, state, disabled, onClick, testid }) {
  const icon = state === "correct" ? <Check className="w-5 h-5 text-[#2A7350]" strokeWidth={3} aria-hidden="true" />
    : state === "wrong" ? <X className="w-5 h-5 text-[#B52B27]" strokeWidth={3} aria-hidden="true" /> : null;
  const sr = state === "correct" ? " (bonne réponse)" : state === "wrong" ? " (votre réponse, fausse)" : "";
  return (
    <button type="button" onClick={onClick} disabled={disabled} data-testid={testid} aria-pressed={state === "selected"}
      className={`text-left flex items-center gap-3 p-4 rounded-2xl border-2 font-bold transition-colors disabled:cursor-default ${optionClass(state)}`}>
      <span className={`w-8 h-8 rounded-full flex items-center justify-center text-sm shrink-0 ${
        state === "selected" ? "bg-terracotta text-white" : state === "correct" ? "bg-[#3D9970] text-white"
        : state === "wrong" ? "bg-[#D9534F] text-white" : "bg-cream text-navy/60"}`}>{label}</span>
      <span className="flex-1">{text}<span className="sr-only">{sr}</span></span>
      {icon}
    </button>
  );
}

function Feedback({ fb }) {
  const ref = useRef(null);
  useEffect(() => { ref.current?.scrollIntoView?.({ behavior: "smooth", block: "nearest" }); }, []);
  return (
    <div ref={ref} aria-live="polite" data-testid="parcours-feedback"
      className={`rounded-2xl p-4 sm:p-5 mt-5 border-2 ${fb.correct ? "bg-[#3D9970]/10 border-[#3D9970]/40" : "bg-[#D9534F]/10 border-[#D9534F]/40"}`}>
      <p className="font-display text-2xl font-bold text-navy" data-testid="parcours-feedback-verdict">
        {fb.correct ? "✅ Bonne réponse !" : "❌ Pas tout à fait."}
      </p>
      {!fb.correct && (
        <p className="text-navy text-lg mt-1" data-testid="parcours-feedback-correct">
          La bonne réponse était : <strong>{fb.correct_answer}</strong>
        </p>
      )}
      {fb.explanation && (
        <p className="text-navy/80 text-lg leading-relaxed mt-3 bg-white/70 rounded-xl p-3 sm:p-4" data-testid="parcours-feedback-explanation">
          {fb.explanation}
        </p>
      )}
    </div>
  );
}

/** Palier joué question par question : validation verrouillée côté serveur + correction immédiate. */
export function PlayView({ state, setState, categoryId, onSubmit, onAbandon }) {
  const { palier, label, pass_threshold, questions, idx, feedback } = state;
  const [selected, setSelected] = useState(null);
  const [busy, setBusy] = useState(false);
  const q = questions[idx];
  const total = questions.length;
  const fb = feedback[q.id];
  const validated = Object.keys(feedback).length;
  const goodSoFar = Object.values(feedback).filter((f) => f.correct).length;

  async function validate() {
    setBusy(true);
    try {
      const { data } = await api.post(`/palier/categories/${categoryId}/${palier}/answer`, { question_id: q.id, answer: selected });
      setState((s) => ({ ...s, feedback: { ...s.feedback, [q.id]: data } }));
    } catch (e) {
      toast.error(formatError(e.response?.data?.detail) || "Impossible de valider la réponse");
    } finally {
      setBusy(false);
    }
  }
  function go(delta) { setSelected(null); setState((s) => ({ ...s, idx: s.idx + delta })); }
  async function finish() { setBusy(true); await onSubmit(); setBusy(false); }

  const stateFor = (i) => {
    if (!fb) return selected === i ? "selected" : "idle";
    if (i === fb.correct_index) return "correct";
    if (i === fb.answer) return "wrong";
    return "dim";
  };

  return (
    <div data-testid="parcours-play">
      <div className="flex items-center justify-between mb-4">
        <button type="button" data-testid="parcours-abandon"
          onClick={() => { if (window.confirm("Abandonner le palier ? Vos réponses seront perdues.")) onAbandon(); }}
          className="inline-flex items-center gap-1 text-sm font-bold text-navy/60 hover:text-navy">
          <X className="w-4 h-4" /> Quitter
        </button>
        <div className="text-sm font-bold text-navy/70">Palier {palier} · {label}</div>
      </div>

      <div className="mb-6">
        <div className="flex items-center justify-between gap-2 flex-wrap text-xs text-navy/60 mb-1">
          <span>Question {idx + 1} / {total}</span>
          <span data-testid="parcours-progress-count">{goodSoFar} bonne{goodSoFar > 1 ? "s" : ""} réponse{goodSoFar > 1 ? "s" : ""} · {validated}/{total} validées · seuil {pass_threshold}/{total}</span>
        </div>
        <div className="w-full h-2 rounded-full bg-cream-dark overflow-hidden">
          <div className="h-full bg-terracotta transition-all" style={{ width: `${((idx + 1) / total) * 100}%` }} />
        </div>
      </div>

      <motion.div key={q.id} initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }}
        className="bg-white rounded-3xl border-2 border-cream-dark p-4 sm:p-8 mb-4" data-testid="parcours-question">
        <h2 className="font-display text-2xl font-extrabold text-navy mb-6">{q.question}</h2>
        <div className="grid gap-3">
          {q.options.map((opt, i) => (
            <OptionButton key={i} label={String.fromCharCode(65 + i)} text={opt} state={stateFor(i)}
              disabled={Boolean(fb) || busy} onClick={() => setSelected(i)} testid={`parcours-option-${i}`} />
          ))}
        </div>
        {fb && <Feedback fb={fb} />}
      </motion.div>

      <div className="flex items-center justify-between gap-3 flex-wrap">
        <button type="button" onClick={() => go(-1)} disabled={idx === 0 || busy} data-testid="parcours-prev"
          className="inline-flex items-center gap-1 bg-white border-2 border-cream-dark text-navy font-bold px-4 py-3 rounded-full hover:border-navy/40 disabled:opacity-40 transition-colors">
          <ChevronLeft className="w-5 h-5" /> Précédente
        </button>
        {!fb ? (
          <button type="button" onClick={validate} disabled={selected === null || busy} data-testid="parcours-validate"
            className="inline-flex items-center gap-2 bg-terracotta text-white font-bold px-6 py-3 rounded-full hover:bg-terracotta-dark shadow-warm disabled:opacity-50 transition-colors">
            {busy ? <Loader2 className="w-5 h-5 animate-spin" /> : <Check className="w-5 h-5" />} Valider ma réponse
          </button>
        ) : idx < total - 1 ? (
          <button type="button" onClick={() => go(1)} data-testid="parcours-next"
            className="inline-flex items-center gap-1 bg-navy text-cream font-bold px-5 py-3 rounded-full hover:bg-navy-dark transition-colors">
            Question suivante <ChevronRight className="w-5 h-5" />
          </button>
        ) : (
          <button type="button" onClick={finish} disabled={busy} data-testid="parcours-submit"
            className="inline-flex items-center gap-2 bg-terracotta text-white font-bold px-6 py-3 rounded-full hover:bg-terracotta-dark shadow-warm disabled:opacity-50 transition-colors">
            {busy ? <Loader2 className="w-5 h-5 animate-spin" /> : <Check className="w-5 h-5" />} Voir mon résultat
          </button>
        )}
      </div>
    </div>
  );
}

export function MistakesReview({ mistakes }) {
  return (
    <section className="text-left mt-10" data-testid="parcours-mistakes">
      <h2 className="font-display text-2xl font-extrabold text-navy mb-4">Revoir mes erreurs</h2>
      {mistakes.length === 0 ? (
        <p className="bg-[#3D9970]/10 border-2 border-[#3D9970]/40 rounded-2xl p-4 text-lg font-bold text-navy" data-testid="parcours-mistakes-none">
          Aucune erreur, bravo !
        </p>
      ) : (
        <ol className="grid gap-4">
          {mistakes.map((m, i) => (
            <li key={m.question_id} className="bg-white border-2 border-cream-dark rounded-2xl p-5" data-testid={`parcours-mistake-${i}`}>
              <p className="font-display text-lg font-bold text-navy mb-2">{m.question}</p>
              <p className="text-navy flex items-start gap-2"><X className="w-5 h-5 text-[#B52B27] shrink-0 mt-0.5" aria-hidden="true" />
                <span>Votre réponse : {m.your_answer ?? <em>sans réponse</em>}</span></p>
              <p className="text-navy font-semibold flex items-start gap-2 mt-1"><Check className="w-5 h-5 text-[#2A7350] shrink-0 mt-0.5" aria-hidden="true" />
                <span>Bonne réponse : {m.correct_answer}</span></p>
              {m.explanation && <p className="text-navy/80 mt-3 bg-cream/70 rounded-xl p-3">{m.explanation}</p>}
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
