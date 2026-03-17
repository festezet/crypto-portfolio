#!/usr/bin/env python3
"""
Génère des données de test pour le Crypto Portfolio Tracker
Achats réguliers de 1000€/mois depuis janvier 2025
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from random import uniform, choice
import requests

from backend.app import app
from backend.models import db, Crypto, Transaction

# Configuration des achats mensuels
MONTHLY_INVESTMENT = 1000  # EUR par mois

# Répartition du portefeuille
ALLOCATION = {
    'BTC': 0.70,    # 70% - 700€/mois
    'ETH': 0.15,    # 15% - 150€/mois
    'SOL': 0.05,    # 5%  - 50€/mois
    'AAVE': 0.02,   # 2%  - 20€/mois
    'HYPE': 0.02,   # 2%  - 20€/mois (Hyperliquid)
    'DOT': 0.02,    # 2%  - 20€/mois (Polkadot)
    'XMR': 0.015,   # 1.5% - 15€/mois
    'XRP': 0.015,   # 1.5% - 15€/mois
    'BNB': 0.01,    # 1%  - 10€/mois
}

# Prix historiques approximatifs (EUR) - Janvier à Novembre 2025
# Basés sur les tendances réelles du marché
HISTORICAL_PRICES = {
    'BTC': [
        (datetime(2025, 1, 1), 42000),
        (datetime(2025, 2, 1), 45000),
        (datetime(2025, 3, 1), 58000),
        (datetime(2025, 4, 1), 62000),
        (datetime(2025, 5, 1), 55000),
        (datetime(2025, 6, 1), 60000),
        (datetime(2025, 7, 1), 65000),
        (datetime(2025, 8, 1), 58000),
        (datetime(2025, 9, 1), 62000),
        (datetime(2025, 10, 1), 68000),
        (datetime(2025, 11, 1), 88000),
    ],
    'ETH': [
        (datetime(2025, 1, 1), 2200),
        (datetime(2025, 2, 1), 2400),
        (datetime(2025, 3, 1), 3200),
        (datetime(2025, 4, 1), 3000),
        (datetime(2025, 5, 1), 2800),
        (datetime(2025, 6, 1), 3100),
        (datetime(2025, 7, 1), 3300),
        (datetime(2025, 8, 1), 2900),
        (datetime(2025, 9, 1), 3000),
        (datetime(2025, 10, 1), 3200),
        (datetime(2025, 11, 1), 3100),
    ],
    'SOL': [
        (datetime(2025, 1, 1), 95),
        (datetime(2025, 2, 1), 110),
        (datetime(2025, 3, 1), 180),
        (datetime(2025, 4, 1), 150),
        (datetime(2025, 5, 1), 140),
        (datetime(2025, 6, 1), 160),
        (datetime(2025, 7, 1), 175),
        (datetime(2025, 8, 1), 145),
        (datetime(2025, 9, 1), 155),
        (datetime(2025, 10, 1), 170),
        (datetime(2025, 11, 1), 230),
    ],
    'AAVE': [
        (datetime(2025, 1, 1), 95),
        (datetime(2025, 2, 1), 110),
        (datetime(2025, 3, 1), 140),
        (datetime(2025, 4, 1), 130),
        (datetime(2025, 5, 1), 120),
        (datetime(2025, 6, 1), 135),
        (datetime(2025, 7, 1), 150),
        (datetime(2025, 8, 1), 125),
        (datetime(2025, 9, 1), 140),
        (datetime(2025, 10, 1), 160),
        (datetime(2025, 11, 1), 180),
    ],
    'HYPE': [  # Hyperliquid - lancé fin 2024
        (datetime(2025, 1, 1), 12),
        (datetime(2025, 2, 1), 15),
        (datetime(2025, 3, 1), 22),
        (datetime(2025, 4, 1), 18),
        (datetime(2025, 5, 1), 16),
        (datetime(2025, 6, 1), 20),
        (datetime(2025, 7, 1), 25),
        (datetime(2025, 8, 1), 19),
        (datetime(2025, 9, 1), 22),
        (datetime(2025, 10, 1), 28),
        (datetime(2025, 11, 1), 26),
    ],
    'DOT': [  # Polkadot
        (datetime(2025, 1, 1), 7.5),
        (datetime(2025, 2, 1), 8.5),
        (datetime(2025, 3, 1), 11),
        (datetime(2025, 4, 1), 9.5),
        (datetime(2025, 5, 1), 8),
        (datetime(2025, 6, 1), 9),
        (datetime(2025, 7, 1), 10),
        (datetime(2025, 8, 1), 8.5),
        (datetime(2025, 9, 1), 9),
        (datetime(2025, 10, 1), 10.5),
        (datetime(2025, 11, 1), 9),
    ],
    'XMR': [  # Monero
        (datetime(2025, 1, 1), 155),
        (datetime(2025, 2, 1), 165),
        (datetime(2025, 3, 1), 190),
        (datetime(2025, 4, 1), 175),
        (datetime(2025, 5, 1), 160),
        (datetime(2025, 6, 1), 170),
        (datetime(2025, 7, 1), 185),
        (datetime(2025, 8, 1), 165),
        (datetime(2025, 9, 1), 175),
        (datetime(2025, 10, 1), 190),
        (datetime(2025, 11, 1), 180),
    ],
    'XRP': [
        (datetime(2025, 1, 1), 0.55),
        (datetime(2025, 2, 1), 0.65),
        (datetime(2025, 3, 1), 0.85),
        (datetime(2025, 4, 1), 0.75),
        (datetime(2025, 5, 1), 0.60),
        (datetime(2025, 6, 1), 0.70),
        (datetime(2025, 7, 1), 0.80),
        (datetime(2025, 8, 1), 0.65),
        (datetime(2025, 9, 1), 0.72),
        (datetime(2025, 10, 1), 0.90),
        (datetime(2025, 11, 1), 1.10),
    ],
    'BNB': [
        (datetime(2025, 1, 1), 280),
        (datetime(2025, 2, 1), 320),
        (datetime(2025, 3, 1), 450),
        (datetime(2025, 4, 1), 520),
        (datetime(2025, 5, 1), 480),
        (datetime(2025, 6, 1), 550),
        (datetime(2025, 7, 1), 580),
        (datetime(2025, 8, 1), 510),
        (datetime(2025, 9, 1), 540),
        (datetime(2025, 10, 1), 590),
        (datetime(2025, 11, 1), 620),
    ],
}

# Noms complets des cryptos
CRYPTO_NAMES = {
    'BTC': 'Bitcoin',
    'ETH': 'Ethereum',
    'SOL': 'Solana',
    'AAVE': 'Aave',
    'HYPE': 'Hyperliquid',
    'DOT': 'Polkadot',
    'XMR': 'Monero',
    'XRP': 'Ripple',
    'BNB': 'Binance Coin',
}

# CoinGecko IDs
COINGECKO_IDS = {
    'BTC': 'bitcoin',
    'ETH': 'ethereum',
    'SOL': 'solana',
    'AAVE': 'aave',
    'HYPE': 'hyperliquid',
    'DOT': 'polkadot',
    'XMR': 'monero',
    'XRP': 'ripple',
    'BNB': 'binancecoin',
}


def get_price_for_date(symbol: str, date: datetime) -> float:
    """Récupère le prix approximatif pour une date donnée"""
    prices = HISTORICAL_PRICES.get(symbol, [])

    for i, (price_date, price) in enumerate(prices):
        if date < price_date:
            if i == 0:
                return price
            # Interpolation linéaire entre les deux dates
            prev_date, prev_price = prices[i-1]
            days_total = (price_date - prev_date).days
            days_elapsed = (date - prev_date).days
            if days_total > 0:
                ratio = days_elapsed / days_total
                return prev_price + (price - prev_price) * ratio
            return prev_price

    # Après la dernière date connue
    if prices:
        return prices[-1][1]
    return 100  # Valeur par défaut


def add_variation(price: float, max_pct: float = 3) -> float:
    """Ajoute une petite variation aléatoire au prix"""
    variation = uniform(-max_pct, max_pct) / 100
    return price * (1 + variation)


def _clear_old_data():
    """Supprime les anciennes donnees de test"""
    print("Suppression des anciennes donnees...")
    Transaction.query.delete()
    Crypto.query.delete()
    db.session.commit()


def _create_cryptos():
    """Cree les cryptos en base et retourne un dict symbol -> Crypto"""
    print("Creation des cryptos...")
    cryptos = {}
    for symbol in ALLOCATION.keys():
        crypto = Crypto(
            symbol=symbol,
            name=CRYPTO_NAMES.get(symbol, symbol),
            coingecko_id=COINGECKO_IDS.get(symbol)
        )
        db.session.add(crypto)
        db.session.flush()
        cryptos[symbol] = crypto
    db.session.commit()
    return cryptos


def _generate_monthly_buys(cryptos, start_date, end_date):
    """Genere les achats mensuels DCA et retourne (month_count, total_invested)"""
    current_date = start_date
    month_count = 0
    total_invested = 0

    while current_date <= end_date:
        month_count += 1
        print(f"\n{current_date.strftime('%B %Y')}")

        for symbol, allocation in ALLOCATION.items():
            amount_eur = MONTHLY_INVESTMENT * allocation
            base_price = get_price_for_date(symbol, current_date)
            price = add_variation(base_price, max_pct=2)
            volume = amount_eur / price
            fee = amount_eur * 0.001
            exchange = choice(['binance', 'kucoin'])

            tx = Transaction(
                date=current_date + timedelta(hours=uniform(9, 18)),
                type='BUY',
                exchange=exchange,
                crypto_id=cryptos[symbol].id,
                volume=volume,
                price=price,
                total=amount_eur,
                fee=fee,
                fee_currency='EUR',
                pair=f"{symbol}/EUR",
                quote_currency='EUR',
                notes=f"DCA mensuel {current_date.strftime('%B %Y')}"
            )
            db.session.add(tx)

            print(f"  {symbol:5} : {amount_eur:6.0f}EUR -> {volume:12.8f} @ {price:10.2f}EUR ({exchange})")
            total_invested += amount_eur

        if current_date.month == 12:
            current_date = datetime(current_date.year + 1, 1, 1)
        else:
            current_date = datetime(current_date.year, current_date.month + 1, 1)

    db.session.commit()
    return month_count, total_invested


def _print_summary(month_count, total_invested):
    """Affiche le resume de la generation"""
    print("\n" + "=" * 60)
    print(f"Donnees generees avec succes!")
    print(f"   - Mois simules : {month_count}")
    print(f"   - Total investi : {total_invested:,.0f}EUR")
    print(f"   - Transactions creees : {Transaction.query.count()}")
    print(f"   - Cryptos : {', '.join(ALLOCATION.keys())}")
    print("\nRepartition de l'investissement :")
    for symbol, alloc in ALLOCATION.items():
        print(f"   {symbol:5} : {alloc*100:5.1f}% ({MONTHLY_INVESTMENT * alloc * month_count:,.0f}EUR)")


def generate_dummy_data():
    """Genere les donnees de test"""
    with app.app_context():
        _clear_old_data()
        cryptos = _create_cryptos()

        print("\nGeneration des achats mensuels (1000EUR/mois)...")
        print("=" * 60)

        start_date = datetime(2025, 1, 1)
        end_date = datetime(2025, 11, 21)

        month_count, total_invested = _generate_monthly_buys(cryptos, start_date, end_date)
        _print_summary(month_count, total_invested)


if __name__ == '__main__':
    generate_dummy_data()
