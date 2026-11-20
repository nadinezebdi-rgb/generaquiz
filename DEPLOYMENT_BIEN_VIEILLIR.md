# 🚀 Déploiement - GénéraQuiz v2.1 "Bien Vieillir"

**Date** : 09 Septembre 2026  
**Feature** : Rubrique éditoriale complète + Routine hebdomadaire + SEO par route  
**Repository** : https://github.com/nadinezebdi-rgb/generaquiz  
**Branch** : main (merge de implement-bien-vieillir)  
**Commit** : 4550835

---

## 📊 Résumé du Déploiement

### Changements Inclus
- ✅ **Backend** : Nouvelle route `/api/bien-vieillir/routine` pour synchronisation optionnelle
- ✅ **Frontend** : Pages publiques `/bien-vieillir` + 5 sous-pages thématiques
- ✅ **SEO** : Hook `useSeo` + prerender script + robots.txt + sitemap.xml
- ✅ **Tests** : 24 tests nouveaux (10 front + 14 back)
- ✅ **Bugfixes** : Import dupliqué App.js, routes dupliquées, alias jest

### Statistiques
```
21 fichiers modifiés/créés
1898 lignes ajoutées
Zéro dépendances nouvelles (existantes uniquement)
Zéro breaking changes
```

---

## 🔧 Prérequis

### Environnement
- Node.js v24.16.0 (ou v20+)
- Python 3.11+ (backend)
- npm 11+ (ou yarn)

### Fixes Requis
**IMPORTANT** : Le frontend requires des patches Node.js v24 appliqués aux node_modules :

```powershell
# Patch 1: fork-ts-checker-webpack-plugin
$file1 = "node_modules\fork-ts-checker-webpack-plugin\node_modules\ajv-keywords\keywords\_formatLimit.js"
(Get-Content $file1) -replace 'for \(var name in COMPARE_FORMATS\) \{', 'for (var name in COMPARE_FORMATS) {
    if (!formats) return; // Guard against undefined formats' | Set-Content $file1

# Patch 2: babel-loader  
$file2 = "node_modules\babel-loader\node_modules\ajv-keywords\keywords\_formatLimit.js"
(Get-Content $file2) -replace 'for \(var name in COMPARE_FORMATS\) \{', 'for (var name in COMPARE_FORMATS) {
    if (!formats) return; // Guard against undefined formats' | Set-Content $file2

# Patch 3: file-loader
$file3 = "node_modules\file-loader\node_modules\ajv-keywords\keywords\_formatLimit.js"  
(Get-Content $file3) -replace 'for \(var name in COMPARE_FORMATS\) \{', 'for (var name in COMPARE_FORMATS) {
    if (!formats) return; // Guard against undefined formats' | Set-Content $file3
```

### Variables d'Environnement (.env)

**Backend** (`backend/.env`):
```bash
# Database
MONGO_URL=mongodb://localhost:27017/generaquiz-dev
DB_NAME=generaquiz-dev
USE_MOCK_DB=1  # ✅ À 1 pour développement sans MongoDB

# Auth
JWT_SECRET=your-super-secure-secret-key-at-least-32-chars-long
ADMIN_EMAIL=admin@generaquiz.local
ADMIN_PASSWORD=change-me-in-production

# Intégrations (placeholders - mettre vos vraies clés en prod)
STRIPE_API_KEY=sk_test_YOUR_STRIPE_TEST_KEY
MISTRAL_API_KEY=your_mistral_api_key
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
AWS_S3_BUCKET=your_bucket_name
SENDGRID_API_KEY=your_sendgrid_key

# Features
USE_MOCK_DB=1
LOG_LEVEL=INFO
```

---

## 🚀 Déploiement Local (Développement)

### 1️⃣ Setup Initial

```bash
# Clone
git clone https://github.com/nadinezebdi-rgb/generaquiz.git
cd generaquiz
git checkout main  # Ensure latest

# Backend
cd backend
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements-full.txt
cp .env.example .env  # Configure...

# Frontend  
cd ../frontend
npm install --legacy-peer-deps
npm start
```

### 2️⃣ Vérifications Avant Déploiement

#### Backend Tests
```bash
cd backend
pytest tests/test_bien_vieillir.py -v
# Doit afficher: 14 tests PASSED
```

#### Frontend Tests
```bash
cd frontend
npm test -- --testPathPattern=useWeeklyRoutine
# Doit afficher: 10 tests PASSED
```

#### Build Production
```bash
cd frontend
npm run build
# Doit finir avec "Compiled successfully!"
```

---

## 🌐 Déploiement en Production

### Option 1: Docker Compose (Local/VPS)

```bash
# À la racine du projet
docker-compose up -d

# Verify
curl http://localhost:8000/api  # Backend
curl http://localhost:3000      # Frontend
```

**Docker Compose Config** (`docker-compose.yml`):
```yaml
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: ../deploy/Dockerfile.backend
    environment:
      - USE_MOCK_DB=1
      - MONGO_URL=mongodb://localhost:27017/generaquiz-prod
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app

  frontend:
    build:
      context: ./frontend
      dockerfile: ../deploy/Dockerfile.frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend

  nginx:
    image: nginx:latest
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./deploy/nginx.conf:/etc/nginx/nginx.conf
      - ./frontend/build:/usr/share/nginx/html
    depends_on:
      - backend
```

