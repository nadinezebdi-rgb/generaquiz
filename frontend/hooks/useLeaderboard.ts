'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { supabase } from '../lib/supabase';
import type {
  Badge,
  FamilyRank,
  Period,
  PlayerRank,
  ScoreResult,
  ScoreSubmission,
  ThemeChampion,
} from '../types/leaderboard';

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? '';
const DEFAULT_PERIOD: Period = 'week';
const REALTIME_DEBOUNCE_MS = 300;
const UPDATED_PLAYER_HIGHLIGHT_MS = 1_500;
const FALLBACK_POLLING_INTERVAL_MS = 15_000;

export type RealtimeStatus = 'SUBSCRIBED' | 'CHANNEL_ERROR' | 'TIMED_OUT' | 'CLOSED' | null;

function buildApiUrl(path: string): string {
  const normalizedBase = API_URL.replace(/\/$/, '');
  return `${normalizedBase}${path}`;
}

function toErrorMessage(caughtError: unknown, fallback: string): string {
  return caughtError instanceof Error ? caughtError.message : fallback;
}

async function parseApiError(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: string; message?: string };
    return payload.detail ?? payload.message ?? `Erreur API (${response.status})`;
  } catch {
    return `Erreur API (${response.status})`;
  }
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(buildApiUrl(path), {
    ...init,
    headers: {
      Accept: 'application/json',
      ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
      ...init?.headers,
    },
  });

  if (!response.ok) {
    throw new Error(await parseApiError(response));
  }

  return response.json() as Promise<T>;
}

export interface UseLeaderboardOptions {
  familyId?: string;
}

export interface UseLeaderboardReturn {
  loading: boolean;
  error: string | null;
  familyLeaderboard: PlayerRank[];
  realtimeStatus: RealtimeStatus;
  isLive: boolean;
  lastUpdatedPlayerId: string | null;
  getFamilyLeaderboard: (family_id: string, period?: Period) => Promise<PlayerRank[]>;
  getGlobalLeaderboard: (period?: Period, limit?: number) => Promise<FamilyRank[]>;
  getThemeChampions: () => Promise<ThemeChampion[]>;
  getPlayerBadges: (player_id: string) => Promise<Badge[]>;
  submitScore: (payload: ScoreSubmission) => Promise<ScoreResult>;
  clearError: () => void;
}

