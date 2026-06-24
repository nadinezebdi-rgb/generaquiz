'use client';

import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import { useLeaderboard } from '../hooks/useLeaderboard';
import type { FamilyRank, Period, PlayerRank, ThemeChampion } from '../types/leaderboard';

interface LeaderboardPanelProps {
  familyId?: string;
  playerId?: string;
  showGlobal?: boolean;
}

type TabKey = 'family' | 'global' | 'themes';

const PERIOD_LABELS: Record<Period, string> = {
  week: 'Semaine',
  month: 'Mois',
  alltime: 'Tout le temps',
};

const PERIODS: Period[] = ['week', 'month', 'alltime'];

function formatScore(score?: number | null): string {
  return new Intl.NumberFormat('fr-FR', {
    maximumFractionDigits: 0,
  }).format(score ?? 0);
}

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

function getMedal(rank: number): string {
  if (rank === 1) return '🥇';
  if (rank === 2) return '🥈';
  if (rank === 3) return '🥉';
  return String(rank);
}

function SkeletonRows() {
  return (
    <div className="space-y-3">
      {[0, 1, 2].map((index) => (
        <div key={index} className="h-14 animate-pulse rounded-xl bg-slate-200" />
      ))}
    </div>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-6 text-center text-sm text-slate-500">
      {message}
    </div>
  );
}

