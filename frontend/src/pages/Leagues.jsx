import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { api } from "@/lib/api";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import {
  Trophy, ArrowUp, ArrowDown, Clock, Crown, Loader2, Users, Sparkles, Calendar,
} from "lucide-react";

/**
 * Leagues page — weekly cohort leaderboard (30 players max) with:
 *   - Tier badge (bronze | argent | or | diamant) + progress to next/previous
 *   - Countdown timer to Sunday 22:00 Paris (week close)
 *   - Promotion line: top 5 (green border at the bottom of rank 5)
 *   - Relegation line: bottom 3 (red border at the top of rank N-2)
 *   - User row highlighted
 */
const TIER_META = {
  bronze:  { label: "Bronze",  emoji: "🥉", color: "bg-[#B87333]", textColor: "text-[#B87333]" },
  argent:  { label: "Argent",  emoji: "🥈", color: "bg-[#9CA3AF]", textColor: "text-[#6B7280]" },
  or:      { label: "Or",      emoji: "🥇", color: "bg-mustard-dark",   textColor: "text-mustard-dark" },
  diamant: { label: "Diamant", emoji: "💎", color: "bg-[#3FB8AF]", textColor: "text-[#2A8B86]" },
};

function fmtCountdown(seconds) {
  if (!seconds || seconds < 0) return "Terminé";
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (d > 0) return `${d}j ${h}h ${m}min`;
  if (h > 0) return `${h}h ${m}min`;
  return `${m}min`;
}

