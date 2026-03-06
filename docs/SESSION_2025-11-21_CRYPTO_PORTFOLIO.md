# Session 2025-11-21 : Crypto Portfolio Tracker

## Objectif
Recréer l'application de suivi de portefeuille crypto perdue après crash PC.

## Travail réalisé

### 1. Création complète de l'application

**Stack technique choisie :**
- Backend : Python 3 + Flask (micro-framework léger)
- Base de données : SQLite (portable)
- Frontend : HTML5/Jinja2 + CSS3 + JavaScript vanilla
- Graphiques : Chart.js
- API externe : CoinGecko (prix temps réel, gratuit)

**Structure créée :**
```
/data/projects/crypto-portfolio/
├── backend/
│   ├── app.py              # Application Flask (port 5050)
│   ├── config.py           # Configuration + CRYPTO_MAPPING
│   ├── api/routes.py       # Endpoints REST
│   ├── models/             # SQLAlchemy (crypto, transaction, portfolio, strategy)
│   └── services/           # Logique métier (portfolio, price, fiscal, import_export)
├── frontend/
│   ├── templates/          # dashboard, transactions, strategies, fiscal, import, settings
│   └── static/css,js/
├── data/portfolio.db
├── scripts/generate_dummy_data.py
├── start.sh
└── requirements.txt
```

### 2. Fonctionnalités implémentées

| Fonctionnalité | Status |
|----------------|--------|
| Dashboard avec résumé portefeuille | ✅ |
| Tableau des positions avec PMP, P&L | ✅ |
| Graphique répartition (pie chart) | ✅ |
| Page transactions avec filtres | ✅ |
| Import CSV Binance/Kucoin | ✅ |
| Export CSV/JSON | ✅ |
| Stratégies de sortie (exit strategies) | ✅ |
| Calcul fiscal FIFO | ✅ |
| Prix temps réel CoinGecko | ✅ |

### 3. Données de test générées

Script DCA simulant 1000€/mois depuis janvier 2025 :
- **Répartition** : 70% BTC, 15% ETH, 5% SOL, 10% altcoins
- **Altcoins** : AAVE, HYPE (Hyperliquid), DOT, XMR, XRP, BNB
- **Résultat** : 99 transactions, 9 cryptos, ~11 000€ investis

### 4. Bugs corrigés

1. **HYPE non reconnu** : Ajout `"HYPE": "hyperliquid"` dans CRYPTO_MAPPING (config.py)

2. **Page Transactions bloquée (spinner)** :
   - Cause : Script dans `{% block content %}` exécuté avant app.js
   - Fix : Déplacé dans `{% block extra_js %}`

3. **Graphique répartition non affiché** :
   - Cause : `loadDashboard()` jamais appelé
   - Fix : Ajout appel dans `DOMContentLoaded` + `allocationChart.destroy()` pour éviter duplication

### 5. Intégration HomeHub

**Fichiers modifiés :**
- `HomeHub.html` : Ajout carte "Crypto Portfolio" avec `launchApp('crypto')`
- `docker_control_server.py` :
  - Ajout entrée 'crypto' dans dict scripts
  - Commande : `gnome-terminal -- bash -c "cd /data/projects/crypto-portfolio && ./start.sh" & sleep 3 && firefox http://localhost:5050`
  - Fix : `shell=True` pour commandes avec espaces

### 6. Graphique évolution historique (2025-11-21 soir)

**Implémentation complète** :
- ✅ Script `generate_snapshots.py` créé pour générer snapshots historiques
- ✅ 325 snapshots générés (1 par jour depuis janvier 2025)
- ✅ Graphique line Chart.js ajouté au dashboard
- ✅ Sélecteur de période : 7j, 30j, 90j, 1an, Tout
- ✅ Double courbe : Valeur totale (bleue) + Total investi (grise pointillés)
- ✅ Tooltip interactif avec montants EUR formatés
- ✅ Responsive et animations fluides

**Fichiers modifiés** :
- `frontend/templates/dashboard.html` : Ajout section graphique historique
- `frontend/static/js/app.js` : Fonction `loadHistory(period)`
- `frontend/static/css/style.css` : Styles boutons période

**Fichiers créés** :
- `scripts/generate_snapshots.py` : Génération snapshots quotidiens
- `CHANGELOG.md` : Documentation des changements

### 7. Bug fix : Boutons de période (2025-11-21 soir)

**Problème détecté** : Les boutons 7j/30j/90j/1an/Tout ne changeaient pas l'affichage du graphique.

**Cause** : Calcul de date incorrect dans `portfolio.py` ligne 201
```python
# Buggé
from_date.replace(day=from_date.day - days)  # Soustrait des jours du JOUR du mois

# Corrigé
from_date = now - timedelta(days=days)  # Soustrait des jours du timestamp
```

**Résultats des tests** :
- ✅ 7j : 8 snapshots (14 nov → 21 nov)
- ✅ 30j : 31 snapshots (22 oct → 21 nov)
- ✅ 90j : 91 snapshots (23 août → 21 nov)
- ✅ 365j : 325 snapshots (1 jan → 21 nov)

**Fichiers modifiés** :
- `backend/services/portfolio.py` : Fix calcul date avec timedelta
- `frontend/templates/dashboard.html` : Active button 30j par défaut
- `BUG_FIX_PERIODE.md` : Documentation du bug

### 8. Prix historiques réels (2025-11-21 soir)

**Objectif** : Utiliser les vrais prix historiques au lieu des prix actuels projetés.

**Implémentation** :
- ✅ Script `generate_snapshots_historical.py` avec API CoinGecko `/market_chart`
- ✅ 1 requête par crypto pour tous les jours (efficient)
- ✅ Rate limiting : 8 secondes entre requêtes (éviter 429)
- ✅ 324 snapshots avec prix historiques réels

**Résultats** :
- **7/9 cryptos** récupérées : ETH, DOT, XRP, HYPE, BTC, XMR, SOL
- **Manquantes** : BNB, AAVE (rate limit API gratuite)
- **BTC inclus** : 77% du portefeuille représenté
- **Évolution réelle** : 1900€ → 17324€ (max) → 12622€ (actuel)
- **Variation** : +812% sur l'année

**Fichiers** :
- `scripts/generate_snapshots_historical.py` : Génération avec prix réels
- `PRIX_HISTORIQUES_README.md` : Documentation technique

**Base de données** :
- Snapshots sauvegardés dans `data/portfolio.db`
- Table `portfolio_snapshots` : 324 lignes
- Pas besoin de régénérer, maintenance = 1 snapshot/jour

## À faire (prochaines sessions)

### Priorité haute
- [x] **Graphique évolution historique** ✅ TERMINÉ
- [x] **Prix historiques réels** ✅ TERMINÉ (7/9 cryptos)

### Priorité moyenne
- [ ] **Trending views** : Mini-graphiques sparkline par crypto
  - API CoinGecko : `/coins/{id}/market_chart?days=7`
  - Affichage dans colonne du tableau positions

### Priorité basse
- [ ] Tests unitaires services
- [ ] Tests intégration API
- [ ] Import automatique via API Binance/Kucoin (clés API)

## Commandes utiles

```bash
# Lancer l'application
cd /data/projects/crypto-portfolio && ./start.sh

# Régénérer données test
source venv/bin/activate && python3 scripts/generate_dummy_data.py

# Accès
http://localhost:5050
```

## Fichiers de documentation

- `/data/projects/crypto-portfolio/README.md` - Guide utilisateur
- `/data/projects/crypto-portfolio/docs/SPECIFICATIONS.md` - Spécifications techniques détaillées

---
*Session terminée : 2025-11-21*
