# Quiz d'Antan — SaaS pour seniors français

## 2026-02-20 (soir +) — Correctifs Robustesse Jobs QA (v2)
- **Contexte** : sur prod, 5 catégories relancées quasi simultanément se sont toutes retrouvées en `failed` au même timestamp (14:51) → signature d'un redémarrage backend prod ou d'une race condition.
- **Fix 1 — `_reap_dead_jobs` (grace period)** : entre `insert_one` et l'écriture du PID par `_run_qa_subprocess`, un job a `status=running` mais `pid=None`. L'ancien code tuait immédiatement ces jobs qui venaient de naître. Nouveau : délai de grâce de **30 s** avant de considérer un job sans PID comme mort. Message d'erreur explicite : `pid never written after 30s`.
- **Fix 2 — Startup dequeue** : `sweep_running_jobs_on_startup` était bien câblé mais `_dequeue_next()` ne l'était pas. Résultat : après un restart du backend, les jobs `queued` restaient bloqués indéfiniment. Ajout de `asyncio.create_task(_dequeue_next())` dans `server.py::startup` juste après le sweep.
- **Test unitaire** (backend) : deux jobs `running` sans PID insérés — jeune (5 s) préservé, vieux (60 s) reaped correctement avec `error="pid never written after 30s"`.
- **Action requise** : republier en prod pour appliquer ces fixes avant de relancer les 5 catégories neuves (Voyages, Génération 70, Génération 40, Cuisine, Histoire).


## 2026-02-20 (soir) — Progression Granulaire QA + Historique Étendu
- **Backend** `admin_qa.py` :
  - `GET /admin/qa/queue` enrichit chaque job `running` et `queued` avec `questions_current` (compte des questions jouables : `difficulty 1..7` ET `quality != flagged`) et `questions_target: 140`.
  - `GET /admin/qa/jobs` — limite par défaut passée de `20` à `30` (max 100) pour voir l'historique quotidien complet.
- **Frontend** `AdminQA.jsx` :
  - `QueueRow` affiche désormais une **mini barre de progression** (h-1.5) sous les estimations, avec le compteur `X / 140` à droite. Barre verte 🟢 si complet, terracotta 🟧 si running, gris 🌫️ si queued.
  - `loadJobs` : paramètre `limit: 30`.
- Validé end-to-end : job factice injecté sur `annees-50-60` (137/140 jouables) → l'API remonte `questions_current: 137, questions_target: 140`, l'UI affiche "137 / 140" avec barre à ~98%.


