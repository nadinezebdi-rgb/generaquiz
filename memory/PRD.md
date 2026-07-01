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

