import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { ArrowRight, Trophy, Gamepad2, Swords, MessageCircle } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { QuickQuestion } from "@/components/QuickQuestion";
import { savePendingMini } from "@/lib/visitorProgress";

const VERDICT = ["On révise ensemble ?", "Un bon début !", "Très joli score !", "Sans faute, bravo !"];
const NAME_KEY = "gq_defi_name";

const cleanName = (n) => (n || "").replace(/[^\p{L}\s'-]/gu, "").trim().slice(0, 24);

export const ThemeMiniQuiz = ({ categoryId, color }) => {
  const [data, setData] = useState(null);
  useEffect(() => {
    let ignore = false;
    api.get(`/categories/${categoryId}/showcase`).then((r) => { if (!ignore) setData(r.data); }).catch(() => {});
    return () => { ignore = true; };
  }, [categoryId]);
  return <MiniQuiz categoryId={categoryId} title={data?.category.title} questions={data?.mini_quiz} color={color} />;
};

function useChallenge() {
  const [params] = useSearchParams();
  const raw = params.get("score");
  const score = raw !== null && /^[0-3]$/.test(raw) ? Number(raw) : null;
  return score === null ? null : { name: cleanName(params.get("defi")), score };
}

const ChallengeBanner = ({ challenge, color }) => (
  <div className="mb-5 flex items-center gap-3 rounded-2xl px-4 py-3 text-navy font-bold" style={{ backgroundColor: `${color}1f` }} data-testid="mini-quiz-challenge-banner">
    <Swords className="w-5 h-5 shrink-0" style={{ color }} />
    <span>{challenge.name || "Un proche"} a fait {challenge.score}/3 — à vous de faire mieux !</span>
  </div>
);

const ChallengeOutcome = ({ challenge, score }) => {
  const who = challenge.name || "votre proche";
  const text = score > challenge.score ? `Vous battez ${who} !` : score === challenge.score ? `Égalité avec ${who} !` : `${who} garde l'avantage… revanche ?`;
  return <p className="font-bold text-navy mb-4" data-testid="mini-quiz-challenge-outcome">{text}</p>;
};

const SendChallenge = ({ categoryId, title, score }) => {
  const [name, setName] = useState(() => localStorage.getItem(NAME_KEY) || "");
  const clean = cleanName(name);
  const shareUrl = `${window.location.origin}/api/share/defi/${categoryId}?${new URLSearchParams(clean ? { n: clean, s: score } : { s: score })}`;
  const text = `${clean ? `${clean} : j'ai` : "J'ai"} fait ${score}/3 au quiz ${title || ""} sur GénéraQuiz. À toi de me battre ! ${shareUrl}`;
  return (
    <div className="mt-6 pt-6 border-t-2 border-cream-dark text-left" data-testid="mini-quiz-send-challenge">
      <p className="font-bold text-navy mb-2 flex items-center gap-2"><Swords className="w-4 h-4" /> Défiez un proche</p>
      <div className="flex gap-2 flex-wrap">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          maxLength={24}
          placeholder="Votre prénom (ex. Mamie Jeanne)"
          aria-label="Votre prénom"
          data-testid="mini-quiz-challenge-name"
          className="flex-1 min-w-[180px] rounded-full border-2 border-cream-dark px-4 py-2.5 text-navy focus:border-navy outline-none"
        />
        <a
          href={`https://wa.me/?text=${encodeURIComponent(text)}`}
          target="_blank"
          rel="noopener noreferrer"
          onClick={() => clean && localStorage.setItem(NAME_KEY, clean)}
          data-testid="mini-quiz-challenge-whatsapp"
          className="inline-flex items-center gap-2 bg-[#25D366] text-white font-bold px-5 py-2.5 rounded-full hover:bg-[#1ebe5a] transition-colors"
        >
          <MessageCircle className="w-4 h-4" /> Envoyer sur WhatsApp
        </a>
      </div>
    </div>
  );
};

export const MiniQuiz = ({ categoryId, title, questions, color = "#E07A5F" }) => {
  const { user } = useAuth();
  const challenge = useChallenge();
  const ref = useRef(null);
  const [idx, setIdx] = useState(0);
  const [score, setScore] = useState(0);
  const [answers, setAnswers] = useState([]);
  const [answered, setAnswered] = useState(false);

  useEffect(() => {
    if (questions?.length && window.location.hash === "#mini-quiz") ref.current?.scrollIntoView({ behavior: "smooth" });
  }, [questions]);

  if (!questions?.length) return null;
  const finished = idx >= questions.length;
  const q = questions[idx];
  const playTo = user ? `/app/quiz/${categoryId}` : `/register?next=/app/quiz/${categoryId}`;

  function next() {
    const n = idx + 1;
    setIdx(n);
    setAnswered(false);
    if (n < questions.length) return;
    if (user) {
      api.post("/mini-quiz/claim", { category_id: categoryId, answers })
        .then(({ data }) => { if (!data.already_claimed) toast.success("Score ajouté à votre historique"); })
        .catch(() => {});
    } else {
      savePendingMini(categoryId, answers);
    }
  }

  return (
    <section className="py-16 scroll-mt-20" id="mini-quiz" ref={ref} data-testid="mini-quiz">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
        <span className="inline-flex items-center gap-2 text-white font-bold px-3 py-1 rounded-full text-xs uppercase tracking-wider mb-3" style={{ backgroundColor: color }}>
          <Gamepad2 className="w-3.5 h-3.5" /> Mini-quiz de la semaine
        </span>
        <h2 className="font-display text-3xl md:text-4xl font-extrabold text-navy mb-6">3 questions, sans compte</h2>
        <div className="bg-white rounded-[24px] border-2 border-cream-dark p-6 shadow-warm">
          {challenge && <ChallengeBanner challenge={challenge} color={color} />}
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
                onDone={(r, choice) => {
                  if (r.correct) setScore((s) => s + 1);
                  setAnswers((a) => [...a, { question_id: q.id, choice }]);
                  setAnswered(true);
                }}
              />
              {answered && (
                <button
                  type="button"
                  onClick={next}
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
              {challenge && <ChallengeOutcome challenge={challenge} score={score} />}
              <p className="text-navy/70 mb-6">
                {VERDICT[Math.min(score, 3)]} {user ? "Votre score est ajouté à votre historique." : "Créez votre compte : ce score sera gardé dans votre historique."}
              </p>
              <Link
                to={playTo}
                data-testid="mini-quiz-continue"
                className="inline-flex items-center gap-2 text-white font-bold px-6 py-3 rounded-full transition-opacity hover:opacity-90 shadow-warm"
                style={{ backgroundColor: color }}
              >
                {user ? "Continuer le quiz" : "Continuer avec un compte"} <ArrowRight className="w-4 h-4" />
              </Link>
              <SendChallenge categoryId={categoryId} title={title} score={score} />
            </div>
          )}
        </div>
      </div>
    </section>
  );
};
