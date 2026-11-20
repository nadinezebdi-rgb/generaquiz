import { useState } from "react";
import { Check, Gamepad2, Loader2, X } from "lucide-react";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { api } from "@/lib/api";

function QuizBody({ habit, questions }) {
  const [idx, setIdx] = useState(0);
  const [fb, setFb] = useState(null);
  const [score, setScore] = useState(0);
  const [busy, setBusy] = useState(false);
  if (idx >= questions.length) {
    return (
      <div className="text-center py-6" data-testid="habit-quiz-result">
        <p className="font-display text-3xl font-extrabold text-navy mb-2">{score} / {questions.length}</p>
        <p className="text-lg text-navy/75">Bravo ! Un geste de plus pour « {habit.label} ».</p>
      </div>
    );
  }
  const q = questions[idx];
  const answer = async (choice) => {
    setBusy(true);
    try {
      const { data } = await api.post(`/bien-vieillir/habits/${habit.id}/quiz/answer`, { question_id: q.id, choice });
      setFb({ ...data, choice });
      if (data.correct) setScore((s) => s + 1);
    } finally { setBusy(false); }
  };
  const state = (i) => !fb ? "idle" : i === fb.correct_index ? "correct" : i === fb.choice ? "wrong" : "dim";
  const cls = { idle: "border-cream-dark hover:border-navy/40", correct: "border-[#3D9970] bg-[#3D9970]/10",
    wrong: "border-[#D9534F] bg-[#D9534F]/10", dim: "border-cream-dark text-navy/50" };
  return (
    <div data-testid="habit-quiz-question">
      <p className="text-sm text-navy/60 mb-2">Question {idx + 1} / {questions.length}</p>
      <h3 className="font-display text-xl font-bold text-navy mb-4">{q.question}</h3>
      <div className="grid gap-2">
        {q.options.map((o, i) => (
          <button key={i} type="button" disabled={Boolean(fb) || busy} onClick={() => answer(i)} data-testid={`habit-quiz-option-${i}`}
            className={`text-left flex items-center gap-3 p-3 rounded-2xl border-2 font-bold text-navy transition-colors ${cls[state(i)]}`}>
            <span className="flex-1">{o}</span>
            {state(i) === "correct" && <Check className="w-5 h-5 text-[#2A7350]" aria-label="bonne réponse" />}
            {state(i) === "wrong" && <X className="w-5 h-5 text-[#B52B27]" aria-label="votre réponse, fausse" />}
          </button>
        ))}
      </div>
      {fb && (
        <div aria-live="polite" className="mt-4 rounded-2xl bg-cream p-4" data-testid="habit-quiz-feedback">
          <p className="text-lg font-bold text-navy">{fb.correct ? "✅ Bonne réponse !" : `❌ Pas tout à fait. La bonne réponse était : ${fb.correct_answer}`}</p>
          {fb.explanation && <p className="text-navy/80 mt-2">{fb.explanation}</p>}
          <button type="button" onClick={() => { setFb(null); setIdx(idx + 1); }} data-testid="habit-quiz-next"
            className="mt-3 bg-navy text-cream font-bold px-5 py-2.5 rounded-full hover:bg-terracotta transition-colors">
            {idx < questions.length - 1 ? "Question suivante" : "Voir mon score"}
          </button>
        </div>
      )}
    </div>
  );
}

/** Bouton « Jouer » d'une habitude : ouvre un mini-quiz thématique Bien vieillir. */
export function HabitQuizButton({ habit }) {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState(null);
  const start = async () => {
    setOpen(true);
    setData(null);
    const r = await api.get(`/bien-vieillir/habits/${habit.id}/quiz`).catch(() => ({ data: { questions: [] } }));
    setData(r.data);
  };
  return (
    <>
      <button type="button" onClick={start} data-testid={`routine-habit-quiz-${habit.id}`}
        className="mt-2 ml-4 sm:ml-11 inline-flex items-center gap-2 text-base font-bold text-terracotta hover:text-bordeaux transition-colors">
        <Gamepad2 className="w-4 h-4" aria-hidden="true" /> Jouer au quiz express<span className="sr-only"> : {habit.label}</span>
      </button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-lg bg-white" data-testid="habit-quiz-dialog">
          <DialogTitle className="font-display text-2xl text-navy"><span aria-hidden="true">{habit.emoji}</span> Quiz express</DialogTitle>
          <DialogDescription className="text-navy/70">{habit.label}</DialogDescription>
          {!data ? <Loader2 className="w-8 h-8 animate-spin text-terracotta mx-auto my-6" />
            : data.questions.length === 0 ? <p className="text-navy/70" data-testid="habit-quiz-empty">Ce quiz arrive bientôt.</p>
            : <QuizBody habit={habit} questions={data.questions} />}
        </DialogContent>
      </Dialog>
    </>
  );
}
