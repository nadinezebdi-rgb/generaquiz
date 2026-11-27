import { useEffect, useState } from "react";
import { Moon, Lightbulb, Eye, EyeOff, MessageCircleHeart } from "lucide-react";
import { api } from "@/lib/api";

export function EveningRiddleCard() {
  const [r, setR] = useState(null);
  const [failed, setFailed] = useState(false);
  const [hint, setHint] = useState(false);
  const [answer, setAnswer] = useState(false);

  useEffect(() => {
    api.get("/enigme/today").then((res) => setR(res.data)).catch(() => setFailed(true));
  }, []);

  if (failed) return null;
  const btn = "inline-flex items-center gap-2 font-bold px-5 py-2.5 rounded-full transition-colors";
  return (
    <section className="bg-navy text-cream rounded-[28px] p-6 md:p-8 mb-8" data-testid="evening-riddle-card" aria-live="polite">
      <p className="flex items-center gap-2 text-mustard font-bold uppercase tracking-wider text-sm mb-2">
        <Moon className="w-4 h-4" aria-hidden="true" /> L&apos;énigme du soir · à résoudre ensemble au dîner
      </p>
      {!r ? <p className="text-cream/80">L&apos;énigme se prépare…</p> : (
        <>
          <h2 className="font-display text-2xl md:text-3xl font-extrabold mb-3" data-testid="evening-riddle-title">{r.titre}</h2>
          <p className="text-lg md:text-xl leading-relaxed mb-5" data-testid="evening-riddle-text">{r.enigme}</p>
          {hint && <p className="bg-cream/10 rounded-2xl p-4 mb-4 text-lg" data-testid="evening-riddle-hint"><strong>Indice :</strong> {r.indice}</p>}
          {answer && (
            <div className="bg-cream text-navy rounded-2xl p-5 mb-4" data-testid="evening-riddle-answer">
              <p className="font-display text-2xl font-extrabold text-bordeaux mb-2">{r.reponse}</p>
              <p className="mb-3">{r.explication}</p>
              <p className="flex items-start gap-2 font-semibold"><MessageCircleHeart className="w-5 h-5 shrink-0 mt-0.5 text-terracotta" aria-hidden="true" />{r.question_famille}</p>
            </div>
          )}
          <div className="flex flex-wrap gap-3">
            {!hint && !answer && (
              <button type="button" onClick={() => setHint(true)} className={`${btn} bg-mustard text-navy hover:bg-mustard/90`} data-testid="evening-riddle-hint-btn">
                <Lightbulb className="w-5 h-5" /> Un indice
              </button>
            )}
            {answer && (
              <button type="button" onClick={() => { setAnswer(false); setHint(false); }} className={`${btn} border-2 border-cream/70 hover:bg-cream/10`} data-testid="evening-riddle-hide-btn">
                <EyeOff className="w-5 h-5" /> Masquer la réponse
              </button>
            )}
            {!answer && (
              <button type="button" onClick={() => setAnswer(true)} className={`${btn} border-2 border-cream/70 hover:bg-cream/10`} data-testid="evening-riddle-answer-btn">
                <Eye className="w-5 h-5" /> Voir la réponse
              </button>
            )}
          </div>
        </>
      )}
    </section>
  );
}
