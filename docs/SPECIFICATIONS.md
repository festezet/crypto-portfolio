# Crypto Portfolio Tracker - Spécifications

## 1. Vue d'ensemble

### 1.1 Objectif
Application web de suivi en temps réel d'un portefeuille de cryptomonnaies multi-exchanges (Binance, Kucoin) avec :
- Suivi des positions et valorisation
- Historique des transactions
- Stratégies de sortie automatisées
- Calcul des P&L pour déclaration fiscale

### 1.2 Stack Technique
- **Backend** : Python 3 + Flask (micro-framework léger)
- **Base de données** : SQLite (légère, portable)
- **Frontend** : HTML5/Jinja2 + CSS3 + JavaScript vanilla
- **Graphiques** : Chart.js
- **APIs externes** : CoinGecko (prix temps réel, gratuit)

### 1.3 Pourquoi Flask ?
- Simple et léger (pas de compilation, pas de node_modules)
- Démarrage rapide (~2 secondes)
- Portable (un seul fichier de base de données)
- Autonome (fonctionne en local sans dépendances cloud)

## 2. Fonctionnalités Détaillées

### 2.1 Tableau de Bord Principal

#### 2.1.1 Vue Portefeuille Global
| Colonne | Description |
|---------|-------------|
| Crypto | Symbole (BTC, ETH, etc.) |
| Volume | Quantité totale détenue |
| Avg Weighted Cost | Prix moyen pondéré d'acquisition (Σ(prix × volume) / Σ(volume)) |
| Cours actuel | Prix temps réel via API CoinGecko |
| Valeur | Volume × Cours actuel |
| P&L | Profit & Loss brut (Valeur - Investissement) |
| P&L % | Pourcentage de gain/perte |
| Exchange | Binance / Kucoin / Manuel |

#### 2.1.2 Résumé Global
- Valeur totale du portefeuille (EUR)
- Investissement total
- P&L global (brut et net)
- Répartition par crypto (pie chart)

### 2.2 Historique des Transactions

#### 2.2.1 Types de transactions
- **BUY** : Achat
- **SELL** : Vente
- **TRANSFER_IN** : Dépôt depuis wallet externe
- **TRANSFER_OUT** : Retrait vers wallet externe
- **STAKING_REWARD** : Récompense de staking
- **AIRDROP** : Airdrop reçu

#### 2.2.2 Données par transaction
- Date/heure
- Type
- Exchange
- Crypto
- Volume
- Prix unitaire
- Montant total
- Frais
- Notes

### 2.3 Graphiques et Visualisation

#### 2.3.1 Répartition du portefeuille
- Pie chart / Doughnut : allocation par crypto (implémenté)

#### 2.3.2 Évolution du portefeuille (À FAIRE)
- Graphique linéaire : valeur du portefeuille dans le temps
- Période configurable : 7j, 30j, 90j, 1an, tout

#### 2.3.3 Trending views par crypto (À FAIRE)
- Mini-graphiques sparkline pour chaque crypto
- Tendance 24h, 7j, 30j
- Intégration API CoinGecko market_chart

### 2.4 Stratégies de Sortie (Exit Strategies)

#### 2.4.1 Concept
Définir des règles de vente automatiques basées sur des seuils de profit pour :
- Sécuriser les bénéfices progressivement
- Réduire l'exposition au fur et à mesure de la hausse
- Récupérer le capital investi

#### 2.4.2 Seuils par défaut
| Seuil profit | Action | Description |
|--------------|--------|-------------|
| +20% | Vendre 10% | Sécuriser premiers gains |
| +50% | Vendre 15% | Prendre des bénéfices |
| +100% | Vendre 20% | Récupérer le capital |
| +200% | Vendre 25% | Réduire l'exposition |
| +500% | Vendre 30% | Maximiser les gains |

#### 2.4.3 Modes d'exécution
1. **Mode Alerte** : Notification quand seuil atteint
2. **Mode Semi-auto** : Génère l'ordre à valider manuellement
3. **Mode Auto** : Exécution automatique (futur, nécessite clés API trade)

### 2.5 Import/Export

#### 2.5.1 Import fichiers
- **Format Binance** : CSV export historique trades (implémenté)
- **Format Kucoin** : CSV export historique trades (implémenté)
- **Format personnalisé** : CSV avec mapping configurable

#### 2.5.2 Export
- Historique complet (CSV, JSON)
- Rapport fiscal annuel (TXT, CSV)

