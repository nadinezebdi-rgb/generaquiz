import { useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, HelpCircle, Flame } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { QuickQuestion } from "@/components/QuickQuestion";
import { adoptAccountStreak, applyTodayAnswer, loadStreak, parisToday } from "@/lib/visitorProgress";

const StreakBadge = ({ streak, testId }) => (
  <div className="inline-flex items-center gap-2 bg-mustard/30 text-navy text-sm font-bold px-3 py-1.5 rounded-full" data-testid={testId}>
    <Flame className="w-4 h-4 text-terracotta" />
    {streak.count > 0
      ? `${streak.count} jour${streak.count > 1 ? "s" : ""} de suite`
      : "Série à démarrer"}
    {streak.best > 1 && <span className="font-normal text-navy/60">· record {streak.best}</span>}
  </div>
);

export const TipQuiz = ({ tip, showContinue = true }) => {
  const { user } = useAuth();
  const isToday = tip?.date_key === parisToday();
  const [streak, setStreak] = useState(() => loadStreak());
  const initial = isToday ? streak.answers[tip?.date_key] || null : null;
  const [done, setDone] = useState(!!initial);
  if (!tip?.quiz) return null;
  const testId = `tip-quiz-${tip.date_key}`;

  function onDone(result, choice) {
    setDone(true);
    if (!isToday) return;
    setStreak(applyTodayAnswer(result.correct, result, choice));
    if (user) {
      api.post("/tips/streak/answer", { choice })
        .then(({ data }) => setStreak(adoptAccountStreak(data)))
        .catch(() => {});
    }
  }

  return (
    <div className="mt-5 bg-white/80 rounded-2xl border-2 border-cream-dark p-4" data-testid={testId}>
      <div className="flex items-center justify-between gap-2 flex-wrap mb-2">
        <span className="inline-flex items-center gap-1 text-[11px] font-bold uppercase tracking-widest text-[#6A994E]">
          <HelpCircle className="w-3.5 h-3.5" /> {isToday ? "La question du jour" : "Testez-vous"}
        </span>
        {isToday && <StreakBadge streak={streak} testId={`${testId}-streak`} />}
      </div>
      <QuickQuestion
        question={tip.quiz.question}
        options={tip.quiz.options}
        initial={initial}
        testId={`${testId}-q`}
        onAnswer={(choice) => api.post(`/tips/${tip.date_key}/answer`, { choice }).then((r) => r.data)}
        onDone={onDone}
      />
      {done && isToday && (
        <p className="mt-3 text-sm text-navy/80" data-testid={`${testId}-comeback`}>
          {streak.last_result
            ? "Revenez demain pour une nouvelle question et prolonger votre série !"
            : "Nouvelle chance demain : une bonne réponse relance votre série."}
        </p>
      )}
      {done && showContinue && (
        <Link
          to={user ? "/app/quiz/bien-vieillir" : "/register?next=/app/quiz/bien-vieillir"}
          data-testid={`${testId}-continue`}
          className="mt-4 inline-flex items-center gap-2 bg-navy text-white text-sm font-bold px-5 py-2.5 rounded-full hover:bg-terracotta transition-colors"
        >
          {user ? "Continuer avec le quiz Bien vieillir" : "Continuer avec un compte"} <ArrowRight className="w-4 h-4" />
        </Link>
      )}
    </div>
  );
};
