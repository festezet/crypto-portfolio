#!/usr/bin/env python3
"""
Crypto Portfolio Tracker - Mode CLI
Consultation du portefeuille et des prix depuis le terminal.

Usage:
    python3 cli.py holdings
    python3 cli.py prices [SYMBOL...]
    python3 cli.py stats
    python3 cli.py fiscal [--year YYYY]
    python3 cli.py export [--format csv|json]
    python3 cli.py import <file> [--exchange binance|kucoin]
"""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.app import create_app


def _get_app():
    """Create Flask app for DB context."""
    app = create_app()
    return app


def cmd_holdings(args):
    """Display current portfolio holdings."""
    app = _get_app()
    with app.app_context():
        from backend.services.portfolio import PortfolioService
        svc = PortfolioService()
        holdings = svc.get_holdings()

        if not holdings:
            print("Portefeuille vide.")
            return

        total_value = 0
        total_pnl = 0

        print(f"{'Symbol':<8} {'Volume':>12} {'PMP':>10} {'Prix':>10} {'Valeur':>12} {'P&L':>12} {'P&L%':>8}")
        print("-" * 76)

        for h in holdings:
            symbol = h.get('symbol', '?')
            volume = h.get('volume', 0)
            avg_price = h.get('avg_buy_price', 0)
            price = h.get('current_price', 0)
            value = h.get('current_value', 0)
            pnl = h.get('pnl', 0)
            pnl_pct = h.get('pnl_percent', 0)

            total_value += value
            total_pnl += pnl

            print(f"{symbol:<8} {volume:>12.4f} {avg_price:>10.2f} {price:>10.2f} {value:>12.2f} {pnl:>+12.2f} {pnl_pct:>+7.1f}%")

        print("-" * 76)
        pnl_sign = "+" if total_pnl >= 0 else ""
        print(f"{'TOTAL':<8} {'':>12} {'':>10} {'':>10} {total_value:>12.2f} {pnl_sign}{total_pnl:>11.2f}")

        if args.json:
            print("\n" + json.dumps(holdings, indent=2, default=str))


def cmd_prices(args):
    """Display current crypto prices."""
    app = _get_app()
    with app.app_context():
        from backend.services.price import price_service

        symbols = args.symbols
        if not symbols:
            from backend.services.portfolio import PortfolioService
            svc = PortfolioService()
            holdings = svc.get_holdings()
            symbols = [h['symbol'] for h in holdings]

        if not symbols:
            print("Aucun symbole. Specifiez des symboles ou ayez des holdings.")
            return

        prices = price_service.get_prices(symbols)

        print(f"{'Symbol':<8} {'Prix (EUR)':>12}")
        print("-" * 22)
        for symbol in sorted(symbols):
            price = prices.get(symbol, 0)
            if price:
                print(f"{symbol:<8} {price:>12.2f}")
            else:
                print(f"{symbol:<8} {'N/A':>12}")


def cmd_stats(args):
    """Display portfolio statistics."""
    app = _get_app()
    with app.app_context():
        from backend.services.portfolio import PortfolioService
        svc = PortfolioService()
        holdings = svc.get_holdings()

        if not holdings:
            print("Portefeuille vide.")
            return

        total_value = sum(h.get('current_value', 0) for h in holdings)
        total_invested = sum(h.get('total_invested', 0) for h in holdings)
        total_pnl = sum(h.get('pnl', 0) for h in holdings)
        n_assets = len(holdings)

        print("=== Statistiques Portefeuille ===")
        print(f"Nombre d'actifs  : {n_assets}")
        print(f"Valeur totale    : {total_value:,.2f} EUR")
        print(f"Total investi    : {total_invested:,.2f} EUR")
        print(f"P&L total        : {total_pnl:+,.2f} EUR")
        if total_invested > 0:
            pnl_pct = (total_pnl / total_invested) * 100
            print(f"P&L %            : {pnl_pct:+.1f}%")

        print(f"\nTop 3 positions :")
        for h in holdings[:3]:
            print(f"  {h.get('symbol', '?')}: {h.get('current_value', 0):,.2f} EUR")


def cmd_fiscal(args):
    """Display fiscal report (capital gains)."""
    app = _get_app()
    with app.app_context():
        from backend.services.fiscal import FiscalService
        svc = FiscalService()
        year = args.year

        report = svc.calculate_gains(year=year)

        if not report:
            print(f"Aucune donnee fiscale pour {year or 'toutes les annees'}.")
            return

        gains = report.get('gains', [])
        total_gain = report.get('total_gain', 0)
        total_loss = report.get('total_loss', 0)
        net = report.get('net_gain', total_gain + total_loss)

        title = f"Rapport fiscal {year}" if year else "Rapport fiscal global"
        print(f"=== {title} ===")
        print(f"Plus-values  : {total_gain:+,.2f} EUR")
        print(f"Moins-values : {total_loss:+,.2f} EUR")
        print(f"Net          : {net:+,.2f} EUR")
        print(f"Operations   : {len(gains)}")


def cmd_export(args):
    """Export portfolio data."""
    app = _get_app()
    with app.app_context():
        from backend.services.import_export import ImportExportService
        svc = ImportExportService()

        result = svc.export_transactions(format=args.format)
        if result and result.get('file_path'):
            print(f"Export: {result['file_path']}")
            print(f"Transactions exportees: {result.get('count', '?')}")
        else:
            print("Erreur export.", file=sys.stderr)
            sys.exit(1)


def cmd_import(args):
    """Import transactions from file."""
    app = _get_app()
    with app.app_context():
        from backend.services.import_export import ImportExportService
        svc = ImportExportService()

        filepath = args.file
        if not os.path.exists(filepath):
            print(f"Fichier non trouve: {filepath}", file=sys.stderr)
            sys.exit(1)

        result = svc.import_file(filepath, exchange=args.exchange)
        if result.get('success'):
            print(f"Import reussi: {result.get('count', '?')} transactions")
        else:
            print(f"Erreur import: {result.get('error', 'unknown')}", file=sys.stderr)
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Crypto Portfolio Tracker - CLI",
        prog="cli.py"
    )
    sub = parser.add_subparsers(dest='command', required=True)

    # holdings
    p_hold = sub.add_parser('holdings', help='Afficher les positions du portefeuille')
    p_hold.add_argument('--json', action='store_true', help='Sortie JSON brute')

    # prices
    p_prices = sub.add_parser('prices', help='Afficher les prix actuels')
    p_prices.add_argument('symbols', nargs='*', help='Symboles (ex: BTC ETH). Defaut: holdings')

    # stats
    sub.add_parser('stats', help='Statistiques du portefeuille')

    # fiscal
    p_fiscal = sub.add_parser('fiscal', help='Rapport fiscal (plus-values)')
    p_fiscal.add_argument('--year', type=int, help='Annee fiscale (defaut: toutes)')

    # export
    p_export = sub.add_parser('export', help='Exporter les transactions')
    p_export.add_argument('--format', choices=['csv', 'json'], default='csv')

    # import
    p_import = sub.add_parser('import', help='Importer des transactions')
    p_import.add_argument('file', help='Fichier a importer')
    p_import.add_argument('--exchange', choices=['binance', 'kucoin', 'generic'], default='generic')

    args = parser.parse_args()
    commands = {
        'holdings': cmd_holdings,
        'prices': cmd_prices,
        'stats': cmd_stats,
        'fiscal': cmd_fiscal,
        'export': cmd_export,
        'import': cmd_import,
    }
    commands[args.command](args)


if __name__ == '__main__':
    main()
