-- ============================================================
-- Quiz d'Antan - Migration 001
-- Création des tables principales pour familles, joueurs,
-- sessions de quiz, scores et badges.
-- Compatible PostgreSQL / Supabase.
-- ============================================================

-- Extension standard Supabase pour gen_random_uuid().
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ------------------------------------------------------------
-- Fonction utilitaire : met à jour automatiquement updated_at.
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ------------------------------------------------------------
-- Table families : groupes familiaux participant au quiz.
-- invite_code est un code court unique permettant d'inviter
-- de nouveaux membres dans une famille.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.families (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  invite_code TEXT NOT NULL UNIQUE,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- ------------------------------------------------------------
-- Trigger updated_at sur families.
-- Le DROP permet de rejouer la migration sans doublonner le trigger.
-- ------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_families_set_updated_at ON public.families;
CREATE TRIGGER trg_families_set_updated_at
BEFORE UPDATE ON public.families
FOR EACH ROW
EXECUTE FUNCTION public.set_updated_at();

-- ------------------------------------------------------------
-- Table players : profils de joueurs, éventuellement liés à
-- Supabase Auth via auth_user_id. Les invités peuvent avoir NULL.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.players (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  family_id UUID REFERENCES public.families(id) ON DELETE CASCADE,
  pseudo TEXT NOT NULL,
  avatar TEXT DEFAULT 'default',
  auth_user_id UUID UNIQUE,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- ------------------------------------------------------------
-- Table quiz_sessions : trace une session de jeu.
-- session_token est généré/signé côté serveur pour éviter les
-- doubles soumissions de score.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.quiz_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  player_id UUID REFERENCES public.players(id) ON DELETE CASCADE,
  family_id UUID REFERENCES public.families(id) ON DELETE CASCADE,
  theme TEXT NOT NULL,
  nb_questions INTEGER NOT NULL DEFAULT 5,
  session_token TEXT NOT NULL UNIQUE,
  started_at TIMESTAMPTZ DEFAULT now(),
  completed_at TIMESTAMPTZ
);

-- ------------------------------------------------------------
-- Table scores : résultat final d'une session terminée.
-- Une seule ligne de score est autorisée par session.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.scores (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES public.quiz_sessions(id) ON DELETE CASCADE UNIQUE,
  player_id UUID REFERENCES public.players(id) ON DELETE CASCADE,
  family_id UUID REFERENCES public.families(id) ON DELETE CASCADE,
  raw_score INTEGER NOT NULL DEFAULT 0,
  total_questions INTEGER NOT NULL DEFAULT 5,
  weighted_score NUMERIC(10,2) NOT NULL DEFAULT 0,
  difficulty_avg NUMERIC(4,2) DEFAULT 1.0,
  time_bonus INTEGER DEFAULT 0,
  theme TEXT NOT NULL,
  era TEXT,
  category TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  CONSTRAINT scores_raw_score_lte_total_questions CHECK (raw_score <= total_questions),
  CONSTRAINT scores_raw_score_non_negative CHECK (raw_score >= 0),
  CONSTRAINT scores_total_questions_positive CHECK (total_questions > 0)
);

-- ------------------------------------------------------------
-- Table badges : récompenses attribuées aux joueurs.
-- L'unicité par joueur/type/thème est gérée par un index unique
-- fonctionnel, car PostgreSQL ne permet pas d'expression JSONB
-- directement dans une contrainte UNIQUE de CREATE TABLE.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.badges (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  player_id UUID REFERENCES public.players(id) ON DELETE CASCADE,
  family_id UUID REFERENCES public.families(id) ON DELETE CASCADE,
  type TEXT NOT NULL,
  context JSONB DEFAULT '{}',
  awarded_at TIMESTAMPTZ DEFAULT now()
);

-- ------------------------------------------------------------
-- Index unique anti-doublon pour les badges par joueur/type/thème.
-- COALESCE évite les doublons lorsque context->>'theme' est absent.
-- ------------------------------------------------------------
CREATE UNIQUE INDEX IF NOT EXISTS idx_badges_unique_player_type_theme
ON public.badges (player_id, type, COALESCE(context->>'theme', '__global__'));

-- ------------------------------------------------------------
-- Index utiles pour les classements et accès fréquents.
-- ------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_families_invite_code ON public.families(invite_code);
CREATE INDEX IF NOT EXISTS idx_families_created_at ON public.families(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_players_family_id ON public.players(family_id);
CREATE INDEX IF NOT EXISTS idx_players_auth_user_id ON public.players(auth_user_id);
CREATE INDEX IF NOT EXISTS idx_players_created_at ON public.players(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_quiz_sessions_player_id ON public.quiz_sessions(player_id);
CREATE INDEX IF NOT EXISTS idx_quiz_sessions_family_id ON public.quiz_sessions(family_id);
CREATE INDEX IF NOT EXISTS idx_quiz_sessions_started_at ON public.quiz_sessions(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_quiz_sessions_completed_at ON public.quiz_sessions(completed_at DESC);
CREATE INDEX IF NOT EXISTS idx_quiz_sessions_token ON public.quiz_sessions(session_token);

CREATE INDEX IF NOT EXISTS idx_scores_session_id ON public.scores(session_id);
CREATE INDEX IF NOT EXISTS idx_scores_player_id ON public.scores(player_id);
CREATE INDEX IF NOT EXISTS idx_scores_family_id ON public.scores(family_id);
CREATE INDEX IF NOT EXISTS idx_scores_created_at ON public.scores(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_scores_weighted_score ON public.scores(weighted_score DESC);
CREATE INDEX IF NOT EXISTS idx_scores_family_weighted_created ON public.scores(family_id, weighted_score DESC, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_scores_player_created ON public.scores(player_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_scores_theme_weighted ON public.scores(theme, weighted_score DESC, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_badges_player_id ON public.badges(player_id);
CREATE INDEX IF NOT EXISTS idx_badges_family_id ON public.badges(family_id);
CREATE INDEX IF NOT EXISTS idx_badges_awarded_at ON public.badges(awarded_at DESC);
CREATE INDEX IF NOT EXISTS idx_badges_type ON public.badges(type);
