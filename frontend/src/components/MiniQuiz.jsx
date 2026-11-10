import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Trophy, Gamepad2 } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { QuickQuestion } from "@/components/QuickQuestion";

const VERDICT = ["On révise ensemble ?", "Un bon début !", "Très joli score !", "Sans faute, bravo !"];

export const ThemeMiniQuiz = ({ categoryId, color }) => {
  const [questions, setQuestions] = useState(null);
  useEffect(() => {
    let ignore = false;
    api.get(`/categories/${categoryId}/showcase`).then((r) => { if (!ignore) setQuestions(r.data.mini_quiz); }).catch(() => {});
    return () => { ignore = true; };
  }, [categoryId]);
  return <MiniQuiz categoryId={categoryId} questions={questions} color={color} />;
};

export const MiniQuiz = ({ categoryId, questions, color = "#E07A5F" }) => {
  const { user } = useAuth();
  const [idx, setIdx] = useState(0);
  const [score, setScore] = useState(0);
  const [answered, setAnswered] = useState(false);
  if (!questions?.length) return null;

  const finished = idx >= questions.length;
  const q = questions[idx];
  const playTo = user ? `/app/quiz/${categoryId}` : `/register?next=/app/quiz/${categoryId}`;

  return (
    <section className="py-16" data-testid="mini-quiz">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
        <span className="inline-flex items-center gap-2 text-white font-bold px-3 py-1 rounded-full text-xs uppercase tracking-wider mb-3" style={{ backgroundColor: color }}>
          <Gamepad2 className="w-3.5 h-3.5" /> Mini-quiz de la semaine
        </span>
        <h2 className="font-display text-3xl md:text-4xl font-extrabold text-navy mb-6">3 questions, sans compte</h2>
        <div className="bg-white rounded-[24px] border-2 border-cream-dark p-6 shadow-warm">
          {!finished ? (
            <>
              <div className="flex items-center justify-between mb-4 text-xs font-bold text-navy/60">
                <span data-testid="mini-quiz-progress">Question {idx + 1} / {questions.length}</span>
                <span data-testid="mini-quiz-score">Score : {score}</span>
              </div>
              <QuickQuestion
                key={q.id}
                question={q.question}
                options={q.options}
                testId={`mini-quiz-q${idx}`}
                onAnswer={(choice) =>
                  api.post(`/categories/${categoryId}/mini-quiz/answer`, { question_id: q.id, choice }).then((r) => r.data)}
                onDone={(r) => { if (r.correct) setScore((s) => s + 1); setAnswered(true); }}
              />
              {answered && (
                <button
                  type="button"
                  onClick={() => { setIdx((i) => i + 1); setAnswered(false); }}
                  data-testid="mini-quiz-next"
                  className="mt-5 inline-flex items-center gap-2 bg-navy text-white text-sm font-bold px-5 py-2.5 rounded-full hover:bg-terracotta transition-colors"
                >
                  {idx + 1 < questions.length ? "Question suivante" : "Voir mon score"} <ArrowRight className="w-4 h-4" />
                </button>
              )}
            </>
          ) : (
            <div className="text-center py-4" data-testid="mini-quiz-result">
              <Trophy className="w-10 h-10 mx-auto mb-3" style={{ color }} />
              <p className="font-display text-4xl font-extrabold text-navy mb-1" data-testid="mini-quiz-final-score">{score} / {questions.length}</p>
              <p className="text-navy/70 mb-6">{VERDICT[Math.min(score, 3)]} D&apos;autres questions vous attendent, du niveau 1 au niveau 7.</p>
              <Link
                to={playTo}
                data-testid="mini-quiz-continue"
                className="inline-flex items-center gap-2 text-white font-bold px-6 py-3 rounded-full transition-opacity hover:opacity-90 shadow-warm"
                style={{ backgroundColor: color }}
              >
                {user ? "Continuer le quiz" : "Continuer avec un compte"} <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          )}
        </div>
      </div>
    </section>
  );
};
