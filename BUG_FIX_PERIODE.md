# Bug Fix : Boutons de période du graphique historique

## Problème identifié (2025-11-21)

**Symptôme** :
Les boutons de sélection de période (7j, 30j, 90j, 1an, Tout) ne changeaient pas l'affichage du graphique historique. Seul le mois de novembre s'affichait quel que soit le bouton cliqué.

## Cause

Bug dans la méthode `get_portfolio_history()` du fichier `backend/services/portfolio.py` ligne 201 :

```python
# CODE BUGGÉ
from_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
from_date = from_date.replace(day=from_date.day - days) if days < from_date.day else from_date.replace(day=1)
```

**Problème** : Cette méthode soustrait le nombre de jours **du jour du mois** au lieu de soustraire des jours au timestamp complet.

**Exemple** :
- Date actuelle : 21 novembre 2025
- Demande : 90 jours avant
- Résultat bugué : `21 - 90 = -69` → 1er novembre (faux !)
- Résultat attendu : 23 août 2025

## Solution

```python
# CODE CORRIGÉ
from datetime import timedelta

# Calculer la date de début en soustrayant le nombre de jours
now = datetime.utcnow()
from_date = now - timedelta(days=days)
```

## Fichiers modifiés

### 1. `backend/services/portfolio.py`
- Ligne 200-201 : Correction du calcul de date avec `timedelta(days=days)`

### 2. `frontend/templates/dashboard.html`
- Ligne 33-34 : Changement de `class="active"` du bouton "7j" vers "30j" pour cohérence

## Tests de validation

Après correction, tous les boutons fonctionnent correctement :

```bash
# Test 7 jours
curl -s "http://localhost:5050/api/portfolio/history?days=7" | python3 -c "..."
# Résultat : 8 snapshots (14 nov → 21 nov)

# Test 30 jours
curl -s "http://localhost:5050/api/portfolio/history?days=30" | python3 -c "..."
# Résultat : 31 snapshots (22 oct → 21 nov)

# Test 90 jours
curl -s "http://localhost:5050/api/portfolio/history?days=90" | python3 -c "..."
# Résultat : 91 snapshots (23 août → 21 nov)

# Test 365 jours (1 an)
curl -s "http://localhost:5050/api/portfolio/history?days=365" | python3 -c "..."
# Résultat : 325 snapshots (1 jan → 21 nov)
```

## Redémarrage requis

Après modification du code backend Python, redémarrer Flask :
```bash
pkill -f "python.*crypto-portfolio.*app.py"
cd /data/projects/crypto-portfolio && ./start.sh
```

## Test visuel

1. Ouvrir http://localhost:5050
2. Observer le graphique "Évolution du portefeuille"
3. Cliquer sur chaque bouton :
   - **7j** : Doit afficher la semaine dernière
   - **30j** : Doit afficher le dernier mois
   - **90j** : Doit afficher les 3 derniers mois
   - **1an** : Doit afficher toute l'année (janvier → novembre)
   - **Tout** : Doit afficher tous les snapshots

## Impact

- ✅ Graphique affiche maintenant correctement toutes les périodes
- ✅ Courbes cohérentes avec les dates
- ✅ Boutons réactifs et classe `active` correctement appliquée

## Prévention

Pour éviter ce type de bug à l'avenir :
1. **Tests unitaires** pour les fonctions de calcul de date
2. **Validation** : Toujours utiliser `timedelta` pour les calculs de date
3. **Logging** : Ajouter des logs pour voir les dates calculées

---

**Bug résolu** : 2025-11-21  
**Auteur** : Claude Code
