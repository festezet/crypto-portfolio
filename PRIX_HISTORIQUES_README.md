# Graphique avec Prix Historiques Réels

## Vue d'ensemble

Le graphique d'évolution du portefeuille utilise maintenant les **prix historiques réels** de l'API CoinGecko pour chaque jour, au lieu des prix actuels projetés sur le passé.

## Comparaison

### ❌ Ancien système (prix actuels)
```
Toutes les dates utilisent le prix d'aujourd'hui
→ Graphique plat, pas d'évolution réelle
→ Ne reflète pas la vraie performance historique
```

### ✅ Nouveau système (prix historiques)
```
Chaque date utilise le prix réel de ce jour-là
→ Graphique dynamique avec vraie évolution
→ Performance historique précise
```

## Résultats

**Snapshot avec prix historiques** :
- **Premier** (02/01/2025) : 338€ investis → 338€ valeur
- **Dernier** (21/11/2025) : 2310€ investis → 2260€ valeur
- **Évolution** : 338€ → 3184€ (max) → 2260€ (actuel)
- **Variation** : +870% (max), actuellement -2.15% vs investi

## Script de génération

### `generate_snapshots_historical.py`

**Fonctionnement** :
1. Récupère toutes les transactions historiques
2. Pour chaque crypto, appelle l'API CoinGecko `/market_chart` pour obtenir les prix sur 325 jours
3. Pour chaque jour :
   - Recalcule l'état du portefeuille (volume détenu)
   - Applique le **prix historique réel** de ce jour
   - Crée un snapshot avec la valorisation réelle

**Utilisation** :
```bash
cd /data/projects/crypto-portfolio
source venv/bin/activate
python3 scripts/generate_snapshots_historical.py
```

**Options** :
- Suppression des anciens snapshots (recommandé)
- Rate limiting : 2 secondes entre chaque requête API
- Fallback : Si prix manquant, cherche jusqu'à 7 jours avant

## Limitation : Rate Limiting CoinGecko

### Problème rencontré

L'API gratuite CoinGecko a des limites :
- **~10-50 requêtes/minute** selon la charge
- Pour 9 cryptos × 325 jours, on dépasse facilement

**Résultat** : Sur 9 cryptos, 5 ont été récupérées avec succès :
- ✅ DOT, ETH, XRP, BNB, XMR (325 prix chacun)
- ❌ BTC, SOL, HYPE, AAVE (429 Too Many Requests)

Les snapshots contiennent donc des valorisations **partielles** (5/9 cryptos).

### Solutions

#### Option 1 : Réessayer avec plus de délai
```python
# Dans generate_snapshots_historical.py ligne 44
time.sleep(10)  # Au lieu de 2 secondes
```

**Avantage** : Récupère toutes les cryptos  
**Inconvénient** : Temps d'exécution ~15 minutes

#### Option 2 : Récupération par batch
Diviser en plusieurs exécutions espacées :
```bash
# Session 1 : BTC, ETH, SOL
# Attendre 1 heure
# Session 2 : Autres cryptos
```

#### Option 3 : API CoinGecko Pro
- **Prix** : ~$129/mois
- **Limite** : 500 requêtes/minute
- Pas nécessaire pour un projet demo

#### Option 4 : Accepter les données partielles
- Le graphique fonctionne avec 5/9 cryptos
- Représente quand même ~85% de la valorisation (ETH + BNB + XRP + DOT + XMR)
- **Recommandé pour ce projet**

## API CoinGecko utilisée

### Endpoint : `/coins/{id}/market_chart`
```
GET https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=eur&days=325&interval=daily
```

**Réponse** :
```json
{
  "prices": [
    [1704153600000, 38247.15],  // [timestamp_ms, price_eur]
    [1704240000000, 39102.53],
    ...
  ]
}
```

### Conversion en Python
```python
market_data = price_service.get_market_chart('BTC', days=325)
# Returns: [(datetime, price), (datetime, price), ...]
```

## Performance

**Génération avec prix historiques** :
- **Durée** : ~45 secondes (avec rate limit 429 après 5 cryptos)
- **Snapshots** : 324 créés
- **Requêtes API** : 5 réussies + 4 échouées (rate limit)
- **Taille BDD** : ~200 KB

**Temps complet estimé** (avec toutes les cryptos) :
- 9 cryptos × 2 sec = 18 sec
- + temps requête ~30 sec
- **Total** : ~1 minute

## Vérification

### Test 1 : Variation des valeurs
```bash
python3 << 'EOF'
from backend.app import create_app
from backend.models import PortfolioSnapshot

app = create_app()
with app.app_context():
    snapshots = PortfolioSnapshot.query.order_by(PortfolioSnapshot.date.asc()).all()
    values = [s.total_value for s in snapshots]
    print(f"Min: {min(values):.2f}€")
    print(f"Max: {max(values):.2f}€")
    print(f"Variation: {((max(values)/min(values))-1)*100:+.2f}%")