export default function Leagues() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [countdown, setCountdown] = useState(0);

  useEffect(() => {
    api.get("/gamification/leagues/current")
      .then((r) => {
        setData(r.data);
        setCountdown(r.data.seconds_until_close || 0);
      })
      .catch((e) => setErr(e.response?.status === 401
        ? "Session expirée — reconnectez-vous."
        : "Impossible de charger votre ligue."))
      .finally(() => setLoading(false));
  }, []);

  // 1-second client-side decrement of the countdown for that "live" feel
  useEffect(() => {
    if (!countdown) return;
    const id = setInterval(() => setCountdown((s) => Math.max(0, s - 1)), 1000);
    return () => clearInterval(id);
  }, [countdown]);

  if (loading) {
    return (
      <div className="min-h-screen paper-bg flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-terracotta" />
      </div>
    );
  }

  if (err) {
    return (
      <div className="min-h-screen paper-bg">
        <Navbar variant="app" />
        <div className="max-w-xl mx-auto px-4 py-20 text-center" data-testid="leagues-error">
          <Trophy className="w-12 h-12 mx-auto text-bordeaux mb-3" />
          <h1 className="font-display text-2xl font-bold text-navy mb-2">Oups</h1>
          <p className="text-navy/70 mb-6">{err}</p>
          <button
            onClick={() => window.location.reload()}
            data-testid="leagues-retry"
            className="inline-flex items-center gap-2 bg-terracotta text-white font-bold px-5 py-3 rounded-full"
          >
            Réessayer
          </button>
        </div>
        <Footer />
      </div>
    );
  }

  if (!data) return null;
  const tier = TIER_META[data.tier] || TIER_META.bronze;
  const lb = data.leaderboard || [];
  const promoteCount = data.promote_top || 5;
  const relegateCount = data.relegate_bottom || 3;
  const relegateStart = Math.max(0, lb.length - relegateCount);

  return (
    <div className="min-h-screen paper-bg">
      <Navbar variant="app" />
      <main className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        {/* ============ HERO TIER BADGE ============ */}
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-navy text-cream rounded-[32px] p-6 md:p-8 mb-6 relative overflow-hidden"
          data-testid="leagues-hero"
        >
          <div className="absolute -top-10 -right-10 w-48 h-48 rounded-full bg-mustard/15 blur-3xl pointer-events-none" />
          <div className="flex items-start gap-4 mb-5">
            <div className={`w-16 h-16 rounded-2xl ${tier.color} flex items-center justify-center shrink-0 text-3xl shadow-warm`}>
              {tier.emoji}
            </div>
            <div className="flex-1 min-w-0">
              <div className="inline-flex items-center gap-2 bg-white/10 text-cream/90 font-bold px-2.5 py-0.5 rounded-full text-xs mb-1 uppercase tracking-wider">
                <Trophy className="w-3.5 h-3.5" /> Cette semaine
              </div>
              <h1 className="font-display text-3xl md:text-4xl font-extrabold leading-tight">
                Ligue <span className="text-mustard italic">{tier.label}</span>
              </h1>
              <p className="text-cream/80 text-sm mt-1" data-testid="leagues-week-key">
                Semaine {data.week_key}
              </p>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <Stat label="Mon rang" value={data.my_rank ? `#${data.my_rank}` : "—"} testid="leagues-my-rank" />
            <Stat label="Mes points" value={data.my_xp || 0} testid="leagues-my-xp" />
            <Stat
              label="Termine dans"
              value={fmtCountdown(countdown)}
              icon={Clock}
              testid="leagues-countdown"
            />
          </div>
        </motion.div>

        {/* ============ INSTRUCTIONS / TIER LADDER ============ */}
        <div className="bg-white border-2 border-cream-dark rounded-2xl p-5 mb-6" data-testid="leagues-rules">
          <div className="flex items-center gap-3 mb-3">
            <Sparkles className="w-5 h-5 text-terracotta" />
            <h2 className="font-display text-xl font-bold text-navy">Comment ça marche ?</h2>
          </div>
          <div className="grid sm:grid-cols-2 gap-2 text-sm text-navy/80">
            <div className="flex items-center gap-2">
              <ArrowUp className="w-4 h-4 text-[#3D9970] shrink-0" />
              Les <strong>{promoteCount} premiers</strong> montent en {data.next_tier ? TIER_META[data.next_tier]?.label : "ligue supérieure"} dimanche à 22h
            </div>
            <div className="flex items-center gap-2">
              <ArrowDown className="w-4 h-4 text-bordeaux shrink-0" />
              Les <strong>{relegateCount} derniers</strong> descendent en {data.previous_tier ? TIER_META[data.previous_tier]?.label : "ligue inférieure"}
            </div>
          </div>
        </div>

        {/* ============ LEADERBOARD ============ */}
        <div className="bg-white border-2 border-cream-dark rounded-[28px] p-4 md:p-6" data-testid="leagues-leaderboard">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-display text-xl font-bold text-navy flex items-center gap-2">
              <Users className="w-5 h-5 text-terracotta" /> Classement de la cohorte
            </h2>
            <span className="text-xs text-navy/60 font-bold">{data.cohort_size} / {data.max_cohort_size} joueurs</span>
          </div>

          {lb.length === 0 ? (
            <EmptyCohort />
          ) : (
            <ol className="space-y-1">
              {lb.map((row, idx) => {
                const isPromoZone = idx < promoteCount;
                const isRelegZone = idx >= relegateStart && lb.length > promoteCount + 1;
                const showPromoLine = idx === promoteCount - 1 && lb.length > promoteCount;
                const showRelegLine = idx === relegateStart && lb.length > promoteCount + 1;
                return (
                  <div key={row.user_id}>
                    {showRelegLine && (
                      <div className="my-2 border-t-2 border-dashed border-bordeaux flex items-center gap-2 -mt-1 pt-1" data-testid="leagues-relegation-line">
                        <ArrowDown className="w-3.5 h-3.5 text-bordeaux" />
                        <span className="text-xs font-bold uppercase tracking-wider text-bordeaux">Zone de relégation</span>
                      </div>
                    )}
                    <li
                      data-testid={`leagues-row-${idx}`}
                      className={`flex items-center gap-3 px-3 py-3 rounded-2xl transition ${
                        row.is_me
                          ? "bg-mustard/30 border-2 border-mustard-dark"
                          : isPromoZone
                          ? "bg-[#3D9970]/8 hover:bg-[#3D9970]/15"
                          : isRelegZone
                          ? "bg-bordeaux/8 hover:bg-bordeaux/15"
                          : "bg-cream hover:bg-cream-dark"
                      }`}
                    >
                      <RankBadge rank={row.rank} isPromo={isPromoZone} isRelegate={isRelegZone} isMe={row.is_me} />
                      <div className="flex-1 min-w-0">
                        <div className={`font-bold truncate ${row.is_me ? "text-navy" : "text-navy/90"}`} data-testid={row.is_me ? "leagues-row-me" : undefined}>
                          {row.name} {row.is_me && <span className="text-terracotta">(moi)</span>}
                        </div>
                      </div>
                      <div className="text-right shrink-0">
                        <div className="font-display text-lg font-extrabold text-navy">{row.xp.toLocaleString("fr-FR")}</div>
                        <div className="text-xs text-navy/60">points</div>
                      </div>
                    </li>
                    {showPromoLine && (
                      <div className="my-2 border-t-2 border-dashed border-[#3D9970] flex items-center gap-2 pt-1 -mb-1" data-testid="leagues-promotion-line">
                        <ArrowUp className="w-3.5 h-3.5 text-[#3D9970]" />
                        <span className="text-xs font-bold uppercase tracking-wider text-[#3D9970]">Zone de promotion</span>
                      </div>
                    )}
                  </div>
                );
              })}
            </ol>
          )}
        </div>

        <div className="mt-6 text-center">
          <Link
            to="/app/daily"
            data-testid="leagues-play-cta"
            className="inline-flex items-center gap-2 bg-terracotta hover:bg-terracotta-dark text-white font-bold px-6 py-4 rounded-full shadow-warm transition"
          >
            <Crown className="w-5 h-5" /> Jouer le Quiz du Jour pour grimper
          </Link>
        </div>
      </main>
      <Footer />
    </div>
  );
}

