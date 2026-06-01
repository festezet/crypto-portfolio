#!/usr/bin/env python3
"""
Inject real Kucoin + Binance transactions into portfolio.db,
replacing the 103 dummy DCA transactions.

Sources:
- /tmp/billing_history/ (Kucoin export)
- Binance screenshot data (BTC position)

Usage:
    python3 scripts/inject_real_transactions.py [--dry-run]
"""
import csv
import sqlite3
import sys
import os
from datetime import datetime, timedelta
from collections import defaultdict

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'portfolio.db')
BILLING_DIR = '/tmp/billing_history'

# EUR/USDT rate from the May 27 2025 USDT-EUR spot buy (0.8798 actual, plan says 0.8807)
EUR_USDT_RATE = 0.8807

# Binance BTC position from screenshot
BINANCE_BTC_VOLUME = 0.06537694
BINANCE_BTC_PRICE_USD = 107413.0
# USD→EUR approximate rate at time of purchase (Nov 2025)
USD_EUR_RATE = 0.9350
BINANCE_BTC_PRICE_EUR = round(BINANCE_BTC_PRICE_USD * USD_EUR_RATE, 2)  # ~100,431 EUR

# Cryptos to add (symbol, name, coingecko_id)
MISSING_CRYPTOS = [
    ('SUI', 'Sui', 'sui'),
    ('AVAX', 'Avalanche', 'avalanche-2'),
    ('PUMP', 'PumpFun', 'pump-fun'),
    ('UNI', 'Uniswap', 'uniswap'),
    ('DOGE', 'Dogecoin', 'dogecoin'),
    ('KCS', 'KuCoin Token', 'kucoin-shares'),
    ('MOVR', 'Moonriver', 'moonriver'),
]


