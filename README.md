# Quiz d’Antan — Intégration Mistral pour quiz intergénérationnels

Ce dossier fournit le nécessaire pour intégrer une génération de quiz via l’API Mistral dans **Quiz d’Antan**, avec une logique pensée pour des questions intergénérationnelles : souvenirs d’enfance, culture générale, musique, objets du quotidien, histoire récente, vie locale, technologies, sport, cinéma, expressions, cuisine, métiers et transmission entre générations.

L’objectif recommandé est de combiner :

- **IA générative** pour renouveler les questions et éviter les répétitions ;
- **cache Redis** pour réduire les coûts et la latence ;
- **pré-génération nocturne** pour disposer d’un stock de quiz prêts à servir ;
- **fallback applicatif** pour garder le service disponible si Redis ou Mistral est momentanément indisponible.

## Structure du projet

```text
quiz_antan/
├── backend/
│   ├── mistral_client.py   # Client Mistral API
│   ├── prompts.py          # Prompts intergénérationnels
│   ├── cache.py            # Cache Redis
│   ├── router.py           # Routes FastAPI
│   └── cron_prefetch.py    # Pré-génération nocturne
└── frontend/
    ├── types/quiz.ts
    ├── hooks/useQuiz.ts
    ├── components/QuizCard.tsx
    ├── components/QuizSession.tsx
    └── components/ThemeSelector.tsx
```

## Installation backend

### 1. Dépendances Python

Depuis le dossier qui contient votre application FastAPI :

```bash
pip install fastapi mistralai redis apscheduler uvicorn
```

### 2. Variables d’environnement requises

Créez un fichier `.env` côté backend à partir de `quiz_antan/.env.example` :

```bash
cp quiz_antan/.env.example .env
```

Variables attendues :

```env
MISTRAL_API_KEY=your_mistral_api_key_here
MISTRAL_MODEL=mistral-small-latest
MISTRAL_TIMEOUT_SECONDS=30
REDIS_URL=redis://localhost:6379/0
```

Description :

| Variable | Rôle | Exemple |
|---|---|---|
| `MISTRAL_API_KEY` | Clé API Mistral utilisée par le backend. | `your_mistral_api_key_here` |
| `MISTRAL_MODEL` | Modèle appelé pour générer les quiz. | `mistral-small-latest` |
| `MISTRAL_TIMEOUT_SECONDS` | Délai maximum d’attente d’une réponse Mistral. | `30` |
| `REDIS_URL` | URL de connexion Redis pour le cache. | `redis://localhost:6379/0` |

> Recommandation : ne jamais exposer `MISTRAL_API_KEY` côté frontend. Toutes les requêtes Mistral doivent passer par le backend.

### 3. Commande de lancement

```bash
uvicorn main:app --reload
```

### 4. Commande cron manuel

Pour déclencher manuellement la pré-génération des quiz :

```bash
python quiz_antan/backend/cron_prefetch.py
```

Dans une architecture réelle, `cron_prefetch.py` peut être appelé par :

- `cron` Linux ;
- un job Docker planifié ;
- APScheduler dans FastAPI ;
- un worker séparé.

## Installation frontend

### 1. Configuration Next.js

Créez un fichier `.env.local` dans votre frontend Next.js à partir de `quiz_antan/.env.local.example` :

```bash
cp quiz_antan/.env.local.example frontend/.env.local
```

Contenu attendu :

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Cette variable permet aux composants React d’appeler le backend FastAPI.

### 2. Import du composant `QuizSession` dans une page Next.js

Exemple complet de page `app/quiz/page.tsx` :

```tsx
import QuizSession from '@/components/QuizSession';

export const metadata = {
  title: 'Quiz d’Antan — Quiz intergénérationnel',
  description: 'Jouez à des quiz variés pour toutes les générations.',
};

export default function QuizPage() {
  return (
    <main className="min-h-screen bg-amber-50 px-4 py-8">
      <section className="mx-auto max-w-4xl">
        <header className="mb-8 text-center">
          <p className="text-sm font-semibold uppercase tracking-wide text-amber-700">
            Quiz d’Antan
          </p>
          <h1 className="mt-2 text-3xl font-bold text-stone-900 md:text-5xl">
            Des questions pour toutes les générations
          </h1>
          <p className="mt-4 text-stone-700">
            Choisissez un thème, lancez une session et partagez vos souvenirs,
            anecdotes et connaissances en famille ou entre amis.
          </p>
        </header>

        <QuizSession />
      </section>
    </main>
  );
}
```

