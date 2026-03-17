#!/usr/bin/env python3
"""
Script pour générer des snapshots historiques avec PRIX HISTORIQUES RÉELS
Utilise l'API CoinGecko market_chart pour obtenir les vrais prix du passé
"""
import sys
import os
from datetime import datetime, timedelta
import time

# Ajouter le répertoire parent au PATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.app import create_app
from backend.models import db, Transaction, PortfolioSnapshot
from backend.services.price import price_service


def get_historical_prices_batch(symbols, from_date, to_date):
    """
    Récupère les prix historiques pour plusieurs cryptos sur une période

    Returns:
        Dict[symbol, Dict[date_str, price]]
    """
    days = (to_date - from_date).days + 1

    print(f"📊 Récupération des prix historiques pour {len(symbols)} cryptos sur {days} jours...")

    all_prices = {}

    for i, symbol in enumerate(symbols, 1):
        print(f"  [{i}/{len(symbols)}] {symbol}...", end=' ', flush=True)

        # Récupérer l'historique complet pour cette crypto
        market_data = price_service.get_market_chart(symbol, days=days)

        if not market_data:
            print(f"❌ Échec")
            continue

        # Construire un dict date -> prix
        symbol_prices = {}
        for timestamp, price in market_data:
            date_key = timestamp.strftime('%Y-%m-%d')
            symbol_prices[date_key] = price

        all_prices[symbol] = symbol_prices
        print(f"✅ {len(symbol_prices)} prix")

        # Rate limiting : pause entre chaque crypto (API gratuite limite à ~10 req/min)
        if i < len(symbols):
            wait_time = 8  # 8 secondes = ~7.5 requêtes/minute (safe)
            print(f"    ⏱️  Attente {wait_time}s (rate limiting)...")
            time.sleep(wait_time)

    return all_prices


def _compute_holdings_from_transactions(transactions):
    """Calcule les holdings a partir d'une liste de transactions"""
    holdings = {}
    for tx in transactions:
        symbol = tx.crypto.symbol
        if symbol not in holdings:
            holdings[symbol] = {'volume': 0, 'total_cost': 0, 'total_fees': 0}

        h = holdings[symbol]
        if tx.is_buy:
            h['volume'] += tx.volume
            h['total_cost'] += tx.total
            h['total_fees'] += tx.fee or 0
        elif tx.is_sell:
            if h['volume'] > 0:
                cost_per_unit = h['total_cost'] / h['volume']
                sold_cost = cost_per_unit * tx.volume
                h['total_cost'] -= sold_cost
                h['volume'] -= tx.volume
                h['total_fees'] += tx.fee or 0

    return {
        symbol: h for symbol, h in holdings.items()
        if h['volume'] > 0.00000001
    }


def _get_historical_price_for_symbol(symbol, date_key, current_date, historical_prices):
    """Recupere le prix historique reel pour un symbole a une date, avec fallback 7 jours"""
    if symbol in historical_prices and date_key in historical_prices[symbol]:
        return historical_prices[symbol][date_key]

    for days_back in range(1, 8):
        prev_date = current_date - timedelta(days=days_back)
        prev_key = prev_date.strftime('%Y-%m-%d')
        if symbol in historical_prices and prev_key in historical_prices[symbol]:
            return historical_prices[symbol][prev_key]

    return None


def _calculate_valuation_with_historical_prices(active_holdings, date_key, current_date, historical_prices):
    """Calcule la valorisation avec les prix historiques reels.
    Returns (total_value, total_invested, details, missing_prices)"""
    total_value = 0
    total_invested = 0
    details = {}
    missing_prices = []

    for symbol, h in active_holdings.items():
        historical_price = _get_historical_price_for_symbol(
            symbol, date_key, current_date, historical_prices
        )

        if not historical_price:
            missing_prices.append(symbol)
            continue

        value = h['volume'] * historical_price
        pnl_pct = ((value - h['total_cost']) / h['total_cost'] * 100) if h['total_cost'] > 0 else 0

        total_value += value
        total_invested += h['total_cost']

        details[symbol] = {
            'volume': round(h['volume'], 8),
            'price': round(historical_price, 2),
            'value': round(value, 2),
            'pnl_pct': round(pnl_pct, 2)
        }

    return total_value, total_invested, details, missing_prices


