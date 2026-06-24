-- ============================================================
-- Quiz d'Antan - Seed de développement local uniquement
-- Ces données servent aux tests Supabase en local.
-- Ne pas utiliser en production.
-- ============================================================

BEGIN;

-- ------------------------------------------------------------
-- Nettoyage ciblé des données de test pour pouvoir rejouer le seed.
-- Les suppressions en cascade retirent joueurs, sessions, scores et badges.
-- ------------------------------------------------------------
DELETE FROM public.families
WHERE invite_code IN ('DUP001', 'MAR042');

-- ------------------------------------------------------------
-- Familles de démonstration.
-- UUID fixes pour faciliter les tests et les exemples d'API.
-- ------------------------------------------------------------
INSERT INTO public.families (id, name, invite_code, created_at, updated_at)
VALUES
  ('11111111-1111-1111-1111-111111111111', 'Les Dupont', 'DUP001', now() - INTERVAL '12 days', now() - INTERVAL '2 days'),
  ('22222222-2222-2222-2222-222222222222', 'Famille Martin', 'MAR042', now() - INTERVAL '10 days', now() - INTERVAL '1 day');

-- ------------------------------------------------------------
-- Joueurs de démonstration : trois générations chez Les Dupont
-- et deux joueurs chez Famille Martin. auth_user_id reste NULL
-- pour simuler des profils invités en développement local.
-- ------------------------------------------------------------
INSERT INTO public.players (id, family_id, pseudo, avatar, auth_user_id, created_at)
VALUES
  ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1', '11111111-1111-1111-1111-111111111111', 'Papy René', 'grandpere', NULL, now() - INTERVAL '11 days'),
  ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2', '11111111-1111-1111-1111-111111111111', 'Maman Claire', 'mere', NULL, now() - INTERVAL '11 days'),
  ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa3', '11111111-1111-1111-1111-111111111111', 'Léo Junior', 'enfant', NULL, now() - INTERVAL '10 days'),
  ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb1', '22222222-2222-2222-2222-222222222222', 'Mamie Jeanne', 'grandmere', NULL, now() - INTERVAL '9 days'),
  ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb2', '22222222-2222-2222-2222-222222222222', 'Tom Martin', 'ado', NULL, now() - INTERVAL '8 days');

-- ------------------------------------------------------------
-- Sessions terminées de démonstration avec thèmes variés pour
-- tester les classements globaux, familiaux et par thème.
-- ------------------------------------------------------------
INSERT INTO public.quiz_sessions (id, player_id, family_id, theme, nb_questions, session_token, started_at, completed_at)
VALUES
  ('cccccccc-cccc-cccc-cccc-ccccccccccc1', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1', '11111111-1111-1111-1111-111111111111', 'nostalgie', 5, 'dev-token-dupont-rene-001', now() - INTERVAL '6 days', now() - INTERVAL '6 days' + INTERVAL '8 minutes'),
  ('cccccccc-cccc-cccc-cccc-ccccccccccc2', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2', '11111111-1111-1111-1111-111111111111', 'culture_generale', 5, 'dev-token-dupont-claire-001', now() - INTERVAL '3 days', now() - INTERVAL '3 days' + INTERVAL '7 minutes'),
  ('cccccccc-cccc-cccc-cccc-ccccccccccc3', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb2', '22222222-2222-2222-2222-222222222222', 'technologie', 5, 'dev-token-martin-tom-001', now() - INTERVAL '1 day', now() - INTERVAL '1 day' + INTERVAL '6 minutes');

-- ------------------------------------------------------------
-- Scores de démonstration : difficultés et bonus temps mixtes.
-- raw_score respecte toujours la contrainte raw_score <= total_questions.
-- ------------------------------------------------------------
INSERT INTO public.scores (
  id,
  session_id,
  player_id,
  family_id,
  raw_score,
  total_questions,
  weighted_score,
  difficulty_avg,
  time_bonus,
  theme,
  era,
  category,
  created_at
)
VALUES
  (
    'dddddddd-dddd-dddd-dddd-ddddddddddd1',
    'cccccccc-cccc-cccc-cccc-ccccccccccc1',
    'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1',
    '11111111-1111-1111-1111-111111111111',
    5,
    5,
    68.50,
    1.25,
    6,
    'nostalgie',
    'annees_60_80',
    'musique_et_objets',
    now() - INTERVAL '6 days' + INTERVAL '8 minutes'
  ),
  (
    'dddddddd-dddd-dddd-dddd-ddddddddddd2',
    'cccccccc-cccc-cccc-cccc-ccccccccccc2',
    'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2',
    '11111111-1111-1111-1111-111111111111',
    4,
    5,
    55.20,
    1.10,
    4,
    'culture_generale',
    'mix_intergenerationnel',
    'histoire_et_vie_quotidienne',
    now() - INTERVAL '3 days' + INTERVAL '7 minutes'
  ),
  (
    'dddddddd-dddd-dddd-dddd-ddddddddddd3',
    'cccccccc-cccc-cccc-cccc-ccccccccccc3',
    'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb2',
    '22222222-2222-2222-2222-222222222222',
    3,
    5,
    43.75,
    1.15,
    2,
    'technologie',
    'annees_2000_2020',
    'objets_connectes_et_web',
    now() - INTERVAL '1 day' + INTERVAL '6 minutes'
  );

-- ------------------------------------------------------------
-- Badges attribués pour tester les récompenses dans l'interface.
-- ------------------------------------------------------------
INSERT INTO public.badges (id, player_id, family_id, type, context, awarded_at)
VALUES
  (
    'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeee1',
    'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1',
    '11111111-1111-1111-1111-111111111111',
    'perfect_score',
    '{"theme": "nostalgie", "label": "Sans faute nostalgique"}'::jsonb,
    now() - INTERVAL '6 days' + INTERVAL '9 minutes'
  ),
  (
    'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeee2',
    'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2',
    '11111111-1111-1111-1111-111111111111',
    'first_game',
    '{"theme": "culture_generale", "label": "Première partie"}'::jsonb,
    now() - INTERVAL '3 days' + INTERVAL '8 minutes'
  );

COMMIT;
