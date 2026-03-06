"""
Configuration de l'application Crypto Portfolio Tracker
"""
import os
from pathlib import Path

# Chemins de base
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
IMPORTS_DIR = DATA_DIR / "imports"
EXPORTS_DIR = DATA_DIR / "exports"
BACKUPS_DIR = DATA_DIR / "backups"

# Base de données
DATABASE_PATH = DATA_DIR / "portfolio.db"
SQLALCHEMY_DATABASE_URI = f"sqlite:///{DATABASE_PATH}"
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Devise de référence
BASE_CURRENCY = "EUR"
SUPPORTED_CURRENCIES = ["EUR", "USD", "USDT", "BTC"]

# API Configuration
PRICE_UPDATE_INTERVAL = 60  # secondes
SNAPSHOT_INTERVAL = 24  # heures

# CoinGecko API (gratuit, pas de clé requise)
COINGECKO_API_URL = "https://api.coingecko.com/api/v3"

# Binance API (optionnel - lecture seule)
BINANCE_API_KEY = os.environ.get("BINANCE_API_KEY", "")
BINANCE_API_SECRET = os.environ.get("BINANCE_API_SECRET", "")

# Kucoin API (optionnel - lecture seule)
KUCOIN_API_KEY = os.environ.get("KUCOIN_API_KEY", "")
KUCOIN_API_SECRET = os.environ.get("KUCOIN_API_SECRET", "")
KUCOIN_API_PASSPHRASE = os.environ.get("KUCOIN_API_PASSPHRASE", "")

# Calcul fiscal
FISCAL_METHOD = "FIFO"  # FIFO, LIFO, PMP
FISCAL_YEAR_START_MONTH = 1  # Janvier

# Stratégies de sortie - Seuils par défaut
DEFAULT_EXIT_STRATEGY = {
    "enabled": False,
    "mode": "alert",  # alert, semi-auto, auto
    "thresholds": [
        {"profit_pct": 20, "sell_pct": 10, "description": "Sécuriser 10% à +20%"},
        {"profit_pct": 50, "sell_pct": 15, "description": "Vendre 15% à +50%"},
        {"profit_pct": 100, "sell_pct": 20, "description": "Vendre 20% à +100%"},
        {"profit_pct": 200, "sell_pct": 25, "description": "Vendre 25% à +200%"},
        {"profit_pct": 500, "sell_pct": 30, "description": "Vendre 30% à +500%"},
    ],
    "capital_recovery": {
        "enabled": True,
        "at_profit_pct": 100,
        "recover_pct": 100
    }
}

# Flask
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
DEBUG = os.environ.get("FLASK_DEBUG", "1") == "1"
HOST = "0.0.0.0"
PORT = 5050

# Mapping des symboles crypto vers CoinGecko IDs
CRYPTO_MAPPING = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "BNB": "binancecoin",
    "SOL": "solana",
    "ADA": "cardano",
    "XRP": "ripple",
    "DOT": "polkadot",
    "DOGE": "dogecoin",
    "AVAX": "avalanche-2",
    "MATIC": "matic-network",
    "LINK": "chainlink",
    "UNI": "uniswap",
    "ATOM": "cosmos",
    "LTC": "litecoin",
    "ETC": "ethereum-classic",
    "XLM": "stellar",
    "ALGO": "algorand",
    "VET": "vechain",
    "FTM": "fantom",
    "NEAR": "near",
    "AAVE": "aave",
    "GRT": "the-graph",
    "FIL": "filecoin",
    "SAND": "the-sandbox",
    "MANA": "decentraland",
    "AXS": "axie-infinity",
    "THETA": "theta-token",
    "XTZ": "tezos",
    "EGLD": "elrond-erd-2",
    "EOS": "eos",
    "CAKE": "pancakeswap-token",
    "RUNE": "thorchain",
    "ZEC": "zcash",
    "KAVA": "kava",
    "AR": "arweave",
    "FLOW": "flow",
    "XMR": "monero",
    "NEO": "neo",
    "WAVES": "waves",
    "DASH": "dash",
    "MKR": "maker",
    "COMP": "compound-governance-token",
    "SNX": "havven",
    "YFI": "yearn-finance",
    "SUSHI": "sushi",
    "CRV": "curve-dao-token",
    "1INCH": "1inch",
    "BAT": "basic-attention-token",
    "ENJ": "enjincoin",
    "CHZ": "chiliz",
    "GALA": "gala",
    "APE": "apecoin",
    "LDO": "lido-dao",
    "OP": "optimism",
    "ARB": "arbitrum",
    "SUI": "sui",
    "SEI": "sei-network",
    "TIA": "celestia",
    "INJ": "injective-protocol",
    "PEPE": "pepe",
    "SHIB": "shiba-inu",
    "FLOKI": "floki",
    "WIF": "dogwifcoin",
    "BONK": "bonk",
    # Hyperliquid et autres nouveaux tokens
    "HYPE": "hyperliquid",
    # Stablecoins
    "USDT": "tether",
    "USDC": "usd-coin",
    "DAI": "dai",
    "BUSD": "binance-usd",
}
