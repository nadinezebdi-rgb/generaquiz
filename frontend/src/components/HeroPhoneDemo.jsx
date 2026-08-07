import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Check, X, Flame, Trophy, Sparkles } from "lucide-react";
import { BACKEND_URL } from "@/lib/api";

/**
 * HeroPhoneDemo — animated mockup showing the app's core loop
 * (question → answer → score bump → badge → confetti → reset).
 *
 * Runs a scripted loop with Framer Motion — no user interaction.
 * The visitor sees the value prop happen in front of them.
 */
const SCRIPT = [
  {
    mascot: "chansons.png",
    category: "Chansons françaises",
    mascotName: "Yvette la Chanteuse",
    question: "Qui a chanté « La Vie en rose » en 1945 ?",
    options: ["Charles Trenet", "Édith Piaf", "Brassens", "Brel"],
    correct: 1,
  },
  {
    mascot: "cinema.png",
    category: "Cinéma français",
    mascotName: "Michel du Cinéma",
    question: "Réalisateur de « La Grande Vadrouille » ?",
    options: ["Truffaut", "Gérard Oury", "Godard", "Rohmer"],
    correct: 1,
  },
];

const STAGES = ["question", "reveal", "score", "reset"];
const STAGE_DURATIONS = { question: 2200, reveal: 1500, score: 1900, reset: 350 };

export default function HeroPhoneDemo() {
  const [stepIdx, setStepIdx] = useState(0);
  const [stage, setStage] = useState("question");
  const [score, setScore] = useState(1);
  const [streak, setStreak] = useState(3);

  const step = SCRIPT[stepIdx];

  useEffect(() => {
    const t = setTimeout(() => {
      const nextIdx = STAGES.indexOf(stage) + 1;
      if (nextIdx >= STAGES.length) {
        setStage("question");
        setStepIdx((i) => (i + 1) % SCRIPT.length);
        setScore((s) => s + 1);
        setStreak((s) => s + 1);
      } else {
        setStage(STAGES[nextIdx]);
      }
    }, STAGE_DURATIONS[stage]);
    return () => clearTimeout(t);
  }, [stage, stepIdx]);

  const revealed = stage === "reveal" || stage === "score";

  return (
    <div className="relative" data-testid="hero-phone-demo">
      <div className="absolute -inset-6 bg-mustard/40 rounded-[40px] rotate-3" />
      <div className="relative bg-white border-4 border-navy rounded-[36px] p-5 shadow-warm">

        {/* Header: mascot + streak */}
        <div className="flex items-center gap-3 mb-3">
          <img
            src={`${BACKEND_URL}/api/static/mascots/${step.mascot}`}
            alt=""
            className="w-14 h-14 rounded-2xl object-cover border-2 border-cream-dark"
          />
          <div className="flex-1 min-w-0">
            <div className="inline-block bg-terracotta text-white text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-widest">
              Quiz du Jour
            </div>
            <div className="font-display text-lg font-extrabold text-navy leading-tight truncate">{step.category}</div>
          </div>
          <motion.div
            key={`streak-${streak}`}
            initial={{ scale: 1 }}
            animate={{ scale: [1, 1.3, 1] }}
            className="flex items-center gap-1 bg-bordeaux text-cream px-2 py-1 rounded-full text-xs font-bold"
          >
            <Flame className="w-3.5 h-3.5 text-mustard" fill="currentColor" />
            {streak}j
          </motion.div>
        </div>

        {/* Progress bar */}
        <div className="h-1.5 bg-cream rounded-full overflow-hidden mb-4">
          <motion.div
            className="h-full bg-terracotta"
            initial={{ width: "20%" }}
            animate={{ width: stage === "score" ? "80%" : "40%" }}
            transition={{ duration: 0.5 }}
          />
        </div>

        {/* Question */}
        <div className="bg-cream border-2 border-cream-dark rounded-2xl p-4 mb-3">
          <p className="text-navy font-semibold text-sm leading-snug">{step.question}</p>
        </div>

        {/* Options */}
        <div className="grid grid-cols-2 gap-2 mb-3">
          {step.options.map((o, i) => {
            const isCorrect = i === step.correct;
            const highlight = revealed && isCorrect;
            return (
              <motion.div
                key={o}
                animate={highlight ? { scale: [1, 1.06, 1] } : {}}
                transition={{ duration: 0.4 }}
                className={`text-xs font-bold py-2 px-2 rounded-xl border-2 text-center leading-tight ${
                  highlight
                    ? "bg-[#3D9970] border-[#2A7350] text-white shadow-warm"
                    : "bg-white border-cream-dark text-navy/70"
                }`}
              >
                {highlight && <Check className="w-3 h-3 inline mr-0.5" strokeWidth={3} />}
                {o}
              </motion.div>
            );
          })}
        </div>

        {/* Score / badge stage */}
        <AnimatePresence mode="wait">
          {stage === "score" ? (
            <motion.div
              key="badge"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              className="bg-navy text-cream rounded-2xl p-3 flex items-center gap-3"
            >
              <div className="w-10 h-10 rounded-full bg-mustard flex items-center justify-center shrink-0 text-lg">
                🎯
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-[10px] font-bold uppercase tracking-widest text-mustard">Badge débloqué</div>
                <div className="font-display font-extrabold truncate">Premier pas</div>
              </div>
              <motion.div
                key={score}
                initial={{ scale: 0.5, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                className="font-display text-2xl font-extrabold text-mustard whitespace-nowrap"
              >
                +100
              </motion.div>
            </motion.div>
          ) : (
            <motion.div
              key="score"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="bg-cream border-2 border-cream-dark rounded-2xl p-3 flex items-center gap-3"
            >
              <Sparkles className="w-4 h-4 text-terracotta shrink-0" />
              <div className="flex-1 text-xs font-bold text-navy">
                {revealed ? "Excellente réponse !" : "À vous de jouer…"}
              </div>
              <div className="font-display text-lg font-extrabold text-terracotta">{score}/5</div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Confetti overlay for score stage */}
        <AnimatePresence>
          {stage === "score" &&
            Array.from({ length: 12 }).map((_, i) => (
              <motion.span
                key={`confetti-${stepIdx}-${i}`}
                initial={{ opacity: 0, y: 0, x: 0, rotate: 0 }}
                animate={{
                  opacity: [0, 1, 0],
                  y: -80 - Math.random() * 60,
                  x: (i - 6) * 12,
                  rotate: Math.random() * 360,
                }}
                exit={{ opacity: 0 }}
                transition={{ duration: 1.4, delay: i * 0.03 }}
                className="absolute top-1/2 left-1/2 pointer-events-none text-lg"
              >
                {["🎉", "✨", "🧡", "🥇", "🌟"][i % 5]}
              </motion.span>
            ))}
        </AnimatePresence>
      </div>

      {/* Corner sticker */}
      <div className="absolute -bottom-5 -right-5 bg-terracotta text-cream rounded-2xl px-4 py-2 font-bold shadow-warm rotate-3 flex items-center gap-1.5 text-sm">
        <Trophy className="w-4 h-4 text-mustard" fill="currentColor" />
        Ligue Or
      </div>
    </div>
  );
}