function Stat({ label, value, icon: Icon, testid }) {
  return (
    <div className="bg-white/10 backdrop-blur-sm rounded-2xl p-3 text-center" data-testid={testid}>
      <div className="text-xs font-bold uppercase tracking-wider text-cream/70 mb-1">{label}</div>
      <div className="font-display text-2xl font-extrabold text-mustard inline-flex items-center justify-center gap-1.5">
        {Icon && <Icon className="w-5 h-5" />}
        {value}
      </div>
    </div>
  );
}

function RankBadge({ rank, isPromo, isRelegate, isMe }) {
  const base = "w-9 h-9 rounded-full flex items-center justify-center font-display font-extrabold shrink-0 text-sm";
  if (isMe) return <div className={`${base} bg-terracotta text-white`}>{rank}</div>;
  if (rank === 1) return <div className={`${base} bg-mustard-dark text-white text-base`}>🥇</div>;
  if (rank === 2) return <div className={`${base} bg-[#9CA3AF] text-white text-base`}>🥈</div>;
  if (rank === 3) return <div className={`${base} bg-[#B87333] text-white text-base`}>🥉</div>;
  if (isPromo) return <div className={`${base} bg-[#3D9970]/20 text-[#3D9970]`}>{rank}</div>;
  if (isRelegate) return <div className={`${base} bg-bordeaux/20 text-bordeaux`}>{rank}</div>;
  return <div className={`${base} bg-white border-2 border-cream-dark text-navy/70`}>{rank}</div>;
}

function EmptyCohort() {
  return (
    <div className="text-center py-10" data-testid="leagues-empty">
      <Calendar className="w-12 h-12 mx-auto text-navy/30 mb-3" />
      <h3 className="font-display text-xl font-bold text-navy mb-1">Vous êtes seul(e) dans votre cohorte</h3>
      <p className="text-navy/60">Jouez quelques quiz et invitez des amis pour la remplir !</p>
    </div>
  );
}
