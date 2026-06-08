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

## Implemented (2026-02-08, iteration 4) — Expansion contenu
- ✅ +2 catégories culture générale dédiées : `culture-40-ans` (Sophie la Quadra, 20 questions 90s/2000s) et `culture-70-ans` (Pierre le Sage, 20 questions 60s/70s)
- ✅ 2 nouveaux personnages caricaturés générés via Nano Banana (Sophie avec vinyle/smartphone, Pierre avec livre/globe/lunettes rondes)
- ✅ Boost des 6 catégories existantes : 4 → 10 questions chacune (chansons, cinéma, années 50-60, objets d'antan, histoire de France, cuisine & terroir)
- ✅ Total : 100 questions, 8 catégories, 8 mascottes
- ✅ Hero landing mis à jour : « Huit univers, huit personnages », « 100+ questions », mention quadras + septuagénaires
- ✅ Tests : 50/50 backend + 100% parcours frontend
- ✅ Corrections éditoriales : q40_3 (L'Aventurier d'Indochine), q40_16 (Sous le Soleil à Saint-Tropez), cu8 (tablier de sapeur)

## Implemented (2026-02-08, iteration 5) — 240 questions + randomisation
- ✅ Pool de questions étendu : 100 → **240 questions** (30 par catégorie pour les 8 catégories)
- ✅ Backend `GET /api/categories/{id}/questions` utilise MongoDB `$sample` aggregation pour retourner un sous-ensemble aléatoire à chaque appel (5 pour free, 20 pour premium)
- ✅ Variété confirmée : 4 visites successives de `/app/quiz/chansons` produisent 4 premières questions différentes
- ✅ Défi Famille bénéficie aussi de la randomisation (déjà via `random.shuffle` côté création — vérifié : 3 défis créés successivement = 2+ snapshots distincts)
- ✅ Tests : **54/54 backend** (185+ cumulés), 100% frontend
- ✅ Couverture pool : test vérifie que 15 appels successifs en premium révèlent les 30 IDs uniques par catégorie (donc seed complet)

## Implemented (2026-02-08, iteration 6) — Espace compte + mot de passe oublié
- ✅ Backend (5 nouveaux endpoints) : `POST /api/auth/forgot-password` (no user enumeration), `POST /api/auth/reset-password` (token single-use, TTL 1h), `POST /api/auth/change-password` (auth, vérifie current_password), `PATCH /api/auth/profile` (auth, update name), `DELETE /api/auth/account` (auth, cascade attempts + challenges)
- ✅ Collection `password_reset_tokens` avec index TTL (expires_at) + unique (token)
- ✅ Email **MOCKÉ** : le lien de reset est retourné dans la réponse (`reset_token`, `reset_link`, `mocked:true`) — à remplacer par Resend/SendGrid quand voulu
- ✅ Frontend : 3 nouvelles pages — `/forgot-password`, `/reset-password?token=`, `/app/account` (profil + abonnement + changement mdp + suppression compte)
- ✅ Login : lien "Mot de passe oublié ?" ajouté
- ✅ Navbar : lien "Mon compte" pour utilisateurs connectés
- ✅ Tests : **82/82 backend** (12 nouveaux), 100% parcours UI end-to-end (register → forgot → reset → change pw → delete)
