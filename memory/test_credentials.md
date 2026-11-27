# Test Credentials for GénéraQuiz SaaS

## Admin Account (post-rebrand)
- **Email** : variable d'environnement `ADMIN_EMAIL` (`admin@generaquiz.fr`)
- **Password** : variable d'environnement `ADMIN_PASSWORD`. Ne jamais écrire le mot de passe dans ce fichier ni dans les tests : le dépôt GitHub est public.
- **Role**: `admin`
- **Plan**: `premium` (lifetime)

Les tests lisent `ADMIN_PASSWORD` (et `FAMILY_PROMO_CODE`) dans l'environnement :
`ADMIN_PASSWORD=... REACT_APP_BACKEND_URL=... pytest backend/tests`

## Promo codes (seedés au démarrage)
- Code cadeau « Premium à vie » : son nom vient de la variable `FAMILY_PROMO_CODE` (aucun code à vie sans elle). L'ancien code publié dans le dépôt est désactivé automatiquement au démarrage.
- `DECOUVERTE30` — 30 jours, max 50 utilisations

## Test User
Register a new account via `/register` for free-plan testing.

## Endpoints (préfixe /api)
- Auth: `/auth/{register,login,logout,me,forgot-password,reset-password,change-password,profile,account}`
- Quiz: `/categories`, `/categories/{id}/questions`, `/attempts`, `/stats`
- Stripe: `/packages`, `/checkout/session`, `/checkout/status/{id}`, `/webhook/stripe` (carte test 4242 4242 4242 4242)
- Défi famille: `/challenges` (POST premium), `/challenges/mine`, `/challenges/{token}` (public), `/challenges/{token}/participate` (public)
- Promo: `/promo/redeem` (auth), `/admin/promo` (admin CRUD — rôle admin requis)
- Livre coop: `/livre/coop/{create,join,{code}/state,{code}/entry,{code}/heartbeat,{code}/close}`
- Livre AI: `/livre/entries/{id}/{rewrite,accept-rewrite}`
- Livre from-quiz: `/livre/from-quiz`
- Static mascots: `/api/static/mascots/{category-id}.png`

## Rate limit
- `/auth/forgot-password` : max 3 appels / 15 min par IP (HTTP 429 au-delà)
