import { toast } from "sonner";

// Static catalog — kept in sync with backend/badges.py BADGES.
// Client-side only for display; server is the source of truth for awarding.
const BADGE_META = {
  first_quiz:       { title: "Premier pas",         emoji: "🎯" },
  first_coop:       { title: "Duo formé",           emoji: "🤝" },
  streak_3:         { title: "Petite flamme",       emoji: "🔥" },
  streak_7:         { title: "Feu de camp",         emoji: "🔥" },
  streak_30:        { title: "Brasier",             emoji: "🔥" },
  streak_100:       { title: "Incandescent",        emoji: "🌟" },
  daily_perfect:    { title: "Sans-faute",          emoji: "✅" },
  daily_speed:      { title: "Éclair",              emoji: "⚡" },
  early_bird:       { title: "Lève-tôt",            emoji: "🐦" },
  coop_5:           { title: "Complice",            emoji: "👥" },
  coop_saviour:     { title: "Sauveur de l'Ancre",  emoji: "🛟" },
  league_promoted:  { title: "Ascension",           emoji: "🚀" },
  league_diamond:   { title: "Ligue Diamant",       emoji: "💎" },
  referrer_1:       { title: "Bon voisin",          emoji: "💌" },
  referrer_5:       { title: "Ambassadeur",         emoji: "📢" },
};

/**
 * Show a celebratory toast for each newly awarded badge.
 * Call this from any endpoint response that includes `awarded_badges: string[]`.
 */
export function showBadgeToasts(badgeIds) {
  if (!Array.isArray(badgeIds) || badgeIds.length === 0) return;
  badgeIds.forEach((id, i) => {
    const meta = BADGE_META[id] || { title: id, emoji: "🏅" };
    // Small stagger so consecutive toasts don't overlap
    setTimeout(() => {
      toast.success(
        `${meta.emoji} Badge débloqué : ${meta.title}`,
        {
          description: "À voir dans votre page Progression",
          duration: 5000,
        },
      );
    }, i * 400);
  });
}
