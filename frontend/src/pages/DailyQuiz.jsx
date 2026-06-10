import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { api, formatError } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import {
  Sparkles, Trophy, ArrowRight, Check, X, Calendar, Crown, LogIn, Share2, Medal, Flame,
} from "lucide-react";
import Logo from "@/components/Logo";
import { toast } from "sonner";

// Fisher-Yates shuffle of options + return mapping so we can re-map to original index
function shuffleOptions(options) {
  const idx = options.map((_, i) => i);
  for (let i = idx.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [idx[i], idx[j]] = [idx[j], idx[i]];
  }
  return { options: idx.map((i) => options[i]), mapping: idx };
}

function rankBadge(rank) {
  if (rank === 1) return { emoji: "🥇", color: "bg-mustard text-navy" };
  if (rank === 2) return { emoji: "🥈", color: "bg-cream-dark text-navy" };
  if (rank === 3) return { emoji: "🥉", color: "bg-terracotta/30 text-navy" };
  return { emoji: `${rank}`, color: "bg-white border-2 border-cream-dark text-navy" };
}

export default function DailyQuiz() {
  const { user, refresh } = useAuth();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [stage, setStage] = useState("intro"); // intro | playing | done
  const [idx, setIdx] = useState(0);
  const [selected, setSelected] = useState(null);
  const [revealed, setRevealed] = useState(false);
  const [score, setScore] = useState(0);
  const [leaderboard, setLeaderboard] = useState(null);
  const [submitResult, setSubmitResult] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const startTime = useRef(null);

  useEffect(() => {
    api.get("/daily/quiz").then((r) => setData(r.data)).catch(() => {});
    api.get("/daily/leaderboard").then((r) => setLeaderboard(r.data)).catch(() => {});
  }, []);

  const currentQ = data?.questions?.[idx];
  const shuffled = useMemo(() => (currentQ ? shuffleOptions(currentQ.options) : null), [currentQ?.id, idx]);

  const start = () => {
    setIdx(0); setSelected(null); setRevealed(false); setScore(0);
    startTime.current = Date.now();
    setStage("playing");
  };

  const pick = (i) => {
    if (revealed) return;
    setSelected(i);
    setRevealed(true);
    if (shuffled && shuffled.mapping[i] === currentQ.correct_index) {
      setScore((s) => s + 1);
    }
  };

  const next = async () => {
    if (idx + 1 >= data.questions.length) {
      // End of quiz: submit if user is logged in
      const duration = Math.round((Date.now() - startTime.current) / 1000);
      if (user) {
        try {
          setSubmitting(true);
          const resp = await api.post("/daily/submit", { score, duration_seconds: duration });
          setSubmitResult(resp.data);
          const lb = await api.get("/daily/leaderboard");
          setLeaderboard(lb.data);
          // Refresh /me so streak fields propagate to navbar/dashboard
          if (refresh) refresh();
        } catch (e) {
          // 409 = already submitted today, that's fine
          if (e.response?.status !== 409) {
            toast.error(formatError(e.response?.data?.detail));
          }
        } finally {
          setSubmitting(false);
        }
      }
      setStage("done");
    } else {
      setIdx(idx + 1); setSelected(null); setRevealed(false);
    }
  };

  const shareLink = async () => {
    const url = `${window.location.origin}/quiz-du-jour`;
    const text = `J'ai fait ${score}/${data?.questions?.length || 5} au Quiz du Jour de GénéraQuiz ! 🎯 Saurez-vous battre mon score ?`;
    try {
      if (navigator.share) {
        await navigator.share({ title: "Quiz du Jour — GénéraQuiz", text, url });
      } else {
        await navigator.clipboard.writeText(`${text} ${url}`);
        toast.success("Lien copié dans le presse-papier !");
      }
    } catch {
      /* user cancelled */
    }
  };

  if (!data) {
    return (
      <div className="min-h-screen paper-bg flex items-center justify-center">
        <div className="text-navy text-xl">Chargement du Quiz du Jour…</div>
      </div>
    );
  }

  const dateLabel = new Date(data.date + "T00:00:00").toLocaleDateString("fr-FR", {
    weekday: "long", day: "numeric", month: "long", year: "numeric",
  });

  return (
    <div className="min-h-screen paper-bg">
      {/* Slim public header */}
      <header className="bg-navy text-white py-3 border-b-2 border-mustard">
        <div className="max-w-5xl mx-auto px-4 flex items-center justify-between">
          <Link to="/" data-testid="daily-home-link"><Logo size="sm" dark asLink={false} showTagline={false} /></Link>
          <span className="text-mustard font-bold text-sm tracking-wide uppercase hidden sm:flex items-center gap-1.5">
            <Calendar className="w-4 h-4" /> Quiz du Jour
          </span>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <AnimatePresence mode="wait">
          {/* ===================== INTRO ===================== */}
          {stage === "intro" && (
            <motion.div
              key="intro"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="bg-white border-4 border-navy rounded-[32px] p-8 md:p-12 shadow-warm text-center"
              data-testid="daily-intro"
            >
              <div className="inline-flex items-center gap-2 bg-mustard text-navy font-bold px-4 py-2 rounded-full text-sm mb-5">
                <Calendar className="w-4 h-4" /> {dateLabel}
              </div>
              <h1 className="font-display text-4xl md:text-6xl font-extrabold text-navy mb-4">
                Quiz du <span className="text-terracotta italic">Jour</span>
              </h1>
              <p className="text-xl text-navy/70 mb-2">
                5 questions, toutes catégories. <strong>Gratuit</strong> et nouveau chaque jour.
              </p>
              <p className="text-base text-navy/60 mb-8">
                Saurez-vous entrer dans le Top 10 du classement quotidien ?
              </p>

              {data.has_played && (
                <div className="max-w-md mx-auto mb-6 bg-terracotta/10 border-2 border-terracotta rounded-2xl p-4">
                  <p className="text-navy font-medium">
                    Vous avez déjà joué aujourd&apos;hui — votre score est enregistré au classement.
                    Revenez demain pour 5 nouvelles questions !
                  </p>
                </div>
              )}

              <button
                data-testid="daily-start-btn"
                onClick={start}
                className="inline-flex items-center gap-2 bg-terracotta hover:bg-terracotta-dark text-white font-bold text-xl px-10 py-5 rounded-full shadow-warm min-h-[64px] transition"
              >
                {data.has_played ? "Rejouer pour le fun" : "Commencer le quiz"} <ArrowRight className="w-5 h-5" />
              </button>

              {!user && (
                <p className="mt-6 text-sm text-navy/60">
                  💡 <Link to="/login" className="text-navy underline font-semibold">Connectez-vous</Link> pour apparaître dans le classement quotidien.
                </p>
              )}

              {/* Mini leaderboard preview */}
              {leaderboard && leaderboard.top.length > 0 && (
                <div className="mt-10 pt-8 border-t-2 border-cream-dark">
                  <h3 className="font-display text-xl font-bold text-navy mb-4 flex items-center justify-center gap-2">
                    <Trophy className="w-5 h-5 text-mustard-dark" />
                    Classement du jour ({leaderboard.total_players} joueur{leaderboard.total_players > 1 ? "s" : ""})
                  </h3>
                  <ul className="space-y-2 max-w-md mx-auto" data-testid="daily-leaderboard">
                    {leaderboard.top.slice(0, 5).map((entry, i) => {
                      const b = rankBadge(i + 1);
                      return (
                        <li key={i} className="flex items-center justify-between bg-cream/60 border border-cream-dark rounded-xl px-4 py-2.5">
                          <div className="flex items-center gap-3">
                            <span className={`w-9 h-9 rounded-full flex items-center justify-center font-extrabold text-base ${b.color}`}>{b.emoji}</span>
                            <span className="font-semibold text-navy">{entry.user_name}</span>
                          </div>
                          <span className="font-display text-lg font-extrabold text-bordeaux">
                            {entry.score}/{entry.total}
                            <span className="text-xs text-navy/50 font-normal ml-1.5">{entry.duration_seconds}s</span>
                          </span>
                        </li>
                      );
                    })}
                  </ul>
                </div>
              )}
            </motion.div>
          )}

          {/* ===================== PLAYING ===================== */}
          {stage === "playing" && currentQ && shuffled && (
            <motion.div
              key={`q-${idx}`}
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0 }}
              className="bg-white border-4 border-navy rounded-[32px] p-6 md:p-10 shadow-warm"
              data-testid="daily-question"
            >
              <div className="flex items-center justify-between mb-5">
                <span className="text-sm font-bold uppercase tracking-wider text-navy/60">
                  Question {idx + 1} / {data.questions.length}
                </span>
                <span className="bg-cream border-2 border-cream-dark text-navy font-bold px-3 py-1 rounded-full text-sm">
                  Score : {score}
                </span>
              </div>
              <div className="w-full bg-cream rounded-full h-3 mb-7 overflow-hidden">
                <div
                  className="bg-terracotta h-3 transition-all duration-300"
                  style={{ width: `${((idx + (revealed ? 1 : 0)) / data.questions.length) * 100}%` }}
                />
              </div>
              <h2 className="font-display text-2xl md:text-3xl font-extrabold text-navy mb-6 leading-snug">
                {currentQ.question}
              </h2>
              <div className="space-y-3 mb-6">
                {shuffled.options.map((opt, i) => {
                  const originalIdx = shuffled.mapping[i];
                  const isCorrect = revealed && originalIdx === currentQ.correct_index;
                  const isWrong = revealed && i === selected && originalIdx !== currentQ.correct_index;
                  return (
                    <button
                      key={i}
                      data-testid={`daily-option-${i}`}
                      onClick={() => pick(i)}
                      disabled={revealed}
                      className={`w-full text-left p-4 md:p-5 rounded-2xl border-2 font-semibold text-lg transition flex items-start gap-3
                        ${isCorrect ? "bg-green-50 border-green-600 text-green-900" : ""}
                        ${isWrong ? "bg-red-50 border-red-600 text-red-900" : ""}
                        ${!revealed ? "bg-white border-cream-dark hover:border-navy hover:bg-cream" : ""}
                        ${revealed && !isCorrect && !isWrong ? "opacity-60" : ""}`}
                    >
                      <span className="w-7 h-7 shrink-0 rounded-full bg-cream border-2 border-cream-dark flex items-center justify-center font-extrabold text-sm">
                        {String.fromCharCode(65 + i)}
                      </span>
                      <span className="flex-1">{opt}</span>
                      {isCorrect && <Check className="w-6 h-6 text-green-700 shrink-0" />}
                      {isWrong && <X className="w-6 h-6 text-red-700 shrink-0" />}
                    </button>
                  );
                })}
              </div>
              {revealed && currentQ.explanation && (
                <div className="bg-cream border-l-4 border-mustard-dark rounded-xl p-4 mb-6">
                  <p className="text-navy text-base leading-relaxed">
                    <strong>💡 Explication :</strong> {currentQ.explanation}
                  </p>
                </div>
              )}
              {revealed && (
                <button
                  data-testid="daily-next-btn"
                  onClick={next}
                  className="w-full inline-flex items-center justify-center gap-2 bg-navy hover:bg-navy/90 text-white font-bold text-lg px-6 py-4 rounded-full transition min-h-[60px]"
                >
                  {idx + 1 >= data.questions.length ? "Voir mon score" : "Question suivante"}{" "}
                  <ArrowRight className="w-5 h-5" />
                </button>
              )}
            </motion.div>
          )}

          {/* ===================== DONE ===================== */}
          {stage === "done" && (
            <motion.div
              key="done"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              className="space-y-6"
              data-testid="daily-result"
            >
              <div className="bg-white border-4 border-navy rounded-[32px] p-8 md:p-12 shadow-warm text-center">
                <Trophy className="w-20 h-20 mx-auto text-mustard-dark mb-4" />
                <h1 className="font-display text-4xl md:text-5xl font-extrabold text-navy mb-3">
                  {score === data.questions.length ? "Sans-faute ! 🎉" : "Bravo !"}
                </h1>
                <p className="text-2xl text-navy/70 mb-6">
                  Vous avez obtenu <strong className="text-bordeaux">{score}/{data.questions.length}</strong>
                </p>

                {user ? (
                  <>
                    {submitting && <p className="text-navy/60 mb-4">Enregistrement du score…</p>}
                    {submitResult?.streak_current >= 1 && (
                      <div
                        data-testid="daily-streak-block"
                        className="inline-flex items-center gap-2 bg-terracotta text-white font-bold px-5 py-3 rounded-full text-lg mb-3 mr-3"
                      >
                        <Flame className="w-5 h-5" fill="currentColor" />
                        Série de <strong>{submitResult.streak_current} jour{submitResult.streak_current > 1 ? "s" : ""}</strong> 🔥
                        {submitResult.streak_current === submitResult.streak_best && submitResult.streak_current >= 2 && (
                          <span className="ml-1 bg-white/20 px-2 py-0.5 rounded-full text-xs">Record !</span>
                        )}
                      </div>
                    )}
                    {leaderboard?.my_rank && (
                      <div className="inline-flex items-center gap-2 bg-mustard text-navy font-bold px-5 py-3 rounded-full text-lg mb-6">
                        <Medal className="w-5 h-5" />
                        Classé <strong>#{leaderboard.my_rank}</strong> sur {leaderboard.total_players} joueurs
                      </div>
                    )}
                  </>
                ) : (
                  <div className="max-w-md mx-auto bg-cream border-2 border-cream-dark rounded-2xl p-5 mb-6 text-left">
                    <p className="font-bold text-navy mb-2 flex items-center gap-2">
                      <LogIn className="w-5 h-5 text-terracotta" /> Connectez-vous pour apparaître au classement
                    </p>
                    <p className="text-sm text-navy/70">
                      Créez un compte gratuit en 30 secondes et défiez votre famille chaque jour.
                    </p>
                  </div>
                )}

                <div className="flex flex-col sm:flex-row gap-3 justify-center">
                  <button
                    data-testid="daily-share-btn"
                    onClick={shareLink}
                    className="inline-flex items-center justify-center gap-2 bg-cream border-2 border-navy text-navy hover:bg-navy hover:text-white font-bold px-6 py-3 rounded-full transition"
                  >
                    <Share2 className="w-4 h-4" /> Partager mon score
                  </button>
                  {user ? (
                    <Link
                      to="/app/dashboard"
                      data-testid="daily-dashboard-cta"
                      className="inline-flex items-center justify-center gap-2 bg-terracotta hover:bg-terracotta-dark text-white font-bold px-6 py-3 rounded-full shadow-warm transition"
                    >
                      Mon Dashboard <ArrowRight className="w-4 h-4" />
                    </Link>
                  ) : (
                    <Link
                      to="/register"
                      data-testid="daily-register-cta"
                      className="inline-flex items-center justify-center gap-2 bg-terracotta hover:bg-terracotta-dark text-white font-bold px-6 py-3 rounded-full shadow-warm transition"
                    >
                      Créer un compte gratuit <ArrowRight className="w-4 h-4" />
                    </Link>
                  )}
                </div>
              </div>

              {/* Premium nudge */}
              {(!user || user.plan !== "premium") && (
                <div className="bg-gradient-to-br from-bordeaux to-navy rounded-[32px] p-8 md:p-10 text-white shadow-warm">
                  <div className="flex flex-col md:flex-row items-start md:items-center gap-6">
                    <div className="bg-mustard text-navy rounded-2xl p-4">
                      <Crown className="w-10 h-10" />
                    </div>
                    <div className="flex-1">
                      <h2 className="font-display text-2xl md:text-3xl font-extrabold mb-2">
                        Envie d&apos;aller plus loin ?
                      </h2>
                      <p className="text-cream/90 mb-4 leading-relaxed">
                        Avec <strong>GénéraQuiz Premium</strong> jouez <strong>30 questions par catégorie</strong>,
                        accédez aux <strong>800 questions</strong> et créez vos <strong>Défis Famille</strong> illimités.
                      </p>
                      <button
                        data-testid="daily-premium-cta"
                        onClick={() => navigate(user ? "/app/pricing" : "/register")}
                        className="inline-flex items-center gap-2 bg-mustard hover:bg-mustard-dark text-navy font-bold px-6 py-3 rounded-full transition"
                      >
                        Découvrir Premium <Sparkles className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {/* Full leaderboard */}
              {leaderboard && leaderboard.top.length > 0 && (
                <div className="bg-white border-4 border-cream-dark rounded-[32px] p-6 md:p-8">
                  <h3 className="font-display text-2xl font-extrabold text-navy mb-4 flex items-center gap-2">
                    <Trophy className="w-6 h-6 text-mustard-dark" />
                    Classement du {dateLabel}
                  </h3>
                  <ul className="space-y-2" data-testid="daily-full-leaderboard">
                    {leaderboard.top.map((entry, i) => {
                      const b = rankBadge(i + 1);
                      const isMine = leaderboard.my_entry && entry.user_name === leaderboard.my_entry.user_name
                        && entry.score === leaderboard.my_entry.score && entry.duration_seconds === leaderboard.my_entry.duration_seconds;
                      return (
                        <li
                          key={i}
                          className={`flex items-center justify-between rounded-xl px-4 py-3 ${
                            isMine ? "bg-mustard/30 border-2 border-mustard-dark" : "bg-cream/40 border border-cream-dark"
                          }`}
                        >
                          <div className="flex items-center gap-3">
                            <span className={`w-9 h-9 rounded-full flex items-center justify-center font-extrabold text-base ${b.color}`}>{b.emoji}</span>
                            <span className="font-semibold text-navy">{entry.user_name}{isMine && " (vous)"}</span>
                          </div>
                          <span className="font-display text-lg font-extrabold text-bordeaux">
                            {entry.score}/{entry.total}
                            <span className="text-xs text-navy/50 font-normal ml-1.5">{entry.duration_seconds}s</span>
                          </span>
                        </li>
                      );
                    })}
                  </ul>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}
