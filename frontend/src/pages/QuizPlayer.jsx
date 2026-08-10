import { useEffect, useState, useRef, useMemo } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { api, BACKEND_URL } from "@/lib/api";
import { showBadgeToasts } from "@/lib/badgeToast";
import Navbar from "@/components/Navbar";
import { ArrowLeft, ChevronRight, RotateCcw, Volume2, Crown, Check, X } from "lucide-react";
import ScoreCard from "@/components/ScoreCard";
import ReportButton from "@/components/ReportButton";

// Fisher-Yates shuffle helper that returns the new options + the new correct index.
function shuffleOptions(options, correctIndex) {
  const indexes = options.map((_, i) => i);
  for (let i = indexes.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [indexes[i], indexes[j]] = [indexes[j], indexes[i]];
  }
  return {
    options: indexes.map((i) => options[i]),
    newCorrectIdx: indexes.indexOf(correctIndex),
    // mapping[displayedIdx] = originalIdx — useful when answers must be submitted with original index
    mapping: indexes,
  };
}

export default function QuizPlayer() {
  const { categoryId } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");
  const [idx, setIdx] = useState(0);
  const [selected, setSelected] = useState(null);
  const [score, setScore] = useState(0);
  const [finished, setFinished] = useState(false);
  // Collected answers to send to the server for authoritative scoring.
  // Each entry: {question_id, answer_index} using the ORIGINAL question index
  // (mapped back from the shuffled display order).
  const [answers, setAnswers] = useState([]);
  const startTime = useRef(Date.now());

  // États du mode défi famille : plusieurs joueurs peuvent se relayer sur une même question.
  const [familyMode, setFamilyMode] = useState(false);
  const [members, setMembers] = useState([]);           // prénoms saisis
  const [responderIdx, setResponderIdx] = useState(0);  // index du répondant actuel
  const [passCount, setPassCount] = useState(0);        // nb de passes sur la question en cours
  const [scoreByMember, setScoreByMember] = useState({}); // {prénom: nb bonnes réponses}
  const [setupDone, setSetupDone] = useState(false);    // true quand l'écran setup est fermé
  const [newMember, setNewMember] = useState("");
  const [questionResponders, setQuestionResponders] = useState({}); // {questionId: prénom du bon répondant}

  useEffect(() => {
    api
      .get(`/categories/${categoryId}/questions`)
      .then((r) => setData(r.data))
      .catch((e) => setErr(e.response?.data?.detail || "Erreur de chargement"));
  }, [categoryId]);

  // Always-called hook: shuffle options for the current question.
  // Computed before any conditional return to respect Rules of Hooks.
  const currentQ = data?.questions?.[idx];
  const shuffled = useMemo(() => {
    if (!currentQ) return null;
    return shuffleOptions(currentQ.options, currentQ.correct_index);
  }, [currentQ?.id, idx]);

  if (err)
    return (
      <div className="min-h-screen paper-bg">
        <Navbar variant="app" />
        <div className="max-w-3xl mx-auto p-12 text-center">
          <p className="text-navy text-xl mb-6">{err}</p>
          <Link to="/app/dashboard" className="text-terracotta font-bold underline">Retour au tableau de bord</Link>
        </div>
      </div>
    );

  if (!data) {
    return (
      <div className="min-h-screen paper-bg">
        <Navbar variant="app" />
        <div className="max-w-3xl mx-auto p-12 text-center text-navy/60 text-xl">Chargement...</div>
      </div>
    );
  }

  const { category, questions, is_premium } = data;
  const total = questions.length;
  const q = questions[idx];
  const currentMember = familyMode && members.length > 0 ? members[responderIdx] : null;
  const hasOtherResponders = familyMode && selected === null && members.length > 1 && passCount < members.length - 1;
  const isLastFamilyChance = familyMode && selected === null && members.length > 1 && passCount >= members.length - 1;

  const speak = (text) => {
    try {
      const u = new SpeechSynthesisUtterance(text);
      u.lang = "fr-FR";
      u.rate = 0.92;
      window.speechSynthesis.cancel();
      window.speechSynthesis.speak(u);
    } catch {}
  };

  // Ajoute un prénom au défi famille, avec une limite de 6 joueurs.
  const addMember = () => {
    const name = newMember.trim();
    if (!name || members.length >= 6) return;
    setMembers((prev) => [...prev, name]);
    setScoreByMember((prev) => ({ ...prev, [name]: prev[name] ?? 0 }));
    setNewMember("");
  };

  // Supprime un prénom saisi avant le lancement du défi famille.
  const removeMember = (nameToRemove) => {
    setMembers((prev) => prev.filter((name) => name !== nameToRemove));
    setScoreByMember((prev) => {
      const next = { ...prev };
      delete next[nameToRemove];
      return next;
    });
  };

  // Lance le quiz en solo sans changer la mécanique existante.
  const startSolo = () => {
    setFamilyMode(false);
    setSetupDone(true);
    startTime.current = Date.now();
  };

  // Lance le défi famille après validation d'au moins deux prénoms.
  const startFamilyChallenge = () => {
    if (members.length < 2) return;
    setFamilyMode(true);
    setResponderIdx(0);
    setPassCount(0);
    setScoreByMember(members.reduce((acc, name) => ({ ...acc, [name]: 0 }), {}));
    setQuestionResponders({});
    setSetupDone(true);
    startTime.current = Date.now();
  };

  const onSelect = (i) => {
    if (selected !== null) return;
    setSelected(i);
    if (shuffled) {
      if (i === shuffled.newCorrectIdx) {
        setScore((s) => s + 1);
        if (familyMode && currentMember) {
          // Le point revient au membre qui a effectivement trouvé la bonne réponse.
          setScoreByMember((prev) => ({
            ...prev,
            [currentMember]: (prev[currentMember] ?? 0) + 1,
          }));
          setQuestionResponders((prev) => ({
            ...prev,
            [q.id ?? idx]: currentMember,
          }));
        }
      }
      // Record this answer using the ORIGINAL option index for server verification
      const originalIdx = shuffled.mapping[i];
      setAnswers((prev) => [...prev, { question_id: currentQ.id, answer_index: originalIdx }]);
    }
  };

  const onNext = () => {
    if (idx + 1 >= total) {
      const dur = Math.round((Date.now() - startTime.current) / 1000);
      api.post("/attempts", {
        category_id: categoryId,
        answers,
        duration_seconds: dur,
      }).then((r) => showBadgeToasts(r.data?.awarded_badges)).catch(() => {});
      setFinished(true);
    } else {
      setIdx((v) => v + 1);
      setSelected(null);
      setPassCount(0);
      if (familyMode && members.length > 0) {
        setResponderIdx((v) => (v + 1) % members.length);
      }
    }
  };

  // Passe la main au prochain membre ; si tout le monde passe, la question est ratée.
  const onPass = () => {
    if (!familyMode || selected !== null || members.length < 2) return;

    if (passCount + 1 >= members.length) {
      onNext();
      return;
    }

    setPassCount((v) => v + 1);
    setResponderIdx((v) => (v + 1) % members.length);
  };

  const restart = () => {
    setIdx(0); setSelected(null); setScore(0); setFinished(false);
    setAnswers([]);
    setResponderIdx(0); setPassCount(0); setQuestionResponders({});
    setScoreByMember(members.reduce((acc, name) => ({ ...acc, [name]: 0 }), {}));
    startTime.current = Date.now();
  };

  return (
    <div className="min-h-screen paper-bg">
      <Navbar variant="app" />

      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <button
          onClick={() => navigate("/app/dashboard")}
          data-testid="quiz-back"
          className="inline-flex items-center gap-2 text-navy hover:text-terracotta font-bold mb-6"
        >
          <ArrowLeft className="w-5 h-5" /> Retour au tableau de bord
        </button>

        {/* Header with mascot */}
        <div className="bg-white border-2 border-cream-dark rounded-[28px] p-6 md:p-8 mb-6 flex items-center gap-5">
          <div className="w-20 h-20 rounded-2xl overflow-hidden bg-cream border-2 border-cream-dark shrink-0">
            <img src={`${BACKEND_URL}${category.mascot_image}`} alt={category.mascot_name} className="w-full h-full object-cover" />
          </div>
          <div className="flex-1">
            <div className="text-xs font-bold uppercase tracking-wider text-navy/60">Catégorie</div>
            <h1 className="font-display text-2xl md:text-3xl font-extrabold text-navy">{category.title}</h1>
            <p className="text-navy/70 text-base">Animée par {category.mascot_name}</p>
          </div>
          {!is_premium && (
            <Link to="/app/pricing" className="hidden md:inline-flex items-center gap-2 bg-mustard hover:bg-mustard-dark text-navy font-bold px-4 py-2 rounded-full text-sm">
              <Crown className="w-4 h-4" /> Plus de questions
            </Link>
          )}
        </div>

        {/* Quiz card */}
        <AnimatePresence mode="wait">
          {!setupDone ? (
            <motion.div
              key="setup"
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0 }}
              className="bg-white border-4 border-navy rounded-[32px] p-6 md:p-10 shadow-warm"
            >
              <div className="text-center mb-8">
                <h2 className="font-display text-3xl md:text-4xl font-extrabold text-navy mb-3">
                  Comment voulez-vous jouer ?
                </h2>
                <p className="text-navy/70 text-lg">
                  Lancez une partie classique ou créez un défi où chaque génération peut aider la famille.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
                <button
                  onClick={startSolo}
                  data-testid="quiz-start-solo"
                  className="bg-cream hover:bg-mustard border-2 border-cream-dark text-navy rounded-2xl p-6 text-left transition"
                >
                  <span className="font-display text-2xl font-extrabold block mb-2">Jouer seul</span>
                  <span className="text-navy/70">Le quiz démarre avec les règles habituelles.</span>
                </button>
                <button
                  onClick={() => setFamilyMode(true)}
                  data-testid="quiz-choose-family"
                  className="bg-white hover:bg-terracotta/5 border-2 border-terracotta text-navy rounded-2xl p-6 text-left transition"
                >
                  <span className="font-display text-2xl font-extrabold block mb-2">Défi famille</span>
                  <span className="text-navy/70">Passez la main si quelqu'un ne sait pas répondre.</span>
                </button>
              </div>

              {familyMode && (
                <div className="bg-cream border-2 border-cream-dark rounded-2xl p-5">
                  <h3 className="font-display text-2xl font-bold text-navy mb-4">Prénoms des joueurs</h3>
                  <div className="flex flex-col sm:flex-row gap-3 mb-4">
                    <input
                      type="text"
                      value={newMember}
                      onChange={(e) => setNewMember(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") {
                          e.preventDefault();
                          addMember();
                        }
                      }}
                      data-testid="quiz-family-name"
                      placeholder="Ex. Marie"
                      disabled={members.length >= 6}
                      className="flex-1 bg-white border-2 border-cream-dark rounded-full px-5 py-3 text-navy font-semibold outline-none focus:border-terracotta"
                    />
                    <button
                      onClick={addMember}
                      disabled={!newMember.trim() || members.length >= 6}
                      data-testid="quiz-family-add"
                      className="bg-navy hover:bg-navy-dark disabled:bg-navy/30 text-white font-bold px-6 py-3 rounded-full transition"
                    >
                      Ajouter
                    </button>
                  </div>

                  <div className="flex flex-wrap gap-2 mb-5">
                    {members.length === 0 ? (
                      <p className="text-navy/60">Ajoutez 2 à 6 prénoms pour commencer.</p>
                    ) : (
                      members.map((name) => (
                        <span key={name} className="inline-flex items-center gap-2 bg-white border-2 border-cream-dark rounded-full px-4 py-2 text-navy font-bold">
                          {name}
                          <button
                            type="button"
                            onClick={() => removeMember(name)}
                            className="text-navy/50 hover:text-terracotta"
                            aria-label={`Supprimer ${name}`}
                          >
                            ×
                          </button>
                        </span>
                      ))
                    )}
                  </div>

                  <button
                    onClick={startFamilyChallenge}
                    disabled={members.length < 2}
                    data-testid="quiz-start-family"
                    className="w-full sm:w-auto bg-terracotta hover:bg-terracotta-dark disabled:bg-terracotta/30 text-white font-bold px-8 py-4 rounded-full shadow-warm transition"
                  >
                    Commencer le défi
                  </button>
                </div>
              )}
            </motion.div>
          ) : !finished ? (
            <motion.div
              key="quiz"
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0 }}
              className="bg-white border-4 border-navy rounded-[32px] p-6 md:p-10 shadow-warm"
            >
              <div className="flex items-center justify-between mb-5">
                <span className="text-base sm:text-lg font-bold uppercase tracking-wider text-navy/60">
                  Question {idx + 1} / {total}
                </span>
                <span className="bg-cream border-2 border-cream-dark text-navy font-bold px-4 py-2 rounded-full text-base">
                  Score : {score}/{idx + (selected !== null ? 1 : 0)}
                </span>
              </div>

              <div className="w-full bg-cream rounded-full h-3 mb-8 overflow-hidden">
                <div
                  className="bg-terracotta h-3 rounded-full transition-all duration-500"
                  style={{ width: `${((idx + (selected !== null ? 1 : 0)) / total) * 100}%` }}
                />
              </div>

              {familyMode && currentMember && (
                <div className="bg-cream border-2 border-cream-dark rounded-2xl px-5 py-4 mb-6 text-center">
                  <p className="text-navy font-display text-2xl font-extrabold">
                    À {currentMember} de répondre
                  </p>
                  {isLastFamilyChance && (
                    <p className="text-terracotta font-bold mt-1">Dernière chance !</p>
                  )}
                </div>
              )}

              <div className="flex items-start gap-4 mb-8">
                <h2 className="font-display text-3xl md:text-4xl lg:text-5xl font-extrabold text-navy leading-snug flex-1" data-testid="quiz-question">
                  {q.question}
                </h2>
                <button
                  onClick={() => speak(q.question)}
                  data-testid="quiz-speak"
                  className="shrink-0 p-4 rounded-2xl bg-cream hover:bg-mustard transition border-2 border-cream-dark"
                  aria-label="Lire la question à voix haute"
                  title="Lire la question à voix haute"
                >
                  <Volume2 className="w-7 h-7 text-navy" />
                </button>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
                {shuffled && shuffled.options.map((opt, i) => {
                  let cls = "bg-white border-2 border-cream-dark text-navy hover:border-terracotta hover:bg-terracotta/5";
                  let icon = null;
                  if (selected !== null) {
                    if (i === shuffled.newCorrectIdx) {
                      cls = "bg-[#3D9970]/15 border-2 border-[#3D9970] text-navy";
                      icon = <Check className="w-6 h-6 text-[#3D9970]" strokeWidth={3} />;
                    } else if (i === selected) {
                      cls = "bg-[#D9534F]/15 border-2 border-[#D9534F] text-navy";
                      icon = <X className="w-6 h-6 text-[#D9534F]" strokeWidth={3} />;
                    } else {
                      cls = "bg-cream border-2 border-cream-dark text-navy/50";
                    }
                  }
                  return (
                    <motion.button
                      key={i}
                      data-testid={`quiz-option-${i}`}
                      whileHover={selected === null ? { scale: 1.02 } : {}}
                      whileTap={selected === null ? { scale: 0.98 } : {}}
                      onClick={() => onSelect(i)}
                      disabled={selected !== null}
                      className={`text-left px-6 py-6 rounded-2xl font-semibold text-xl md:text-2xl leading-snug transition min-h-[96px] flex items-center justify-between ${cls}`}
                    >
                      <span>
                        <span className="font-display text-2xl md:text-3xl mr-3 text-terracotta">{String.fromCharCode(65 + i)}.</span>
                        {opt}
                      </span>
                      {icon}
                    </motion.button>
                  );
                })}
              </div>

              {hasOtherResponders && (
                <div className="mb-6 text-center">
                  <button
                    onClick={onPass}
                    data-testid="quiz-family-pass"
                    className="w-full sm:w-auto border-2 border-dashed border-navy/30 text-navy/60 hover:text-navy hover:border-navy/50 font-bold px-6 py-4 rounded-2xl transition"
                  >
                    Je ne sais pas — passer
                  </button>
                </div>
              )}

              <AnimatePresence>
                {selected !== null && shuffled && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    className={`rounded-2xl p-5 mb-6 border-2 ${
                      selected === shuffled.newCorrectIdx
                        ? "bg-[#3D9970]/10 border-[#3D9970]/40"
                        : "bg-[#D9534F]/10 border-[#D9534F]/40"
                    }`}
                    data-testid="quiz-feedback"
                  >
                    <p className="font-display text-2xl font-bold text-navy mb-2">
                      {selected === shuffled.newCorrectIdx ? "✅ Bonne réponse !" : "❌ Presque !"}
                    </p>
                    <p className="text-navy/80 text-lg leading-relaxed">{q.explanation}</p>
                  </motion.div>
                )}
              </AnimatePresence>

              {selected !== null && (
                <div className="flex justify-between items-center gap-3">
                  <ReportButton questionId={q.id} />
                  <button
                    onClick={onNext}
                    data-testid="quiz-next"
                    className="inline-flex items-center gap-2 bg-navy hover:bg-navy-dark text-white font-bold text-xl px-10 py-5 rounded-full transition min-h-[64px] shadow-soft"
                  >
                    {idx + 1 >= total ? "Voir mon score" : "Question suivante"}
                    <ChevronRight className="w-6 h-6" />
                  </button>
                </div>
              )}
            </motion.div>
          ) : (
            <motion.div
              key="finished"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="bg-white border-4 border-mustard rounded-[32px] p-8 md:p-12 text-center shadow-warm"
            >
              <div className="text-7xl mb-5 pop-anim">{score === total ? "🏆" : score >= total / 2 ? "⭐" : "💪"}</div>
              <h2 className="font-display text-4xl md:text-5xl font-extrabold text-navy mb-3">
                {score === total ? "Parfait !" : score >= total / 2 ? "Bravo !" : "Continuez !"}
              </h2>
              <p className="text-2xl text-navy/80 mb-2">
                Votre score :{" "}
                <span className="font-display font-extrabold text-bordeaux text-3xl">{score} / {total}</span>
              </p>

              {familyMode && members.length > 0 && (
                <div className="bg-cream border-2 border-cream-dark rounded-2xl p-5 my-6 text-left">
                  <h3 className="font-display text-2xl font-bold text-navy mb-3 text-center">Contributions de la famille</h3>
                  <p className="text-navy/80 text-lg text-center leading-relaxed">
                    {members.map((name, i) => {
                      const count = scoreByMember[name] ?? 0;
                      const label = count === 0
                        ? `${name} : 0 réponse`
                        : `${name} a répondu à ${count} question${count > 1 ? "s" : ""}`;
                      return `${label}${i < members.length - 1 ? " · " : ""}`;
                    }).join("")}
                  </p>
                </div>
              )}

              <p className="text-lg text-navy/60 mb-8">
                {score === total
                  ? "Vous êtes une mémoire vivante !"
                  : score >= total / 2
                  ? "Belle performance, vos souvenirs sont vifs."
                  : "La pratique rend parfait — essayez encore !"}
              </p>
              {!is_premium && total < 10 && (
                <div className="bg-mustard/30 border-2 border-mustard-dark rounded-2xl p-5 mb-6">
                  <p className="text-navy font-medium mb-3">
                    Vous jouez avec la formule Découverte (5 questions par quiz).
                    Passez en <strong>Premium</strong> pour 30 questions et toutes les activités.
                  </p>
                  <Link
                    to="/app/pricing"
                    data-testid="quiz-upgrade"
                    className="inline-flex items-center gap-2 bg-terracotta hover:bg-terracotta-dark text-white font-bold px-6 py-3 rounded-full shadow-warm"
                  >
                    <Crown className="w-5 h-5" /> Passer Premium
                  </Link>
                </div>
              )}
              <div className="flex flex-wrap gap-3 justify-center mb-8">
                <button
                  onClick={restart}
                  data-testid="quiz-restart"
                  className="inline-flex items-center gap-2 bg-terracotta hover:bg-terracotta-dark text-white font-bold px-6 py-4 rounded-full shadow-warm min-h-[56px]"
                >
                  <RotateCcw className="w-5 h-5" /> Rejouer
                </button>
                <Link
                  to="/app/dashboard"
                  data-testid="quiz-back-dashboard"
                  className="inline-flex items-center gap-2 bg-white border-2 border-navy text-navy hover:bg-navy hover:text-white font-bold px-6 py-4 rounded-full min-h-[56px]"
                >
                  Autres catégories <ChevronRight className="w-5 h-5" />
                </Link>
              </div>

              {/* ============ SHAREABLE SCORE CARD ============ */}
              <ScoreCard
                title={category.title}
                subtitle="Catégorie"
                score={score}
                total={total}
                mascotImage={category.mascot_image}
                mascotName={category.mascot_name}
                shareText={`🎯 J'ai fait ${score}/${total} en ${category.title} sur GénéraQuiz ! Saurez-vous battre mon score ?`}
                shareUrl={`${window.location.origin}/quiz-du-jour`}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}
