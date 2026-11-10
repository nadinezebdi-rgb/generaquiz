import { useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, HelpCircle } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { QuickQuestion } from "@/components/QuickQuestion";

export const TipQuiz = ({ tip }) => {
  const { user } = useAuth();
  const [done, setDone] = useState(false);
  if (!tip?.quiz) return null;
  const testId = `tip-quiz-${tip.date_key}`;

  return (
    <div className="mt-5 bg-white/80 rounded-2xl border-2 border-cream-dark p-4" data-testid={testId}>
      <div className="inline-flex items-center gap-1 text-[11px] font-bold uppercase tracking-widest text-[#6A994E] mb-2">
        <HelpCircle className="w-3.5 h-3.5" /> Testez-vous
      </div>
      <QuickQuestion
        question={tip.quiz.question}
        options={tip.quiz.options}
        testId={`${testId}-q`}
        onAnswer={(choice) => api.post(`/tips/${tip.date_key}/answer`, { choice }).then((r) => r.data)}
        onDone={() => setDone(true)}
      />
      {done && (
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
