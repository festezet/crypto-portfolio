"""
Configuration de la base de données SQLAlchemy
"""
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from sqlalchemy.engine import Engine
import sqlite3

db = SQLAlchemy()


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Active les clés étrangères pour SQLite"""
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def init_db(app):
    """Initialise la base de données avec l'application Flask"""
    db.init_app(app)

    with app.app_context():
        # Importer tous les modèles pour les créer
        from . import Crypto, Transaction, PortfolioSnapshot, ExitStrategy, StrategyAlert

        # Créer toutes les tables
        db.create_all()

        # Insérer les cryptos de base si la table est vide
        if Crypto.query.count() == 0:
            _seed_cryptos()


def _seed_cryptos():
    """Insère les cryptomonnaies courantes dans la base"""
    from . import Crypto
    from backend.config import CRYPTO_MAPPING

    cryptos = [
        Crypto(symbol="BTC", name="Bitcoin", coingecko_id="bitcoin"),
        Crypto(symbol="ETH", name="Ethereum", coingecko_id="ethereum"),
        Crypto(symbol="BNB", name="Binance Coin", coingecko_id="binancecoin"),
        Crypto(symbol="SOL", name="Solana", coingecko_id="solana"),
        Crypto(symbol="ADA", name="Cardano", coingecko_id="cardano"),
        Crypto(symbol="XRP", name="Ripple", coingecko_id="ripple"),
        Crypto(symbol="DOT", name="Polkadot", coingecko_id="polkadot"),
        Crypto(symbol="DOGE", name="Dogecoin", coingecko_id="dogecoin"),
        Crypto(symbol="AVAX", name="Avalanche", coingecko_id="avalanche-2"),
        Crypto(symbol="MATIC", name="Polygon", coingecko_id="matic-network"),
        Crypto(symbol="LINK", name="Chainlink", coingecko_id="chainlink"),
        Crypto(symbol="UNI", name="Uniswap", coingecko_id="uniswap"),
        Crypto(symbol="ATOM", name="Cosmos", coingecko_id="cosmos"),
        Crypto(symbol="LTC", name="Litecoin", coingecko_id="litecoin"),
        Crypto(symbol="USDT", name="Tether", coingecko_id="tether"),
        Crypto(symbol="USDC", name="USD Coin", coingecko_id="usd-coin"),
    ]

    for crypto in cryptos:
        db.session.add(crypto)

    db.session.commit()
