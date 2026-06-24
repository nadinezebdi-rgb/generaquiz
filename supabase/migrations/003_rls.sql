-- ============================================================
-- Quiz d'Antan - Migration 003
-- Activation de Row Level Security et politiques d'accès.
-- Compatible Supabase Auth via auth.uid().
-- ============================================================

-- ------------------------------------------------------------
-- Activation de la sécurité ligne par ligne sur toutes les tables.
-- ------------------------------------------------------------
ALTER TABLE public.families ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.players ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.quiz_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.scores ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.badges ENABLE ROW LEVEL SECURITY;

-- ------------------------------------------------------------
-- Fonction helper : indique si l'utilisateur authentifié est membre
-- d'une famille via son profil player.auth_user_id.
-- SECURITY DEFINER évite les récursions de politiques entre tables.
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.is_family_member(target_family_id UUID)
RETURNS BOOLEAN AS $$
  SELECT EXISTS (
    SELECT 1
    FROM public.players p
    WHERE p.family_id = target_family_id
      AND p.auth_user_id = auth.uid()
  );
$$ LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public;

-- ------------------------------------------------------------
-- Fonction helper : indique si l'utilisateur authentifié est le
-- propriétaire d'une famille. Ici, le propriétaire est représenté
-- par un profil player lié à auth.uid() dans cette famille.
-- À adapter si une colonne owner_auth_user_id est ajoutée plus tard.
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.is_family_owner(target_family_id UUID)
RETURNS BOOLEAN AS $$
  SELECT public.is_family_member(target_family_id);
$$ LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public;

-- ============================================================
-- Politiques RLS : families
-- ============================================================

-- Politique families SELECT : un utilisateur lit uniquement sa famille.
DROP POLICY IF EXISTS "families_select_membre_famille" ON public.families;
CREATE POLICY "families_select_membre_famille"
ON public.families
FOR SELECT
TO authenticated
USING (public.is_family_member(id));

-- Politique families INSERT : tout utilisateur authentifié peut créer une famille.
DROP POLICY IF EXISTS "families_insert_utilisateur_authentifie" ON public.families;
CREATE POLICY "families_insert_utilisateur_authentifie"
ON public.families
FOR INSERT
TO authenticated
WITH CHECK (auth.uid() IS NOT NULL);

-- Politique families UPDATE : seul le propriétaire/membre authentifié peut modifier sa famille.
DROP POLICY IF EXISTS "families_update_proprietaire" ON public.families;
CREATE POLICY "families_update_proprietaire"
ON public.families
FOR UPDATE
TO authenticated
USING (public.is_family_owner(id))
WITH CHECK (public.is_family_owner(id));

-- Politique families DELETE : seul le propriétaire/membre authentifié peut supprimer sa famille.
DROP POLICY IF EXISTS "families_delete_proprietaire" ON public.families;
CREATE POLICY "families_delete_proprietaire"
ON public.families
FOR DELETE
TO authenticated
USING (public.is_family_owner(id));

-- ============================================================
-- Politiques RLS : players
-- ============================================================

-- Politique players SELECT : un utilisateur lit uniquement les joueurs de sa famille.
DROP POLICY IF EXISTS "players_select_meme_famille" ON public.players;
CREATE POLICY "players_select_meme_famille"
ON public.players
FOR SELECT
TO authenticated
USING (public.is_family_member(family_id) OR auth_user_id = auth.uid());

-- Politique players INSERT : tout utilisateur authentifié peut créer son profil.
-- Les profils invités sans auth_user_id doivent être créés côté serveur service role.
DROP POLICY IF EXISTS "players_insert_utilisateur_authentifie" ON public.players;
CREATE POLICY "players_insert_utilisateur_authentifie"
ON public.players
FOR INSERT
TO authenticated
WITH CHECK (auth.uid() IS NOT NULL AND (auth_user_id IS NULL OR auth_user_id = auth.uid()));

-- Politique players UPDATE : un joueur authentifié modifie uniquement son propre profil.
DROP POLICY IF EXISTS "players_update_profil_propre" ON public.players;
CREATE POLICY "players_update_profil_propre"
ON public.players
FOR UPDATE
TO authenticated
USING (auth_user_id = auth.uid())
WITH CHECK (auth_user_id = auth.uid());

-- Politique players DELETE : un joueur authentifié supprime uniquement son propre profil.
DROP POLICY IF EXISTS "players_delete_profil_propre" ON public.players;
CREATE POLICY "players_delete_profil_propre"
ON public.players
FOR DELETE
TO authenticated
USING (auth_user_id = auth.uid());

-- ============================================================
-- Politiques RLS : quiz_sessions
-- ============================================================

-- Politique quiz_sessions SELECT : un utilisateur lit uniquement les sessions de sa famille.
DROP POLICY IF EXISTS "quiz_sessions_select_meme_famille" ON public.quiz_sessions;
CREATE POLICY "quiz_sessions_select_meme_famille"
ON public.quiz_sessions
FOR SELECT
TO authenticated
USING (public.is_family_member(family_id));

-- Politique quiz_sessions INSERT : les sessions sont créées côté serveur avec service role.
-- Aucun INSERT direct client n'est autorisé pour le rôle authenticated.
DROP POLICY IF EXISTS "quiz_sessions_insert_service_role_uniquement" ON public.quiz_sessions;
CREATE POLICY "quiz_sessions_insert_service_role_uniquement"
ON public.quiz_sessions
FOR INSERT
TO service_role
WITH CHECK (true);

-- ============================================================
-- Politiques RLS : scores
-- ============================================================

-- Politique scores SELECT : un utilisateur lit uniquement les scores de sa famille.
DROP POLICY IF EXISTS "scores_select_meme_famille" ON public.scores;
CREATE POLICY "scores_select_meme_famille"
ON public.scores
FOR SELECT
TO authenticated
USING (public.is_family_member(family_id));

-- Politique scores INSERT : les scores sont soumis côté serveur avec service role uniquement.
DROP POLICY IF EXISTS "scores_insert_service_role_uniquement" ON public.scores;
CREATE POLICY "scores_insert_service_role_uniquement"
ON public.scores
FOR INSERT
TO service_role
WITH CHECK (true);

-- ============================================================
-- Politiques RLS : badges
-- ============================================================

-- Politique badges SELECT : un utilisateur lit uniquement les badges de sa famille.
DROP POLICY IF EXISTS "badges_select_meme_famille" ON public.badges;
CREATE POLICY "badges_select_meme_famille"
ON public.badges
FOR SELECT
TO authenticated
USING (public.is_family_member(family_id));

-- Politique badges INSERT : les badges sont attribués côté serveur avec service role uniquement.
DROP POLICY IF EXISTS "badges_insert_service_role_uniquement" ON public.badges;
CREATE POLICY "badges_insert_service_role_uniquement"
ON public.badges
FOR INSERT
TO service_role
WITH CHECK (true);

-- ------------------------------------------------------------
-- Droits de lecture sur les vues de classement.
-- Les vues globales sont exposées aux utilisateurs authentifiés ;
-- les politiques RLS des tables sources restent la barrière de sécurité.
-- ------------------------------------------------------------
GRANT SELECT ON public.v_family_leaderboard TO authenticated;
GRANT SELECT ON public.v_player_leaderboard TO authenticated;
GRANT SELECT ON public.v_theme_champions TO authenticated;
