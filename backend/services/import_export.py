"""
Service d'import/export de fichiers
Supporte les formats Binance, Kucoin et CSV personnalisé
"""
import csv
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import io

from backend.models import db, Crypto, Transaction
from backend.config import IMPORTS_DIR, EXPORTS_DIR


class ImportExportService:
    """Service pour l'import et l'export de données"""

    # Mapping des colonnes Binance Trade History
    BINANCE_COLUMNS = {
        'Date(UTC)': 'date',
        'Pair': 'pair',
        'Side': 'type',
        'Price': 'price',
        'Executed': 'volume',
        'Amount': 'total',
        'Fee': 'fee',
    }

    # Mapping des colonnes Kucoin Trade History
    KUCOIN_COLUMNS = {
        'tradeCreatedAt': 'date',
        'symbol': 'pair',
        'side': 'type',
        'price': 'price',
        'size': 'volume',
        'funds': 'total',
        'fee': 'fee',
        'feeCurrency': 'fee_currency',
    }

    def import_binance_csv(self, file_content: str, filename: str = None) -> Dict[str, Any]:
        """
        Importe un fichier CSV d'historique Binance

        Format attendu:
        Date(UTC),Pair,Side,Price,Executed,Amount,Fee

        Args:
            file_content: Contenu du fichier CSV
            filename: Nom du fichier pour traçabilité

        Returns:
            Résultat de l'import avec stats
        """
        reader = csv.DictReader(io.StringIO(file_content))
        imported = 0
        errors = []
        skipped = 0

        for row_num, row in enumerate(reader, start=2):
            try:
                result = self._process_binance_row(row, filename)
                if result == 'skipped':
                    skipped += 1
                elif result:
                    db.session.add(result)
                    imported += 1
            except Exception as e:
                errors.append(f"Ligne {row_num}: {str(e)}")

        if imported > 0:
            db.session.commit()

        return {
            'success': True,
            'imported': imported,
            'skipped': skipped,
            'errors': errors,
            'source': 'binance'
        }

    def _process_binance_row(self, row, filename):
        """Traite une ligne CSV Binance et retourne une Transaction, 'skipped', ou leve une exception"""
        date_str = row.get('Date(UTC)', '')
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            date = datetime.strptime(date_str, '%Y-%m-%d')

        pair = row.get('Pair', '')
        symbol = self._extract_symbol_from_pair(pair)

        side = row.get('Side', '').upper()
        tx_type = 'BUY' if side == 'BUY' else 'SELL'

        price = self._parse_number(row.get('Price', '0'))
        volume = self._parse_number(row.get('Executed', '0').split()[0])
        total = self._parse_number(row.get('Amount', '0').split()[0])
        fee = self._parse_number(row.get('Fee', '0').split()[0])

        existing = Transaction.query.filter_by(
            date=date, type=tx_type, volume=volume, exchange='binance'
        ).first()

        if existing:
            return 'skipped'

        crypto = Crypto.get_or_create(symbol)

        return Transaction(
            date=date, type=tx_type, exchange='binance',
            crypto_id=crypto.id, volume=volume, price=price,
            total=total, fee=fee, pair=pair,
            imported_from=filename or 'binance_import'
        )

    def import_kucoin_csv(self, file_content: str, filename: str = None) -> Dict[str, Any]:
        """
        Importe un fichier CSV d'historique Kucoin

        Format attendu:
        tradeCreatedAt,symbol,side,price,size,funds,fee,feeCurrency

        Args:
            file_content: Contenu du fichier CSV
            filename: Nom du fichier pour traçabilité

        Returns:
            Résultat de l'import avec stats
        """
        reader = csv.DictReader(io.StringIO(file_content))
        imported = 0
        errors = []
        skipped = 0

        for row_num, row in enumerate(reader, start=2):
            try:
                result = self._process_kucoin_row(row, filename)
                if result == 'skipped':
                    skipped += 1
                elif result:
                    db.session.add(result)
                    imported += 1
            except Exception as e:
                errors.append(f"Ligne {row_num}: {str(e)}")

        if imported > 0:
            db.session.commit()

        return {
            'success': True,
            'imported': imported,
            'skipped': skipped,
            'errors': errors,
            'source': 'kucoin'
        }

    def _process_kucoin_row(self, row, filename):
        """Traite une ligne CSV Kucoin et retourne une Transaction, 'skipped', ou leve une exception"""
        date_str = row.get('tradeCreatedAt', '')
        try:
            date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except ValueError:
            date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')

        pair = row.get('symbol', '').replace('-', '/')
        symbol = pair.split('/')[0] if '/' in pair else pair.split('-')[0]

        side = row.get('side', '').lower()
        tx_type = 'BUY' if side == 'buy' else 'SELL'

        price = self._parse_number(row.get('price', '0'))
        volume = self._parse_number(row.get('size', '0'))
        total = self._parse_number(row.get('funds', '0'))
        fee = self._parse_number(row.get('fee', '0'))
        fee_currency = row.get('feeCurrency', 'USDT')

        existing = Transaction.query.filter_by(
            date=date, type=tx_type, volume=volume, exchange='kucoin'
        ).first()

        if existing:
            return 'skipped'

        crypto = Crypto.get_or_create(symbol)

        return Transaction(
            date=date, type=tx_type, exchange='kucoin',
            crypto_id=crypto.id, volume=volume, price=price,
            total=total, fee=fee, fee_currency=fee_currency,
            pair=pair, imported_from=filename or 'kucoin_import'
        )

    def import_generic_csv(self, file_content: str, mapping: Dict[str, str],
                           exchange: str = 'manual', filename: str = None) -> Dict[str, Any]:
        """
        Importe un fichier CSV avec un mapping personnalisé

        Args:
            file_content: Contenu du fichier CSV
            mapping: Dictionnaire de mapping colonnes -> champs
                     Ex: {'Date': 'date', 'Crypto': 'symbol', 'Qty': 'volume', ...}
            exchange: Nom de l'exchange
            filename: Nom du fichier

        Returns:
            Résultat de l'import
        """
        reader = csv.DictReader(io.StringIO(file_content))
        imported = 0
        errors = []
        skipped = 0

        for row_num, row in enumerate(reader, start=2):
            try:
                result = self._process_generic_row(row, row_num, mapping, exchange, filename)
                if isinstance(result, str) and result.startswith('skip:'):
                    errors.append(result[5:])
                    continue
                if result:
                    db.session.add(result)
                    imported += 1
            except Exception as e:
                errors.append(f"Ligne {row_num}: {str(e)}")

        if imported > 0:
            db.session.commit()

        return {
            'success': True,
            'imported': imported,
            'skipped': skipped,
            'errors': errors,
            'source': exchange
        }

    def _process_generic_row(self, row, row_num, mapping, exchange, filename):
        """Traite une ligne CSV generique et retourne une Transaction ou 'skip:reason'"""
        mapped = {}
        for csv_col, field in mapping.items():
            if csv_col in row:
                mapped[field] = row[csv_col]

        date = self._parse_date(mapped.get('date', ''))

        symbol = mapped.get('symbol', '').upper()
        if not symbol:
            return f"skip:Ligne {row_num}: Symbole manquant"

        tx_type = mapped.get('type', 'BUY').upper()
        if tx_type not in ['BUY', 'SELL', 'TRANSFER_IN', 'TRANSFER_OUT']:
            tx_type = 'BUY'

        volume = self._parse_number(mapped.get('volume', '0'))
        price = self._parse_number(mapped.get('price', '0'))
        total = self._parse_number(mapped.get('total', str(volume * price)))
        fee = self._parse_number(mapped.get('fee', '0'))

        if volume <= 0:
            return f"skip:Ligne {row_num}: Volume invalide"

        crypto = Crypto.get_or_create(symbol)

        return Transaction(
            date=date, type=tx_type, exchange=exchange,
            crypto_id=crypto.id, volume=volume, price=price,
            total=total if total > 0 else volume * price,
            fee=fee, notes=mapped.get('notes'),
            imported_from=filename or f'{exchange}_import'
        )

    def detect_format(self, file_content: str) -> Optional[str]:
        """
        Détecte automatiquement le format du fichier CSV

        Returns:
            'binance', 'kucoin', ou None si inconnu
        """
        try:
            reader = csv.DictReader(io.StringIO(file_content))
            headers = reader.fieldnames or []

            # Vérifier les colonnes Binance
            binance_cols = ['Date(UTC)', 'Pair', 'Side', 'Price', 'Executed']
            if all(col in headers for col in binance_cols):
                return 'binance'

            # Vérifier les colonnes Kucoin
            kucoin_cols = ['tradeCreatedAt', 'symbol', 'side', 'price', 'size']
            if all(col in headers for col in kucoin_cols):
                return 'kucoin'

        except Exception:
            pass

        return None

    def export_transactions_csv(self, crypto_id: int = None,
                                 exchange: str = None,
                                 from_date: datetime = None,
                                 to_date: datetime = None) -> str:
        """
        Exporte les transactions en CSV

        Returns:
            Contenu CSV
        """
        query = Transaction.query

        if crypto_id:
            query = query.filter_by(crypto_id=crypto_id)
        if exchange:
            query = query.filter_by(exchange=exchange)
        if from_date:
            query = query.filter(Transaction.date >= from_date)
        if to_date:
            query = query.filter(Transaction.date <= to_date)

        transactions = query.order_by(Transaction.date.asc()).all()

        output = io.StringIO()
        writer = csv.writer(output)

        # En-têtes
        writer.writerow([
            'Date', 'Type', 'Exchange', 'Symbol', 'Volume', 'Price',
            'Total', 'Fee', 'Fee Currency', 'Pair', 'Notes'
        ])

        # Données
        for tx in transactions:
            writer.writerow([
                tx.date.isoformat() if tx.date else '',
                tx.type,
                tx.exchange,
                tx.crypto.symbol if tx.crypto else '',
                tx.volume,
                tx.price,
                tx.total,
                tx.fee,
                tx.fee_currency,
                tx.pair or '',
                tx.notes or ''
            ])

        return output.getvalue()

    def export_transactions_json(self, crypto_id: int = None,
                                  exchange: str = None) -> str:
        """
        Exporte les transactions en JSON

        Returns:
            JSON string
        """
        query = Transaction.query

        if crypto_id:
            query = query.filter_by(crypto_id=crypto_id)
        if exchange:
            query = query.filter_by(exchange=exchange)

        transactions = query.order_by(Transaction.date.asc()).all()

        return json.dumps({
            'exported_at': datetime.utcnow().isoformat(),
            'transactions': [tx.to_dict() for tx in transactions]
        }, indent=2)

    def _extract_symbol_from_pair(self, pair: str) -> str:
        """Extrait le symbole de la crypto d'une paire de trading"""
        # Ex: BTCUSDT -> BTC, ETHBTC -> ETH
        quote_currencies = ['USDT', 'USDC', 'BUSD', 'EUR', 'USD', 'BTC', 'ETH', 'BNB']

        pair = pair.upper()
        for quote in quote_currencies:
            if pair.endswith(quote):
                return pair[:-len(quote)]

        return pair

    def _parse_number(self, value: str) -> float:
        """Parse une valeur numérique (gère les virgules européennes)"""
        if not value:
            return 0.0
        # Nettoyer la valeur
        value = str(value).strip()
        # Gérer le format européen (1.234,56 -> 1234.56)
        if ',' in value and '.' in value:
            if value.index(',') > value.index('.'):
                # Format européen: 1.234,56
                value = value.replace('.', '').replace(',', '.')
            else:
                # Format US: 1,234.56
                value = value.replace(',', '')
        elif ',' in value:
            value = value.replace(',', '.')

        try:
            return float(value)
        except ValueError:
            return 0.0

    def _parse_date(self, date_str: str) -> datetime:
        """Parse une date dans différents formats"""
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d',
            '%d/%m/%Y %H:%M:%S',
            '%d/%m/%Y',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%Y-%m-%dT%H:%M:%S%z',
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        # Essayer ISO format
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except ValueError:
            pass

        raise ValueError(f"Format de date non reconnu: {date_str}")


# Instance globale du service
import_export_service = ImportExportService()
