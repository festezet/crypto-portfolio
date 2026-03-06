"""
Application Flask principale - Crypto Portfolio Tracker
"""
import os
import sys

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, send_from_directory
from flask_cors import CORS

from backend.config import (
    SQLALCHEMY_DATABASE_URI,
    SQLALCHEMY_TRACK_MODIFICATIONS,
    SECRET_KEY,
    DEBUG,
    HOST,
    PORT,
    DATA_DIR
)
from backend.models import init_db
from backend.api import api_bp


def create_app():
    """Factory function pour créer l'application Flask"""

    app = Flask(
        __name__,
        template_folder='../frontend/templates',
        static_folder='../frontend/static'
    )

    # Configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = SQLALCHEMY_TRACK_MODIFICATIONS
    app.config['SECRET_KEY'] = SECRET_KEY

    # CORS pour les appels API depuis le frontend
    CORS(app)

    # Initialiser la base de données
    init_db(app)

    # Enregistrer le blueprint API
    app.register_blueprint(api_bp)

    # S'assurer que les répertoires existent
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / 'imports').mkdir(exist_ok=True)
    (DATA_DIR / 'exports').mkdir(exist_ok=True)
    (DATA_DIR / 'backups').mkdir(exist_ok=True)

    # Routes frontend
    @app.route('/')
    def index():
        return render_template('dashboard.html')

    @app.route('/transactions')
    def transactions():
        return render_template('transactions.html')

    @app.route('/strategies')
    def strategies():
        return render_template('strategies.html')

    @app.route('/fiscal')
    def fiscal():
        return render_template('fiscal.html')

    @app.route('/settings')
    def settings():
        return render_template('settings.html')

    @app.route('/import')
    def import_page():
        return render_template('import.html')

    # Route pour les fichiers statiques (images crypto)
    @app.route('/crypto-icons/<symbol>')
    def crypto_icon(symbol):
        # Utiliser des icônes génériques ou CoinGecko
        return send_from_directory(
            app.static_folder + '/images',
            f'{symbol.lower()}.png',
            mimetype='image/png'
        )

    # Gestionnaire d'erreurs
    @app.errorhandler(404)
    def not_found(e):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Not found'}), 404
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def server_error(e):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Internal server error'}), 500
        return render_template('500.html'), 500

    return app


# Import pour le gestionnaire d'erreurs
from flask import request, jsonify

# Créer l'application
app = create_app()

if __name__ == '__main__':
    print(f"""
    ╔══════════════════════════════════════════════════════════╗
    ║           CRYPTO PORTFOLIO TRACKER                       ║
    ║                                                          ║
    ║   Démarrage du serveur...                                ║
    ║   URL: http://{HOST}:{PORT}                              ║
    ║   API: http://{HOST}:{PORT}/api                          ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    app.run(host=HOST, port=PORT, debug=DEBUG)
