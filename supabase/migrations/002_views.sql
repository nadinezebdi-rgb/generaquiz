-- ============================================================
-- Quiz d'Antan - Migration 002
-- Vues de classement pour familles, joueurs et champions par thème.
-- Compatible PostgreSQL / Supabase.
-- ============================================================

-- ------------------------------------------------------------
-- Vue v_family_leaderboard : classement global des familles
-- sur les 30 derniers jours. Le meilleur thème correspond au
-- thème ayant le score cumulé le plus élevé pour chaque famille.
-- ------------------------------------------------------------
CREATE OR REPLACE VIEW public.v_family_leaderboard AS
WITH recent_scores AS (
  SELECT
    s.family_id,
    s.theme,
    s.weighted_score,
    s.created_at
  FROM public.scores s
  WHERE s.created_at >= now() - INTERVAL '30 days'
),
family_stats AS (
  SELECT
    f.id AS family_id,
    f.name AS family_name,
    COALESCE(SUM(rs.weighted_score), 0)::NUMERIC(12,2) AS total_score,
    COUNT(rs.*)::INTEGER AS nb_sessions,
    COUNT(DISTINCT p.id)::INTEGER AS nb_players,
    MAX(rs.created_at) AS last_played_at
  FROM public.families f
  LEFT JOIN public.players p ON p.family_id = f.id
  LEFT JOIN recent_scores rs ON rs.family_id = f.id
  GROUP BY f.id, f.name
),
best_theme_by_family AS (
  SELECT DISTINCT ON (family_id)
    family_id,
    theme AS best_theme
  FROM (
    SELECT
      family_id,
      theme,
      SUM(weighted_score) AS theme_score
    FROM recent_scores
    GROUP BY family_id, theme
  ) theme_scores
  ORDER BY family_id, theme_score DESC, theme ASC
)
SELECT
  fs.family_id,
  fs.family_name,
  fs.total_score,
  fs.nb_sessions,
  fs.nb_players,
  btf.best_theme,
  fs.last_played_at,
  RANK() OVER (ORDER BY fs.total_score DESC) AS rank
FROM family_stats fs
LEFT JOIN best_theme_by_family btf ON btf.family_id = fs.family_id;

-- ------------------------------------------------------------
-- Vue v_player_leaderboard : classement des joueurs au sein
-- de chaque famille. La restriction à la famille autorisée est
-- assurée par les politiques RLS appliquées aux tables sources.
-- ------------------------------------------------------------
CREATE OR REPLACE VIEW public.v_player_leaderboard AS
WITH player_stats AS (
  SELECT
    p.id AS player_id,
    p.pseudo,
    p.avatar,
    p.family_id,
    COALESCE(SUM(s.weighted_score), 0)::NUMERIC(12,2) AS total_score,
    COUNT(s.*)::INTEGER AS nb_sessions,
    COALESCE(MAX(s.weighted_score), 0)::NUMERIC(10,2) AS best_score,
    MAX(s.created_at) AS last_played_at
  FROM public.players p
  LEFT JOIN public.scores s ON s.player_id = p.id
  GROUP BY p.id, p.pseudo, p.avatar, p.family_id
)
SELECT
  ps.player_id,
  ps.pseudo,
  ps.avatar,
  ps.family_id,
  ps.total_score,
  ps.nb_sessions,
  ps.best_score,
  ps.last_played_at,
  RANK() OVER (PARTITION BY ps.family_id ORDER BY ps.total_score DESC) AS rank_in_family
FROM player_stats ps;

-- ------------------------------------------------------------
-- Vue v_theme_champions : pour chaque thème, le joueur ayant
-- obtenu le meilleur score pondéré unique. En cas d'égalité,
-- le score le plus récent est retenu, puis l'UUID stabilise l'ordre.
-- ------------------------------------------------------------
CREATE OR REPLACE VIEW public.v_theme_champions AS
SELECT
  ranked.theme,
  ranked.player_id,
  ranked.pseudo,
  ranked.family_id,
  ranked.best_score,
  ranked.achieved_at
FROM (
  SELECT
    s.theme,
    s.player_id,
    p.pseudo,
    s.family_id,
    s.weighted_score AS best_score,
    s.created_at AS achieved_at,
    ROW_NUMBER() OVER (
      PARTITION BY s.theme
      ORDER BY s.weighted_score DESC, s.created_at DESC, s.player_id
    ) AS rn
  FROM public.scores s
  JOIN public.players p ON p.id = s.player_id
) ranked
WHERE ranked.rn = 1;