## Montage dans FastAPI `main.py`

Exemple complet de `main.py` incluant le router quiz :

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from quiz_antan.backend.router import router as quiz_router

app = FastAPI(
    title="Quiz d’Antan API",
    description="API de génération de quiz intergénérationnels avec Mistral.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(quiz_router, prefix="/api/quiz", tags=["quiz"])


@app.get("/health")
def health_check():
    return {"status": "ok"}
```

Endpoints recommandés dans `quiz_antan.backend.router` :

| Méthode | Route | Rôle |
|---|---|---|
| `GET` | `/api/quiz/themes` | Retourne la liste des thèmes disponibles. |
| `POST` | `/api/quiz/generate` | Génère ou récupère un quiz depuis le cache. |
| `POST` | `/api/quiz/prefetch` | Lance une pré-génération contrôlée, à réserver à l’administration. |

## Prompt intergénérationnel recommandé

À placer dans `quiz_antan/backend/prompts.py` :

```python
SYSTEM_PROMPT = """
Tu es le moteur de génération de Quiz d’Antan, un jeu de quiz intergénérationnel.
Ta mission est de créer des questions variées, bienveillantes, accessibles et amusantes,
qui permettent aux jeunes, adultes, parents, grands-parents et arrière-grands-parents
 de jouer ensemble.

Règles éditoriales :
- Mélange les époques : années 1950 à aujourd’hui, sans te limiter à une seule génération.
- Mélange les types de culture : histoire, vie quotidienne, objets anciens, musique,
  cinéma, sport, cuisine, école, métiers, inventions, expressions populaires, télévision,
  jeux, géographie, traditions et usages numériques.
- Évite les questions trop clivantes, politiques ou anxiogènes.
- Favorise les questions qui peuvent déclencher une discussion ou un souvenir.
- Alterne questions faciles, moyennes et un peu plus difficiles.
- N’utilise pas toujours les mêmes célébrités, événements ou décennies.
- Réponds uniquement en JSON valide, sans texte autour.
"""

USER_PROMPT_TEMPLATE = """
Génère un quiz intergénérationnel sur le thème : {theme}.

Paramètres :
- Nombre de questions : {question_count}
- Difficulté publique cible : {difficulty}
- Époque cible : {era}
- Public : familles, seniors, adultes et jeunes joueurs ensemble

Contraintes de variété :
- Inclure au moins 3 décennies différentes si le thème le permet.
- Inclure au moins une question accessible aux plus jeunes.
- Inclure au moins une question qui parlera davantage aux générations plus âgées.
- Inclure au moins une question reliant passé et présent.
- Varier les formats : connaissance, comparaison, souvenir collectif, objet, chanson,
  expression, événement ou usage du quotidien.

Format JSON attendu :
{
  "theme": "string",
  "era": "string",
  "difficulty": "string",
  "questions": [
    {
      "id": "string",
      "question": "string",
      "choices": ["string", "string", "string", "string"],
      "answerIndex": 0,
      "explanation": "string",
      "generationHint": "pour quel public ou souvenir cette question peut créer une discussion"
    }
  ]
}
"""
```

## Stratégie de cache

1. **Sans cache** : chaque demande utilisateur appelle Mistral. C’est simple à mettre en place, mais le coût augmente linéairement avec le trafic et la latence dépend directement du temps de réponse de l’API.
2. **Avec cache Redis** : la clé de cache peut combiner `theme`, `difficulty`, `era`, `question_count` et une version de prompt. Si une combinaison existe déjà, le backend renvoie le quiz immédiatement sans nouvel appel Mistral.
3. **Pré-génération nocturne** : `cron_prefetch.py` génère chaque nuit un stock de quiz pour les thèmes les plus utilisés. Les premiers utilisateurs du matin reçoivent donc une réponse rapide et peu coûteuse.
4. **Fallback si Redis down** : si Redis est indisponible, le backend doit continuer à fonctionner en appelant directement Mistral. Si Mistral échoue aussi, il peut retourner un petit quiz local de secours ou un message clair invitant à réessayer.
5. **TTL 24h** : chaque quiz généré peut être stocké avec un TTL de 24 heures. Cela garde les questions suffisamment fraîches tout en évitant de regénérer les mêmes combinaisons trop souvent.

Exemple de clé Redis :

```text
quiz:v1:{theme}:{difficulty}:{era}:{question_count}
```

## Thèmes disponibles

| Thème | Catégorie | Era cible | Difficulté publique cible |
|---|---|---|---|
| Souvenirs d’école | Vie quotidienne | 1950-aujourd’hui | Facile |
| Objets d’hier et d’aujourd’hui | Vie quotidienne | 1950-aujourd’hui | Facile |
| Musique à travers les générations | Culture | 1960-aujourd’hui | Moyenne |
| Cinéma et télévision familiale | Culture | 1960-aujourd’hui | Moyenne |
| Expressions et proverbes | Langue française | Toutes époques | Facile |
| Cuisine de famille | Traditions | 1950-aujourd’hui | Facile |
| Inventions qui ont changé la vie | Sciences et technologies | 1900-aujourd’hui | Moyenne |
| Sport populaire | Sport | 1950-aujourd’hui | Moyenne |
| Histoire du quotidien | Histoire sociale | 1945-aujourd’hui | Moyenne |
| Jeux et loisirs | Loisirs | 1950-aujourd’hui | Facile |
| Métiers d’hier et de demain | Société | 1950-aujourd’hui | Moyenne |
| Transports et voyages | Vie quotidienne | 1950-aujourd’hui | Moyenne |
| Mode et tendances | Culture populaire | 1950-aujourd’hui | Facile |
| Nouvelles technologies | Technologie | 1980-aujourd’hui | Moyenne |
| Fêtes et traditions | Traditions | Toutes époques | Facile |
| Géographie de proximité | Géographie | Toutes époques | Facile |
| Publicités et slogans cultes | Culture populaire | 1960-aujourd’hui | Moyenne |
| Radio, télé et internet | Médias | 1950-aujourd’hui | Moyenne |
| Mémoire des années marquantes | Histoire récente | 1950-aujourd’hui | Difficile douce |
| Passé ou présent ? | Comparaison intergénérationnelle | 1950-aujourd’hui | Facile |

## Coûts estimés

Mistral indique pour **Mistral Small 4** un tarif API de **0,15 $ par million de tokens en entrée** et **0,60 $ par million de tokens en sortie** [[1]](#ref1). Les estimations ci-dessous utilisent cette hypothèse tarifaire et une hypothèse technique volontairement simple :

- 1 génération de quiz = environ **1 500 tokens en entrée** ;
- 1 génération de quiz = environ **2 500 tokens en sortie** ;
- coût estimé par quiz généré sans cache = `1 500 × 0,15 / 1 000 000 + 2 500 × 0,60 / 1 000 000`, soit environ **0,001725 $** ;
- scénario avec cache = **70 % de réponses servies depuis Redis** et **30 % de nouveaux appels Mistral** ;
- les montants n’incluent pas Redis, hébergement, logs, monitoring, marge d’erreur de tokenisation ni éventuelles variations de prix.

| Scénario | Quiz demandés / mois | Appels Mistral sans cache | Coût estimé sans cache | Appels Mistral avec cache 70 % | Coût estimé avec cache |
|---:|---:|---:|---:|---:|---:|
| Petit lancement | 100 | 100 | ~0,17 $ / mois | 30 | ~0,05 $ / mois |
| Trafic régulier | 1 000 | 1 000 | ~1,73 $ / mois | 300 | ~0,52 $ / mois |
| Forte activité | 10 000 | 10 000 | ~17,25 $ / mois | 3 000 | ~5,18 $ / mois |

> À retenir : le cache n’est pas seulement une optimisation de coût. Il améliore aussi la latence, absorbe les pics de trafic et réduit la dépendance immédiate à l’API Mistral.

## Recommandations de maintenance

- Versionner les prompts avec un préfixe de cache (`quiz:v1`, puis `quiz:v2` si le prompt change fortement).
- Journaliser les erreurs Mistral sans stocker de données personnelles inutiles.
- Ajouter un contrôle JSON strict côté backend avant de renvoyer une réponse au frontend.
- Prévoir une liste de thèmes autorisés côté backend pour éviter les abus.
- Mesurer le taux de cache hit afin d’ajuster la pré-génération nocturne.
- Ajouter une limite de fréquence par IP ou utilisateur si le site devient public.

## Référence

<p id="ref1" class="ref_item">[1] Mistral AI — Pricing <a target="_blank" rel="noreferrer" href="https://mistral.ai/pricing/">https://mistral.ai/pricing/</a></p>
