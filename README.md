# Crypto Portfolio Tracker

## 🎯 Objectif

Application web de suivi de portefeuille crypto multi-exchanges avec strategies de sortie automatisees et calcul fiscal.

## 🚀 Démarrage

```bash
cd /data/projects/crypto-portfolio
./start.sh    # Lance venv + serveur sur http://localhost:5050
```

Application web de suivi de portefeuille crypto multi-exchanges avec stratégies de sortie automatisées et calcul fiscal.

## Fonctionnalités

- **Dashboard** : Vue d'ensemble du portefeuille avec valorisation temps réel
- **Multi-exchanges** : Support Binance et Kucoin
- **Import/Export** : Import des fichiers CSV d'historique des exchanges
- **Prix temps réel** : Via API CoinGecko (gratuit, sans clé)
- **Calcul PMP** : Prix Moyen Pondéré automatique
- **P&L** : Profit & Loss brut et net par position
- **Stratégies de sortie** : Alertes automatiques sur seuils de profit
- **Rapport fiscal** : Calcul des plus-values (méthode FIFO) pour déclaration

## Installation

### Prérequis
- Python 3.8+
- pip

### Installation rapide

```bash
cd /data/projects/crypto-portfolio
./start.sh
```

Le script :
1. Crée un environnement virtuel Python
2. Installe les dépendances
3. Lance le serveur web

### Installation manuelle

```bash
# Créer l'environnement virtuel
python3 -m venv venv
source venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt

# Lancer l'application
python3 backend/app.py
```

## Utilisation

### Accès
- **URL** : http://localhost:5050
- **API** : http://localhost:5050/api

### Import de transactions

1. Aller sur la page "Import"
2. Sélectionner la source (Binance, Kucoin, ou détection auto)
3. Glisser-déposer votre fichier CSV d'export

#### Format Binance
Export depuis : Ordres > Historique des trades > Exporter

#### Format Kucoin
Export depuis : Ordres > Historique des transactions > Exporter

### Stratégies de sortie

Les stratégies de sortie permettent de définir des seuils de profit auxquels vendre progressivement :

| Seuil | Action |
|-------|--------|
| +20%  | Vendre 10% |
| +50%  | Vendre 15% |
| +100% | Vendre 20% + récupérer capital |
| +200% | Vendre 25% |
| +500% | Vendre 30% |

Ces seuils sont configurables par crypto.

### Rapport fiscal

Le rapport fiscal calcule les plus-values selon la méthode FIFO (First In, First Out) :
- Liste des cessions avec détail des acquisitions
- Calcul automatique des plus/moins-values
- Export CSV pour déclaration

## API

### Endpoints principaux

```
GET  /api/portfolio       # Résumé du portefeuille
GET  /api/holdings        # Positions détaillées
GET  /api/transactions    # Liste des transactions
POST /api/transactions    # Ajouter une transaction
POST /api/import          # Importer un fichier
GET  /api/prices          # Prix temps réel
GET  /api/strategies      # Stratégies de sortie
GET  /api/fiscal/<year>   # Rapport fiscal
```

## 📂 Structure

```
crypto-portfolio/
├── backend/
│   ├── app.py              # Application Flask
│   ├── config.py           # Configuration
│   ├── api/routes.py       # Endpoints API
│   ├── models/             # Modèles SQLAlchemy
│   └── services/           # Logique métier
├── frontend/
│   ├── templates/          # Pages HTML
│   └── static/             # CSS, JS, images
├── data/
│   ├── portfolio.db        # Base de données SQLite
│   ├── imports/            # Fichiers importés
│   └── exports/            # Fichiers exportés
├── docs/
│   └── SPECIFICATIONS.md
├── requirements.txt
├── start.sh
└── README.md
```

## Configuration

Les variables d'environnement optionnelles :

```bash
# Clés API (optionnel - pour import automatique)
export BINANCE_API_KEY="..."
export BINANCE_API_SECRET="..."
export KUCOIN_API_KEY="..."
export KUCOIN_API_SECRET="..."
export KUCOIN_API_PASSPHRASE="..."

# Configuration serveur
export FLASK_DEBUG=1
export SECRET_KEY="votre-clé-secrète"
```

## Développement

### Ajouter une nouvelle crypto

Les cryptos sont automatiquement créées lors de l'import. Pour ajouter manuellement :

```bash
curl -X POST http://localhost:5050/api/cryptos \
  -H "Content-Type: application/json" \
  -d '{"symbol": "NEW", "name": "New Coin", "coingecko_id": "new-coin"}'
```

### Ajouter une transaction manuellement

```bash
curl -X POST http://localhost:5050/api/transactions \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTC",
    "type": "BUY",
    "date": "2024-01-15T10:00:00",
    "volume": 0.5,
    "price": 40000,
    "fee": 10,
    "exchange": "binance"
  }'
```

## Stack technique

- **Backend** : Python 3 + Flask (micro-framework léger)
- **Base de données** : SQLite (portable, un seul fichier)
- **Frontend** : HTML5/Jinja2 + CSS3 + JavaScript vanilla
- **Graphiques** : Chart.js
- **API externe** : CoinGecko (prix temps réel, gratuit)

## Bugs connus et TODO

### Bugs corrigés ✅
- [x] Page Transactions : Script déplacé dans `{% block extra_js %}`
- [x] Graphique répartition (pie chart) : Ajout `loadDashboard()` + `destroy()`
- [x] Intégration HomeHub : Lien ajouté avec terminal + Firefox auto

### Fonctionnalités à ajouter
- [ ] **Graphique évolution historique** : Courbe de la valeur du portefeuille dans le temps (priorité)
- [ ] Trending views : Mini-graphiques sparkline de tendance pour chaque crypto
- [ ] Tests unitaires et d'intégration

### Intégrations
- [x] Lien dans HomeHub ✅
- [ ] Import automatique via API Binance/Kucoin

## Données de test

Générer des données DCA simulées (1000€/mois depuis janvier 2025) :

```bash
cd /data/projects/crypto-portfolio
source venv/bin/activate
python3 scripts/generate_dummy_data.py
```

## Licence

Usage personnel uniquement.

---
*Développé avec Flask, SQLite et Chart.js*
