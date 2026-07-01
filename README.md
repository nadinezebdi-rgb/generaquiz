# Quiz d'Antan — Plateforme de quiz intergénérationnel

Plateforme complète de quiz intergénérationnel propulsée par **Mistral AI**, avec leaderboard en temps réel, gestion des familles, cache Redis, et suivi mensuel des performances.

L'objectif est de faire jouer ensemble grands-parents, parents, adolescents et enfants à partir de 8 ans, autour de questions mêlant nostalgie, culture générale, musique, cinéma, cuisine, sport et histoire.

L'architecture repose sur :

- **IA générative** (Mistral Small 4) pour des questions toujours différentes, en français natif ;
- **cache Redis** pour réduire les coûts et la latence ;
- **pré-génération nocturne** pour un stock de quiz prêts à servir ;
- **Supabase** pour la persistance des scores, le leaderboard et le Realtime ;
- **suivi mensuel automatique** pour surveiller tarifs et performances Mistral.

---

## Structure du projet

```text
quiz_antan/
├── main.py                              # FastAPI — point d'entrée
├── .env.example                         # Variables d'env backend
├── .env.local.example                   # Variables d'env frontend
│
├── backend/
│   ├── mistral_client.py                # Client Mistral API (retry, parsing JSON)
│   ├── prompts.py                       # Prompts intergénérationnels + catalogue thèmes
│   ├── cache.py                         # Cache Redis async (TTL 24h, fallback gracieux)
│   ├── router.py                        # Routes quiz : /generate, /themes, /random
│   ├── cron_prefetch.py                 # Pré-génération nocturne à 2h00 (APScheduler)
│   ├── supabase_client.py               # Client Supabase (service role, singleton)
│   ├── leaderboard_service.py           # Calcul score, badges, classements
│   ├── leaderboard_router.py            # Routes leaderboard : submit, family, global
│   ├── family_router.py                 # Routes familles : create, join, by-code
│   └── mistral_monitor.py               # Monitoring mensuel tarifs + latence Mistral
│
├── frontend/
│   ├── lib/
│   │   └── supabase.ts                  # Client Supabase singleton navigateur
│   ├── types/
│   │   ├── quiz.ts                      # Types Question, QuizSession, Theme…
│   │   └── leaderboard.ts               # Types FamilyRank, PlayerRank, Badge…
│   ├── hooks/
│   │   ├── useQuiz.ts                   # Hook quiz : état, score, navigation
│   │   └── useLeaderboard.ts            # Hook leaderboard : Realtime + fallback polling
│   ├── components/
│   │   ├── QuizCard.tsx                 # Carte question + animation réponse
│   │   ├── QuizSession.tsx              # Orchestrateur : sélection → quiz → résultat
│   │   ├── ThemeSelector.tsx            # Grille de thèmes groupés par catégorie
│   │   ├── LeaderboardPanel.tsx         # Classement en direct (onglets + animation)
│   │   ├── BadgeShowcase.tsx            # Affichage des badges obtenus
│   │   └── FamilyInvite.tsx             # Créer / rejoindre une famille via code
│   └── app/
│       ├── quiz/page.tsx                # Page /quiz
│       └── leaderboard/page.tsx         # Page /leaderboard
│
└── supabase/
    ├── migrations/
    │   ├── 001_create_tables.sql        # Tables : families, players, sessions, scores, badges
    │   ├── 002_views.sql                # Vues : classements familles, joueurs, champions
    │   └── 003_rls.sql                  # Row Level Security par famille
    └── seed.sql                         # Données de test (dev uniquement)
```

---

## Installation backend

### 1. Dépendances Python

```bash
pip install fastapi mistralai redis apscheduler uvicorn supabase httpx
```

### 2. Variables d'environnement

Créez un fichier `.env` à partir de `.env.example` :

```bash
cp .env.example .env
```

```env
# Mistral
MISTRAL_API_KEY=your_mistral_api_key_here
MISTRAL_MODEL=mistral-small-latest
MISTRAL_TIMEOUT_SECONDS=30

# Redis
REDIS_URL=redis://localhost:6379/0

# Supabase
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_here

# CORS
ALLOWED_ORIGINS=http://localhost:3000

# Environnement
APP_ENV=development

# Monitoring mensuel Mistral
MONITOR_MONTHLY_QUIZ=10000
MONITOR_CACHE_RATIO=30
MONITOR_TOKENS_PER_QUIZ=800
MONITOR_BENCHMARK_RUNS=3
MONITOR_WEBHOOK_URL=
```

