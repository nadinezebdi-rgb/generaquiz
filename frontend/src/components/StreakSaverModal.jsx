import { useState } from "react";
import { Link } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Flame, Coins, X, Tv, AlertTriangle, Sparkles } from "lucide-react";
import { api, formatError } from "@/lib/api";

const STREAK_SAVER_COST = 10;

/**
 * StreakSaverModal — appears when the user broke their streak yesterday.
 *
 * Trigger condition (computed by parent):
 *   streak_current >= 2 AND streak_last_date === today_minus_2
 *
 * Two actions:
 *   - Spend 10 credits → POST /api/gamification/streak-saver
 *   - Earn credits first via ads → /app/earn-credits (deeplink, modal closes)
 *
 * Idempotency: parent dismisses the modal on success (refresh()).
 */
export default function StreakSaverModal({ user, onClose, onSaved }) {
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");

  if (!user) return null;
  const credits = user.credits || 0;
  const enoughCredits = credits >= STREAK_SAVER_COST;
  const streak = user.streak_current || 0;

  const save = async () => {
    if (!enoughCredits || saving) return;
    setErr("");
    setSaving(true);
    try {
      const { data } = await api.post("/gamification/streak-saver");
      onSaved?.(data);
    } catch (e) {
      setErr(formatError(e.response?.data?.detail) || "Impossible de sauver la série");
    } finally {
      setSaving(false);
    }
  };

  return (
    <AnimatePresence>
      <motion.div
        key="overlay"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 bg-navy/80 backdrop-blur-sm flex items-center justify-center p-4"
        data-testid="streak-saver-overlay"
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.9, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95 }}
          className="bg-white border-2 border-cream-dark rounded-[32px] w-full max-w-md overflow-hidden"
          data-testid="streak-saver-modal"
        >
          {/* Header — animated flame */}
          <div className="bg-bordeaux text-cream p-6 text-center relative">
            <button
              onClick={onClose}
              data-testid="streak-saver-close"
              className="absolute top-3 right-3 w-9 h-9 rounded-full bg-white/15 hover:bg-white/25 flex items-center justify-center transition"
              aria-label="Fermer"
            >
              <X className="w-4 h-4" />
            </button>
            <motion.div
              animate={{ rotate: [-5, 5, -5], scale: [1, 1.08, 1] }}
              transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
              className="inline-block mb-2"
            >
              <Flame className="w-16 h-16 text-mustard mx-auto" fill="currentColor" />
            </motion.div>
            <h2 className="font-display text-3xl font-extrabold mb-1">Votre flamme s&apos;éteint !</h2>
            <p className="text-cream/85 text-sm">
              Vous aviez une série de <strong className="text-mustard">{streak} jours</strong>. Sauvez-la avant minuit.
            </p>
          </div>

          {/* Body */}
          <div className="p-6">
            <div className="bg-mustard/20 border-2 border-mustard-dark rounded-2xl p-4 mb-5 flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-bordeaux shrink-0 mt-0.5" />
              <p className="text-sm text-navy/85 leading-relaxed">
                Vous n&apos;avez pas joué hier. En sauvant maintenant, votre série continuera comme si vous aviez joué.
              </p>
            </div>

            {err && (
              <div className="bg-bordeaux/10 border-2 border-bordeaux/40 rounded-xl p-3 mb-4 text-bordeaux text-sm" data-testid="streak-saver-error">
                {err}
              </div>
            )}

            {/* Primary action — credits */}
            <button
              onClick={save}
              disabled={!enoughCredits || saving}
              data-testid="streak-saver-pay"
              className={`w-full inline-flex items-center justify-center gap-2 font-bold text-lg px-6 py-4 rounded-full transition mb-3 ${
                enoughCredits
                  ? "bg-terracotta hover:bg-terracotta-dark text-white shadow-warm"
                  : "bg-cream-dark text-navy/40 cursor-not-allowed"
              }`}
            >
              <Coins className="w-5 h-5" />
              {saving ? "Sauvetage..." : `Sauver pour ${STREAK_SAVER_COST} crédits`}
            </button>

            <div className="text-center text-xs font-bold text-navy/50 mb-3">
              Solde actuel : <span data-testid="streak-saver-credits">{credits}</span> crédits
            </div>

            {!enoughCredits && (
              <Link
                to="/app/earn-credits"
                data-testid="streak-saver-earn"
                onClick={onClose}
                className="w-full inline-flex items-center justify-center gap-2 bg-navy hover:bg-navy-dark text-white font-bold px-6 py-3 rounded-full transition"
              >
                <Tv className="w-4 h-4" />
                Gagner des crédits (regarder une pub)
              </Link>
            )}

            <button
              onClick={onClose}
              data-testid="streak-saver-dismiss"
              className="w-full text-sm text-navy/60 hover:text-bordeaux font-bold mt-4 inline-flex items-center justify-center gap-1"
            >
              <Sparkles className="w-3.5 h-3.5" /> Tant pis, je laisse filer
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