function TabButton({ active, children, onClick }: { active: boolean; children: ReactNode; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full px-4 py-2 text-sm font-medium transition ${
        active
          ? 'bg-amber-500 text-white shadow-sm'
          : 'bg-white text-slate-600 ring-1 ring-slate-200 hover:bg-amber-50 hover:text-amber-700'
      }`}
    >
      {children}
    </button>
  );
}

function FamilyTable({
  players,
  playerId,
  lastUpdatedPlayerId,
}: {
  players: PlayerRank[];
  playerId?: string;
  lastUpdatedPlayerId: string | null;
}) {
  if (players.length === 0) {
    return <EmptyState message="Aucun score familial pour cette période." />;
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200 text-sm">
          <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-3">Rang</th>
              <th className="px-4 py-3">Pseudo</th>
              <th className="px-4 py-3 text-right">Score</th>
              <th className="px-4 py-3 text-right">Sessions</th>
              <th className="px-4 py-3">Badges</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {players.map((player) => {
              const isCurrentPlayer = player.player_id === playerId;
              const isRecentlyUpdated = player.player_id === lastUpdatedPlayerId;

              return (
                <tr
                  key={player.player_id}
                  className={`transition-colors duration-300 ${
                    isRecentlyUpdated
                      ? 'animate-pulse bg-emerald-50'
                      : isCurrentPlayer
                        ? 'bg-amber-50'
                        : 'bg-white'
                  }`}
                >
                  <td className="whitespace-nowrap px-4 py-4 font-semibold text-slate-700">
                    #{player.rank_in_family}
                  </td>
                  <td className="px-4 py-4">
                    <div className="flex items-center gap-3">
                      <span className="flex h-9 w-9 items-center justify-center rounded-full bg-slate-100 text-lg">
                        {player.avatar && player.avatar !== 'default' ? player.avatar : '👤'}
                      </span>
                      <div>
                        <div className="flex items-center gap-2 font-medium text-slate-900">
                          {player.pseudo ?? 'Joueur anonyme'}
                          {isCurrentPlayer ? (
                            <span className="rounded-full bg-amber-200 px-2 py-0.5 text-xs font-semibold text-amber-900">
                              Vous
                            </span>
                          ) : null}
                          {isRecentlyUpdated ? (
                            <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-semibold text-emerald-700">
                              Nouveau score
                            </span>
                          ) : null}
                        </div>
                        {player.last_played_at ? (
                          <p className="text-xs text-slate-500">Dernière partie : {formatDate(player.last_played_at)}</p>
                        ) : null}
                      </div>
                    </div>
                  </td>
                  <td className="whitespace-nowrap px-4 py-4 text-right font-semibold text-slate-900">
                    {formatScore(player.total_score)} pts
                  </td>
                  <td className="whitespace-nowrap px-4 py-4 text-right text-slate-600">{player.nb_sessions}</td>
                  <td className="px-4 py-4">
                    {player.badges && player.badges.length > 0 ? (
                      <div className="flex flex-wrap gap-1">
                        {player.badges.slice(0, 3).map((badge) => (
                          <span key={badge.id} className="rounded-full bg-slate-100 px-2 py-1 text-xs text-slate-600">
                            {badge.type.replaceAll('_', ' ')}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span className="text-xs text-slate-400">Aucun</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function GlobalTable({ families }: { families: FamilyRank[] }) {
  if (families.length === 0) {
    return <EmptyState message="Aucune famille classée pour le moment." />;
  }

  return (
    <div className="space-y-3">
      {families.slice(0, 10).map((family, index) => {
        const rank = family.rank ?? index + 1;
        const activePlayers = family.nb_active_players ?? family.nb_players ?? 0;

        return (
          <article key={family.family_id} className="flex items-center justify-between rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex items-center gap-4">
              <span className="flex h-11 w-11 items-center justify-center rounded-full bg-amber-100 text-lg font-bold text-amber-900">
                {getMedal(rank)}
              </span>
              <div>
                <h3 className="font-semibold text-slate-900">{family.family_name ?? 'Famille sans nom'}</h3>
                <p className="text-sm text-slate-500">{activePlayers} joueur{activePlayers > 1 ? 's' : ''} actif{activePlayers > 1 ? 's' : ''}</p>
              </div>
            </div>
            <div className="text-right">
              <p className="font-bold text-slate-900">{formatScore(family.total_score)} pts</p>
              {family.best_theme ? <p className="text-xs text-slate-500">Thème fort : {family.best_theme}</p> : null}
            </div>
          </article>
        );
      })}
    </div>
  );
}

function ThemeGrid({ champions }: { champions: ThemeChampion[] }) {
  if (champions.length === 0) {
    return <EmptyState message="Aucun champion de thème disponible." />;
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {champions.map((champion) => (
        <article key={`${champion.theme}-${champion.player_id}`} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="mb-4 flex items-center justify-between gap-3">
            <h3 className="font-semibold text-slate-900">{champion.theme}</h3>
            <span className="rounded-full bg-amber-100 px-3 py-1 text-sm" aria-hidden="true">🏆</span>
          </div>
          <p className="text-sm text-slate-500">Champion</p>
          <p className="mt-1 text-lg font-bold text-slate-900">{champion.pseudo ?? 'Joueur anonyme'}</p>
          <div className="mt-4 flex items-end justify-between gap-3 text-sm">
            <span className="font-semibold text-amber-700">{formatScore(champion.best_score)} pts</span>
            <span className="text-xs text-slate-500">{formatDate(champion.achieved_at)}</span>
          </div>
        </article>
      ))}
    </div>
  );
}

export function LeaderboardPanel({ familyId, playerId, showGlobal = true }: LeaderboardPanelProps) {
  const initialTab = useMemo<TabKey>(() => {
    if (familyId) return 'family';
    if (showGlobal) return 'global';
    return 'themes';
  }, [familyId, showGlobal]);

  const [activeTab, setActiveTab] = useState<TabKey>(initialTab);
  const [period, setPeriod] = useState<Period>('week');
  const [familyRows, setFamilyRows] = useState<PlayerRank[]>([]);
  const [globalRows, setGlobalRows] = useState<FamilyRank[]>([]);
  const [themeChampions, setThemeChampions] = useState<ThemeChampion[]>([]);
  const {
    loading,
    error,
    familyLeaderboard,
    isLive,
    lastUpdatedPlayerId,
    getFamilyLeaderboard,
    getGlobalLeaderboard,
    getThemeChampions,
  } = useLeaderboard({ familyId });

  const loadFamilyRows = useCallback(() => {
    if (!familyId) {
      return;
    }

    getFamilyLeaderboard(familyId, period)
      .then(setFamilyRows)
      .catch(() => setFamilyRows([]));
  }, [familyId, getFamilyLeaderboard, period]);

  const loadGlobalRows = useCallback(() => {
    getGlobalLeaderboard(period, 10)
      .then(setGlobalRows)
      .catch(() => setGlobalRows([]));
  }, [getGlobalLeaderboard, period]);

  const loadThemeChampions = useCallback(() => {
    getThemeChampions()
      .then(setThemeChampions)
      .catch(() => setThemeChampions([]));
  }, [getThemeChampions]);

  useEffect(() => {
    if (activeTab === 'family') {
      loadFamilyRows();
    }

    if (activeTab === 'global') {
      loadGlobalRows();
    }

    if (activeTab === 'themes') {
      loadThemeChampions();
    }
  }, [activeTab, loadFamilyRows, loadGlobalRows, loadThemeChampions]);

  // Le hook met à jour `familyLeaderboard` après un événement Realtime ou un fallback polling.
  useEffect(() => {
    setFamilyRows(familyLeaderboard);
  }, [familyLeaderboard]);

  useEffect(() => {
    setActiveTab(initialTab);
  }, [initialTab]);

  return (
    <section className="rounded-3xl bg-slate-50 p-4 shadow-sm ring-1 ring-slate-200 sm:p-6">
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-medium uppercase tracking-wide text-amber-700">Quiz d&apos;Antan</p>
          <h2 className="mt-1 text-2xl font-bold text-slate-950">Classements familiaux</h2>
          <p className="mt-2 text-sm text-slate-600">Suivez les scores, les champions et les badges pour motiver toute la famille.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {familyId ? (
            <TabButton active={activeTab === 'family'} onClick={() => setActiveTab('family')}>
              <span className="inline-flex items-center gap-2">
                <span>Ma famille</span>
                <span className="inline-flex items-center">
                  <span className={`mr-1 inline-block h-2 w-2 rounded-full ${isLive ? 'bg-green-400' : 'bg-slate-300'}`} />
                  <span className="text-xs text-slate-400">{isLive ? 'En direct' : 'Hors ligne'}</span>
                </span>
              </span>
            </TabButton>
          ) : null}
          {showGlobal ? (
            <TabButton active={activeTab === 'global'} onClick={() => setActiveTab('global')}>
              Classement global
            </TabButton>
          ) : null}
          <TabButton active={activeTab === 'themes'} onClick={() => setActiveTab('themes')}>
            Champions de thème
          </TabButton>
        </div>
      </div>

      {(activeTab === 'family' || activeTab === 'global') ? (
        <div className="mb-5 flex flex-wrap gap-2">
          {PERIODS.map((nextPeriod) => (
            <button
              key={nextPeriod}
              type="button"
              onClick={() => setPeriod(nextPeriod)}
              className={`rounded-full px-3 py-1.5 text-sm font-medium transition ${
                period === nextPeriod
                  ? 'bg-slate-900 text-white'
                  : 'bg-white text-slate-600 ring-1 ring-slate-200 hover:bg-slate-100'
              }`}
            >
              {PERIOD_LABELS[nextPeriod]}
            </button>
          ))}
        </div>
      ) : null}

      {error ? (
        <div className="mb-5 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      ) : null}

      {loading ? <SkeletonRows /> : null}

      {!loading && activeTab === 'family' && (
        familyId ? (
          <FamilyTable players={familyRows} playerId={playerId} lastUpdatedPlayerId={lastUpdatedPlayerId} />
        ) : (
          <EmptyState message="Aucune famille sélectionnée." />
        )
      )}

      {!loading && activeTab === 'global' && <GlobalTable families={globalRows} />}

      {!loading && activeTab === 'themes' && <ThemeGrid champions={themeChampions} />}
    </section>
  );
}

export default LeaderboardPanel;
