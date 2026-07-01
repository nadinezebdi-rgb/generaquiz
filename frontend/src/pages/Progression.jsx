import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { api, BACKEND_URL } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import BadgeShareCard from "@/components/BadgeShareCard";
import {
  Trophy, Zap, TrendingUp, Loader2, Lock, Sparkles, Award, Flame, X, Share2,
} from "lucide-react";

/**
 * Progression — user level curve + per-category mastery + full badge catalog.
 *
 * Data sources (all authenticated):
 *   - GET /api/progression/me      → level, xp_progress, mastery[]
 *   - GET /api/badges/catalog      → full catalog with `earned` flag per user
 */

const TIER_STYLES = {
  novice:   { bg: "bg-cream-dark",           text: "text-navy/60",     bar: "bg-navy/25" },
  apprenti: { bg: "bg-mustard/40",           text: "text-navy",         bar: "bg-mustard-dark" },
  confirme: { bg: "bg-terracotta/30",        text: "text-terracotta-dark", bar: "bg-terracotta" },
  expert:   { bg: "bg-[#3D9970]/25",         text: "text-[#2A7350]",    bar: "bg-[#3D9970]" },
  maitre:   { bg: "bg-bordeaux/25",          text: "text-bordeaux",     bar: "bg-bordeaux" },
};
const BADGE_TIER_STYLES = {
  bronze:  "bg-[#B87333] text-white",
  argent:  "bg-[#9CA3AF] text-white",
  or:      "bg-mustard-dark text-navy",
  diamant: "bg-[#3FB8AF] text-white",
};

