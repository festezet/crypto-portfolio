#!/bin/bash
# Script de lancement du Crypto Portfolio Tracker

cd "$(dirname "$0")"

# Vérifier si l'environnement virtuel existe
if [ ! -d "venv" ]; then
    echo "Création de l'environnement virtuel..."
    python3 -m venv venv
fi

# Activer l'environnement virtuel
source venv/bin/activate

# Installer les dépendances si nécessaire
if [ ! -f "venv/.installed" ]; then
    echo "Installation des dépendances..."
    pip install -r requirements.txt
    touch venv/.installed
fi

# Créer les répertoires de données
mkdir -p data/imports data/exports data/backups

# Lancer l'application
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║           CRYPTO PORTFOLIO TRACKER                       ║"
echo "║                                                          ║"
echo "║   Démarrage du serveur...                                ║"
echo "║   URL: http://localhost:5050                             ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Lancer le serveur en arrière-plan
python3 backend/app.py &
SERVER_PID=$!

# Attendre que le serveur démarre
sleep 4

# Ouvrir le navigateur via gio (évite conflit Firefox)
gio open "http://localhost:5050" 2>/dev/null &

# Attendre le serveur (Ctrl+C pour arrêter)
wait $SERVER_PID
