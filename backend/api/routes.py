"""
Routes de l'API REST
"""
from flask import Blueprint, request, jsonify, Response
from datetime import datetime

from backend.services.portfolio import portfolio_service
from backend.services.price import price_service
from backend.services.import_export import import_export_service
from backend.services.strategy import strategy_service
from backend.services.fiscal import fiscal_service
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
        return jsonify(summary)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/portfolio/history', methods=['GET'])
def get_portfolio_history():
    """Récupère l'historique du portefeuille"""
    days = request.args.get('days', 30, type=int)
    try:
        history = portfolio_service.get_portfolio_history(days=days)
        return jsonify(history)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/portfolio/snapshot', methods=['POST'])
def create_snapshot():
    """Crée un snapshot du portefeuille"""
    try:
        snapshot = portfolio_service.create_snapshot()
        return jsonify(snapshot.to_dict()), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================
# HOLDINGS ENDPOINTS
# ============================================================

@api_bp.route('/holdings', methods=['GET'])
def get_holdings():
    """Récupère les positions détaillées"""
    try:
        holdings = portfolio_service.get_holdings()
        return jsonify(holdings)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/holdings/<symbol>', methods=['GET'])
def get_holding(symbol):
    """Récupère les détails d'une position"""
    try:
        holding = portfolio_service.get_holding_details(symbol)
        if holding:
            return jsonify(holding)
        return jsonify({'error': 'Position not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


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
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/transactions', methods=['POST'])
def add_transaction():
    """Ajoute une nouvelle transaction"""
    data = request.get_json()

    required = ['symbol', 'type', 'volume', 'price', 'date']
    for field in required:
        if field not in data:
            return jsonify({'error': f'Missing field: {field}'}), 400

    try:
        tx = portfolio_service.add_transaction(data)
        return jsonify(tx.to_dict()), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/transactions/<int:tx_id>', methods=['PUT'])
def update_transaction(tx_id):
    """Met à jour une transaction"""
    data = request.get_json()

    try:
        tx = portfolio_service.update_transaction(tx_id, data)
        if tx:
            return jsonify(tx.to_dict())
        return jsonify({'error': 'Transaction not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/transactions/<int:tx_id>', methods=['DELETE'])
def delete_transaction(tx_id):
    """Supprime une transaction"""
    try:
        if portfolio_service.delete_transaction(tx_id):
            return jsonify({'success': True})
        return jsonify({'error': 'Transaction not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================
# PRICES ENDPOINTS
# ============================================================

@api_bp.route('/prices', methods=['GET'])
def get_prices():
    """Récupère les prix actuels"""
    symbols = request.args.get('symbols', '').split(',')
    symbols = [s.strip().upper() for s in symbols if s.strip()]

    if not symbols:
        # Récupérer les symboles des holdings
        holdings = portfolio_service.get_holdings()
        symbols = [h['symbol'] for h in holdings]

    try:
        prices = price_service.get_prices(symbols)
        return jsonify(prices)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/prices/<symbol>', methods=['GET'])
def get_price(symbol):
    """Récupère le prix d'une crypto"""
    try:
        price = price_service.get_price(symbol.upper())
        change = price_service.get_price_change_24h(symbol.upper())
        return jsonify({
            'symbol': symbol.upper(),
            'price': price,
            'change_24h': change
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================
# IMPORT/EXPORT ENDPOINTS
# ============================================================

@api_bp.route('/import', methods=['POST'])
def import_file():
    """Importe un fichier de transactions"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    try:
        content = file.read().decode('utf-8')
        source = request.form.get('source', 'auto')

        # Détection automatique du format
        if source == 'auto':
            source = import_export_service.detect_format(content)

        if source == 'binance':
            result = import_export_service.import_binance_csv(content, file.filename)
        elif source == 'kucoin':
            result = import_export_service.import_kucoin_csv(content, file.filename)
        else:
            # Format générique - nécessite un mapping
            mapping = request.form.get('mapping')
            if mapping:
                import json
                mapping = json.loads(mapping)
                result = import_export_service.import_generic_csv(
                    content, mapping,
                    exchange=source or 'manual',
                    filename=file.filename
                )
            else:
                return jsonify({'error': 'Unknown format and no mapping provided'}), 400

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/export/transactions', methods=['GET'])
def export_transactions():
    """Exporte les transactions"""
    format_type = request.args.get('format', 'csv')
    crypto_id = request.args.get('crypto_id', type=int)
    exchange = request.args.get('exchange')

    try:
        if format_type == 'json':
            content = import_export_service.export_transactions_json(
                crypto_id=crypto_id,
                exchange=exchange
            )
            mimetype = 'application/json'
            filename = 'transactions.json'
        else:
            content = import_export_service.export_transactions_csv(
                crypto_id=crypto_id,
                exchange=exchange
            )
            mimetype = 'text/csv'
            filename = 'transactions.csv'

        return Response(
            content,
            mimetype=mimetype,
            headers={'Content-Disposition': f'attachment; filename={filename}'}
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================
# STRATEGIES ENDPOINTS
# ============================================================

@api_bp.route('/strategies', methods=['GET'])
def get_strategies():
    """Récupère les stratégies de sortie"""
    try:
        strategies = strategy_service.get_strategies()
        return jsonify(strategies)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/strategies/<int:strategy_id>', methods=['GET'])
def get_strategy(strategy_id):
    """Récupère une stratégie"""
    try:
        strategy = strategy_service.get_strategy(strategy_id)
        if strategy:
            return jsonify(strategy)
        return jsonify({'error': 'Strategy not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/strategies', methods=['POST'])
def create_strategy():
    """Crée une stratégie de sortie"""
    data = request.get_json()

    if 'symbol' not in data:
        return jsonify({'error': 'Missing symbol'}), 400

    try:
        strategy = strategy_service.create_strategy(
            crypto_symbol=data['symbol'],
            thresholds=data.get('thresholds'),
            mode=data.get('mode', 'alert'),
            enabled=data.get('enabled', True)
        )
        return jsonify(strategy.to_dict()), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/strategies/<int:strategy_id>', methods=['PUT'])
def update_strategy(strategy_id):
    """Met à jour une stratégie"""
    data = request.get_json()

    try:
        strategy = strategy_service.update_strategy(strategy_id, data)
        if strategy:
            return jsonify(strategy.to_dict())
        return jsonify({'error': 'Strategy not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/strategies/<int:strategy_id>', methods=['DELETE'])
def delete_strategy(strategy_id):
    """Supprime une stratégie"""
    try:
        if strategy_service.delete_strategy(strategy_id):
            return jsonify({'success': True})
        return jsonify({'error': 'Strategy not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/strategies/check', methods=['POST'])
def check_strategies():
    """Vérifie les stratégies et crée les alertes"""
    try:
        alerts = strategy_service.check_strategies()
        return jsonify({
            'new_alerts': len(alerts),
            'alerts': [a.to_dict() for a in alerts]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================
# ALERTS ENDPOINTS
# ============================================================

@api_bp.route('/alerts', methods=['GET'])
def get_alerts():
    """Récupère les alertes en attente"""
    try:
        alerts = strategy_service.get_pending_alerts()
        return jsonify(alerts)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/alerts/<int:alert_id>/execute', methods=['POST'])
def execute_alert(alert_id):
    """Exécute une alerte (enregistre la vente)"""
    data = request.get_json() or {}

    try:
        tx = strategy_service.execute_alert(
            alert_id,
            actual_price=data.get('price'),
            actual_volume=data.get('volume'),
            notes=data.get('notes')
        )
        if tx:
            return jsonify({
                'success': True,
                'transaction': tx.to_dict()
            })
        return jsonify({'error': 'Alert not found or already processed'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/alerts/<int:alert_id>/dismiss', methods=['POST'])
def dismiss_alert(alert_id):
    """Ignore une alerte"""
    data = request.get_json() or {}

    try:
        if strategy_service.dismiss_alert(alert_id, notes=data.get('notes')):
            return jsonify({'success': True})
        return jsonify({'error': 'Alert not found or already processed'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================
# FISCAL ENDPOINTS
# ============================================================

@api_bp.route('/fiscal/<int:year>', methods=['GET'])
def get_fiscal_report(year):
    """Récupère le rapport fiscal pour une année"""
    try:
        report = fiscal_service.calculate_yearly_gains(year)
        return jsonify(report)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/fiscal/<int:year>/export', methods=['GET'])
def export_fiscal_report(year):
    """Exporte le rapport fiscal"""
    format_type = request.args.get('format', 'text')

    try:
        if format_type == 'csv':
            content = fiscal_service.export_fiscal_csv(year)
            mimetype = 'text/csv'
            filename = f'rapport_fiscal_{year}.csv'
        else:
            content = fiscal_service.generate_fiscal_report(year)
            mimetype = 'text/plain'
            filename = f'rapport_fiscal_{year}.txt'

        return Response(
            content,
            mimetype=mimetype,
            headers={'Content-Disposition': f'attachment; filename={filename}'}
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================
# CRYPTOS ENDPOINTS
# ============================================================

@api_bp.route('/cryptos', methods=['GET'])
def get_cryptos():
    """Récupère la liste des cryptos"""
    try:
        cryptos = Crypto.query.all()
        return jsonify([c.to_dict() for c in cryptos])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/cryptos', methods=['POST'])
def add_crypto():
    """Ajoute une crypto"""
    data = request.get_json()

    if 'symbol' not in data:
        return jsonify({'error': 'Missing symbol'}), 400

    try:
        crypto = Crypto.get_or_create(
            symbol=data['symbol'],
            name=data.get('name'),
            coingecko_id=data.get('coingecko_id')
        )
        return jsonify(crypto.to_dict()), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