> Ne jamais exposer `MISTRAL_API_KEY` ou `SUPABASE_SERVICE_ROLE_KEY` côté frontend. Toutes les requêtes sensibles passent par le backend.

### 3. Lancement

```bash
uvicorn quiz_antan.main:app --reload --port 8000
```

### 4. Pré-génération manuelle

```bash
python backend/cron_prefetch.py
```

### 5. Monitoring Mistral manuel

```bash
python backend/mistral_monitor.py
```

---

## Installation frontend

### 1. Variables d'environnement Next.js

Créez un fichier `.env.local` dans votre dossier frontend :

```bash
cp .env.local.example frontend/.env.local
```

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=https://xxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_anon_key_here
```

### 2. Dépendances npm

```bash
npm install @supabase/supabase-js
```

### 3. Pages disponibles

| Route | Composant | Description |
|---|---|---|
| `/quiz` | `app/quiz/page.tsx` | Sélection de thème et jeu |
| `/leaderboard` | `app/leaderboard/page.tsx` | Classement global en temps réel |

---

## Routes API

### Quiz

| Méthode | Route | Description |
|---|---|---|
| `GET` | `/api/quiz/themes` | Liste des thèmes avec métadonnées |
| `GET` | `/api/quiz/generate?theme=...&nb=5` | Génère ou sert depuis le cache |
| `GET` | `/api/quiz/random` | Thème aléatoire intergénérationnel |

### Leaderboard

| Méthode | Route | Description |
|---|---|---|
| `POST` | `/api/leaderboard/submit` | Soumet un score de fin de session |
| `GET` | `/api/leaderboard/family/{id}?period=week` | Classement d'une famille |
| `GET` | `/api/leaderboard/global?period=week&limit=10` | Classement global |
| `GET` | `/api/leaderboard/themes` | Champions par thème |
| `GET` | `/api/leaderboard/player/{id}/badges` | Badges d'un joueur |

### Familles

| Méthode | Route | Description |
|---|---|---|
| `POST` | `/api/family/create` | Crée une famille (génère un invite_code) |
| `POST` | `/api/family/join` | Rejoint une famille via code |
| `GET` | `/api/family/{id}` | Info famille + liste joueurs |
| `GET` | `/api/family/by-code/{code}` | Recherche par code d'invitation |

### Système

| Méthode | Route | Description |
|---|---|---|
| `GET` | `/` | Statut API |
| `GET` | `/health` | Statut API + Redis |

---

## Base de données Supabase

### Appliquer les migrations

```bash
# Via Supabase CLI
supabase db push

# Ou dans l'éditeur SQL Supabase, dans l'ordre :
# 1. supabase/migrations/001_create_tables.sql
# 2. supabase/migrations/002_views.sql
# 3. supabase/migrations/003_rls.sql
```

### Charger les données de test (dev uniquement)

```bash
supabase db seed --file supabase/seed.sql
```

### Tables

| Table | Description |
|---|---|
| `families` | Groupes familiaux avec code d'invitation |
| `players` | Joueurs rattachés à une famille |
| `quiz_sessions` | Trace de chaque partie jouée |
| `scores` | Scores pondérés par session |
| `badges` | Trophées attribués automatiquement |

### Vues SQL

| Vue | Description |
|---|---|
| `v_family_leaderboard` | Classement global des familles (RANK sur 30 jours) |
| `v_player_leaderboard` | Classement des joueurs par famille |
| `v_theme_champions` | Meilleur score par thème |

---

## Realtime Supabase

Les scores s'affichent en direct chez toutes les familles connectées via WebSocket Supabase Realtime.

**Activation requise dans le dashboard Supabase :**
Database → Replication → activer **INSERT** sur la table `scores`.

Le hook `useLeaderboard` souscrit automatiquement au channel famille, avec :

- debounce de 300 ms sur les refetch ;
- fallback polling toutes les 15 s si la connexion WebSocket échoue ;
- indicateur "En direct" / "Hors ligne" dans `LeaderboardPanel`.

---

## Calcul du score

```
score = (bonnes_réponses / total) × 100 × multiplicateur_difficulté + bonus_temps
```

| Paramètre | Valeur |
|---|---|
| Difficulté facile | ×1.0 |
| Difficulté moyen | ×1.5 |
| Difficulté difficile | ×2.0 |
| Réponse en < 5 s | +10 pts |
| Réponse en < 10 s | +5 pts |
| Score famille | Somme des scores des membres sur 7 jours glissants |

### Badges automatiques

| Badge | Condition |
|---|---|
| `first_game` | Première partie complétée |
| `perfect_score` | 100 % de bonnes réponses |
| `streak_3` | 3 sessions en 3 jours consécutifs |
| `theme_champion` | Meilleur score sur un thème dans la famille |
| `best_elder` | Meilleur score de la session parmi les joueurs seniors |

---

## Monitoring mensuel Mistral

Le script `backend/mistral_monitor.py` s'exécute automatiquement **le 1er de chaque mois à 03h00**.

Pour l'activer, ajouter dans `cron_prefetch.py`, dans `start_scheduler()` :

```python
from quiz_antan.backend.mistral_monitor import run_monthly_monitor

