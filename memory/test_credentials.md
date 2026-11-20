# Test Credentials for GénéraQuiz SaaS

## Admin Account (post-rebrand)
- **Email**: `admin@generaquiz.fr`
- **Password**: `pF44gVBfLdushm3NZ6dN`   ← nouveau, rotation faite le 2026-08-19 après un signalement de fuite dans l'historique du chat Emergent. L'ancien `Admin2026!` ne fonctionne plus.
- **Role**: `admin`
- **Plan**: `premium` (lifetime)

⚠️ Ce fichier n'est PAS servi par le backend static — il vit dans /app/memory/ et n'est utilisé que par les agents internes.

## Promo codes (seedés au démarrage)
- `FAMILLE2026` — à vie, utilisations illimitées
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
