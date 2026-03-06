# Changelog - Crypto Portfolio Tracker

## 2025-11-21 - Graphique historique implémenté

### Ajouts
- ✅ Script `scripts/generate_snapshots.py` pour générer des snapshots historiques quotidiens
- ✅ Graphique d'évolution temporel sur le dashboard avec Chart.js (line chart)
- ✅ Sélecteur de période : 7j, 30j, 90j, 1an, Tout
- ✅ Double courbe : Valeur totale (bleue pleine) + Total investi (grise pointillés)
- ✅ 325 snapshots générés depuis la première transaction (janvier 2025)

### Technique
- **Endpoint API** : `/api/portfolio/history?days=X` (déjà existant)
- **Service** : `portfolio_service.get_portfolio_history()` (déjà existant)
- **Modèle** : `PortfolioSnapshot` (déjà existant)
- **Frontend** : Fonction JavaScript `loadHistory(period)` dans app.js
- **CSS** : Classe `.period-selector` et `.period-btn` pour les boutons

### Fichiers modifiés
- `frontend/templates/dashboard.html` : Ajout du graphique historique
- `frontend/static/js/app.js` : Fonction `loadHistory()` + intégration dans `loadDashboard()`
- `frontend/static/css/style.css` : Styles pour les boutons de période

### Fichiers créés
- `scripts/generate_snapshots.py` : Génération des snapshots historiques

### Utilisation
```bash
# Regénérer des snapshots (si besoin)
cd /data/projects/crypto-portfolio
source venv/bin/activate
python3 scripts/generate_snapshots.py

# Lancer l'application
./start.sh

# Accéder au dashboard
firefox http://localhost:5050
```

### Fonctionnalités du graphique
- ✅ Affichage responsive (height: 300px)
- ✅ Tooltip interactif avec montants formatés en EUR
- ✅ Légende en haut avec styles personnalisés
- ✅ Axes avec grid semi-transparent
- ✅ Courbe lissée (tension: 0.4)
- ✅ Zone remplie sous la courbe bleue
- ✅ Animation de transition lors du changement de période
- ✅ Destruction propre du graphique lors du rechargement

### Prochaines étapes (optionnel)
- [ ] Ajouter mini-graphiques sparkline par crypto (trending)
- [ ] Optimiser : Utiliser l'API historique CoinGecko pour prix réels du passé
- [ ] Ajouter snapshot automatique via cron (1x/jour)
- [ ] Export historique en CSV