### 2.6 Calcul Fiscal

#### 2.6.1 Méthode de calcul
- **FIFO** (First In, First Out) : Méthode standard en France

#### 2.6.2 Rapport annuel
- Liste des cessions (ventes)
- Prix d'acquisition (méthode FIFO)
- Prix de cession
- Plus/moins-value par transaction
- Total des plus-values imposables

## 3. Architecture Technique

### 3.1 Structure du projet
```
crypto-portfolio/
├── backend/
│   ├── app.py              # Application Flask principale
│   ├── config.py           # Configuration
│   ├── api/routes.py       # Endpoints API REST
│   ├── models/             # Modèles SQLAlchemy
│   │   ├── crypto.py
│   │   ├── transaction.py
│   │   ├── portfolio.py
│   │   └── strategy.py
│   └── services/           # Logique métier
│       ├── portfolio.py    # Calcul positions, PMP, P&L
│       ├── price.py        # Prix temps réel CoinGecko
│       ├── import_export.py
│       ├── strategy.py
│       └── fiscal.py
├── frontend/
│   ├── templates/          # Pages HTML (Jinja2)
│   │   ├── base.html
│   │   ├── dashboard.html
│   │   ├── transactions.html
│   │   ├── strategies.html
│   │   ├── fiscal.html
│   │   ├── import.html
│   │   └── settings.html
│   └── static/
│       ├── css/style.css
│       └── js/app.js
├── data/
│   ├── portfolio.db        # Base SQLite
│   ├── imports/
│   └── exports/
├── scripts/
│   └── generate_dummy_data.py
├── docs/
│   └── SPECIFICATIONS.md
├── requirements.txt
├── start.sh
└── README.md
```

### 3.2 API Endpoints

```
GET  /api/portfolio              # Résumé portefeuille
GET  /api/portfolio/history      # Historique valorisation
GET  /api/holdings               # Positions détaillées
GET  /api/transactions           # Liste transactions
POST /api/transactions           # Ajouter transaction
PUT  /api/transactions/<id>      # Modifier transaction
DELETE /api/transactions/<id>    # Supprimer transaction
POST /api/import                 # Importer fichier
GET  /api/export/transactions    # Exporter données
GET  /api/prices                 # Prix temps réel
GET  /api/strategies             # Liste stratégies
POST /api/strategies             # Créer stratégie
GET  /api/alerts                 # Alertes actives
GET  /api/fiscal/<year>          # Rapport fiscal
```

## 4. Bugs connus et améliorations

### 4.1 Bugs corrigés ✅
- [x] **Page Transactions** : Script déplacé dans `{% block extra_js %}` pour charger après app.js
- [x] **Graphique répartition** : Ajout appel `loadDashboard()` + destroy() pour éviter duplication
- [x] **Intégration HomeHub** : Lien ajouté avec lancement terminal + ouverture Firefox auto

### 4.2 Fonctionnalités à ajouter
- [ ] **Graphique évolution historique** : Courbe de la valeur du portefeuille dans le temps (priorité haute)
  - Nécessite : endpoint `/api/portfolio/history` + table `portfolio_snapshots`
  - Affichage : Chart.js line chart avec périodes configurables (7j, 30j, 90j, 1an)
- [ ] **Trending views** : Mini-graphiques sparkline de tendance pour chaque crypto
  - API CoinGecko : `/coins/{id}/market_chart?days=7`
- [ ] **Tests unitaires** : Couverture des services métier
- [ ] **Tests d'intégration** : Tests API endpoints

### 4.3 Intégrations futures
- [x] Lien dans HomeHub pour lancer l'application ✅
- [ ] Import automatique via API Binance/Kucoin (avec clés API)
- [ ] Notifications desktop pour les alertes de stratégie

## 5. Données de test

Un script génère des données de test simulant une stratégie DCA :
- **Montant** : 1000€/mois depuis janvier 2025
- **Répartition** : 70% BTC, 15% ETH, 5% SOL, 10% altcoins
- **Altcoins** : AAVE, HYPE, DOT, XMR, XRP, BNB

```bash
python3 scripts/generate_dummy_data.py
```

## 6. Lancement

```bash
cd /data/projects/crypto-portfolio
./start.sh
# Ouvrir http://localhost:5050
```

---

*Document créé le : 2025-11-21*
*Dernière mise à jour : 2025-11-21*
*Version : 1.1*
