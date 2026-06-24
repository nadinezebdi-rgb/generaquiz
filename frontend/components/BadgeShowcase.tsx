'use client';

import { useEffect, useMemo, useState } from 'react';
import { useLeaderboard } from '../hooks/useLeaderboard';
import type { Badge, BadgeType } from '../types/leaderboard';

interface BadgeShowcaseProps {
  badges?: Badge[];
  playerId: string;
}

const BADGE_LABELS: Record<string, string> = {
  first_game: 'Première partie',
  perfect_score: 'Score parfait',
  streak_3: "3 jours d'affilée",
  theme_champion: 'Champion de thème',
  best_elder: 'Meilleur grand-parent',
};

const BADGE_ICONS: Record<string, string> = {
  first_game: '🎮',
  perfect_score: '💯',
  streak_3: '🔥',
  theme_champion: '🏆',
  best_elder: '👵',
};

function formatDate(value?: string | null): string {
  if (!value) {
    return 'Date inconnue';
  }

  return new Intl.DateTimeFormat('fr-FR', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  }).format(new Date(value));
}

function getBadgeLabel(type: BadgeType): string {
  return BADGE_LABELS[type] ?? String(type).replaceAll('_', ' ');
}

function getBadgeIcon(type: BadgeType): string {
  return BADGE_ICONS[type] ?? '⭐';
}

export function BadgeShowcase({ badges, playerId }: BadgeShowcaseProps) {
  const { getPlayerBadges, loading, error } = useLeaderboard({ autoPollFamily: false });
  const [loadedBadges, setLoadedBadges] = useState<Badge[]>(badges ?? []);

  const shouldFetchBadges = useMemo(() => badges === undefined && Boolean(playerId), [badges, playerId]);

  useEffect(() => {
    if (badges !== undefined) {
      setLoadedBadges(badges);
      return;
    }

    if (!shouldFetchBadges) {
      return;
    }

    getPlayerBadges(playerId)
      .then(setLoadedBadges)
      .catch(() => {
        setLoadedBadges([]);
      });
  }, [badges, getPlayerBadges, playerId, shouldFetchBadges]);

  if (loading && shouldFetchBadges) {
    return (
      <div className="grid gap-2 sm:grid-cols-2">
        {[0, 1, 2].map((index) => (
          <div key={index} className="h-16 rounded-xl bg-slate-200 animate-pulse" />
        ))}
      </div>
    );
  }

  if (error && shouldFetchBadges) {
    return <p className="text-sm text-red-600">{error}</p>;
  }

  if (loadedBadges.length === 0) {
    return <p className="text-sm text-slate-500">Aucun badge gagné pour le moment.</p>;
  }

  return (
    <div className="grid gap-2 sm:grid-cols-2">
      {loadedBadges.map((badge) => (
        <article
          key={badge.id}
          className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white p-3 shadow-sm"
        >
          <span className="flex h-10 w-10 items-center justify-center rounded-full bg-amber-100 text-xl">
            {getBadgeIcon(badge.type)}
          </span>
          <div className="min-w-0">
            <h3 className="truncate text-sm font-semibold text-slate-900">{getBadgeLabel(badge.type)}</h3>
            <p className="text-xs text-slate-500">Obtenu le {formatDate(badge.awarded_at)}</p>
          </div>
        </article>
      ))}
    </div>
  );
}

export default BadgeShowcase;
