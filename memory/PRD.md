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

## Implemented (2026-02-08, iteration 13) — Quiz du Jour 🎯
- ✅ **Nouvelle feature : Quiz du Jour** — 5 questions quotidiennes, MÊMES pour tous, déterministes (seed = hash SHA256 du date_key)
- ✅ Mix multi-catégories : 5 catégories tirées au sort sur 8 chaque jour, 1 question par catégorie choisie
- ✅ **Jouable SANS COMPTE** (CTA viral) — score local uniquement pour les anonymes
- ✅ Pour les utilisateurs connectés : score sauvegardé + classement quotidien Top 10 + rang affiché
- ✅ **1 soumission/user/jour** : index unique MongoDB `(user_id, date_key)` + HTTP 409 si re-submit
- ✅ Endpoints : `GET /api/daily/quiz` (public), `POST /api/daily/submit` (auth), `GET /api/daily/leaderboard` (public + ranking si auth)
- ✅ Frontend route publique : `/quiz-du-jour` (intro → playing → done) avec shuffle d'options (Fisher-Yates)
- ✅ Écran de fin : trophy + rang + nudge Premium + share natif (`navigator.share`) avec fallback clipboard
- ✅ CTA Landing : bandeau bordeaux/navy `landing-daily-cta`, lien navbar `nav-daily`/`nav-daily-auth`
- ✅ Widget Dashboard : `dashboard-daily-cta` affiche le rang du jour si déjà joué, sinon "Jouer maintenant"
- ✅ Stat landing mise à jour : **800+ Questions**
- ✅ Tests : 13/13 backend pytest + 100% frontend E2E (anon + admin), aucune régression


## Implemented (2026-02-08, iteration 14) — Streaks 🔥 + Email matinal automatisé
- ✅ **Streaks** (séries de jours consécutifs) calculées au moment de la soumission du Quiz du Jour
  - 3 cas : première fois → 1 ; dernier=hier → +1 ; dernier ancien → RESET à 1, best préservé
  - Champs persistés : `streak_current`, `streak_best`, `streak_last_date` sur le document user
  - Exposés via `/api/auth/me` et retournés dans la réponse de `POST /api/daily/submit`
- ✅ **UI Streaks** :
  - Badge 🔥 dans le widget Dashboard (`data-testid=dashboard-streak-badge`)
  - Bloc dédié sur l'écran de fin du Quiz du Jour (`daily-streak-block`) avec mention "Record !" si streak_current == streak_best
  - Carte "Ma série & notifications" sur `/app/account` avec série actuelle + meilleure série + trophée 🏆 si >=7 jours
- ✅ **Email matinal automatisé** via Resend :
  - Scheduler APScheduler intégré à FastAPI (`/app/backend/daily_email.py`) déclenché à **09:00 Europe/Paris** chaque jour
  - Envoi uniquement aux users opt-in qui n'ont PAS encore joué aujourd'hui
  - Template HTML stylé (palette bordeaux/navy/mustard) avec badge streak + CTA "Jouer maintenant"
  - Rate-limit pacing 4 req/s (Resend max 5/s)
- ✅ **Opt-in/Opt-out** : `PATCH /api/auth/preferences/daily-email` (Pydantic-validated) + toggle UI sur Account (`account-email-optin-toggle`). Par défaut opt-in.
- ✅ **Endpoint admin manuel** : `POST /api/admin/daily-email/trigger` (admin-only) pour déclencher l'envoi à la demande
- ✅ Auto-refresh du contexte Auth après submit pour propager streak aux composants
- ✅ Tests : 11/11 backend pytest + 100% frontend (3/3 flows E2E)
- ✅ DB nettoyée : 49 users de test supprimés, reste 2 users légitimes (admin + nadine)


## Implemented (2026-02-08, iteration 15) — Backend prêt pour app mobile 📱
- ✅ **Économie de crédits virtuels** :
  - **5 crédits offerts à l'inscription** + backfill au boot pour comptes existants
  - Ledger `credit_ledger` (audit trail complet : welcome, hint, ad_reward, challenge_complete...)
  - `WELCOME_CREDITS=5`, `HINT_5050_COST=2`, `STREAK_SAVER_COST=10`, `AD_REWARD_DAILY_CAP=5/jour`
- ✅ **Endpoints gamification mobile** (`/api/gamification/...`) :
  - `GET /credits/balance` — solde + 20 dernières entrées ledger
  - `POST /credits/spend` — anti-cheat coût serveur, raisons whitelist (`hint_5050`, `streak_save`, `skip_question`, `bonus_question`)
  - `POST /credits/earn-ad` — +1 par pub, cap 5/jour avec HTTP 429
  - `POST /streak-saver` — sauvegarde de série après 1 jour manqué
  - `POST /challenge/submit` — score persisté + 50 XP base + 1 XP/correct + 1 crédit
  - `GET /leagues/current` — cohorte hebdo (30 joueurs), tier (bronze→argent→or→diamant), classement temps réel, timer fin semaine
- ✅ **Ligues hebdomadaires** :
  - 4 tiers : `bronze` → `argent` → `or` → `diamant`
  - Cohortes de 30 joueurs assignées de façon déterministe (SHA256 user+week+tier)
  - **Scheduler hebdo lundi 00:05 Europe/Paris** (APScheduler) : promotion Top 5 / relégation 3 derniers
  - XP gagné via `/daily/submit` (10 XP × score) et `/challenge/submit` (50 + score)