scheduler.add_job(
    run_monthly_monitor,
    'cron',
    day=1, hour=3, minute=0,
    id='monthly_mistral_monitor',
    replace_existing=True
)
```

À chaque exécution, le script :

1. Benchmark la latence des 3 modèles (Small 4, Large 3, Medium 3.5) avec 3 appels réels ;
2. Vérifie les tarifs depuis l'API Mistral et détecte tout changement ;
3. Calcule le coût mensuel estimé selon votre volume configuré ;
4. Génère un rapport Markdown dans `reports/mistral_report_YYYY-MM.md` ;
5. Envoie une notification Slack/Discord si `MONITOR_WEBHOOK_URL` est défini.

---

## Thèmes disponibles

| Thème | Catégorie | Ère cible | Difficulté cible |
|---|---|---|---|
| Chansons des années 70 | Nostalgie | 1950-1980 | Mixte |
| Films d'animation | Moderne | Mixte | Facile |
| Cuisine française | Intemporel | Intemporel | Mixte |
| Sport français | Intemporel | Mixte | Moyen |
| Jeux des années 80 | Nostalgie | 1950-1980 | Mixte |
| Animaux et nature | Culture | Intemporel | Facile |
| Histoire de France | Intemporel | Intemporel | Moyen |
| TV et pub d'antan | Nostalgie | 1950-1980 | Difficile |
| Musique moderne | Moderne | 2000-2020 | Mixte |
| Géographie France | Intemporel | Intemporel | Facile |

---

## Choix du modèle Mistral

| Modèle | Input | Output | Latence | Recommandation |
|---|---|---|---|---|
| `mistral-small-latest` | $0,15/M | $0,60/M | 0,8–2 s | **Idéal pour la production** |
| `mistral-large-latest` | $0,50/M | $1,50/M | 2–4 s | Si Small manque de finesse culturelle |
| `mistral-medium-latest` | $1,50/M | $7,50/M | 2–5 s | Non justifié pour des quiz |

Changer de modèle sans toucher au code :

```env
MISTRAL_MODEL=mistral-large-latest
```

---

## Coûts estimés (avec cache Redis ×30)

| Volume | Small 4 | Large 3 |
|---|---|---|
| 1 000 quiz/mois | ~$0,02 | ~$0,05 |
| 10 000 quiz/mois | ~$0,19 | ~$0,45 |
| 100 000 quiz/mois | ~$1,93 | ~$4,53 |

> Le cache Redis (pré-génération nocturne, ratio ×30) réduit les appels Mistral réels à environ 3 % du volume total. Les coûts ci-dessus en tiennent compte.

---

## Stratégie de cache

1. **Sans cache** : chaque quiz appelle Mistral directement (latence 1–5 s, coût linéaire).
2. **Cache Redis** : clé `quiz:{theme}:{nb}`, TTL 24h. Réponse en < 20 ms si hit.
3. **Pré-génération nocturne** : `cron_prefetch.py` génère 10 questions par thème à 2h00.
4. **Fallback** : si Redis est indisponible, appel direct Mistral sans interruption de service.
5. **Invalidation** : un changement de prompt incrémente la version de clé (`quiz:v2:...`).

---

## Recommandations de maintenance

- Versionner les prompts (`quiz:v1:...` → `quiz:v2:...`) à chaque changement significatif.
- Consulter les rapports mensuels dans `reports/` pour détecter une hausse de tarifs ou une dégradation de latence.
- Révoquer et renouveler les tokens GitHub et clés API régulièrement.
- Ne jamais commiter `.env` ou `.env.local` — ils sont exclus par `.gitignore`.
- Activer les alertes de dépenses dans le dashboard Mistral Studio.

---

## Référence

[1] Mistral AI — Pricing : https://mistral.ai/pricing/ (juin 2026)
