import { useEffect, useState, useRef, useMemo } from "react";
import { useParams, Link } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { api, BACKEND_URL } from "@/lib/api";
import { Sparkles, ChevronRight, Trophy, ArrowRight, Check, X } from "lucide-react";

// Fisher-Yates: shuffle options + return mapping[displayedIdx] = originalIdx
function shuffleOptions(options) {
  const indexes = options.map((_, i) => i);
  for (let i = indexes.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [indexes[i], indexes[j]] = [indexes[j], indexes[i]];
  }
  return {
    options: indexes.map((i) => options[i]),
    mapping: indexes,
  };
}

export default function ChallengePlay() {
  const { token } = useParams();
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");
  const [stage, setStage] = useState("intro"); // intro | playing | done | error
  const [name, setName] = useState("");
  const [idx, setIdx] = useState(0);
  const [selected, setSelected] = useState(null);
  const [answers, setAnswers] = useState([]);
  const [result, setResult] = useState(null);
  const startTime = useRef(null);

  useEffect(() => {
    api
      .get(`/challenges/${token}`)
      .then((r) => setData(r.data))
      .catch((e) => {
        setErr(e.response?.data?.detail || "Défi introuvable");
        setStage("error");
      });
  }, [token]);

  // Always-called hook for shuffling — placed before any conditional return.
  const currentQ = data?.questions?.[idx];
  const shuffled = useMemo(() => {
    if (!currentQ) return null;
    return shuffleOptions(currentQ.options);
  }, [currentQ?.id, idx]);

  if (stage === "error" || err) {
    return (
      <div className="min-h-screen paper-bg flex items-center justify-center p-6">
        <div className="bg-white border-2 border-cream-dark rounded-3xl p-10 text-center max-w-md">
          <h1 className="font-display text-3xl font-extrabold text-navy mb-3">Oups !</h1>
          <p className="text-navy/70 text-lg mb-6">{err || "Ce défi n'est plus disponible."}</p>
          <Link to="/" className="inline-flex items-center gap-2 bg-terracotta text-white font-bold px-5 py-3 rounded-full">
            Aller sur Quiz d'Antan
          </Link>
        </div>
      </div>
    );
  }

  if (!data) {
    return <div className="min-h-screen paper-bg flex items-center justify-center text-navy text-xl">Chargement...</div>;
  }

  const start = () => {
    if (!name.trim()) return;
    setStage("playing");
    setIdx(0); setAnswers([]); setSelected(null); setResult(null);
    startTime.current = Date.now();
  };

  const q = data.questions[idx];

  const pick = (i) => {
    if (selected !== null) return;
    setSelected(i);
  };

  const next = async () => {
    // Map the displayed (shuffled) index back to the original index before submitting to server
    const originalIdx = shuffled ? shuffled.mapping[selected] : selected;
    const newAnswers = [...answers, originalIdx];
    setAnswers(newAnswers);
    setSelected(null);
    if (idx + 1 >= data.questions.length) {
      try {
        const duration = Math.round((Date.now() - startTime.current) / 1000);
        const { data: r } = await api.post(`/challenges/${token}/participate`, {
          name: name.trim(),
          answers: newAnswers,
          duration_seconds: duration,
        });
        setResult(r);
        setStage("done");
      } catch (e) {
        setErr(e.response?.data?.detail || "Erreur");
      }
    } else {
      setIdx(idx + 1);
    }
  };

  return (
    <div className="min-h-screen paper-bg">
      {/* Slim public header */}
      <header className="bg-navy text-white py-3 border-b-2 border-mustard">
        <div className="max-w-4xl mx-auto px-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-mustard" />
            <span className="font-display text-xl font-bold">Quiz d'Antan</span>
          </Link>
          <span className="text-mustard font-bold text-sm tracking-wide uppercase">Défi famille</span>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <AnimatePresence mode="wait">
          {stage === "intro" && (
            <motion.div
              key="intro"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="bg-white border-4 border-navy rounded-[32px] p-8 md:p-12 shadow-warm text-center"
            >
              {data.category_mascot_image && (
                <div className="w-32 h-32 mx-auto rounded-3xl overflow-hidden bg-cream border-4 border-mustard mb-5 float-anim">
                  <img src={`${BACKEND_URL}${data.category_mascot_image}`} alt="" className="w-full h-full object-cover" />
                </div>
              )}
              <div className="inline-flex items-center gap-2 bg-mustard text-navy font-bold px-3 py-1 rounded-full text-sm mb-3">
                Défi de {data.creator_name}
              </div>
              <h1 className="font-display text-4xl md:text-5xl font-extrabold text-navy mb-3">
                {data.category_title}
              </h1>
              <p className="text-xl text-navy/70 mb-7">
                {data.total} questions vous attendent ! Saurez-vous battre les autres ?
              </p>

              <div className="max-w-md mx-auto mb-5">
                <label className="block text-left font-bold text-navy mb-2">Votre prénom</label>
                <input
                  data-testid="play-name-input"
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Ex : Lucas, Mamie, Papi..."
                  maxLength={40}
                  className="w-full text-lg p-4 rounded-2xl border-2 border-cream-dark focus:border-navy bg-white min-h-[56px]"
                />
              </div>

              <button
                data-testid="play-start-btn"
                onClick={start}
                disabled={!name.trim()}
                className="inline-flex items-center gap-2 bg-terracotta hover:bg-terracotta-dark text-white font-bold text-lg px-8 py-4 rounded-full shadow-warm min-h-[60px] disabled:opacity-50 transition"
              >
                Commencer le défi <ArrowRight className="w-5 h-5" />
              </button>

              {data.participants.length > 0 && (
                <div className="mt-8 pt-6 border-t-2 border-cream-dark">
                  <h3 className="font-display text-lg font-bold text-navy mb-3">
                    <Trophy className="w-5 h-5 inline mr-2 text-mustard-dark" />
                    Déjà joué par
                  </h3>
                  <div className="flex flex-wrap gap-2 justify-center">
                    {data.participants.slice(0, 5).map((p, i) => (
                      <span key={i} className="bg-cream border border-cream-dark rounded-full px-3 py-1 text-sm">
                        {p.name} <strong className="text-bordeaux">{p.score}/{p.total}</strong>
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </motion.div>
          )}

          {stage === "playing" && (
            <motion.div
              key={`q${idx}`}
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0 }}
              className="bg-white border-4 border-navy rounded-[32px] p-6 md:p-10 shadow-warm"
            >
              <div className="flex items-center justify-between mb-5">
                <span className="text-sm font-bold uppercase tracking-wider text-navy/60">
                  Question {idx + 1} / {data.total}
                </span>
                <span className="bg-cream border-2 border-cream-dark text-navy font-bold px-3 py-1 rounded-full text-sm">
                  Joueur : {name}
                </span>
              </div>
              <div className="w-full bg-cream rounded-full h-3 mb-7 overflow-hidden">
                <div className="bg-terracotta h-3" style={{ width: `${((idx + (selected !== null ? 1 : 0)) / data.total) * 100}%` }} />
              </div>

              <h2 data-testid="play-question" className="font-display text-2xl md:text-3xl font-extrabold text-navy leading-snug mb-7">
                {q.question}
              </h2>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
                {shuffled && shuffled.options.map((opt, i) => {
                  let cls = "bg-white border-2 border-cream-dark text-navy hover:border-terracotta hover:bg-terracotta/5";
                  if (selected !== null) {
                    if (i === selected) cls = "bg-navy text-white border-2 border-navy";
                    else cls = "bg-cream border-2 border-cream-dark text-navy/50";
                  }
                  return (
                    <motion.button
                      key={i}
                      data-testid={`play-option-${i}`}
                      whileHover={selected === null ? { scale: 1.02 } : {}}
                      whileTap={selected === null ? { scale: 0.98 } : {}}
                      onClick={() => pick(i)}
                      disabled={selected !== null}
                      className={`text-left px-6 py-5 rounded-2xl font-semibold text-lg transition min-h-[72px] ${cls}`}
                    >
                      <span className="font-display text-xl mr-2 text-terracotta">{String.fromCharCode(65 + i)}.</span>
                      {opt}
                    </motion.button>
                  );
                })}
              </div>

              {selected !== null && (
                <div className="flex justify-end">
                  <button
                    onClick={next}
                    data-testid="play-next-btn"
                    className="inline-flex items-center gap-2 bg-terracotta hover:bg-terracotta-dark text-white font-bold text-lg px-7 py-4 rounded-full shadow-warm min-h-[56px] transition"
                  >
                    {idx + 1 >= data.total ? "Valider mes réponses" : "Question suivante"}
                    <ChevronRight className="w-5 h-5" />
                  </button>
                </div>
              )}
            </motion.div>
          )}

          {stage === "done" && result && (
            <motion.div
              key="done"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="bg-white border-4 border-mustard rounded-[32px] p-8 md:p-12 shadow-warm"
            >
              <div className="text-center mb-8">
                <div className="text-7xl mb-4 pop-anim">
                  {result.score === result.total ? "🏆" : result.score >= result.total / 2 ? "⭐" : "💪"}
                </div>
                <h2 className="font-display text-4xl font-extrabold text-navy mb-2">Bravo {name} !</h2>
                <p className="text-2xl text-navy/80">
                  Score :{" "}
                  <span className="font-display font-extrabold text-bordeaux text-3xl">
                    {result.score} / {result.total}
                  </span>
                </p>
              </div>

              {/* Detail per question */}
              <div className="space-y-2 mb-7">
                {result.detail.map((d, i) => (
                  <div
                    key={i}
                    data-testid={`play-detail-${i}`}
                    className={`flex items-start gap-3 p-3 rounded-2xl border-2 ${
                      d.is_correct
                        ? "bg-[#3D9970]/10 border-[#3D9970]/40"
                        : "bg-[#D9534F]/10 border-[#D9534F]/40"
                    }`}
                  >
                    {d.is_correct ? (
                      <Check className="w-5 h-5 text-[#3D9970] mt-1 shrink-0" strokeWidth={3} />
                    ) : (
                      <X className="w-5 h-5 text-[#D9534F] mt-1 shrink-0" strokeWidth={3} />
                    )}
                    <div className="text-sm text-navy/80">
                      <div className="font-bold mb-1">Question {i + 1}</div>
                      <div>{d.explanation}</div>
                    </div>
                  </div>
                ))}
              </div>

              {/* Mini leaderboard */}
              <div data-testid="play-leaderboard" className="bg-cream rounded-2xl p-5">
                <h3 className="font-display text-xl font-bold text-navy mb-3 flex items-center gap-2">
                  <Trophy className="w-5 h-5 text-mustard-dark" /> Classement
                </h3>
                <ol className="space-y-2">
                  {result.leaderboard.map((p, i) => {
                    const isMe = p.name === name && i === result.leaderboard.findIndex((x) => x.name === name);
                    return (
                      <li
                        key={`${p.name}-${p.completed_at}`}
                        className={`flex items-center justify-between p-3 rounded-xl ${
                          isMe ? "bg-mustard/40 border-2 border-mustard-dark" : "bg-white border border-cream-dark"
                        }`}
                      >
                        <div className="flex items-center gap-3">
                          <span className="font-display text-lg font-extrabold text-navy w-8 text-center">
                            {["🥇", "🥈", "🥉"][i] || `#${i + 1}`}
                          </span>
                          <span className="font-bold text-navy">{p.name}{isMe ? " (vous)" : ""}</span>
                        </div>
                        <span className="font-display font-extrabold text-bordeaux">{p.score}/{p.total}</span>
                      </li>
                    );
                  })}
                </ol>
              </div>

              <div className="mt-6 text-center">
                <Link
                  to="/register"
                  data-testid="play-cta-register"
                  className="inline-flex items-center gap-2 bg-terracotta hover:bg-terracotta-dark text-white font-bold px-6 py-3 rounded-full shadow-warm"
                >
                  Créer mon compte Quiz d'Antan <ArrowRight className="w-5 h-5" />
                </Link>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}