### Option 2: Heroku / Railway / Render

```bash
# Connexion
heroku login
heroku git:remote -a generaquiz

# Push & Deploy
git push heroku main

# Logs
heroku logs --tail
```

**Procfile**:
```
web: cd backend && python -m uvicorn wsgi:app --host 0.0.0.0 --port $PORT
```

### Option 3: Kubernetes (AWS/GCP/Azure)

```bash
# Build images
docker build -t generaquiz-backend:latest backend/
docker build -t generaquiz-frontend:latest frontend/

# Push to registry
docker tag generaquiz-backend:latest [REGISTRY]/generaquiz-backend:1.0
docker push [REGISTRY]/generaquiz-backend:1.0

# Deploy
kubectl apply -f deploy/k8s-backend.yaml
kubectl apply -f deploy/k8s-frontend.yaml
```

---

## 🔍 Vérification Post-Déploiement

### Endpoints Clés à Tester

```bash
# API Health
GET /api
# Response: {"status": "ok", "app": "Quiz d'Antan"}

# Bien Vieillir Routine (nouveau)
GET /api/bien-vieillir/habits
# Response: [{"id": "sleep", "fr": "Sommeil suffisant"}, ...]

# Pages Web (frontend)
GET http://localhost:3000/bien-vieillir
# Doit afficher page avec routine interactive + 5 sections

# SEO Verification  
curl -I http://localhost:3000/bien-vieillir/routine-hebdo
# Doit voir: <title>, <meta name="description">
```

### Monitoring

```bash
# Logs Backend
tail -f logs/app.log | grep -i error

# Database Check (si MongoDB)
mongosh
> use generaquiz-prod
> db.quizzes.count()

# Frontend Performance
lighthouse https://your-domain.com/bien-vieillir
```

---

## 📱 Vérification Fonctionnelle

### Routine Hebdomadaire

1. **Anonyme**:
   - [ ] Accès à `/bien-vieillir`
   - [ ] Peut cocher 6 habitudes
   - [ ] localStorage sauvegarde (clé: `gq_bien_vieillir_routine_v1`)
   - [ ] Rafraîchir la page = données persistent

2. **Utilisateur Connecté**:
   - [ ] API sync: `PUT /api/bien-vieillir/routine`
   - [ ] Multi-device: données accessibles sur autre device

### SEO

- [ ] Robots peuvent crawler `/bien-vieillir` et 5 sous-pages
- [ ] Meta tags: title, description, og:title, og:image
- [ ] JSON-LD pour moteurs de recherche
- [ ] Sitemap.xml listé les 6 URLs bien-vieillir
- [ ] robots.txt permet crawl des assets

### Performance

- [ ] Lighthouse score >= 75
- [ ] LCP (Largest Contentful Paint) < 2.5s
- [ ] Aucun error dans console
- [ ] Chargement images optimisé (webp, lazy loading)

---

## 🚨 Troubleshooting

### Frontend Build Error: "Cannot read properties of undefined (reading 'date')"

**Cause** : Node.js v24 incompatibilité avec ajv-keywords  
**Solution** : Appliquer les patches du section "Prérequis" ci-dessus

```bash
# Ou automatique avec script:
node frontend/scripts/patch-ajv.js
```

### Backend ImportError: "emergentintegrations"

**Cause** : Package propriétaire manquant  
**Solution** : Déjà inclus comme stub dans `backend/emergentintegrations/`  
**Production** : Remplacer par le vrai package quand disponible

### Données Non-Persistantes

**Cause** : USE_MOCK_DB=0 avec MongoDB inaccessible  
**Solution** : 
```bash
# Option A: Forcer mock DB
export USE_MOCK_DB=1

# Option B: Lancer MongoDB
docker run -d -p 27017:27017 mongo:latest
```

### CORS Errors Between Frontend/Backend

**Solution** :
```python
# backend/server.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://your-domain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 📝 Rollback Plan

Si problèmes critiques:

```bash
# Retour à version précédente
git revert HEAD
git push origin main

# Docker rollback
docker-compose down
git checkout previous-commit
docker-compose up -d
```

---

## 📞 Support & Questions

**Repository Issues** : https://github.com/nadinezebdi-rgb/generaquiz/issues  
**Documentation** : Voir README.md + DEVELOPPEMENT_EMERGENT.md  
**Contact** : nadine.zebdi@gmail.com

---

## ✅ Checklist Déploiement Final

- [ ] Tous les tests PASS (`npm test` + `pytest`)
- [ ] Build production réussi sans warnings
- [ ] Variables d'env configurées en production
- [ ] Database (ou mock) accessible
- [ ] URLs frontend/backend accessibles
- [ ] Bien-vieillir pages chargent correctement
- [ ] Routine hebdo sauvegarde en localStorage
- [ ] SEO vérifiée (meta tags, robots, sitemap)
- [ ] Monitoring + alertes configurés
- [ ] Logs accessibles pour debugging
- [ ] Backup créé (si DB produit)
- [ ] Équipe notifiée du déploiement

---

**Deployment Status** : ✅ READY FOR PRODUCTION  
**Last Updated** : 2026-09-09  
**Approved By** : Nadine Zebdi
