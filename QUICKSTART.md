# Guide de démarrage du Backend + Frontend

Ce document explique comment démarrer complètement le système (backend + frontend).

## Prérequis

- Python 3.9+
- Node.js 18+
- MongoDB (en cours d'exécution)
- MySQL (en cours d'exécution)

## 1. Configuration Backend

### 1.1 Installer les dépendances

```bash
cd src/api
pip install -r requirements.txt
```

### 1.2 Configurer les variables d'environnement

Copiez `.env.example` en `.env` (ou vérifiez que `.env` existe avec les bonnes valeurs) :

```bash
# Les valeurs par défaut devraient fonctionner si MongoDB/MySQL tournent localement
cat .env
```

Valeurs attendues :

- `MONGODB_URI=mongodb://localhost:27017`
- `MONGODB_DB=urban_data`
- `MYSQL_HOST=localhost`
- `MYSQL_PORT=3306`
- `MYSQL_DATABASE=urban_data`
- `MYSQL_USER=root`
- `MYSQL_PASSWORD=dbl2025`

## 2. Vérifier les bases de données

### 2.1 MongoDB

```bash
# Démarrer MongoDB (si pas encore lancé)
mongod

# Vérifier que les données sont chargées
mongo
> use urban_data
> db.geo_quartiers.count()  // Doit afficher un nombre > 0
> exit
```

### 2.2 MySQL

```bash
# Démarrer MySQL (si pas encore lancé)
mysql.server start

# Vérifier les tables KPI
mysql -u root -p urban_data
> SHOW TABLES;  // Doit afficher fact_kpi_* tables
> SELECT COUNT(*) FROM fact_kpi_confort_quartier;
> exit
```

## 3. Démarrer le Backend

### Option A : Via le script de lancement

```bash
cd src/api
python run.py
```

Le script va :

- Vérifier que MongoDB et MySQL sont accessibles
- Lancer le serveur FastAPI sur `http://localhost:8000`
- Afficher les logs en temps réel

### Option B : Directement avec uvicorn

```bash
cd src/api
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Option C : Python direct

```bash
cd src/api
python main.py
```

**⚠️ Le serveur doit rester en cours d'exécution dans un terminal séparé.**

## 4. Vérifier que le Backend fonctionne

```bash
# Dans un autre terminal
curl http://localhost:8000/health

# Devrait retourner :
# {"status":"ok","mongodb":"connected","mysql":"connected"}
```

Tester un endpoint :

```bash
curl "http://localhost:8000/api/quartiers/geojson" | jq '.features | length'
```

## 5. Démarrer le Frontend

### 5.1 Installer les dépendances

```bash
cd Front
npm install
```

### 5.2 Configuration API

Vérifiez que `.env` existe et contient :

```
VITE_API_URL=http://localhost:8000
```

### 5.3 Lancer le dev server

```bash
cd Front
npm run dev
```

Le frontend sera disponible sur `http://localhost:5173` (ou un autre port si 5173 est occupé).

## 6. Architecture complète

```
┌─────────────────────────────────────────────────────────┐
│                  React Frontend                          │
│                                                          │
│  http://localhost:5173                                  │
│  - Carte avec quartiers                                 │
│  - Sidebar gauche (quartiers, adresses)                │
│  - Sidebar droite (KPI, rapport)                        │
└──────────────────────────────┬──────────────────────────┘
                               │
                    API Calls via fetch
                               │
                               ▼
┌──────────────────────────────────────────────────────────┐
│            FastAPI Backend (Python)                      │
│                                                          │
│  http://localhost:8000                                  │
│  - GET /api/quartiers/geojson                           │
│  - GET /api/kpi/quartier/{id}                           │
│  - GET /api/quartiers/{id}/addresses                    │
│  - ... (7 endpoints)                                    │
└──────┬─────────────────────────┬────────────────────────┘
       │                         │
       ▼                         ▼
   MongoDB              MySQL
   (Géométries)         (KPI)
   localhost:27017      localhost:3306
```

## 7. Dépannage

### Backend refuses de démarrer

**"MongoDB not available"**

- Assurez-vous que `mongod` s'exécute
- Vérifiez que `MONGODB_URI` est correct dans `.env`

**"MySQL not available"**

- Assurez-vous que MySQL s'exécute
- Vérifiez les identifiants dans `.env`

### Frontend affiche "API indisponible"

- Vérifiez que le backend s'exécute: `curl http://localhost:8000/health`
- Vérifiez que `VITE_API_URL` est bien configuré dans `Front/.env`
- Vérifiez que le frontend charge la bonne URL dans la console du navigateur

### Les quartiers s'affichent mais pas les KPI

- Vérifiez que les tables MySQL contiennent des données:
  ```sql
  SELECT COUNT(*) FROM fact_kpi_confort_quartier;
  ```
- Les adresses affichent "Aucune donnée" car la base d'adresses n'existe pas encore (à implémenter)

## 8. Fichiers clés

- `src/api/main.py` : Application FastAPI (tous les endpoints)
- `src/api/requirements.txt` : Dépendances Python
- `src/api/.env` : Configuration (MongoDB, MySQL)
- `Front/src/services/apiService.ts` : Client API (fetch)
- `Front/.env` : Configuration frontend (URL API)
- `docs/API_FRONTEND_BACKEND.md` : Contrat API complet

## 9. Prochaines étapes

- [ ] Implémenter une vraie base d'adresses (IGN/BANO)
- [ ] Ajouter l'authentification au backend
- [ ] Déployer sur un serveur (Docker, Kubernetes)
- [ ] Ajouter des tests unitaires
- [ ] Implémenter la pagination pour les grands résultats
