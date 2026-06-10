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

## Implemented (2026-02-08, iteration 7) — Fix 3 priorités utilisateur
- ✅ **Priorité 1 — Shuffle Fisher-Yates** : QuizPlayer + ChallengePlay mélangent les 4 options à chaque question (stable durant la réponse). Plus de biais position A/B. Validé : 5 visites de `/app/quiz/cinema` → 5 premières options DIFFÉRENTES.
- ✅ **Priorité 2 — Décalage 30 vs 20** : limite Premium 20 → **30 questions** (utilise tout le pool). UI cohérente avec le `count` affiché.
- ✅ **Priorité 3 — Questions ambiguës** : o20 reformulée → "pétrir la pâte à pain" / Le pétrin ; o28 reformulée → "couper le sucre en pains coniques" / Un casse-sucre. Une seule bonne réponse défendable.
- ✅ **Mapping serveur** : `ChallengePlay` map shuffled→original avant POST `/participate` pour que le scoring serveur reste correct (anti-triche préservée).
- ✅ Tests : 11/11 nouveaux backend, 100% frontend (shuffle, stabilité par question, scoring cohérent, copie Premium = 30 questions partout).

## Implemented (2026-02-08, iteration 8) — Audit éditorial complet (14 corrections)
- ✅ **6 critiques (faits faux)** corrigés : a4 (date Âge tendre→1961), a17 (Bellemare→La tête et les jambes), a26 (remplacé par Perrier 1903), c24 (Manureva→Allô maman bobo), q40_30 (Bruel→Casser la voix), q70_27 (Vierzy 1968→1972)
- ✅ **5 moyennes (ambiguïtés)** : a13 (suppr "Toutes"), a30 (date Intervilles 1965→1962), cu5 (Toulouse→Castelnaudary unique), cu26 (mannele=bonhomme), q70_28 (Vietnam → LBJ 1965 ground troops)
- ✅ **3 mineures (précisions)** : c23 (Occupation au lieu de Mai 68), o15 (grillagé pour exclure buffet), ci19 (Sophie Marceau 14 ans)
- ✅ Total : 240 questions, **~6 % d'audit éditorial appliqué**, 226 questions inchangées (jugées correctes)
- ✅ Vérification 14/14 par script de contrôle automatique

## Implemented (2026-02-08, iteration 9) — Resend intégré (vrais emails)
- ✅ Installation `resend==2.30.1` + clé API + SENDER_EMAIL dans `.env`
- ✅ `_send_reset_email()` async non-bloquant via `asyncio.to_thread(resend.Emails.send, …)`
- ✅ Email HTML inline-styled (français, palette terracotta/navy, mobile-friendly) avec bouton CTA + lien de secours + mention "valable 1h"
- ✅ Endpoint `/api/auth/forgot-password` : plus de leak (`reset_token`, `reset_link`, `mocked` retirés)
- ✅ Réponse uniforme : `email_sent` toujours présent (true/false) pour empêcher l'énumération
- ✅ Frontend `/forgot-password` réécrit : plus de bloc "démo lien", remplacé par écran "Vérifiez votre boîte mail" + bouton "Renvoyer"
- ✅ Mode test Resend : seul `nadine.zebdi@gmail.com` (compte propriétaire) reçoit réellement l'email tant que le domaine n'est pas vérifié sur resend.com/domains
- ✅ Tests : 5/5 backend (test_forgot_password.py), 100% frontend, vrai email Resend reçu (id=c9111f21-...)

## Implemented (2026-02-08, iteration 10) — Refactor + rate-limit
- ✅ **Refactor server.py 970→120 lignes** (88 % de réduction). Structure modulaire :
  - `core.py` (218 lignes) : env, db, helpers, deps `get_current_user`/`get_admin_user`, rate-limiter factory, modèles Pydantic
  - `routers/auth.py` (175 lignes) : register/login/logout/me/forgot/reset/change-pw/profile/delete + Resend
  - `routers/quiz.py` (59 lignes) : categories/questions/attempts/stats
  - `routers/payments.py` (91 lignes) : Stripe checkout/webhook/packages
  - `routers/challenges.py` (97 lignes) : Défi Famille
  - `routers/promo.py` (103 lignes) : promo redeem + admin CRUD
- ✅ **Rate-limit IP-based in-memory** sur `/api/auth/forgot-password` (3 appels / 15 min, HTTP 429 + `Retry-After` au-delà)
- ✅ Isolation par endpoint : `/auth/login` non impacté par le bucket forgot-password
- ✅ Tests : 19/19 backend, 100 % frontend E2E, **zéro régression sur les 9 itérations précédentes**

## Implemented (2026-02-08, iteration 11) — Rebrand GénéraQuiz
- ✅ Nouveau nom : **GénéraQuiz** (avec "Quiz" en accent terracotta, "Généra" en navy)
- ✅ Nouveau slogan : **"Le jeu qui rapproche les générations"** (sous le logo navbar + dans le footer)
- ✅ Nouveau logo : composant `Logo.jsx` réutilisable — **deux cercles entrelacés SVG** (terracotta + navy avec dégradés) avec monogramme "GQ" en mustard au centre. Symbolise le rapprochement de deux générations.
- ✅ 3 tailles (`sm`/`md`/`lg`), 2 modes (`dark` pour fond sombre du footer), tagline optionnelle, link/no-link
- ✅ Application globale : Navbar, Footer, toutes pages auth (Login/Register/Forgot/Reset), email Resend
- ✅ HTML : `<title>GénéraQuiz — Le jeu qui rapproche les générations</title>`, meta description mise à jour
- ✅ Admin email : `admin@quizdantan.fr` → `admin@generaquiz.fr` (nouveau admin auto-créé au démarrage, mot de passe inchangé `Admin2026!`)
- ✅ Footer : `contact@generaquiz.fr`, mention `generaquiz.fr`
- ✅ Domaine Resend : prêt à recevoir `generaquiz.fr` une fois les DNS configurés


## Implemented (2026-02-08, iteration 12) — Massive question bank expansion
- ✅ **Total questions: 240 → 800** (+560 nouvelles questions générées par Claude Sonnet 4.5)
- ✅ **100 questions par catégorie** (30 curées + 70 IA) sur les 8 catégories
- ✅ Variété de difficulté par catégorie : ~50 % facile (enfants/famille), ~35 % moyen, ~15 % difficile (seniors connaisseurs)
- ✅ Public ciblé : enfants, parents, grands-parents en famille
- ✅ Architecture : `/app/backend/data/extra_questions/{category_id}.json` (8 fichiers JSON, 70 q chacun)
- ✅ Loader idempotent dans `seed_data.py` qui agrège base + extras
- ✅ Script de génération réutilisable : `/app/backend/generate_questions.py` (Claude Sonnet 4.5 via Emergent LLM Key, dédoublonnage automatique, batchs de 25)
- ✅ Catégories mises à jour : `count` = 100 (affiché dans la landing/dashboard)
- ✅ Reseed automatique au boot : 800 questions en DB, 100 par catégorie

## Backlog (P1/P2)
- 🟡 P1 : Vérifier le domaine `generaquiz.fr` sur Resend (action utilisateur DNS) puis basculer `SENDER_EMAIL` vers `contact@generaquiz.fr`
- 🟡 P2 : Mode tournoi (Défi Famille en temps réel multi-joueurs)
- 🟡 P2 : Système de badges / progression par catégorie
- 🟡 P2 : Stats avancées : graphique progression hebdo, classement amis
