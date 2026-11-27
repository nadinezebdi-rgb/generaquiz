# Test Credentials for GénéraQuiz SaaS

⚠️ Aucun mot de passe en clair dans ce fichier (dépôt GitHub). Les identifiants de test sont dans `backend/.env` (non versionné).

## Admin de test (aperçu uniquement, n'existe pas en production)
- Email : variable `TEST_ADMIN_EMAIL` dans `/app/backend/.env` (qa-admin@generaquiz.fr)
- Mot de passe : variable `TEST_ADMIN_PASSWORD` dans `/app/backend/.env`
- Rôle : superadmin, Premium jusqu'en 2099
- Les tests pytest lisent `os.environ["TEST_ADMIN_EMAIL"]` / `os.environ["TEST_ADMIN_PASSWORD"]` : `export $(grep TEST_ADMIN /app/backend/.env | xargs)` avant de lancer.

## Compte propriétaire
- admin@generaquiz.fr : mot de passe géré par le propriétaire uniquement, jamais écrit ici.

## Codes promo
- `DECOUVERTE30` — 30 jours, max 50 utilisations
- `FAMILLE2026` — DÉSACTIVÉ (audit sécurité 2026-11), Premium retiré aux comptes non admin qui l'avaient utilisé

## Test User
Créer un compte via `/register` pour tester la formule gratuite (5 questions / jour).

## Limites
- `/auth/login` : 30 / 15 min par IP + 8 échecs / 15 min par compte
- `/auth/register` : 5 / heure par IP
- `/auth/forgot-password` : 3 / 15 min par IP
- `/contact` : 5 / heure par IP
- Livre coop public : 15 codes inconnus / 15 min par IP ; sessions expirées après 24 h
- Les limites sont stockées dans Mongo (`rate_limits`) : `db.rate_limits.delete_many({})` pour réinitialiser pendant les tests.

## Stripe
Carte test 4242 4242 4242 4242, date future, CVC 123.
