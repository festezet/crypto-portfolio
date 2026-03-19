# Crypto Portfolio Tracker - Specification Technique
> Version: 1.0 | Date: 2026-03-13 | Projet: PRJ-XXX

---

## 1. Vision & Contexte

### 1.1 Probleme

Suivre un portefeuille crypto reparti sur plusieurs exchanges (Binance, Kucoin) est fastidieux : pas de vue consolidee, pas de calcul automatique du P&L, et la declaration fiscale annuelle necessite un travail manuel important pour reconstituer les plus-values (methode FIFO). Ce projet centralise toutes les donnees dans une application web locale, avec calcul automatise du PMP, des strategies de sortie, et du rapport fiscal.

### 1.2 Utilisateurs

| Profil | Objectif | Usage |
|--------|----------|-------|
| Investisseur crypto personnel | Suivre la performance de son portefeuille multi-exchanges en temps reel | Quotidien |
| Declarant fiscal | Generer un rapport FIFO des plus-values pour la declaration annuelle (formulaire 2086) | Annuel |
| Trader actif | Definir des strategies de sortie automatisees avec seuils de profit progressifs | Hebdomadaire |

### 1.3 Criteres de succes

- [x] Import CSV des transactions Binance et Kucoin avec detection automatique du format
- [x] Calcul en temps reel du P&L par position via l'API CoinGecko
- [x] Rapport fiscal FIFO exportable en CSV pour la declaration
- [x] Strategies de sortie avec alertes sur seuils de profit configurables
- [ ] Graphique d'evolution historique du portefeuille (snapshots)
- [ ] Tests unitaires et d'integration

---

## 2. Stack Technique

| Couche | Technologie | Version | Justification |
|--------|------------|---------|---------------|
| Backend | Python 3 + Flask | Flask 3.0.0 | Micro-framework leger, ideal pour une app locale single-user |
| ORM | SQLAlchemy | 2.0.23 | ORM mature, bien integre avec Flask via Flask-SQLAlchemy 3.1.1 |
| Base de donnees | SQLite | 3.x (embarque) | Portable (un seul fichier), zero config, suffisant pour usage personnel |
| Frontend | HTML5/Jinja2 + CSS3 + JavaScript vanilla | - | Pas de framework JS, rendu cote serveur avec enrichissement JS |
| Graphiques | Chart.js | CDN (derniere) | Graphiques interactifs (doughnut, line) charges via CDN |
| API externe | CoinGecko API v3 | Gratuit | Prix temps reel sans cle API, rate limit respecte cote client |
| CORS | Flask-CORS | 4.0.0 | Autorise les appels cross-origin (utile pour integration HomeHub) |

### 2.1 Dependances externes

**Fichier** : `/data/projects/crypto-portfolio/requirements.txt`

| Package | Version | Role |
|---------|---------|------|
| Flask | 3.0.0 | Framework web |
| Flask-SQLAlchemy | 3.1.1 | Integration ORM |
| Flask-CORS | 4.0.0 | Gestion CORS |
| SQLAlchemy | 2.0.23 | ORM base de donnees |
| requests | 2.31.0 | Appels HTTP (CoinGecko) |
| python-binance | 1.0.19 | SDK Binance (optionnel, pour import API futur) |
| kucoin-python | 1.0.11 | SDK Kucoin (optionnel, pour import API futur) |
| pandas | 2.1.3 | Parsing CSV avance |
| numpy | 1.26.2 | Calculs numeriques (dependance pandas) |
| reportlab | 4.0.7 | Generation PDF (non utilise actuellement) |
| python-dateutil | 2.8.2 | Parsing de dates multi-formats |
| pytz | 2023.3 | Gestion des fuseaux horaires |
| cryptography | 41.0.7 | Chiffrement (reserve pour stockage cles API futur) |
| pytest | 7.4.3 | Tests (non implementes) |

**API tierce** :
- **CoinGecko API v3** : `https://api.coingecko.com/api/v3` - gratuit, sans cle API, rate limit ~10-30 req/min