export default function Progression() {
  const { user } = useAuth();
  const [prog, setProg] = useState(null);
  const [badges, setBadges] = useState([]);
  const [loading, setLoading] = useState(true);
  const [shareBadge, setShareBadge] = useState(null);

  useEffect(() => {
    Promise.all([
      api.get("/progression/me").then((r) => setProg(r.data)),
      api.get("/badges/catalog").then((r) => setBadges(r.data)),
    ]).finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen paper-bg flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-terracotta" />
      </div>
    );
  }
  if (!prog) return null;

  const earnedCount = badges.filter((b) => b.earned).length;

  return (
    <div className="min-h-screen paper-bg">
      <Navbar variant="app" />
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-10">

        {/* ============ LEVEL HERO ============ */}
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-navy text-cream rounded-[32px] p-6 md:p-8 mb-6 relative overflow-hidden"
          data-testid="progression-hero"
        >
          <div className="absolute -top-16 -right-16 w-64 h-64 rounded-full bg-terracotta/15 blur-3xl pointer-events-none" />
          <div className="flex items-start gap-4 mb-6">
            <div className="w-20 h-20 rounded-3xl bg-terracotta flex items-center justify-center shadow-warm shrink-0">
              <span className="font-display text-4xl font-extrabold text-white" data-testid="progression-level">
                {prog.level}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <div className="inline-flex items-center gap-2 bg-white/10 text-cream/90 font-bold px-2.5 py-0.5 rounded-full text-xs mb-1 uppercase tracking-wider">
                <Zap className="w-3.5 h-3.5 text-mustard" /> Progression
              </div>
              <h1 className="font-display text-3xl md:text-4xl font-extrabold leading-tight">
                Niveau <span className="text-mustard italic">{prog.level}</span>
              </h1>
              <p className="text-cream/80 text-sm mt-1" data-testid="progression-xp-summary">
                {prog.xp_total.toLocaleString("fr-FR")} points au total · plus que {prog.xp_to_next} points pour le niveau {prog.level + 1}
              </p>
            </div>
          </div>

          {/* Progress bar */}
          <div className="mb-1 flex items-center justify-between text-xs font-bold text-cream/80">
            <span>Niveau {prog.level}</span>
            <span data-testid="progression-progress-pct">{prog.progress_pct}%</span>
            <span>Niveau {prog.level + 1}</span>
          </div>
          <div className="h-3 bg-white/15 rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-mustard"
              initial={{ width: 0 }}
              animate={{ width: `${prog.progress_pct}%` }}
              transition={{ duration: 0.8, ease: "easeOut" }}
              data-testid="progression-progress-bar"
            />
          </div>
        </motion.div>

        {/* ============ BADGES ============ */}
        <div className="bg-white border-2 border-cream-dark rounded-[28px] p-5 md:p-7 mb-6" data-testid="progression-badges">
          <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
            <div>
              <h2 className="font-display text-2xl font-bold text-navy flex items-center gap-2">
                <Award className="w-6 h-6 text-terracotta" /> Vos badges
              </h2>
              <p className="text-sm text-navy/60">
                <span data-testid="progression-badges-count">{earnedCount}</span> / {badges.length} débloqués
                {earnedCount > 0 && (
                  <span className="ml-2 text-terracotta font-medium">
                    · Cliquez sur un badge pour <strong>partager votre exploit</strong> 🎉
                  </span>
                )}
              </p>
            </div>
          </div>

          <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 gap-3">
            {badges.map((b) => {
              const tierStyle = BADGE_TIER_STYLES[b.tier] || BADGE_TIER_STYLES.bronze;
              const Tag = b.earned ? "button" : "div";
              return (
                <motion.div
                  key={b.id}
                  data-testid={`progression-badge-${b.id}`}
                  whileHover={b.earned ? { y: -3 } : {}}
                  className="relative"
                >
                  <Tag
                    onClick={b.earned ? () => setShareBadge(b) : undefined}
                    disabled={!b.earned}
                    className={`w-full rounded-2xl p-3 text-center border-2 transition ${
                      b.earned
                        ? "bg-cream border-cream-dark hover:border-terracotta cursor-pointer"
                        : "bg-cream-dark/40 border-cream-dark grayscale opacity-60 cursor-default"
                    }`}
                    title={b.earned ? "Cliquez pour partager" : b.desc}
                  >
                    {!b.earned && (
                      <Lock className="absolute top-1.5 right-1.5 w-3.5 h-3.5 text-navy/40" />
                    )}
                    {b.earned && (
                      <Share2 className="absolute top-1.5 right-1.5 w-3.5 h-3.5 text-terracotta" data-testid={`badge-earned-${b.id}`} />
                    )}
                    <div className={`inline-flex items-center justify-center w-12 h-12 rounded-full ${b.earned ? tierStyle : "bg-navy/10 text-navy/40"} text-2xl mb-1.5 shadow-sm`}>
                      {b.emoji}
                    </div>
                    <div className="text-xs font-bold text-navy leading-tight line-clamp-2">{b.title}</div>
                  </Tag>
                </motion.div>
              );
            })}
          </div>
        </div>

        {/* ============ MASTERY ============ */}
        <div className="bg-white border-2 border-cream-dark rounded-[28px] p-5 md:p-7 mb-6" data-testid="progression-mastery">
          <div className="flex items-center gap-3 mb-4">
            <TrendingUp className="w-6 h-6 text-terracotta" />
            <h2 className="font-display text-2xl font-bold text-navy">Maîtrise par catégorie</h2>
          </div>
          <p className="text-sm text-navy/60 mb-5">
            Chaque quiz terminé fait progresser votre maîtrise. Devenez <strong>Maître</strong> avec 200+ réponses à 90% ou plus.
          </p>

          <div className="space-y-3">
            {prog.mastery.map((m) => {
              const tier = TIER_STYLES[m.tier.key] || TIER_STYLES.novice;
              const pct = m.tier.ratio_pct || 0;
              return (
                <div
                  key={m.category_id}
                  data-testid={`progression-mastery-${m.category_id}`}
                  className="bg-cream border-2 border-cream-dark rounded-2xl p-3 flex items-center gap-3"
                >
                  {m.mascot_image ? (
                    <img
                      src={`${BACKEND_URL}${m.mascot_image}`}
                      alt=""
                      className="w-12 h-12 rounded-xl object-cover shrink-0"
                    />
                  ) : (
                    <div className="w-12 h-12 rounded-xl bg-navy/10 shrink-0" />
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2 mb-1 flex-wrap">
                      <div className="font-bold text-navy truncate">{m.title}</div>
                      <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${tier.bg} ${tier.text}`}>
                        {m.tier.label}
                      </span>
                    </div>
                    <div className="h-1.5 bg-white rounded-full overflow-hidden mb-1">
                      <div className={`h-full ${tier.bar}`} style={{ width: `${pct}%` }} />
                    </div>
                    <div className="text-xs text-navy/60">
                      {m.correct} / {m.total} bonnes réponses ({pct}%) · {m.quizzes_played} quiz
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="text-center">
          <Link
            to="/app/dashboard"
            data-testid="progression-play-cta"
            className="inline-flex items-center gap-2 bg-terracotta hover:bg-terracotta-dark text-white font-bold px-6 py-4 rounded-full shadow-warm transition"
          >
            <Sparkles className="w-5 h-5" /> Continuer à jouer
          </Link>
        </div>
      </main>

      {/* ============ SHARE BADGE MODAL ============ */}
      <AnimatePresence>
        {shareBadge && (
          <motion.div
            key="share-overlay"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-navy/85 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto"
            data-testid="badge-share-overlay"
            onClick={() => setShareBadge(null)}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.94, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="w-full max-w-lg my-8"
              onClick={(e) => e.stopPropagation()}
              data-testid="badge-share-modal"
            >
              <button
                onClick={() => setShareBadge(null)}
                data-testid="badge-share-close"
                className="mb-3 ml-auto flex items-center justify-center w-10 h-10 rounded-full bg-white/15 hover:bg-white/30 text-white transition"
                aria-label="Fermer"
              >
                <X className="w-5 h-5" />
              </button>
              <BadgeShareCard
                badge={shareBadge}
                playerName={user?.name || "Un joueur"}
                earnedAt={shareBadge.earned_at}
                shareUrl="https://generaquiz.fr"
              />
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      <Footer />
    </div>
  );
}
