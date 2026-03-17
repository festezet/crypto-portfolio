#!/usr/bin/env python3
"""
Script pour générer des snapshots historiques du portefeuille
Simule des snapshots quotidiens depuis la première transaction
"""
import sys
import os
from datetime import datetime, timedelta

# Ajouter le répertoire parent au PATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.app import create_app
from backend.models import db, Transaction, PortfolioSnapshot
from backend.services.portfolio import portfolio_service
from backend.services.price import price_service


def _compute_holdings_at_date(transactions):
    """Calcule les holdings a partir d'une liste de transactions"""
    holdings = {}
    for tx in transactions:
        symbol = tx.crypto.symbol
        if symbol not in holdings:
            holdings[symbol] = {
                'volume': 0,
                'total_cost': 0,
                'total_fees': 0
            }

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


def _calculate_snapshot_valuation(active_holdings, prices):
    """Calcule la valorisation du portefeuille et retourne (total_value, total_invested, details)"""
    total_value = 0
    total_invested = 0
    details = {}

    for symbol, h in active_holdings.items():
        current_price = prices.get(symbol, 0)
        value = h['volume'] * current_price
        pnl_pct = ((value - h['total_cost']) / h['total_cost'] * 100) if h['total_cost'] > 0 else 0

        total_value += value
        total_invested += h['total_cost']

        details[symbol] = {
            'volume': round(h['volume'], 8),
            'price': round(current_price, 2),
            'value': round(value, 2),
            'pnl_pct': round(pnl_pct, 2)
        }

    return total_value, total_invested, details


def _process_snapshot_date(current_date):
    """Traite une date pour la generation de snapshot.
    Returns: 'skipped' si existant, 'no_data' si pas de donnees, ou le snapshot cree."""
    existing = PortfolioSnapshot.query.filter(
        db.func.date(PortfolioSnapshot.date) == current_date.date()
    ).first()

    if existing:
        return 'skipped'

    transactions_until_date = Transaction.query.filter(
        Transaction.date <= current_date
    ).order_by(Transaction.date.asc()).all()

    if not transactions_until_date:
        return 'no_data'

    active_holdings = _compute_holdings_at_date(transactions_until_date)
    if not active_holdings:
        return 'no_data'

    symbols = list(active_holdings.keys())
    try:
        prices = price_service.get_prices(symbols)
    except Exception as e:
        print(f"  Erreur recuperation prix pour {current_date.date()}: {e}")
        return 'no_data'

    total_value, total_invested, details = _calculate_snapshot_valuation(active_holdings, prices)

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


def generate_historical_snapshots():
    """Genere des snapshots historiques depuis la premiere transaction"""
    app = create_app()

    with app.app_context():
        existing_count = PortfolioSnapshot.query.count()
        print(f"Snapshots existants : {existing_count}")

        first_tx = Transaction.query.order_by(Transaction.date.asc()).first()
        if not first_tx:
            print("Aucune transaction trouvee.")
            return

        print(f"Premiere transaction : {first_tx.date}")
        last_tx = Transaction.query.order_by(Transaction.date.desc()).first()
        print(f"Derniere transaction : {last_tx.date}")

        current_date = first_tx.date.replace(hour=23, minute=59, second=59, microsecond=0)
        end_date = datetime.utcnow().replace(hour=23, minute=59, second=59, microsecond=0)

        snapshots_created = 0
        snapshots_skipped = 0

        print(f"\nGeneration des snapshots de {current_date.date()} a {end_date.date()}...")

        while current_date <= end_date:
            result = _process_snapshot_date(current_date)
            if result == 'skipped':
                snapshots_skipped += 1
            elif result != 'no_data':
                snapshots_created += 1
                if snapshots_created % 10 == 0:
                    print(f"  {snapshots_created} snapshots crees...")
            current_date += timedelta(days=1)

        db.session.commit()

        print(f"\nGeneration terminee !")
        print(f"  Crees : {snapshots_created}")
        print(f"  Ignores (existants) : {snapshots_skipped}")
        print(f"  Total snapshots : {PortfolioSnapshot.query.count()}")


if __name__ == '__main__':
    generate_historical_snapshots()
