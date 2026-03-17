"""
Service de gestion du portefeuille
Calcul des positions, P&L, prix moyens pondérés
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
from collections import defaultdict
from sqlalchemy import func

from backend.models import db, Crypto, Transaction, PortfolioSnapshot
from backend.services.price import price_service


class PortfolioService:
    """Service pour la gestion du portefeuille"""

    def get_holdings(self) -> List[Dict[str, Any]]:
        """
        Calcule les positions actuelles du portefeuille

        Returns:
            Liste des positions avec détails (volume, PMP, valorisation, P&L)
        """
        transactions = Transaction.query.order_by(Transaction.date.asc()).all()
        holdings = self._compute_raw_holdings(transactions)

        # Filtrer les positions avec un volume positif significatif
        active_holdings = {
            symbol: h for symbol, h in holdings.items()
            if h['volume'] > 0.00000001
        }

        # Récupérer les prix actuels
        symbols = list(active_holdings.keys())
        prices = price_service.get_prices(symbols) if symbols else {}

        # Construire le résultat avec valorisation
        result = [
            self._enrich_holding(symbol, h, prices)
            for symbol, h in active_holdings.items()
        ]

        result.sort(key=lambda x: x['current_value'], reverse=True)
        return result

    def _compute_raw_holdings(self, transactions) -> Dict[str, Dict]:
        """Calcule les holdings bruts a partir des transactions"""
        holdings = {}

        for tx in transactions:
            symbol = tx.crypto.symbol
            if symbol not in holdings:
                holdings[symbol] = {
                    'crypto_id': tx.crypto_id,
                    'symbol': symbol,
                    'name': tx.crypto.name,
                    'volume': 0,
                    'total_cost': 0,
                    'total_fees': 0,
                    'first_buy_date': None,
                    'exchanges': set(),
                    'transactions_count': 0
                }

            h = holdings[symbol]
            h['transactions_count'] += 1
            h['exchanges'].add(tx.exchange)

            if tx.is_buy:
                h['volume'] += tx.volume
                h['total_cost'] += tx.total
                h['total_fees'] += tx.fee or 0
                if h['first_buy_date'] is None:
                    h['first_buy_date'] = tx.date

            elif tx.is_sell:
                if h['volume'] > 0:
                    cost_per_unit = h['total_cost'] / h['volume'] if h['volume'] > 0 else 0
                    sold_cost = cost_per_unit * tx.volume
                    h['total_cost'] -= sold_cost
                    h['volume'] -= tx.volume
                    h['total_fees'] += tx.fee or 0

        return holdings

    def _enrich_holding(self, symbol, h, prices) -> Dict[str, Any]:
        """Enrichit un holding brut avec prix, PMP et P&L"""
        current_price = prices.get(symbol, 0)
        volume = h['volume']
        total_cost = h['total_cost']
        total_fees = h['total_fees']

        pmp = total_cost / volume if volume > 0 else 0
        current_value = volume * current_price
        pnl_brut = current_value - total_cost
        pnl_net = pnl_brut - total_fees
        pnl_pct = (pnl_brut / total_cost * 100) if total_cost > 0 else 0
        change_24h = price_service.get_price_change_24h(symbol)

        return {
            'crypto_id': h['crypto_id'],
            'symbol': symbol,
            'name': h['name'],
            'volume': round(volume, 8),
            'pmp': round(pmp, 2),
            'current_price': round(current_price, 2),
            'total_invested': round(total_cost, 2),
            'total_fees': round(total_fees, 2),
            'current_value': round(current_value, 2),
            'pnl_brut': round(pnl_brut, 2),
            'pnl_net': round(pnl_net, 2),
            'pnl_pct': round(pnl_pct, 2),
            'change_24h': round(change_24h, 2) if change_24h else None,
            'first_buy_date': h['first_buy_date'].isoformat() if h['first_buy_date'] else None,
            'exchanges': list(h['exchanges']),
            'transactions_count': h['transactions_count']
        }

    def get_portfolio_summary(self) -> Dict[str, Any]:
        """
        Calcule le résumé global du portefeuille

        Returns:
            Dictionnaire avec totaux et métriques
        """
        holdings = self.get_holdings()

        total_value = sum(h['current_value'] for h in holdings)
        total_invested = sum(h['total_invested'] for h in holdings)
        total_fees = sum(h['total_fees'] for h in holdings)
        total_pnl_brut = sum(h['pnl_brut'] for h in holdings)
        total_pnl_net = total_pnl_brut - total_fees
        total_pnl_pct = (total_pnl_brut / total_invested * 100) if total_invested > 0 else 0

        # Répartition par exchange
        exchanges_allocation = defaultdict(float)
        for h in holdings:
            for exchange in h['exchanges']:
                exchanges_allocation[exchange] += h['current_value']

        # Répartition par crypto (top 10)
        crypto_allocation = [
            {'symbol': h['symbol'], 'value': h['current_value'],
             'pct': (h['current_value'] / total_value * 100) if total_value > 0 else 0}
            for h in holdings[:10]
        ]

        return {
            'total_value': round(total_value, 2),
            'total_invested': round(total_invested, 2),
            'total_fees': round(total_fees, 2),
            'total_pnl_brut': round(total_pnl_brut, 2),
            'total_pnl_net': round(total_pnl_net, 2),
            'total_pnl_pct': round(total_pnl_pct, 2),
            'holdings_count': len(holdings),
            'exchanges_allocation': dict(exchanges_allocation),
            'crypto_allocation': crypto_allocation,
            'last_updated': datetime.utcnow().isoformat()
        }

    def get_holding_details(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Récupère les détails d'une position spécifique

        Args:
            symbol: Symbole de la crypto

        Returns:
            Détails de la position ou None
        """
        holdings = self.get_holdings()
        for h in holdings:
            if h['symbol'].upper() == symbol.upper():
                # Ajouter l'historique des transactions
                crypto = Crypto.query.filter_by(symbol=symbol.upper()).first()
                if crypto:
                    transactions = Transaction.query.filter_by(
                        crypto_id=crypto.id
                    ).order_by(Transaction.date.desc()).all()

                    h['transactions'] = [tx.to_dict() for tx in transactions]

                return h
        return None

    def get_portfolio_history(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        Récupère l'historique des snapshots du portefeuille

        Args:
            days: Nombre de jours d'historique

        Returns:
            Liste des snapshots
        """
        from datetime import timedelta

        # Calculer la date de début en soustrayant le nombre de jours
        now = datetime.utcnow()
        from_date = now - timedelta(days=days)

        snapshots = PortfolioSnapshot.query.filter(
            PortfolioSnapshot.date >= from_date
        ).order_by(PortfolioSnapshot.date.asc()).all()

        return [s.to_dict() for s in snapshots]

    def create_snapshot(self) -> PortfolioSnapshot:
        """
        Crée un snapshot du portefeuille actuel

        Returns:
            Le snapshot créé
        """
        summary = self.get_portfolio_summary()
        holdings = self.get_holdings()

        details = {
            h['symbol']: {
                'volume': h['volume'],
                'price': h['current_price'],
                'value': h['current_value'],
                'pnl_pct': h['pnl_pct']
            }
            for h in holdings
        }

        return PortfolioSnapshot.create_snapshot(
            total_value=summary['total_value'],
            total_invested=summary['total_invested'],
            details=details
        )

    def get_transactions(self, crypto_id: int = None, exchange: str = None,
                         tx_type: str = None, limit: int = 100,
                         offset: int = 0) -> Dict[str, Any]:
        """
        Récupère les transactions avec filtres

        Returns:
            Dictionnaire avec transactions et pagination
        """
        query = Transaction.query

        if crypto_id:
            query = query.filter_by(crypto_id=crypto_id)
        if exchange:
            query = query.filter_by(exchange=exchange)
        if tx_type:
            query = query.filter_by(type=tx_type)

        total = query.count()
        transactions = query.order_by(
            Transaction.date.desc()
        ).offset(offset).limit(limit).all()

        return {
            'transactions': [tx.to_dict() for tx in transactions],
            'total': total,
            'limit': limit,
            'offset': offset
        }

    def add_transaction(self, data: Dict[str, Any]) -> Transaction:
        """
        Ajoute une nouvelle transaction

        Args:
            data: Données de la transaction

        Returns:
            Transaction créée
        """
        # Récupérer ou créer la crypto
        crypto = Crypto.get_or_create(data['symbol'])

        tx = Transaction(
            date=datetime.fromisoformat(data['date']) if isinstance(data['date'], str) else data['date'],
            type=data['type'],
            exchange=data.get('exchange', 'manual'),
            crypto_id=crypto.id,
            volume=float(data['volume']),
            price=float(data['price']),
            total=float(data['volume']) * float(data['price']),
            fee=float(data.get('fee', 0)),
            fee_currency=data.get('fee_currency', 'EUR'),
            pair=data.get('pair'),
            quote_currency=data.get('quote_currency', 'EUR'),
            notes=data.get('notes')
        )

        db.session.add(tx)
        db.session.commit()

        return tx

    def update_transaction(self, tx_id: int, data: Dict[str, Any]) -> Optional[Transaction]:
        """
        Met à jour une transaction existante

        Args:
            tx_id: ID de la transaction
            data: Nouvelles données

        Returns:
            Transaction mise à jour ou None
        """
        tx = Transaction.query.get(tx_id)
        if not tx:
            return None

        if 'date' in data:
            tx.date = datetime.fromisoformat(data['date']) if isinstance(data['date'], str) else data['date']
        if 'type' in data:
            tx.type = data['type']
        if 'exchange' in data:
            tx.exchange = data['exchange']
        if 'volume' in data:
            tx.volume = float(data['volume'])
        if 'price' in data:
            tx.price = float(data['price'])
        if 'fee' in data:
            tx.fee = float(data['fee'])
        if 'notes' in data:
            tx.notes = data['notes']

        # Recalculer le total
        tx.total = tx.volume * tx.price

        db.session.commit()

        return tx

    def delete_transaction(self, tx_id: int) -> bool:
        """
        Supprime une transaction

        Args:
            tx_id: ID de la transaction

        Returns:
            True si supprimée, False sinon
        """
        tx = Transaction.query.get(tx_id)
        if not tx:
            return False

        db.session.delete(tx)
        db.session.commit()

        return True


# Instance globale du service
portfolio_service = PortfolioService()
