# Quiz d'Antan — SaaS pour seniors français

## Problem Statement (verbatim)
"fais moi un saas avec les données ci jointes, avec des personnages caricaturé"
Source data: French senior quiz platform (6 categories, 8 activities, sample questions).

## User choices
- SaaS complet avec abonnement Stripe + auth JWT
- Caricatures cartoon coloré moderne
- Génération Nano Banana

## Architecture
- **Backend**: FastAPI, MongoDB (motor), JWT cookies, bcrypt, emergentintegrations (Stripe + Gemini)
- **Frontend**: React 19, react-router 7, Tailwind, framer-motion, axios, lucide icons
- **Routes API** (`/api`): auth/register, auth/login, auth/logout, auth/me, categories, categories/{id}/questions, attempts (GET/POST), stats, packages, checkout/session, checkout/status/{id}, webhook/stripe
- **Static**: `/api/static/mascots/*.png` — 6 generated caricatures
- **Frontend routes**: `/`, `/login`, `/register`, `/app/dashboard`, `/app/quiz/:categoryId`, `/app/pricing`, `/app/success`

## User personas
- Senior francophone (60+) — joueur principal, lecture vocale, gros caractères
- Famille / petits-enfants — défis (futur)
- Admin — seedé via .env

## Implemented (2026-02-08)
- ✅ Landing page (hero, marquee, 6 categories with mascots, démo quiz, activities, pricing, footer)
- ✅ Auth JWT (register, login, logout, /me) via httpOnly cookies
- ✅ Dashboard (stats, attempts, catégories)
- ✅ Quiz player (questions, lecture vocale FR, score, feedback, sauvegarde)
- ✅ Stripe checkout (Mensuel 9.99€ / Annuel 89.99€) avec polling + webhook
- ✅ 6 mascots cartoon générés via Gemini Nano Banana
- ✅ MongoDB seed automatique (catégories + 24 questions)

## P1 backlog (next iterations)
- Lecture vocale plus naturelle (OpenAI TTS)
- Activités fonctionnelles (Atelier Mémoire, Jeux de Mots, Journal de Vie)
- Défis famille (multi-joueurs)
- Reset password + email vérification
- Plus de questions par catégorie (cible 40-70 par catégorie)
- Customer portal Stripe (annulation, factures)
- Mode sombre / mode contraste élevé pour seniors mal-voyants

## Implemented (2026-02-08, iteration 2) — Défi Famille
- ✅ Backend: collection `challenges`, endpoints POST /api/challenges (Premium-only), GET /api/challenges/mine, GET /api/challenges/{token} (public, anti-cheat: hides correct_index), POST /api/challenges/{token}/participate (public, server-side score calculation)
- ✅ Frontend: /app/challenges (liste), /app/challenges/new (création + gating Premium), /app/challenges/{token} (lien partage WhatsApp/SMS/Email/copy + leaderboard live polling 5s), /defi/{token} (jeu public sans compte)
- ✅ Anti-triche : `correct_index` jamais exposé au client, score calculé côté serveur
- ✅ Tests : 38/38 backend (13 nouveaux pour challenges), tous parcours frontend validés

## Implemented (2026-02-08, iteration 3) — Codes promo
- ✅ Backend: collection `promo_codes`, endpoints `POST /api/admin/promo`, `GET /api/admin/promo`, `PATCH /api/admin/promo/{id}` (toggle), `DELETE /api/admin/promo/{id}` (admin-only via `get_admin_user` dependency), `POST /api/promo/redeem` (auth user). Validation : code unique, max_uses, expires_at, déduplication par utilisateur.
- ✅ Frontend : page admin `/app/admin/promo` (création + liste + copier + activer/désactiver + supprimer), bloc de redeem sur `/app/pricing` (avec gestion success/error et message persistant pendant la redirection).
- ✅ Durées : 7j / 30j / 90j / 1 an / illimité (36500 jours ≈ à vie).
- ✅ Tests : 16/16 backend + 4/4 parcours frontend (création admin, gating non-admin, redeem free→Premium, gating Premium).
- ✅ Seed démo : `FAMILLE2026` (à vie, illimité), `YYW3W1-R` (30j, 3 utilisations max).