**APIs Exchange (optionnel, variables d'environnement)** :
- Binance : `BINANCE_API_KEY`, `BINANCE_API_SECRET`
- Kucoin : `KUCOIN_API_KEY`, `KUCOIN_API_SECRET`, `KUCOIN_API_PASSPHRASE`

---

## 3. Architecture

### 3.1 Vue Contexte (C4 Level 1)

```
[Investisseur] --HTTP--> [Crypto Portfolio Tracker (localhost:5050)]
                              |
                              |--HTTPS--> [CoinGecko API] (prix temps reel)
                              |
                              |--fichier--> [CSV Binance/Kucoin] (import)
```

L'application est 100% locale. Aucune authentification necessaire (single-user). Le seul appel externe est vers CoinGecko pour les prix.

### 3.2 Vue Container (C4 Level 2)

```
[Navigateur Web]
    |
    |--> [Frontend (Jinja2/HTML + JS + Chart.js)]
    |         |
    |         |--> [API REST (/api/*)]  <-- Blueprint Flask
    |                   |
    |                   |--> [Service Portfolio]  -- calcul PMP, P&L, holdings
    |                   |--> [Service Price]      -- cache CoinGecko, rate limiting
    |                   |--> [Service Import]     -- parsing CSV Binance/Kucoin
    |                   |--> [Service Strategy]   -- seuils de sortie, alertes
    |                   |--> [Service Fiscal]     -- algorithme FIFO, rapport
    |                   |
    |                   |--> [SQLAlchemy ORM]
    |                            |
    |                            |--> [SQLite: data/portfolio.db]
    |
    |--> [CoinGecko API v3] (via Service Price)
```

### 3.3 Structure du projet

```
crypto-portfolio/
├── backend/
│   ├── __init__.py
│   ├── app.py                 # Point d'entree Flask, factory create_app()
│   ├── config.py              # Configuration centralisee, CRYPTO_MAPPING
│   ├── api/
│   │   ├── __init__.py        # Blueprint 'api' avec prefix '/api'
│   │   └── routes.py          # 24 endpoints REST
│   ├── models/
│   │   ├── __init__.py        # Exports : db, Crypto, Transaction, etc.
│   │   ├── database.py        # Init SQLAlchemy, PRAGMA FK, seed cryptos
│   │   ├── crypto.py          # Modele Crypto (symbol, coingecko_id)
│   │   ├── transaction.py     # Modele Transaction + enums Type/Exchange
│   │   ├── portfolio.py       # Modele PortfolioSnapshot (JSON details)
│   │   └── strategy.py        # Modeles ExitStrategy + StrategyAlert
│   └── services/
│       ├── __init__.py        # Exports des instances globales
│       ├── portfolio.py       # PortfolioService : holdings, PMP, P&L
│       ├── price.py           # PriceService : cache 60s, rate limit 1.5s
│       ├── import_export.py   # ImportExportService : CSV Binance/Kucoin
│       ├── strategy.py        # StrategyService : seuils, alertes, execution
│       └── fiscal.py          # FiscalService : FIFO, rapport, export CSV
├── frontend/
│   ├── templates/
│   │   ├── base.html          # Layout : sidebar + topbar + modal + toast
│   │   ├── dashboard.html     # Cards resume + graphiques + tableau positions
│   │   ├── transactions.html  # Liste filtrable + ajout manuel
│   │   ├── strategies.html    # Gestion strategies + alertes en attente
│   │   ├── fiscal.html        # Rapport fiscal par annee + export
│   │   ├── import.html        # Upload CSV drag-and-drop
│   │   └── settings.html      # Cles API + preferences + gestion donnees
│   └── static/
│       ├── css/
│       │   └── style.css      # Theme dark, variables CSS, responsive
│       └── js/
│           └── app.js         # Logique client : API calls, Chart.js, modals
├── data/
│   ├── portfolio.db           # Base de donnees SQLite
│   ├── imports/               # Fichiers CSV importes
│   ├── exports/               # Fichiers exportes (CSV, JSON, TXT)
│   └── backups/               # Backups automatiques
├── scripts/
│   └── generate_dummy_data.py # Generation de donnees DCA simulees
├── docs/
│   ├── SPECIFICATIONS.md      # Ancienne spec (remplacee par ce fichier)
│   └── spec/
│       └── SPEC.md            # Cette specification
├── requirements.txt
├── start.sh                   # Lancement venv + serveur + navigateur
└── README.md
```

### 3.4 Flux de donnees

```
Flux 1 - Import CSV :
  [Fichier CSV] → [POST /api/import] → [ImportExportService.detect_format()]
                → [import_binance_csv() | import_kucoin_csv() | import_generic_csv()]
                → [Crypto.get_or_create()] → [Transaction INSERT] → [SQLite]

Flux 2 - Dashboard (chargement) :
  [Browser] → [GET /api/portfolio] → [PortfolioService.get_portfolio_summary()]
           → [get_holdings()] → [Transaction.query.order_by(date)]
           → Calcul PMP par crypto → [PriceService.get_prices()] (CoinGecko)
           → Calcul P&L (current_value - total_cost) → [JSON response]

Flux 3 - Verification strategies :
  [POST /api/strategies/check] → [StrategyService.check_strategies()]
           → Pour chaque strategie active :
               [PortfolioService.get_holdings()] → calcul profit_pct
               → [ExitStrategy.get_triggered_thresholds(profit_pct)]
               → Si seuil franchi : [StrategyAlert INSERT (status=pending)]
           → [JSON: {new_alerts: N}]

Flux 4 - Rapport fiscal :
  [GET /api/fiscal/2025] → [FiscalService.calculate_yearly_gains(2025)]
           → Transaction.query.order_by(date) → grouper par crypto
           → Pour chaque crypto : construire file FIFO (achats)
               → Pour chaque vente dans [start_date, end_date] :
                   Consommer lots FIFO → calculer gain = proceeds - cost_basis - fees
           → [JSON: gains_by_crypto + totals]
```

---

## 4. Modele de Donnees

### 4.1 Schema conceptuel

| Entite | Description | Relations |
|--------|-------------|-----------|
| `Crypto` | Cryptomonnaie (BTC, ETH...) | 1:N → Transaction, 1:N → ExitStrategy |
| `Transaction` | Achat, vente ou transfert | N:1 → Crypto |
| `PortfolioSnapshot` | Photo du portefeuille a un instant T | Independant (pas de FK) |
| `ExitStrategy` | Strategie de sortie pour une crypto | N:1 → Crypto, 1:N → StrategyAlert |
| `StrategyAlert` | Alerte declenchee par un seuil | N:1 → ExitStrategy |

### 4.2 Schema SQL

Les tables sont creees par SQLAlchemy via `db.create_all()` dans `backend/models/database.py`. Voici le schema equivalent en SQL pur, reconstruit a partir des modeles ORM :

```sql
-- ============================================================
-- Table: cryptos
-- Source: backend/models/crypto.py
-- ============================================================
CREATE TABLE IF NOT EXISTS cryptos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    coingecko_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index : recherche rapide par symbole
CREATE UNIQUE INDEX IF NOT EXISTS ix_cryptos_symbol ON cryptos(symbol);

-- Seed initial (16 cryptos communes) via _seed_cryptos() dans database.py
-- INSERT INTO cryptos (symbol, name, coingecko_id) VALUES
--   ('BTC', 'Bitcoin', 'bitcoin'),
--   ('ETH', 'Ethereum', 'ethereum'),
--   ('BNB', 'Binance Coin', 'binancecoin'),
--   ('SOL', 'Solana', 'solana'),
--   ('ADA', 'Cardano', 'cardano'),
--   ('XRP', 'Ripple', 'ripple'),
--   ('DOT', 'Polkadot', 'polkadot'),
--   ('DOGE', 'Dogecoin', 'dogecoin'),
--   ('AVAX', 'Avalanche', 'avalanche-2'),
--   ('MATIC', 'Polygon', 'matic-network'),
--   ('LINK', 'Chainlink', 'chainlink'),
--   ('UNI', 'Uniswap', 'uniswap'),
--   ('ATOM', 'Cosmos', 'cosmos'),
--   ('LTC', 'Litecoin', 'litecoin'),
--   ('ETC', 'Ethereum Classic', 'ethereum-classic'),
--   ('XLM', 'Stellar', 'stellar');

-- ============================================================
-- Table: transactions
-- Source: backend/models/transaction.py
-- ============================================================
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TIMESTAMP NOT NULL,
    type VARCHAR(20) NOT NULL,          -- Valeurs: BUY, SELL, TRANSFER_IN, TRANSFER_OUT,
                                        --          STAKING_REWARD, AIRDROP, FEE
    exchange VARCHAR(20) NOT NULL DEFAULT 'manual',  -- Valeurs: binance, kucoin, manual, other
    crypto_id INTEGER NOT NULL,
    volume FLOAT NOT NULL,              -- Quantite de crypto
    price FLOAT NOT NULL,               -- Prix unitaire en devise de base (EUR)
    total FLOAT NOT NULL,               -- volume * price
    fee FLOAT DEFAULT 0.0,              -- Frais de transaction
    fee_currency VARCHAR(10) DEFAULT 'EUR',
    pair VARCHAR(20),                   -- Paire de trading (ex: BTC/USDT)
    quote_currency VARCHAR(10) DEFAULT 'EUR',
    notes TEXT,
    imported_from VARCHAR(255),         -- Nom du fichier CSV source
    external_id VARCHAR(100),           -- ID unique de l'exchange (deduplication)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (crypto_id) REFERENCES cryptos(id)
);

-- Index : tri chronologique des transactions (utilise partout)
CREATE INDEX IF NOT EXISTS ix_transactions_date ON transactions(date);

-- ============================================================
-- Table: portfolio_snapshots
-- Source: backend/models/portfolio.py
-- ============================================================
CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    total_value FLOAT NOT NULL DEFAULT 0.0,     -- Valorisation totale en EUR
    total_invested FLOAT NOT NULL DEFAULT 0.0,  -- Total investi en EUR
    total_pnl FLOAT NOT NULL DEFAULT 0.0,       -- total_value - total_invested
    total_pnl_pct FLOAT NOT NULL DEFAULT 0.0,   -- (pnl / invested) * 100
    details TEXT,                                -- JSON : {symbol: {volume, price, value, pnl_pct}}
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index : recherche par date pour l'historique
CREATE INDEX IF NOT EXISTS ix_portfolio_snapshots_date ON portfolio_snapshots(date);

-- ============================================================
-- Table: exit_strategies
-- Source: backend/models/strategy.py
-- ============================================================
CREATE TABLE IF NOT EXISTS exit_strategies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    crypto_id INTEGER NOT NULL,
    enabled BOOLEAN DEFAULT 0,
    mode VARCHAR(20) DEFAULT 'alert',    -- Valeurs: alert, semi-auto, auto
    thresholds TEXT,                      -- JSON : [{profit_pct, sell_pct, description}, ...]
    executed_thresholds TEXT,             -- JSON : [20, 50, ...] (profit_pct deja executes)
    capital_recovery_enabled BOOLEAN DEFAULT 1,
    capital_recovery_at_pct FLOAT DEFAULT 100.0,
    capital_recovery_amount_pct FLOAT DEFAULT 100.0,
    capital_recovered BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (crypto_id) REFERENCES cryptos(id)
);

-- ============================================================
-- Table: strategy_alerts
-- Source: backend/models/strategy.py
-- ============================================================
CREATE TABLE IF NOT EXISTS strategy_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_id INTEGER NOT NULL,
    date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    threshold_pct FLOAT NOT NULL,         -- Seuil qui a declenche l'alerte (ex: 100)
    sell_pct FLOAT NOT NULL,              -- % du volume a vendre (ex: 20)
    current_profit_pct FLOAT NOT NULL,    -- Profit reel au moment du declenchement
    current_price FLOAT NOT NULL,         -- Prix au moment du declenchement
    volume_to_sell FLOAT NOT NULL,        -- Volume calcule a vendre
    estimated_value FLOAT NOT NULL,       -- Valeur estimee de la vente
    status VARCHAR(20) DEFAULT 'pending', -- Valeurs: pending, executed, dismissed
    executed_at TIMESTAMP,
    executed_price FLOAT,
    executed_volume FLOAT,
    alert_type VARCHAR(20) DEFAULT 'threshold',  -- Valeurs: threshold, capital_recovery
    notes TEXT,

    FOREIGN KEY (strategy_id) REFERENCES exit_strategies(id) ON DELETE CASCADE
);
```

**Notes sur le schema** :
- SQLite ne supporte pas nativement les triggers `updated_at`. SQLAlchemy gere cette mise a jour via le parametre `onupdate=datetime.utcnow` au niveau Python.
- Les PRAGMA `foreign_keys = ON` sont actives dans `database.py` via un event listener SQLAlchemy.
- Les champs `thresholds`, `executed_thresholds` et `details` stockent du JSON serialise en `TEXT`. Les modeles ORM fournissent des getters/setters Python qui font le `json.loads()`/`json.dumps()` automatiquement.

### 4.3 Migrations

Pas de systeme de migration formel. Le schema est cree automatiquement par `db.create_all()` au demarrage de l'application. Pour les evolutions de schema, la procedure est :

1. Modifier le modele SQLAlchemy
2. Supprimer `data/portfolio.db` (ou backup + drop/recreate)
3. Relancer l'application

Les donnees sont preservees via export CSV/JSON avant migration.

---

## 5. Features (Exigences Fonctionnelles)

### F-001: Dashboard portefeuille (P1)

**User story :** En tant qu'investisseur, je veux voir un resume de mon portefeuille avec valorisation temps reel, afin de suivre ma performance globale.

**Criteres d'acceptation :**
- [x] Affichage de 4 KPIs : valeur totale, total investi, P&L total (EUR + %), nombre de positions
- [x] Graphique doughnut (Chart.js) de la repartition par crypto
- [x] Graphique line (Chart.js) de l'evolution historique avec selecteur de periode (7j, 30j, 90j, 1an, tout)
- [x] Tableau des positions avec colonnes : crypto, volume, PMP, cours actuel, valeur, P&L, P&L %, exchange
- [x] Tri par valorisation decroissante

**Fichiers source :**
- Template : `frontend/templates/dashboard.html`
- Logique JS : `frontend/static/js/app.js` (fonctions `loadDashboard()`, `updateSummaryCards()`, `updateHoldingsTable()`, `updateCharts()`, `loadHistory()`)
- API : `GET /api/portfolio`, `GET /api/holdings`, `GET /api/portfolio/history`
- Service : `backend/services/portfolio.py` (`get_portfolio_summary()`, `get_holdings()`, `get_portfolio_history()`)

**Cas limites :**
- Portefeuille vide : affiche "Aucune position" avec lien vers import
- Prix CoinGecko indisponible : affiche prix = 0 et P&L = "N/A"
- Volume residuel < 0.00000001 apres vente : filtre automatiquement (evite residus de float)

---

### F-002: Import CSV multi-exchanges (P1)

**User story :** En tant qu'investisseur, je veux importer mes transactions depuis Binance et Kucoin via fichier CSV, afin de centraliser mon historique.

**Criteres d'acceptation :**
- [x] Detection automatique du format (Binance vs Kucoin) par analyse des en-tetes CSV
- [x] Import Binance : colonnes `Date(UTC)`, `Pair`, `Side`, `Price`, `Executed`, `Amount`, `Fee`
- [x] Import Kucoin : colonnes `tradeCreatedAt`, `symbol`, `side`, `price`, `size`, `funds`, `fee`
- [x] Import generique : colonnes `Date`, `Type`, `Symbol`, `Volume`, `Price`, `Fee`
- [x] Deduplication via `external_id` (evite les doublons lors de reimports)
- [x] Extraction automatique du symbole depuis la paire de trading (ex: `BTCUSDT` → `BTC`)
- [x] Zone de drag-and-drop pour le fichier

**Fichiers source :**
- Template : `frontend/templates/import.html`
- Logique JS : `frontend/static/js/app.js` (fonction `setupFileUpload()`, `handleFileUpload()`)
- API : `POST /api/import`
- Service : `backend/services/import_export.py` (`ImportExportService`)

**Algorithme de detection** (dans `detect_format()`) :
```python
# Lecture des en-tetes du CSV
# Si 'Date(UTC)' et 'Pair' → format Binance
# Si 'tradeCreatedAt' et 'symbol' → format Kucoin
# Sinon → format generique
```

**Parsing des nombres** (`_parse_number()`) :
- Gere les formats EU (virgule decimale) et US (point decimal)
- Supprime les separateurs de milliers
- Exemples : `"1.234,56"` → `1234.56`, `"1,234.56"` → `1234.56`

**Parsing des dates** (`_parse_date()`) :
- 7+ formats supportes : ISO 8601, `DD/MM/YYYY HH:MM:SS`, `MM/DD/YYYY`, `YYYY-MM-DD HH:MM:SS`, etc.
- Fallback vers `dateutil.parser.parse()` en dernier recours

**Cas limites :**
- Fichier vide ou sans transactions valides : retourne `{imported: 0, errors: [...]}`
- Crypto inconnue dans le CSV : creee automatiquement via `Crypto.get_or_create()`
- Paire avec stablecoin (ex: `BTCUSDT`) : symbole extrait = `BTC`, quote = `USDT`

---

### F-003: Calcul du Prix Moyen Pondere (P1)

**User story :** En tant qu'investisseur, je veux connaitre mon prix d'achat moyen par crypto, afin d'evaluer ma performance par rapport au cours actuel.

**Criteres d'acceptation :**
- [x] PMP recalcule dynamiquement a chaque chargement (pas de stockage)
- [x] Prend en compte les achats (BUY, TRANSFER_IN, STAKING_REWARD, AIRDROP)
- [x] Ajuste le cout proportionnellement lors des ventes (SELL, TRANSFER_OUT)
- [x] Calcul du P&L brut (`current_value - total_cost`) et net (`pnl_brut - total_fees`)

**Fichier source :** `backend/services/portfolio.py` - methode `get_holdings()`

**Algorithme PMP** :
```python
# Pour chaque transaction triee par date ASC :
#   Si achat (is_buy) :
#     volume += tx.volume
#     total_cost += tx.total (volume * price)
#     total_fees += tx.fee
#
#   Si vente (is_sell) :
#     cost_per_unit = total_cost / volume
#     sold_cost = cost_per_unit * tx.volume
#     total_cost -= sold_cost
#     volume -= tx.volume
#
# PMP = total_cost / volume
# P&L brut = (volume * current_price) - total_cost
# P&L net = P&L brut - total_fees
# P&L % = (P&L brut / total_cost) * 100
```

**Cas limites :**
- Volume apres vente = 0 : position filtree du resultat
- Vente superieure au volume detenu : le volume peut devenir negatif (pas de garde-fou dans le code actuel)

---

### F-004: Strategies de sortie (P1)

**User story :** En tant que trader, je veux definir des seuils de profit auxquels vendre progressivement, afin de securiser mes gains sans surveiller le marche en permanence.

**Criteres d'acceptation :**
- [x] 3 modes : `alert` (notification seulement), `semi-auto` (confirmation requise), `auto` (execution automatique)
- [x] Seuils par defaut configurables dans `config.py` : +20%/10%, +50%/15%, +100%/20%, +200%/25%, +500%/30%
- [x] Recuperation du capital : a +100% de profit, possibilite de recuperer 100% du capital investi
- [x] Suivi des seuils deja executes (evite les doublons)
- [x] Verification manuelle via bouton "Verifier les seuils" ou automatique toutes les 5 minutes (cote client)
- [x] Alertes en attente avec options "Executer" (cree une transaction SELL) ou "Ignorer"

**Fichiers source :**
- Template : `frontend/templates/strategies.html`
- Modeles : `backend/models/strategy.py` (`ExitStrategy`, `StrategyAlert`)
- Service : `backend/services/strategy.py` (`StrategyService`)
- API : `GET/POST /api/strategies`, `POST /api/strategies/check`, `GET /api/alerts`, `POST /api/alerts/<id>/execute`, `POST /api/alerts/<id>/dismiss`

**Format des seuils** (JSON stocke dans `exit_strategies.thresholds`) :
```json
[
    {"profit_pct": 20, "sell_pct": 10, "description": "Securiser 10% a +20%"},
    {"profit_pct": 50, "sell_pct": 15, "description": "Vendre 15% a +50%"},
    {"profit_pct": 100, "sell_pct": 20, "description": "Vendre 20% a +100%"},
    {"profit_pct": 200, "sell_pct": 25, "description": "Vendre 25% a +200%"},
    {"profit_pct": 500, "sell_pct": 30, "description": "Vendre 30% a +500%"}
]
```

**Flux de verification** (`check_strategies()`) :
1. Recuperer toutes les strategies actives (`enabled=True`)
2. Pour chaque strategie, calculer le `profit_pct` actuel via le holding correspondant
3. Appeler `get_triggered_thresholds(profit_pct)` : retourne les seuils franchis et non executes
4. Pour chaque seuil franchi, creer un `StrategyAlert` avec `status=pending`
5. Verifier aussi la recuperation du capital si `capital_recovery_enabled=True`

**Execution d'une alerte** (`execute_alert()`) :
1. Recuperer le holding courant pour la crypto
2. Calculer le volume a vendre : `holding.volume * (sell_pct / 100)`
3. Creer une `Transaction` de type `SELL`
4. Marquer l'alerte comme `executed`
5. Marquer le seuil comme execute dans la strategie

---

### F-005: Rapport fiscal FIFO (P1)

**User story :** En tant que declarant, je veux generer un rapport de plus-values pour une annee fiscale, afin de remplir le formulaire 2086.

**Criteres d'acceptation :**
- [x] Methode FIFO (First In, First Out) : les premiers achats sont les premiers vendus
- [x] Calcul par crypto et global : plus-values, moins-values, resultat net
- [x] Detail de chaque cession : date, volume, prix de vente, cout d'acquisition FIFO, frais, gain, duree de detention
- [x] Export CSV avec colonnes normalisees pour la declaration
- [x] Export rapport texte formate
- [x] Les achats anterieurs a l'annee fiscale sont pris en compte dans la file FIFO

**Fichiers source :**
- Template : `frontend/templates/fiscal.html`
- Service : `backend/services/fiscal.py` (`FiscalService`, `FIFOLot`)
- API : `GET /api/fiscal/<year>`, `GET /api/fiscal/<year>/export`

**Algorithme FIFO detaille** (dans `_calculate_crypto_gains()`) :

```python
@dataclass
class FIFOLot:
    date: datetime
    volume: float
    price: float
    fee: float

    def consume(self, volume):
        consumed = min(volume, self.volume)
        cost_basis = consumed * self.price
        fee_portion = (consumed / self.volume) * self.fee if self.volume > 0 else 0
        self.volume -= consumed
        return (consumed, cost_basis, fee_portion)

# Pour chaque crypto :
fifo_queue = []

for tx in transactions_sorted_by_date:
    if tx.is_buy:
        # Empiler dans la file FIFO
        fifo_queue.append(FIFOLot(date=tx.date, volume=tx.volume,
                                   price=tx.price, fee=tx.fee))

    elif tx.is_sell AND start_date <= tx.date <= end_date:
        # Depiler FIFO pour calculer le cout d'acquisition
        volume_to_sell = tx.volume
        cost_basis = 0
        acquisition_fees = 0

        while volume_to_sell > 0 AND fifo_queue non vide:
            lot = fifo_queue[0]
            consumed, lot_cost, lot_fee = lot.consume(volume_to_sell)
            cost_basis += lot_cost
            acquisition_fees += lot_fee
            volume_to_sell -= consumed
            if lot.volume <= 0:
                fifo_queue.pop(0)  # Lot epuise, passer au suivant

        # Calcul du gain
        proceeds = tx.total          # volume * prix de vente
        total_fees = acquisition_fees + tx.fee
        gain = proceeds - cost_basis - total_fees
```

**Duree de detention** : moyenne ponderee par volume des periodes entre chaque lot FIFO consomme et la date de vente.

**Informations fiscales affichees** :
- Flat tax France : 30% sur les plus-values nettes
- Declaration via formulaire 2086
- Obligation de declarer les comptes etrangers (Binance, Kucoin)

---

### F-006: Gestion des transactions (P2)

**User story :** En tant qu'investisseur, je veux voir, ajouter, modifier et supprimer mes transactions, afin de corriger des erreurs ou ajouter des operations manuelles.

**Criteres d'acceptation :**
- [x] Liste paginee avec filtres : type (BUY/SELL), exchange, crypto (recherche texte)
- [x] Ajout manuel via modal : date, type, crypto, volume, prix, frais, exchange, notes
- [x] Modification d'une transaction existante
- [x] Suppression avec confirmation
- [x] Recalcul automatique du total (`volume * price`) a la modification

**Fichiers source :**
- Template : `frontend/templates/transactions.html`
- Logique JS : `frontend/static/js/app.js` (fonctions `loadTransactions()`, `filterTransactions()`, `showAddTransactionModal()`, `updateTransactionsTable()`)
- API : `GET /api/transactions`, `POST /api/transactions`, `PUT /api/transactions/<id>`, `DELETE /api/transactions/<id>`
- Service : `backend/services/portfolio.py` (`get_transactions()`, `add_transaction()`, `update_transaction()`, `delete_transaction()`)

---

### F-007: Export des donnees (P2)

**User story :** En tant qu'investisseur, je veux exporter mes transactions et rapports, afin de les sauvegarder ou les partager avec un comptable.

**Criteres d'acceptation :**
- [x] Export transactions en CSV
- [x] Export transactions en JSON
- [x] Export fiscal en CSV (colonnes normalisees declaration)
- [x] Export fiscal en texte formate

**Fichiers source :**
- Service : `backend/services/import_export.py` (`export_transactions_csv()`, `export_transactions_json()`)
- Service : `backend/services/fiscal.py` (`export_fiscal_csv()`, `generate_fiscal_report()`)
- API : `GET /api/export/transactions?format=csv|json`, `GET /api/fiscal/<year>/export?format=csv|text`

---

### F-008: Prix temps reel CoinGecko (P1)

**User story :** En tant qu'investisseur, je veux que les prix soient mis a jour automatiquement, afin de voir la valorisation actuelle de mon portefeuille.

**Criteres d'acceptation :**
- [x] Requetes batch : une seule requete CoinGecko pour tous les symboles (endpoint `/simple/price`)
- [x] Cache en memoire avec TTL de 60 secondes
- [x] Rate limiting client : minimum 1.5 secondes entre deux requetes
- [x] Changement 24h inclus dans la reponse (`include_24hr_change=true`)
- [x] Prix historique via `/coins/{id}/history` (pour recalculs)
- [x] Market chart via `/coins/{id}/market_chart` (pour graphiques)
- [x] Mapping 60+ symboles vers CoinGecko IDs dans `config.py`

**Fichier source :** `backend/services/price.py` (`PriceService`)

**Gestion du cache** :
```python
# Structure du cache (en memoire, dict Python)
_cache = {
    "BTC_eur": {
        "price": 45000.0,
        "change_24h": 2.5,
        "timestamp": 1710000000.0  # time.time()
    }
}
# Validite : time.time() - timestamp < 60 secondes
```

**Rate limiting** :
```python
def _rate_limit(self):
    elapsed = time.time() - self._last_request_time
    if elapsed < 1.5:
        time.sleep(1.5 - elapsed)
    self._last_request_time = time.time()
```

**Cas limites :**
- Symbole absent du mapping : retourne `None`, affiche "Warning" dans les logs
- CoinGecko indisponible (timeout 10s) : retourne `None`, utilise le dernier cache si disponible
- Stablecoins (USDT, USDC) : inclus dans le mapping, prix ~1 EUR

---

### F-009: Parametres et configuration (P3)

**User story :** En tant qu'utilisateur, je veux configurer mes preferences (devise, methode fiscale, cles API), afin de personnaliser l'application.

**Criteres d'acceptation :**
- [x] Stockage des preferences en `localStorage` cote client (devise, methode fiscale, intervalle prix)
- [x] Stockage des cles API en `localStorage` (note : non securise, prevu pour migration serveur)
- [x] Section "Danger Zone" : suppression de toutes les donnees (non implemente)
- [x] Export/import de sauvegarde (export JSON fonctionnel, import non implemente)

**Fichier source :** `frontend/templates/settings.html`

**Limites connues :**
- Les preferences ne sont pas persistees cote serveur
- Les cles API stockees en `localStorage` ne sont pas securisees
- La suppression globale et l'import de sauvegarde ne sont pas implementes

---

## 6. API / Interfaces

### 6.1 Endpoints REST

Tous les endpoints sont prefixes par `/api` via le Blueprint Flask defini dans `backend/api/__init__.py`.
Les reponses suivent le format standard JSON. Pas d'authentification (application locale).

**Fichier source :** `backend/api/routes.py`

---

#### Portfolio

##### `GET /api/portfolio`
**Description :** Resume global du portefeuille
**Reponse 200 :**
```json
{
    "total_value": 15000.00,
    "total_invested": 10000.00,
    "total_fees": 150.00,
    "total_pnl_brut": 5000.00,
    "total_pnl_net": 4850.00,
    "total_pnl_pct": 50.00,
    "holdings_count": 8,
    "exchanges_allocation": {"binance": 10000.0, "kucoin": 5000.0},
    "crypto_allocation": [
        {"symbol": "BTC", "value": 8000.0, "pct": 53.33}
    ],
    "last_updated": "2026-03-13T12:00:00"
}
```

##### `GET /api/holdings`
**Description :** Positions detaillees (toutes les cryptos avec volume > 0)
**Reponse 200 :** Liste de holdings :
```json
[
    {
        "crypto_id": 1,
        "symbol": "BTC",
        "name": "Bitcoin",
        "volume": 0.5,
        "pmp": 30000.00,
        "current_price": 45000.00,
        "total_invested": 15000.00,
        "total_fees": 50.00,
        "current_value": 22500.00,
        "pnl_brut": 7500.00,
        "pnl_net": 7450.00,
        "pnl_pct": 50.00,
        "change_24h": 2.5,
        "first_buy_date": "2024-01-15T10:00:00",
        "exchanges": ["binance"],
        "transactions_count": 12
    }
]
```

##### `GET /api/holdings/<symbol>`
**Description :** Detail d'une position avec historique des transactions

##### `GET /api/portfolio/history?days=30`
**Description :** Historique des snapshots du portefeuille
**Parametres query :**
| Param | Type | Requis | Description |
|-------|------|--------|-------------|
| days | int | Non | Nombre de jours (defaut: 30) |

##### `POST /api/portfolio/snapshot`
**Description :** Cree un snapshot du portefeuille actuel

---

#### Transactions

##### `GET /api/transactions`
**Parametres query :**
| Param | Type | Requis | Description |
|-------|------|--------|-------------|
| crypto_id | int | Non | Filtrer par crypto |
| exchange | str | Non | Filtrer par exchange |
| type | str | Non | Filtrer par type (BUY, SELL) |
| limit | int | Non | Nombre de resultats (defaut: 100) |
| offset | int | Non | Offset pour pagination (defaut: 0) |

**Reponse 200 :**
```json
{
    "transactions": [
        {
            "id": 1,
            "date": "2024-01-15T10:00:00",
            "type": "BUY",
            "exchange": "binance",
            "crypto_id": 1,
            "crypto_symbol": "BTC",
            "volume": 0.5,
            "price": 40000.0,
            "total": 20000.0,
            "fee": 10.0,
            "fee_currency": "EUR",
            "pair": "BTCEUR",
            "quote_currency": "EUR",
            "notes": null,
            "imported_from": "binance_export.csv",
            "created_at": "2024-01-15T10:00:00"
        }
    ],
    "total": 150,
    "limit": 100,
    "offset": 0
}
```

##### `POST /api/transactions`
**Body :**
```json
{
    "symbol": "BTC",
    "type": "BUY",
    "date": "2024-01-15T10:00:00",
    "volume": 0.5,
    "price": 40000,
    "fee": 10,
    "exchange": "binance",
    "notes": "Achat DCA"
}
```
**Reponse 201 :** Transaction creee (format `to_dict()`)

##### `PUT /api/transactions/<id>`
**Body :** Champs a modifier (meme format que POST, tous optionnels)
**Reponse 200 :** Transaction mise a jour

##### `DELETE /api/transactions/<id>`
**Reponse 200 :** `{"ok": true, "message": "Transaction supprimee"}`

---

#### Prix

##### `GET /api/prices`
**Description :** Prix actuels de toutes les cryptos en portefeuille
**Reponse 200 :** `{"BTC": 45000.0, "ETH": 3000.0, ...}`

##### `GET /api/prices/<symbol>`
**Description :** Prix d'une crypto specifique
**Reponse 200 :** `{"symbol": "BTC", "price": 45000.0, "change_24h": 2.5}`

---

#### Import / Export

##### `POST /api/import`
**Content-Type :** `multipart/form-data`
**Body :**
| Champ | Type | Requis | Description |
|-------|------|--------|-------------|
| file | File | Oui | Fichier CSV |
| source | str | Non | `auto`, `binance`, `kucoin`, `manual` (defaut: auto) |

**Reponse 200 :**
```json
{
    "ok": true,
    "imported": 42,
    "duplicates": 3,
    "errors": ["Ligne 15: format de date invalide"],
    "source": "binance"
}
```

##### `GET /api/export/transactions`
**Parametres query :**
| Param | Type | Requis | Description |
|-------|------|--------|-------------|
| format | str | Non | `csv` ou `json` (defaut: csv) |

**Reponse :** Fichier telecharge (`Content-Disposition: attachment`)

---

#### Strategies

##### `GET /api/strategies`
**Description :** Liste de toutes les strategies de sortie
**Reponse 200 :** Liste de strategies (format `ExitStrategy.to_dict()`)

##### `POST /api/strategies`
**Body :**
```json
{
    "symbol": "BTC",
    "mode": "alert",
    "enabled": true
}
```
**Note :** Les seuils par defaut de `config.DEFAULT_EXIT_STRATEGY` sont appliques automatiquement.

##### `PUT /api/strategies/<id>`
**Body :** Champs a modifier (enabled, mode, thresholds)

##### `DELETE /api/strategies/<id>`

##### `POST /api/strategies/check`
**Description :** Verifie tous les seuils et cree des alertes si necessaire
**Reponse 200 :** `{"checked": 5, "new_alerts": 2}`

---

#### Alertes

##### `GET /api/alerts`
**Description :** Alertes en attente (`status=pending`)

##### `POST /api/alerts/<id>/execute`
**Description :** Execute l'alerte (cree une transaction SELL)

##### `POST /api/alerts/<id>/dismiss`
**Description :** Ignore l'alerte

---

#### Fiscal

##### `GET /api/fiscal/<year>`
**Description :** Rapport fiscal pour une annee
**Reponse 200 :**
```json
{
    "year": 2025,
    "start_date": "2025-01-01T00:00:00",
    "end_date": "2025-12-31T23:59:59",
    "total_gains": 5000.00,
    "total_losses": 1200.00,
    "net_gain": 3800.00,
    "sales_count": 15,
    "taxable_amount": 3800.00,
    "reportable_loss": 0,
    "gains_by_crypto": {
        "BTC": {
            "symbol": "BTC",
            "sales": [
                {
                    "date": "2025-06-15T10:00:00",
                    "volume": 0.1,
                    "sale_price": 50000.0,
                    "proceeds": 5000.0,
                    "cost_basis": 3000.0,
                    "total_fees": 15.0,
                    "gain": 1985.0,
                    "gain_pct": 66.17,
                    "holding_period_days": 150,
                    "acquisition_details": [...]
                }
            ],
            "summary": {
                "total_volume_sold": 0.1,
                "total_proceeds": 5000.0,
                "total_cost_basis": 3000.0,
                "total_fees": 15.0,
                "total_gain": 1985.0
            }
        }
    }
}
```

##### `GET /api/fiscal/<year>/export`
**Parametres query :**
| Param | Type | Requis | Description |
|-------|------|--------|-------------|
| format | str | Non | `csv` ou `text` (defaut: csv) |

---

#### Cryptos

##### `GET /api/cryptos`
**Description :** Liste de toutes les cryptos enregistrees

##### `POST /api/cryptos`
**Body :** `{"symbol": "NEW", "name": "New Coin", "coingecko_id": "new-coin"}`

---

### 6.2 Routes Frontend

Definies dans `backend/app.py`, servent les templates Jinja2 :

| Route | Template | Description |
|-------|----------|-------------|
| `/` | `dashboard.html` | Dashboard principal |
| `/transactions` | `transactions.html` | Liste des transactions |
| `/strategies` | `strategies.html` | Gestion des strategies |
| `/fiscal` | `fiscal.html` | Rapport fiscal |
| `/import` | `import.html` | Import de fichiers CSV |
| `/settings` | `settings.html` | Parametres |

### 6.3 Interface CLI

Le projet propose une interface CLI pour consulter et gerer le portefeuille depuis le terminal, sans lancer le serveur web.

**Fichier source** : `cli.py`

**Commandes disponibles** :

| Commande | Description | Arguments | Options |
|----------|-------------|-----------|---------|
| `holdings` | Affiche les positions du portefeuille avec PMP, prix, valeur, P&L | - | `--json` : sortie JSON brute |
| `prices` | Affiche les prix actuels des cryptos | `[symbols...]` : symboles (ex: BTC ETH). Si vide, affiche les holdings | - |
| `stats` | Statistiques du portefeuille (nb actifs, valeur totale, P&L, top 3) | - | - |
| `fiscal` | Rapport fiscal des plus-values (FIFO) | - | `--year YYYY` : annee fiscale (defaut: toutes) |
| `export` | Exporte les transactions vers fichier | - | `--format csv\|json` (defaut: csv) |
| `import` | Importe des transactions depuis fichier CSV | `file` : chemin du fichier | `--exchange binance\|kucoin\|generic` (defaut: generic) |

**Exemples d'utilisation** :

```bash
# Afficher les positions
python3 cli.py holdings

# Afficher les prix BTC et ETH
python3 cli.py prices BTC ETH

# Statistiques du portefeuille
python3 cli.py stats

# Rapport fiscal pour 2025
python3 cli.py fiscal --year 2025

# Exporter les transactions en CSV
python3 cli.py export --format csv

# Importer depuis un fichier Binance
python3 cli.py import transactions.csv --exchange binance

# Lancement serveur web (voir section 8.4)
./start.sh
```

---

## 7. Exigences Non-Fonctionnelles

### 7.1 Performance

| Metrique | Cible | Mesure |
|----------|-------|--------|
| Temps de reponse API (portfolio) | < 500ms | Hors temps CoinGecko |
| Temps de reponse API (transactions) | < 200ms | Requete SQLite paginee |
| Cache prix CoinGecko | 60s TTL | Evite les appels redondants |
| Rate limiting CoinGecko | 1.5s min entre requetes | Respecte les limites API gratuites |
| Import CSV | < 5s pour 1000 lignes | Avec deduplication |

### 7.2 Securite

- **Authentification** : Aucune (application locale, single-user)
- **Validation des entrees** : Basique (conversion de types dans les routes Flask)
- **Donnees sensibles** : Cles API exchanges stockees en `localStorage` (non securise - a migrer serveur)
- **CORS** : Active via Flask-CORS (permissif, car usage local)
- **Secret key Flask** : Valeur par defaut `dev-secret-key-change-in-production` (acceptable pour usage local)

### 7.3 Fiabilite

- **Backup automatique** : Repertoire `data/backups/` prevu mais pas de backup automatise implemente
- **Gestion d'erreurs** : Error handlers Flask pour 404 et 500 (retournent JSON pour les appels API, HTML sinon)
- **Recovery** : En cas de crash, relancer `./start.sh`. Les donnees SQLite persistent.
- **PRAGMA foreign_keys** : Active pour garantir l'integrite referentielle

### 7.4 Interface utilisateur

- **Theme** : Dark mode exclusif (variables CSS dans `:root`)
- **Responsive** : Media queries pour 600px, 768px et 1200px (grilles adaptatives)
- **Composants UI** : Systeme modal, toast notifications, spinner de chargement, badges colores, progress bars
- **Palette** : `--primary: #3b82f6`, `--success: #22c55e`, `--danger: #ef4444`, `--warning: #f59e0b`
- **Layout** : Sidebar fixe 240px + content area avec topbar sticky 60px
- **Police** : Segoe UI / -apple-system / BlinkMacSystemFont

**Fichier source :** `frontend/static/css/style.css` (703 lignes)

### 7.5 Limites connues

- **Pas d'authentification** : application prevue pour un usage local uniquement
- **Pas de migration de schema** : evolution de la DB necessite une recreation
- **Pas de tests automatises** : pytest dans les dependances mais aucun test ecrit
- **Pas de websocket** : les prix ne se mettent pas a jour en temps reel sans action utilisateur
- **Methodes fiscales alternatives** : LIFO et PMP ne sont pas implementes (selecteur desactive dans l'UI)
- **Import API automatique** : les SDKs Binance et Kucoin sont installes mais l'import via API n'est pas implemente
- **Backup automatique** : le repertoire existe mais aucun mecanisme n'est code
- **Suppression globale des donnees** : bouton present dans l'UI mais fonctionnalite non implementee
- **Cache en memoire** : perdu a chaque redemarrage du serveur (pas de persistence Redis/fichier)

---

## 8. Deploiement & Configuration

### 8.1 Prerequis

- Python 3.8+
- pip
- Acces reseau vers `api.coingecko.com` (pour les prix)

### 8.2 Installation

```bash
cd /data/projects/crypto-portfolio

# Option 1 : Script automatique (recommande)
./start.sh

# Option 2 : Installation manuelle
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
mkdir -p data/imports data/exports data/backups
```

### 8.3 Variables d'environnement

| Variable | Description | Requis | Defaut |
|----------|-------------|--------|--------|
| `FLASK_DEBUG` | Active le mode debug Flask | Non | `1` |
| `SECRET_KEY` | Cle secrete Flask pour les sessions | Non | `dev-secret-key-change-in-production` |
| `BINANCE_API_KEY` | Cle API Binance (lecture seule) | Non | `` (vide) |
| `BINANCE_API_SECRET` | Secret API Binance | Non | `` (vide) |
| `KUCOIN_API_KEY` | Cle API Kucoin | Non | `` (vide) |
| `KUCOIN_API_SECRET` | Secret API Kucoin | Non | `` (vide) |
| `KUCOIN_API_PASSPHRASE` | Passphrase API Kucoin | Non | `` (vide) |

**Fichier source :** `backend/config.py`

### 8.4 Lancement

```bash
# Developpement (mode recommande)
cd /data/projects/crypto-portfolio
./start.sh
# → Lance venv + serveur + ouvre Firefox sur http://localhost:5050

# Lancement serveur seul (sans navigateur)
source venv/bin/activate
python3 backend/app.py
# → Serveur Flask sur http://0.0.0.0:5050
```

**Script `start.sh`** :
1. `cd` vers le repertoire du projet
2. Cree le venv Python si inexistant
3. Active le venv
4. Installe les dependances si `venv/.installed` n'existe pas
5. Cree les repertoires `data/` si inexistants
6. Lance `python3 backend/app.py` en arriere-plan
7. Attend 4 secondes puis ouvre le navigateur via `gio open`
8. `wait` sur le PID du serveur (Ctrl+C pour arreter)

### 8.5 Port reseau

- **Port** : 5050 (enregistre dans `/data/projects/infrastructure/data/port_registry.json`)
- **Bind** : `0.0.0.0` (accessible depuis le reseau local)

### 8.6 Base de donnees

- **Emplacement** : `data/portfolio.db`
- **Creation** : Automatique au premier lancement (`db.create_all()`)
- **Seed** : 16 cryptos communes inserees automatiquement (`_seed_cryptos()` dans `database.py`)
- **Backup** : `cp data/portfolio.db data/backups/portfolio.db.$(date +%Y%m%d_%H%M%S).bak`
- **Restore** : `cp data/backups/portfolio.db.TIMESTAMP.bak data/portfolio.db`

---

## 9. Glossaire

| Terme | Definition |
|-------|-----------|
| **PMP** | Prix Moyen Pondere. Cout moyen d'acquisition d'une crypto, recalcule a chaque achat et ajuste proportionnellement a chaque vente. |
| **P&L** | Profit and Loss. Difference entre la valeur actuelle et le cout d'acquisition. Brut = sans frais, Net = avec frais. |
| **FIFO** | First In, First Out. Methode de valorisation fiscale ou les premiers achats sont consideres comme les premiers vendus. |
| **Holding** | Position active sur une crypto (volume > 0). |
| **Snapshot** | Photo de l'etat du portefeuille a un instant T, stockee pour l'historique. |
| **Seuil de sortie** | Pourcentage de profit a partir duquel une alerte est declenchee pour vendre une partie de la position. |
| **Capital recovery** | Mecanisme de recuperation du capital investi initial quand le profit atteint +100%. |
| **FIFOLot** | Dataclass Python representant un lot d'achat dans la file FIFO, avec volume, prix et frais. Consomme progressivement lors des ventes. |
| **CoinGecko ID** | Identifiant unique d'une crypto dans l'API CoinGecko (ex: `bitcoin`, `ethereum`). Mappe depuis le symbole via `CRYPTO_MAPPING` dans `config.py`. |
| **Flat tax** | Prelevement forfaitaire unique de 30% en France sur les plus-values d'actifs numeriques. |
| **Formulaire 2086** | Formulaire fiscal francais pour la declaration des cessions d'actifs numeriques. |
| **DCA** | Dollar Cost Averaging. Strategie d'investissement regulier (ex: 1000EUR/mois) pour lisser le prix d'entree. |

---

## Annexes

### A. Decisions architecturales (ADRs)

**ADR-001 : SQLAlchemy ORM plutot que SQL brut**
- Contexte : Besoin de manipuler 5 tables avec relations FK et serialisation JSON
- Decision : SQLAlchemy avec Flask-SQLAlchemy pour l'integration Flask
- Consequence : Pas de migrations SQL formelles, schema gere par `db.create_all()`

**ADR-002 : Cache en memoire plutot que Redis**
- Contexte : Les prix CoinGecko doivent etre caches pour eviter le rate limiting
- Decision : Dict Python en memoire avec TTL de 60s
- Consequence : Cache perdu au redemarrage, mais acceptable pour une app locale

**ADR-003 : JavaScript vanilla plutot que React/Vue**
- Contexte : Application single-user locale, 6 pages
- Decision : JS vanilla avec Chart.js pour les graphiques
- Consequence : Code plus simple, pas de build step, mais logique dupliquee entre pages

**ADR-004 : Stockage JSON en TEXT plutot que tables normalisees**
- Contexte : Les seuils de strategies et details de snapshots sont des structures flexibles
- Decision : Serialisation JSON dans des colonnes TEXT avec getters/setters Python
- Consequence : Pas de requetes SQL sur les sous-champs, mais flexibilite du schema

### B. CRYPTO_MAPPING complet

Le fichier `backend/config.py` contient un mapping de 60+ symboles vers les identifiants CoinGecko :

```
BTC→bitcoin, ETH→ethereum, BNB→binancecoin, SOL→solana, ADA→cardano,
XRP→ripple, DOT→polkadot, DOGE→dogecoin, AVAX→avalanche-2,
MATIC→matic-network, LINK→chainlink, UNI→uniswap, ATOM→cosmos,
LTC→litecoin, ETC→ethereum-classic, XLM→stellar, ALGO→algorand,
VET→vechain, FTM→fantom, NEAR→near, AAVE→aave, GRT→the-graph,
FIL→filecoin, SAND→the-sandbox, MANA→decentraland, AXS→axie-infinity,
THETA→theta-token, XTZ→tezos, EGLD→elrond-erd-2, EOS→eos,
CAKE→pancakeswap-token, RUNE→thorchain, ZEC→zcash, KAVA→kava,
AR→arweave, FLOW→flow, XMR→monero, NEO→neo, WAVES→waves, DASH→dash,
MKR→maker, COMP→compound-governance-token, SNX→havven,
YFI→yearn-finance, SUSHI→sushi, CRV→curve-dao-token, 1INCH→1inch,
BAT→basic-attention-token, ENJ→enjincoin, CHZ→chiliz, GALA→gala,
APE→apecoin, LDO→lido-dao, OP→optimism, ARB→arbitrum, SUI→sui,
SEI→sei-network, TIA→celestia, INJ→injective-protocol, PEPE→pepe,
SHIB→shiba-inu, FLOKI→floki, WIF→dogwifcoin, BONK→bonk,
HYPE→hyperliquid, USDT→tether, USDC→usd-coin, DAI→dai,
BUSD→binance-usd
```

Pour ajouter une nouvelle crypto au mapping, ajouter une entree dans le dictionnaire `CRYPTO_MAPPING` de `backend/config.py`.

### C. Historique des versions

| Version | Date | Changements |
|---------|------|-------------|
| 1.0 | 2026-03-13 | Creation initiale de cette specification (remplacement de SPECIFICATIONS.md) |