def _process_historical_snapshot_date(current_date, all_transactions, historical_prices, skip_existing):
    """Traite une date pour la generation de snapshot avec prix historiques.
    Returns: 'skipped' si existant, 'no_data' si pas de donnees, ou le snapshot cree."""
    date_key = current_date.strftime('%Y-%m-%d')

    existing = PortfolioSnapshot.query.filter(
        db.func.date(PortfolioSnapshot.date) == current_date.date()
    ).first()

    if existing and skip_existing:
        return 'skipped'

    transactions_until_date = [
        tx for tx in all_transactions if tx.date <= current_date
    ]

    if not transactions_until_date:
        return 'no_data'

    active_holdings = _compute_holdings_from_transactions(transactions_until_date)
    if not active_holdings:
        return 'no_data'

    total_value, total_invested, details, missing_prices = \
        _calculate_valuation_with_historical_prices(
            active_holdings, date_key, current_date, historical_prices
        )

    if missing_prices:
        print(f"  {date_key}: Prix manquants pour {', '.join(missing_prices)}")

    if total_value == 0:
        return 'no_data'

    pnl = total_value - total_invested
    pnl_pct = (pnl / total_invested * 100) if total_invested > 0 else 0

    snapshot = PortfolioSnapshot(
        date=current_date,
        total_value=total_value,
        total_invested=total_invested,
        total_pnl=pnl,
        total_pnl_pct=pnl_pct
    )
    snapshot.details = details
    db.session.add(snapshot)
    return snapshot


def generate_historical_snapshots_with_real_prices():
    """Genere des snapshots historiques avec les VRAIS prix historiques"""
    app = create_app()

    with app.app_context():
        delete_old = input("Supprimer les anciens snapshots ? (o/n) [n]: ").lower()
        if delete_old == 'o':
            count = PortfolioSnapshot.query.count()
            PortfolioSnapshot.query.delete()
            db.session.commit()
            print(f"{count} anciens snapshots supprimes")

        first_tx = Transaction.query.order_by(Transaction.date.asc()).first()
        if not first_tx:
            print("Aucune transaction trouvee.")
            return

        print(f"Premiere transaction : {first_tx.date}")

        start_date = first_tx.date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = datetime.utcnow().replace(hour=23, minute=59, second=59, microsecond=0)

        all_transactions = Transaction.query.order_by(Transaction.date.asc()).all()
        all_symbols = set(tx.crypto.symbol for tx in all_transactions)
        print(f"{len(all_symbols)} cryptos detectees : {', '.join(sorted(all_symbols))}")

        historical_prices = get_historical_prices_batch(
            list(all_symbols), start_date, end_date
        )

        if not historical_prices:
            print("Impossible de recuperer les prix historiques.")
            return

        print(f"\nGeneration des snapshots avec prix reels...")

        snapshots_created = 0
        snapshots_skipped = 0
        skip_existing = (delete_old != 'o')
        current_date = start_date

        while current_date <= end_date:
            result = _process_historical_snapshot_date(
                current_date, all_transactions, historical_prices, skip_existing
            )
            if result == 'skipped':
                snapshots_skipped += 1
            elif result != 'no_data':
                snapshots_created += 1
                if snapshots_created % 10 == 0:
                    db.session.commit()
                    date_key = current_date.strftime('%Y-%m-%d')
                    print(f"  {snapshots_created} snapshots crees... (dernier: {date_key})")
            current_date += timedelta(days=1)

        db.session.commit()

        print(f"\nGeneration terminee avec prix historiques reels !")
        print(f"  Crees : {snapshots_created}")
        print(f"  Ignores : {snapshots_skipped}")
        print(f"  Total : {PortfolioSnapshot.query.count()}")


if __name__ == '__main__':
    print("=" * 60)
    print("  GÉNÉRATION SNAPSHOTS AVEC PRIX HISTORIQUES RÉELS")
    print("=" * 60)
    print()
    print("⚠️  Ce script utilise l'API CoinGecko pour récupérer les vrais prix.")
    print("⏱️  Temps estimé : ~2-3 minutes (rate limiting)")
    print()

    confirm = input("Continuer ? (o/n) [o]: ").lower()
    if confirm == 'n':
        print("❌ Annulé")
        sys.exit(0)

    generate_historical_snapshots_with_real_prices()
