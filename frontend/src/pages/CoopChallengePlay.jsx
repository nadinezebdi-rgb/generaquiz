import { useEffect, useMemo, useState } from "react";
import { Link, useParams, useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { api, formatError } from "@/lib/api";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import {
  HandHelping, ArrowRight, Trophy, Sparkles, Heart, Check, X,
  Smartphone, Loader2, RefreshCcw, Home,
} from "lucide-react";

/**
 * CoopChallengePlay — Asymmetric cooperative gameplay on a single device.
 *
 * Flow per question:
 *   1. Banner shows "C'est à toi <playerName> (<role>) !"
 *   2. User either picks an answer OR taps "🆘 Demander de l'aide à <partner>"
 *   3. If help requested → "Passez le téléphone à <partner> 📱→👴/🧒" overlay
 *      (blocks the question until the partner taps "C'est moi, c'est parti !")
 *   4. After the answer → reveal correct/wrong + XP earned + explanation
 *   5. "Question suivante" advances OR shows the final results screen
 *
 * The server enforces correctness — the client just sends {answer_index, help_used}.
 */
const ROLE_INFO = {
  senior: { emoji: "👴", label: "Senior", color: "bg-bordeaux" },
  jeune: { emoji: "🧒", label: "Jeune", color: "bg-navy" },
};

export default function CoopChallengePlay() {
  const { token } = useParams();
  const navigate = useNavigate();

  const [challenge, setChallenge] = useState(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  // Per-question UI state
  const [helpRequested, setHelpRequested] = useState(false); // current Q has had "help" requested
  const [partnerReady, setPartnerReady] = useState(false);   // partner tapped "C'est parti"
  const [feedback, setFeedback] = useState(null);            // last answer's server response
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    api.get(`/coop-challenges/${token}`)
      .then((r) => setChallenge(r.data))
      .catch((e) => setErr(formatError(e.response?.data?.detail) || "Défi introuvable"))
      .finally(() => setLoading(false));
  }, [token]);

  const currentQ = useMemo(() => {
    if (!challenge) return null;
    const idx = challenge.current_index;
    return challenge.questions?.[idx] || null;
  }, [challenge]);

  const currentPlayer = useMemo(() => {
    if (!challenge || !currentQ) return null;
    return challenge.players.find((p) => p.role === currentQ.assigned_to);
  }, [challenge, currentQ]);

  const partner = useMemo(() => {
    if (!challenge || !currentQ) return null;
    return challenge.players.find((p) => p.role !== currentQ.assigned_to);
  }, [challenge, currentQ]);

  const onAnswer = async (answerIndex) => {
    if (submitting || feedback) return;
    setSubmitting(true);
    try {
      const { data } = await api.post(`/coop-challenges/${token}/answer`, {
        answer_index: answerIndex,
        help_used: helpRequested,
      });
      setFeedback(data);
    } catch (e) {
      setErr(formatError(e.response?.data?.detail) || "Erreur lors de l'envoi de la réponse");
    } finally {
      setSubmitting(false);
    }
  };

  const onRequestHelp = () => {
    setHelpRequested(true);
    setPartnerReady(false);
  };

  const onNext = () => {
    // Apply the server's new state, then reset the per-question UI flags
    if (!feedback) return;
    setChallenge((prev) => ({
      ...prev,
      current_index: prev.current_index + 1,
      stats_coop: feedback.stats_coop,
      status: feedback.completed ? "completed" : prev.status,
    }));
    setFeedback(null);
    setHelpRequested(false);
    setPartnerReady(false);
  };

  if (loading) {
    return (
      <div className="min-h-screen paper-bg flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-terracotta" />
      </div>
    );
  }

  if (err || !challenge) {
    return (
      <div className="min-h-screen paper-bg">
        <Navbar variant="app" />
        <div className="max-w-xl mx-auto px-4 py-20 text-center">
          <h1 className="font-display text-3xl font-bold text-navy mb-3">Oups</h1>
          <p className="text-navy/70 mb-6">{err || "Défi introuvable"}</p>
          <Link to="/app/challenges" className="inline-flex items-center gap-2 bg-terracotta text-white font-bold px-5 py-3 rounded-full">
            <Home className="w-4 h-4" /> Retour aux défis
          </Link>
        </div>
        <Footer />
      </div>
    );
  }

  if (challenge.status === "completed") {
    return <FinalResults challenge={challenge} onReplay={() => navigate("/app/coop/new")} />;
  }

  const total = challenge.total;
  const idx = challenge.current_index;
  const score = challenge.stats_coop?.total_xp || 0;
  const correct = challenge.stats_coop?.correct_count || 0;
  const helpsUsed = challenge.stats_coop?.helps_used || 0;

  if (!currentQ || !currentPlayer) {
    return null;
  }

  const roleInfo = ROLE_INFO[currentPlayer.role];
  const partnerRoleInfo = ROLE_INFO[partner.role];

  // Hide question text until partner taps "C'est parti" after a help request
  const showQuestion = !helpRequested || partnerReady;

  return (
    <div className="min-h-screen paper-bg">
      <Navbar variant="app" />
      <main className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 py-6 md:py-10">

        {/* ============ HEADER: team + score + progress ============ */}
        <div className="bg-white border-2 border-cream-dark rounded-2xl p-4 mb-5" data-testid="coop-play-header">
          <div className="flex items-center justify-between gap-3 mb-3">
            <div className="min-w-0 flex-1">
              <div className="text-xs font-bold uppercase tracking-wider text-navy/60">Équipe</div>
              <div className="font-display text-xl font-extrabold text-navy truncate" data-testid="coop-team-name">
                {challenge.team_name}
              </div>
            </div>
            <div className="flex items-center gap-3 shrink-0">
              <div className="text-right">
                <div className="text-xs font-bold uppercase tracking-wider text-navy/60">Score</div>
                <div className="font-display text-2xl font-extrabold text-terracotta" data-testid="coop-score">
                  {score} XP
                </div>
              </div>
            </div>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="font-bold text-navy">Question {idx + 1} / {total}</span>
            <span className="text-navy/60 flex items-center gap-1">
              <HandHelping className="w-4 h-4" /> {helpsUsed} aide{helpsUsed > 1 ? "s" : ""}
            </span>
          </div>
          <div className="mt-2 h-2 bg-cream rounded-full overflow-hidden">
            <div className="h-full bg-terracotta transition-all" style={{ width: `${(idx / total) * 100}%` }} />
          </div>
        </div>

        {/* ============ PASS-THE-PHONE OVERLAY ============ */}
        <AnimatePresence>
          {helpRequested && !partnerReady && !feedback && (
            <motion.div
              key="passe"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-navy text-cream rounded-[28px] p-8 text-center mb-5"
              data-testid="coop-pass-phone-overlay"
            >
              <Smartphone className="w-12 h-12 mx-auto mb-3 text-mustard" />
              <div className="font-display text-2xl md:text-3xl font-extrabold mb-2">
                Passe le téléphone <span className="text-mustard">à {partner.name}</span> {partnerRoleInfo.emoji}
              </div>
              <p className="text-cream/80 mb-5">
                {currentPlayer.name} bloque sur cette question — c&apos;est à {partner.name} de sauver l&apos;équipe !
              </p>
              <button
                data-testid="coop-partner-ready"
                onClick={() => setPartnerReady(true)}
                className="inline-flex items-center gap-2 bg-mustard hover:bg-mustard-dark text-navy font-bold text-lg px-6 py-4 rounded-full transition"
              >
                C&apos;est moi, c&apos;est parti ! <ArrowRight className="w-5 h-5" />
              </button>
              <p className="text-xs text-cream/60 mt-3">
                💡 Réponse correcte = +50 XP (au lieu de 100 si solo).
              </p>
            </motion.div>
          )}
        </AnimatePresence>

        {/* ============ TURN BANNER ============ */}
        {showQuestion && !feedback && (
          <div
            className={`${roleInfo.color} text-white rounded-2xl p-4 mb-4 flex items-center gap-3`}
            data-testid="coop-turn-banner"
          >
            <span className="text-3xl">{roleInfo.emoji}</span>
            <div className="flex-1 min-w-0">
              <div className="text-xs font-bold uppercase tracking-wider opacity-80">À toi de jouer</div>
              <div className="font-display text-xl font-extrabold truncate" data-testid="coop-current-player">
                {helpRequested ? partner.name : currentPlayer.name}
              </div>
            </div>
            {helpRequested && (
              <span className="bg-white/20 text-white text-xs font-bold px-2 py-1 rounded-full">
                Aide en cours
              </span>
            )}
          </div>
        )}

        {/* ============ QUESTION + OPTIONS ============ */}
        {showQuestion && !feedback && (
          <div className="bg-white border-2 border-cream-dark rounded-[28px] p-6 md:p-8" data-testid="coop-question-card">
            <h2 className="font-display text-2xl md:text-3xl font-extrabold text-navy mb-6 leading-snug" data-testid="coop-question-text">
              {currentQ.question}
            </h2>
            <div className="space-y-3">
              {currentQ.options.map((opt, i) => (
                <button
                  key={i}
                  data-testid={`coop-option-${i}`}
                  disabled={submitting}
                  onClick={() => onAnswer(i)}
                  className="w-full text-left bg-cream hover:bg-mustard hover:border-mustard-dark border-2 border-cream-dark rounded-2xl p-4 font-medium text-navy text-lg transition disabled:opacity-60"
                >
                  <span className="inline-block w-7 h-7 rounded-full bg-white border-2 border-cream-dark text-center font-bold text-navy mr-3 align-middle">
                    {String.fromCharCode(65 + i)}
                  </span>
                  {opt}
                </button>
              ))}
            </div>
            {!helpRequested && (
              <button
                data-testid="coop-request-help"
                onClick={onRequestHelp}
                className="mt-5 w-full inline-flex items-center justify-center gap-2 bg-mustard/30 hover:bg-mustard border-2 border-mustard-dark text-navy font-bold py-3 rounded-full transition"
              >
                <HandHelping className="w-5 h-5" /> Demander de l&apos;aide à {partner.name} {partnerRoleInfo.emoji}
              </button>
            )}
          </div>
        )}

        {/* ============ FEEDBACK ============ */}
        <AnimatePresence>
          {feedback && (
            <motion.div
              key="feedback"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              className={`rounded-[28px] p-6 md:p-8 mb-4 border-2 ${
                feedback.is_correct ? "bg-[#3D9970]/15 border-[#3D9970]/50" : "bg-bordeaux/15 border-bordeaux/50"
              }`}
              data-testid="coop-feedback"
            >
              <div className="flex items-center gap-3 mb-3">
                {feedback.is_correct ? (
                  <div className="w-12 h-12 rounded-full bg-[#3D9970] flex items-center justify-center">
                    <Check className="w-7 h-7 text-white" strokeWidth={3} />
                  </div>
                ) : (
                  <div className="w-12 h-12 rounded-full bg-bordeaux flex items-center justify-center">
                    <X className="w-7 h-7 text-white" strokeWidth={3} />
                  </div>
                )}
                <div className="flex-1">
                  <div className="font-display text-2xl font-extrabold text-navy">
                    {feedback.is_correct ? "Bravo !" : "Raté…"}
                  </div>
                  {feedback.help_used && (
                    <div className="text-sm text-navy/70 flex items-center gap-1">
                      <HandHelping className="w-4 h-4" /> Avec l&apos;aide de {partner.name}
                    </div>
                  )}
                </div>
                <div className="text-right shrink-0">
                  <div className="text-xs font-bold uppercase tracking-wider text-navy/60">Gagné</div>
                  <div className="font-display text-3xl font-extrabold text-terracotta" data-testid="coop-feedback-xp">
                    +{feedback.xp_earned} XP
                  </div>
                </div>
              </div>
              {!feedback.is_correct && (
                <p className="text-navy/80 mb-3">
                  La bonne réponse était : <strong>{currentQ.options[feedback.correct_index]}</strong>
                </p>
              )}
              {feedback.explanation && (
                <p className="text-navy/70 italic bg-white/60 rounded-xl p-3 mb-4">
                  💡 {feedback.explanation}
                </p>
              )}
              <button
                data-testid="coop-next"
                onClick={onNext}
                className="w-full inline-flex items-center justify-center gap-2 bg-navy hover:bg-navy-dark text-white font-bold px-6 py-4 rounded-full text-lg transition"
              >
                {feedback.completed ? "Voir le résultat final" : "Question suivante"} <ArrowRight className="w-5 h-5" />
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      </main>
      <Footer />
    </div>
  );
}

function FinalResults({ challenge, onReplay }) {
  const s = challenge.stats_coop || {};
  const total = challenge.total;
  const helpsUsed = s.helps_used || 0;
  const helpsSuccessful = s.helps_successful || 0;
  const correct = s.correct_count || 0;
  const totalXp = s.total_xp || 0;
  const accuracy = total ? Math.round((correct / total) * 100) : 0;

  return (
    <div className="min-h-screen paper-bg">
      <Navbar variant="app" />
      <main className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <div className="bg-navy text-cream rounded-[32px] p-8 text-center mb-5" data-testid="coop-final-card">
          <Trophy className="w-14 h-14 mx-auto text-mustard mb-3" />
          <div className="text-xs font-bold uppercase tracking-wider text-mustard mb-2">Défi terminé</div>
          <h1 className="font-display text-4xl md:text-5xl font-extrabold mb-3">
            {challenge.team_name}
          </h1>
          <div className="font-display text-6xl font-extrabold text-mustard mb-1" data-testid="coop-final-xp">
            {totalXp} XP
          </div>
          <p className="text-cream/80">
            {correct}/{total} bonnes réponses · {accuracy}% de réussite
          </p>
        </div>

        <div className="grid grid-cols-2 gap-3 mb-5">
          <div className="bg-white border-2 border-cream-dark rounded-2xl p-4 text-center">
            <HandHelping className="w-7 h-7 mx-auto text-terracotta mb-1" />
            <div className="font-display text-3xl font-extrabold text-navy" data-testid="coop-final-helps">{helpsUsed}</div>
            <div className="text-xs font-bold uppercase tracking-wider text-navy/60">aide{helpsUsed > 1 ? "s" : ""} demandée{helpsUsed > 1 ? "s" : ""}</div>
          </div>
          <div className="bg-white border-2 border-cream-dark rounded-2xl p-4 text-center">
            <Heart className="w-7 h-7 mx-auto text-bordeaux fill-current mb-1" />
            <div className="font-display text-3xl font-extrabold text-navy" data-testid="coop-final-helps-ok">{helpsSuccessful}</div>
            <div className="text-xs font-bold uppercase tracking-wider text-navy/60">sauvée{helpsSuccessful > 1 ? "s" : ""}</div>
          </div>
        </div>

        {helpsSuccessful > 0 && (
          <div className="bg-mustard/30 border-2 border-mustard-dark rounded-2xl p-4 mb-5 flex items-center gap-3" data-testid="coop-coop-message">
            <Sparkles className="w-6 h-6 text-bordeaux shrink-0" />
            <p className="text-navy">
              <strong>{challenge.players[0].name}</strong> et <strong>{challenge.players[1].name}</strong> se sont sauvés mutuellement {helpsSuccessful} fois.
              Voilà l&apos;esprit GénéraQuiz ! 🧡
            </p>
          </div>
        )}

        <div className="grid sm:grid-cols-2 gap-3">
          <button
            onClick={onReplay}
            data-testid="coop-replay"
            className="inline-flex items-center justify-center gap-2 bg-terracotta hover:bg-terracotta-dark text-white font-bold px-6 py-4 rounded-full text-lg shadow-warm transition"
          >
            <RefreshCcw className="w-5 h-5" /> Refaire un défi
          </button>
          <Link
            to="/app/challenges"
            data-testid="coop-final-home"
            className="inline-flex items-center justify-center gap-2 bg-white border-2 border-cream-dark hover:border-navy text-navy font-bold px-6 py-4 rounded-full text-lg transition"
          >
            <Home className="w-5 h-5" /> Mes défis
          </Link>
        </div>
      </main>
      <Footer />
    </div>
  );
}
