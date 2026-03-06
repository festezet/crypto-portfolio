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


def generate_historical_snapshots():
    """Génère des snapshots historiques depuis la première transaction"""
    app = create_app()

    with app.app_context():
        # Vérifier s'il y a déjà des snapshots
        existing_count = PortfolioSnapshot.query.count()
        print(f"📊 Snapshots existants : {existing_count}")

        # Récupérer la date de la première transaction
        first_tx = Transaction.query.order_by(Transaction.date.asc()).first()
        if not first_tx:
            print("❌ Aucune transaction trouvée. Importez d'abord des transactions.")
            return

        print(f"📅 Première transaction : {first_tx.date}")

        # Récupérer la date de la dernière transaction
        last_tx = Transaction.query.order_by(Transaction.date.desc()).first()
        print(f"📅 Dernière transaction : {last_tx.date}")

        # Générer des snapshots quotidiens
        current_date = first_tx.date.replace(hour=23, minute=59, second=59, microsecond=0)
        end_date = datetime.utcnow().replace(hour=23, minute=59, second=59, microsecond=0)

        snapshots_created = 0
        snapshots_skipped = 0

        print(f"\n🔄 Génération des snapshots de {current_date.date()} à {end_date.date()}...")

        while current_date <= end_date:
            # Vérifier si un snapshot existe déjà pour cette date
            existing = PortfolioSnapshot.query.filter(
                db.func.date(PortfolioSnapshot.date) == current_date.date()
            ).first()

            if existing:
                snapshots_skipped += 1
                current_date += timedelta(days=1)
                continue

            # Calculer l'état du portefeuille à cette date
            # On récupère toutes les transactions jusqu'à cette date
            transactions_until_date = Transaction.query.filter(
                Transaction.date <= current_date
            ).order_by(Transaction.date.asc()).all()

            if not transactions_until_date:
                current_date += timedelta(days=1)
                continue

            # Calculer les holdings à cette date (même logique que portfolio_service)
            holdings = {}
            for tx in transactions_until_date:
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

            # Filtrer les holdings actifs
            active_holdings = {
                symbol: h for symbol, h in holdings.items()
                if h['volume'] > 0.00000001
            }

            if not active_holdings:
                current_date += timedelta(days=1)
                continue

            # Récupérer les prix pour cette date (on utilise les prix actuels car API limitée)
            # Dans un vrai système, on utiliserait l'API historical de CoinGecko
            symbols = list(active_holdings.keys())
            try:
                prices = price_service.get_prices(symbols)
            except Exception as e:
                print(f"⚠️  Erreur récupération prix pour {current_date.date()}: {e}")
                current_date += timedelta(days=1)
                continue

            # Calculer la valorisation
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

            # Créer le snapshot
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
            snapshots_created += 1

            # Afficher la progression tous les 10 snapshots
            if snapshots_created % 10 == 0:
                print(f"  📈 {snapshots_created} snapshots créés...")

            current_date += timedelta(days=1)

        # Commit final
        db.session.commit()

        print(f"\n✅ Génération terminée !")
        print(f"  ✨ Créés : {snapshots_created}")
        print(f"  ⏭️  Ignorés (existants) : {snapshots_skipped}")
        print(f"  📊 Total snapshots : {PortfolioSnapshot.query.count()}")


if __name__ == '__main__':
    generate_historical_snapshots()