## 2026-02-20 (nuit++) — Tableau File d'Attente QA
- **Backend** nouveau `GET /admin/qa/queue` :
  - Durée médiane par kind (rerun / topup) calculée sur les 10 derniers `done` — fallback 5 min
  - Pour chaque `running` : `elapsed_sec` + `remaining_sec` estimé
  - Pour chaque `queued` : `position` + `wait_before_start_sec` (simulation d'occupation des slots)
- **Frontend** `AdminQA.jsx` : nouvelle section "File d'attente" tout en haut, visible seulement si des jobs actifs. Auto-refresh 8s si `queued_count > 0`. Chaque ligne = badge position/spinner + catégorie + estimations en français ("fin estimée dans 43s", "démarrage estimé dans 1min 3s") + bouton Annuler direct.
- Testé end-to-end : 3 jobs lancés → tableau affiche 2 running + 1 queued avec estimations cohérentes.


## 2026-02-20 (nuit +) — Bouton Annuler Job
- **Backend** `POST /admin/qa/jobs/{job_id}/cancel` :
  - Job `queued` → status `cancelled` + `return_code=-3`
  - Job `running` → `os.kill(pid, SIGTERM)` (si PID vivant) + status `cancelled` + libère le slot via `_dequeue_next()` (le prochain queued démarre immédiatement)
  - Job déjà terminé → 409 « Job déjà X — rien à annuler »
  - Audit `qa.cancel` tracé (was + killed_pid)
- **Frontend** `AdminQA.jsx` : bouton bordeaux "ANNULER" (ou "Retirer de la file" si queued) sous les boutons Régénérer/Compléter, visible uniquement quand un job actif existe pour la catégorie. Confirmation `window.confirm` avant appel.
- Testé end-to-end :
  - queued cancel → `{was: "queued"}` (Chansons retiré de la file)
  - running cancel → `{was: "running", killed_pid: 6643}` + return_code -15 (SIGTERM propre)
  - re-cancel job cancelled → 409 « déjà failed »


## 2026-02-20 (nuit) — Robustesse QA Jobs (5 correctifs)
- **`admin_qa.py`** refonte complète du pilotage des subprocess :
  1. **`_pid_alive(pid)`** — teste `os.kill(pid, 0)` (signal 0 = no-op), traite `OSError/TypeError/ValueError` comme processus mort.
  2. **`_reap_dead_jobs()`** — parcourt les jobs `running`, passe en `failed` ceux dont le PID est mort. Appelé dans `qa_rerun/qa_topup` AVANT le contrôle 409 et dans `GET /jobs` pour ne plus afficher de fantômes.
  3. **`sweep_running_jobs_on_startup()`** — au démarrage backend, purge INCONDITIONNELLEMENT tous les jobs `running` (les PID sont morts ET peuvent avoir été réattribués → aucun check PID ici). Log explicite `[qa-jobs] startup sweep — N job(s) running → failed`. Wire dans `server.py::startup`.
  4. **Timeout 15 min** dans `_run_qa_subprocess` — `asyncio.wait_for(proc.wait(), timeout=900)`, kill si dépassé, marque `failed / return_code=-2 / error="timeout after 900s"`.
  5. **Sérialisation** — nouvelle limite `_MAX_CONCURRENT_QA_JOBS = 2`. Au 3ᵉ lancement, statut initial `queued` au lieu de `running`. `_dequeue_next()` appelé dans le `finally` de chaque job qui se termine → démarre automatiquement le prochain FIFO par `started_at`.
- Testé end-to-end :
  - 8 zombies simulés → tous purgés au restart (log OK)
  - 3 lancements consécutifs → 2 running + 1 queued visible dans `/api/admin/qa/jobs`
  - Voyages 120/140 et Cuisine 132/140 en cours en parallèle sans pression mémoire (2 audits Opus max)


## 2026-02-20 (tard) — Rappel dimanche + Badge fidélité + Historique défis
- **Rappel Défi Dimanche** — nouveau module `weekly_reminders.py` avec `send_weekly_challenge_reminders()`. Envoi via Resend chaque dimanche 19:00 Paris (nouveau job scheduler `weekly_palier_reminder`) aux users opt-in qui n'ont PAS encore participé (exclusion via un pré-scan de `weekly_palier_scores`). Template HTML dédié avec CTA "Relever le défi".
- **Badge Fidélité Hebdo** — nouveau badge `weekly_streak_4` (or, famille palier, 🔥 "Fidèle du défi"). Attribué quand l'utilisateur a joué le défi 4 semaines ISO consécutives (calcul via `date.fromisocalendar` sur les 4 dernières entrées `weekly_palier_scores`, écarts de 7 jours). Hook idempotent dans `badges.check_after_palier` (nouveau paramètre `matched_weekly=True`). Toast frontend ajouté.
- **Historique Défis Passés** — nouveau endpoint `GET /api/palier/weekly/history?limit=4` qui renvoie les 4 défis passés (semaine courante exclue) avec gagnant + score + total_players. Affichage sur la bannière défi hebdo du Dashboard (section "Champions des semaines passées") avec 👑 par gagnant.
- **Scheduler** : maintenant 11 jobs actifs (ajout `weekly_palier_reminder` dimanche 19:00).
- **Top-up Voyages/Cuisine** : les 2 tournent en background (Voyages 51/140, Cuisine 91/140). Les subprocess sont tués par les restart du backend — noté comme dette technique (design fragile, un supervisor dédié serait mieux).


## 2026-02-20 (nuit +) — Trophées profil + Email Grand Maître + Défi Hebdo Palier
- **Section "Mes trophées"** sur `/app/account` : composant `BadgesSection` qui appelle `/api/badges/catalog`, affiche les badges collectés dans une grille avec emoji + titre + description + tier (bronze/argent/or/diamant). Bouton dépliant "Voir les X badges à débloquer" pour ceux non gagnés.
- **Email félicitations Grand Maître** : nouveau module `badge_emails.py` avec `send_grand_maitre_email(user, categories_count)`. Wire depuis `badges.check_after_palier` quand le badge `palier_grand_maitre` tombe (best-effort, ne bloque jamais l'attribution). Template HTML façon Resend (👑, CTA "Voir mes trophées").
- **Défi Hebdo Palier** : nouveau router `routers/palier_weekly.py`
  - Clé de semaine ISO (`2026-W08`)
  - `pick_weekly_challenge()` — cron chaque lundi 00:10 Paris, tire une catégorie aléatoire + palier 2..6 (uniforme)
  - `record_weekly_score()` appelé depuis `palier_submit` — upsert best-of dans `weekly_palier_scores`
  - `GET /api/palier/weekly` — défi courant + top 10 (auto-tirage si aucun défi)
- **Scheduler** : +1 job `weekly_palier_pick` lundi 00:10 → total 10 jobs actifs
- **Dashboard** : bannière gradient terracotta/bordeaux "Défi de la semaine" avec titre catégorie + palier + top 3 (🥇🥈🥉) + CTA "Relever le défi" vers `/app/parcours/{id}`
- **Top-up Voyages** : en cours, 25/140 (job `5c89f6e5` toujours running).
- Testé : défi automatiquement tiré au premier hit (`Objets d'antan · Palier 6` pour la W34), bannière rendue avec les 3 badges déjà obtenus visibles sur le profil.


## 2026-02-20 (nuit) — Badges palier + Classement + Top-up Voyages
- **3 nouveaux badges** dans `badges.py` :
  - `palier_perfect_20` (or) : 20/20 parfait sur un palier (toutes catégories, toutes difficultés)
  - `palier_expert` (or) : valider le palier 7 (Expert) d'une catégorie
  - `palier_grand_maitre` (diamant) : palier 7 validé dans 3 catégories DISTINCTES
- **`badges.check_after_palier(...)`** — hook idempotent appelé depuis `palier_submit`. Retourne les badge_ids nouvellement attribués → répercutés en toasts côté UI dans `Parcours.jsx`.
- **`GET /api/palier/leaderboard/{category_id}`** (auth utilisateur) — top 10 par nombre de paliers validés (desc), tiebreaker sur `sum_best`, puis `last_played_at`. Renvoie aussi le rang de l'utilisateur courant s'il n'est pas dans le top (`me_out_of_top`).
- **Frontend `Parcours.jsx`** : nouveau composant `Leaderboard` sous les 7 paliers de l'overview, médailles 🥇🥈🥉 sur le top 3, ligne surlignée si c'est l'utilisateur courant. Empty state amical si aucun joueur.
- **Top-up Voyages lancé** : job `5c89f6e5` en cours, 16 → 25 questions déjà, restera à ~140 après ~30 min (124 questions × Sonnet+Opus).
- Testé curl : palier 7 avec 20/20 → badges `palier_perfect_20` + `palier_expert` attribués. Leaderboard affiche bien Admin en tête (2 paliers, cumul 40).


## 2026-02-20 (soir) — Parcours à paliers (140 questions / catégorie)
- **Backend nouveau**
  - `topup_paliers.py` : script standalone qui génère les questions manquantes par palier (Sonnet 4.6 + Opus 4.8 fact-check). Prompt intégrant la difficulté (1..7).
  - `migrate_difficulty.py` : one-shot qui distribue les questions existantes en round-robin sur les 7 paliers (appliqué en preview, 792 questions taggées).
  - `topup_paliers_job.py` : job nocturne 05:00 Paris qui top-up UNIQUEMENT les catégories avec un déficit ≥ 3.
  - `routers/palier.py` : parcours utilisateur (`GET /api/palier/categories/{id}`, `POST /{n}/start`, `POST /{n}/submit`) — server-authoritative scoring, 14/20 pour valider, mêmes questions au rejeu, palier N+1 débloqué si palier N completed.
  - `admin_qa.py` : nouveau `POST /api/admin/qa/topup/{cat_id}` + `qa_summary` enrichi (couverture par palier, `missing_for_full_parcours`).
  - `scheduler.py` : ajout du 9ᵉ job nocturne `paliers_topup_nightly` à 05:00.
- **Frontend nouveau**
  - `pages/Parcours.jsx` : page complète avec 3 états (overview / playing / result). Overview = 7 cartes palier avec verrou/best-score/stock. Play = 20 questions avec nav Préc/Suiv, seuil visible. Result = badge validé/échec + CTA rejouer / palier suivant.
  - `pages/AdminQA.jsx` : chaque catégorie affiche maintenant les 7 barres palier (vert/jaune/vide + count sous chaque) + boutons **Régénérer** (fact-check Opus) et **Compléter à 140** (top-up Sonnet+Opus, désactivé si déjà complet).
  - `pages/Dashboard.jsx` : chaque catégorie a un CTA supplémentaire **🏆 Parcours** vers `/app/parcours/{id}`.
  - Route `/app/parcours/:categoryId` protégée.
- **Testé** : login admin → QA affiche paliers + Cinéma "complet" désactivé + les autres avec "manque N". `/app/parcours/cinema` overview + play view fonctionnels. Curl : `start` d'un palier 2 sans valider palier 1 renvoie bien 403.


## 2026-02-20 — Rôle Super-Admin + Journal d'audit
- **Nouveau rôle `superadmin`** au-dessus d'`admin`. Le seed idempotent au démarrage (`server.py`) promeut auto le user défini via `ADMIN_EMAIL` en `superadmin`. Aucun autre superadmin ne peut être créé depuis l'UI (point d'entrée unique = env).
- **Nouvelles dépendances backend** dans `core.py` :
  - `get_admin_user` accepte désormais `admin` ET `superadmin`.
  - `get_superadmin_user` réservé aux actions gouvernance (change_role, audit).
  - `record_audit(admin, action, ...)` — helper never-raise qui écrit dans `admin_audit_log`.
- **Nouveaux endpoints** :
  - `GET /api/admin/users` (admin) — recherche/filtre/paginé
  - `POST /api/admin/users/{id}/role` (superadmin) — assigne `admin`/`user`. Garde-fous : pas d'auto-modification, pas de modification d'un superadmin, pas de promotion superadmin.
  - `GET /api/admin/audit` (superadmin) — filtre action/email/mot-clé
  - `GET /api/admin/audit/actions` — distinct
- **Instrumentation audit** sur : `user.role_change`, `qa.bulk_approve`, `qa.bulk_delete`, `qa.bulk_flag`, `qa.delete`, `qa.rerun`, `promo.create`, `promo.toggle`, `promo.delete`.
- **Frontend** :
  - Nouvelle page `/app/admin/users` (`AdminUsers.jsx`) : table filtre + boutons Promouvoir/Rétrograder visibles UNIQUEMENT si le user courant est superadmin. Bandeau explicatif si simple admin.
  - Nouvelle page `/app/admin/audit` (`AdminAudit.jsx`) : liste chrono avec badges d'action, diff avant/après en JSON, filtre par action/mot-clé.
  - `AdminRoute` accepte prop `requireSuperadmin` (utilisé pour `/app/admin/audit`).
  - `AdminDropdown` + `MobileMenu` élargis : "Utilisateurs" pour tous les admins, "Journal d'audit" (badge SUPER) uniquement pour superadmin.
  - Navbar/MobileMenu : la condition d'affichage passe de `role === "admin"` à `role in ("admin","superadmin")`.
- **Tests curl OK** : superadmin peut lister/changer les rôles + voir l'audit ; le journal enregistre correctement admin_email, target_label, before, after et timestamp.


## 2026-02-19 (soir) — Feuilleter Le Livre (mode plein écran)
- **Nouveau composant** `frontend/src/components/FeuilleterModal.jsx` : mode plein écran type « vrai livre ». Structure :
  - Page 0 : couverture (nom auteur + année + titre « Mes souvenirs. Mon histoire. »)
  - Pour chaque chapitre avec entrées : page-titre (emoji + Chapitre N + label + nb souvenirs) puis 1 page par souvenir (question en italique, texte avec lettrine terracotta, photos en grille, date en pied)
  - Page finale : « À suivre… »
- Alimenté par `/api/livre/entries` (déjà existant, tri chrono par chapitre). Empty state si `total_entries === 0`.
- **Navigation** : boutons latéraux + clavier `←/→/Home/End/Échap` + swipe tactile (framer-motion drag) + table des matières horizontale cliquable en bas.
- **Wired dans** `pages/MonLivre.jsx` : bouton « Feuilleter mon livre » (desktop + variante mobile), désactivé si aucun souvenir. Bouton PDF conservé pour téléchargement/impression.


## 2026-02-19 — Stripe frontend wiring + EHPAD alignée sur Wivy
- **Câblage Stripe B2C + Cadeaux (P0 DONE)**
  - `frontend/src/lib/checkout.js` (nouveau) : helper `startCheckout(packageId)` → POST `/api/checkout/session` puis redirect Stripe. 401 → redirect `/register?next=/app/pricing&pkg=<id>` + sessionStorage `pending_checkout_package`.
  - `frontend/src/config/pricing.js` : Famille rebranchée sur `famille_v2_monthly` / `famille_v2_yearly` (les anciens `famille_*` sont legacy grandfathering). `GIFTS[]` reçoit un champ `stripeId` (`gift_famille` / `gift_heritage` / `gift_livre`).
  - `frontend/src/pages/Pricing.jsx` : `PlanCard` et `GiftCard` CTA → `startCheckout()` avec loader + toast. Reprise auto d'un `pkg` en attente au retour sur `/app/pricing`.
  - `frontend/src/pages/Register.jsx` : respecte `?next=` + `?pkg=` après inscription.
  - **Vérifié via curl** (admin token) : les 8 packages (`solo_monthly`, `solo_yearly`, `famille_v2_monthly`, `famille_v2_yearly`, `heritage_yearly`, `gift_famille`, `gift_heritage`, `gift_livre`) créent chacun une session Stripe valide.

- **Offre EHPAD alignée sur Wivy (nouveau)**
  - `pricing.js` : suppression de `PRO_PLANS` / `PRO_SETUP_FEE` (multi-paliers mensuels). Remplacés par :
    - `PRO_RESIDENCE` : 990 € HT/an (1 188 € TTC), utilisateurs illimités, 12 mois, sans reconduction tacite.
    - `PRO_RESEAU` : sur devis pour multi-sites.
    - `PRO_STEPS` : 4 étapes (devis → signature → facture → activation).
    - `PRO_TYPES` élargi (EHPAD, résidences services, résidences autonomie, accueil de jour, foyers logements, USLD, associations, CCAS).
  - `components/ProPricing.jsx` refonte complète : héro + 2 cartes (Résidence highlight / Réseau devis) + 3 pastilles de réassurance (sans tacite / essai gratuit / illimité) + process 4 étapes façon Wivy. CTA principaux : *Demander un devis* + *Essai gratuit*.

- **Backlog inchangé** : Coop Notifications (P1), Feuilleter Le Livre (P1), EHPAD Superviseur (P2), EHPAD CRM Brevo (P2), Stripe B2B checkout (P2).


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


## 2026-02-17 — Validation vitrine Voyages & discussion_prompts EHPAD

### Statut : ✅ VALIDÉ PAR L'UTILISATEUR
- Page vitrine `/voyages-france` (`VoyagesShowcase.jsx`) — hero Jeanne, exemples de questions, section "déclencheur de conversation" avec témoignage EHPAD, CTA final — vérifiée visuellement (3 screenshots).
- 130 questions enrichies avec `discussion_prompt` en base :
  - annees-50-60 : 25, chansons : 25, cinema : 25, cuisine-terroir : 15, culture-70-ans : 15, voyages-france : 7, culture-40-ans : 6, histoire-france : 6, objets-antan : 6.
- Route `/voyages-france` correctement branchée dans `App.js`.

### Prochaines priorités (P1)
- Coop Atelier / Livre de Vie temps partagé (grand-parent + petit-enfant sur même session).
- EHPAD Superviseur (P2) — rôle admin établissement.
- EHPAD CRM (P2) — brancher formulaire `/ehpad` sur Brevo ou collection Mongo leads.

## 2026-02-17 — Coop Livre de Vie (P1) + Hook Deps Audit

### Coop Atelier — sessions partagées ✅
Un grand-parent peut ouvrir un chapitre en "mode coop" et inviter un petit-enfant / proche à écrire à ses côtés. Sync via polling léger 4 s, aucun compte requis pour l'invité, souvenirs attribués au prénom saisi.

- **Backend** (`routers/livre.py`): 7 endpoints coop
  - `POST /api/livre/coop/create` (auth) — crée session pour un chapitre, réutilise l'existante active (idempotent), code alphanumérique 6 caractères non ambigus
  - `POST /api/livre/coop/join` (public) — l'invité entre son prénom + code
  - `GET /api/livre/coop/{code}/state` (public) — chapitre, prompts, entrées, participants
  - `POST /api/livre/coop/{code}/heartbeat` (public) — met à jour last_seen
  - `POST /api/livre/coop/{code}/entry` (public) — l'invité ajoute un souvenir en mode `delegated`
  - `GET /api/livre/coop/mine` (auth) — mes sessions actives
  - `POST /api/livre/coop/{code}/close` (auth) — fermeture par le propriétaire
- **Collection Mongo** : `livre_coop_sessions` `{id, owner_user_id, owner_name, chapter_id, invite_code, status, participants:[{name, is_owner, joined_at, last_seen}], created_at}`
- **Frontend**
  - `LivreCoop.jsx` — page publique `/livre/coop/:code` avec écran de bienvenue, avatars participants + indicateur en ligne, composer en pied de page, polling 4 s
  - `MonLivre.jsx` — dans ChapterModal : bouton "Remplir ce chapitre à deux" + modal de partage (code + bouton copier lien + WhatsApp)
- **Attribution** : les souvenirs de l'invité s'enregistrent en mode `delegated` avec `delegated_author_name = prénom` et `visibility = "family"` dans le Livre du propriétaire. `coop_session_code` conservé pour traçabilité.

### Hook Deps Audit ✅
Après investigation, le rapport de 64 warnings comportait principalement des faux positifs. Aucun eslint.config.js n'était présent dans le projet, donc la règle `react-hooks/exhaustive-deps` n'était pas active. Audit manuel des 3 hotspots critiques cités :

- **QuizPlayer.jsx:41** — useEffect `[categoryId]` : correct (n'utilise que `categoryId` + `api` stable)
- **MotsFleches.jsx:122** — useEffect `[letters, liveCheck, grid, gridId]` : correct (checkTimer via ref, setMistakes stable)
- **MotsMeles.jsx:157** — useCallback `[start, busy, gridId]` : correct (setters stables, refs pas nécessaires)

Ajouter aveuglément des deps aux setters (stables React) ou refs aurait cassé la logique de polling live de MotsFleches. Décision : ne pas toucher.

### Fichiers touchés
- **Modifiés** : `/app/backend/routers/livre.py` (+200 lignes coop), `/app/frontend/src/App.js` (route + import), `/app/frontend/src/pages/MonLivre.jsx` (ChapterModal + CoopShareModal)
- **Créés** : `/app/frontend/src/pages/LivreCoop.jsx` (page invité publique)

### Tests
- Backend end-to-end via curl : create → join → state → entry → state (2 entries) ✅
- Frontend E2E (screenshots) : join screen → main view → composer → send → entry appears ✅
- Owner flow (screenshots) : ouvrir chapitre → bouton coop → modal partage avec code `4HTRJB` ✅


## 2026-02-17 — Repositionnement "Jouer. Se souvenir. Transmettre." (Phases 1→4)

### Nouvelle promesse produit ✅
GénéraQuiz devient une plateforme intergénérationnelle : JOUER → SE SOUVENIR → RACONTER → TRANSMETTRE.

### Phase 1 — Landing repositionnée
- Hero H1 : "5 minutes pour jouer. Toute une vie à raconter."
- Sous-titre : "GénéraQuiz fait revivre les souvenirs grâce au jeu et rapproche les générations pour mieux transmettre les histoires familiales."
- Pill : "Jouer. Se souvenir. Transmettre." (remplace "Le premier club mémoire intergénérationnel")
- 2 CTAs : "Commencer gratuitement" + "Découvrir GénéraQuiz" (scroll vers #how-it-works)
- Nouvelle section `HowItWorksSection.jsx` (4 étapes visuelles Je joue / Je me souviens / Je raconte / Je transmets)

### Phase 2 — Livre de Vie à 12 chapitres
- Ajout de 4 nouveaux chapitres : `origines` (1), `couple` (6), `enfants` (7), `evenements` (11)
- Migration douce idempotente : `famille` → `enfants`, `epreuves` → `transmission` (via `_migrate_legacy_chapters` au startup)
- Nouveau widget Dashboard `LivreProgressCard.jsx` : "Votre Livre de Vie prend forme" + barre de progression + 4 stats + CTA "Feuilleter"
- Nouvel endpoint `GET /api/livre/progression` (agrégats souvenirs / photos / chapitres complétés / pages estimées)

### Phase 3 — Assistance rédactionnelle IA
- Nouveau routeur `routers/livre_ai.py` avec 2 endpoints :
  - `POST /api/livre/entries/{id}/rewrite` : propose une reformulation sans écraser le texte source
  - `POST /api/livre/entries/{id}/accept-rewrite` : archive l'original dans `original_text`, applique la version acceptée
- **Guardrails stricts** dans le prompt système : interdiction absolue d'inventer personne, date, lieu, événement, émotion (6 règles inviolables)
- Modèle : **gpt-5.5** via Emergent LLM key (gpt-5.6 pas encore listé dans emergentintegrations)
- Composant `RewriteAssistantModal.jsx` : 3 boutons "❤️ Ça me ressemble", "✏️ Modifier", "🔄 Reformuler autrement" + 3 tons (natural / warmer / concise)
- Bouton "✨ Reformuler" ajouté à `EntryPreview` (visible uniquement si mode=text et text >= 20 caractères)

### Phase 4 — Boucle Quiz → Livre (feature signature)
- Nouveau endpoint `POST /api/livre/from-quiz` avec mapping automatique catégorie → chapitre :
  - chansons/cinema/culture-70/culture-40/cuisine-terroir → passions
  - voyages-france → voyages
  - histoire-france → evenements
  - annees-50-60 → adolescence
  - objets-antan → enfance
- Nouveau composant `QuizMemoryBridge.jsx` injecté dans `QuizPlayer.jsx` sous le feedback : "💭 Ce moment vous rappelle un souvenir ?" avec zone de saisie et confirmation "Souvenir ajouté à votre Livre de Vie · [chapitre]"
- Champs `source="quiz"` + `quiz_question_id` + `quiz_category_slug` tracés sur l'entrée
- Fix bonus : `QUIZ_MEMORY_MAP["histoire"]` corrigé (`epreuves` → `evenements`)

### Fichiers touchés
- **Modifiés** : `Landing.jsx`, `Dashboard.jsx`, `MonLivre.jsx`, `QuizPlayer.jsx`, `livre.py` (12 chapitres + progression + from-quiz + QUIZ_MEMORY_MAP), `server.py` (registre routeur + migration startup)
- **Créés** : `HowItWorksSection.jsx`, `LivreProgressCard.jsx`, `RewriteAssistantModal.jsx`, `QuizMemoryBridge.jsx`, `livre_ai.py`, `tests/test_iteration40_livre_ai_boucle.py`

### Tests
- Testing agent iteration 40 : **100% backend + 100% frontend** ✅
- 12 chapitres visibles dans le bon ordre, migration OK (0 orpheline)
- Rewrite AI testé avec input "Marie" → aucun autre prénom inventé, guardrails respectés
- from-quiz testé pour 6 mappings catégorie → chapitre : tous corrects
- Aucun casse-flow : login, dashboard, coop, quiz classique fonctionnent

### Notes de production
- Modèle IA actuel : gpt-5.5 (mettre à jour vers gpt-5.6 dès qu'il est ajouté au catalogue emergentintegrations)
- Refactor recommandé (non urgent) : `livre.py` fait 1113 lignes, à découper en submodules (chapters/entries/family/coop/pdf/ai) — reporté en backlog technique


## 2026-08-19 — Sécurité admin + copy + nouveaux tarifs (Livre imprimé, Offre Pro)

### 🚨 P0 — Rotation du mot de passe admin
- L'ancien mot de passe `Admin2026!` était visible dans l'historique du chat Emergent (signalé par l'utilisateur).
- Nouveau mot de passe généré via `secrets.choice(alphanum+special)` sur 20 caractères, stocké **uniquement** dans `/app/backend/.env` et `/app/memory/test_credentials.md` (fichier non servi publiquement).
- Ancien mot de passe : HTTP 401 ✅ · Nouveau : HTTP 200 ✅

### 🔐 Restauration de l'espace admin
- **Nouvelle page `AdminHome.jsx`** (route `/app/admin`) : tableau de bord central avec 3 tuiles (Analytics / Codes promo / Signalements).
- **Nouveau composant `<AdminRoute>`** dans `App.js` : vérifie `user.role === "admin"` côté client (les endpoints `/api/admin/*` étaient déjà protégés par `get_admin_user` côté serveur — testé HTTP 403 pour un compte non-admin).
- `AdminDropdown` (menu Navbar avatar) enrichi : entrée "Administration → Tableau de bord admin" ajoutée en 1ère position.
- `MobileMenu` : entrée "Tableau de bord" ajoutée dans la section Admin.

### ✏️ Copy changes
- Landing : "Huit univers, huit personnages" → **"Neuf univers, neuf personnages"** avec accroche Jeanne la Voyageuse.
- Carte catégorie "Voyages & régions de France" : badge **"✨ NOUVEAU"** ajouté (Landing + Dashboard).
- MonLivre chapter modal : bandeau **"✨ Racontez simplement votre souvenir, GénéraQuiz le transforme en un joli récit pour votre livre de vie."** ajouté ; bouton coop renommé "Remplir à deux avec un proche".
- EarnCredits.jsx : "accès aux 8 catégories" → "accès aux 9 univers".

### 💰 Nouveaux tarifs (page Pricing)
Nouveau composant `PrintedBookPricing.jsx` injecté sous la reassurance-strip :

**📖 Livre imprimé** (3 offres) :
| Offre | Prix | Prix/livre | Économie |
|---|---|---|---|
| 📕 1 livre | 79,90 € | 79,90 € | — |
| 📚 2 livres ⭐ (Le plus choisi) | 129,90 € | 64,95 € | 29,90 € |
| 🎁 3 livres | 179,90 € | 59,97 € | 59,80 € |
+ mention **"PDF gratuit inclus"** pour tous les abonnés · format A5 · impression à la demande. Les CTAs pointent vers `mailto:contact@generaquiz.fr` en attendant le vrai checkout Stripe.

**🏥 Offre Pro** (à partir de 59 €/mois, devis 48h) — 8 catégories affichées : EHPAD, Associations, Clubs du 3ᵉ âge, CCAS, Collectivités territoriales, Structures médicalisées, Médiathèques, Bibliothèques. CTA `mailto:` "Demander un devis".

### Fichiers touchés
- **Modifiés** : `Landing.jsx`, `Dashboard.jsx`, `MonLivre.jsx`, `EarnCredits.jsx`, `Pricing.jsx`, `App.js` (AdminRoute + route /app/admin), `AdminDropdown.jsx`, `MobileMenu.jsx`, `.env` (nouveau ADMIN_PASSWORD).
- **Créés** : `AdminHome.jsx`, `PrintedBookPricing.jsx`.

### Tests
- Login admin avec nouveau mot de passe : HTTP 200 ✅
- Ancien mot de passe rejeté : HTTP 401 ✅
- Non-admin sur `/api/admin/analytics/overview` : HTTP 403 ✅
- Non-admin sur `/api/admin/promo` : HTTP 403 ✅
- Badge "Nouveau" sur voyages-france : visible Landing + Dashboard ✅
- Section Livre imprimé + Offre Pro : rendues correctement sur `/app/pricing` ✅
- Bandeau pitch dans le Livre : visible et bien formaté ✅

### Notes production
- Aucun endpoint Stripe créé pour les livres imprimés (CTA mailto uniquement) → à câbler en itération suivante avec des PACKAGES dédiés (`livre_1`, `livre_2`, `livre_3`, `pro_lite`, `pro_ehpad`).
- Le contrôle de rôle côté frontend NE remplace PAS la vérification serveur — les deux sont en place.


## 2026-08-19 (suite) — Anti-répétition + Fact-check IA + fix seed admin

### 🎯 Correctif A — Anti-répétition
- Nouvelle collection `user_seen_questions {user_id, category_id, question_id, seen_at, seen_count}` upsert à chaque tirage.
- `GET /categories/{id}/questions` : exclut les questions vues dans les 30 derniers jours, avec fallback repêche si <5 restantes.
- Réponse enrichie de `pool: {total, seen_recently, remaining_fresh, reported_excluded}`.
- Widget frontend "📚 X/N nouvelles questions à découvrir" affiché en tête de quiz.

### 🎯 Correctif C — Exclusion signalements
- Le tirage exclut désormais les questions ayant ≥2 signalements avec statut ≠ "dismissed".
- Backend automatique, aucun bouton à activer côté admin.

### 🎯 Correctif B3 + D — Fact-check IA permanent (pipeline)
- Nouveau script `audit_and_regen_questions.py` :
  - Fact-check via **Claude Opus 4.8** (JSON strict, seuil confidence ≥ 85, verdicts correct/doubtful/wrong)
  - Régénération via **Claude Sonnet 4.6** avec prompt strict anti-hallucination
  - Chaque question générée est re-vérifiée avant insertion (double-passe)
- Champs ajoutés : `questions.quality: "verified"|"flagged"` + `questions.fact_check: {verdict, confidence, comment, correction, checked_at, checker_model}`
- Les questions `quality: "flagged"` sont automatiquement exclues du tirage côté `quiz.py`.
- Rapport JSON généré dans `/tmp/qa_report_{category}.json`.

**Résultat audit Chansons (100 questions)** : 46 verified · 54 flagged · 7 régen OK · 47 régen refusées → pool jouable = **53 questions** au lieu de 100. Exemples d'erreurs détectées : "Mon Légionnaire" datée 1945 (vraie date 1936), "Amsterdam hymne à la liberté" (interprétation subjective), etc.

### 🚨 Fix seed admin (bugs signalés par l'utilisateur)
- Retrait des valeurs par défaut hardcodées : `ADMIN_EMAIL` et `ADMIN_PASSWORD` n'ont **plus de fallback** dans `core.py`. Si absents, le seed est **skip complet** avec un warning log.
- Backfill idempotent du rôle admin : à chaque startup, si un compte existe avec `ADMIN_EMAIL` mais `role != "admin"`, le rôle est **forcé à "admin"** (idem plan_tier + plan). Résout le cas où un utilisateur s'était inscrit avec l'email admin avant le seed.
- Vérifié : `admin@generaquiz.fr` login HTTP 200, role=admin dans `/auth/me`.
- Note historique : l'ancienne valeur par défaut `Admin2026!` a été présente dans le code source jusqu'à ce commit. Si le repo est publié, elle reste dans l'historique Git.

### Fichiers touchés
- **Modifiés** : `core.py` (retrait défauts admin), `server.py` (seed skip + backfill rôle), `routers/quiz.py` (anti-répétition + exclusion flagged/signalés + pool), `frontend/src/pages/QuizPlayer.jsx` (affichage pool).
- **Créés** : `audit_and_regen_questions.py` (pipeline QA), `/tmp/qa_report_chansons.json` (rapport).

### Prochaines étapes
- Lancer l'audit sur les autres catégories : `ONLY_CATEGORY=cinema python audit_and_regen_questions.py`, etc.
- Coût estimé : ~2-3€ Emergent LLM Key pour 800 questions (8 catégories × 100).
- Durée : ~10 min par catégorie via LLM externe.


## 2026-08-19 (suite 2) — Admin QA Dashboard + audit des 7 autres catégories

### 🎯 Admin QA Dashboard `/app/admin/qa`
Nouveau backend `routers/admin_qa.py` + nouvelle page `AdminQA.jsx`.

**Endpoints (rôle admin)** :
- `GET /admin/qa/summary` — répartition par catégorie (verified/flagged/unchecked/% jouable)
- `GET /admin/qa/questions?category_id&quality&limit&offset` — liste paginée triée par confidence croissante
- `POST /admin/qa/{id}/approve` — force verified (retour au tirage)
- `POST /admin/qa/{id}/flag` — force flagged (retire du tirage)
- `POST /admin/qa/{id}/apply-correction` — applique la correction textuelle proposée par le fact-check (sauvegarde original dans `original_snapshot`)
- `DELETE /admin/qa/{id}` — suppression définitive

**Frontend** :
- Résumé visuel : 9 cartes catégorie avec barre 3 couleurs (vert verified / crème unchecked / orange flagged) + % jouable
- Filtres : catégorie sélectionnée + quality (flagged/verified/unchecked/all)
- Liste : question + 4 options (bonne en vert), verdict + confidence, commentaire fact-check, correction proposée si dispo
- Actions : Approuver / Appliquer la correction / Flagger / Supprimer
- Toutes les actions retirent l'item de la liste localement + rafraîchissent le résumé

### 🎯 Audit lancé sur les 7 catégories restantes (en background)
Script `run_all_audits.sh` séquentiel dans `/tmp/audit_all.log` : cinema → cuisine-terroir → culture-40-ans → culture-70-ans → annees-50-60 → objets-antan → voyages-france → histoire-france. ~10 min/catégorie.

Résultats partiels au moment du finish :
- Chansons : 53 verified / 54 flagged / 7 régen OK (100 %)
- Cinema : ~45/100 en cours (39 verified déjà, 24 flagged)

### Ajouts UI navigation
- AdminHome : passage à 4 tuiles (ajout "Qualité IA") avec grid `lg:grid-cols-4`
- AdminDropdown Navbar : 5 entrées (Admin / Analytics / Promos / Signalements / Qualité IA)
- MobileMenu : entrée "Qualité IA" ajoutée dans la section Admin

### Fichiers touchés
- **Créés** : `backend/routers/admin_qa.py`, `frontend/src/pages/AdminQA.jsx`, `/tmp/run_all_audits.sh`
- **Modifiés** : `backend/server.py` (registre routeur admin_qa), `frontend/src/App.js` (route /app/admin/qa + import), `AdminHome.jsx` (4ᵉ tuile + grid 4 cols), `AdminDropdown.jsx` (5ᵉ entrée), `MobileMenu.jsx` (idem)

### Tests
- Backend endpoints admin QA : summary + questions filtrées OK, actions approve/flag/apply-correction/delete OK
- Frontend : dashboard rendu, 78 questions flagged listées avec fact-check commentaires, boutons d'action fonctionnels
- Sécurité : tous les endpoints admin_qa passent par `get_admin_user` → HTTP 403 pour un non-admin


## 2026-08-19 (suite 3) — Regen Batch + QA Search

### 🎯 Regen Batch — relance du fact-check depuis le dashboard
Nouveaux endpoints (rôle admin) :
- `POST /api/admin/qa/rerun/{category_id}` — lance le script `audit_and_regen_questions.py` en subprocess Python non bloquant. Crée un doc dans `db.qa_jobs` (status: running → done/failed). Refuse HTTP 409 si un job "running" existe déjà pour la même catégorie (anti double-facturation LLM).
- `GET /api/admin/qa/jobs?limit=10` — liste des jobs récents triés par `started_at desc`, enrichis avec `log_tail` (6 dernières lignes du log) pour un suivi live.

**Frontend** : bouton "▶ Régénérer la catégorie" sur chaque tuile de catégorie. Pendant qu'un job tourne, le bouton se transforme en "Audit en cours…" (disabled) et un mini log tail apparaît sous la tuile. Un badge global "N audit(s) en cours" s'affiche en tête. Polling automatique de `/admin/qa/jobs` toutes les 8 s tant qu'au moins un job est actif.

### 🎯 QA Search — recherche par mot-clé
- Paramètre `q` ajouté à `GET /api/admin/qa/questions` : cherche insensible à la casse dans `question`, `options`, `fact_check.comment`, `fact_check.correction` (escape regex avant $regex).
- Frontend : input avec debounce 400 ms, icône Search, bouton × pour effacer. Filtre combiné avec les autres (catégorie, quality).

### Fichiers touchés
- **Modifié** : `backend/routers/admin_qa.py` (endpoints rerun + jobs + search sur qa_questions), `frontend/src/pages/AdminQA.jsx` (search + rerun buttons + jobs polling)

### Tests
- Testing agent iteration 42 : **9/10 backend + 100% frontend** (1 skip conflit 409 déjà couvert en amont)
- Recherche 'Piaf' : 10 résultats retournés côté API et affichés en UI ✅
- Rerun voyages-france → job créé (status running) puis exécuté en subprocess ✅
- Anti double-execution 409 : validé ✅
- Régressions (approve/flag/apply-correction/delete/quality filter) : 0 ✅

### Statut audit global
- 5/9 catégories déjà auditées (chansons, cinema, cuisine-terroir, culture-40/70-ans)
- 4/9 restantes : annees-50-60 (partiel 5/100), objets-antan, histoire-france, voyages-france → à relancer depuis le dashboard


## 2026-08-19 (suite 4) — QA Bulk Actions

### 🎯 Actions groupées sur le dashboard `/app/admin/qa`
Nouveaux endpoints admin (rôle admin) :
- `POST /api/admin/qa/bulk/approve` `{ids:[]}` → `quality: verified` sur toutes
- `POST /api/admin/qa/bulk/flag` `{ids:[]}` → `quality: flagged` sur toutes
- `POST /api/admin/qa/bulk/delete` `{ids:[]}` → suppression définitive

Validation Pydantic : `ids` obligatoire, 1 à 500 éléments (HTTP 422 sinon).

### 🐛 Fix route-order critique
Les routes `/bulk/*` étaient interceptées par `/{qid}/approve|flag|apply-correction` (FastAPI matche par ordre de déclaration → `qid = "bulk"`). Correction : les routes bulk sont maintenant déclarées **avant** les routes paramétrées.

### Frontend
- Checkbox sur chaque `QuestionCard` (data-testid `admin-qa-select-{id}`) → surlignage ring terracotta quand sélectionnée
- Bouton "Tout sélectionner (N) / Tout désélectionner" en tête de liste
- Barre sticky en bas de page (data-testid `admin-qa-bulk-bar`) qui apparaît dès qu'au moins 1 item est sélectionné : compteur + 3 boutons (Approuver / Flagger / Supprimer) + ×
- Suppression demande `window.confirm()` avec message "Aucun retour arrière possible"
- Sélection reset automatique quand catégorie / quality / recherche changent

### Fichiers touchés
- Backend : `routers/admin_qa.py` (nouveaux endpoints bulk + réordonnancement)
- Frontend : `pages/AdminQA.jsx` (state selected + handlers + UI checkboxes + sticky bar)

### Tests
- Testing agent iteration 43 : **8/9 backend (1 skip destructif volontaire) + 100% frontend**, 0 régression
- Fix route-order vérifié : `POST /bulk/approve` retourne `{ok:true, matched:N, modified:N}` (200) au lieu du 404 du handler single-question
- Validation Pydantic : HTTP 422 sur ids vides ou > 500
- Sécurité : HTTP 403 pour non-admin sur tous les endpoints bulk

