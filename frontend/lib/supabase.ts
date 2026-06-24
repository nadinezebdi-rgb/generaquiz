import { createClient } from '@supabase/supabase-js';

// Singleton Supabase réutilisé dans toute l'app côté navigateur.
export const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
);
