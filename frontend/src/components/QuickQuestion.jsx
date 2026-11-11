import { useState } from "react";
import { CheckCircle2, XCircle, Loader2 } from "lucide-react";

// Question QCM publique : la correction vient du serveur (onAnswer → {correct, correct_index, explanation}).
export const QuickQuestion = ({ question, options, onAnswer, onDone, initial = null, testId = "quick-question" }) => {
  const [picked, setPicked] = useState(initial?.picked ?? null);
  const [result, setResult] = useState(initial);
  const [busy, setBusy] = useState(false);

  async function choose(i) {
    if (result || busy) return;
    setPicked(i);
    setBusy(true);
    try {
      const r = await onAnswer(i);
      setResult(r);
      onDone?.(r, i);
    } catch {
      setPicked(null);
    } finally {
      setBusy(false);
    }
  }

  const style = (i) => {
    if (!result) return picked === i ? "border-navy bg-navy/5" : "border-cream-dark bg-white hover:border-navy";
    if (i === result.correct_index) return "border-emerald-500 bg-emerald-50";
    if (i === picked) return "border-red-400 bg-red-50";
    return "border-cream-dark bg-white opacity-60";
  };

  return (
    <div data-testid={testId}>
      <p className="font-bold text-navy mb-3" data-testid={`${testId}-text`}>{question}</p>
      <div className="grid sm:grid-cols-2 gap-2">
        {options.map((o, i) => (
          <button
            key={o}
            type="button"
            disabled={!!result || busy}
            onClick={() => choose(i)}
            data-testid={`${testId}-option-${i}`}
            className={`text-left text-sm font-semibold text-navy rounded-xl border-2 px-4 py-3 transition-colors flex items-center gap-2 ${style(i)}`}
          >
            {busy && picked === i && <Loader2 className="w-4 h-4 animate-spin shrink-0" />}
            {result && i === result.correct_index && <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />}
            {result && i === picked && !result.correct && <XCircle className="w-4 h-4 text-red-500 shrink-0" />}
            <span>{o}</span>
          </button>
        ))}
      </div>
      {result && (
        <p className={`mt-3 text-sm leading-relaxed ${result.correct ? "text-emerald-700" : "text-navy/80"}`} data-testid={`${testId}-feedback`}>
          <b>{result.correct ? "Bravo !" : "Pas tout à fait."}</b> {result.explanation}
        </p>
      )}
    </div>
  );
};
