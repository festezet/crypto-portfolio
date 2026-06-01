"""
Routes de l'API REST - Routes principales (portfolio, holdings, transactions, prices, cryptos)
"""
from flask import Blueprint, request
from datetime import datetime
from shared_lib.flask_helpers import success, error

from backend.services.portfolio import portfolio_service
from backend.services.price import price_service
from backend.models import Crypto, Transaction

api_bp = Blueprint('api', __name__, url_prefix='/api')


# ============================================================
# PORTFOLIO ENDPOINTS
# ============================================================

@api_bp.route('/portfolio', methods=['GET'])
def get_portfolio():
    """Récupère le résumé du portefeuille"""
    try:
        summary = portfolio_service.get_portfolio_summary()
        return success(summary)
    except Exception as e:
        return error(500, str(e))


@api_bp.route('/portfolio/history', methods=['GET'])
def get_portfolio_history():
    """Récupère l'historique du portefeuille"""
    days = request.args.get('days', 30, type=int)
    try:
        history = portfolio_service.get_portfolio_history(days=days)
        return success(history)
    except Exception as e:
        return error(500, str(e))


@api_bp.route('/portfolio/snapshot', methods=['POST'])
def create_snapshot():
    """Crée un snapshot du portefeuille"""
    try:
        snapshot = portfolio_service.create_snapshot()
        return success(snapshot.to_dict(), 201)
    except Exception as e:
        return error(500, str(e))


# ============================================================
# HOLDINGS ENDPOINTS
# ============================================================

@api_bp.route('/holdings', methods=['GET'])
def get_holdings():
    """Récupère les positions détaillées"""
    try:
        holdings = portfolio_service.get_holdings()
        return success(holdings)
    except Exception as e:
        return error(500, str(e))


@api_bp.route('/holdings/<symbol>', methods=['GET'])
def get_holding(symbol):
    """Récupère les détails d'une position"""
    try:
        holding = portfolio_service.get_holding_details(symbol)
        if holding:
            return success(holding)
        return error(404, 'Position not found')
    except Exception as e:
        return error(500, str(e))


# ============================================================
# TRANSACTIONS ENDPOINTS
# ============================================================

@api_bp.route('/transactions', methods=['GET'])
def get_transactions():
    """Récupère les transactions avec filtres"""
    crypto_id = request.args.get('crypto_id', type=int)
    exchange = request.args.get('exchange')
    tx_type = request.args.get('type')
    limit = request.args.get('limit', 100, type=int)
    offset = request.args.get('offset', 0, type=int)

    try:
        result = portfolio_service.get_transactions(
            crypto_id=crypto_id,
            exchange=exchange,
            tx_type=tx_type,
            limit=limit,
            offset=offset
        )
        return success(result)
    except Exception as e:
        return error(500, str(e))


@api_bp.route('/transactions', methods=['POST'])
def add_transaction():
    """Ajoute une nouvelle transaction"""
    data = request.get_json()

    required = ['symbol', 'type', 'volume', 'price', 'date']
    for field in required:
        if field not in data:
            return error(400, f'Missing field: {field}')

    try:
        tx = portfolio_service.add_transaction(data)
        return success(tx.to_dict(), 201)
    except Exception as e:
        return error(500, str(e))


@api_bp.route('/transactions/<int:tx_id>', methods=['PUT'])
def update_transaction(tx_id):
    """Met à jour une transaction"""
    data = request.get_json()

    try:
        tx = portfolio_service.update_transaction(tx_id, data)
        if tx:
            return success(tx.to_dict())
        return error(404, 'Transaction not found')
    except Exception as e:
        return error(500, str(e))


@api_bp.route('/transactions/<int:tx_id>', methods=['DELETE'])
def delete_transaction(tx_id):
    """Supprime une transaction"""
    try:
        if portfolio_service.delete_transaction(tx_id):
            return success()
        return error(404, 'Transaction not found')
    except Exception as e:
        return error(500, str(e))


# ============================================================
# PRICES ENDPOINTS
# ============================================================

@api_bp.route('/prices', methods=['GET'])
def get_prices():
    """Récupère les prix actuels"""
    symbols = request.args.get('symbols', '').split(',')
    symbols = [s.strip().upper() for s in symbols if s.strip()]

    if not symbols:
        holdings = portfolio_service.get_holdings()
        symbols = [h['symbol'] for h in holdings]

    try:
        prices = price_service.get_prices(symbols)
        return success(prices)
    except Exception as e:
        return error(500, str(e))


@api_bp.route('/prices/<symbol>', methods=['GET'])
def get_price(symbol):
    """Récupère le prix d'une crypto"""
    try:
        price = price_service.get_price(symbol.upper())
        change = price_service.get_price_change_24h(symbol.upper())
        return success({
            'symbol': symbol.upper(),
            'price': price,
            'change_24h': change
        })
    except Exception as e:
        return error(500, str(e))


# ============================================================
# CRYPTOS ENDPOINTS
# ============================================================

@api_bp.route('/cryptos', methods=['GET'])
def get_cryptos():
    """Récupère la liste des cryptos"""
    try:
        cryptos = Crypto.query.all()
        return success([c.to_dict() for c in cryptos])
    except Exception as e:
        return error(500, str(e))


@api_bp.route('/cryptos', methods=['POST'])
def add_crypto():
    """Ajoute une crypto"""
    data = request.get_json()

    if 'symbol' not in data:
        return error(400, 'Missing symbol')

    try:
        crypto = Crypto.get_or_create(
            symbol=data['symbol'],
            name=data.get('name'),
            coingecko_id=data.get('coingecko_id')
        )
        return success(crypto.to_dict(), 201)
    except Exception as e:
        return error(500, str(e))