export function useLeaderboard(options: UseLeaderboardOptions = {}): UseLeaderboardReturn {
  const { familyId } = options;
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [familyLeaderboard, setFamilyLeaderboard] = useState<PlayerRank[]>([]);
  const [realtimeStatus, setRealtimeStatus] = useState<RealtimeStatus>(null);
  const [lastUpdatedPlayerId, setLastUpdatedPlayerId] = useState<string | null>(null);

  const mountedRef = useRef(true);
  const latestFamilyPeriodRef = useRef<Period>(DEFAULT_PERIOD);
  const debounceTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const highlightTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const fallbackIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const runRequest = useCallback(async <T>(request: () => Promise<T>, fallback: string): Promise<T> => {
    setLoading(true);
    setError(null);

    try {
      return await request();
    } catch (caughtError) {
      const message = toErrorMessage(caughtError, fallback);
      if (mountedRef.current) {
        setError(message);
      }
      throw new Error(message);
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, []);

  const getFamilyLeaderboard = useCallback(
    async (family_id: string, selectedPeriod: Period = DEFAULT_PERIOD) => {
      latestFamilyPeriodRef.current = selectedPeriod;
      const params = new URLSearchParams({ period: selectedPeriod });

      return runRequest(async () => {
        const data = await requestJson<PlayerRank[]>(
          `/api/leaderboard/family/${encodeURIComponent(family_id)}?${params.toString()}`,
        );

        if (mountedRef.current) {
          setFamilyLeaderboard(data);
        }

        return data;
      }, 'Impossible de charger le classement familial.');
    },
    [runRequest],
  );

  const getGlobalLeaderboard = useCallback(
    async (selectedPeriod: Period = DEFAULT_PERIOD, limit = 10) => {
      const params = new URLSearchParams({
        period: selectedPeriod,
        limit: String(limit),
      });

      return runRequest(
        () => requestJson<FamilyRank[]>(`/api/leaderboard/global?${params.toString()}`),
        'Impossible de charger le classement global.',
      );
    },
    [runRequest],
  );

  const getThemeChampions = useCallback(
    async () => runRequest(
      () => requestJson<ThemeChampion[]>('/api/leaderboard/themes'),
      'Impossible de charger les champions de thème.',
    ),
    [runRequest],
  );

  const getPlayerBadges = useCallback(
    async (player_id: string) => runRequest(
      () => requestJson<Badge[]>(`/api/leaderboard/player/${encodeURIComponent(player_id)}/badges`),
      'Impossible de charger les badges du joueur.',
    ),
    [runRequest],
  );

  const submitScore = useCallback(
    async (payload: ScoreSubmission) => runRequest(
      () => requestJson<ScoreResult>('/api/leaderboard/submit', {
        method: 'POST',
        body: JSON.stringify(payload),
      }),
      'Impossible de soumettre le score.',
    ),
    [runRequest],
  );

  // Active le canal Realtime familial et remplace l'ancien polling systématique.
  useEffect(() => {
    if (!familyId) {
      setRealtimeStatus(null);
      setFamilyLeaderboard([]);
      return undefined;
    }

    const channel = supabase
      .channel(`family-scores-${familyId}`)
      .on(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table: 'scores',
          filter: `family_id=eq.${familyId}`,
        },
        (payload) => {
          const newScore = payload.new as { player_id?: string | null };

          if (newScore.player_id) {
            setLastUpdatedPlayerId(newScore.player_id);

            if (highlightTimeoutRef.current) {
              clearTimeout(highlightTimeoutRef.current);
            }

            highlightTimeoutRef.current = setTimeout(() => {
              if (mountedRef.current) {
                setLastUpdatedPlayerId(null);
              }
            }, UPDATED_PLAYER_HIGHLIGHT_MS);
          }

          // Debounce de 300 ms pour regrouper plusieurs insertions proches.
          if (debounceTimeoutRef.current) {
            clearTimeout(debounceTimeoutRef.current);
          }

          debounceTimeoutRef.current = setTimeout(() => {
            getFamilyLeaderboard(familyId, latestFamilyPeriodRef.current).catch(() => {
              // On évite une exception non gérée pendant le rafraîchissement Realtime.
            });
          }, REALTIME_DEBOUNCE_MS);
        },
      )
      .subscribe((status) => {
        if (
          status === 'SUBSCRIBED'
          || status === 'CHANNEL_ERROR'
          || status === 'TIMED_OUT'
          || status === 'CLOSED'
        ) {
          setRealtimeStatus(status);
        }
      });

    return () => {
      supabase.removeChannel(channel);

      if (debounceTimeoutRef.current) {
        clearTimeout(debounceTimeoutRef.current);
        debounceTimeoutRef.current = null;
      }

      if (highlightTimeoutRef.current) {
        clearTimeout(highlightTimeoutRef.current);
        highlightTimeoutRef.current = null;
      }
    };
  }, [familyId, getFamilyLeaderboard]);

  // Fallback : si le canal Realtime échoue, on repasse en polling léger toutes les 15 secondes.
  useEffect(() => {
    if (!familyId || (realtimeStatus !== 'CHANNEL_ERROR' && realtimeStatus !== 'TIMED_OUT')) {
      if (fallbackIntervalRef.current) {
        clearInterval(fallbackIntervalRef.current);
        fallbackIntervalRef.current = null;
      }
      return undefined;
    }

    fallbackIntervalRef.current = setInterval(() => {
      getFamilyLeaderboard(familyId, latestFamilyPeriodRef.current).catch(() => {
        // L'erreur est déjà exposée dans l'état `error` du hook.
      });
    }, FALLBACK_POLLING_INTERVAL_MS);

    return () => {
      if (fallbackIntervalRef.current) {
        clearInterval(fallbackIntervalRef.current);
        fallbackIntervalRef.current = null;
      }
    };
  }, [familyId, getFamilyLeaderboard, realtimeStatus]);

  return {
    loading,
    error,
    familyLeaderboard,
    realtimeStatus,
    isLive: realtimeStatus === 'SUBSCRIBED',
    lastUpdatedPlayerId,
    getFamilyLeaderboard,
    getGlobalLeaderboard,
    getThemeChampions,
    getPlayerBadges,
    submitScore,
    clearError,
  };
}