- ✅ **Apple Sign-In / Google Sign-In backend** (`/app/backend/routers/social_auth.py`) :
  - PyJWT 2.13 + cryptography + httpx async + cache JWKS 24h
  - Vérification stricte : iss / aud / exp (5 min leeway) / azp (Google) / email_verified (Google)
  - Endpoints `POST /api/auth/apple` et `POST /api/auth/google` (id_token → JWT applicatif)
  - **Safe by default** : 503 si env vars Apple/Google absentes (jamais d'auth non vérifiée)
  - Variables à configurer en prod : `APPLE_SERVICES_ID`, `APPLE_BUNDLE_ID`, `GOOGLE_WEB_CLIENT_ID`, `GOOGLE_IOS_CLIENT_ID`, `GOOGLE_ANDROID_CLIENT_ID`
  - `.env.example` documenté
- ✅ **Pages légales web (obligatoires Apple / RGPD)** :
  - `/cgu` Conditions Générales d'Utilisation
  - `/cgv` Conditions Générales de Vente (Stripe / Apple StoreKit / Google Play)
  - `/confidentialite` Politique de Confidentialité RGPD (CNIL ready)
  - Composant `LegalLayout.jsx` réutilisable + liens footer
- ✅ **DST-aware** : utilisation `zoneinfo("Europe/Paris")` pour basculement CET/CEST automatique (été/hiver)
- ✅ Tests : 17/17 backend pytest + 100% frontend smoke. Aucune régression.

## Architecture mobile (pour le nouveau projet Mobile Agent)
Le backend est **prêt à être consommé** par une app React Native :
- Auth : `/api/auth/{register,login,apple,google}` retournent `access_token` JWT
- Quiz : `/api/categories`, `/api/categories/{id}/questions`, `/api/attempts`
- Daily : `/api/daily/{quiz,submit,leaderboard}`
- Gamification : `/api/gamification/{credits,leagues,challenge}`
- Paiements : Stripe (web) + RevenueCat à brancher côté mobile (le backend reçoit déjà les webhooks Stripe)


## Implemented (2026-02-15, iteration 16) — 🤖 Toutes les questions générées par Mistral
- ✅ **Intégration Mistral AI** (SDK officiel `mistralai==1.5.0`) avec modèle `mistral-small-latest`
- ✅ **Régénération nocturne automatique** : APScheduler à **03:00 Europe/Paris** chaque nuit régénère **les 800 questions** (100/catégorie × 8 catégories)
- ✅ **Endpoint admin manuel** : `POST /api/admin/mistral/regenerate` (admin-only) lance la régénération en background (~5 min)
- ✅ **Architecture zero-downtime** :
  - Mistral génère TOUTES les questions en MongoDB (pool persistant)
  - Les joueurs jouent depuis MongoDB → **latence 0 ms** au quiz
  - Si une catégorie échoue côté Mistral → l'ancien pool est conservé (rollback automatique)
- ✅ **Seed initial conservé** : si MongoDB est vide au boot (premier déploiement / flush), les 240 questions seed servent de fallback en attendant la première régénération nocturne
- ✅ **Format JSON strict** : Mistral retourne du JSON pur via `response_format={"type": "json_object"}`, parsing robuste avec retry (3 tentatives par batch de 25 questions)
- ✅ **Coût estimé** : ~0,50 €/mois pour 24 000 générations/mois (8 cat × 100 q × 30 nuits)
- ✅ **Tests qualité** : 800/800 questions générées avec succès le 24/06, qualité factuelle excellente (1-2 % d'ambiguïtés possibles — bouton "Signaler" à ajouter en v2)

## Variables d'environnement à configurer en production
- `MISTRAL_API_KEY` — clé API Mistral (obtenue sur console.mistral.ai)
- `MISTRAL_MODEL` — défaut `mistral-small-latest` (recommandé : rapide + économique)

## Backlog (P2)
- Bouton "Signaler cette question" sur le frontend pour collecter les questions ambiguës générées
- Endpoint admin pour valider/supprimer manuellement les questions signalées
- Métriques mensuelles Mistral (latence moyenne, taux de retry, coût exact)


## Implemented (2026-02-15, iteration 17) — 🚩 Signalement de questions + revue admin
- ✅ **Bouton "Signaler" discret** sur chaque question (QuizPlayer + DailyQuiz) après réponse
- ✅ **Modal de signalement** avec 5 raisons : réponse incorrecte / ambiguë / doublon / inapproprié / autre + commentaire facultatif
- ✅ **Anti-spam** : 1 signalement par user par question (dédup 24h pending)
- ✅ **Backend** : nouveau router `/app/backend/routers/reports.py`
  - `POST /api/quiz/report` — auth required, raisons whitelist
  - `GET /api/admin/reports?status=pending|resolved|all` — admin only, agrégé par question avec compteurs
  - `POST /api/admin/reports/{question_id}/resolve` — action `delete` (supprime la question — Mistral régénère à 03h) ou `dismiss`
- ✅ **Frontend admin** : nouvelle page `/app/admin/reports` (`AdminReports.jsx`)
  - 3 onglets : En attente / Traités / Tous
  - Pour chaque question signalée : texte, options avec ✓ sur la bonne, badge Mistral 🤖, compteur par raison, commentaires dépliables
  - 2 actions : "Supprimer la question" (rouge) ou "Écarter" (blanc)
- ✅ **Navigation** : lien navbar admin "Signalements" (à côté de "Promos")
- ✅ Tests : flow complet validé (report → admin list → resolve dismiss → resolved tab)



## Validated (2026-02-16, iteration 18) — 🔑 Nouvelle clé Mistral
- ✅ Ancienne clé `HfmN...` révoquée par l'utilisateur (avait été partagée en clair)
- ✅ Nouvelle clé `ybVF...` (32 chars) installée via le panneau Environment Variables Emergent
- ✅ Test direct du SDK `mistralai==1.5.0` : 5 questions « Chansons françaises 60-70 » générées avec JSON valide
- ✅ Test backend end-to-end via testing agent (8/8 pytest passent) :
  - Admin login OK (admin@generaquiz.fr)
  - `POST /api/admin/mistral/regenerate` : 401 anon / 403 non-admin / 200 admin
  - Régénération Mistral lancée sans erreur d'authentification
  - Routes critiques non régressées : `/api/categories`, `/api/daily/quiz`, `/api/auth/me`

## Recommandations techniques relevées (à traiter en P2)
- **Concurrence régénération** : `asyncio.create_task(mistral_regenerate_all())` est fire-and-forget — ajouter un `asyncio.Lock` ou un statut Mongo pour empêcher 2 régénérations simultanées (risque de doubler les coûts Mistral)
- **Atomicité Mongo** : `delete_many` + `insert_many` non atomique — si le processus est tué entre les 2, la catégorie reste vide. Utiliser une approche "insert temp tag → atomic swap"
- **Truncation JSON** : `max_tokens=4000` peut tronquer la sortie sur les longs prompts (warnings observés). Soit augmenter, soit splitter en plus petits batches
- **Healthcheck Mistral** : ajouter une route `/api/admin/mistral/ping` qui appelle `client.models.list()` pour détecter les rotations de clé tôt


## 2026-02-16 — Sprint P2 + Mistral hardening (iteration 19) ✅

### Features livrées (14/14 backend, 5/5 frontend — tous tests verts)
- 🛡️ **Mistral hardening** : `asyncio.Lock` module-level empêche les régénérations concurrentes. Nouveau `GET /api/admin/mistral/ping` (ok, latency_ms, model, lock_held, last_run, questions_per_category, total_questions). Persistance dans `db.app_state`.
- 📧 **Email expiration Premium J-7** : APScheduler 10:00 Paris, helper idempotent via `users.expiration_email_sent_for`, skip comptes lifetime.
- 📊 **Stats publiques** : router `routers/stats.py` → `GET /api/stats/public` (no-auth). Frontend `StatsSection.jsx` avec 5 compteurs animés (IntersectionObserver + RAF). Détection pays via `Accept-Language`.
- 👥 **Parrainage** : router `routers/referral.py`. Code unique `PRENOM-XXXX`, index unique sparse + backfill startup. Bonus +5 crédits aux 2 parties à la 1ʳᵉ partie du filleul. Frontend: Register `?code=` prefill + validation live debounce 400ms. Account: carte "Parrainer un proche" avec code/lien/compteur/copy.
- 📺 **Pub → Crédit** : page `/app/earn-credits` avec timer 15s + AdSense slot (REACT_APP_ADSENSE_CLIENT/SLOT). House ad de fallback. Lien "Crédits" dans la Navbar avec badge solde.

### Code review comments traités
- ✅ DuplicateKeyError retry sur referral_code race
- ✅ Ledger-then-$inc dans grant_referral_bonus_if_eligible (audit safe)
- ⏳ Index sur `attempts.created_at` (déprioritisé, ok < 10k attempts)
- ⏳ Mongo transactions pour bonus (nécessite replica set)
- ⏳ Pool client Mistral (micro-opti ~50ms)

### Schéma DB ajouts
- `users.referral_code` (unique sparse), `referred_by_user_id`, `referral_count`, `referral_bonus_granted`, `country_code`, `expiration_email_sent_for`
- Collection `app_state` (key, status, started_at, finished_at, last_summary)

### Variables d'env ajoutées
- `REACT_APP_ADSENSE_CLIENT` (vide par défaut → fallback house ad)
- `REACT_APP_ADSENSE_SLOT`

## 2026-02-16 — Mode Coopératif "Défi Famille" Phase A (iteration 20) ✅

### Concept livré (14/14 backend + 7/7 frontend)
Refonte stratégique du Défi Famille : passe d'un quiz partagé "chacun pour soi" à un **jeu d'équipe asymétrique sur même appareil** (Senior + Jeune).
Inspiration : *It Takes Two*, *Keep Talking and Nobody Explodes* appliqué à la culture générale française.

### Mécaniques implémentées
- **Création de défi** (`/app/coop/new`) : team_name, 2 joueurs avec rôles différents obligatoires (Senior/Jeune), catégorie au choix parmi les 8 existantes, 4–20 questions
- **Alternance auto des questions** : Q0 → joueur 1, Q1 → joueur 2, etc. (annoté côté backend via `assigned_to: "senior"|"jeune"`)
- **Bouton "Demander de l'aide à <partner>"** → overlay "Passe le téléphone à <name> 📱→👴/🧒" qui CACHE la question jusqu'à ce que le partenaire confirme "C'est moi, c'est parti !"
- **Scoring asymétrique** :
  - Solo correct : **100 XP**
  - Avec aide correct : **50 XP**
  - Faux : **0 XP**
- **Stats finales** : total_xp, helps_used, helps_successful, correct_count, accuracy_pct
- **Race-condition guard** : conditional update `{current_index: idx, status: "in_progress"}` → 409 si double-submit parallèle
- **Accès libre (free + premium)** pour piloter l'engagement (volontairement non-gaté)

### Backend
- Nouveau router `/api/coop-challenges` (POST create, GET state, POST answer, GET mine/list)
- Collection MongoDB `coop_challenges` (index unique sur `token`, index composite `creator_user_id + created_at`)
- `_assign_role(idx)` alterne sur `idx % 2`
- `_public_view()` strip `correct_index/explanation` des questions à venir (visible dans `answers_log` pour le récap)

### Frontend
- `CoopChallengeCreate.jsx` : formulaire avec validation rôles différents
- `CoopChallengePlay.jsx` : gameplay complet avec overlay passe-plat, feedback animé, écran de résultats finaux
- Hero card "Mode Coopératif" en haut de `/app/challenges` (toujours visible, même pour les free)
- Section "Défi Classique" en dessous, gardée pour les Premium
- Champ `birth_year` optionnel à l'inscription

### Modèle utilisateur étendu
- `birth_year` (optional int, 1900-2026)
- `age_group` computed dans `user_to_public` : ≤25 = "jeune", ≥55 = "senior", autres = "libre" (préparation Phase B pour suggestions auto de duo)

### Code review comments traités
- ✅ Race-condition guard double-tap (conditional update)
- ✅ Bump birth_year max année à 2026
- ⏳ Strip `correct_index/explanation` du `answers_log` — laissé intentionnellement (récap éducatif)
- ⏳ `starter_index` paramétrable — non requis pour MVP
- ⏳ FinalResults state explicite — la dérivation actuelle est OK

## Roadmap Mode Coopératif

### Phase B (à venir — sur demande utilisateur)
4 nouvelles catégories modernes à générer via Mistral (~400 questions, 1 nuit) :
- 🎮 **Génération Écrans** (Léo le Streamer) — jeux vidéo, Twitch, YouTube
- 📱 **Tech & Réseaux** (Léna l'Influenceuse) — TikTok, Instagram, IA, smartphones
- 🎵 **Hits & Rap Actuel** (Rayan le Beatmaker) — rap français 2010-2026, hits Spotify
- 🍔 **Street Food & Fooding** (Chloé la Foodie) — bubble tea, smash burger, ramen, vegan

### Phase C (idées)
- Mode à distance (WebSocket sync entre 2 téléphones)
- Questions "Pont" (pop culture commune aux 2 générations) tagguées dans le pool
- Match "Choc des Générations" : duels avec scoreboard temps réel
- Suggestions auto de duo via `age_group` à la création (« Mamie + nièce de 12 ans »)


## 2026-02-16 — Sprint 1 Gamification "Rendre visible l'existant" (iteration 21) ✅

### Constat
2 piliers de la spec gamification utilisateur étaient déjà implémentés côté BACKEND mais totalement invisibles côté frontend :
- Ligues hebdomadaires (cohortes de 30, Bronze→Argent→Or→Diamant)
- Streak Saver (10 crédits ou pub pour ressusciter sa flamme)

Sprint 1 rectifie ça avec le minimum de code possible (10/10 backend pytest pass).

### Livré

**🏆 Page `/app/leagues`**
- Hero card avec tier badge (🥉🥈🥇💎), my_rank, my_xp, countdown live jusqu'à dimanche 22h Paris
- Section "Comment ça marche" expliquant promo (5 premiers) / relégation (3 derniers)
- Leaderboard 30 joueurs max avec lignes promotion (verte pointillée) et relégation (rouge pointillée)
- Ma ligne en surbrillance mustard + médailles 🥇🥈🥉 pour top 3
- État vide explicite quand la cohorte n'a qu'un membre
- Gestion erreur 401/réseau avec bouton "Réessayer"

**🔥 StreakSaverModal (auto-trigger sur Dashboard)**
- Détection client-side via `streakAtRisk(user)` — streak≥2 + last_date == J-2
- Flamme animée Framer Motion, message "Votre flamme s'éteint !"
- 2 boutons : "Sauver pour 10 crédits" (terracotta) OU "Gagner des crédits via pub" (lien EarnCredits)
- Bouton "Tant pis, je laisse filer" + close croix
- onSaved refresh le user state du contexte

**📧 Email rappel ligue dimanche 20h Paris**
- Nouveau cron APScheduler `league_reminder_sunday_20h`
- Cible : ranks 6-8 (close to promote) + ranks (N-5..N-3) (close to relegate)
- Skip cohortes < 9 joueurs pour éviter promote/relegate overlap
- Idempotent : `reminder_sent_week` posé par user pour ne pas spammer
- Sujet : "🚀 Plus que 2h pour grimper en ligue supérieure !" / "⚠️ Tu risques de perdre ta ligue"
- Skip si RESEND_API_KEY absent (renvoie `{sent:0, reason:'no_resend_key'}`)

**🔄 XP feeds toutes les voies vers les ligues**
- `POST /api/attempts` (quiz catégorie) → +XP_PER_CORRECT_CATEGORY × score dans league_scores
- `POST /api/coop-challenges/{token}/answer` → +xp_earned (100/50/0) dans league_scores
- `POST /api/daily/submit` était déjà branché (no-op)

**🐛 Cohorte bucketing**
- `LEAGUE_BUCKETS_PER_TIER = 10` (était 10000) → cohortes se remplissent dès ~30 users actifs au lieu de jamais
- Documenté pour montée à 50+ buckets quand DAU > 300

### Navigation
- Navbar : nouveau lien "Ligues" 🏆 entre "Mes quiz" et "Défi famille"
- Route protégée `/app/leagues`

### Tests
- 10/10 backend pytest pass (`/app/backend/tests/test_iteration21_leagues.py`)
- Frontend Leagues + Dashboard + Navbar : tous les data-testids vérifiés
- Code review : 7 commentaires non-bloquants, 3 traités (cohort bucketing, n<9 guard, 401 UI)

### Reste pour Sprint 2 (mode coop récompensé)
- Combo multiplier ×1/×1.5/×2/×3 dans `/api/coop-challenges/{token}/answer`
- Carte fin de partie partageable "Complicité 95%" (réutilise ScoreCard.jsx)
- Badge "Sauveur" simplifié

### Reste pour Sprint 3 (mascottes)
- Système `users.mascot_levels` + tracking points par catégorie
- 4 paliers cosmétiques par mascotte (skins générés via Nano Banana)
- Page `/app/collection`


## 2026-02-16 — Sprint A+B+C : Sécurité + Badges + Progression (iteration 22) ✅

Basé sur l'audit PDF externe (`generaquiz_analysis.pdf`). 15/15 backend pytest + frontend OK.

### 🔒 A. Server-authoritative scoring (Reco #1 audit, P0 sécurité)
**Avant** : `POST /api/attempts { score:999, total:999 }` depuis la console navigateur → cheat instant #1 en Ligue Diamant.

**Après** :
- `AttemptCreate` payload = `{category_id, answers: [{question_id, answer_index}], duration_seconds}`
- Serveur charge les `correct_index` depuis Mongo et recalcule le score
- Refuse un `question_id` étranger à la `category_id` (400)
- `answer_index` borné 0-3 par Pydantic (422 si tricheur)
- Idem pour `/api/daily/submit` (contre les cached daily questions)
- Frontend `QuizPlayer.jsx` et `DailyQuiz.jsx` mappent le `selected` shuffled → `original_index` avant envoi

### 🏅 B. Badges persistants (Reco #5 audit)
- Catalog `/app/backend/badges.py` : **15 badges** répartis en 5 familles (starter, streak, daily, coop, league, social)
- Collection `user_badges` avec index unique `(user_id, badge_id)` → idempotent
- Helper `award_badge()` + hooks in-line dans les endpoints (never breaks the request on failure)
- Nouveaux endpoints : `GET /api/badges/catalog` (avec flag `earned` par user) + `GET /api/badges/mine`
- Réponses des endpoints de jeu incluent `awarded_badges: string[]` → toast client via `sonner`
- Frontend `lib/badgeToast.js` : `showBadgeToasts()` déclenche des toasts célébratoires avec délai staggeré

### 📈 C. Progression solo (Reco #6 audit)
- **Level curve** : `xp_for_level(L) = 25 * L * (L+1)` — L1=0, L2=50, L5=750, L10=2750, L20=10500 XP
- `compute_level(xp)` retourne `{level, xp_in_level, xp_to_next, progress_pct}` → exposé dans `user_to_public`
- **Category mastery** : collection `user_category_stats` upserted à chaque `/api/attempts`
  - Tiers : Novice → Apprenti (20+ answered) → Confirmé (50+, ≥70%) → Expert (100+, ≥80%) → Maître (200+, ≥90%)
- Nouveau endpoint `GET /api/progression/me` : level + mastery par catégorie
- Nouvelle page `/app/progression` : hero niveau avec barre XP animée, grille 15 badges (verrouillés grisés), 8 bars mastery avec mascotte

### 🧭 Navbar
- Nouveau lien "Niv X" avec l'éclair ⚡ → `/app/progression`

### 📊 Data model additions
- `users.xp_total` (existait, maintenant utilisé)
- `users.level` **computed** dans user_to_public (pas stocké — recalculé depuis xp_total)
- Collection `user_badges` `{user_id, badge_id, earned_at, meta?}` (unique idx)
- Collection `user_category_stats` `{user_id, category_id, correct, total, quizzes_played, created_at, updated_at}` (unique idx)
- Index composite `questions.{id, category_id}` pour la security lookup performance

### Code review comments (non traités, non bloquants)
- `compute_level` scan linéaire jusqu'à L500 — closed-form dispo si perf devient un souci
- `check_after_attempt` fait un `count_documents` — cheap à low volume, ajouter `first_quiz_awarded_at` sur user quand DAU > 1000
- Navbar wrap sur desktop 1920px — cosmétique, tolérable pour l'instant
- `model_config = ConfigDict(extra='forbid')` sur `AttemptCreate` pour bloquer les champs inconnus au lieu de les stripper

### Ce qui n'est PAS fait (spec audit)
- **Reco #2** collection unifiée `game_sessions` → refacto, low ROI
- **Reco #4** extraction `challenges.participants` → seulement si volume élevé
- **Reco #7** multijoueur live WebSocket → gros chantier séparé
- **Reco #9-10** real-time leaderboards → polling OK au MVP
- **Reco #8** clean README Supabase → doc, low priority


## 2026-02-16 — UX seniors : traduction FR + BadgeShareCard (iteration 23) ✅

### Contexte
Le cœur de cible (Françoise 72 ans, Papi Robert) a déjà des difficultés en informatique — les termes anglais sont un obstacle majeur. On simplifie le vocabulaire visible ET on ajoute le partage social des exploits.

### Changements
- ❌ **Retiré** : le badge "Plus de 12 000 seniors nous font confiance" sur la Landing (chiffre non-fondé)
- ✅ **Remplacé par** : "Le jeu qui réunit les générations" (positionnement sans chiffre)
- 🇫🇷 **XP → points** dans toute l'interface visible :
  - `Leagues.jsx` : "Mes points" et "points" au lieu de "XP"
  - `Progression.jsx` : "0 points au total, plus que 50 points pour le niveau 2"
  - `CoopChallengePlay.jsx` : "+50 points au lieu de 100 si solo", "+xxx points", "xxx points" (5 occurrences)
  - `Challenges.jsx` : "100 points en solo", "Terminé · X points" (3 occurrences)
  - Variables internes (`xp_total`, `xp_gained`, `my_xp` dans l'API) **conservées** pour compat backend
- 🏆 **Nouveau composant** `BadgeShareCard.jsx` : carte PNG partageable pour chaque badge débloqué
  - Halo lumineux coloré selon `tier` (bronze/argent/or/diamant)
  - Grand emoji du badge dans un cercle avec shadow-warm
  - "Palier bronze/argent/or/diamant" en label
  - Titre + description du badge
  - "Débloqué par [PRÉNOM]" avec accent doré
  - Date au format français ("1 juillet 2026")
  - Footer : "generaquiz.fr · Le jeu qui rapproche les générations"
  - 3 actions : Partager (Web Share API + fallback clipboard) / WhatsApp (wa.me deep link) / Télécharger PNG (html-to-image)
- 🖱️ **Interaction Progression** :
  - Badges débloqués → tuile cliquable avec icône Share2 en top-right (data-testid `badge-earned-<id>`)
  - Clic ouvre modal `data-testid='badge-share-modal'` avec la BadgeShareCard
  - Overlay `bg-navy/85 backdrop-blur-sm`, fermeture au clic hors modal ou bouton croix
  - Message subtil : "Cliquez sur un badge pour partager votre exploit 🎉"
  - Badges verrouillés → non-interactive `<div>` (pas de handler)

### Tests
- 100% frontend passed (iteration 23)
- Phrase seniors bien absente
- 0 occurrence de "XP" visible sur les pages testées
- Modal ouvre/ferme correctement, 3 boutons fonctionnels
- WhatsApp deep link vérifié avec le bon texte
- PNG download avec nom `generaquiz-badge-<id>.png`
- Badges verrouillés non-cliquables


## 2026-02-16 — Section "Une plateforme complète" sur la Landing (iteration 24) ✅

### Contexte
L'utilisateur a soumis un prototype HTML/CSS externe (`generaquiz-dashboard.zip`) présentant une nouvelle section positionnant GénéraQuiz comme une **plateforme d'activités seniors** au-delà des quiz. 7 activités mises en avant, toutes en cours de développement.

Choix utilisateur: **1c/2a/3a** → section ajoutée à la Landing publique, cartes en placeholder "En développement", bouton "Tout découvrir" scrolle vers Tarifs.

### Livré (100% frontend, 0 backend touché)
- Nouveau composant `PlatformSection.jsx` injecté sur la Landing entre Categories et Pricing
- **Sidebar gauche** (sticky en desktop) :
  - Pill bordeaux "Au-delà des quiz"
  - Titre "Une plateforme complète" (« complète » en terracotta italique)
  - Description marketing
  - Bouton navy "Tout découvrir →" qui scrolle smoothly vers `#tarifs`
- **Section Quiz & Activités** (4 cartes, icônes terracotta) :
  - 🧠 **Atelier Mémoire** — badge « Nouveau » (mustard)
  - 📖 **Mon Journal de Vie** — badge « Populaire » (terracotta light)
  - 🍽️ **Recettes d'Antan**
  - 📷 **Photothèque**
- **Séparateur pointillé** "JEUX DE MOTS"
- **Section Jeux de Mots** (3 cartes, icônes navy) :
  - ✏️ **Mots Croisés**
  - 💬 **Charades**
  - 🔍 **Mots Mêlés**
- Toutes les cartes portent un badge "EN DEV." en haut à droite + `cursor-not-allowed` + tooltip "En cours de développement"
- Note d'info en bas : "🚧 Toutes ces activités sont en cours de développement. Rejoignez Premium pour y accéder en avant-première"
- Animation Framer Motion staggered à l'apparition (delay 0.05s par carte)
- Palette parfaitement intégrée au design system existant (aucun nouveau token CSS)

### Data-testids ajoutés
- `platform-section`, `platform-pill`, `platform-discover-btn`, `platform-separator`, `platform-availability-note`
- `platform-card-<key>` × 7, `platform-badge-dev-<key>` × 7


## 2026-02-16 — Sprint 2 Coop Récompensé (iteration 25) ✅

### Combo multiplier — Backend
Nouveau système dans `routers/coop_challenges.py` :
- `COMBO_TIERS` : 3 correct-no-help d'affilée = ×1.5, 5 = ×2, 7+ = ×3
- Streak reset par `is_correct == False` OU `help_used == true`
- `stats_coop.current_combo` (streak en cours) + `stats_coop.best_combo` (max atteint)
- `stats_coop.solo_correct_count` (pour le calcul de complicité)
- Base XP × multiplier appliqué à `xp_earned` (100→300 sur combo ×3)
- Réponse `/answer` retourne `combo`, `multiplier`, `combo_broken`, `base_xp`
- Testé ×1.0 → ×1.5 → ×2 → ×3 → break sur help_used ✅

### Combo UI — Frontend `CoopChallengePlay.jsx`
- Bandeau `data-testid='coop-combo-banner'` en haut de la page quand combo ≥ 3
- Affichage "🔥 Combo ×2 · 5 d'affilée sans aide" avec animation spring
- Feedback après réponse : "+150 points" + label rouge "Combo ×1.5" ou "Combo perdu 💔"

### Carte de fin partageable — Nouveau composant `CoopShareCard.jsx`
Réutilise la mécanique html-to-image de `BadgeShareCard`.

Contenu de la carte :
- Header "GénéraQuiz · Duo" + date FR
- **Complicité XX%** en géant (fontSize 96) sur fond mustard
- Titre du tier :
  - ≥95% : Fusion Temporelle Parfaite ✨🧡
  - ≥85% : Duo Légendaire 🌟
  - ≥70% : Complices de Toujours 🤝
  - ≥50% : Belle Équipe 👍
  - <50%  : Duo en Rodage 🌱
- Grille 2×2 : Bonnes réponses, Combo max, Aides réussies, Points
- Bloc "LE DUO — Player1 + Player2 — « TeamName »"
- 3 boutons : Partager (Web Share API), WhatsApp (`wa.me`), Télécharger PNG

Formule de complicité : `round((solo_correct + helps_successful × 0.75) / total × 100)`.
Les aides réussies comptent 75% (récompense l'entraide sans dévaluer le solo).

### FinalResults refonte
- La carte partageable devient LA carte de résultats principale
- 3 stats compactes en dessous : aides sauvées, combo max, précision %
- 2 boutons : Refaire un défi / Mes défis
- Suppression du header "Trophy" + team_name séparé (déjà dans la carte)

### Data-testids
- `coop-combo-banner`, `coop-combo-multiplier`
- `coop-feedback-mult`, `coop-feedback-combo-broken`
- `coop-share-wrapper`, `coop-share-visual`, `coop-share-complicity`
- `coop-share-btn`, `coop-share-whatsapp`, `coop-share-download`
- `coop-final-card`, `coop-final-combo`, `coop-final-accuracy`, `coop-final-helps`


## 2026-02-16 — Sprint A Vision "Duolingo de la mémoire" — Hero & positionnement (iteration 25) ✅

### Refonte Hero
- **Nouveau H1** : « 5 minutes par jour pour **stimuler votre mémoire** et partager un moment en famille » (positionnement précis, promesse temps + duo mémoire/famille)
- **Sous-titre** citant la stimulation cognitive et le lien social (langage prudent, pas médical)
- **Pill** : « Le premier club mémoire intergénérationnel »
- **⭐⭐⭐⭐⭐** avec « Déjà adopté par des familles partout en France » (sans chiffre inventé)
- **CTA unique** « Commencer gratuitement » (le bouton secondaire « Essayer un quiz » a été supprimé pour focaliser)
- **Micro-copie de réassurance** sous le CTA : « Sans engagement · Aucune carte bancaire requise · Prêt en 30 secondes »

### Nouveau composant `HeroPhoneDemo.jsx`
Animation scriptée en boucle (Framer Motion) montrant le cœur de la valeur :
- Header : mascotte + badge streak clignotant "🔥 3j"
- Barre de progression qui remplit à chaque étape
- Question affichée dans un cadre cream
- 4 options → révélation de la bonne réponse (bounce + vert)
- Écran "Excellente réponse ! 1/5" → bascule vers "Badge débloqué : Premier pas +100" avec confettis emojis 🎉✨🧡🥇🌟
- Sticker corner "Ligue Or 🏆"
- Loop entre 2 catégories (Chansons françaises, Cinéma français)
- Score et streak s'incrémentent à chaque cycle

### Nouveau composant `TestimonialsSection.jsx`
Section « Ils jouent déjà avec GénéraQuiz » injectée entre le marquee et le Daily CTA :
- 3 témoignages types : **Senior** (Françoise 72 ans), **Famille** (Marc 38 ans, Lyon), **EHPAD** (Sylvie animatrice, EHPAD Les Tilleuls)
- Chaque carte : badge coloré du type + 5 étoiles + Quote icon + citation + nom + contexte
- Animation staggered à l'apparition (delay 0.1s par carte)
- Copy volontairement anonymisé pour ne pas inventer de faux témoignages — à personnaliser plus tard

### Data-testids ajoutés
- `hero-title`, `hero-subtitle`, `hero-pill`, `hero-rating`, `hero-reassurance`
- `hero-phone-demo`
- `testimonials-section`, `testimonial-0/1/2`

### À venir (Sprints B → E)
- **Sprint B** : 3 paliers tarifaires (Club Mémoire 4,99€ / Famille 7,99€ / Premium 12,99€) + Stripe multi-price
- **Sprint C** : Score Mémoire 5 axes (Culture / Régularité / Attention / Rapidité / Mémoire) + radar chart
- **Sprint D** : Landing EHPAD dédiée + Mode Senior (fonts XL, TTS)
- **Sprint E** : Page /pourquoi (science) + Admin dashboard analytics



---

## Sprint B — 3 paliers tarifaires (2026-08-07) ✅

Backend: `PACKAGES` dict in `core.py` étendu à 6 packages (club/famille/premium × monthly/yearly) —
seule source de vérité, monnaie EUR :
- club_monthly 4,99 € · club_yearly 49,99 €
- famille_monthly 7,99 € · famille_yearly 79,99 €
- premium_monthly 12,99 € · premium_yearly 129,99 €

`/api/checkout/session` accepte les 6 `package_id` et persiste `tier`/`period` sur la transaction.
Webhook et /checkout/status écrivent en parallèle `plan='premium'` (legacy) et `plan_tier`/`plan_period` (nouveau).

Frontend `Pages/Pricing.jsx` :
- Toggle Mensuel/Annuel avec badge économie
- 4 cartes (Découverte gratuit + Club Mémoire + Famille + Premium)
- Famille en carte "Le plus populaire"
- Radar sur "Formule actuelle" quand user.plan_tier match
- FAQ mini + bandeau réassurance

Fixes suite iteration 25 :
- Route `/app/pricing` sortie de `ProtectedRoute` → page publique (redirige au login au clic CTA)
- `seed_admin` : ajout `plan_tier='premium'` + `plan_period='yearly'` + backfill idempotent pour l'admin existant

Tests: iteration 25 (9/9 pytest backend) + iteration 26 (retest UI 100 %) — verts.

## Sprint C — Score Mémoire 5 axes (2026-08-07) ✅

Nouveau module `/app/backend/memory_score.py` — 5 axes cognitifs recalculés à chaque appel
depuis les collections existantes (aucun stockage) :
- **Culture** — précision globale sur `attempts` (cold-start si < 3 quiz)
- **Régularité** — jours joués sur 30 j (attempts ∪ daily_attempts) + bonus streak
- **Attention** — précision sur `daily_attempts` (cold-start si < 3)
- **Rapidité** — moyenne secondes/question, mapping 6 s → 100 pts / 25 s → 0 pt
- **Mémoire** — précision cumulée × multiplicateur de largeur (nombre de catégories jouées)

Overall = moyenne des 5 axes. Tous les scores clampés 0-100.

Endpoint : `GET /api/progression/memory-score` (auth requis).

Composant frontend `/app/frontend/src/components/MemoryScoreRadar.jsx` — recharts RadarChart :
- Card "Score Mémoire" avec badge tier (Cold start → Exceptionnel) et overall /100
- Radar SVG à 5 axes
- 5 boutons axis-*, panneau focus avec hint + flag cold_start
- Intégré dans `Progression.jsx` au-dessus des badges

Tests: iteration 27 — 5/5 pytest backend + UI e2e verts.

### À venir
- **Sprint D** : Landing EHPAD `/ehpad` + Mode Senior (fonts XL, contraste, TTS)
- **Sprint E** : `/pourquoi` (science) + Admin Analytics
- **Stripe Prod Keys** : bascule test → live
- **Sprint 3 Mascottes** : 4 niveaux d'affection (Nano Banana skins)
- **Refactor** : découper `server.py` (APScheduler), unifier attempts / daily_attempts / coop_challenges

---

## Sprint D + Atelier Mémoire + Mascot Affection (2026-08-07) ✅

### Sprint D — EHPAD landing + Mode Senior
- Nouvelle page publique **`/ehpad`** ciblée animateurs/directeurs (Hero, benefits, stats, CTA démo mail + tel)
- **SeniorModeContext** + **SeniorModeToggle** (Confort+ dans la Navbar sur toutes les pages)
  - Toggle une classe `.senior-mode` sur `<html>` → CSS boostent base font (20px), tap targets (52px min), border 2px, focus outline 4px terracotta
  - Pref stockée dans `localStorage.gq_senior_mode`

### Atelier Mémoire — première activité non-quiz
- Nouveau routeur `/app/backend/routers/atelier.py` (mount sur `/api/atelier`)
  - 5 thèmes × 5 prompts ouverts (annees-60/70/80/enfance/famille)
  - `POST /atelier/sessions` sauvegarde les réponses libres dans `atelier_entries`, +25 pts, badge `premier_atelier` idempotent + `atelier_5` au 5ᵉ atelier
  - `GET /atelier/entries` renvoie les sessions groupées
- 2 nouvelles pages front : `/app/atelier` (flow 5 étapes) et `/app/atelier/mes-souvenirs` (carnet de souvenirs)
- 2 nouveaux badges au catalogue : `premier_atelier` (argent), `atelier_5` (or)

### Mascot Affection — Sprint 3 débloqué (Nano Banana)
- Script `generate_mascot_skins.py` → **24 skins générés** via `emergentintegrations` (Gemini Nano Banana `gemini-3.1-flash-image-preview`)
  - 3 skins par mascotte (level 1: friendly wave, level 2: in action, level 3: golden hero) × 8 catégories
- Backend `progression.py`: `_affection_for(total)` → level 0/1/2/3 selon réponses cumulées (0/20/100/500)
- Front `Progression.jsx`: rendu du skin correspondant + badge overlay `♥{level}` (fallback vers image de base si 404)

Tests: iteration 28 — 20/21 pytest backend + Frontend 100 % — verts.
Coût crédit LLM confirmé pour la génération des 18 skins (finalement 24 pour cohérence 8 catégories).

### Backlog restant
- **Stripe Prod Keys** : bascule test → live
- **Sprint E** : `/pourquoi` (science) + Admin Analytics
- **Refactor** : découper `server.py`, unifier attempts/daily_attempts/coop_challenges en `game_sessions`
- **Mobile app** : Expo React Native
- **CRM connect** : demandes EHPAD via mailto → HubSpot / Brevo


---

## Sprint E — /pourquoi + Admin Analytics (2026-08-07) ✅

### Page publique `/pourquoi` — la science derrière l'app
- Hero avec titre "Un quiz par jour, jusqu'à 38 % de démence en moins."
- 4 chiffres-clés cliqués sur études réelles :
  - 38 % risque démence en moins (Verghese, NEJM 2003)
  - +5 ans espérance vie cognitive (Wilson, Neurology 2013)
  - ×2 baisse dépression (Menec, Gerontology 2003)
  - ≥ 3×/sem. seuil efficacité mesuré
- 3 piliers : répétition espacée, progression adaptée, lien intergénérationnel
- 4 cartes d'études cliquables (liens vers NEJM, Neurology, Oxford Academic)
- Bandeau d'honnêteté : GénéraQuiz n'est pas un dispositif médical
- CTA final vers `/ehpad` + `/register`

### Dashboard Admin `/app/admin/analytics`
Nouveau routeur `admin_analytics.py` monté sur `/api/admin/analytics/*` (guard `get_admin_user`) :
- `GET /overview` — total users, new_30d/24h, paid, conversion_pct, DAU, MAU, dau_mau_pct, MRR estimé, revenue MTD, ARPU
- `GET /signups?days=30` — timeseries inscriptions jour par jour (clamped 1-180)
- `GET /revenue?days=30` — timeseries recettes journalières EUR
- `GET /categories` — top catégories par attempts + accuracy
- `GET /atelier` — sessions, entries, unique users, breakdown par thème

Frontend `AdminAnalytics.jsx` :
- 4 KPI cards (Users / Paid / MRR / DAU-MAU)
- 2 recharts (LineChart signups + BarChart recettes)
- Tableau top catégories
- Bloc Atelier Mémoire (sessions / entries / unique / avg + by_theme)
- Bouton Rafraîchir

Navbar admin : nouveau lien `Analytics` (data-testid nav-admin-analytics) visible uniquement pour role=admin.
Footer : nouveaux liens `footer-pourquoi` et `footer-ehpad`.

Tests: iteration 29 — 19/19 pytest backend + Frontend 100 % — verts.

### Notes tech (revue code)
- Aggregations sur `created_at` stockés en ISO string (fragile si passage à datetime — à unifier)
- MRR estimate duplique le prix par tier — à centraliser un jour avec `PACKAGES`
- `signups` charge jusqu'à 20 000 docs en mémoire — OK à cette échelle, à passer en `$group` MongoDB au-delà

### Backlog restant
- **Onboarding Tour** (P1) : tour interactif 4-5 tooltips au premier login
- **Coop Atelier** (P1) : session famille partagée (invitation par lien)
- **EHPAD CRM** (P1) : Brevo/HubSpot/collection Mongo — à trancher
- **Refactor** : découper `server.py`, unifier `attempts / daily_attempts / coop_challenges` en `game_sessions`
- **Mobile app** : Expo React Native


---

## Jeux de Mots — Étape 0 + 1 : Charades (2026-08-08) ✅

### Étape 0 — PlatformSection assainie
- Carte **Atelier Mémoire** : maintenant Link cliquable vers `/app/atelier`, badge "En ligne" vert + pill "Jouer" (au lieu de "EN DEV")
- Carte **Charades** : ajoutée comme Link vers `/app/charades`, badge "Nouveau"
- Les autres cartes (Journal de Vie, Recettes d'Antan, Photothèque, Mots Croisés, Mots Mêlés) restent en "EN DEV" avec `cursor-not-allowed`
- Sidebar réécrite : "Deux sont déjà en ligne."

### Étape 1 — Charades françaises 🎭
Backend nouveau `charades_data.py` + router `/api/charades/*` :
- 13 charades classiques françaises vérifiées manuellement (Château, Bonjour, Poulet, Vinaigre, Souris, Lapin, Chaton, Marmite, Chapeau, Bonbon, Sapin, Orange, Carotte)
- **Anti-cheat** : `_public_charade()` strip la réponse avant tout retour au client
- Normalisation tolérante : minuscules + accents supprimés + non-alphanumériques retirés (`CHÂTEAU` = `chateau` = ` château `)
- Récompense : **+5 pts par bonne réponse**, idempotent (pas de double comptage), attribué au 1er correct uniquement
- Ligue hebdomadaire créditée en même temps
- Nouveau badge **`amateur_mots`** (or) débloqué au 10ᵉ charade résolue distincte

Frontend `/app/charades` :
- Card avec 3 lignes de charade, input, bouton indice, bouton valider
- Panneau reveal (vert bravo / rouge ce n'est pas ça), badge "Déjà résolue"
- Précédent / Suivant / Passer + progression `X / 13 résolues`
- Toast récompense +5 pts

Navbar & MobileMenu : nouveau lien `Charades` visible pour utilisateurs connectés.

Tests: iteration 33 — 13/13 pytest backend + Frontend 100 % — verts.

### Backlog Jeux de Mots restant
- **Mots Mêlés** (option b — Mistral IA) : cron nocturne génère un thème + 10 mots + placement algorithmique dans une grille MongoDB
- **Mots Croisés** (options e + f) : MVP grille 5×5 fléchée pré-authorée × 10, puis génération IA
- **Autres activités** (Journal de Vie, Recettes d'Antan, Photothèque) : à scoper

### Autre backlog
- Onboarding Tour (P1)
- Coop Atelier (P1)
- EHPAD CRM (P1)
- Refactor `server.py`, unifier attempts/daily/coop en `game_sessions`
- Mobile app Expo


---

## Jeux de Mots — Vague 1 : Charades packs + Mots Mêlés IA (2026-08-08) ✅

### Charades — enrichissement thématique
- Restructuration en 3 packs : `classique` (13), `nature` (4), `cuisine` (2) → **19 charades total** (toutes validées manuellement)
- Nouveaux endpoints : `GET /charades/packs` (avec compteurs), `GET /charades/list?pack=<id>`
- Frontend : onglets pack cliquables (charades-pack-*) qui rechargent la liste, compteur trophée par pack

### Mots Mêlés IA — nouveau jeu complet 🧩
Backend :
- `wordsearch_data.py` — algorithme de placement 8 directions (h/v/diag), grid 12×12, retries jusqu'à succès, remplissage aléatoire des cases libres
- 5 grilles seed thématiques (Cuisine française, Chansons françaises, Cinéma français, La ferme, Les fleurs) insérées au 1er boot
- `wordsearch_mistral.py` — générateur IA : prompt Mistral JSON strict (thème + 10 mots) → placement algo → insert Mongo. Fallback silencieux si Mistral fail
- Cron **APScheduler 03:30 Europe/Paris** ajoute 1 grille par nuit (jusqu'à 40, puis prune des plus anciennes)
- Router `mots_meles.py` : `/grids`, `/grids/{id}`, `POST /grids/{id}/find`
- **Anti-cheat** : les positions des mots ne sont **jamais** envoyées au client, seule la liste des mots + statut trouvé/non-trouvé. Le backend valide la ligne (start→end) contre les mots cibles
- Scoring server-side : **+2 pts / mot trouvé**, **+10 pts bonus** grille complétée, idempotent (double-clic sur le même mot = 0 pt)
- League hebdomadaire créditée en parallèle

Frontend `/app/mots-meles` :
- Liste des grilles avec preview (emoji, difficulté, progression, badge Complète)
- GridPlay : grille interactive 12×12 (144 boutons `mots-meles-cell-r-c`), sélection en 2 clics (1ʳᵉ lettre + dernière lettre), preview de la ligne pendant hover, feedback visuel (surbrillance verte permanente sur mots trouvés + pulse mustard sur nouveau trouvé)
- Liste des mots à droite (case ✓ + strike-through quand trouvé)
- Toasts +2 pts / +10 bonus complétion
- Sur ligne invalide (non droite/diagonale) : toast d'erreur, sélection reset

Landing PlatformSection : carte Mots Mêlés désormais cliquable ("Nouveau" + "Jouer" vert). Navbar + MobileMenu : nouveau lien.

Tests: iteration 34 — 9/9 pytest backend + Frontend 100 % — 1 mini bug UX de compteur (fixé) + doublon BREL seed (fixé).

### Backlog restant
- **Mots Croisés MVP** (prochaine vague) : 10 grilles fléchées 5×5 pré-authorées + interactive grid UI
- **Charades expansion** : générateur Mistral pour passer de 19 à 50+ (bibliothèque évolutive)
- Onboarding Tour, Coop Atelier, EHPAD CRM
- Refactor `server.py` (APScheduler prend de l'ampleur — 6 jobs quotidiens/hebdo maintenant)


---

## Jeux de Mots — Vague 2 : Grid Themes IA + Charades Expansion + Mots Fléchés MVP (2026-08-08) ✅

### Grid Themes IA
- `wordsearch_mistral.py` : liste `THEME_FAMILIES` (10 catégories culturelles françaises) tirée au sort à chaque exécution nocturne (Régions, Années 60, Métiers d'autrefois, Cuisine régionale, Jardin & saisons, Chansons, Cinéma classique, Sport, Écrivains, Vie quotidienne d'antan)
- Prompt Mistral paramétré `{family}/{hint}` — chaque grille générée porte le champ `family` en base pour analytics futurs

### Charades Expansion
- Nouveau module `charades_mistral.py` : job nocturne 04:00 Paris via APScheduler
- Prompt strict avec rotation `PACKS_ROTATION` (classique, cuisine, nature, metiers, animaux, voyages) selon `day_of_year`
- **QA automatique** : chaque candidate testée sur (parts 2-3 items, longueur, doublon avec bibliothèque statique OU précédemment générée, longueur hint 5-220 chars) — les rejets sont loggués
- Stockage `mistral_charades` collection, pruning au-delà de 60
- `/api/charades/list` et `/api/charades/packs` fusionnent dynamiquement bibliothèque statique + Mistral (avec labels fallback pour packs découverts : Métiers, Animaux, Voyages)
- **Endpoint admin** : `POST /api/charades/admin/generate` déclenche manuellement le job (gated `get_admin_user`, retourne report {pack, attempted, accepted, rejected_reasons})
- Test réussi : 5 candidats → 4 acceptés (1 doublon "souris" détecté), pack "animaux" ajouté dynamiquement

### Mots Fléchés MVP
- 5 grilles 5×5 hand-authored dans `mots_fleches_data.py` : Cuisine du dimanche, À la ferme, Fleurs et arbres, Années 60, Voyages en France
- Modèle cellule : `block` (avec `clue_h` et/ou `clue_v`) ou `letter` (avec `answer` — jamais envoyé au client, anti-cheat)
- Router `/api/mots-fleches/*` : list, get (public), submit (validation lettre par lettre + bonus +5 grille complète)
- Idempotent : `xp_total` crédité uniquement du delta `points - best_prior`
- Frontend `MotsFleches.jsx` :
  - Liste des 5 grilles avec meilleur score + badge Complète
  - GridPlay avec grid 5×5 (input par cellule), auto-advance à droite après frappe, Backspace vide + recule, flèches ↑↓←→ naviguent uniquement sur les cellules `letter`
  - Feedback visuel : mistake rouge, cursor mustard, submit + reset
  - Anti-cheat total : le backend n'envoie jamais les réponses

Landing PlatformSection : la carte "Mots Croisés" est désormais Live vers `/app/mots-fleches`. Navbar + MobileMenu : nouveau lien "Mots Fléchés".

Tests: iteration 35 — 13/13 pytest backend + Frontend 100 % — verts.

### Note design signalée
Le testing agent remonte que la navbar desktop devient encombrée sur < 1280px avec l'ajout de nouveaux liens jeu. Un menu déroulant "Jeux" (Charades / Mots Mêlés / Mots Fléchés / Atelier) est recommandé pour la prochaine passe UX.

### Backlog restant
- **Navbar Jeux dropdown** (P2) — décongestionner desktop 1024-1280px
- **Charades expansion** : laisser le cron 04:00 tourner 1-2 semaines pour arriver à 50+ charades
- **Mots Fléchés v2** : passer de 5×5 à 8×10 grille classique + génération Mistral
- **Onboarding Tour** (P1)
- **Coop Atelier** (P1)
- **EHPAD CRM** (P1)
- Refactor `server.py` (APScheduler : 7 jobs quotidiens/hebdomadaires maintenant)


---

## Vague 3 : Navbar Jeux dropdown + Mots Fléchés v2 (2026-08-08) ✅

### Navbar Games Menu
- Nouveau composant `GamesDropdown.jsx` : 1 trigger "Jeux" + menu avec 4 items (Atelier Mémoire / Charades / Mots Mêlés / Mots Fléchés) chacun avec icône + description
- Accessibilité complète : `aria-expanded` togglé, ferme sur clic extérieur, ferme sur Escape
- Navbar desktop : les 4 liens individuels supprimés → 1 seul bouton "Jeux". Décongestionnement à 1024-1280px
- MobileMenu : structure plate conservée (drawer déjà spacieux)

### Mots Fléchés v2
- Modèle étendu : les grilles portent maintenant `rows` × `cols` (non-carré supporté). Backward compat via champ `size` legacy
- `_public_grid` continue à masquer les réponses (anti-cheat)
- `_grid_by_id` : merge des grilles statiques (mf01..mf05) + collection `fleches_generated` (Mistral)
- Nouveau module `fleches_mistral.py` :
  - `THEME_ROTATION` : 10 thèmes culturels français (Cuisine, Cinéma, Chansons, Régions, Ferme, Fleurs, Métiers, Vie d'antan, Sport, Écrivains)
  - Prompt Mistral strict : {theme, emoji, entries: [{word, clue}]} × 6-8 lignes
  - **QA automatique** par entrée : longueur mot 3-8 lettres, sans accent, clue 5-60 chars ne contenant pas le mot
  - Assemblage row-based : chaque ligne = block(clue) + lettres, pad avec blocks pour rectangularité
  - Cron **APScheduler 04:30 Europe/Paris** — 1 grille/nuit, pruning au-delà de 30
- Endpoint admin manuel `POST /api/mots-fleches/admin/generate` (gated admin) — testé live, grille 6×6 "Vie quotidienne d'antan" générée
- Frontend `MotsFleches.jsx` mis à jour : `grid.cols || grid.size` pour le CSS grid, `moveCursor`/`filledCount` gèrent rows/cols indépendamment

Tests: iteration 36 — 6/6 pytest backend + Frontend 100 % — verts. Aucun action_item, aucun design_issue restant.

### Backlog restant
- **Onboarding Tour** (P1)
- **Coop Atelier** (P1) — session famille partagée
- **EHPAD CRM** (P1)
- **Charades bibliothèque** : laisser le cron 04:00 accumuler 4-5 semaines pour dépasser 50
- **Mots Fléchés v3** : grilles avec intersections verticales (vrais mots fléchés) — algorithme de placement plus complexe
- Refactor `server.py` (8 jobs APScheduler)
- Mobile app Expo


---

## Mots Fléchés v3 : Croisements verticaux + look journal (2026-08-08) ✅

### Livrable honnête (scope réaliste)
Génération automatique de vrais mots croisés avec intersections = problème combinatoire dur (backtracking, solver, wordlist filtré). Trop lourd pour MVP. Deux volets délivrés à la place :

**1. Look "journal" — arrow markers**
- Frontend `MotsFleches.jsx` : les cases noires affichent maintenant des flèches ▶ (clue_h → droite) et ▼ (clue_v → bas) en couleur mustard, positionnées en bas-droite de chaque case
- Applied à toutes les grilles existantes (mf01..mf05 + mf06 + grilles Mistral) — visuellement, cela ressemble maintenant à un vrai mots fléchés de journal français

**2. Grille mf06 — Carré magique (preuve de concept avec croisements)**
- 3×3 magic square : MER / EAU / RUE en lignes ET en colonnes = 6 mots français, chaque lettre croise 2 mots
- Champ `words: [{answer, direction, row, col}]` ajouté au modèle (pour validation avancée future)
- Difficulté "difficile" (car les intersections rendent chaque erreur pénalisante)
- 9 lettres × 1 pt + 5 bonus complétion = 14 pts

Tests: iteration 37 — 5/5 pytest backend + Frontend 100 % — verts. Aucun action item.

### Backlog restant (mots fléchés v4 et au-delà)
- **v4 — Solver automatique** : générateur backtracking à partir d'un wordlist français validé + template de grille avec black cells (structurel comme les journaux). Nécessite ~2000 lignes de code (dict lookup, arc consistency, MRV heuristic). Alternative : intégrer bibliothèque tierce (`crossword-composer`, `qxw`) ou puzzle library premium.
- **v4 bis — Mistral avec template contraint** : plutôt qu'un solver, forcer Mistral à remplir un template pré-authoré (positions fixes, mots à trouver qui matchent) — plus rapide mais qualité variable
- Onboarding Tour, Coop Atelier, EHPAD CRM
- Charades bibliothèque expansion (laisser le cron 04:00 accumuler)
- Refactor `server.py` (8 jobs APScheduler)



---

## Navbar Admin Dropdown + compactage responsive (2026-02-10) ✅

### Contexte
User admin ne voyait plus les liens admin car la navbar débordait sur laptop 1440px (10+ items, breakpoint `lg:flex` à 1024px = trop tôt).

### Livrables
1. **AdminDropdown.jsx** — nouveau composant qui regroupe Analytics / Promos / Signalements dans un menu déroulant "Admin" avec icône shield, click-outside + Escape, `data-testid`.
2. **Navbar.jsx compactée** — text-lg → text-base, px-4 → px-3, `whitespace-nowrap` sur tous les items, container élargi à `max-w-[1600px]`, retrait de "Défi famille" (accessible via CTA du hero dashboard).
3. **Breakpoint responsive rehaussé** — desktop nav visible à partir de 1400px (arbitrary Tailwind class `min-[1400px]:flex`), MobileMenu (drawer) prend le relais en-dessous. MobileMenu contient déjà les 3 liens admin.

### Résultats vérifiés (screenshot tool)
- 1920px : desktop nav propre, no overflow ✅
- 1440px : desktop nav complète (Quiz du Jour, Mes quiz, Jeux, Ligues, Niv N, Crédits, Mon compte, Admin ⌄, Quitter, Confort +) ✅
- 1399 → 375px : mobile drawer avec section Admin dédiée ✅
- Admin dropdown → click Analytics → route `/app/admin/analytics` fonctionne ✅

### Fichiers touchés
- Créé : `/app/frontend/src/components/AdminDropdown.jsx`
- Modifiés : `/app/frontend/src/components/Navbar.jsx`, `/app/frontend/src/components/MobileMenu.jsx`

### Backlog restant
- Onboarding Tour (P1)
- Coop Atelier grand-parent / petit-enfant (P1)
- EHPAD CRM (P2)
- Refactor `server.py` scheduler → `scheduler.py` (technique)
- Mobile app Expo (backlog)


---

## Mots Fléchés — Refonte grilles + feedback en direct (2026-02-10) ✅

### Bug identifié (user report)
Les grilles mf01-mf05 étaient des "5×5" (en réalité 4×4 zone jouable) avec des réponses stockées en charabia (`RITS/ABHO/WLYU/MEMR`) qui ne correspondaient pas aux définitions ("Céréale d'Asie" = RIZ 3 lettres, mais 4 cases…). Seule mf06 (MER/EAU/RUE) était valide.

### Livrables
1. **6 grilles 4×4 avec vrais croisements** — carrés magiques 3×3 (matrice symétrique) où chaque ligne ET chaque colonne forme un vrai mot français vérifié :
   - mf01 Petit-déjeuner 🥐 · BOL/OSE/LES (facile)
   - mf02 À la ferme 🐓 · OIE/IRA/EAU (facile)
   - mf03 Nature & vigne 🍇 · ROC/OSE/CEP (moyen)
   - mf04 Petits mots courants 📚 · ILE/LES/EST (moyen)
   - mf05 Objets du quotidien 🔑 · SAC/AIL/CLE (difficile)
   - mf06 Ville & Nature 🎯 · MER/EAU/RUE (difficile, inchangée)
   - Symétrie vérifiée par `assert` au chargement (fail-fast)
2. **Nouvel endpoint `POST /mots-fleches/grids/{id}/check`** — retourne `{correct_cells, total_cells, accuracy_pct, mistakes}` sans écrire en DB, sans XP, sans league update. Idéal pour la validation en direct.
3. **Toggle front "Vérifier au fur et à mesure" (ON par défaut)** — debounce 400 ms sur `letters` : appelle `/check` et repeint les cases fausses en rouge en live. L'erreur d'une case disparaît instantanément dès que le joueur retape (avant même le debounce).
4. **UI refresh** — badge "Grilles 4×4 croisées" + copy "Six grilles thématiques avec vrais croisements (carrés magiques 3×3)".

### Fichiers touchés
- Réécrit : `/app/backend/mots_fleches_data.py`
- Modifié : `/app/backend/routers/mots_fleches.py` (ajout endpoint /check)
- Modifié : `/app/frontend/src/pages/MotsFleches.jsx` (état liveCheck, debounce, toggle UI, copy)

### Vérification
- Backend : curl `/api/mots-fleches/grids/mf01/check` avec BOL/OSE/LES → correct_cells=9, accuracy=100 % ✅
- Frontend (screenshot admin@1440px) : liste 6 grilles, ouverture mf01, saisie X → cellule rouge en direct, correction → rouge disparaît ✅


---

## Mots Fléchés v4 — Mistral avec vrais croisements + Word Complete Celebration (2026-02-10) ✅

### Backend : générateur Mistral repensé
- **Bank de 15 carrés magiques 3×3 pré-vérifiés** dans `fleches_mistral.py` (AIL/ILE/LES, VIN/IRE/NEZ, ARC/RUE/CEP, ANE/NUL/ELU, DES/EAU/SUD, etc.) — chaque triplet est une matrice symétrique où chaque ligne ET chaque colonne forment un vrai mot français commun.
- **Le job nocturne** :
  1. Choisit un triplet aléatoire dans la bank (garantie de crossings valides)
  2. Demande à Mistral 3 clues fraîches pour ce triplet via `PROMPT_RECLUE` (validation stricte : 5-60 chars, pas de contamination)
  3. Fallback sur les clues par défaut du bank si Mistral échoue ou renvoie du JSON invalide
  4. Persiste la grille 4×4 magic-square (difficulté "difficile", champ `words` pour validation avancée)
- **L'ancien mode row-based est supprimé** — plus jamais de grilles sans croisements verticaux.

### Frontend : Word Complete Celebration
- `completedCells` calculé via `useMemo` : pour chaque ligne et chaque colonne, si toutes les cases-lettres sont remplies ET aucune n'est marquée mistake → toutes les cases du mot deviennent vertes.
- Fonctionne en direct via le mode "Vérifier au fur et à mesure" (les mistakes sont mises à jour par le debounce `/check` toutes les 400 ms).
- Résultat : un carré magique 3×3 complètement résolu devient tout vert (9 cases + 6 mots) — récompense visuelle immédiate.

### Vérification
- 15 triples du bank tous confirmés symétriques par assertion ✅
- 3 grilles Mistral générées via `POST /admin/generate` — toutes 4×4 difficulté "difficile" avec clues variées ✅
- Screenshot admin@1440 : mf02 avec OIE tapé en row 1 → 3 cases vertes ✅ · OIE/IRA/EAU complet → 9 cases vertes ✅ · grille Mistral "Petits mots courants" (ART/RUE/TES) affiche clues fraîches ✅

### Fichiers touchés
- Réécrit : `/app/backend/fleches_mistral.py` (bank + reclue Mistral, ancien row-based supprimé)
- Modifié : `/app/frontend/src/pages/MotsFleches.jsx` (`completedCells`, style vert)


---

## Mots Fléchés v5 — Grilles 4×4 pleines + son de victoire (2026-02-10) ✅

### Backend : solver 4×4 + double bank
- **Solver custom** : recherche exhaustive de matrices 4×4 symétriques (magic-squares) parmi ~290 mots français ultra-courants (4 lettres). 89 solutions viables trouvées, dont 15 sélectionnées à la main.
- **`MAGIC_BANK_4`** (15 entrées) ajoutée dans `fleches_mistral.py` — themes CERF/EPEE/REVE/FEES ("Contes de fées"), ETAT/TOUR/AUTO/TROU ("Sur la route"), PORC/OEIL/RIRE/CLES, GROS/ROSE/OSER/SERA…
- **`_pick_puzzle()`** : 60 % du temps 4×4 (grille 5×5 avec 16 cases jouables), 40 % du temps 3×3 (grille 4×4 avec 9 cases jouables).
- `_build_magic_grid` et `_mistral_reclue` généralisés pour supporter n=3 ou n=4 mots.

### Frontend : Son de victoire "ding"
- Toggle "Son 🔔" (ON par défaut) à côté du toggle "Vérifier au fur et à mesure".
- Web Audio API : dès qu'un NOUVEAU mot devient complet (nouvelle entrée dans `completedWords`), un ding doux (880 Hz + harmonique 1320 Hz, decay 0.45 s, gain 0.18) est joué.
- `prevCompletedSigRef` évite de rejouer le son quand `completedWords` re-render sans changement.
- Refactor `completedCells` dérivé de `completedWords` (source de vérité unifiée).

### Vérification (screenshot admin@1440)
- 8 grilles Mistral générées : mix 2×(4×4) + 6×(5×5) ✅
- Ouverture grille 5×5 "Petits mots précis" (SEPT/ETUI/PURE/TIEN) — 16 cases vides + 8 clues Mistral fraîches ✅
- Saisie SEPT → 4 cases vertes + 2 oscillateurs audio (1 ding) ✅
- Saisie complète 16 lettres → 16 cases vertes + 14 oscillateurs (7 dings pour 4 lignes + 4 colonnes, quelques events fusionnés par le batching React) ✅

### Fichiers touchés
- Modifié : `/app/backend/fleches_mistral.py` (MAGIC_BANK_4, `_pick_puzzle`, `_build_magic_grid` généralisé)
- Modifié : `/app/frontend/src/pages/MotsFleches.jsx` (Web Audio ding, `completedWords`, toggle Son, copy)


---

## Mon Livre de Vie — MVP + V1 (2026-02-10) ✅

### Refonte stratégique
Positionnement app enrichi : **« Jouez. Souvenez-vous. Transmettez. »**. L'ancien "Atelier Mémoire" évolue en **"📖 Mon Livre de Vie"** — module central de mémoire intergénérationnelle privé par défaut.

### Backend — `/app/backend/routers/livre.py` (nouveau, ~400 lignes)
- **10 chapitres progressifs** hardcodés : Enfance 🍼 · École 🎒 · Adolescence 🎵 · Rencontres 💑 · Métier 👷 · Famille 👨‍👩‍👧‍👦 · Voyages ✈️ · Passions 🎨 · Épreuves 🌱 · Transmission 💌. 5 prompts par chapitre (50 au total).
- Collection `livre_entries` : `{chapter_id, prompt_id, mode: text|audio|delegated, text, audio_b64, photos, delegated_author_name, visibility}`.
- Endpoints principaux :
  - `GET /livre/chapters` — 10 chapitres + compteur d'entrées
  - `GET /livre/chapters/{id}` — prompts + entrées de ce chapitre
  - `POST /livre/entries` — création d'un souvenir (+10 XP)
  - `GET /livre/entries` — vue Livre regroupée par chapitre
  - `GET /livre/souvenir-du-jour` — prompt aléatoire déterministe par user + date
- Endpoints Famille (P1) : questions envoyées/reçues/répondues, invitations avec 4 permissions (view/comment/contribute/manage).

### Frontend — `/app/frontend/src/pages/MonLivre.jsx` (nouveau, ~700 lignes)
- Hero avec tagline et rappel privacy.
- 2 onglets : "Mon livre" et "Ma famille".
- Jauge de progression douce avec messages chaleureux évolutifs.
- Grille 10 chapitres cliquables.
- Modal chapitre : liste des 5 prompts + previews des entrées existantes (texte / audio player / photos).
- Modal saisie avec 3 modes : ✍️ Texte, 🎙️ Audio (MediaRecorder Web API, 60 s max, base64), 👨‍👩‍👧 Délégué + photos (3 max, base64).
- Onglet Famille : envoi de question, inbox/sent, invitations avec permissions.

### Dashboard enrichi
Nouvelle carte "📖 Souvenir du jour · {chapitre}" avec le prompt du jour et CTA "Raconter →" vers `/app/livre`.

### Navigation
- Menu Jeux : "Atelier Mémoire" → **"Mon Livre de Vie"** pointant vers `/app/livre`.
- Ancien `/app/atelier` conservé pour rétrocompat (entrées existantes visibles).

### Vérifications (screenshot admin@1440)
- Dashboard : carte Souvenir du jour + CTA ✅
- /app/livre : hero + jauge + 10 chapitres ✅
- Modal chapitre : 5 prompts visibles ✅
- Modal saisie Texte : sauvegarde OK, toast "🌱", entry preview ✅
- Onglet Ma famille : formulaire question + invite + listings ✅

### V2 restants (backlog)
- Whisper transcription audio auto
- Génération PDF téléchargeable
- Impression print-on-demand
- Version EHPAD complète

---

## Mon Livre de Vie V2 — 4 fonctionnalités (2026-02-10) ✅

### 1. Whisper transcription automatique
- Nouvel endpoint `POST /livre/transcribe` — utilise `emergentintegrations.llm.openai.OpenAISpeechToText` avec `whisper-1` + `EMERGENT_LLM_KEY`.
- Bouton "✨ Transcrire en texte" dans le mode audio du modal souvenir — remplit automatiquement la légende avec la transcription française.
- Testé end-to-end via curl (silence WAV → transcription renvoyée) ✅.

### 2. PDF téléchargeable
- Nouvel endpoint `GET /livre/export/pdf` — construit un PDF ReportLab avec couverture (titre / nom / date en gros), sommaire chapitres, et pour chaque chapitre les prompts + entrées (texte ou "audio non transcrit") + auteur délégué.
- Bouton "📕 Télécharger mon Livre en PDF" dans le hero de `MonLivre.jsx` — fetch axios en `responseType: blob` puis download programmatique.
- Testé : HTTP 200, 2.9 KB, magic bytes `%PDF-1.4` ✅.

### 3. Quiz Memory Triggers
- Nouvel endpoint `GET /livre/memory-trigger/{category_slug}` — mapping manuel 12 catégories quiz → chapitre du Livre + prompt-hint.
- Composant `<MemoryTrigger>` dans `QuizPlayer.jsx` : après le score final, affiche une carte chaleureuse « Vous avez un souvenir à raconter ? » + prompt-hint + CTA "Aller raconter →" vers `/app/livre`.
- Testé : GET cuisine → `{chapter_id: enfance, prompt_hint: "Une odeur ou un plat…"}` ✅.

### 4. Couvertures illustrées Nano Banana
- Script `generate_livre_covers.py` — 10 aquarelles douces (palette maison : terracotta / navy / mustard / cream / bordeaux) via Gemini 3.1 Flash Image Preview + `EMERGENT_LLM_KEY`.
- Endpoint `GET /livre/covers` — retourne pour chaque chapitre l'URL statique de sa couverture (vide tant que le script n'a pas été exécuté).
- ⚠️ **À exécuter une fois manuellement** : `cd /app/backend && python generate_livre_covers.py` — coûte ~10 requêtes Nano Banana. Non lancé automatiquement pour maîtriser les coûts.

### Fichiers touchés
- Modifié : `/app/backend/routers/livre.py` (transcribe + export/pdf + memory-trigger + covers endpoints)
- Créé : `/app/backend/generate_livre_covers.py`
- Modifié : `/app/frontend/src/pages/MonLivre.jsx` (bouton PDF + bouton Transcrire + textarea transcript)
- Modifié : `/app/frontend/src/pages/QuizPlayer.jsx` (composant MemoryTrigger)
- Dépendance ajoutée : `reportlab==5.0.0`

- Souvenirs déclenchés par les quiz (memory triggers)
- Nano Banana couverture illustrée par chapitre


---

## Livre de Vie V3 — Couvertures + PDF illustré + Onboarding Tour (2026-02-10) ✅

### 1. 10 couvertures Nano Banana générées
- Script `generate_livre_covers.py` exécuté avec succès : **10 aquarelles** de 670 KB à 900 KB stockées dans `/app/backend/static/livre_covers/`.
- Sujets : landau + ourson (enfance), cahier + encrier (école), transistor + cassette (adolescence), main tenant une lettre d'amour (rencontres), outils de métiers (métier), table dressée (famille), valise + carte (voyages), vinyle + peinture + échecs (passions), chêne dans la pierre (épreuves), recette manuscrite + enveloppe (transmission).
- Palette maison respectée : terracotta / navy / mustard / cream / bordeaux.

### 2. PDF illustré (`GET /livre/export/pdf`)
- **Couverture de chapitre pleine page** avant chaque section (12×12 cm centrée) si l'illustration Nano Banana existe.
- **Photos des souvenirs** intégrées : jusqu'à 3 par entrée, ReportLab Table 3 colonnes.
- **Légendes** affichées si présentes.
- Taille finale : ~1.1 MB pour un Livre avec photos (vs 3 KB en V2 texte-only).

### 3. Onboarding Tour
- Nouveau `<OnboardingTour />` dans `/app/frontend/src/components/OnboardingTour.jsx`.
- 4 étapes : Bienvenue · Quiz du Jour · Mon Livre de Vie · Progression douce.
- Framer Motion pour transitions, dots de navigation, "Passer la visite" + CTA principal.
- Se déclenche à la première connexion (`localStorage.generaquiz_onboarding_v1`).
- Rejouable via `?tour=1`.
- Injecté en tête de `Dashboard.jsx`.

### Fichiers touchés
- Créé : `/app/frontend/src/components/OnboardingTour.jsx`
- Modifié : `/app/backend/routers/livre.py` (PDF illustré + URL /api/static), `/app/frontend/src/pages/MonLivre.jsx` (fetch covers + ChapterTile avec image), `/app/frontend/src/pages/Dashboard.jsx` (injection OnboardingTour).
- 10 fichiers créés dans `/app/backend/static/livre_covers/*.png` (~8 MB total).

### Vérifications (screenshots admin@1440)
- Onboarding tour étape 1 "Bienvenue dans GénéraQuiz 👋" à `?tour=1` ✅
- Onboarding tour étape 4 "Votre progression 🌱" avec CTA "Explorer →" ✅
- Grille des chapitres avec aquarelles Nano Banana (ourson+landau, cahier+encrier, transistor+cassette) ✅
- Endpoint `/livre/covers` : 10 URLs `/api/static/livre_covers/*.png` ✅
- Endpoint `/livre/export/pdf` : 1.1 MB PDF-1.4 avec covers + photos ✅


---

## Version EHPAD — Espace animateur B2B (2026-02-10) ✅

### Backend — `/app/backend/routers/ehpad.py` (nouveau, ~230 lignes)
Nouveau rôle `role: "ehpad_animator"` (les admins passent aussi les checks).

Collections :
- `ehpad_residents` : fiches sans e-mail pour respecter la vie privée.
- `ehpad_sessions` : séance collective (kind quiz OU prompt).
- `ehpad_session_responses` : 1 réponse par résident par séance (upsert).

Endpoints principaux : CRUD résidents, sessions, réponses, dashboard stats, `POST /admin/promote` pour passer un compte en animateur.

### Frontend — 3 pages sous `/app/ehpad`
- `EhpadDashboard.jsx` — hero + 3 stats (résidents / séances / souvenirs) + 3 tabs.
- `EhpadNewSession.jsx` — assistant 3 étapes (support quiz|prompt / résidents / notes).
- `EhpadSessionView.jsx` — saisie par résident : score 0-5 pour quiz, textarea auto-save pour souvenir.

Guard `_require_animator` renvoie 403 non-animateurs → le front redirige vers `/app/dashboard`.

### Vérifications
- Backend curl : `POST /ehpad/residents` ✅, `GET /ehpad/dashboard` ✅.
- Frontend screenshots @1440 : dashboard EHPAD propre ✅, Nouvelle séance avec 8 catégories + chip résident ✅.

### Fichiers créés / touchés
- Créé : `/app/backend/routers/ehpad.py`, `/app/frontend/src/pages/EhpadDashboard.jsx`, `/app/frontend/src/pages/EhpadSession.jsx`
- Modifié : `/app/backend/server.py`, `/app/frontend/src/App.js`.

### Backlog EHPAD V2
- Stripe B2B checkout dédié pour créer directement les comptes animateurs
- Multi-animateurs par établissement + rôle directeur avec vue agrégée
- Export PDF des séances (compte-rendu imprimable pour les familles)
- Photos de la séance (groupe, ambiance) dans le compte-rendu
- Facturation à la séance ou forfait mensuel par résident


---

## Nouvelle catégorie : Voyages & régions de France (2026-02-10) ✅

### Contenu
- 🧳 **Voyages & régions de France** — 9ᵉ carte du dashboard
- Sous-titre : *Régions, monuments, paysages, traditions et souvenirs de vacances.*
- Mascotte : **👩‍🦳 Jeanne la Voyageuse** — générée via Nano Banana en background (722 KB, valise vintage + carte + chapeau à ruban tricolore).
- 15 questions seed rédigées à la main (Mont-Saint-Michel, Ville Rose, champs de lavande, choucroute alsacienne, Bourgogne, Corse, Chambord, nougat de Montélimar, Rocamadour…).

### Innovation EHPAD : Discussion prompt
- Nouveau champ optionnel `discussion_prompt` sur une question.
- 7 des 15 questions voyages en sont dotées : « Et vous, où partiez-vous en vacances lorsque vous étiez jeune ? », « Avez-vous des souvenirs d'un été en Provence ? », etc.
- Helper Python `QD()` (Q + Discussion) dans `seed_data.py`.
- Le front QuizPlayer affiche un bandeau visible « 🗣️ Question à raconter en groupe » avec l'accroche italique — idéal en séance EHPAD.

### Force-seed nouvelle catégorie
- `server.py` boucle sur `CATEGORIES` au démarrage : toute catégorie sans question en DB reçoit immédiatement ses seed_questions (idempotent, ne double pas les insertions).
- La régénération Mistral nocturne (03:00 Paris) complétera la catégorie jusqu'à 100 questions.

### Mapping mémoire
- `QUIZ_MEMORY_MAP["voyages-france"] → chapter voyages` — après un quiz voyages, l'utilisateur voit un CTA « Où passiez-vous vos vacances quand vous étiez jeune ? » vers son Livre de Vie.

### Vérifications
- `GET /api/categories` → 9 catégories, voyages-france présente avec mascotte Jeanne la Voyageuse ✅
- `GET /api/categories/voyages-france/questions` → 15 questions dont 7 avec discussion_prompt ✅
- Screenshot dashboard : 9 tuiles catégories visibles ✅
- Mascotte statique servie via `/api/static/mascots/voyages-france.png` (722 KB) ✅

### Fichiers touchés
- Modifié : `/app/backend/seed_data.py` (+ helper QD, +15 questions, +1 catégorie), `/app/backend/generate_mascots.py` (+prompt Jeanne), `/app/backend/server.py` (force-seed loop), `/app/backend/routers/livre.py` (memory-trigger map), `/app/frontend/src/pages/QuizPlayer.jsx` (rendu discussion_prompt).
- Créé : `/app/backend/static/mascots/voyages-france.png` (722 KB via Nano Banana).