def read_csv(filename):
    """Read a CSV file from the billing directory, handling BOM."""
    path = os.path.join(BILLING_DIR, filename)
    with open(path, encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def parse_time(s):
    """Parse Kucoin timestamp (UTC+02:00 timezone, stored as-is)."""
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f'):
        try:
            return datetime.strptime(s.strip(), fmt)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse time: {s}")


def time_close(t1, t2, max_seconds=3):
    """Check if two timestamps are within max_seconds of each other."""
    return abs((t1 - t2).total_seconds()) <= max_seconds


def get_crypto_id(conn, symbol):
    """Get crypto ID by symbol, or None."""
    row = conn.execute("SELECT id FROM cryptos WHERE symbol = ?", (symbol,)).fetchone()
    return row[0] if row else None


def ensure_cryptos(conn):
    """Add missing cryptos to the cryptos table."""
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    added = []
    for symbol, name, cg_id in MISSING_CRYPTOS:
        existing = get_crypto_id(conn, symbol)
        if not existing:
            conn.execute(
                "INSERT INTO cryptos (symbol, name, coingecko_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (symbol, name, cg_id, now, now)
            )
            added.append(symbol)
    if added:
        print(f"  Added cryptos: {', '.join(added)}")
    else:
        print("  All cryptos already exist")


def insert_transaction(conn, date, tx_type, exchange, crypto_id, volume, price_eur,
                       fee=0, fee_currency='EUR', pair=None, quote_currency='EUR',
                       notes=None, imported_from=None, external_id=None):
    """Insert a single transaction."""
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    total = round(volume * price_eur, 8)
    conn.execute("""
        INSERT INTO transactions
        (date, type, exchange, crypto_id, volume, price, total, fee, fee_currency,
         pair, quote_currency, notes, imported_from, external_id, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (date, tx_type, exchange, crypto_id, volume, round(price_eur, 8), total,
          fee, fee_currency, pair, quote_currency, notes, imported_from, external_id, now, now))


def process_convert_market(conn):
    """
    Process Convert Market trades:
    - Funding Account USDT withdrawals (Convert Market) = USDT cost per trade
    - Trading Account crypto deposits (Convert Market) = crypto received
    - Match by timestamp (±3s)
    """
    print("\n--- Convert Market BUYs ---")

    # Parse Funding Account Convert Market USDT withdrawals
    funding_rows = read_csv('Account History_Funding Account.csv')
    funding_usdt = []
    for r in funding_rows:
        if r['Type'] == 'Convert Market' and r['Currency'] == 'USDT' and r['Side'] == 'Withdrawal':
            funding_usdt.append({
                'time': parse_time(r['Time(UTC+02:00)']),
                'amount_usdt': float(r['Amount']),
                'matched': False,
            })

    # Parse Trading Account Convert Market crypto deposits
    trading_rows = read_csv('Account History_Trading Account.csv')
    crypto_deposits = []
    for r in trading_rows:
        if r['Type'] == 'Convert Market' and r['Side'] == 'Deposit':
            currency = r['Currency']
            # Skip USDT deposits (BNB→USDT conversion result) and KCS (dust)
            if currency in ('USDT', 'KCS'):
                continue
            crypto_deposits.append({
                'time': parse_time(r['Time(UTC+02:00)']),
                'currency': currency,
                'amount': float(r['Amount']),
                'matched_usdt': 0.0,
            })

    # Also get Trading Account Convert Market USDT withdrawals (BNB-sale-funded trades)
    trading_usdt = []
    for r in trading_rows:
        if r['Type'] == 'Convert Market' and r['Currency'] == 'USDT' and r['Side'] == 'Withdrawal':
            trading_usdt.append({
                'time': parse_time(r['Time(UTC+02:00)']),
                'amount_usdt': float(r['Amount']),
                'matched': False,
            })

    # Match: for each crypto deposit, find matching USDT sources
    for dep in crypto_deposits:
        # First try Funding Account
        for fu in funding_usdt:
            if not fu['matched'] and time_close(dep['time'], fu['time']):
                dep['matched_usdt'] += fu['amount_usdt']
                fu['matched'] = True
                break
        # Then try Trading Account USDT withdrawals
        for tu in trading_usdt:
            if not tu['matched'] and time_close(dep['time'], tu['time']):
                dep['matched_usdt'] += tu['amount_usdt']
                tu['matched'] = True
                break

    # Insert matched BUY transactions
    count = 0
    unmatched = []
    for dep in crypto_deposits:
        crypto_id = get_crypto_id(conn, dep['currency'])
        if not crypto_id:
            print(f"  WARNING: No crypto_id for {dep['currency']}, skipping")
            continue

        if dep['matched_usdt'] <= 0:
            unmatched.append(dep)
            continue

        price_eur = (dep['matched_usdt'] * EUR_USDT_RATE) / dep['amount']
        total_eur = dep['matched_usdt'] * EUR_USDT_RATE
        date_str = dep['time'].strftime('%Y-%m-%d %H:%M:%S')

        insert_transaction(
            conn, date_str, 'BUY', 'kucoin', crypto_id,
            dep['amount'], price_eur,
            pair=f"{dep['currency']}/USDT", quote_currency='EUR',
            notes=f"Convert Market: {dep['matched_usdt']:.2f} USDT × {EUR_USDT_RATE}",
            imported_from='kucoin_billing_history'
        )
        count += 1

    if unmatched:
        print(f"  WARNING: {len(unmatched)} unmatched deposits:")
        for u in unmatched:
            print(f"    {u['currency']} {u['amount']} at {u['time']}")

    print(f"  Inserted {count} Convert Market BUY transactions")
    return count


def process_dust_to_kcs(conn):
    """
    Process "Convert Dust to KCS" entries from Trading Account.
    Small leftover amounts of various cryptos were converted to KCS.
    Record as BUY at ~0 cost (dust).
    """
    print("\n--- Convert Dust to KCS ---")

    trading_rows = read_csv('Account History_Trading Account.csv')
    total_kcs = 0.0
    for r in trading_rows:
        if r['Type'] == 'Convert Dust to KCS' and r['Currency'] == 'KCS' and r['Side'] == 'Deposit':
            total_kcs += float(r['Amount'])

    if total_kcs > 0:
        crypto_id = get_crypto_id(conn, 'KCS')
        # Price ~0 since it's dust conversion (negligible value)
        insert_transaction(
            conn, '2025-12-03 00:59:10', 'BUY', 'kucoin', crypto_id,
            total_kcs, 0.0,
            notes=f"Convert Dust to KCS: {total_kcs:.8f} KCS",
            imported_from='kucoin_billing_history'
        )
        print(f"  BUY {total_kcs:.8f} KCS (dust conversion, cost ~0)")
        return 1
    return 0


def process_bnb_sell(conn):
    """
    Process BNB → USDT conversion via Convert Market (Oct 6 2025).
    Trading Account: BNB Withdrawal 0.42830996, USDT Deposit 517.52 at same time.
    """
    print("\n--- BNB → USDT Sell ---")

    trading_rows = read_csv('Account History_Trading Account.csv')

    # Find BNB withdrawal (Convert Market)
    for r in trading_rows:
        if (r['Type'] == 'Convert Market' and r['Currency'] == 'BNB'
                and r['Side'] == 'Withdrawal'):
            bnb_amount = float(r['Amount'])
            bnb_time = parse_time(r['Time(UTC+02:00)'])

            # Find matching USDT deposit
            usdt_amount = None
            for r2 in trading_rows:
                if (r2['Type'] == 'Convert Market' and r2['Currency'] == 'USDT'
                        and r2['Side'] == 'Deposit'
                        and time_close(parse_time(r2['Time(UTC+02:00)']), bnb_time)):
                    usdt_amount = float(r2['Amount'])
                    break

            if usdt_amount:
                price_usdt = usdt_amount / bnb_amount
                price_eur = price_usdt * EUR_USDT_RATE
                date_str = bnb_time.strftime('%Y-%m-%d %H:%M:%S')

                crypto_id = get_crypto_id(conn, 'BNB')
                insert_transaction(
                    conn, date_str, 'SELL', 'kucoin', crypto_id,
                    bnb_amount, price_eur,
                    pair='BNB/USDT', quote_currency='EUR',
                    notes=f"Convert Market BNB→USDT: {usdt_amount:.2f} USDT",
                    imported_from='kucoin_billing_history'
                )
                print(f"  BNB SELL: {bnb_amount} BNB at {price_eur:.2f} EUR ({usdt_amount:.2f} USDT)")
                return 1

    print("  WARNING: BNB sell not found")
    return 0


def process_spot_orders(conn):
    """
    Process Spot Orders (filled):
    - BUYs: BTC-EUR, ETH-EUR, DOT-USDT
    - SELLs: XMR-USDT, HYPE-USDT, KCS-USDT
    """
    print("\n--- Spot Orders ---")

    rows = read_csv('Spot Orders_Filled Orders.csv')
    count_buy = 0
    count_sell = 0

    for r in rows:
        symbol = r['Symbol']       # e.g. BTC-EUR, DOT-USDT
        side = r['Side']           # BUY or SELL
        filled_amount = float(r['Filled Amount'])  # crypto quantity
        avg_price = float(r['Avg. Filled Price'])  # price per unit
        filled_volume = float(r['Filled Volume'])  # total in quote currency
        fee = float(r['Fee'])
        fee_currency = r['Fee Currency']
        date_str = r['Filled Time(UTC+02:00)']

        # Parse symbol
        parts = symbol.split('-')
        crypto_symbol = parts[0]
        quote = parts[1]

        # Skip USDT-EUR buy (that's just buying stablecoins, not a crypto investment)
        if crypto_symbol == 'USDT':
            print(f"  Skipping USDT-EUR buy ({filled_amount} USDT)")
            continue

        crypto_id = get_crypto_id(conn, crypto_symbol)
        if not crypto_id:
            print(f"  WARNING: No crypto_id for {crypto_symbol}")
            continue

        # Determine EUR price
        if quote == 'EUR':
            price_eur = avg_price
            fee_eur = fee if fee_currency == 'EUR' else fee * EUR_USDT_RATE
        elif quote == 'USDT':
            price_eur = avg_price * EUR_USDT_RATE
            fee_eur = fee * EUR_USDT_RATE if fee_currency == 'USDT' else fee
        else:
            print(f"  WARNING: Unknown quote currency {quote} for {symbol}")
            continue

        tx_type = side.upper()  # BUY or SELL

        insert_transaction(
            conn, date_str, tx_type, 'kucoin', crypto_id,
            filled_amount, price_eur,
            fee=round(fee_eur, 8), fee_currency='EUR',
            pair=symbol, quote_currency=quote,
            notes=f"Spot: {filled_amount} @ {avg_price} {quote}",
            imported_from='kucoin_spot_orders'
        )

        if tx_type == 'BUY':
            count_buy += 1
            print(f"  BUY {filled_amount} {crypto_symbol} @ {price_eur:.2f} EUR ({symbol})")
        else:
            count_sell += 1
            print(f"  SELL {filled_amount} {crypto_symbol} @ {price_eur:.2f} EUR ({symbol})")

    print(f"  Inserted {count_buy} Spot BUYs, {count_sell} Spot SELLs")
    return count_buy + count_sell


def process_withdrawals(conn):
    """
    Process blockchain withdrawals (TRANSFER_OUT to Kraken/Binance).
    Skip USDT withdrawals (not crypto transfers to external exchanges).
    """
    print("\n--- Blockchain Withdrawals (TRANSFER_OUT) ---")

    rows = read_csv('Deposit_Withdrawal History_Withdrawal History.csv')
    count = 0

    for r in rows:
        coin = r['Coin']
        amount = float(r['Amount'])
        fee = float(r['Fee'])
        date_str = r['Time(UTC+02:00)']
        status = r['Status']
        network = r['Transfer Network']

        # Skip USDT withdrawals and failed transfers
        if coin == 'USDT' or status != 'SUCCESS':
            continue

        crypto_id = get_crypto_id(conn, coin)
        if not crypto_id:
            print(f"  WARNING: No crypto_id for {coin}")
            continue

        # For TRANSFER_OUT, price is 0 (no sale, just moving coins)
        # But we record the amount transferred
        insert_transaction(
            conn, date_str, 'TRANSFER_OUT', 'kucoin', crypto_id,
            amount, 0,  # price=0 for transfers
            fee=fee, fee_currency=coin,
            pair=None, quote_currency='EUR',
            notes=f"Withdrawal to external wallet via {network}",
            imported_from='kucoin_withdrawal_history'
        )
        count += 1
        print(f"  TRANSFER_OUT {amount} {coin} (fee: {fee} {coin}, network: {network})")

    print(f"  Inserted {count} TRANSFER_OUT transactions")
    return count


def process_binance_btc(conn):
    """
    Add Binance BTC position from screenshot.
    0.06537694 BTC at cost price $107,413 per BTC.
    """
    print("\n--- Binance BTC BUY ---")

    crypto_id = get_crypto_id(conn, 'BTC')
    date_str = '2025-11-15 12:00:00'  # approximate purchase date

    insert_transaction(
        conn, date_str, 'BUY', 'binance', crypto_id,
        BINANCE_BTC_VOLUME, BINANCE_BTC_PRICE_EUR,
        pair='BTC/USD', quote_currency='USD',
        notes=f"Binance screenshot: cost ${BINANCE_BTC_PRICE_USD:.0f}/BTC, {BINANCE_BTC_VOLUME} BTC",
        imported_from='binance_screenshot'
    )
    total_eur = BINANCE_BTC_VOLUME * BINANCE_BTC_PRICE_EUR
    print(f"  BUY {BINANCE_BTC_VOLUME} BTC @ {BINANCE_BTC_PRICE_EUR:.2f} EUR (${BINANCE_BTC_PRICE_USD:.0f})")
    print(f"  Total: {total_eur:.2f} EUR")
    return 1


def verify(conn):
    """Print verification summary."""
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)

    # Count by type
    for tx_type in ('BUY', 'SELL', 'TRANSFER_OUT'):
        row = conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(volume), 0) FROM transactions WHERE type = ?",
            (tx_type,)
        ).fetchone()
        print(f"  {tx_type}: {row[0]} transactions")

    # Holdings per crypto (BUY - SELL - TRANSFER_OUT)
    print("\n  Holdings (calculated):")
    cryptos = conn.execute("SELECT id, symbol FROM cryptos ORDER BY symbol").fetchall()
    for cid, symbol in cryptos:
        buys = conn.execute(
            "SELECT COALESCE(SUM(volume), 0) FROM transactions WHERE crypto_id = ? AND type IN ('BUY', 'TRANSFER_IN')",
            (cid,)
        ).fetchone()[0]
        sells = conn.execute(
            "SELECT COALESCE(SUM(volume), 0) FROM transactions WHERE crypto_id = ? AND type IN ('SELL', 'TRANSFER_OUT')",
            (cid,)
        ).fetchone()[0]
        holding = buys - sells
        if abs(holding) > 1e-10 or buys > 0:
            cost = conn.execute(
                "SELECT COALESCE(SUM(total), 0) FROM transactions WHERE crypto_id = ? AND type = 'BUY'",
                (cid,)
            ).fetchone()[0]
            print(f"    {symbol:6s}: bought={buys:.8f}, sold/out={sells:.8f}, "
                  f"holding={holding:.8f}, cost={cost:.2f} EUR")

    total_cost = conn.execute(
        "SELECT COALESCE(SUM(total), 0) FROM transactions WHERE type = 'BUY'"
    ).fetchone()[0]
    total_sold = conn.execute(
        "SELECT COALESCE(SUM(total), 0) FROM transactions WHERE type = 'SELL'"
    ).fetchone()[0]
    print(f"\n  Total invested (BUY): {total_cost:.2f} EUR")
    print(f"  Total sold (SELL):    {total_sold:.2f} EUR")
    print(f"  Total tx count: {conn.execute('SELECT COUNT(*) FROM transactions').fetchone()[0]}")


def main():
    dry_run = '--dry-run' in sys.argv

    print("=" * 60)
    print("INJECTING REAL TRANSACTIONS INTO portfolio.db")
    print("=" * 60)

    if dry_run:
        print("*** DRY RUN MODE - no changes will be saved ***\n")

    conn = sqlite3.connect(os.path.abspath(DB_PATH))
    conn.row_factory = sqlite3.Row

    try:
        # Step 1: Purge dummy transactions
        old_count = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        print(f"\nStep 1: Purging {old_count} dummy transactions...")
        conn.execute("DELETE FROM transactions")
        print(f"  Deleted {old_count} rows")

        # Step 2: Ensure all cryptos exist
        print("\nStep 2: Adding missing cryptos...")
        ensure_cryptos(conn)

        # Step 3: Convert Market BUYs
        print("\nStep 3: Injecting Convert Market BUYs...")
        n1 = process_convert_market(conn)

        # Step 3b: Dust to KCS conversion
        n1b_dust = process_dust_to_kcs(conn)

        # Step 3c: BNB sell (Convert Market)
        n1b = process_bnb_sell(conn)

        # Step 4: Spot Orders (BUYs + SELLs)
        print("\nStep 4: Injecting Spot Orders...")
        n2 = process_spot_orders(conn)

        # Step 5: Blockchain Withdrawals (TRANSFER_OUT)
        print("\nStep 5: Injecting Withdrawals (TRANSFER_OUT)...")
        n3 = process_withdrawals(conn)

        # Step 6: Binance BTC
        print("\nStep 6: Injecting Binance BTC BUY...")
        n4 = process_binance_btc(conn)

        total = n1 + n1b_dust + n1b + n2 + n3 + n4
        print(f"\nTotal inserted: {total} transactions")

        # Verify
        verify(conn)

        if dry_run:
            print("\n*** DRY RUN - rolling back ***")
            conn.rollback()
        else:
            conn.commit()
            print("\n*** Changes committed ***")

    except Exception as e:
        conn.rollback()
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == '__main__':
    main()
