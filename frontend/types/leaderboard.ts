/**
 * Types partagés pour le leaderboard persistant de Quiz d'Antan.
 * Les champs suivent les réponses JSON exposées par le backend FastAPI.
 */

export type Period = 'week' | 'month' | 'alltime';

export type BadgeType =
  | 'first_game'
  | 'perfect_score'
  | 'streak_3'
  | 'theme_champion'
  | 'best_elder'
  | string;

export type Difficulty = 'facile' | 'moyen' | 'difficile';

export interface FamilyRank {
  family_id: string;
  family_name: string | null;
  total_score: number;
  nb_sessions: number;
  nb_players?: number;
  nb_active_players?: number;
  best_theme?: string | null;
  last_played_at?: string | null;
  rank: number;
}

export interface PlayerRank {
  player_id: string;
  pseudo: string | null;
  avatar?: string | null;
  family_id: string;
  total_score: number;
  nb_sessions: number;
  best_score?: number;
  last_played_at?: string | null;
  rank_in_family: number;
  badges?: Badge[];
}

export interface ThemeChampion {
  theme: string;
  player_id: string;
  pseudo: string | null;
  family_id: string;
  best_score: number;
  achieved_at: string | null;
}

export interface Badge {
  id: string;
  player_id: string;
  family_id?: string | null;
  type: BadgeType;
  awarded_at?: string | null;
  context: Record<string, unknown>;
}

export interface ScoreAnswerSubmission {
  question_id: string;
  chosen: string;
  correct: boolean;
  difficulty: Difficulty;
  time_taken_seconds?: number | null;
  time_bonus?: number | null;
}

export interface ScoreSubmission {
  session_token: string;
  player_id: string;
  family_id: string;
  theme: string;
  answers: ScoreAnswerSubmission[];
}

export interface ScoreResult {
  score: number;
  rank: number | null;
  badges_earned: BadgeType[];
}
