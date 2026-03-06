# Graphique Évolution Historique - Documentation

## Vue d'ensemble

Le graphique d'évolution historique affiche la valorisation du portefeuille crypto dans le temps avec deux courbes :
- **Valeur totale** (bleue, zone remplie) : Valorisation actuelle du portefeuille
- **Total investi** (grise, pointillés) : Capital investi cumulé

![Graphique Historique](docs/screenshot_history_chart.png)

## Fonctionnalités

### Sélecteur de période
- **7j** : Derniers 7 jours
- **30j** : Dernier mois (par défaut)
- **90j** : 3 derniers mois
- **1an** : Dernière année
- **Tout** : Depuis la première transaction

### Interactivité
- **Hover** : Affiche tooltip avec date et montants EUR
- **Responsive** : S'adapte à la taille de l'écran
- **Animation** : Transition fluide lors du changement de période

## Architecture technique

### Backend

#### Modèle `PortfolioSnapshot`
```python
class PortfolioSnapshot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False)
    total_value = db.Column(db.Float, nullable=False)
    total_invested = db.Column(db.Float, nullable=False)
    total_pnl = db.Column(db.Float, nullable=False)
    total_pnl_pct = db.Column(db.Float, nullable=False)
    details = db.Column(db.Text, nullable=True)  # JSON
```

#### Endpoint API
```
GET /api/portfolio/history?days=30
```

**Réponse** :
```json
[
  {
    "id": 1,
    "date": "2025-01-01T23:59:59",
    "total_value": 7000.50,
    "total_invested": 7000.00,
    "total_pnl": 0.50,
    "total_pnl_pct": 0.007,
    "details": { ... }
  },
  ...
]
```

#### Service
```python
def get_portfolio_history(self, days: int = 30) -> List[Dict]:
    """Récupère les snapshots depuis X jours"""
    from_date = datetime.utcnow() - timedelta(days=days)
    snapshots = PortfolioSnapshot.query.filter(
        PortfolioSnapshot.date >= from_date
    ).order_by(PortfolioSnapshot.date.asc()).all()
    return [s.to_dict() for s in snapshots]
```

### Frontend

#### HTML (dashboard.html)
```html
<div class="card">
    <div class="card-header">
        <h3 class="card-title">Évolution du portefeuille</h3>
        <div class="period-selector">
            <button class="period-btn active" onclick="loadHistory(7)">7j</button>
            <button class="period-btn" onclick="loadHistory(30)">30j</button>
            <button class="period-btn" onclick="loadHistory(90)">90j</button>
            <button class="period-btn" onclick="loadHistory(365)">1an</button>
            <button class="period-btn" onclick="loadHistory('all')">Tout</button>
        </div>
    </div>
    <div class="chart-container" style="height: 300px;">
        <canvas id="history-chart"></canvas>
    </div>
</div>
```

#### JavaScript (app.js)
```javascript
async function loadHistory(period = 30) {
    const endpoint = period === 'all'
        ? '/portfolio/history?days=9999'
        : `/portfolio/history?days=${period}`;
    
    const history = await apiCall(endpoint);
    
    historyChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: history.map(s => formatDate(s.date)),
            datasets: [
                {
                    label: 'Valeur totale',
                    data: history.map(s => s.total_value),
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    fill: true
                },
                {
                    label: 'Total investi',
                    data: history.map(s => s.total_invested),
                    borderColor: '#64748b',
                    borderDash: [5, 5],
                    fill: false
                }
            ]
        },
        options: { ... }
    });
}
```

#### CSS (style.css)
```css
.period-selector {
    display: flex;
    gap: 8px;
}

.period-btn {
    padding: 6px 12px;
    background-color: transparent;
    border: 1px solid var(--border-color);
    cursor: pointer;
    transition: all 0.2s ease;
}

.period-btn.active {
    background-color: var(--primary);
    color: white;
}
```

## Génération des snapshots

### Script automatique
```bash
cd /data/projects/crypto-portfolio
source venv/bin/activate
python3 scripts/generate_snapshots.py
```

### Logique du script
1. Récupère la date de première et dernière transaction
2. Boucle jour par jour
3. Pour chaque jour :
   - Recalcule l'état du portefeuille à cette date
   - Récupère les prix actuels (limitation API CoinGecko)
   - Crée un snapshot avec valorisation
4. Skip les snapshots existants

### Cron pour mise à jour quotidienne (optionnel)
```bash
# Ajouter à crontab
0 0 * * * cd /data/projects/crypto-portfolio && source venv/bin/activate && python3 scripts/generate_snapshots.py
```

## Performances

- **Snapshots actuels** : 325 (1/jour depuis janvier 2025)
- **Taille BDD** : ~150 KB pour 325 snapshots
- **Requête API** : ~50ms pour 30 jours
- **Rendu Chart.js** : ~100ms

## Améliorations futures

### Priorité haute
- [ ] Utiliser API historique CoinGecko pour prix réels du passé
- [ ] Snapshot automatique via cron quotidien
- [ ] Cache côté frontend (éviter recharger à chaque changement de période)

### Priorité moyenne
- [ ] Export historique en CSV
- [ ] Graphique par crypto individuelle
- [ ] Comparaison avec BTC/ETH (performance relative)
- [ ] Annotations d'événements (achats importants, ventes)

### Priorité basse
- [ ] Zoom sur période personnalisée
- [ ] Multi-monnaie (USD, BTC)
- [ ] Graphique candlestick pour volatilité

## Tests

### Test endpoint
```bash
curl -s http://localhost:5050/api/portfolio/history?days=7 | python3 -m json.tool
```

### Test génération snapshots
```bash
python3 scripts/generate_snapshots.py
# Sortie attendue : "✅ Génération terminée ! ✨ Créés : X"
```

### Test visuel
```bash
firefox http://localhost:5050
# Vérifier :
# - Graphique s'affiche correctement
# - Boutons de période fonctionnent
# - Tooltip affiche montants EUR
# - Responsive (redimensionner fenêtre)
```

## Troubleshooting

### Graphique ne s'affiche pas
1. Vérifier console navigateur (F12)
2. Tester endpoint API : `curl http://localhost:5050/api/portfolio/history?days=30`
3. Vérifier snapshots en BDD : `python3 -c "from backend.models import PortfolioSnapshot; print(PortfolioSnapshot.query.count())"`

### Snapshots vides
```bash
cd /data/projects/crypto-portfolio
source venv/bin/activate
python3 scripts/generate_snapshots.py
```

### Erreur "No snapshots"
- Importer d'abord des transactions via `/import`
- Générer les snapshots avec le script

---

**Auteur** : Claude Code  
**Date** : 2025-11-21  
**Version** : 1.0
