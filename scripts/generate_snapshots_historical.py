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


def generate_historical_snapshots_with_real_prices():
    """Génère des snapshots historiques avec les VRAIS prix historiques"""
    app = create_app()

    with app.app_context():
        # Supprimer les anciens snapshots (option)
        delete_old = input("Supprimer les anciens snapshots ? (o/n) [n]: ").lower()
        if delete_old == 'o':
            count = PortfolioSnapshot.query.count()
            PortfolioSnapshot.query.delete()
            db.session.commit()
            print(f"🗑️  {count} anciens snapshots supprimés")

        # Vérifier les transactions
        first_tx = Transaction.query.order_by(Transaction.date.asc()).first()
        if not first_tx:
            print("❌ Aucune transaction trouvée.")
            return

        print(f"📅 Première transaction : {first_tx.date}")

        # Calculer la période
        start_date = first_tx.date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = datetime.utcnow().replace(hour=23, minute=59, second=59, microsecond=0)

        # Récupérer toutes les transactions
        all_transactions = Transaction.query.order_by(Transaction.date.asc()).all()

        # Identifier toutes les cryptos uniques
        all_symbols = set(tx.crypto.symbol for tx in all_transactions)
        print(f"💰 {len(all_symbols)} cryptos détectées : {', '.join(sorted(all_symbols))}")

        # Récupérer les prix historiques pour TOUTES les cryptos d'un coup
        historical_prices = get_historical_prices_batch(
            list(all_symbols),
            start_date,
            end_date
        )

        if not historical_prices:
            print("❌ Impossible de récupérer les prix historiques.")
            return

        print(f"\n🔄 Génération des snapshots avec prix réels...")

        snapshots_created = 0
        snapshots_skipped = 0

        current_date = start_date

        while current_date <= end_date:
            date_key = current_date.strftime('%Y-%m-%d')

            # Vérifier si snapshot existe déjà
            existing = PortfolioSnapshot.query.filter(
                db.func.date(PortfolioSnapshot.date) == current_date.date()
            ).first()

            if existing and delete_old != 'o':
                snapshots_skipped += 1
                current_date += timedelta(days=1)
                continue

            # Calculer l'état du portefeuille à cette date
            transactions_until_date = [
                tx for tx in all_transactions if tx.date <= current_date
            ]

            if not transactions_until_date:
                current_date += timedelta(days=1)
                continue

            # Calculer les holdings
            holdings = {}
            for tx in transactions_until_date:
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

            # Filtrer holdings actifs
            active_holdings = {
                symbol: h for symbol, h in holdings.items()
                if h['volume'] > 0.00000001
            }

            if not active_holdings:
                current_date += timedelta(days=1)
                continue

            # Calculer la valorisation avec les PRIX HISTORIQUES RÉELS
            total_value = 0
            total_invested = 0
            details = {}

            missing_prices = []

            for symbol, h in active_holdings.items():
                # Récupérer le prix historique réel
                if symbol in historical_prices and date_key in historical_prices[symbol]:
                    historical_price = historical_prices[symbol][date_key]
                else:
                    # Prix manquant (essayer jour précédent)
                    historical_price = None
                    for days_back in range(1, 8):  # Chercher jusqu'à 7 jours avant
                        prev_date = current_date - timedelta(days=days_back)
                        prev_key = prev_date.strftime('%Y-%m-%d')
                        if symbol in historical_prices and prev_key in historical_prices[symbol]:
                            historical_price = historical_prices[symbol][prev_key]
                            break

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

            if missing_prices:
                print(f"  ⚠️  {date_key}: Prix manquants pour {', '.join(missing_prices)}")

            if total_value == 0:
                current_date += timedelta(days=1)
                continue

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

            if snapshots_created % 10 == 0:
                db.session.commit()
                print(f"  📈 {snapshots_created} snapshots créés... (dernier: {date_key})")

            current_date += timedelta(days=1)

        # Commit final
        db.session.commit()

        print(f"\n✅ Génération terminée avec prix historiques RÉELS !")
        print(f"  ✨ Créés : {snapshots_created}")
        print(f"  ⏭️  Ignorés : {snapshots_skipped}")
        print(f"  📊 Total : {PortfolioSnapshot.query.count()}")


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
